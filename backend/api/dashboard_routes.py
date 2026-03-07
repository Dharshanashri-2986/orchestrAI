"""
dashboard_routes.py — Dashboard API Endpoints
OrchestrAI Autonomous Multi-Agent System

Provides JSON API for the interactive career dashboard.
"""

from __future__ import annotations

import logging
import os
from fastapi import APIRouter
from backend.github_yaml_db import read_yaml_from_github

logger = logging.getLogger("OrchestrAI.DashboardAPI")

router = APIRouter(prefix="/api", tags=["Dashboard API"])


@router.get("/dashboard")
async def get_dashboard_data():
    """
    Return all dashboard data in a single API call.
    Reads from GitHub YAML database and returns structured JSON.
    """
    logger.info("DashboardAPI: Fetching all dashboard data...")

    jobs_data = read_yaml_from_github("database/jobs.yaml")
    skill_gap_data = read_yaml_from_github("database/skill_gap_per_job.yaml")
    cover_letter_data = read_yaml_from_github("database/cover_letter_index.yaml")
    optimization_data = read_yaml_from_github("database/resume_optimizations.yaml")
    scores_data = read_yaml_from_github("database/opportunity_scores.yaml")
    practice_data = read_yaml_from_github("database/practice_sessions.yaml")
    portfolio_data = read_yaml_from_github("database/portfolio.yaml")
    security_data = read_yaml_from_github("database/security_reports.yaml")
    strategy_data = read_yaml_from_github("database/career_strategy.yaml")
    readiness_data = read_yaml_from_github("database/career_readiness.yaml")
    interview_data = read_yaml_from_github("database/interview_sessions.yaml")
    per_internship_data = read_yaml_from_github("database/per_internship_portfolios.yaml")

    def _clean_apply_link(link: str) -> str:
        if isinstance(link, str) and "linkedin.com/jobs/view/" in link:
            return link.split("?")[0]
        return link

    # Normalize all data to safe structures
    jobs = jobs_data.get("jobs", []) if isinstance(jobs_data, dict) else []
    for j in jobs:
        if "apply_link" in j:
            j["apply_link"] = _clean_apply_link(j["apply_link"])

    skill_analysis = skill_gap_data.get("job_skill_analysis", []) if isinstance(skill_gap_data, dict) else []
    cover_letters = cover_letter_data.get("cover_letters", []) if isinstance(cover_letter_data, dict) else []
    optimizations = optimization_data if isinstance(optimization_data, list) else []
    scores = scores_data if isinstance(scores_data, list) else []
    practice = practice_data if isinstance(practice_data, list) else []
    portfolio = portfolio_data.get("portfolio", {}) if isinstance(portfolio_data, dict) else {}
    security_reports = security_data.get("security_reports", []) if isinstance(security_data, dict) else []
    strategy = strategy_data.get("strategy", {}) if isinstance(strategy_data, dict) else {}
    readiness = readiness_data.get("career_readiness", {}) if isinstance(readiness_data, dict) else {}
    interviews = interview_data.get("interview_sessions", []) if isinstance(interview_data, dict) else []
    per_internship = per_internship_data.get("per_internship_portfolios", []) if isinstance(per_internship_data, dict) else []

    logger.info("DashboardAPI: Returning %d jobs, %d security reports.", len(jobs), len(security_reports))

    _render_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")

    def normalize_urls(data):
        if isinstance(data, dict):
            return {k: normalize_urls(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [normalize_urls(item) for item in data]
        elif isinstance(data, str) and _render_url and data.startswith(_render_url):
            return data.replace(_render_url, "")
        return data

    result = {
        "jobs": jobs,
        "skill_analysis": skill_analysis,
        "cover_letters": cover_letters,
        "optimizations": optimizations,
        "scores": scores,
        "practice": practice,
        "portfolio": portfolio,
        "security_reports": security_reports,
        "strategy": strategy,
        "readiness": readiness,
        "interviews": interviews,
        "per_internship_portfolios": per_internship,
    }
    return normalize_urls(result)
