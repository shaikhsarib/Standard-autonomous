"""
Domain-Specific Playbooks for High-Value Commercial Verticals:
1. Logistics, Freight & Transportation
2. Event Management, Venues & Catering
3. Local Businesses & Direct Services (Retail, Clinics, Salons, Home Services)
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class BusinessVertical(str, Enum):
    LOGISTICS_TRANSPORT = "logistics_transport"
    EVENT_MANAGEMENT = "event_management"
    LOCAL_SERVICES = "local_services"
    GENERAL = "general"

class VerticalPlaybook(BaseModel):
    vertical: BusinessVertical
    display_title: str
    target_problems: List[str]
    quantified_loss_template: str
    whatsapp_pitch_template: str
    email_subject_template: str
    email_body_template: str
    hermes_objections: Dict[str, str]

LOGISTICS_PLAYBOOK = VerticalPlaybook(
    vertical=BusinessVertical.LOGISTICS_TRANSPORT,
    display_title="Logistics, Freight & Fleet Transportation",
    target_problems=[
        "Paying 15-25% broker margins on freight spot loads",
        "Slow quote turnaround: Shippers abandon inquiries if quote takes >15 minutes",
        "Manual phone & WhatsApp driver dispatch causing coordination bottlenecks",
        "Lack of instant mobile freight rate estimator and shipment status bot"
    ],
    quantified_loss_template="Losing 15-20% margin to freight brokers and ~8-12 spot loads weekly due to delayed manual quote turnaround",
    whatsapp_pitch_template=(
        "Hi team {company}, saw your fleet operations in {location}! "
        "Shippers book whoever quotes rates within 5 mins. We build instant WhatsApp freight calculators & direct driver dispatch bots so you skip 20% broker fees. "
        "Open to a 2-min video preview?"
    ),
    email_subject_template="Automating direct shipper quotes for {company} (skip 18% broker cuts)",
    email_body_template=(
        "Hi Team {company},\n\n"
        "I was checking out commercial freight and transport operators in {location} and came across your business.\n\n"
        "The #1 bottleneck in freight right now is quote turnaround time: shippers searching for trucks request 3 quotes and book the first one who responds within 15 minutes. "
        "We build direct WhatsApp freight rate estimators and automated dispatch bots that capture shippers instantly and help fleet operators bypass 15-25% broker commissions.\n\n"
        "Would you be open to a 5-minute screen share this week to see how this works for your lane routes?\n\n"
        "Warm regards,\n"
        "Freight Automation & Tech Team"
    ),
    hermes_objections={
        "broker_network": (
            "Understood! Keep your existing broker network for baseline volume. "
            "Our automated WhatsApp rate bot is designed to capture 100% of direct repeat shippers who search for {company} online—giving you direct freight at full margin without giving away 18%."
        ),
        "fleet_size": (
            "Whether you manage 5 trucks or 50, manual quote calculation ties up your dispatchers on the phone for hours. "
            "Our rate bot instantly calculates mileage, toll, and weight tiers 24/7 so your team only talks to pre-qualified shippers ready to load."
        ),
        "rates_fluctuate": (
            "Exactly why static PDF rate sheets don't work! Our tool lets you update base per-km diesel rates in a simple spreadsheet, and the WhatsApp bot immediately quotes shippers with live accurate pricing."
        )
    }
)

EVENT_MANAGEMENT_PLAYBOOK = VerticalPlaybook(
    vertical=BusinessVertical.EVENT_MANAGEMENT,
    display_title="Event Management, Venues & Catering",
    target_problems=[
        "65%+ of event inquiries happen between 7 PM - 11 PM when offices are closed",
        "No real-time date availability checker causing prospective clients to call competitors",
        "Slow RFP response times: couples & corporate planners compare 4-5 venues simultaneously",
        "Manual brochure emailing with 50%+ bounce rate on PDF downloads"
    ],
    quantified_loss_template="Losing 40-50% of high-intent wedding and corporate event inquiries arriving after-hours without instant date & package confirmation",
    whatsapp_pitch_template=(
        "Hi team {company}, love your events in {location}! "
        "Over 65% of event planners search venues after 8 PM. We build automated WhatsApp date-checkers & instant package quote bots that double site visit bookings. "
        "Can I share a 1-min live demo?"
    ),
    email_subject_template="Capturing after-hours event bookings for {company}",
    email_body_template=(
        "Hi Team {company},\n\n"
        "I was admiring your event portfolio and venue setups in {location}.\n\n"
        "Data across premier event venues shows that over 65% of high-budget inquiries occur on mobile between 7 PM and 11 PM. "
        "When prospective clients can't immediately check date availability or pricing tiers, they submit RFPs to 3 competitor venues.\n\n"
        "We build branded WhatsApp booking bots that instantly answer date availability, qualify guest counts/budget tiers, and auto-book venue walk-throughs directly into your calendar.\n\n"
        "Would you be open to a 5-minute walkthrough of a live prototype this Wednesday?\n\n"
        "Warm regards,\n"
        "Event Tech & Booking Team"
    ),
    hermes_objections={
        "word_of_mouth": (
            "Word of mouth is undeniably the best source! But even word-of-mouth referrals look up your website or Instagram at 9 PM on their phones. "
            "If they hit a static page with no date checker, 60% delay contacting and often end up booking another venue with instant answers."
        ),
        "custom_events": (
            "Every luxury wedding or corporate gala is unique! That's why the bot doesn't make the final booking—it qualifies the 3 core criteria (Date, Guest Count, Budget Tier) and immediately books a 15-minute consultation with your lead planner."
        ),
        "too_busy": (
            "That's the best time to automate! When you're managing events on-site on weekends, you shouldn't have to manually answer 20 repetitive 'Is Dec 12 available?' messages. The bot handles inquiries while you run the floor."
        )
    }
)

LOCAL_SERVICES_PLAYBOOK = VerticalPlaybook(
    vertical=BusinessVertical.LOCAL_SERVICES,
    display_title="Local SMBs, Clinics, Salons & Direct Services",
    target_problems=[
        "Paying 20-30% platform commissions on repeat customers to aggregators",
        "High telephone abandonment rate during peak working hours",
        "No direct mobile booking engine on Google Maps profile or website",
        "Unanswered after-hours customer queries lost to nearby competitors"
    ],
    quantified_loss_template="Losing 20-30% margin on aggregator commissions and ~15-25 direct walk-in/call appointments weekly",
    whatsapp_pitch_template=(
        "Hi team {company}, noticed you're doing great work in {location}! "
        "We build direct WhatsApp booking systems so you keep 100% of customer margin instead of paying 25% aggregator cuts. "
        "Open to a 2-min demo?"
    ),
    email_subject_template="Idea for {company}'s direct customer bookings (cut commission)",
    email_body_template=(
        "Hi Team {company},\n\n"
        "I was looking at top-rated local services in {location} and came across your profile.\n\n"
        "Many local operators lose 20-30% of their net profits to platform aggregators on repeat customers who already know their brand. "
        "We help businesses launch 1-click WhatsApp booking engines and missed-call text-back automations that convert local Google searchers directly into confirmed appointments without middleman cuts.\n\n"
        "Would you be open to a quick 5-min demo this week to see how it works?\n\n"
        "Warm regards,\n"
        "Local Growth & Automation Team"
    ),
    hermes_objections={
        "on_aggregators": (
            "Aggregators are great for brand-new customer discovery! But you shouldn't pay 25% commission on repeat clients or people who searched for {company} directly on Google. Direct WhatsApp booking keeps that entire 25% in your pocket."
        ),
        "have_whatsapp": (
            "Having a standard WhatsApp number is a great start! But when clients message after closing or during busy hours, waiting 2 hours for a reply loses the sale. Our automated bot confirms appointments and answers FAQs instantly in under 3 seconds."
        ),
        "not_tech_savvy": (
            "You don't need any technical skills at all. The client simply chats on WhatsApp as normal, and confirmed bookings sync straight to your Google Calendar or phone."
        )
    }
)

PLAYBOOKS: Dict[BusinessVertical, VerticalPlaybook] = {
    BusinessVertical.LOGISTICS_TRANSPORT: LOGISTICS_PLAYBOOK,
    BusinessVertical.EVENT_MANAGEMENT: EVENT_MANAGEMENT_PLAYBOOK,
    BusinessVertical.LOCAL_SERVICES: LOCAL_SERVICES_PLAYBOOK,
    BusinessVertical.GENERAL: LOCAL_SERVICES_PLAYBOOK,
}

def detect_vertical(business_type: str, company_name: str = "") -> BusinessVertical:
    """Classifies business into one of the specialized commercial verticals."""
    text = f"{business_type} {company_name}".lower()

    # Logistics keywords
    logistics_keywords = [
        "logistic", "freight", "transport", "truck", "fleet", "cargo", 
        "packer", "mover", "courier", "shipping", "warehouse", "supply chain",
        "carrier", "trailer", "haul", "express cargo"
    ]
    if any(k in text for k in logistics_keywords):
        return BusinessVertical.LOGISTICS_TRANSPORT

    # Event keywords
    event_keywords = [
        "event", "wedding", "venue", "banquet", "cater", "party", "hall",
        "decorator", "convention", "marriage", "resort", "mandap", "dj", "planner"
    ]
    if any(k in text for k in event_keywords):
        return BusinessVertical.EVENT_MANAGEMENT

    # Local SMB keywords
    local_keywords = [
        "clinic", "dental", "dentist", "doctor", "hospital", "salon", "spa", 
        "restaurant", "cafe", "dhaba", "dining", "bar", "bakery", "auto", 
        "repair", "garage", "mechanic", "plumber", "electrician", "gym", "fitness",
        "retail", "boutique", "cleaning", "pest control"
    ]
    if any(k in text for k in local_keywords):
        return BusinessVertical.LOCAL_SERVICES

    return BusinessVertical.GENERAL

def get_playbook(vertical: BusinessVertical) -> VerticalPlaybook:
    return PLAYBOOKS.get(vertical, LOCAL_SERVICES_PLAYBOOK)
