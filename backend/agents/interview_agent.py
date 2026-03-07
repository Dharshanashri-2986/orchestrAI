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
) -> dict:
    """
    Generate the next interview question.

    Parameters
    ----------
    company : str          – Target company name (e.g. "Tinder")
    role : str             – Target role (e.g. "Machine Learning Engineer Intern")
    question_history : list – Previous Q&A pairs: [{"role":"ai","content":"..."}, ...]
    user_answer : str|None – The candidate's latest answer (if any)

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
        f"Your interview style is professional but encouraging. "
        f"Ask one question at a time. Alternate between technical, behavioral, "
        f"and coding questions naturally. "
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
                "Please begin the interview. Greet me briefly and ask your first question."
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
