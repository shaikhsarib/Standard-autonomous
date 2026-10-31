"""
Email Outreach Module
---------------------
Sends personalized cold emails to discovered businesses.
Tracks sent emails to avoid duplicates.
"""

import json
import os
import smtplib
import ssl
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SENT_LOG_FILE = "outreach_sent.json"


def _load_sent_log() -> list:
    if not os.path.exists(SENT_LOG_FILE):
        return []
    try:
        with open(SENT_LOG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_sent_log(log: list) -> None:
    try:
        with open(SENT_LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)
    except OSError as exc:
        logging.error(f"Could not save sent log: {exc}")


def already_contacted(email: str) -> bool:
    """Check if this email was already contacted."""
    return any(entry.get("email") == email for entry in _load_sent_log())


def send_cold_email(
    to_email: str,
    subject: str,
    body: str,
    business_name: str,
) -> bool:
    """
    Send a cold email via Gmail SMTP.
    Returns True on success.
    """
    if not all([EMAIL_SENDER, EMAIL_PASSWORD]):
        logging.warning("[Email] EMAIL_SENDER or EMAIL_PASSWORD not set. Skipping.")
        return False

    if already_contacted(to_email):
        logging.info(f"[Email] Already contacted {to_email}, skipping.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())

        # Log the sent email
        log = _load_sent_log()
        log.append({
            "email": to_email,
            "business_name": business_name,
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat(),
            "replied": False,
        })
        _save_sent_log(log)

        logging.info(f"[Email] Sent to {to_email} ({business_name})")
        return True

    except Exception as exc:
        logging.error(f"[Email] Failed to send to {to_email}: {exc}")
        return False


def mark_replied(email: str) -> None:
    """Mark an email as replied (used by reply tracker)."""
    log = _load_sent_log()
    for entry in log:
        if entry.get("email") == email:
            entry["replied"] = True
    _save_sent_log(log)


def get_pending_replies() -> list:
    """Return all emails sent but not yet replied."""
    return [e for e in _load_sent_log() if not e.get("replied")]
