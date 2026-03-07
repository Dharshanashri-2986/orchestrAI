"""
main.py — OrchestrAI Career Agent Entry Point
Runs on Render as a FastAPI Web Service.

Flow:
  Render Env Vars  →  FastAPI + Scheduler  →  Gmail email
"""

import logging
import os
import sys
import threading
import traceback
import base64
import requests
from typing import List, Dict

from dotenv import load_dotenv

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("OrchestrAI")

# ── Entry point ───────────────────────────────────────────────────────────────
def run_full_pipeline():
    from backend.agents.execution_agent import run_orchestrai_pipeline
    try:
        run_orchestrai_pipeline()
    except Exception as exc:
        logger.error("Pipeline CRASHED: %s", traceback.format_exc())

# ── FastAPI Web Server Setup ───────────────────────────────────────────────
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="OrchestrAI Dashboard", description="OrchestrAI Autonomous Career Intelligence System.")

# ── Include Dashboard API routes ───────────────────────────────────────────
from backend.api.dashboard_routes import router as dashboard_api_router
app.include_router(dashboard_api_router)

# ── Include Practice routes ────────────────────────────────────────────────
try:
    from backend.api.practice_routes import router as practice_router
    app.include_router(practice_router)
except Exception:
    pass

STATIC_DIRS = [
    "database",
    "application_packages",
    "frontend/practice",
    "frontend/portfolio",
    "frontend/portfolio/internships",
    "frontend/interview",
    "frontend/analytics",
    "frontend/dashboard",
    "optimized_resumes",
    "cover_letters",
]
from backend.github_yaml_db import DATA_DIR

for _d in STATIC_DIRS:
    _path = os.path.join(DATA_DIR, _d)
    os.makedirs(_path, exist_ok=True)

# Seed each directory with a placeholder so StaticFiles doesn't crash
for _d in STATIC_DIRS:
    _placeholder = os.path.join(DATA_DIR, _d, ".keep")
    if not os.path.exists(_placeholder):
        try:
            with open(_placeholder, "w") as f:
                f.write("")
        except Exception:
            pass

# ── Specialized Asset Serving with GitHub Fallback ────────────────────────────
from backend.github_yaml_db import read_raw_file_from_github
from fastapi.responses import FileResponse, Response

async def _serve_with_github_fallback(category: str, filename: str):
    """Try local disk first, then GitHub cloud."""
    local_path = os.path.join(DATA_DIR, category, filename)
    if os.path.exists(local_path):
        return FileResponse(local_path)
    
    # Fallback to GitHub
    github_path = f"{category}/{filename}"
    logger.info("Asset not found locally: %s. Fetching from GitHub...", github_path)
    content = read_raw_file_from_github(github_path)
    if content:
        # Save locally for next time
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass
        
        # Serve as markdown or plain depending on ext
        media_type = "text/markdown" if filename.endswith(".md") else "text/plain"
        return Response(content=content, media_type=media_type)
        
    return HTMLResponse(f"Not Found: {filename} (Tried Local & GitHub)", status_code=404)

@app.get("/cover_letters/{filename}")
async def serve_cover_letter_file(filename: str):
    return await _serve_with_github_fallback("cover_letters", filename)

@app.get("/optimized_resumes/{filename}")
async def serve_optimized_resume_file(filename: str):
    return await _serve_with_github_fallback("optimized_resumes", filename)

# ── Mount static directories (safe — all dirs guaranteed to exist) ──────────
def _safe_mount(route, directory, name, html=False):
    try:
        kwargs = {"html": html} if html else {}
        app.mount(route, StaticFiles(directory=directory, **kwargs), name=name)
        logger.info("Mounted static dir: %s -> %s", route, directory)
    except Exception as exc:
        logger.warning("Could not mount %s: %s", route, exc)

_safe_mount("/database",            os.path.join(DATA_DIR, "database"),             "database")
_safe_mount("/application_packages", os.path.join(DATA_DIR, "application_packages"), "application_packages")
_safe_mount("/frontend/practice",   os.path.join(DATA_DIR, "frontend/practice"),    "practice")
_safe_mount("/portfolio",           os.path.join(DATA_DIR, "frontend/portfolio"),   "portfolio", html=True)
_safe_mount("/interview",           os.path.join(DATA_DIR, "frontend/interview"),   "interview", html=True)
_safe_mount("/dashboard/static",    os.path.join(DATA_DIR, "frontend/dashboard"),   "dashboard_static", html=False)

