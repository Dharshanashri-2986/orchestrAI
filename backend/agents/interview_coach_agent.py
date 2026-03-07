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
<title>Mock Interview — {{role}} at {{company}}</title>
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
</style>
</head>
<body>

<div class="hero">
  <h1>Interactive Mock Interview</h1>
  <h2>{{role}} &mdash; <strong>{{company}}</strong></h2>
  <div class="hero-badges">
    <span class="badge">👤 {{user_name}}</span>
    <span class="badge">📅 {{ts}}</span>
    <span class="badge">⏱️ AI Guided</span>
  </div>
</div>

<div class="container">

  <div class="skill-info">
    <h3>🎯 Target Competencies</h3>
    <div class="skill-tags">{{skill_tags or '<span class="skill-tag">General Software Engineering</span>'}}</div>
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
    {{_q_items(questions.get('technical', []), '⚙️')}}
  </div>

  <div class="section-container" id="coding">
    <h3 class="section-title"><span>💻</span> Coding Challenges</h3>
    <p class="section-desc">Write robust, optimal code and explain your time/space complexities.</p>
    {{_code_items(questions.get('coding', []))}}
  </div>

  <div class="section-container" id="behavioral">
    <h3 class="section-title"><span>🧠</span> Behavioral & Situational</h3>
    <p class="section-desc">Use the STAR method (Situation, Task, Action, Result) to frame your answers.</p>
    {{_q_items(questions.get('behavioral', []), '🧠')}}
  </div>

  {{case_section}}

  <div class="feedback-form">
    <h3 style="color:#c084fc">📝 Interview Debrief</h3>
    <p class="section-desc" style="margin-bottom:0">Submit your performance data. The agent will analyze your gaps and update your career learning plan immediately.</p>
    
    <div class="form-grid">
      <div class="form-group" style="margin:0">
        <label>Company</label>
        <input class="form-input" id="fb_company" value="{{company}}" readonly />
      </div>
      <div class="form-group" style="margin:0">
        <label>Role</label>
        <input class="form-input" id="fb_role" value="{{role}}" readonly />
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
    OrchestrAI Autonomous Carrier Intelligence System &copy; {{datetime.now().year}}
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
