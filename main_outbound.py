"""
Main Outbound Lead Generation Pipeline
---------------------------------------
Usage:
  python main_outbound.py --location "Delhi" --types "restaurant,salon,gym"
  python main_outbound.py --location "Mumbai" --check-replies
  python main_outbound.py --location "Pune" --dry-run
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from services.llm_client import ProductionLLMClient
from outreach.google_discovery import discover_businesses
from outreach.gmaps_scraper import gmaps_discover_businesses
from outreach.pain_point_analyzer import analyze_business
from outreach.email_outreach import send_cold_email, get_pending_replies, mark_replied
from outreach.reply_tracker import check_for_replies
from outreach.email_finder import find_email_for_business
from delivery.delivery_module import send_telegram

# All business categories — local to popular
ALL_BUSINESS_TYPES = [
    # Food
    "restaurant", "dhaba", "bakery", "catering", "sweet shop",
    "cafe", "tiffin service", "hotel",
    # Beauty & Wellness
    "salon", "spa", "gym", "yoga", "physiotherapy",
    # Health
    "clinic", "dental clinic", "medical store", "pathology lab",
    # Education
    "coaching center", "tuition", "computer training",
    "dance classes", "music classes", "driving school",
    # Professional
    "ca firm", "lawyer", "event management", "travel agent",
    "interior designer", "digital marketing", "web designer",
    "software company", "architect",
    # Retail
    "boutique", "jewellery shop", "mobile repair", "tailor",
    "hardware store", "furniture shop", "optical shop",
    # Home Services
    "plumber", "electrician", "carpenter", "painter",
    "pest control", "home cleaning", "ac repair", "packers movers",
    # Auto
    "automobile workshop", "car service", "bike repair",
    # Creative
    "photographer", "videographer", "graphic designer",
]

# Sensible default — covers most common no-website business types
DEFAULT_TYPES = [
    "restaurant", "salon", "gym", "clinic", "coaching center",
    "bakery", "boutique", "photographer", "ca firm", "event management",
    "plumber", "electrician", "mobile repair", "automobile workshop",
    "travel agent",
]

# Mumbai — only categories verified working on Sulekha Mumbai
MUMBAI_TYPES = [
    # Food & Hospitality
    "restaurant", "hotel", "banquet hall", "sweet shop", "catering",
    # Health & Medical
    "clinic", "dental clinic", "medical store", "pathology lab", "gym", "yoga",
    # Education
    "coaching center", "tuition", "driving school",
    # Professional
    "ca firm", "event management", "travel agent",
    "interior designer", "photographer",
    # Retail & Repair
    "salon", "boutique", "jewellery shop", "tailor",
    "hardware store", "mobile repair",
    # Home Services
    "plumber", "electrician", "pest control",
    "packers movers", "ac repair",
    # Automobile
    "automobile workshop",
]


OUTBOUND_LEADS_FILE = "outbound_leads.json"


def _load_outbound_leads() -> list:
    if not os.path.exists(OUTBOUND_LEADS_FILE):
        return []
    try:
        with open(OUTBOUND_LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_outbound_leads(leads: list) -> None:
    with open(OUTBOUND_LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)


def _send_lead_to_telegram(business: dict, analysis: dict, replied: bool = False) -> None:
    """Format and send a discovered/replied lead to Telegram."""
    status = "REPLIED ✅" if replied else "DISCOVERED 🔍"
    pain_points_text = "\n".join([f"  • {p}" for p in analysis.get("pain_points", [])])

    lead_data = {
        "name": business.get("name", "-"),
        "website": business.get("source_url", "-"),
        "budget": "-",
        "email": business.get("email", "-"),
        "extra": (
            f"\n📍 Location: {business.get('location', '-')}"
            f"\n🏪 Type: {business.get('business_type', '-')}"
            f"\n📊 Status: {status}"
            f"\n📞 Phone: {business.get('phone', '-')}"
            f"\n❌ Has Website: {'Yes' if business.get('has_website') else 'No'}"
            f"\n\n🔥 Pain Points:\n{pain_points_text}"
            f"\n\n💡 Loss: {analysis.get('business_loss', '-')}"
        )
    }

    import html
    def _s(v): return str(v) if v else "-"

    message = (
        f"<b>🎯 Outbound Lead — {status}</b>\n\n"
        f"<b>Name:</b> {html.escape(_s(lead_data['name']))}\n"
        f"<b>Email:</b> {html.escape(_s(lead_data['email']))}\n"
        f"<b>Phone:</b> {html.escape(_s(business.get('phone')))}\n"
        f"<b>Location:</b> {html.escape(_s(business.get('location')))}\n"
        f"<b>Business Type:</b> {html.escape(_s(business.get('business_type')))}\n"
        f"<b>Has Website:</b> {'Yes' if business.get('has_website') else 'No ❌'}\n\n"
        f"<b>Pain Points:</b>\n{html.escape(pain_points_text)}\n\n"
        f"<b>Daily Loss:</b> {html.escape(_s(analysis.get('business_loss')))}\n\n"
        f"<b>Email Subject:</b> {html.escape(_s(analysis.get('email_subject')))}"
    )

    import requests as _req
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not all([token, chat_id]):
        logging.warning("Telegram not configured — printing lead instead:")
        print(message)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = _req.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
        if resp.ok:
            logging.info(f"Lead sent to Telegram: {business.get('name')}")
        else:
            logging.error(f"Telegram failed: {resp.text}")
    except Exception as exc:
        logging.error(f"Telegram error: {exc}")


def run_discovery(location: str, business_types: list, limit: int, dry_run: bool, use_gmaps: bool = False) -> None:
    """
    Discover businesses → analyze pain points → send cold emails → notify Telegram.
    Only processes businesses that have NO website.
    """
    logging.info(f"Starting discovery | location={location!r} | source={'Google Maps' if use_gmaps else 'Sulekha'} | types={len(business_types)}")

    try:
        llm_client = ProductionLLMClient()
    except Exception as exc:
        logging.error(f"LLM init failed: {exc}")
        return

    # Source: Google Maps (Selenium) or Sulekha
    if use_gmaps:
        businesses = gmaps_discover_businesses(
            city=location,
            business_types=business_types,
            limit_per_type=limit,
        )
    else:
        businesses = discover_businesses(
            location=location,
            business_types=business_types,
            limit_per_type=limit,
        )

    if not businesses:
        logging.warning("No businesses found.")
        return

    # Filter: only no-website businesses
    no_web = [b for b in businesses if not b.get("has_website")]
    logging.info(f"Found {len(businesses)} total | {len(no_web)} without website — processing these only")

    outbound_leads = _load_outbound_leads()
    existing_names = {b.get("name", "").lower() for b in outbound_leads}

    for business in no_web:
        name = business.get("name", "")
        if name.lower() in existing_names:
            logging.info(f"Already processed: {name}, skipping.")
            continue

        # Analyze pain points — uses fallback if LLM quota exceeded
        analysis = analyze_business(business, llm_client)
        business["analysis"] = analysis
        business["discovered_at"] = datetime.utcnow().isoformat()

        # Send to Telegram immediately
        _send_lead_to_telegram(business, analysis, replied=False)

        # Find email and send (skip if dry_run)
        if not dry_run:
            if not business.get("email"):
                found_email = find_email_for_business(name, business.get("location", location))
                if found_email:
                    business["email"] = found_email

            sent = False
            if business.get("email"):
                sent = send_cold_email(
                to_email=business["email"],
                subject=analysis.get("email_subject", "Aapke business ke liye ek suggestion"),
                body=analysis.get("email_body", ""),
                business_name=name,
            )
            business["email_sent"] = sent
            time.sleep(3)  # avoid Gmail rate limit
        else:
            if dry_run:
                logging.info(f"[DryRun] Would send email to: {business.get('email')} — {name}")
            business["email_sent"] = False

        outbound_leads.append(business)
        existing_names.add(name.lower())

        _save_outbound_leads(outbound_leads)
        time.sleep(2)

    logging.info(f"Discovery phase complete. Processed {len(businesses)} businesses.")


def run_reply_check() -> None:
    """
    Phase 2: Check for email replies → mark as qualified → send to Telegram.
    """
    logging.info("Checking for email replies...")
    pending = get_pending_replies()
    pending_emails = [e["email"] for e in pending]

    if not pending_emails:
        logging.info("No pending emails to check replies for.")
        return

    replies = check_for_replies(pending_emails)

    if not replies:
        logging.info("No new replies found.")
        return

    # Load outbound leads to enrich reply data
    outbound_leads = _load_outbound_leads()
    leads_by_email = {b.get("email", "").lower(): b for b in outbound_leads}

    for reply in replies:
        sender = reply["from_email"].lower()
        mark_replied(sender)

        business = leads_by_email.get(sender, {
            "name": reply.get("from_name", sender),
            "email": sender,
            "business_type": "unknown",
            "location": "-",
        })
        analysis = business.get("analysis", {
            "pain_points": [],
            "business_loss": "-",
            "email_subject": "-",
        })

        # Add reply details
        analysis["reply_preview"] = reply.get("body_preview", "")

        logging.info(f"Sending replied lead to Telegram: {business.get('name')}")
        _send_lead_to_telegram(business, analysis, replied=True)


def main():
    parser = argparse.ArgumentParser(description="Outbound Lead Generation Pipeline")
    parser.add_argument("--location", type=str, default="Delhi", help="City to search in")
    parser.add_argument(
        "--types",
        type=str,
        default="",
        help="Comma-separated business types (leave empty for default 15 types)",
    )
    parser.add_argument(
        "--all-types",
        action="store_true",
        help="Run across ALL business categories (~40 types)",
    )
    parser.add_argument(
        "--mumbai",
        action="store_true",
        help="Run Mumbai preset — 30 categories verified on Sulekha Mumbai",
    )
    parser.add_argument(
        "--gmaps",
        action="store_true",
        help="Use Google Maps (Selenium browser) instead of Sulekha — more accurate, slower",
    )
    parser.add_argument("--limit", type=int, default=5, help="Businesses per type")
    parser.add_argument("--check-replies", action="store_true", help="Check inbox for replies only")
    parser.add_argument("--dry-run", action="store_true", help="Discover and analyze, don't send emails")
    args = parser.parse_args()

    if args.check_replies:
        run_reply_check()
        return

    if args.mumbai:
        types = MUMBAI_TYPES
        if not args.location or args.location == "Delhi":
            args.location = "Mumbai"
        logging.info(f"Mumbai preset: {len(types)} business types in {args.location}")
    elif args.all_types:
        types = ALL_BUSINESS_TYPES
        logging.info(f"Running ALL {len(types)} business types")
    elif args.types:
        types = [t.strip() for t in args.types.split(",") if t.strip()]
    else:
        types = DEFAULT_TYPES
        logging.info(f"Using default {len(types)} business types")

    run_discovery(args.location, types, args.limit, args.dry_run, use_gmaps=args.gmaps)


if __name__ == "__main__":
    main()
