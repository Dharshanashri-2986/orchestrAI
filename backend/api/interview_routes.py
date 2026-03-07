"""
interview_routes.py — Real-Time Interview API
OrchestrAI Autonomous Multi-Agent System

Provides endpoints for the conversational AI interviewer, 
dynamic difficulty tracking, and coding challenges.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.agents.interview_agent import generate_next_question, evaluate_answer
from backend.agents.coding_interview_agent import generate_coding_problem, evaluate_code

logger = logging.getLogger("OrchestrAI.InterviewAPI")

router = APIRouter(prefix="/api/interview", tags=["Interview API"])

@router.post("/ask")
async def ask_interview_question(request: Request):
    """
    Generate the next AI interview question.
    """
    try:
        body = await request.json()
        company = body.get("company", "the company")
        role = body.get("role", "the role")
        question_history = body.get("question_history", [])
        user_answer = body.get("user_answer", None)
        difficulty = body.get("difficulty", "medium")

        result = generate_next_question(
            company=company,
            role=role,
            question_history=question_history,
            user_answer=user_answer,
            difficulty=difficulty,
        )
        return JSONResponse(result)

    except Exception as exc:
        logger.error("POST /api/interview/ask error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

@router.post("/evaluate")
async def evaluate_interview_answer(request: Request):
    """
    Evaluate a candidate's answer.
    """
    try:
        body = await request.json()
        company = body.get("company", "the company")
        role = body.get("role", "the role")
        question = body.get("question", "")
        user_answer = body.get("user_answer", "")

        result = evaluate_answer(
            company=company,
            role=role,
            question=question,
            user_answer=user_answer,
        )
        return JSONResponse(result)

    except Exception as exc:
        logger.error("POST /api/interview/evaluate error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

@router.post("/coding/generate")
async def get_coding_problem(request: Request):
    """
    Generate a coding problem for the candidate.
    """
    try:
        body = await request.json()
        role = body.get("role", "Software Engineer")
        result = generate_coding_problem(role)
        return JSONResponse(result)
    except Exception as exc:
        logger.error("POST /api/interview/coding/generate error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

@router.post("/run_code")
async def run_interview_code(request: Request):
    """
    Evaluate candidate's code submission.
    """
    try:
        body = await request.json()
        problem = body.get("problem", "")
        code = body.get("code", "")
        result = evaluate_code(problem, code)
        return JSONResponse(result)
    except Exception as exc:
        logger.error("POST /api/interview/run_code error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

@router.post("/update_difficulty")
async def update_interview_difficulty(request: Request):
    """
    Update the difficulty level for a specific session in interview_sessions.yaml.
    """
    try:
        from backend.github_yaml_db import read_yaml_from_github, update_yaml
        
        body = await request.json()
        company = body.get("company", "")
        role = body.get("role", "")
        difficulty = body.get("difficulty", "medium")
        
        file_path = "database/interview_sessions.yaml"
        db = read_yaml_from_github(file_path)
        sessions = db.get("interview_sessions", []) if isinstance(db, dict) else []
        
        updated = False
        for s in sessions:
            if s.get("company") == company and s.get("role") == role:
                s["current_difficulty"] = difficulty
                updated = True
                break
        
        if updated:
            db["interview_sessions"] = sessions
            update_yaml(file_path, db)
            return JSONResponse({"status": "ok", "difficulty": difficulty})
        
        return JSONResponse({"status": "not_found", "message": "Session not found in DB"}, status_code=404)

    except Exception as exc:
        logger.error("POST /api/interview/update_difficulty error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)
