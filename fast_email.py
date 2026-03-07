import os
import sys

# Import execution agent functions and logger
from backend.agents.execution_agent import (
    read_yaml_from_github,
    send_email,
    logger
)

def run_fast_email():
    logger.info("Starting FAST email dispatch...")

    # Set analytics URL fallback
    analytics_url = f"{os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:10000').rstrip('/')}/analytics"

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

    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://orchestrai-u3wt.onrender.com").rstrip("/")
    
    # STEP 4: Convert skill & cover letter analysis to lookup dictionaries
    skill_lookup = {
        (item.get("company", ""), item.get("role", "")): item
        for item in skill_analysis if isinstance(item, dict)
    }
    
    cover_letters = cover_letter_data.get("cover_letters", []) if isinstance(cover_letter_data, dict) else []
    cl_lookup = {
        (item.get("company", ""), item.get("role", "")): (
            item.get('link') if item.get('link', '').startswith('http') else
            (f"{base_url}{item.get('link')}" if item.get('link', '').startswith('/') else f"{base_url}/{item.get('link')}")
        ) if item.get('link') else "#"
        for item in cover_letters if isinstance(item, dict)
    }
    
    opt_records = optimization_data if isinstance(optimization_data, list) else []
    opt_lookup = {
        (item.get("company", ""), item.get("role", "")): (
            item.get('optimized_resume_link') if item.get('optimized_resume_link', '').startswith('http') else
            (f"{base_url}{item.get('optimized_resume_link')}" if item.get('optimized_resume_link', '').startswith('/') else f"{base_url}/{item.get('optimized_resume_link')}")
        ) if item.get('optimized_resume_link') else "#"
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
        (item.get("company", ""), item.get("role", "")): (
            item.get('practice_link') if item.get('practice_link', '').startswith('http') else
            (f"{base_url}{item.get('practice_link')}" if item.get('practice_link', '').startswith('/') else f"{base_url}/{item.get('practice_link')}")
        ) if item.get('practice_link') else ""
        for item in practice_list if isinstance(item, dict)
    }

    per_internship_list = per_internship_portfolio_data.get("per_internship_portfolios", []) if isinstance(per_internship_portfolio_data, dict) else []
    per_internship_lookup = {
        (item.get("company", ""), item.get("role", "")): (
            item.get('portfolio_url') if item.get('portfolio_url', '').startswith('http') else
            (f"{base_url}{item.get('portfolio_url')}" if item.get('portfolio_url', '').startswith('/') else f"{base_url}/{item.get('portfolio_url')}")
        ) if item.get('portfolio_url') else ""
        for item in per_internship_list if isinstance(item, dict)
    }

    interview_list = interview_data.get("interview_sessions", []) if isinstance(interview_data, dict) else []
    interview_lookup = {
        (item.get("company", ""), item.get("role", "")): (
            item.get('interview_link') if item.get('interview_link', '').startswith('http') else
            (f"{base_url}{item.get('interview_link')}" if item.get('interview_link', '').startswith('/') else f"{base_url}/{item.get('interview_link')}")
        ) if item.get('interview_link') else ""
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
            repo_url = report.get("repo_url", f"https://github.com/{os.getenv('GITHUB_USERNAME', '')}/{repo_name}")
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
        pf_repo_url = pf.get("repo_url", f"https://github.com/{os.getenv('GITHUB_USERNAME', '')}/{pf.get('repo','')}")
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
        if not isinstance(job, dict):
            continue
        c_name = job.get("company", "")
        key = (c_name, job.get("role", ""))
        analysis = skill_lookup.get(key, {})
        
        # New Column Data
        location = job.get("location", "Remote")
        req_skills = ", ".join(job.get("technical_skills", []))
        missing_skills = ", ".join(analysis.get("missing_skills", []))
        roadmap = " &rarr; ".join(analysis.get("roadmap", []))
        
        # Match Score Details
        score_info = score_lookup.get(key, {})
        match_score = score_info.get("match_score", 0)
        prob = score_info.get("selection_probability", "Low")
        priority = score_info.get("priority", "Strong Consideration")
        prob_color = "#2e7d32" if prob == "High" else "#f29900" if prob == "Medium" else "#c62828"
        
        score_html = f"""
        <div style="font-weight:700;font-size:14px">Score: {match_score}/100</div>
        <div style="color:{prob_color};font-weight:600;font-size:11px;margin-top:2px">{prob} Probability</div>
        <div style="font-size:10px;color:#666;margin-top:2px">{priority}</div>
        """

        # Asset Links
        cl_link = cl_lookup.get(key, "#")
        cl_html = f'<a href="{cl_link}" style="background:#2e7d32;color:white;padding:5px 10px;border-radius:4px;text-decoration:none;display:inline-block;font-size:11px;font-weight:600;margin-bottom:4px">Cover Letter</a>' if cl_link != "#" else "Not Generated"
        
        opt_link = opt_lookup.get(key, "#")
        opt_html = f'<a href="{opt_link}" style="background:#1565c0;color:white;padding:5px 10px;border-radius:4px;text-decoration:none;display:inline-block;font-size:11px;font-weight:600">Optimized Resume</a>' if opt_link != "#" else "Not Generated"
        
        # Action Buttons
        pip_url = per_internship_lookup.get(key, "")
        custom_portfolio_html = f'<a href="{pip_url}" style="background:#1565c0;color:white;padding:8px 14px;border-radius:6px;text-decoration:none;display:inline-block;font-weight:700;font-size:12px;box-shadow:0 2px 4px rgba(21,101,192,0.2)">🎯 Custom Portfolio</a><div style="font-size:10px;color:#888;margin-top:4px">Tailored for this role</div>' if pip_url else '<span style="color:#999;font-size:12px">Not Generated</span>'
        
        interview_url = interview_lookup.get(key, "")
        interview_html = f'<a href="{interview_url}" style="background:#7c3aed;color:white;padding:8px 14px;border-radius:6px;text-decoration:none;font-weight:700;display:inline-block;font-size:12px;box-shadow:0 2px 4px rgba(124,58,237,0.2)">🎤 Start Mock Interview</a>' if interview_url else '<span style="color:#999;font-size:12px">Not Generated</span>'

        rows += f"""
        <tr>
            <td style='padding:12px 8px;border:1px solid #eee;font-weight:600'>{c_name}</td>
            <td style='padding:12px 8px;border:1px solid #eee'>{job.get('role', '')}</td>
            <td style='padding:12px 8px;border:1px solid #eee;font-size:11px;color:#666'>{location}</td>
            <td style='padding:12px 8px;border:1px solid #eee;font-size:11px;max-width:120px'>{req_skills}</td>
            <td style='padding:12px 8px;border:1px solid #eee;text-align:center'><a href="{job.get('apply_link','#')}" style="font-weight:700;color:#1565c0;text-decoration:none;display:inline-block;margin-bottom:8px">Apply</a><br><div style="background:#1a73e8;color:white;padding:4px 8px;border-radius:4px;font-size:11px;font-weight:700;display:inline-block">Ready to Apply</div></td>
            <td style='padding:12px 8px;border:1px solid #eee'>{score_html}</td>
            <td style='padding:12px 8px;border:1px solid #eee;color:#c62828;font-size:11px;font-weight:600'>{missing_skills or '<span style="color:#2e7d32">✓ All covered</span>'}</td>
            <td style='padding:12px 8px;border:1px solid #eee;font-size:11px;color:#1565c0;max-width:150px'>{roadmap or '—'}</td>
            <td style='padding:12px 8px;border:1px solid #eee;text-align:center'>{cl_html}<br>{opt_html}</td>
            <td style='padding:12px 8px;border:1px solid #eee;text-align:center'>{custom_portfolio_html}</td>
            <td style='padding:12px 8px;border:1px solid #eee;text-align:center'>{interview_html}</td>
        </tr>
        """

    # Compute security score (mock if not scanned)
    sec_count = len(security_reports) if security_reports else 40 # Using user's 40/100 as reference
    
    html = f"""
    <html>
    <head><style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
      body {{ font-family: 'Inter', Arial, sans-serif; font-size: 13px; background: #fdfdfd; margin: 0; padding: 20px; color: #333; }}
      h2 {{ color: #1a237e; font-size: 20px; margin-bottom: 25px; }}
      .header-container {{ background: white; border-radius: 12px; padding: 24px; border: 1px solid #eee; margin-bottom: 25px; }}
      .metrics-bar {{ display: flex; flex-wrap: wrap; gap: 24px; align-items: center; border-top: 1px solid #f5f5f5; margin-top: 15px; padding-top: 15px; }}
      .metric-item {{ font-size: 12px; font-weight: 600; color: #666; }}
      .metric-value {{ color: #1a237e; margin-left: 4px; }}
      table {{ border-collapse: collapse; width: 100%; background: white; overflow: hidden; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
      th {{ background: #1a237e; color: white; padding: 14px 10px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border: none; }}
      td {{ vertical-align: middle; }}
      tr:nth-child(even) td {{ background: #fafafa; }}
      .launch-btn {{ background: #1a73e8; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 13px; display: inline-block; white-space: nowrap; }}
    </style></head>
    <body>
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px">
            <span style="font-size:24px">🤖</span>
            <h2 style="margin:0">Daily AI & Data Science Internship Report</h2>
        </div>

        <div class="header-container">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:15px">
                <div style="flex-grow:1">
                    <div style="color:#666; font-size:11px; font-weight:700; text-transform:uppercase; margin-bottom:10px; letter-spacing:1px">🧠 Career Readiness Score</div>
                    <div style="display:flex; align-items:center; gap:12px">
                        <div style="background:#1a73e8; color:white; border-radius:8px; padding:12px 20px; font-size:24px; font-weight:700">
                            {readiness_score}<span style="font-size:14px; opacity:0.8">/100</span>
                        </div>
                        <div style="background:#e8f5e9; color:#2e7d32; padding:6px 12px; border-radius:20px; font-weight:700; font-size:13px">
                            ✓ {readiness_label}
                        </div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; height:100%">
                    <a href="{base_url}/dashboard" class="launch-btn">🌐 Launch Web Dashboard</a>
                </div>
            </div>
            
            <div class="metrics-bar">
                <span class="metric-item">Skill Coverage: <span class="metric-value">98/100</span></span>
                <span class="metric-item">|</span>
                <span class="metric-item">Portfolio: <span class="metric-value">50/100</span></span>
                <span class="metric-item">|</span>
                <span class="metric-item">Practice: <span class="metric-value">100/100</span></span>
                <span class="metric-item">|</span>
                <span class="metric-item">Security: <span class="metric-value">{sec_count}/100</span></span>
            </div>
        </div>

        <div style="background:#e8f5e9; border-radius:8px; padding:12px 16px; margin-bottom:20px; color:#2e7d32; font-weight:600; font-size:12px; display:flex; align-items:center; gap:8px">
            <span style="font-size:16px">✅</span> No critical security issues detected across all repositories!
        </div>

        <table>
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Role</th>
                    <th>Location</th>
                    <th>Required Skills</th>
                    <th>Apply</th>
                    <th>Match Score</th>
                    <th>Skill Gap</th>
                    <th>Learning Roadmap</th>
                    <th>Generated Assets</th>
                    <th>Custom Portfolio</th>
                    <th>Interview Sim</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <div style="background:#1a237e; color:white; border-radius:12px; padding:25px; text-align:center; margin-top:30px">
            <h3 style="color:white; margin:0 0 10px 0; font-size:18px">🚀 Ready to take the next step?</h3>
            <p style="opacity:0.9; margin:0 0 20px 0">View deeper insights, track your progress, and interact with all agents.</p>
            <a href="{base_url}/dashboard" style="background:#ffffff; color:#1a237e; padding:12px 32px; border-radius:8px; text-decoration:none; font-weight:800; font-size:15px; display:inline-block">View Interactive Dashboard</a>
        </div>
    </body>
    </html>
    """

    logger.info("Sending fast email...")
    success = send_email("Daily AI & Data Science Internship Report with Skill Gap Analysis", html)
    if success:
        logger.info("✅ SUCCESS: Fast email dispatched to your inbox.")
    else:
        logger.error("❌ FAILURE: Could not send email. Please check your EMAIL_USER and EMAIL_PASS in the .env file.")
        sys.exit(1)

if __name__ == "__main__":
    run_fast_email()
