"""
interview_coach_agent.py — AI Interview Coach
OrchestrAI Autonomous Multi-Agent System

PURPOSE:
  For each internship listing, generate a tailored mock interview simulation
  page containing technical, behavioral, coding, and case-study questions.

FLOW:
  1. Read jobs from database/jobs.yaml
  2. Read user profile from database/users.yaml
  3. Use LLM to generate 8+ role-specific questions per job
  4. Build a rich HTML interview practice page
  5. Save HTML to DATA_DIR/frontend/interview/{slug}.html
  6. Serve via Render static mount at /interview/{slug}.html
  7. Save index to database/interview_sessions.yaml
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

from backend.github_yaml_db import (
    read_yaml_from_github,
    write_yaml_to_github,
    append_log_entry,
    _get_raw_file,
    _put_raw_file,
)

load_dotenv()
logger = logging.getLogger("OrchestrAI.InterviewCoachAgent")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
openai_client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL, max_retries=0) if GEMINI_API_KEY else None

JOBS_FILE             = "database/jobs.yaml"
USERS_FILE            = "database/users.yaml"
INTERVIEW_INDEX_FILE  = "database/interview_sessions.yaml"

DEFAULT_USER_NAME   = os.getenv("USER_NAME", "Applicant")
DEFAULT_SKILLS      = ["Python", "Machine Learning", "SQL", "Data Analysis"]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:40]


def _is_data_role(role: str) -> bool:
    keywords = ["data", "analyst", "analytics", "business analyst", "bi ", "sql"]
    return any(k in role.lower() for k in keywords)


# ─────────────────────────────────────────────────────────────────────────────
# LLM Question Generator
# ─────────────────────────────────────────────────────────────────────────────

def _generate_questions(company: str, role: str, skills: list[str], user_skills: list[str]) -> dict:
    """
    Call Gemini to generate 4 categories of interview questions.
    Returns dict with keys: technical, behavioral, coding, case
    """
    skills_str = ", ".join(skills[:8]) if skills else "Python, ML, SQL"
    user_skills_str = ", ".join(user_skills[:6]) if user_skills else "Python"
    include_case = _is_data_role(role)

    prompt = f"""You are a senior interviewer at {company}.
Generate realistic interview questions for the role: {role}
Required skills: {skills_str}
Candidate has: {user_skills_str}

Return EXACTLY this format (no extra text):
TECHNICAL:
1. [question]
2. [question]
3. [question]

BEHAVIORAL:
1. [question]
2. [question]
3. [question]

CODING:
1. [coding problem title] — [brief description]
2. [coding problem title] — [brief description]

{"CASE:" if include_case else ""}
{"1. [data/business case scenario]" if include_case else ""}
{"2. [data/business case scenario]" if include_case else ""}
"""

    fallback = {
        "technical": [
            f"Explain your experience with {skills[0] if skills else 'Python'} and how you've used it in projects.",
            f"How would you approach building a {role.replace(' Intern', '')} pipeline from scratch?",
            f"Describe a challenging technical problem you solved using {skills[1] if len(skills) > 1 else 'Machine Learning'}.",
        ],
        "behavioral": [
            "Tell me about a time you had to learn a new technology quickly.",
            "Describe a situation where you had to work under tight deadlines.",
            "Give an example of a project where you collaborated with a team.",
        ],
        "coding": [
            f"Implement a function to {skills[0].lower() if skills else 'clean'} a dataset and handle missing values",
            "Write an efficient algorithm for binary search and analyze its time complexity",
        ],
        "case": [
            f"Given a dataset of {company}'s user behavior, how would you identify churn patterns?",
            "A/B test results show 10% lift in metric X but 5% drop in metric Y — what's your recommendation?",
        ] if include_case else [],
    }

    if not openai_client:
        return fallback

    try:
        resp = openai_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.7,
        )
        raw = resp.choices[0].message.content.strip()

        def _extract_section(label: str, text: str) -> list[str]:
            pattern = rf"{label}:?\s*\n(.*?)(?=\n[A-Z]+:|\Z)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if not match:
                return []
            lines = match.group(1).strip().split("\n")
            result = []
            for line in lines:
                line = re.sub(r"^\d+\.\s*", "", line).strip()
                if line and len(line) > 5:
                    result.append(line)
            return result[:3]

        return {
            "technical": _extract_section("TECHNICAL", raw) or fallback["technical"],
            "behavioral": _extract_section("BEHAVIORAL", raw) or fallback["behavioral"],
            "coding":    _extract_section("CODING", raw) or fallback["coding"],
            "case":      _extract_section("CASE", raw) if include_case else [],
        }

    except Exception as exc:
        logger.warning("InterviewCoachAgent: LLM failed for %s — %s. Using fallback.", role, exc)
        return fallback


# ─────────────────────────────────────────────────────────────────────────────
# HTML Page Builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_interview_html(
    company: str,
    role: str,
    skills: list[str],
    questions: dict,
    user_name: str,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%B %d, %Y")
    skill_tags = "".join(
        f'<span class="skill-tag">{s}</span>' for s in skills[:8]
    )

    def _q_items(qs: list[str], icon: str) -> str:
        if not qs:
            return '<div class="empty-state">No questions generated.</div>'
        html = ""
        for i, q in enumerate(qs):
            html += f"""
            <div class="q-card">
              <div class="q-header">
                <span class="q-icon">{icon}</span>
                <span class="q-title">Question {i+1}</span>
              </div>
              <p class="q-text">{q}</p>
              <textarea class="q-textarea" placeholder="Type your answer here or practice answering out loud..."></textarea>
              <div class="q-actions">
                <button class="btn-outline" onclick="toggleHint(this)">💡 Show Hint</button>
                <div class="hint-box" style="display:none;">Focus on your personal experience and use the STAR method.</div>
              </div>
            </div>
            """
        return html

    def _code_items(qs: list[str]) -> str:
        if not qs:
            return "<div class='empty-state'>No coding challenges generated.</div>"
        html = ""
        for i, q in enumerate(qs):
            html += f"""
            <div class="code-card">
              <div class="code-header">
                <div class="mac-dots"><span></span><span></span><span></span></div>
                <span class="code-title">Problem {i+1}</span>
              </div>
              <div class="code-body">
                <p class="code-prompt">{q}</p>
                <div class="editor-wrapper">
                  <div class="line-numbers">1<br>2<br>3<br>4<br>5</div>
                  <textarea class="code-textarea" placeholder="# Write your python solution here..."></textarea>
                </div>
              </div>
              <div class="code-footer">
                <button class="btn-primary" onclick="runSimulation(this)">▶ Run Code (Simulated)</button>
              </div>
            </div>
            """
        return html

    case_section = ""
    if questions.get("case"):
        case_items = "".join(
            f"""
            <div class="case-card">
              <div class="case-icon">📊</div>
              <div class="case-content">
                <h4 style="color:#fcd34d">Case {i+1}</h4>
                <p>{q}</p>
                <textarea class="q-textarea" placeholder="Outline your analytical approach..."></textarea>
              </div>
            </div>
            """ for i, q in enumerate(questions["case"])
        )
        case_section = f"""
        <div class="section-container" id="case-study">
          <h3 class="section-title"><span>📊</span> Case Study Questions</h3>
          <p class="section-desc">Analytical and data-driven scenario questions.</p>
          <div class="case-grid">{case_items}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Mock Interview — {role} at {company}</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&family=Inter:wght@400;500;600&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet"/>
