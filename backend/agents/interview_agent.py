"""
interview_agent.py — Real-Time AI Interviewer
OrchestrAI Autonomous Multi-Agent System

PURPOSE:
  Provide a conversational AI interviewer that dynamically generates
  interview questions and follow-up questions based on the user's answers.
  Includes portfolio-personalized questions and a 5-metric evaluation system.
"""

from __future__ import annotations
import logging
import os
import re
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger("OrchestrAI.InterviewAgent")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
openai_client = (
    OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL, max_retries=0)
    if GEMINI_API_KEY
    else None
)


def generate_next_question(
    company: str,
    role: str,
    question_history: list[dict],
    user_answer: str | None = None,
    difficulty: str = "medium",
    portfolio_projects: list[str] | None = None,
) -> dict:
    """
    Generate the next adaptive interview question.

    Parameters
    ----------
    company         : Target company name
    role            : Target role
    question_history: Previous Q&A pairs [{role: "ai"|"user", content: "..."}]
    user_answer     : The candidate's latest answer (if any)
    difficulty      : "easy", "medium", or "hard"
    portfolio_projects: List of GitHub project names for personalized questions

    Returns dict { "next_question": str, "question_type": str, "follow_up_context": str }
    """

    if not openai_client:
        return {
            "next_question": f"Tell me about your experience relevant to the {role} position at {company}.",
            "question_type": "behavioral",
            "follow_up_context": "",
        }

    # Portfolio context string
    portfolio_ctx = ""
    if portfolio_projects:
        project_list = ", ".join(portfolio_projects[:5])
        portfolio_ctx = (
            f"\n\nCONTEXT: The candidate's GitHub portfolio includes these projects: {project_list}. "
            f"Occasionally reference these projects in your questions to make the interview personalized and realistic. "
            f"For example: 'I see you built {portfolio_projects[0] if portfolio_projects else 'a project'}. "
            f"Tell me about the architecture and design decisions you made for it.'"
        )

    system_prompt = (
        f"You are a senior technical interviewer at {company}. "
        f"You are conducting a real-time interview for the role: {role}. "
        f"Current difficulty level: {difficulty.upper()}. "
        f"Your style is professional, encouraging, and conversational. "
        f"Ask ONE question at a time. Naturally alternate between technical, behavioral and coding topics. "
        f"Generate a {difficulty} difficulty question. "
        f"IMPORTANT: If the candidate just answered a question, FIRST write a 1-sentence acknowledgment "
        f"that is specific to their answer (e.g., 'That's a solid approach for handling large datasets.'). "
        f"Then pivot to a deeper follow-up OR a new topic as appropriate. "
        f"The follow-up should go deeper into what they just mentioned — "
        f"e.g., if they mention 'data pipelines', ask about pipeline optimization or failure handling. "
        f"Keep the question concise and specific to the {role} role."
        f"{portfolio_ctx}"
        f"\n\nAt the end of your response on a new line, add EXACTLY one classification tag: "
        f"[TYPE:technical] or [TYPE:behavioral] or [TYPE:coding]"
    )

    messages = [{"role": "system", "content": system_prompt}]

    for entry in question_history:
        if entry.get("role") == "ai":
            messages.append({"role": "assistant", "content": entry["content"]})
        elif entry.get("role") == "user":
            messages.append({"role": "user", "content": entry["content"]})

    if not question_history and not user_answer:
        messages.append({
            "role": "user",
            "content": f"Please begin the interview at {difficulty} difficulty. Greet me briefly and ask your first question.",
        })
    elif user_answer:
        messages.append({"role": "user", "content": user_answer})

    try:
        resp = openai_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=messages,
            max_tokens=500,
            temperature=0.75,
        )
        raw = resp.choices[0].message.content.strip()

        question_type = "technical"
        clean_text = raw
        for tag in ["[TYPE:technical]", "[TYPE:behavioral]", "[TYPE:coding]"]:
            if tag in raw:
                question_type = tag.replace("[TYPE:", "").replace("]", "")
                clean_text = raw.replace(tag, "").strip()
                break

        # Extract follow-up context (first sentence = acknowledgment)
        sentences = clean_text.split(". ")
        follow_up_context = sentences[0].strip() if len(sentences) > 1 else ""

        return {
            "next_question": clean_text,
            "question_type": question_type,
            "follow_up_context": follow_up_context,
        }

    except Exception as exc:
        logger.error("InterviewAgent: Gemini call failed — %s", exc)
        if not question_history:
            return {
                "next_question": (
                    f"Welcome! Let's begin your {difficulty} difficulty interview for {role} at {company}. "
                    f"Can you walk me through your most relevant project experience?"
                ),
                "question_type": "behavioral",
                "follow_up_context": "",
            }
        return {
            "next_question": (
                "That's a solid point. Can you elaborate on the technical challenges "
                "you faced and how you overcame them?"
            ),
            "question_type": "technical",
            "follow_up_context": "",
        }


