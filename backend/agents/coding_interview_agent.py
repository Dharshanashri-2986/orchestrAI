"""
coding_interview_agent.py — AI Coding Challenge Agent
OrchestrAI Autonomous Multi-Agent System
"""

import logging
import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger("OrchestrAI.CodingInterviewAgent")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
openai_client = (
    OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL, max_retries=0)
    if GEMINI_API_KEY
    else None
)

def generate_coding_problem(role: str) -> dict:
    """
    Generate a Python coding problem for a interview.
    """
    if not openai_client:
        return {
            "problem": "Write a Python function to find the maximum element in a list.",
            "input_example": "[1, 5, 3, 9, 2]",
            "expected_output": "9"
        }

    system_prompt = (
        f"You are a technical interviewer for a {role} role. "
        "Generate a relevant Python coding problem. "
        "The problem should be challenging but solvable within 15-20 minutes. "
        "Return EXACTLY a JSON object with: \n"
        "- problem: Detailed description of the task.\n"
        "- input_example: String representation of input.\n"
        "- expected_output: String representation of expected result."
    )

    try:
        resp = openai_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[{"role": "system", "content": system_prompt}],
            max_tokens=500,
            temperature=0.7
        )
        raw = resp.choices[0].message.content.strip()
        
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return data
        return json.loads(raw)
    except Exception as e:
        logger.error("Failed to generate coding problem: %s", e)
        return {
            "problem": f"Implement a basic data structure or algorithm relevant to {role}.",
            "input_example": "N/A",
            "expected_output": "N/A"
        }

def evaluate_code(problem: str, code: str) -> dict:
    """
    Evaluate the candidate's code submission.
    """
    if not openai_client:
        return {
            "correctness": "Unknown",
            "runtime_complexity": "N/A",
            "code_quality": "N/A",
            "suggestion": "API key missing. Could not evaluate."
        }

    system_prompt = (
        "You are a senior code reviewer. Evaluate this Python code submission for an interview problem.\n"
        f"Problem: {problem}\n\n"
        "Assess for:\n"
        "1. Correctness: Does it solve the problem?\n"
        "2. Complexity: What is the Time and Space complexity?\n"
        "3. Quality: Is it clean, efficient, and Pythonic?\n"
        "Return EXACTLY a JSON object with: correctness (Pass/Fail/Partial), runtime_complexity, code_quality (1-10), suggestion."
    )

    try:
        resp = openai_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Code Submission:\n{code}"}
            ],
            max_tokens=400,
            temperature=0.2
        )
        raw = resp.choices[0].message.content.strip()
        
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return json.loads(raw)
    except Exception as e:
        logger.error("Failed to evaluate code: %s", e)
        return {
            "correctness": "Error",
            "runtime_complexity": "N/A",
            "code_quality": "N/A",
            "suggestion": f"Evaluation error: {str(e)}"
        }
