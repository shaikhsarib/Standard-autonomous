import html
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from config.settings import settings
from src.models.lead import Lead, OutreachChannel

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    def __init__(self):
        pass

    def send_telegram(self, message: str) -> bool:
        bot_token = settings.telegram_bot_token
        chat_id = settings.telegram_chat_id
        if not bot_token or not chat_id:
            logger.info("[Telegram] Bot token or Chat ID not configured. Skipping.")
            return False

        try:
            import requests
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            res = requests.post(url, json=payload, timeout=8)
            return res.ok
        except Exception as e:
            logger.error(f"[Telegram] Failed sending notification: {e}")
            return False

    def send_whatsapp(self, to_phone: str, message: str) -> bool:
        sid = settings.twilio_account_sid
        token = settings.twilio_auth_token
        from_number = settings.twilio_whatsapp_from
        
        if not all([sid, token, from_number]):
            logger.info(f"[WhatsApp] Twilio credentials not fully configured. (Mock delivery to {to_phone})")
            logger.info(f"[WhatsApp Preview] -> {message}")
            return True

        try:
            from twilio.rest import Client
            client = Client(sid, token)
            formatted_to = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
            formatted_from = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"

            msg = client.messages.create(
                body=message,
                from_=formatted_from,
                to=formatted_to
            )
            logger.info(f"[WhatsApp] Message sent successfully. SID: {msg.sid}")
            return True
        except Exception as e:
            logger.error(f"[WhatsApp] Delivery failed to {to_phone}: {e}")
            return False

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        sender = settings.email_sender
        pwd = settings.email_password

        if not sender or not pwd:
            logger.info(f"[Email] SMTP credentials not configured. (Mock email to {to_email}: {subject})")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = to_email
            
            # Plain text body
            msg.attach(MIMEText(body, "plain", "utf-8"))

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender, pwd)
                server.sendmail(sender, to_email, msg.as_string())

            logger.info(f"[Email] Sent cold email to {to_email}")
            return True
        except Exception as e:
            logger.error(f"[Email] Failed sending to {to_email}: {e}")
            return False

    def notify_lead_captured(self, lead: Lead) -> None:
        p = lead.profile
        html_msg = (
            f"<b>🚀 New Qualified Lead Captured!</b>\n\n"
            f"<b>Company:</b> {html.escape(p.company_name)}\n"
            f"<b>Type:</b> {html.escape(p.business_type)}\n"
            f"<b>Location:</b> {html.escape(p.location)}\n"
            f"<b>Phone:</b> {html.escape(p.phone or 'N/A')}\n"
            f"<b>Email:</b> {html.escape(p.email or lead.contact_email or 'N/A')}\n"
            f"<b>Budget:</b> {html.escape(lead.budget or 'N/A')}\n"
            f"<b>Interest Level:</b> {html.escape(lead.interest_level or 'High')}\n"
            f"<b>Summary:</b> {html.escape(lead.summary or 'Automated match')}\n"
        )
        self.send_telegram(html_msg)

    # Aliases
    send_whatsapp_twilio = send_whatsapp
    send_smtp_email = send_email
    send_telegram_notification = notify_lead_captured

dispatcher = NotificationDispatcher()
delivery_dispatcher = dispatcher