def evaluate_answer(
    company: str,
    role: str,
    question: str,
    user_answer: str,
) -> dict:
    """
    Evaluate an interview answer using 5 metrics.

    Returns
    -------
    dict {
        "technical_accuracy": int,      # 0-10
        "problem_solving": int,         # 0-10
        "communication_clarity": int,   # 0-10
        "system_thinking": int,         # 0-10
        "confidence": int,              # 0-10
        "overall_score": int,           # average
        "strengths": list[str],         # 2-3 bullet strengths
        "weaknesses": list[str],        # 2-3 bullet weaknesses
        "improvements": list[str],      # 2-3 actionable improvements
        "feedback": str                 # 1-2 sentence summary
    }
    """
    if not openai_client:
        return _fallback_evaluation()

    system_prompt = (
        f"You are an expert mock interview evaluator for {company}, assessing a candidate for {role}.\n"
        "Evaluate the candidate's answer on these 5 dimensions (score 1-10 each):\n"
        "1. technical_accuracy: Correctness and depth of technical knowledge\n"
        "2. problem_solving: Ability to analyze and solve problems systematically\n"
        "3. communication_clarity: Clarity, structure, and conciseness of explanation\n"
        "4. system_thinking: High-level thinking, trade-offs, scalability considerations\n"
        "5. confidence: Assertiveness and conviction in the response\n\n"
        "Also provide:\n"
        "- strengths: list of 2-3 specific strengths (what they did well)\n"
        "- weaknesses: list of 2-3 specific gaps or areas of improvement\n"
        "- improvements: list of 2-3 concrete, actionable suggestions\n"
        "- feedback: 1-2 sentence overall verdict\n\n"
        "Return EXACTLY this JSON (no markdown, no extra text):\n"
        "{\n"
        '  "technical_accuracy": 7,\n'
        '  "problem_solving": 8,\n'
        '  "communication_clarity": 6,\n'
        '  "system_thinking": 5,\n'
        '  "confidence": 7,\n'
        '  "strengths": ["Clear explanation of X", "Good use of Y"],\n'
        '  "weaknesses": ["Missed Z", "Could be more specific about W"],\n'
        '  "improvements": ["Try to mention trade-offs", "Add an example"],\n'
        '  "feedback": "Solid answer overall but needs more depth in system design."\n'
        "}"
    )

    user_prompt = f"Question: {question}\n\nCandidate's Answer: {user_answer}"

    try:
        resp = openai_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=600,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()

        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            data = json.loads(raw)

        scores = [
            int(data.get("technical_accuracy", 5)),
            int(data.get("problem_solving", 5)),
            int(data.get("communication_clarity", 5)),
            int(data.get("system_thinking", 5)),
            int(data.get("confidence", 5)),
        ]
        overall = round(sum(scores) / len(scores))

        return {
            "technical_accuracy": scores[0],
            "problem_solving": scores[1],
            "communication_clarity": scores[2],
            "system_thinking": scores[3],
            "confidence": scores[4],
            "overall_score": overall,
            "strengths": data.get("strengths", []),
            "weaknesses": data.get("weaknesses", []),
            "improvements": data.get("improvements", []),
            "feedback": str(data.get("feedback", "Good effort. Keep practicing!")),
            # Legacy fields for backward compatibility
            "technical_score": scores[0],
            "clarity_score": scores[2],
            "communication_score": scores[4],
        }

    except Exception as exc:
        logger.error("InterviewAgent: Evaluation failed — %s", exc)
        return _fallback_evaluation()


