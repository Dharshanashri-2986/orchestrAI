"""
career_readiness_agent.py — Career Readiness Score Calculator
OrchestrAI Autonomous Multi-Agent System

PURPOSE:
  Calculate an overall Career Readiness Score (0-100) by combining:
    - Skill Coverage    (40%) — how well skills match target roles
    - Portfolio Score   (20%) — number/quality of projects
    - Interview Score   (20%) — practice sessions completed
    - Security Health   (20%) — GitHub repo security posture

FORMULA:
  readiness_score =
      0.40 * skill_coverage
    + 0.20 * portfolio_score
    + 0.20 * interview_practice_score
    + 0.20 * security_score

OUTPUT: database/career_readiness.yaml
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from backend.github_yaml_db import (
    read_yaml_from_github,
    write_yaml_to_github,
    append_log_entry,
)

load_dotenv()
logger = logging.getLogger("OrchestrAI.CareerReadinessAgent")

# ── File paths ────────────────────────────────────────────────────────────────
SCORES_FILE    = "database/opportunity_scores.yaml"
SKILL_GAP_FILE = "database/skill_gap_per_job.yaml"
SECURITY_FILE  = "database/security_reports.yaml"
PORTFOLIO_FILE = "database/portfolio.yaml"
PRACTICE_FILE  = "database/practice_sessions.yaml"
READINESS_FILE = "database/career_readiness.yaml"


# ==============================================================================
# Component scorers (each returns 0–100)
# ==============================================================================

def _score_skill_coverage() -> tuple[float, str]:
    """
    Skill coverage = how many jobs have ALL required skills covered.
    Uses skill_gap_per_job.yaml: if missing_skills is empty → fully covered.
    """
    try:
        data = read_yaml_from_github(SKILL_GAP_FILE) or {}
        analyses = data.get("job_skill_analysis", [])
        if not analyses:
            return 50.0, "No skill gap data yet — run SkillAgent first"

        total = len(analyses)
        fully_covered = sum(1 for a in analyses if not a.get("missing_skills"))
        partial = sum(1 for a in analyses if 0 < len(a.get("missing_skills", [])) <= 3)
        # Weighted: full coverage = 1 pt, partial = 0.5 pt
        raw = (fully_covered + 0.5 * partial) / total
        score = round(min(100, raw * 100), 1)

        top_gaps = []
        from collections import Counter
        freq: Counter = Counter()
        for a in analyses:
            for s in a.get("missing_skills", []):
                freq[str(s)] += 1
        top_gaps = [s for s, _ in freq.most_common(3)]

        detail = f"{fully_covered}/{total} roles fully covered"
        if top_gaps:
            detail += f". Top gaps: {', '.join(top_gaps)}"
        logger.info("CareerReadinessAgent: Skill coverage = %.1f — %s", score, detail)
        return score, detail
    except Exception as exc:
        logger.warning("CareerReadinessAgent: Skill coverage error — %s", exc)
        return 50.0, "Could not compute skill coverage"


def _score_portfolio() -> tuple[float, str]:
    """
    Portfolio score based on project count, demo links, and stars.
    Max score: 100 (7+ projects with demos = 100)
    """
    try:
        data = read_yaml_from_github(PORTFOLIO_FILE) or {}
        projects = data.get("portfolio", {}).get("projects", [])
        if not isinstance(projects, list):
            return 0.0, "No portfolio data"

        n = len(projects)
        demos = sum(1 for p in projects if p.get("demo_url") and p.get("demo_url") != "#")
        stars = sum(int(p.get("stars", 0)) for p in projects)

        # Scoring rubric
        project_pts = min(50, n * 8)          # 8 pts per project, max 50
        demo_pts    = min(30, demos * 10)      # 10 pts per demo, max 30
        star_pts    = min(20, stars // 5)      # 1 pt per 5 stars, max 20
        score = round(project_pts + demo_pts + star_pts, 1)

        detail = f"{n} projects, {demos} with live demos, {stars} total stars"
        logger.info("CareerReadinessAgent: Portfolio = %.1f — %s", score, detail)
        return score, detail
    except Exception as exc:
        logger.warning("CareerReadinessAgent: Portfolio score error — %s", exc)
        return 0.0, "Could not compute portfolio score"


def _score_interview_practice() -> tuple[float, str]:
    """
    Interview readiness based on number of practice sessions.
    5 sessions = 100%. Linear scaling.
    """
    try:
        data = read_yaml_from_github(PRACTICE_FILE)
        sessions = data if isinstance(data, list) else []
        count = len(sessions)
        TARGET = 5
        score = round(min(100, (count / TARGET) * 100), 1)
        detail = f"{count} session{'s' if count != 1 else ''} completed (target: {TARGET})"
        if count >= TARGET:
            detail += " ✅ Interview-ready!"
        logger.info("CareerReadinessAgent: Interview practice = %.1f — %s", score, detail)
        return score, detail
    except Exception as exc:
        logger.warning("CareerReadinessAgent: Practice score error — %s", exc)
        return 0.0, "No practice session data"


def _score_security_health() -> tuple[float, str]:
    """
    Security health = inverse of risk.
    All Safe = 100, each High repo = -20, each Medium = -10, each Low = -5.
    """
    try:
        data = read_yaml_from_github(SECURITY_FILE) or {}
        reports = data.get("security_reports", [])
        if not reports:
            return 100.0, "No repos scanned yet — assume healthy"

        total = len(reports)
        high   = sum(1 for r in reports if r.get("risk_level") == "High")
        medium = sum(1 for r in reports if r.get("risk_level") == "Medium")
        low    = sum(1 for r in reports if r.get("risk_level") == "Low")

        penalty = (high * 20) + (medium * 10) + (low * 5)
        score = round(max(0, 100 - penalty), 1)

        detail = f"{total} repos scanned: {high} High, {medium} Medium, {low} Low risk"
        logger.info("CareerReadinessAgent: Security health = %.1f — %s", score, detail)
        return score, detail
    except Exception as exc:
        logger.warning("CareerReadinessAgent: Security score error — %s", exc)
        return 100.0, "Could not compute security score"


def _readiness_label(score: float) -> str:
    if score >= 85: return "🚀 Job-Ready"
    if score >= 70: return "✅ Strong Candidate"
    if score >= 55: return "📈 Good Progress"
    if score >= 40: return "⚠️ Needs Work"
    return "🛠️ Early Stage"


def _get_top_recommendations(
    skill_score: float, portfolio_score: float,
    practice_score: float, security_score: float,
    skill_detail: str, portfolio_detail: str,
    practice_detail: str
) -> list[str]:
    recs = []
    components = [
        (skill_score,     "skill",     skill_detail),
        (practice_score,  "practice",  practice_detail),
        (portfolio_score, "portfolio", portfolio_detail),
        (security_score,  "security",  ""),
    ]
    # Sort by weakest first
    for score, kind, detail in sorted(components, key=lambda x: x[0]):
        if kind == "skill" and score < 80:
            recs.append(f"Close skill gaps — {detail.split('.')[0] if '.' in detail else detail}")
        elif kind == "practice" and score < 80:
            recs.append(f"Complete more mock interviews — {detail}")
        elif kind == "portfolio" and score < 80:
            recs.append(f"Strengthen your portfolio — {detail}")
        elif kind == "security" and score < 80:
            recs.append("Fix HIGH-risk security vulnerabilities in your GitHub repos")
        if len(recs) >= 3:
            break
    return recs or ["You're doing great — keep maintaining your skills!"]


# ==============================================================================
# Main agent function
# ==============================================================================

def run_career_readiness_agent() -> dict:
    """
    Compute career readiness score and save to database/career_readiness.yaml.
    """
    logger.info("CareerReadinessAgent: Computing readiness score...")

    skill_score,    skill_detail    = _score_skill_coverage()
    portfolio_score, portfolio_detail = _score_portfolio()
    practice_score,  practice_detail  = _score_interview_practice()
    security_score,  security_detail  = _score_security_health()

    # Weighted formula
    readiness_score = round(
        0.40 * skill_score
        + 0.20 * portfolio_score
        + 0.20 * practice_score
        + 0.20 * security_score,
        1
    )

    label = _readiness_label(readiness_score)
    recommendations = _get_top_recommendations(
        skill_score, portfolio_score, practice_score, security_score,
        skill_detail, portfolio_detail, practice_detail
    )

    output = {
        "career_readiness": {
            "readiness_score":       readiness_score,
            "label":                 label,
            "generated_at":          datetime.now(timezone.utc).isoformat(),
            "components": {
                "skill_coverage": {
                    "score":  skill_score,
                    "weight": "40%",
                    "detail": skill_detail,
                },
                "portfolio_strength": {
                    "score":  portfolio_score,
                    "weight": "20%",
                    "detail": portfolio_detail,
                },
                "interview_practice": {
                    "score":  practice_score,
                    "weight": "20%",
                    "detail": practice_detail,
                },
                "security_health": {
                    "score":  security_score,
                    "weight": "20%",
                    "detail": security_detail,
                },
            },
            "top_recommendations": recommendations,
        }
    }

    try:
        write_yaml_to_github(READINESS_FILE, output)
        logger.info("CareerReadinessAgent: Saved readiness score %.1f (%s)", readiness_score, label)
    except Exception as exc:
        logger.error("CareerReadinessAgent: Failed to save — %s", exc)

    try:
        append_log_entry({
            "agent":     "CareerReadinessAgent",
            "action":    f"Computed readiness score: {readiness_score} — {label}",
            "status":    "completed",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        })
    except Exception:
        pass

    logger.info("CareerReadinessAgent: Done. Score=%.1f | %s", readiness_score, label)
    return output


# ==============================================================================
# Stand-alone entry point
# ==============================================================================
if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    result = run_career_readiness_agent()
    cr = result.get("career_readiness", {})
    print(f"\n{'='*55}")
    print(f"🎯 CAREER READINESS SCORE: {cr.get('readiness_score')}/100  {cr.get('label')}")
    print(f"{'='*55}")
    for name, comp in cr.get("components", {}).items():
        print(f"  {name:22s}: {comp['score']:5.1f}/100  ({comp['weight']}) — {comp['detail']}")
    print(f"\n📋 Top Recommendations:")
    for i, rec in enumerate(cr.get("top_recommendations", []), 1):
        print(f"  {i}. {rec}")