@app.get("/dashboard")
@app.get("/dashboard/")
async def serve_dashboard():
    """Serve the interactive career intelligence dashboard."""
    path = os.path.join(DATA_DIR, "frontend/dashboard/index.html")
    if os.path.exists(path):
        from fastapi.responses import FileResponse
        return FileResponse(path, media_type="text/html")
    return HTMLResponse(
        "<h1>Dashboard Loading... 🤖</h1>"
        "<p>The dashboard files are being set up. Please refresh in a few seconds.</p>"
        "<script>setTimeout(()=>location.reload(), 3000)</script>",
        status_code=202,
    )

@app.get("/analytics")
@app.get("/analytics/")
async def serve_analytics():
    """Specific route for analytics to ensure index.html is served without 404s."""
    path = os.path.join(DATA_DIR, "frontend/analytics/index.html")
    if os.path.exists(path):
        from fastapi.responses import FileResponse
        return FileResponse(path)
    # If not found, try a sync before giving up
    sync_from_github_cloud()
    if os.path.exists(path):
         from fastapi.responses import FileResponse
         return FileResponse(path)
    return HTMLResponse("<h1>Hold on... 🤖</h1><p>The analytics dashboard is being synced from the cloud. Please refresh in 5 seconds.</p><script>setTimeout(()=>location.reload(), 5000)</script>", status_code=202)

@app.get("/debug-sync")
def debug_sync():
    import glob
    files = glob.glob(os.path.join(DATA_DIR, "**/*"), recursive=True)
    # Filter for interesting dirs
    interesting = [f for f in files if "cover_letters" in f or "optimized_resumes" in f or "database" in f]
    return {"data_dir": os.path.abspath(DATA_DIR), "files_found": len(files), "interesting_files": interesting[:100]}

def sync_from_github_cloud():
    """Download all YAML and HTML files from GitHub to local DATA_DIR."""
    from backend.github_yaml_db import GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO, GITHUB_BRANCH, _BASE_URL, _auth_headers
    if not all([GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO]):
        logger.warning("Cloud Sync: Missing credentials — skipping sync.")
        return

    _REPO_SLUG = GITHUB_REPO if "/" in GITHUB_REPO else f"{GITHUB_USERNAME}/{GITHUB_REPO}"
    logger.info("Cloud Sync: Starting deep sync from %s...", _REPO_SLUG)

    dirs_to_sync = [
        "database",
        "cover_letters",
        "optimized_resumes",
        "application_packages",
        "frontend/analytics",
        "frontend/portfolio/internships",
        "frontend/interview",
        "frontend/practice",
        "frontend/dashboard",
    ]
    
    for d in dirs_to_sync:
        url = f"{_BASE_URL}/repos/{_REPO_SLUG}/contents/{d}?ref={GITHUB_BRANCH}"
        try:
            resp = requests.get(url, headers=_auth_headers(), timeout=15)
            if resp.status_code == 200:
                files = resp.json()
                if isinstance(files, list):
                    for f_meta in files:
                        path = f_meta["path"]
                        if f_meta["type"] == "file":
                            # Download file
                            f_url = f_meta["url"]
                            f_resp = requests.get(f_url, headers=_auth_headers(), timeout=10)
                            if f_resp.status_code == 200:
                                raw_bytes = base64.b64decode(f_resp.json()["content"])
                                local_path = os.path.join(DATA_DIR, path)
                                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                                
                                # If binary file, write as bytes
                                if any(path.lower().endswith(ext) for ext in [".pdf", ".png", ".jpg", ".jpeg"]):
                                    with open(local_path, "wb") as f:
                                        f.write(raw_bytes)
                                else:
                                    # Otherwise write as strings
                                    with open(local_path, "w", encoding="utf-8") as f:
                                        f.write(raw_bytes.decode("utf-8"))
                                logger.info("Cloud Sync: ✓ %s", path)
            else:
                logger.warning("Cloud Sync: Could not list %s (%d)", d, resp.status_code)
        except Exception as e:
            logger.error("Cloud Sync: Failed for %s - %s", d, e)

@app.get("/sync")
def manual_sync():
    sync_from_github_cloud()
    return {"status": "ok", "message": "Deep sync completed from GitHub."}