def generate_final_report(
    company: str,
    role: str,
    evaluations: list[dict],
    coding_score: int | None = None,
) -> dict:
    """
    Generate a final interview performance report.

    Parameters
    ----------
    evaluations : list of evaluation dicts from evaluate_answer()
    coding_score: score for coding section (0-100), if applicable

    Returns dict with overall scores, recommendations, verdict
    """
    if not evaluations:
        return {"error": "No evaluation data provided"}

    # Average each metric across all evaluations
    keys = ["technical_accuracy", "problem_solving", "communication_clarity", "system_thinking", "confidence"]
    averages = {}
    for k in keys:
        vals = [e.get(k, 5) for e in evaluations if isinstance(e.get(k), (int, float))]
        averages[k] = round(sum(vals) / len(vals)) if vals else 5

    overall_interview = round(sum(averages.values()) / len(averages))

    # Compile all strengths/weaknesses
    all_strengths = []
    all_weaknesses = []
    for e in evaluations:
        all_strengths.extend(e.get("strengths", []))
        all_weaknesses.extend(e.get("weaknesses", []))

    # Unique top items
    top_strengths = list(dict.fromkeys(all_strengths))[:4]
    top_weaknesses = list(dict.fromkeys(all_weaknesses))[:4]

    # Verdict
    if overall_interview >= 8:
        verdict = "🏆 Exceptional Candidate"
        verdict_color = "#10b981"
    elif overall_interview >= 7:
        verdict = "✅ Strong Candidate"
        verdict_color = "#06b6d4"
    elif overall_interview >= 5:
        verdict = "⚠️ Developing Candidate"
        verdict_color = "#f59e0b"
    else:
        verdict = "📘 Needs More Preparation"
        verdict_color = "#ef4444"

    # AI-generated recommendations
    recommendations = []
    if averages["system_thinking"] < 6:
        recommendations.append("Study System Design fundamentals — scalability, CAP theorem, database sharding")
    if averages["technical_accuracy"] < 6:
        recommendations.append(f"Review core technical concepts for {role} — algorithms, data structures, ML foundations")
    if averages["communication_clarity"] < 6:
        recommendations.append("Practice structured communication using the STAR method for behavioral questions")
    if averages["problem_solving"] < 6:
        recommendations.append("Work on problem decomposition — practice breaking complex problems into smaller steps")
    if averages["confidence"] < 6:
        recommendations.append("Build confidence by doing more mock interviews and reviewing fundamentals daily")
    if not recommendations:
        recommendations = [
            "Focus on optimizing code for edge cases and performance",
            "Practice system design with real-world scenarios",
            "Expand knowledge of distributed systems and cloud architecture",
        ]

    coding_included = coding_score is not None
    overall_total = round((overall_interview * 10 + (coding_score or 70)) / 2) if coding_included else overall_interview * 10

    return {
        "company": company,
        "role": role,
        "metrics": {
            "technical_knowledge": averages["technical_accuracy"] * 10,
            "problem_solving": averages["problem_solving"] * 10,
            "communication": averages["communication_clarity"] * 10,
            "system_thinking": averages["system_thinking"] * 10,
            "confidence": averages["confidence"] * 10,
            "coding_ability": coding_score or 70,
        },
        "overall_score": overall_total,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "top_strengths": top_strengths,
        "top_weaknesses": top_weaknesses,
        "recommendations": recommendations[:4],
        "total_questions": len(evaluations),
    }


def _fallback_evaluation() -> dict:
    return {
        "technical_accuracy": 6,
        "problem_solving": 6,
        "communication_clarity": 6,
        "system_thinking": 5,
        "confidence": 6,
        "overall_score": 6,
        "strengths": ["Shows understanding of core concepts", "Clear communication"],
        "weaknesses": ["Could go deeper into technical details", "Consider mentioning trade-offs"],
        "improvements": ["Add concrete examples", "Mention scalability considerations"],
        "feedback": "Good effort! Focus on adding more technical depth. (API key missing or error)",
        "technical_score": 6,
        "clarity_score": 6,
        "communication_score": 6,
    }
