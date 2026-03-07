"""
interview_routes.py — Real-Time Interview API
OrchestrAI Autonomous Multi-Agent System

Provides the POST /api/interview/ask endpoint for the conversational
AI interviewer on the frontend interview pages.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.agents.interview_agent import generate_next_question, evaluate_answer

logger = logging.getLogger("OrchestrAI.InterviewAPI")

router = APIRouter(prefix="/api/interview", tags=["Interview API"])


@router.post("/ask")
async def ask_interview_question(request: Request):
    """
    Generate the next AI interview question.

    Body:
      {
        "company": "Tinder",
        "role": "Machine Learning Engineer Intern",
        "question_history": [
            {"role": "ai", "content": "..."},
            {"role": "user", "content": "..."}
        ],
        "user_answer": "optional string"
      }

    Returns:
      { "next_question": "...", "question_type": "technical|behavioral|coding" }
    """
    try:
        body = await request.json()
        company = body.get("company", "the company")
        role = body.get("role", "the role")
        question_history = body.get("question_history", [])
        user_answer = body.get("user_answer", None)

        result = generate_next_question(
            company=company,
            role=role,
            question_history=question_history,
            user_answer=user_answer,
        )

        return JSONResponse(result)

    except Exception as exc:
        logger.error("POST /api/interview/ask error: %s", exc)
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )


@router.post("/evaluate")
async def evaluate_interview_answer(request: Request):
    """
    Evaluate a candidate's answer.

    Body:
      {
        "company": "Tinder",
        "role": "Machine Learning Engineer Intern",
        "question": "...",
        "user_answer": "..."
      }

    Returns:
      {
        "technical_score": int,
        "clarity_score": int,
        "communication_score": int,
        "feedback": "string"
      }
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
        return JSONResponse(
            {"status": "error", "message": str(exc)},
            status_code=500,
        )