@app.on_event("startup")
def start_scheduler():
    # Sync from cloud first so we have the latest files to serve
    try:
        sync_from_github_cloud()
    except Exception as e:
        logger.error("Initial sync failure: %s", e)

    try:
        from backend.scheduler import schedule_daily_internship_email, run_once_now

        if os.getenv("RUN_ON_STARTUP", "false").lower() == "true":
            logger.info("Startup trigger: running full pipeline immediately in background...")
            t = threading.Thread(target=run_full_pipeline, daemon=True)
            t.start()

        logger.info("Starting scheduler: full pipeline will run daily at 9:30 AM IST.")
        schedule_daily_internship_email(run_full_pipeline, hour=9, minute=30)
    except Exception as exc:
        logger.error("Scheduler startup failed: %s", exc)

from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

# Allow browser POSTs from interview pages (same Render domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

@app.head("/")
def head_root():
    """UptimeRobot / health probes send HEAD — return 200 so it doesn't mark us as down."""
    return JSONResponse(content={}, status_code=200)

@app.get("/health")
def health():
    """Health check endpoint for UptimeRobot monitoring. Always returns 200."""
    return JSONResponse(content={"status": "ok", "service": "OrchestrAI"}, status_code=200)

@app.post("/log-feedback")
async def log_feedback(request: Request):
    """
    Receive interview feedback from the mock interview page.
    Body: { company, role, questions_faced, confidence_level, difficulty_level }
    Saves to database/interview_feedback.yaml on GitHub.
    """
    try:
        body = await request.json()
        from backend.agents.interview_feedback_agent import append_feedback_entry
        ok = append_feedback_entry({
            "company":          body.get("company", ""),
            "role":             body.get("role", ""),
            "questions_faced":  body.get("questions_faced", []),
            "confidence":       int(body.get("confidence_level", 5)),
            "difficulty":       int(body.get("difficulty_level", 5)),
        })
        if ok:
            return JSONResponse({"status": "ok", "message": "Feedback saved! Skill gaps will update in tomorrow's report."})
        else:
            return JSONResponse({"status": "error", "message": "Save failed — check server logs."}, status_code=500)
    except Exception as exc:
        logger.error("POST /log-feedback error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

@app.get("/", response_class=HTMLResponse)
def index():
    eu = os.getenv("EMAIL_USER", "NOT SET")
    er = os.getenv("EMAIL_RECEIVER", "NOT SET")
    ep = "✅ SET" if os.getenv("EMAIL_PASS") else "❌ NOT SET"
    return f"""
    <html><head><title>OrchestrAI Dashboard</title></head>
    <body style='font-family:sans-serif;max-width:700px;margin:40px auto;padding:20px'>
      <h1>🤖 OrchestrAI Career Intelligence System</h1>
      <p>Your autonomous AI career agent is running on Render.</p>
      <hr/>
      <h3>⚙️ Email Configuration</h3>
      <ul>
        <li><b>EMAIL_USER:</b> {eu}</li>
        <li><b>EMAIL_RECEIVER:</b> {er}</li>
        <li><b>EMAIL_PASS:</b> {ep}</li>
      </ul>
      <hr/>
      <h3>🔧 Actions</h3>
      <p><a href='/test-email' style='background:#4CAF50;color:white;padding:10px 20px;border-radius:5px;text-decoration:none'>✉️ Test Email Now</a></p>
      <p><a href='/trigger' style='background:#2196F3;color:white;padding:10px 20px;border-radius:5px;text-decoration:none'>🚀 Run Pipeline (background)</a></p>
      <p><a href='/trigger-sync' style='background:#FF9800;color:white;padding:10px 20px;border-radius:5px;text-decoration:none'>🔍 Run Pipeline (with error display)</a></p>
    </body></html>
    """

@app.get("/trigger", response_class=HTMLResponse)
def trigger_pipeline(background_tasks: BackgroundTasks):
    logger.info("Manual HTTP trigger: running full pipeline in background...")
    background_tasks.add_task(run_full_pipeline)
    return "<h1>Pipeline Triggered! 🚀</h1><p>The AI agents are running in the background. The email will arrive in your inbox in ~10 minutes.</p><p><a href='/'>← Back to Dashboard</a></p>"

@app.get("/trigger-sync", response_class=HTMLResponse)
def trigger_pipeline_sync():
    """Runs the full pipeline synchronously and shows any errors in browser."""
    logger.info("Sync HTTP trigger: running full pipeline synchronously...")
    try:
        run_full_pipeline()
        return "<h1>Pipeline Completed ✅</h1><p>All agents ran successfully. Check your inbox!</p><p><a href='/'>← Back to Dashboard</a></p>"
    except Exception as e:
        err = traceback.format_exc()
        logger.error("Sync trigger FAILED: %s", err)
        return f"<h1>Pipeline FAILED ❌</h1><pre style='color:red;background:#ffeaea;padding:20px'>{err}</pre>"

@app.get("/test-email", response_class=HTMLResponse)
def test_email_endpoint():
    """Send a quick test email to verify email credentials are working."""
    import smtplib, json, requests as req
    from email.message import EmailMessage

    eu = os.getenv("EMAIL_USER", "")
    ep = os.getenv("EMAIL_PASS", "")
    er = os.getenv("EMAIL_RECEIVER", eu)
    sh = os.getenv("SMTP_HOST", "smtp.gmail.com")
    sp = int(os.getenv("SMTP_PORT", 587))
    resend_key = os.getenv("RESEND_API_KEY", "")

    # ── Try Resend first ──────────────────────────────────────────────────────
    if resend_key:
        try:
            payload = {
                "from": "OrchestrAI <onboarding@resend.dev>",
                "to": [er or eu],
                "subject": "OrchestrAI Test Email 🚀",
                "html": "<h1>OrchestrAI Test 🚀</h1><p>Resend API is working! You will receive the daily reports at this address.</p>",
            }
            resp = req.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                data=json.dumps(payload), timeout=30
            )
            if resp.status_code in (200, 201):
                return f"<h1>✅ Test Email Sent via Resend!</h1><p>Successfully sent to <b>{er or eu}</b>. Check your inbox now!</p><p><a href='/trigger'>Now run the full pipeline →</a></p>"
            else:
                return f"<h1>❌ Resend API Error</h1><p style='color:red'>{resp.status_code}: {resp.text}</p><p>Check your RESEND_API_KEY in Render Environment Variables.</p>"
        except Exception as e:
            return f"<h1>❌ Resend Failed</h1><p style='color:red'>{e}</p>"

    # ── Fall back to SMTP ─────────────────────────────────────────────────────
    if not eu or eu in ("your-gmail@gmail.com", ""):
        return """<h1>❌ Email Not Configured</h1>
        <p>Neither <b>RESEND_API_KEY</b> nor <b>EMAIL_USER</b> is set.</p>
        <h3>Recommended Fix (free, works on Render):</h3>
        <ol>
          <li>Go to <a href='https://resend.com'>resend.com</a> → Sign up free</li>
          <li>Create an API Key</li>
          <li>Add <b>RESEND_API_KEY</b> to your Render Environment Variables</li>
          <li>Add <b>EMAIL_RECEIVER</b> = your Gmail address</li>
          <li>Come back and visit /test-email again</li>
        </ol>"""

    if not ep or ep in ("xxxx-xxxx-xxxx-xxxx", ""):
        return "<h1>❌ App Password Not Set</h1><p><b>EMAIL_PASS</b> is missing. Generate a Gmail App Password at: <a href='https://myaccount.google.com/apppasswords'>myaccount.google.com/apppasswords</a></p>"

    try:
        msg = EmailMessage()
        msg["Subject"] = "OrchestrAI Test Email 🚀"
        msg["From"] = eu
        msg["To"] = er or eu
        msg.set_content("Test email from OrchestrAI. SMTP is working!")
        with smtplib.SMTP(sh, sp) as server:
            server.starttls()
            server.login(eu, ep)
            server.send_message(msg)
        return f"<h1>✅ Test Email Sent via SMTP!</h1><p>Successfully sent to <b>{er or eu}</b>. Check your inbox!</p><p><a href='/trigger'>Now run the full pipeline →</a></p>"
    except Exception as e:
        return f"<h1>❌ SMTP Failed</h1><p style='color:red'><b>Error:</b> {e}</p><p>Render blocks SMTP on free tier. <a href='https://resend.com'>Use Resend instead</a> — it's free!</p>"

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        logger.info("Manual trigger: running full pipeline immediately...")
        from backend.scheduler import run_once_now
        run_once_now(run_full_pipeline)
    else:
        import uvicorn
        port = int(os.environ.get("PORT", "10000"))
        logger.info(f"Starting Uvicorn on 0.0.0.0:{port}")
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
