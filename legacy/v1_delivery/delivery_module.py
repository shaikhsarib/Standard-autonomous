import json
import os
import smtplib
import ssl
from email.mime.text import MIMEText
import requests
import html
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WHATSAPP_RECEIVER = os.getenv("WHATSAPP_NUMBER")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

LEADS_FILE = "actionable_leads.json"


def _s(value) -> str:
    """Coerce any value to a safe string (never None/empty)."""
    return str(value) if value is not None else "-"


def load_actionable_leads() -> list:
    """Load leads from the JSON file."""
    if not os.path.exists(LEADS_FILE):
        return []
    try:
        with open(LEADS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_lead_to_file(lead_data: dict) -> bool:
    """Append a lead to the JSON file; returns True on success."""
    leads = load_actionable_leads()
    leads.append(lead_data)
    try:
        with open(LEADS_FILE, "w") as f:
            json.dump(leads, f, indent=4)
        return True
    except OSError as exc:
        logging.error(f"[File] Save failed: {exc}")
        return False


def send_telegram(lead_data: dict) -> bool:
    """Send lead details via Telegram (HTML-escaped, None-safe)."""
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logging.warning("[Telegram] Token or Chat ID missing. Skipping.")
        return False

    esc_name = html.escape(_s(lead_data.get("name")))
    esc_website = html.escape(_s(lead_data.get("website")))
    esc_budget = html.escape(_s(lead_data.get("budget")))
    esc_email = html.escape(_s(lead_data.get("email")))

    message = (
        "<b>New Lead Generated</b>\n\n"
        f"<b>Name:</b> {esc_name}\n"
        f"<b>Website:</b> {esc_website}\n"
        f"<b>Budget:</b> {esc_budget}\n"
        f"<b>Email:</b> {esc_email}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.ok:
            logging.info("Successfully sent lead to Telegram.")
            return True
        logging.error(f"[Telegram] {resp.status_code} - {resp.text}")
        return False
    except Exception as exc:
        logging.error(f"[Telegram] Request failed: {exc}")
        return False


def send_email(lead_data: dict) -> bool:
    """Send lead details via Email (None-safe)."""
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        logging.warning("[Email] Credentials missing. Skipping.")
        return False

    name = _s(lead_data.get("name"))
    website = _s(lead_data.get("website"))
    budget = _s(lead_data.get("budget"))
    email = _s(lead_data.get("email"))

    subject = f"New Lead Generated: {name}"
    body = f"Lead Details:\n\nName: {name}\nWebsite: {website}\nBudget: {budget}\nEmail: {email}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        logging.info("[Email] Sent successfully.")
        return True
    except Exception as exc:
        logging.error(f"[Email] Failed: {exc}")
        return False


def send_whatsapp(lead_data: dict) -> bool:
    """Send lead details via WhatsApp using Twilio (None-safe)."""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, WHATSAPP_RECEIVER]):
        logging.warning("[WhatsApp] Twilio config missing. Skipping.")
        return False

    name = _s(lead_data.get("name"))
    email = _s(lead_data.get("email"))
    budget = _s(lead_data.get("budget"))

    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_FROM}",
            body=f"New Lead: {name}, Email: {email}, Budget: {budget}",
            to=f"whatsapp:{WHATSAPP_RECEIVER}",
        )
        logging.info(f"[WhatsApp] Sent via Twilio. SID: {message.sid}")
        return True
    except Exception as exc:
        logging.error(f"[WhatsApp] Failed: {exc}")
        return False


def lead_exists(email: str, name: str) -> bool:
    """Check whether a lead with this email+name already exists."""
    for lead in load_actionable_leads():
        if lead.get("email") == email and lead.get("name") == name:
            return True
    return False


def deliver_lead(lead_data: dict) -> dict:
    """Deliver lead through all configured channels and return per-channel status."""
    status = {"file": False, "telegram": False, "email": False, "whatsapp": False}

    email = lead_data.get("email", "")
    name = lead_data.get("name", "")

    if not lead_exists(email, name):
        status["file"] = save_lead_to_file(lead_data)
        if status["file"]:
            logging.info("[File] Saved successfully.")
    else:
        logging.info("[File] Duplicate lead — skipping save.")
        status["file"] = True  # already exists, treat as success

    status["telegram"] = send_telegram(lead_data)
    status["email"] = send_email(lead_data)
    status["whatsapp"] = send_whatsapp(lead_data)

    logging.info(f"Delivery summary: {json.dumps(status, indent=2)}")
    return status