<style>
  :root {{
    --bg-dark: #09090b;
    --bg-card: rgba(255, 255, 255, 0.03);
    --border-color: rgba(255, 255, 255, 0.08);
    --primary: #7c3aed;
    --primary-hover: #6d28d9;
    --secondary: #06b6d4;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --error: #ef4444;
    --success: #10b981;
    --gradient-bg: linear-gradient(135deg, rgba(124,58,237,0.1), rgba(6,182,212,0.1));
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Inter', sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-main);
    background-image: 
      radial-gradient(circle at 15% 50%, rgba(124, 58, 237, 0.08), transparent 25%),
      radial-gradient(circle at 85% 30%, rgba(6, 182, 212, 0.08), transparent 25%);
    background-attachment: fixed;
    line-height: 1.6;
    padding-bottom: 60px;
  }}
  /* Typography */
  h1, h2, h3, h4 {{ font-family: 'Outfit', sans-serif; }}
  
  /* Navbar / Hero */
  .hero {{
    padding: 60px 20px; text-align: center; border-bottom: 1px solid var(--border-color);
    background: rgba(0,0,0,0.2); backdrop-filter: blur(10px); position: relative; overflow: hidden;
  }}
  .hero::before {{
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(124,58,237,0.1) 0%, transparent 50%); pointer-events: none;
  }}
  .hero h1 {{
    font-size: 2.5rem; font-weight: 800; margin-bottom: 10px;
    background: linear-gradient(to right, #fff, #a5b4fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .hero h2 {{ font-size: 1.2rem; color: var(--text-muted); font-weight: 400; margin-bottom: 20px; }}
  .hero-badges {{ display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; }}
  .badge {{
    background: rgba(255,255,255,0.05); border: 1px solid var(--border-color);
    padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 500;
    display: flex; align-items: center; gap: 6px;
  }}
  
  /* Main Container */
  .container {{ max-width: 900px; margin: 40px auto; padding: 0 20px; }}
  
  /* Skill Tags */
  .skill-info {{
    background: var(--bg-card); border: 1px solid var(--border-color);
    border-radius: 16px; padding: 24px; margin-bottom: 30px; text-align: center;
  }}
  .skill-info h3 {{ font-size: 1.1rem; margin-bottom: 12px; color: #fff; }}
  .skill-tags {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }}
  .skill-tag {{
    background: rgba(6,182,212,0.1); border: 1px solid rgba(6,182,212,0.3);
    color: var(--secondary); padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;
  }}

  /* Sticky Timer */
  .timer-wrapper {{
    position: sticky; top: 20px; z-index: 100;
    background: rgba(9, 9, 11, 0.8); backdrop-filter: blur(12px);
    border: 1px solid rgba(124, 58, 237, 0.4); border-radius: 16px;
    padding: 16px 24px; margin-bottom: 40px;
    display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5), 0 0 20px rgba(124,58,237,0.15);
  }}
  .timer-display {{ display: flex; flex-direction: column; }}
  .timer-label {{ font-size: 0.75rem; color: var(--primary); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
  .timer-time {{ font-family: 'Fira Code', monospace; font-size: 2rem; font-weight: 700; color: #fff; }}
  .timer-controls {{ display: flex; gap: 10px; }}
  
  /* Buttons */
  button {{ font-family: inherit; cursor: pointer; transition: all 0.2s; outline: none; }}
  .btn-primary {{
    background: var(--primary); color: #fff; border: none; padding: 10px 20px;
    border-radius: 8px; font-weight: 600; font-size: 0.9rem;
    box-shadow: 0 4px 15px rgba(124,58,237,0.3);
  }}
  .btn-primary:disabled {{ opacity: 0.6; cursor: not-allowed; }}
  .btn-primary:not(:disabled):hover {{ background: var(--primary-hover); transform: translateY(-1px); box-shadow: 0 6px 20px rgba(124,58,237,0.4); }}
  .btn-secondary {{
    background: rgba(255,255,255,0.05); color: #fff; border: 1px solid var(--border-color);
    padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 0.9rem;
  }}
  .btn-secondary:hover {{ background: rgba(255,255,255,0.1); }}
  .btn-outline {{
    background: transparent; color: var(--text-muted); border: 1px solid rgba(255,255,255,0.2);
    padding: 6px 12px; border-radius: 6px; font-size: 0.8rem;
  }}
  .btn-outline:hover {{ border-color: var(--text-main); color: var(--text-main); }}

  /* Evaluation Cards */
  .eval-card {{
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 12px;
    padding: 16px;
    align-self: flex-end;
    max-width: 85%;
    animation: bubbleIn 0.3s ease;
  }}
  .eval-score {{
    display: flex; flex-direction: column; align-items: center;
    background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 8px;
    min-width: 70px;
  }}
  .eval-score span {{ font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; }}
  .eval-score strong {{ font-size: 1.1rem; color: #10b981; }}

  /* Sections */
  .section-container {{ margin-bottom: 50px; }}
  .section-title {{
    font-size: 1.4rem; color: #fff; margin-bottom: 8px; display: flex; align-items: center; gap: 10px;
  }}
  .section-desc {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px; }}

  /* Q Cards */
  .q-card {{
    background: var(--bg-card); border: 1px solid var(--border-color);
    border-radius: 12px; padding: 20px; margin-bottom: 16px;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .q-card:focus-within {{ border-color: rgba(124,58,237,0.3); box-shadow: 0 4px 20px rgba(0,0,0,0.2); }}
  .q-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }}
  .q-icon {{ background: rgba(124,58,237,0.2); color: #a5b4fc; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 6px; font-size: 0.8rem; }}
  .q-title {{ font-weight: 600; font-size: 0.9rem; color: var(--text-muted); }}
  .q-text {{ font-size: 1.05rem; color: #fff; margin-bottom: 16px; line-height: 1.5; font-weight: 500; }}
  
  /* Textareas */
  .q-textarea {{
    width: 100%; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color);
    color: #fff; border-radius: 8px; padding: 12px; font-family: inherit; font-size: 0.95rem;
    min-height: 80px; resize: vertical; margin-bottom: 12px; transition: border-color 0.2s;
  }}
  .q-textarea:focus {{ outline: none; border-color: var(--primary); }}
  
  .hint-box {{
    margin-top: 10px; padding: 12px; background: rgba(6,182,212,0.05); border-left: 3px solid var(--secondary);
    border-radius: 4px; font-size: 0.85rem; color: #cbd5e1;
  }}

  /* Code IDE */
  .code-card {{
    background: #11111b; border: 1px solid #313244; border-radius: 12px;
    overflow: hidden; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
  }}
  .code-header {{
    background: #181825; padding: 10px 16px; display: flex; align-items: center; border-bottom: 1px solid #313244;
  }}
  .mac-dots {{ display: flex; gap: 6px; margin-right: 16px; }}
  .mac-dots span {{ width: 10px; height: 10px; border-radius: 50%; opacity: 0.8; }}
  .mac-dots span:nth-child(1) {{ background: #f38ba8; }}
  .mac-dots span:nth-child(2) {{ background: #f9e2af; }}
  .mac-dots span:nth-child(3) {{ background: #a6e3a1; }}
  .code-title {{ font-family: 'Fira Code', monospace; font-size: 0.8rem; color: #a6adc8; }}
  
  .code-body {{ padding: 20px; }}
  .code-prompt {{ color: #cdd6f4; font-size: 0.95rem; margin-bottom: 16px; line-height: 1.5; font-weight: 500; }}
  
  .editor-wrapper {{
    display: flex; background: #1e1e2e; border-radius: 8px; border: 1px solid #313244; overflow: hidden;
  }}
  .line-numbers {{
    padding: 16px 12px; background: #181825; color: #585b70; font-family: 'Fira Code', monospace;
    font-size: 0.9rem; text-align: right; user-select: none; line-height: 1.6;
  }}
  .code-textarea {{
    flex: 1; background: transparent; border: none; color: #89b4fa; padding: 16px;
    font-family: 'Fira Code', monospace; font-size: 0.9rem; resize: vertical; min-height: 120px;
    line-height: 1.6;
  }}
  .code-textarea:focus {{ outline: none; }}
  .code-footer {{
    background: #181825; padding: 12px 20px; display: flex; justify-content: flex-end; border-top: 1px solid #313244;
  }}

  /* Case Grid */
  .case-grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}
  .case-card {{
    background: linear-gradient(135deg, rgba(245,158,11,0.05), transparent);
    border: 1px solid rgba(245,158,11,0.2); border-radius: 12px; padding: 20px;
    display: flex; gap: 16px; transition: transform 0.2s;
  }}
  .case-card:focus-within {{ border-color: rgba(245,158,11,0.4); }}
  .case-icon {{ font-size: 1.5rem; }}
  .case-content {{ flex: 1; }}
  .case-content p {{ color: #fff; font-size: 0.95rem; margin-bottom: 12px; line-height: 1.5; }}

  /* Feedback Form */
  .feedback-form {{
    background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px;
    padding: 30px; position: relative; overflow: hidden; margin-top: 60px;
  }}
  .feedback-form::before {{
    content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px;
    background: var(--gradient-bg);
  }}
  .feedback-form h3 {{ font-size: 1.4rem; color: #fff; margin-bottom: 8px; }}
  .form-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 24px; }}
  .form-group {{ margin-bottom: 20px; }}
  .form-group label {{ display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }}
  
  .form-input {{
    width: 100%; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color);
    color: #fff; border-radius: 8px; padding: 12px 16px; font-size: 0.95rem;
    transition: all 0.2s; font-family: inherit;
  }}
  .form-input:read-only {{ opacity: 0.7; cursor: not-allowed; }}
  .form-input:focus:not(:read-only) {{ outline: none; border-color: var(--primary); background: rgba(0,0,0,0.5); }}
  
  .slider-wrapper {{ margin-top: 8px; }}
  .slider-labels {{ display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-top: 8px; }}
  input[type=range] {{
    width: 100%; appearance: none; height: 6px; border-radius: 3px; background: #334155; outline: none;
  }}
  input[type=range]::-webkit-slider-thumb {{
    appearance: none; width: 18px; height: 18px; border-radius: 50%; background: #fff; cursor: pointer;
    box-shadow: 0 0 10px rgba(0,0,0,0.5); border: 2px solid var(--primary);
  }}
  #fb_difficulty::-webkit-slider-thumb {{ border-color: var(--secondary); }}
  
  .submit-area {{ display: flex; flex-direction: column; align-items: flex-start; gap: 16px; margin-top: 24px; border-top: 1px solid var(--border-color); padding-top: 24px; }}
  
  /* Toast Notification */
  .toast {{
    position: fixed; bottom: 30px; right: 30px; background: #18182b; border-left: 4px solid var(--primary);
    color: #fff; padding: 16px 24px; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    display: flex; align-items: center; gap: 12px; transform: translateX(120%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 1000;
  }}
  .toast.show {{ transform: translateX(0); }}
  .toast-icon {{ font-size: 1.2rem; }}

  @media(max-width: 768px) {{
    .form-grid {{ grid-template-columns: 1fr; }}
    .timer-wrapper {{ flex-direction: column; gap: 16px; text-align: center; }}
  }}

  /* === AI INTERVIEW CHAT === */
  .ai-chat-section {{
    background: var(--card);
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 16px;
    padding: 0;
    margin-bottom: 40px;
    overflow: hidden;
    box-shadow: 0 10px 40px rgba(124,58,237,0.1);
  }}
  .ai-chat-header {{
    background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(59,130,246,0.15));
    padding: 20px 24px;
    border-bottom: 1px solid rgba(124,58,237,0.2);
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .ai-chat-header h3 {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.2rem;
    color: #c084fc;
    margin: 0;
  }}
  .ai-chat-header .live-dot {{
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #10b981;
    animation: livePulse 1.5s infinite;
    margin-left: auto;
  }}
  .ai-chat-header .live-label {{
    font-size: 0.75rem;
    color: #10b981;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  @keyframes livePulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.5; transform: scale(0.8); }}
  }}
  .chat-messages {{
    padding: 24px;
    max-height: 500px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-height: 120px;
  }}
  .chat-messages::-webkit-scrollbar {{ width: 6px; }}
  .chat-messages::-webkit-scrollbar-thumb {{ background: rgba(124,58,237,0.3); border-radius: 3px; }}
  .chat-bubble {{
    max-width: 85%;
    padding: 14px 18px;
    border-radius: 16px;
    font-size: 0.95rem;
    line-height: 1.6;
    animation: bubbleIn 0.3s ease;
  }}
  @keyframes bubbleIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  .chat-bubble.ai {{
    background: rgba(124,58,237,0.12);
    border: 1px solid rgba(124,58,237,0.25);
    color: var(--text-primary);
    align-self: flex-start;
    border-bottom-left-radius: 4px;
  }}
  .chat-bubble.user {{
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.25);
    color: var(--text-primary);
    align-self: flex-end;
    border-bottom-right-radius: 4px;
  }}
  .chat-bubble .bubble-label {{
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
    display: block;
  }}
  .chat-bubble.ai .bubble-label {{ color: #a78bfa; }}
  .chat-bubble.user .bubble-label {{ color: #60a5fa; }}
  .chat-type-badge {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 2px 8px;
    border-radius: 4px;
    margin-top: 8px;
  }}
  .chat-type-badge.technical {{ background: rgba(239,68,68,0.15); color: #f87171; }}
  .chat-type-badge.behavioral {{ background: rgba(16,185,129,0.15); color: #34d399; }}
  .chat-type-badge.coding {{ background: rgba(245,158,11,0.15); color: #fbbf24; }}
  .chat-input-area {{
    display: flex;
    gap: 12px;
    padding: 20px 24px;
    border-top: 1px solid rgba(255,255,255,0.06);
    background: rgba(0,0,0,0.15);
  }}
  .chat-input-area textarea {{
    flex: 1;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 12px 16px;
    color: #fff;
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    resize: none;
    outline: none;
    min-height: 48px;
    max-height: 120px;
  }}
  .chat-input-area textarea:focus {{
    border-color: rgba(124,58,237,0.5);
    box-shadow: 0 0 0 3px rgba(124,58,237,0.1);
  }}
  .chat-send-btn {{
    padding: 12px 24px;
    border-radius: 12px;
    border: none;
    background: linear-gradient(135deg, #7c3aed, #3b82f6);
    color: #fff;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s;
  }}
  .chat-send-btn:hover {{ transform: translateY(-1px); box-shadow: 0 6px 20px rgba(124,58,237,0.4); }}
  .chat-send-btn:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
  .chat-empty {{
    text-align: center;
    color: var(--text-muted);
    padding: 30px;
    font-size: 0.9rem;
  }}
  .typing-indicator {{
    display: flex; gap: 4px; padding: 14px 18px; align-self: flex-start;
  }}
  .typing-indicator span {{
    width: 8px; height: 8px; border-radius: 50%; background: #a78bfa;
    animation: typingBounce 1.4s infinite;
  }}
  .typing-indicator span:nth-child(2) {{ animation-delay: 0.2s; }}
  .typing-indicator span:nth-child(3) {{ animation-delay: 0.4s; }}
  @keyframes typingBounce {{
    0%, 60%, 100% {{ transform: translateY(0); opacity: 0.4; }}
    30% {{ transform: translateY(-8px); opacity: 1; }}
  }}
</style>
</head>
<body>

<div class="hero">
  <h1>Interactive Mock Interview</h1>
  <h2>{role} &mdash; <strong>{company}</strong></h2>
  <div class="hero-badges">
    <span class="badge">👤 {user_name}</span>
    <span class="badge">📅 {ts}</span>
    <span class="badge">⏱️ AI Guided</span>
  </div>
</div>

<div class="container">

  <div class="skill-info">
    <h3>🎯 Target Competencies</h3>
    <div class="skill-tags">{skill_tags or '<span class="skill-tag">General Software Engineering</span>'}</div>
  </div>

  <div class="timer-wrapper">
    <div class="timer-display">
      <span class="timer-label">Session Timer</span>
      <span class="timer-time" id="timer">30:00</span>
    </div>
    <div class="timer-controls">
      <button class="btn-primary" onclick="startTimer()" id="btnStart">▶ Start Interview</button>
      <button class="btn-secondary" onclick="resetTimer()">↺ Reset</button>
    </div>
  </div>

  <div class="section-container" id="technical">
    <h3 class="section-title"><span>⚙️</span> Technical Deep Dive</h3>
    <p class="section-desc">Assess your domain knowledge and fundamental concepts. Type your answers or practice out loud.</p>
    {_q_items(questions.get('technical', []), '⚙️')}
  </div>

  <div class="section-container" id="coding">
    <h3 class="section-title"><span>💻</span> Coding Challenges</h3>
    <p class="section-desc">Write robust, optimal code and explain your time/space complexities.</p>
    {_code_items(questions.get('coding', []))}
  </div>

  <div class="section-container" id="behavioral">
    <h3 class="section-title"><span>🧠</span> Behavioral & Situational</h3>
    <p class="section-desc">Use the STAR method (Situation, Task, Action, Result) to frame your answers.</p>
    {_q_items(questions.get('behavioral', []), '🧠')}
  </div>

  {case_section}

  <!-- ═══ AI INTERVIEW CHAT ═══ -->
  <div class="ai-chat-section" id="aiChatSection">
    <div class="ai-chat-header">
      <span style="font-size:1.4rem">🤖</span>
      <h3>AI Interview Chat</h3>
      <span class="live-dot"></span>
      <span class="live-label">Live</span>
    </div>
    <div class="chat-messages" id="chatMessages">
      <div class="chat-empty" id="chatEmpty">
        Click <strong>"Start AI Interview"</strong> below to begin a real-time conversational interview powered by AI.
      </div>
    </div>
    <div class="chat-input-area">
      <textarea id="chatInput" placeholder="Type your answer here..." rows="2" disabled></textarea>
      <button class="chat-send-btn" id="chatSendBtn" onclick="sendChatAnswer()" disabled>Submit Answer</button>
    </div>
    <div style="padding: 12px 24px; text-align:center;">
      <button class="btn-primary" id="chatStartBtn" onclick="startAIInterview()" style="padding:12px 32px; border-radius:12px; font-weight:700">
        🚀 Start AI Interview
      </button>
    </div>
  </div>

  <div class="feedback-form">
    <h3 style="color:#c084fc">📝 Interview Debrief</h3>
    <p class="section-desc" style="margin-bottom:0">Submit your performance data. The agent will analyze your gaps and update your career learning plan immediately.</p>
    
    <div class="form-grid">
      <div class="form-group" style="margin:0">
        <label>Company</label>
        <input class="form-input" id="fb_company" value="{company}" readonly />
      </div>
      <div class="form-group" style="margin:0">
        <label>Role</label>
        <input class="form-input" id="fb_role" value="{role}" readonly />
      </div>
    </div>

    <div class="form-group" style="margin-top:20px">
      <label>Questions You Struggled With <span style="text-transform:none;font-weight:400;color:var(--text-muted)">(one per line)</span></label>
      <textarea class="form-input" id="fb_questions" rows="4" placeholder="e.g. Explaining backpropagation mathematically..."></textarea>
    </div>

    <div class="form-grid">
      <div class="form-group" style="margin:0">
        <label>Your Confidence: <span id="conf_val" style="color:#fff;font-size:1rem">6</span>/10</label>
        <div class="slider-wrapper">
          <input id="fb_confidence" type="range" min="1" max="10" value="6" oninput="document.getElementById('conf_val').textContent=this.value"/>
          <div class="slider-labels"><span>Shaky</span><span>Masterful</span></div>
        </div>
      </div>
      <div class="form-group" style="margin:0">
        <label>Interview Difficulty: <span id="diff_val" style="color:#fff;font-size:1rem">7</span>/10</label>
        <div class="slider-wrapper">
          <input id="fb_difficulty" type="range" min="1" max="10" value="7" oninput="document.getElementById('diff_val').textContent=this.value"/>
          <div class="slider-labels"><span>A Breeze</span><span>Brutal</span></div>
        </div>
      </div>
    </div>

    <div class="submit-area">
      <button class="btn-primary" style="padding:14px 28px; font-size:1rem; width: 100%; border-radius: 12px; font-weight: 800" onclick="submitFeedback()" id="btnSubmit">
        📤 Log Interview & Update Analytics
      </button>
    </div>
  </div>

  <div style="text-align:center; padding-top: 40px; color: var(--text-muted); font-size: 0.8rem">
    OrchestrAI Autonomous Carrier Intelligence System &copy; {datetime.now().year}
  </div>

</div>

<!-- Toast -->
<div class="toast" id="toast">
  <span class="toast-icon" id="toast-icon">✅</span>
  <div class="toast-content" style="text-align: left">
    <h4 style="font-size:0.95rem;margin-bottom:2px;color:#fff;font-weight:600" id="toast-title">Success</h4>
    <p style="font-size:0.85rem;color:var(--text-muted)" id="toast-msg">Feedback logged securely.</p>
  </div>
</div>

<script>
// ----- Interactions -----
function toggleHint(btn) {{
  const hint = btn.nextElementSibling;
  if(hint.style.display === 'none' || hint.style.display === '') {{
    hint.style.display = 'block';
    btn.textContent = 'Hide Hint';
    btn.style.color = '#fff';
    btn.style.borderColor = '#fff';
  }} else {{
    hint.style.display = 'none';
    btn.textContent = '💡 Show Hint';
    btn.style.color = 'var(--text-muted)';
    btn.style.borderColor = 'rgba(255,255,255,0.2)';
  }}
}}

function runSimulation(btn) {{
  const orig = btn.innerHTML;
  btn.innerHTML = '⏳ Compiling & Running...';
  btn.style.opacity = '0.8';
  btn.disabled = true;
  setTimeout(() => {{
    btn.innerHTML = '✅ All 14 Test Cases Passed!';
    btn.style.background = 'var(--success)';
    btn.style.opacity = '1';
    btn.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.4)';
    setTimeout(() => {{
      btn.innerHTML = orig;
      btn.style.background = 'var(--primary)';
      btn.style.boxShadow = '0 4px 15px rgba(124,58,237,0.3)';
      btn.disabled = false;
    }}, 4000);
  }}, 1500);
}}

function showToast(title, msg, isError=false) {{
  const toast = document.getElementById('toast');
  document.getElementById('toast-title').textContent = title;
  document.getElementById('toast-msg').textContent = msg;
  toast.style.borderLeftColor = isError ? 'var(--error)' : 'var(--success)';
  document.getElementById('toast-icon').textContent = isError ? '❌' : '✅';
  
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 4000);
}}

// ----- Timer -----
let timerInterval = null;
let seconds = 1800; // 30 min
function startTimer() {{
  if (timerInterval) return;
  document.getElementById('btnStart').textContent = '⏸ Pause Interview';
  document.getElementById('btnStart').onclick = pauseTimer;
  document.getElementById('btnStart').style.background = 'var(--secondary)';
  
  timerInterval = setInterval(() => {{
    if (seconds <= 0) {{ 
        clearInterval(timerInterval); 
        showToast('Time is up!', 'Interview session automatically concluded.'); 
        timerInterval = null;
        return; 
    }}
    seconds--;
    const m = String(Math.floor(seconds/60)).padStart(2,'0');
    const s = String(seconds%60).padStart(2,'0');
    document.getElementById('timer').textContent = m+':'+s;
  }}, 1000);
}}
function pauseTimer() {{
  clearInterval(timerInterval);
  timerInterval = null;
  document.getElementById('btnStart').textContent = '▶ Resume Interview';
  document.getElementById('btnStart').style.background = 'var(--primary)';
  document.getElementById('btnStart').onclick = startTimer;
}}
function resetTimer() {{
  clearInterval(timerInterval);
  timerInterval = null;
  seconds = 1800;
  document.getElementById('timer').textContent = '30:00';
  document.getElementById('btnStart').textContent = '▶ Start Interview';
  document.getElementById('btnStart').style.background = 'var(--primary)';
  document.getElementById('btnStart').onclick = startTimer;
}}

// ----- API Submission -----
async function submitFeedback() {{
  const company = document.getElementById('fb_company').value;
  const role = document.getElementById('fb_role').value;
  const rawQ = document.getElementById('fb_questions').value.trim();
  const confidence = parseInt(document.getElementById('fb_confidence').value);
  const difficulty = parseInt(document.getElementById('fb_difficulty').value);
  const btn = document.getElementById('btnSubmit');

  if (!rawQ) {{
    showToast('Missing Insight', 'Please add the questions you struggled with to update your metrics.', true);
    document.getElementById('fb_questions').focus();
    return;
  }}

  const questions_faced = rawQ.split('\\n').map(q => q.trim()).filter(q => q.length > 2);
  const payload = {{ company, role, questions_faced, confidence_level: confidence, difficulty_level: difficulty }};

  btn.innerHTML = '⏳ Synchronizing with OrchestrAI Analytics...';
  btn.disabled = true;

  try {{
    const resp = await fetch(window.location.origin + '/log-feedback', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(payload)
    }});
    const data = await resp.json();
    if (resp.ok && data.status === 'ok') {{
      showToast('Interview Logged Successfully!', 'Your readiness score and career strategy have been updated.');
      document.getElementById('fb_questions').value = '';
    }} else {{
      showToast('Sync Error', data.message || 'Failed to save feedback analytics.', true);
    }}
  }} catch(e) {{
    showToast('Connection Error', 'Could not reach OrchestrAI agent network: ' + e.message, true);
  }} finally {{
    setTimeout(() => {{
        btn.innerHTML = '📤 Log Interview & Update Analytics';
        btn.disabled = false;
    }}, 1000);
  }}
}}

// ----- AI Interview Chat -----
var chatHistory = [];
var chatCompany = '{company}';
var chatRole = '{role}';

function addChatBubble(role, text, qtype) {{
  var messages = document.getElementById('chatMessages');
  var empty = document.getElementById('chatEmpty');
  if (empty) empty.style.display = 'none';

  var bubble = document.createElement('div');
  bubble.className = 'chat-bubble ' + role;

  var label = document.createElement('span');
  label.className = 'bubble-label';
  label.textContent = role === 'ai' ? '🤖 AI Interviewer' : '👤 You';
  bubble.appendChild(label);

  var content = document.createElement('div');
  content.textContent = text;
  bubble.appendChild(content);

  if (qtype && role === 'ai') {{
    var badge = document.createElement('span');
    badge.className = 'chat-type-badge ' + qtype;
    badge.textContent = qtype;
    bubble.appendChild(badge);
  }}

  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}}

function showTypingIndicator() {{
  var messages = document.getElementById('chatMessages');
  var indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.id = 'typingIndicator';
  indicator.innerHTML = '<span></span><span></span><span></span>';
  messages.appendChild(indicator);
  messages.scrollTop = messages.scrollHeight;
}}

function removeTypingIndicator() {{
  var el = document.getElementById('typingIndicator');
  if (el) el.remove();
}}

async function callInterviewAPI(userAnswer) {{
  var payload = {{
    company: chatCompany,
    role: chatRole,
    question_history: chatHistory,
    user_answer: userAnswer || null
  }};

  var resp = await fetch(window.location.origin + '/api/interview/ask', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(payload)
  }});
  return await resp.json();
}}

async function startAIInterview() {{
  var startBtn = document.getElementById('chatStartBtn');
  var input = document.getElementById('chatInput');
  var sendBtn = document.getElementById('chatSendBtn');

  startBtn.disabled = true;
  startBtn.innerHTML = '⏳ Connecting to AI Interviewer...';

  showTypingIndicator();

  try {{
    var data = await callInterviewAPI(null);
    removeTypingIndicator();

    chatHistory.push({{ role: 'ai', content: data.next_question }});
    addChatBubble('ai', data.next_question, data.question_type);

    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
    startBtn.style.display = 'none';
  }} catch (e) {{
    removeTypingIndicator();
    startBtn.disabled = false;
    startBtn.innerHTML = '🚀 Start AI Interview';
    showToast('Connection Error', 'Could not reach AI interviewer: ' + e.message, true);
  }}
}}

async function callInterviewEvaluate(question, userAnswer) {{
  var payload = {{
    company: chatCompany,
    role: chatRole,
    question: question,
    user_answer: userAnswer
  }};

  var resp = await fetch(window.location.origin + '/api/interview/evaluate', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(payload)
  }});
  return await resp.json();
}}

function addEvaluationCard(evalData) {{
  var messages = document.getElementById('chatMessages');
  var card = document.createElement('div');
  card.className = 'eval-card';
  card.innerHTML = `
    <div style="font-size:0.85rem; font-weight:700; color:#cbd5e1; margin-bottom:8px; text-transform:uppercase; letter-spacing:1px;">📊 Answer Evaluation</div>
    <div style="display:flex; gap:16px; margin-bottom:12px; flex-wrap:wrap;">
      <div class="eval-score"><span>Tech Depth</span><strong>${{evalData.technical_score}}/10</strong></div>
      <div class="eval-score"><span>Clarity</span><strong>${{evalData.clarity_score}}/10</strong></div>
      <div class="eval-score"><span>Comms</span><strong>${{evalData.communication_score}}/10</strong></div>
    </div>
    <div style="font-size:0.9rem; color:#f8fafc; background:rgba(0,0,0,0.2); padding:10px; border-radius:8px; border-left:3px solid #3b82f6;">
      <strong>Suggestion:</strong> ${{evalData.feedback || 'No specific suggestion.'}}
    </div>
  `;
  messages.appendChild(card);
  messages.scrollTop = messages.scrollHeight;
}}

async function sendChatAnswer() {{
  var input = document.getElementById('chatInput');
  var sendBtn = document.getElementById('chatSendBtn');
  var answer = input.value.trim();

  if (!answer) {{
    input.focus();
    return;
  }}

  var lastAiQuestion = '';
  for (var i = chatHistory.length - 1; i >= 0; i--) {{
    if (chatHistory[i].role === 'ai') {{
      lastAiQuestion = chatHistory[i].content;
      break;
    }}
  }}

  // Show user's answer
  chatHistory.push({{ role: 'user', content: answer }});
  addChatBubble('user', answer, null);
  input.value = '';
  input.disabled = true;
  sendBtn.disabled = true;

  showTypingIndicator();

  try {{
    var askPromise = callInterviewAPI(answer);
    var evalPromise = callInterviewEvaluate(lastAiQuestion, answer);

    var [data, evalData] = await Promise.all([askPromise, evalPromise]);

    removeTypingIndicator();

    if (evalData && evalData.technical_score !== undefined) {{
      addEvaluationCard(evalData);
    }}

    chatHistory.push({{ role: 'ai', content: data.next_question }});
    addChatBubble('ai', data.next_question, data.question_type);

    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }} catch (e) {{
    removeTypingIndicator();
    input.disabled = false;
    sendBtn.disabled = false;
    showToast('Error', 'AI response failed: ' + e.message, true);
  }}
}}

// Allow Enter to submit (Shift+Enter for new line)
document.addEventListener('DOMContentLoaded', function() {{
  var chatInput = document.getElementById('chatInput');
  if (chatInput) {{
    chatInput.addEventListener('keydown', function(e) {{
      if (e.key === 'Enter' && !e.shiftKey) {{
        e.preventDefault();
        sendChatAnswer();
      }}
    }});
  }}
}});
</script>
</body>
</html>"""



# ─────────────────────────────────────────────────────────────────────────────
# Main agent
# ─────────────────────────────────────────────────────────────────────────────

def run_interview_coach_agent() -> list[dict]:
    logger.info("InterviewCoachAgent: Starting...")

    jobs_data  = read_yaml_from_github(JOBS_FILE)
    jobs       = jobs_data.get("jobs", []) if isinstance(jobs_data, dict) else []

    users_data = read_yaml_from_github(USERS_FILE)
    user       = users_data.get("user", {}) if isinstance(users_data, dict) else {}
    user_name  = user.get("name", DEFAULT_USER_NAME)
    user_skills = user.get("resume_skills", DEFAULT_SKILLS)

    from backend.github_yaml_db import DATA_DIR
    interview_dir = os.path.join(DATA_DIR, "frontend", "interview")
    os.makedirs(interview_dir, exist_ok=True)

    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://orchestrai-u3wt.onrender.com")
    index    = []
    generated = 0

    for job in jobs:  # Process all internships as requested
        if not isinstance(job, dict):
            continue

        company    = job.get("company", "Unknown")
        role       = job.get("role", "Intern")
        job_skills = [str(s) for s in job.get("technical_skills", []) if s]

        try:
            questions = _generate_questions(company, role, job_skills, user_skills)

            html = _build_interview_html(
                company=company,
                role=role,
                skills=job_skills,
                questions=questions,
                user_name=user_name,
            )

            slug = f"{_slugify(company)}_{_slugify(role)}"
            file_name = f"{slug}.html"
            file_path = f"frontend/interview/{file_name}"
            
            _, sha = _get_raw_file(file_path)
            ts = datetime.now(timezone.utc).isoformat()
            _put_raw_file(file_path, html, sha, f"feat(interview): generated for {company} — {ts}")

            interview_url = f"/interview/{slug}.html"
            index.append({
                "company":        company,
                "role":           role,
                "interview_link": interview_url,
                "generated_at":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            })
            generated += 1
            logger.info("InterviewCoachAgent: ✓ %s — %s → %s", company, role, interview_url)

        except Exception as exc:
            logger.error("InterviewCoachAgent: Failed for %s %s — %s", company, role, exc)

    # Save index to GitHub
    try:
        write_yaml_to_github(INTERVIEW_INDEX_FILE, {"interview_sessions": index})
    except Exception as exc:
        logger.error("InterviewCoachAgent: Failed to save index — %s", exc)

    try:
        append_log_entry({
            "agent":     "InterviewCoachAgent",
            "action":    f"Generated {generated} interview simulation pages",
            "status":    "success" if generated > 0 else "partial",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        })
    except Exception:
        pass

    logger.info("InterviewCoachAgent: Done. %d pages generated.", generated)
    return index


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    results = run_interview_coach_agent()
    print(f"\n✅ Generated {len(results)} interview pages:")
    for r in results:
        print(f"  {r['company']:25s} | {r['role']:35s} | {r['interview_link']}")
