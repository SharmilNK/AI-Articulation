"""
Sends the generated Word doc via Gmail SMTP.
Requires a Gmail App Password (2FA must be enabled on the sender account).
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date
from config import GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _build_html_body(today_str: str, section_titles: list[str]) -> str:
    items_html = "".join(f"<li>{t}</li>" for t in section_titles)
    return f"""
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto;">
  <h2 style="color: #1A53A1;">AI Articulation Daily Digest — {today_str}</h2>
  <p>Hi there,</p>
  <p>Your daily AI conversation brief is ready. Today's doc covers:</p>
  <ul>{items_html}</ul>
  <p>Open the attached <strong>.docx</strong> file to review your talking points,
  mock conversations, and concept summaries.</p>
  <p style="color: #888; font-size: 12px;">
    Generated automatically by AI-Articulation.<br/>
    Sources: Lenny's Newsletter · Spill the GPTea · Intuitive Autonomy ·
    Enterprise AI Executive · Bridge by Adi Agrawal · Tomorrow Toolbox ·
    Maven Rewind 2025 · Conventional Commits
  </p>
</body>
</html>
"""


def send_digest(doc_path: str) -> bool:
    if not all([GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL]):
        logger.error(
            "Missing email credentials. Set GMAIL_USER, GMAIL_APP_PASSWORD, "
            "and RECIPIENT_EMAIL in your .env file."
        )
        return False

    # Support comma-separated list of recipients
    recipients = [r.strip() for r in RECIPIENT_EMAIL.split(",") if r.strip()]

    today_str = date.today().strftime("%B %d, %Y")
    subject = f"AI Articulation Digest — {today_str}"

    section_titles = [
        "Today's AI Conversation Starters",
        "Recent AI Updates & Your Opinion",
        "Core AI/ML Concepts Explained Simply",
        "AI Roadblocks & Industry Responses",
        "Mock Conversations: Executive & Data Scientist",
        "GitHub & Dev Standards Update",
        "AI Governance Frameworks (NIST · Microsoft · Google)",
        "AI Strategy Frameworks (a16z · MIT Sloan · Stanford HAI)",
        "Enterprise AI Adoption Toolkit",
    ]

    msg = MIMEMultipart("mixed")
    msg["From"] = GMAIL_USER
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    html_body = _build_html_body(today_str, section_titles)
    msg.attach(MIMEText(html_body, "html"))

    # Attach the Word document
    filename = os.path.basename(doc_path)
    try:
        with open(doc_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)
    except FileNotFoundError:
        logger.error("Document not found at %s", doc_path)
        return False

    try:
        logger.info("Connecting to Gmail SMTP...")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        logger.info("Digest emailed to %d recipient(s): %s", len(recipients), ", ".join(recipients))
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. Make sure you're using a Gmail App Password "
            "(not your regular password). See: https://myaccount.google.com/apppasswords"
        )
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", e)
        return False
