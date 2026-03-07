import os
import sys

# Set receiver
os.environ["EMAIL_RECEIVER"] = "dharshpsgps@gmail.com"

# Import execution agent functions and logger
from backend.agents.execution_agent import (
    read_yaml_from_github,
    send_email,
    logger
)

def run_fast_email():
    logger.info("Starting FAST email dispatch...")

    # Set analytics URL fallback
    analytics_url = "https://orchestrai-agent.onrender.com/analytics"

    # STEP 3: Read GitHub database
    jobs_data = read_yaml_from_github("database/jobs.yaml")
    skill_gap_data = read_yaml_from_github("database/skill_gap_per_job.yaml")
    cover_letter_data = read_yaml_from_github("database/cover_letter_index.yaml")
    optimization_data = read_yaml_from_github("database/resume_optimizations.yaml")
    apply_packages_data = read_yaml_from_github("database/application_packages.yaml")
    scores_data = read_yaml_from_github("database/opportunity_scores.yaml")
    practice_data = read_yaml_from_github("database/practice_sessions.yaml")
    portfolio_data = read_yaml_from_github("database/portfolio.yaml")
    security_data = read_yaml_from_github("database/security_reports.yaml")
    strategy_data = read_yaml_from_github("database/career_strategy.yaml")
    readiness_data = read_yaml_from_github("database/career_readiness.yaml")
    interview_data = read_yaml_from_github("database/interview_sessions.yaml")
    per_internship_portfolio_data = read_yaml_from_github("database/per_internship_portfolios.yaml")

    jobs = jobs_data.get("jobs", []) if isinstance(jobs_data, dict) else []
    skill_analysis = skill_gap_data.get("job_skill_analysis", []) if isinstance(skill_gap_data, dict) else []

    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://orchestrai-agent.onrender.com").rstrip("/")
    
    # STEP 4: Convert skill & cover letter analysis to lookup dictionaries
    skill_lookup = {
        (item.get("company", ""), item.get("role", "")): item
        for item in skill_analysis if isinstance(item, dict)
    }
    
    cover_letters = cover_letter_data.get("cover_letters", []) if isinstance(cover_letter_data, dict) else []
    cl_lookup = {
        (item.get("company", ""), item.get("role", "")): (f"{base_url}{item.get('link')}" if item.get('link', '').startswith('/') else f"{base_url}/{item.get('link')}") if item.get('link') else "#"
        for item in cover_letters if isinstance(item, dict)
    }
    
    opt_records = optimization_data if isinstance(optimization_data, list) else []
    opt_lookup = {
        (item.get("company", ""), item.get("role", "")): (f"{base_url}{item.get('optimized_resume_link')}" if item.get('optimized_resume_link', '').startswith('/') else f"{base_url}/{item.get('optimized_resume_link')}") if item.get('optimized_resume_link') else "#"
        for item in opt_records if isinstance(item, dict)
    }

    apply_packages = apply_packages_data if isinstance(apply_packages_data, list) else []
    app_pkg_lookup = {
        (item.get("company", ""), item.get("role", "")): item
        for item in apply_packages if isinstance(item, dict)
    }

    scores_list = scores_data if isinstance(scores_data, list) else []
    score_lookup = {
        (item.get("company", ""), item.get("role", "")): item
        for item in scores_list if isinstance(item, dict)
    }

    practice_list = practice_data if isinstance(practice_data, list) else []
    practice_lookup = {
        (item.get("company", ""), item.get("role", "")): (f"{base_url}{item.get('practice_link')}" if item.get('practice_link', '').startswith('/') else f"{base_url}/{item.get('practice_link')}") if item.get('practice_link') else ""
        for item in practice_list if isinstance(item, dict)
    }

    per_internship_list = per_internship_portfolio_data.get("per_internship_portfolios", []) if isinstance(per_internship_portfolio_data, dict) else []
    per_internship_lookup = {
        (item.get("company", ""), item.get("role", "")): (f"{base_url}{item.get('portfolio_url')}" if item.get('portfolio_url', '').startswith('/') else f"{base_url}/{item.get('portfolio_url')}") if item.get('portfolio_url') else ""
        for item in per_internship_list if isinstance(item, dict)
    }

    interview_list = interview_data.get("interview_sessions", []) if isinstance(interview_data, dict) else []
    interview_lookup = {
        (item.get("company", ""), item.get("role", "")): (f"{base_url}{item.get('interview_link')}" if item.get('interview_link', '').startswith('/') else f"{base_url}/{item.get('interview_link')}") if item.get('interview_link') else ""
        for item in interview_list if isinstance(item, dict)
    }

    portfolio_url = portfolio_data.get("portfolio", {}).get("url", "#") if isinstance(portfolio_data, dict) else "#"
    portfolio_html = f'<a href="{portfolio_url}" style="background:#2e7d32;color:white;padding:8px 14px;border-radius:6px;text-decoration:none;display:inline-block;font-weight:600;min-width:max-content;">View Portfolio</a>' if portfolio_url != "#" else "Not Generated"

    security_reports = security_data.get("security_reports", []) if isinstance(security_data, dict) else []

    # Build per-repo security lookup
    sec_report_lookup = {}
    sec_insights_html = ""
    if security_reports:
        for report in security_reports:
            repo_name = report.get("repo", "Unknown")
            repo_url = report.get("repo_url", f"https://github.com/Swathy1209/{repo_name}")
            risk_level = report.get("risk_level", "")
            if not risk_level:
                rs = report.get("risk_score", 0)
                risk_level = "High" if rs > 7 else "Medium" if rs > 3 else "Low" if rs > 0 else "Safe"
            risk_color = {"High": "red", "Medium": "orange", "Low": "#f9a825", "Safe": "green"}.get(risk_level, "gray")
            issues = report.get("issues", [])
            top_issue = str(issues[0]) if issues else "No issues found."
            pr_url = report.get("auto_fix_pr", "")
            total_vulns = report.get("total_vulnerabilities", 0)
            scanned_files = report.get("scanned_files", 0)

            sec_report_lookup[repo_name] = {"level": risk_level, "color": risk_color}

            pr_html = f' <a href="{pr_url}" style="background:#1565c0;color:white;padding:2px 8px;border-radius:3px;text-decoration:none;font-size:11px">View PR →</a>' if pr_url else ""
            sec_insights_html += (
                f'<li style="margin-bottom:10px">'
                f'<a href="{repo_url}" style="font-weight:bold;color:#1a237e">{repo_name}</a> — '
                f'Risk: <span style="color:{risk_color};font-weight:bold">{risk_level}</span>'
                f' | {total_vulns} vulns | {scanned_files} files scanned{pr_html}'
                f'<br><span style="font-size:12px;color:#555;margin-left:10px">⤷ {top_issue[:100]}</span>'
                f'</li>'
            )
    else:
        sec_insights_html = "<li>No security scans performed yet. Scanner runs automatically each day.</li>"

    strategy = strategy_data.get("strategy", {}) if isinstance(strategy_data, dict) else {}
    strategy_goal = strategy.get("goal", "Data Engineering Internship")
    strategy_actions = strategy.get("actions", [])
    strategy_analysis = strategy.get("analysis", {})

    if strategy_actions:
        strategy_action_html = "".join(
            f'<li style="margin:6px 0;padding:4px 8px;background:#e8f5e9;border-left:3px solid #2e7d32;border-radius:3px">{action}</li>'
            for action in strategy_actions
        )
    else:
        strategy_action_html = "<li>Keep practicing and building projects!</li>"

    top_skills = strategy_analysis.get("top_missing_skills", [])
    portfolio_str = strategy_analysis.get("portfolio_strength", "")
    practice_str = strategy_analysis.get("practice_status", "")
    top_opps = strategy_analysis.get("top_opportunities", [])

    skill_badges = "".join(
        f'<span style="background:#ffebee;color:#c62828;padding:3px 8px;border-radius:12px;font-size:11px;margin:2px;display:inline-block">{s}</span>'
        for s in top_skills[:5]
    ) if top_skills else '<span style="color:green">✓ No critical skill gaps</span>'

    opp_list = "".join(f"<li style='font-size:12px;margin:3px 0'>{o}</li>" for o in top_opps[:3]) if top_opps else "<li>Run pipeline to identify top matches</li>"

    cr = readiness_data.get("career_readiness", {}) if isinstance(readiness_data, dict) else {}
    readiness_score = cr.get("readiness_score", 0)
    readiness_label = cr.get("label", "")
    readiness_color = (
        "#2e7d32" if readiness_score >= 85 else
        "#1565c0" if readiness_score >= 70 else
        "#e65100" if readiness_score >= 50 else "#c62828"
    )
    readiness_html = (
        f'<div style="background:{readiness_color};color:white;border-radius:10px;padding:14px 20px;display:inline-block;margin-bottom:16px">'
        f'<span style="font-size:28px;font-weight:700">{readiness_score}</span>'
        f'<span style="font-size:14px">/100</span>&nbsp;&nbsp;'
        f'<span style="font-size:15px;font-weight:600">{readiness_label}</span></div>'
    ) if readiness_score else '<span style="color:#999">Readiness score computing...</span>'

    pf = security_data.get("priority_security_fix", {}) if isinstance(security_data, dict) else {}
    if pf and pf.get("issue") and pf.get("risk") in ("HIGH", "MEDIUM", "HIGH"):
        pf_risk_color = "red" if pf.get("risk") == "HIGH" else "orange"
        pf_repo_url = pf.get("repo_url", f"https://github.com/Swathy1209/{pf.get('repo','')}")
        priority_fix_html = (
            f'<div style="background:#fff3e0;border:2px solid #e65100;border-radius:10px;padding:16px;margin-bottom:20px">'
            f'<h3 style="color:#e65100;margin:0 0 10px 0">🚨 Priority Security Fix Required</h3>'
            f'<table style="width:100%;font-size:13px;border-collapse:collapse">'
            f'<tr><td style="color:#666;width:100px">Repository</td><td><a href="{pf_repo_url}" style="color:#1565c0;font-weight:600">{pf.get("repo","")}</a></td></tr>'
            f'<tr><td style="color:#666">Risk Level</td><td><span style="background:{pf_risk_color};color:white;padding:2px 8px;border-radius:3px;font-size:12px;font-weight:600">{pf.get("risk","")}</span></td></tr>'
            f'<tr><td style="color:#666">Vulnerability</td><td style="font-weight:600">{pf.get("issue","")}</td></tr>'
            f'<tr><td style="color:#666">File</td><td><code style="background:#f5f5f5;padding:2px 6px;border-radius:3px">{pf.get("file","")}:{pf.get("line","")}</code></td></tr>'
            f'<tr><td style="color:#666">Code</td><td><code style="background:#ffebee;padding:2px 6px;border-radius:3px;color:#b71c1c">{str(pf.get("snippet",""))[:80]}</code></td></tr>'
            f'<tr><td style="color:#666">Fix</td><td style="color:#2e7d32">{pf.get("fix","")}</td></tr>'
            f'</table></div>'
        )
    else:
        priority_fix_html = '<div style="background:#e8f5e9;border-radius:8px;padding:12px;margin-bottom:16px;color:#2e7d32">✅ No critical security issues detected across all repositories!</div>'

    rows = ""
    for job in jobs:
        if not isinstance(job, dict): continue
        c_name = job.get("company", "")
        key = (c_name, job.get("role", ""))
        analysis = skill_lookup.get(key, {})
        missing_skills = ", ".join(analysis.get("missing_skills", []))
        roadmap = " &rarr; ".join(analysis.get("roadmap", []))
        cl_link = cl_lookup.get(key, "#")
        cl_html = f'<a href="{cl_link}" style="background:#2e7d32; color:white; padding:6px 12px; text-decoration:none; border-radius:6px; display:inline-block; margin-bottom: 4px;">Cover Letter</a>' if cl_link and cl_link != "#" else "Not Generated"
        opt_link = opt_lookup.get(key, "#")
        opt_html = f'<a href="{opt_link}" style="background:#0277bd; color:white; padding:6px 12px; text-decoration:none; border-radius:6px; display:inline-block;">Optimized Resume</a>' if opt_link and opt_link != "#" else "Not Generated"
        app_pkg = app_pkg_lookup.get(key, {})
        app_status = app_pkg.get("status", "Not Generated")
        app_link = app_pkg.get("application_package_link", "#")
        status_color = "#f29900" if app_status == "Not Generated" else "#1a73e8"
        app_html = f'<br><br><a href="{app_link}" style="padding:4px 8px; border-radius:4px; font-weight:bold; color:white; background-color:{status_color}; font-size:11px; text-decoration:none; display:inline-block;">{app_status}</a>' if app_link and app_link != "#" else f'<br><br><span style="padding:4px 8px; border-radius:4px; font-weight:bold; color:white; background-color:{status_color}; font-size:11px; display:inline-block;">{app_status}</span>'
        score_info = score_lookup.get(key, {})
        score_html = f"<b>Score:</b> {score_info.get('match_score', 0)}/100<br>"
        pip_url = per_internship_lookup.get(key, "")
        custom_portfolio_html = f'<a href="{pip_url}" style="background:#1565c0;color:white;padding:8px 14px;border-radius:6px;text-decoration:none;display:inline-block;font-weight:600;font-size:12px">🎯 Custom Portfolio</a>' if pip_url else '<span style="color:#999;font-size:12px">Not Generated</span>'
        interview_url = interview_lookup.get(key, "")
        interview_html = f'<a href="{interview_url}" style="background:#7c3aed;color:white;padding:8px 14px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;font-size:12px">🎤 Start Mock Interview</a>' if interview_url else '<span style="color:#999;font-size:12px">Not Generated</span>'

        rows += f"<tr><td style='padding:8px;border:1px solid #ddd'>{c_name}</td><td style='padding:8px;border:1px solid #ddd'>{job.get('role', '')}</td><td style='padding:8px;border:1px solid #ddd'><a href=\"{job.get('apply_link','#')}\" style=\"font-weight:bold;color:#1565c0\">Apply</a>{app_html}</td><td style='padding:8px;border:1px solid #ddd'>{score_html}</td><td style='padding:8px;border:1px solid #ddd'>{cl_html}<br><br>{opt_html}</td><td style='padding:8px;border:1px solid #ddd;text-align:center'>{custom_portfolio_html}</td><td style='padding:8px;border:1px solid #ddd;text-align:center'>{interview_html}</td></tr>"

    html = f"""
    <html>
    <head><style>
      body {{ font-family: Arial, sans-serif; font-size: 13px; background: #f8f9fa; margin: 0; padding: 20px; }}
      h2, h3 {{ color: #1a237e; }}
      table {{ border-collapse: collapse; width: 100%; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
      th {{ background: #1a237e; color: white; padding: 10px 8px; text-align: left; font-size: 12px; white-space: nowrap; }}
      tr:nth-child(even) td {{ background: #f5f5f5; }}
    </style></head>
    <body>
        <h2>&#x1F916; Daily AI &amp; Data Science Internship Report</h2>
        <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:20px;">
          <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap">
            <div>
              <p style="color:#666;font-size:12px;margin:0 0 6px 0;font-weight:600">&#x1F3AF; CAREER READINESS SCORE</p>
              {readiness_html}
            </div>
            <div style="margin-bottom:16px;">
              <a href="https://orchestrai.onrender.com/dashboard" style="background:linear-gradient(135deg, #1e3a8a, #3b82f6);color:white;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;display:inline-block;box-shadow:0 4px 6px rgba(59,130,246,0.25);border:1px solid #60a5fa">🌐 Launch Web Dashboard</a>
            </div>
          </div>
        </div>
        {priority_fix_html}
        <table><tr><th>Company</th><th>Role</th><th>Apply</th><th>Match Score</th><th>Generated Assets</th><th>&#x1F3AF; Custom Portfolio</th><th>&#x1F3A4; Interview Sim</th></tr>{rows}</table>
        <h3>&#x1F9ED; Career Strategy Recommendation</h3>
        <p>Goal: {strategy_goal}</p>
        <p>Top Missing Skills: {skill_badges}</p>
        <div style="background:#1a1a2e;border-radius:12px;padding:20px;text-align:center;margin-top:24px">
          <a href="{base_url}/dashboard" style="background:linear-gradient(135deg,#06b6d4,#7c3aed);color:white;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block;margin:4px">🚀 View Interactive Dashboard</a>
        </div>
    </body>
    </html>
    """

    logger.info("Sending fast email...")
    send_email("Daily AI & Data Science Internship Report with Skill Gap Analysis", html)
    logger.info("Fast email dispatched to your inbox.")

if __name__ == "__main__":
    run_fast_email()
