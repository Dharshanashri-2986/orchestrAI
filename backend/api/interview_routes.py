"""
interview_routes.py — Real-Time Interview API
OrchestrAI Autonomous Multi-Agent System

Provides endpoints for the conversational AI interviewer,
dynamic difficulty tracking, coding challenges, and final reports.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.agents.interview_agent import (
    generate_next_question,
    evaluate_answer,
    generate_final_report,
)
from backend.agents.coding_interview_agent import (
    generate_coding_problem,
    evaluate_code,
    execute_code_judge0,
    generate_code_review,
    get_hint,
)

logger = logging.getLogger("OrchestrAI.InterviewAPI")

router = APIRouter(prefix="/api/interview", tags=["Interview API"])


@router.post("/ask")
async def ask_interview_question(request: Request):
    """Generate the next adaptive AI interview question."""
    try:
        body = await request.json()
        company = body.get("company", "the company")
        role = body.get("role", "the role")
        question_history = body.get("question_history", [])
        user_answer = body.get("user_answer", None)
        difficulty = body.get("difficulty", "medium")
        portfolio_projects = body.get("portfolio_projects", [])

        result = generate_next_question(
            company=company,
            role=role,
            question_history=question_history,
            user_answer=user_answer,
            difficulty=difficulty,
            portfolio_projects=portfolio_projects,
        )
        return JSONResponse(result)

    except Exception as exc:
        logger.error("POST /api/interview/ask error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/evaluate")
async def evaluate_interview_answer(request: Request):
    """Evaluate a candidate's answer with 5 metrics + AI feedback."""
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
    """Generate a coding problem with test cases, hints, and starter code."""
    try:
        body = await request.json()
        role = body.get("role", "Software Engineer")
        difficulty = body.get("difficulty", "medium")
        result = generate_coding_problem(role, difficulty)
        return JSONResponse(result)
    except Exception as exc:
        logger.error("POST /api/interview/coding/generate error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/execute_code")
async def execute_code_endpoint(request: Request):
    """
    Execute code via Judge0 API against test cases.
    Returns real pass/fail results per test case.
    """
    try:
        body = await request.json()
        code = body.get("code", "")
        language = body.get("language", "python")
        test_cases = body.get("test_cases", [])
        problem = body.get("problem", "")

        # Try real Judge0 execution
        result = execute_code_judge0(code=code, language=language, test_cases=test_cases)
        return JSONResponse(result)

    except Exception as exc:
        logger.error("POST /api/interview/execute_code error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/run_code")
async def run_interview_code(request: Request):
    """Legacy endpoint: AI-based code evaluation (no real execution)."""
    try:
        body = await request.json()
        problem = body.get("problem", "")
        code = body.get("code", "")
        result = evaluate_code(problem, code)
        return JSONResponse(result)
    except Exception as exc:
        logger.error("POST /api/interview/run_code error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/code_review")
async def code_review_endpoint(request: Request):
    """Generate detailed AI code review after submission."""
    try:
        body = await request.json()
        problem = body.get("problem", "")
        code = body.get("code", "")
        execution_results = body.get("execution_results", None)

        result = generate_code_review(problem=problem, code=code, execution_results=execution_results)
        return JSONResponse(result)

    except Exception as exc:
        logger.error("POST /api/interview/code_review error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/hint")
async def get_coding_hint(request: Request):
    """Return a specific progressive hint for a coding problem."""
    try:
        body = await request.json()
        problem = body.get("problem", "")
        hints = body.get("hints", [])
        hint_index = int(body.get("hint_index", 0))

        result = get_hint(problem=problem, hints=hints, hint_index=hint_index)
        return JSONResponse(result)

    except Exception as exc:
        logger.error("POST /api/interview/hint error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/report")
async def generate_interview_report(request: Request):
    """Generate a final interview performance report."""
    try:
        body = await request.json()
        company = body.get("company", "the company")
        role = body.get("role", "the role")
        evaluations = body.get("evaluations", [])
        coding_score = body.get("coding_score", None)

        result = generate_final_report(
            company=company,
            role=role,
            evaluations=evaluations,
            coding_score=coding_score,
        )
        return JSONResponse(result)

    except Exception as exc:
        logger.error("POST /api/interview/report error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/update_difficulty")
async def update_interview_difficulty(request: Request):
    """Update the difficulty level for a specific session in interview_sessions.yaml."""
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

        return JSONResponse({"status": "not_found", "message": "Session not found"}, status_code=404)

    except Exception as exc:
        logger.error("POST /api/interview/update_difficulty error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)
