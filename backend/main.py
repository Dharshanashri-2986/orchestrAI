"""
server.py — OrchestrAI FastAPI Server
Real-Time Interactive Interview Coach API

Run locally:
    uvicorn backend.server:app --reload --port 8000

API Docs:
    http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.practice_routes import router as practice_router
from backend.api.interview_routes import router as interview_router
from backend.api.dashboard_routes import router as dashboard_router
from backend.agents.interview_feedback_agent import append_feedback_entry

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("OrchestrAI.Server")

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="OrchestrAI Practice API",
    description=(
        "Real-Time AI Interview Coach — powered by Google Gemini.\n\n"
        "Ask interview questions in Tamil or English and receive:\n"
        "- Professional interview answers\n"
        "- Simplified practice versions\n"
        "- Confidence tips\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — allow practice HTML pages (hosted on GitHub Pages) to call this API ─
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # In production, restrict to your GitHub Pages domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(practice_router)
app.include_router(interview_router)
app.include_router(dashboard_router)

# ── Static Files ──────────────────────────────────────────────────────────────
# Serve the frontend directory at /frontend
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "OrchestrAI Practice API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health":     "GET  /practice/health",
            "ask":        "POST /practice/{company}/{role}/ask",
            "interview":  "BASE /api/interview",
            "dashboard":  "GET  /api/dashboard",
        },
    }


@app.post("/log-feedback")
async def log_feedback(request: Request):
    """
    Endpoint for the interview debrief form.
    Logs feedback to database/interview_feedback.yaml for secondary analysis.
    """
    try:
        payload = await request.json()
        logger.info("POST /log-feedback received for %s", payload.get("company"))
        success = append_feedback_entry(payload)
        if success:
            return {"status": "ok", "message": "Feedback logged successfully"}
        return JSONResponse({"status": "error", "message": "Failed to write to database"}, status_code=500)
    except Exception as e:
        logger.error("POST /log-feedback error: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
