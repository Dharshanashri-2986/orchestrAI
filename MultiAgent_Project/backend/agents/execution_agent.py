"""
execution_agent.py — The Final Orchestrator
OrchestrAI Autonomous Multi-Agent System
"""

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

from backend.agents.career_agent import run_career_agent
from backend.agents.skill_agent import run_skill_agent
from backend.github_yaml_db import read_yaml_from_github, append_log_entry

logger = logging.getLogger("OrchestrAI.ExecutionAgent")

# Email Configuration
EMAIL_USER     = os.getenv("EMAIL_USER", "")
EMAIL_PASS     = os.getenv("EMAIL_PASS", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", EMAIL_USER)
SMTP_HOST      = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT", 587))

def send_email(subject: str, html_content: str) -> bool:
    """Send the HTML email using SMTP."""
    if not EMAIL_USER or not EMAIL_PASS:
        logger.error("ExecutionAgent: EMAIL_USER or EMAIL_PASS not configured in .env")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"OrchestrAI <{EMAIL_USER}>"
    msg["To"] = EMAIL_RECEIVER

    # Set content type to HTML
    msg.set_content("Your email client does not support HTML. Please view it in a modern client.")
    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        logger.info("ExecutionAgent: Successfully sent email to %s", EMAIL_RECEIVER)
        return True
    except Exception as e:
        logger.error("ExecutionAgent: Failed to send email - %s", e)
        return False

def __log_activity(action: str):
    try:
        append_log_entry({
            "agent": "ExecutionAgent",
            "action": action,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        })
    except:
        pass

def run_orchestrai_pipeline():
    logging.info("Starting OrchestrAI pipeline")

    # STEP 1: Fetch internships
    run_career_agent()

    # STEP 2: Generate per-job skill gap analysis
    run_skill_agent()

    # STEP 3: Read GitHub database
    jobs_data = read_yaml_from_github("database/jobs.yaml")
    skill_gap_data = read_yaml_from_github("database/skill_gap_per_job.yaml")

    jobs = jobs_data.get("jobs", []) if isinstance(jobs_data, dict) else []
    skill_analysis = skill_gap_data.get("job_skill_analysis", []) if isinstance(skill_gap_data, dict) else []

    # STEP 4: Convert skill analysis to lookup dictionary
    skill_lookup = {
        (item.get("company", ""), item.get("role", "")): item
        for item in skill_analysis if isinstance(item, dict)
    }

    # STEP 5: Generate HTML table rows
    rows = ""

    for job in jobs:
        if not isinstance(job, dict):
            continue
            
        key = (job.get("company", ""), job.get("role", ""))
        analysis = skill_lookup.get(key, {})

        missing_skills = ", ".join(analysis.get("missing_skills", []))
        roadmap = " &rarr; ".join(analysis.get("roadmap", []))

        rows += f"""
        <tr>
            <td>{job.get('company', '')}</td>
            <td>{job.get('role', '')}</td>
            <td>{job.get('location', '')}</td>
            <td>{', '.join(job.get('technical_skills', []))}</td>
            <td><a href="{job.get('apply_link','#')}">Apply</a></td>
            <td>{missing_skills}</td>
            <td>{roadmap}</td>
        </tr>
        """

    # STEP 6: Generate full HTML email
    html = f"""
    <html>
    <body>
        <h2>Daily AI & Data Science Internship Report</h2>

        <table border="1" cellpadding="8" style="border-collapse: collapse;">
            <tr style="background-color: #f1f3f4; text-align: left;">
                <th>Company</th>
                <th>Role</th>
                <th>Location</th>
                <th>Technical Skills</th>
                <th>Apply</th>
                <th>Skill Gap</th>
                <th>Learning Roadmap</th>
            </tr>
            {rows}
        </table>
    </body>
    </html>
    """

    # STEP 7: Send email
    send_email(
        subject="Daily AI & Data Science Internship Report with Skill Gap Analysis",
        html_content=html
    )

    logging.info("OrchestrAI pipeline completed successfully")
    __log_activity("Pipeline execution completed and email sent")
