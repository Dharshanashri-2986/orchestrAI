import os
import json
import logging
import requests
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("OrchestrAI.DailyEmail")

def send_daily_dashboard_email():
    """
    Generate and send the daily dashboard email.
    Uses Resend API (preferred) or SMTP fallback.
    """
    logger.info("Starting to send daily dashboard email...")
    
    # Render Environment Variables (prioritizing the requested ones)
    resend_key = os.getenv("EMAIL_API_KEY", os.getenv("RESEND_API_KEY", ""))
    email_sender = os.getenv("EMAIL_SENDER", os.getenv("EMAIL_USER", ""))
    email_pass = os.getenv("EMAIL_PASS", "")
    email_receiver = os.getenv("EMAIL_RECEIVER", email_sender)
    
    # Website URL for the button
    website_url = os.getenv("WEBSITE_URL", "https://orchestrai.onrender.com")
    
    # Personalization
    # Assuming EMAIL_USER or EMAIL_RECEIVER might not have a name, 
    # we can use a personalized greeting if available, else a generic one.
    # The requirement gives an example: Hello Dharshanashri,
    # We can hardcode or just use a generic if we don't know the user's name.
    # Let's try to extract from email if no name is provided.
    personal_name = os.getenv("USER_FIRST_NAME", "Dharshanashri")
    
    subject = "[Task Update] AI and Data Science internships list updated"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
        <h2 style="color: #2c3e50;">OrchestrAI</h2>
        <p style="font-size: 16px; color: #555;"><strong>Task update from OrchestrAI</strong></p>
        <p style="font-size: 16px;">Hello {personal_name},</p>
        <p style="font-size: 16px;">
            AI and Data Science internships list updated.<br>
            Your daily career dashboard is ready.
        </p>
        <div style="margin-top: 30px; margin-bottom: 30px;">
            <a href="{website_url}"
               style="background:#10b981;color:white;padding:12px 20px;text-decoration:none;border-radius:6px;font-size: 16px; font-weight: bold; display: inline-block;">
               View Dashboard
            </a>
        </div>
        <p style="font-size: 14px; color: #888;">
            Daily AI & Data Science Internship Update.<br>
            &copy; OrchestrAI
        </p>
    </div>
    """

    if not email_receiver:
        logger.error("No EMAIL_RECEIVER or EMAIL_USER configured.")
        return

    # Try Resend API first
    if resend_key:
        logger.info("Using Resend API to send daily email...")
        try:
            payload = {
                "from": "OrchestrAI <onboarding@resend.dev>",
                "to": [email_receiver],
                "subject": subject,
                "html": html_content,
            }
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json"
                },
                data=json.dumps(payload),
                timeout=30
            )
            if resp.status_code in (200, 201):
                logger.info("Successfully sent daily email via Resend to %s", email_receiver)
                return True
            else:
                logger.error("Resend API failed: %s - %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("Resend API exception: %s", e)

    # Fallback to SMTP
    if email_sender and email_pass:
        logger.info("Using SMTP to send daily email...")
        try:
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", 587))

            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = email_sender
            msg["To"] = email_receiver
            
            # Using set_content with subtype='html'
            msg.set_content(html_content, subtype='html')

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(email_sender, email_pass)
                server.send_message(msg)
            
            logger.info("Successfully sent daily email via SMTP to %s", email_receiver)
            return True
        except Exception as e:
            logger.error("SMTP failed: %s", e)
            return False

    logger.error("Email not sent: neither Resend API nor SMTP credentials worked.")
    return False
