"""
interview_agent.py — Real-Time AI Interviewer
OrchestrAI Autonomous Multi-Agent System

PURPOSE:
  Provide a conversational AI interviewer that dynamically generates
  interview questions and follow-up questions based on the user's answers.
  Turns static interview prep into a real-time interactive session.
"""

from __future__ import annotations
import logging
import os

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
) -> dict:
    """
    Generate the next interview question.

    Parameters
    ----------
    company : str          – Target company name (e.g. "Tinder")
    role : str             – Target role (e.g. "Machine Learning Engineer Intern")
    question_history : list – Previous Q&A pairs: [{"role":"ai","content":"..."}, ...]
    user_answer : str|None – The candidate's latest answer (if any)
    difficulty : str       – Difficulty level: "easy", "medium", or "hard"

    Returns
    -------
    dict  { "next_question": str, "question_type": str }
    """

    if not openai_client:
        return {
            "next_question": f"Tell me about your experience relevant to the {role} position at {company}.",
            "question_type": "behavioral",
        }

    # ── Build the conversation messages ──────────────────────────────────
    system_prompt = (
        f"You are a senior technical interviewer at {company}. "
        f"You are conducting a real-time interview for the role: {role}. "
        f"The current interview difficulty level is: {difficulty.upper()}. "
        f"Your interview style is professional but encouraging. "
        f"Ask one question at a time. Alternate between technical, behavioral, "
        f"and coding questions naturally. "
        f"Generate a {difficulty} difficulty interview question. "
        f"After the candidate answers, acknowledge their response briefly "
        f"(1 sentence) and then ask a deeper follow-up or move to the next topic. "
        f"Keep questions concise and specific to the role. "
        f"At the end of your response, on a new line, add exactly one of these tags: "
        f"[TYPE:technical] or [TYPE:behavioral] or [TYPE:coding] "
        f"to classify the question you just asked."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Replay the conversation history
    for entry in question_history:
        if entry.get("role") == "ai":
            messages.append({"role": "assistant", "content": entry["content"]})
        elif entry.get("role") == "user":
            messages.append({"role": "user", "content": entry["content"]})

    # If it's the very first question (no history, no answer)
    if not question_history and not user_answer:
        messages.append({
            "role": "user",
            "content": (
                f"Please begin the interview at {difficulty} difficulty. Greet me briefly and ask your first question."
            ),
        })
    elif user_answer:
        messages.append({"role": "user", "content": user_answer})

    # ── Call Gemini ──────────────────────────────────────────────────────
    try:
        resp = openai_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=messages,
            max_tokens=400,
            temperature=0.75,
        )
        raw = resp.choices[0].message.content.strip()

        # Parse the [TYPE:...] tag
        question_type = "technical"  # default
        clean_text = raw
        for tag in ["[TYPE:technical]", "[TYPE:behavioral]", "[TYPE:coding]"]:
            if tag in raw:
                question_type = tag.replace("[TYPE:", "").replace("]", "")
                clean_text = raw.replace(tag, "").strip()
                break

        return {
            "next_question": clean_text,
            "question_type": question_type,
        }

    except Exception as exc:
        logger.error("InterviewAgent: Gemini call failed — %s", exc)
        # Graceful fallback
        if not question_history:
            return {
                "next_question": (
                    f"Welcome! Let's begin your interview for {role} at {company}. "
                    f"Can you walk me through your most relevant project experience?"
                ),
                "question_type": "behavioral",
            }
        return {
            "next_question": (
                "That's a good answer. Can you elaborate on the technical challenges "
                "you faced and how you overcame them?"
            ),
            "question_type": "technical",
        }

def evaluate_answer(
    company: str,
    role: str,
    question: str,
    user_answer: str,
) -> dict:
    """
    Evaluate an interview answer.

    Parameters
    ----------
    company : str
    role : str
    question : str
    user_answer : str

    Returns
    -------
    dict
        {
            "technical_score": int,
            "clarity_score": int,
            "communication_score": int,
            "feedback": str
        }
    """
    if not openai_client:
        return {
            "technical_score": 7,
            "clarity_score": 7,
            "communication_score": 7,
            "feedback": "Good answer, but could be more specific. (API key missing)"
        }

    system_prompt = (
        f"You are a mock interview evaluator for {company} assessing a candidate for the {role} role. "
        "Evaluate the candidate's answer to the given question. "
        "Score the answer from 1 to 10 for:\n"
        "- technical_score: Technical accuracy and depth.\n"
        "- clarity_score: Clarity and structure of the explanation.\n"
        "- communication_score: Overall communication skills and conciseness.\n"
        "Provide a short, constructive piece of 'feedback' (1-2 sentences) on how to improve.\n\n"
        "Return EXACTLY a JSON object with this shape:\n"
        "{\n"
        '  "technical_score": 8,\n'
        '  "clarity_score": 7,\n'
        '  "communication_score": 6,\n'
        '  "feedback": "..."\n'
        "}\n"
        "Do not include markdown blocks or any other text outside the JSON."
    )

    user_prompt = (
        f"Question: {question}\n\n"
        f"Candidate's Answer: {user_answer}"
    )

    try:
        resp = openai_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=300,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        
        import re
        import json
        
        # Robustly extract JSON block
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            raw_json = json_match.group(0)
        else:
            raw_json = raw

        data = json.loads(raw_json)
        return {
            "technical_score": int(data.get("technical_score", 0)),
            "clarity_score": int(data.get("clarity_score", 0)),
            "communication_score": int(data.get("communication_score", 0)),
            "feedback": str(data.get("feedback", "No feedback provided.")),
        }

    except Exception as exc:
        logger.error("InterviewAgent: Evaluation failed — %s", exc)
        return {
            "technical_score": 5,
            "clarity_score": 5,
            "communication_score": 5,
            "feedback": "Failed to evaluate answer. Please try again."
        }

