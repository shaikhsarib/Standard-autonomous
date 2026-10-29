"""
Reply Tracker
-------------
Checks Gmail inbox via IMAP for replies to cold emails.
When a reply is found, marks the lead as qualified and
sends it to Telegram.
"""

import imaplib
import email
import os
import logging
from email.header import decode_header
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = "imap.gmail.com"


def _decode_header_value(value: str) -> str:
    """Safely decode email header."""
    decoded_parts = decode_header(value)
    result = ""
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += part
    return result


def check_for_replies(pending_emails: List[str]) -> List[Dict[str, Any]]:
    """
    Check Gmail inbox for replies from businesses we contacted.
    Returns list of businesses that replied.
    
    pending_emails: list of email addresses we sent to
    """
    if not all([EMAIL_SENDER, EMAIL_PASSWORD]):
        logging.warning("[ReplyTracker] Email credentials not set.")
        return []

    if not pending_emails:
        return []

    replies_found: List[Dict[str, Any]] = []

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_SENDER, EMAIL_PASSWORD)
        mail.select("inbox")

        # Search for unread emails
        _, msg_ids = mail.search(None, "UNSEEN")

        for msg_id in msg_ids[0].split():
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_header = _decode_header_value(msg.get("From", ""))
            subject = _decode_header_value(msg.get("Subject", ""))

            # Extract sender email
            sender_email = None
            if "<" in from_header and ">" in from_header:
                sender_email = from_header.split("<")[1].split(">")[0].strip()
            else:
                sender_email = from_header.strip()

            # Check if this is a reply from someone we contacted
            if sender_email and sender_email.lower() in [e.lower() for e in pending_emails]:
                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

                replies_found.append({
                    "from_email": sender_email,
                    "from_name": from_header,
                    "subject": subject,
                    "body_preview": body[:300],
                })
                logging.info(f"[ReplyTracker] Reply found from: {sender_email}")

        mail.logout()

    except Exception as exc:
        logging.error(f"[ReplyTracker] IMAP error: {exc}")

    return replies_found
