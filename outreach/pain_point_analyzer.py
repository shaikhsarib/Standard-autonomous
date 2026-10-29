"""
Pain Point Analyzer
-------------------
Uses Gemini to analyze a business and generate:
  - Specific pain points based on business type
  - A personalized cold email pitch
  - A short WhatsApp/SMS message
"""

import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Pain points by business type (fallback if LLM fails)
PAIN_POINTS_MAP = {
    "restaurant": [
        "No online ordering — losing orders to Zomato/Swiggy commission (30%)",
        "No table reservation system — missed bookings during peak hours",
        "No loyalty program — customers go to competitor next time",
    ],
    "dhaba": [
        "No digital menu — customers don't know what's available today",
        "No WhatsApp ordering — missing delivery opportunities",
        "Not visible on Google Maps — nearby customers can't find you",
    ],
    "salon": [
        "No online appointment booking — staff wastes 2hrs/day on phone calls",
        "High no-show rate — no automated reminder system",
        "No digital portfolio to attract new clients on Instagram/Google",
    ],
    "spa": [
        "No online slot booking — losing customers who don't want to call",
        "No membership management — manual tracking on paper/diary",
        "No customer retention system — clients don't come back",
    ],
    "gym": [
        "No membership management software — tracking on paper/diary",
        "No automated fee reminder — members forget, revenue delayed",
        "No workout/diet tracking app — members switch to gyms that have apps",
    ],
    "yoga": [
        "No online class booking — students call or message individually",
        "No attendance/payment tracking — manual and error-prone",
        "No recorded session library — losing students who want flexibility",
    ],
    "clinic": [
        "No online appointment — long queues, patients go elsewhere",
        "No digital patient records — finding old prescriptions wastes time",
        "No automated reminder — high no-show rate",
    ],
    "dental clinic": [
        "No online appointment booking — receptionist overloaded",
        "Patients forget follow-up appointments — no reminder system",
        "No visible reviews/portfolio online — losing new patients",
    ],
    "medical store": [
        "No inventory management — overstocking or stockouts daily",
        "No prescription reminder for repeat customers",
        "No home delivery tracking — losing to online pharmacies",
    ],
    "pathology lab": [
        "No online report delivery — patients visit twice unnecessarily",
        "No online booking for tests — losing walk-in customers",
        "No automated result notification via SMS/WhatsApp",
    ],
    "coaching center": [
        "No student attendance/fee tracking — done manually on registers",
        "No doubt-solving platform — students go to YouTube instead",
        "No online batch — losing students who moved cities",
    ],
    "tuition": [
        "No fee management — chasing parents for payments manually",
        "No student progress report system — parents feel unattended",
        "No online classes option — losing students post-COVID",
    ],
    "computer training": [
        "No course catalog/brochure online — students don't know what you offer",
        "No placement portal — alumni don't refer others",
        "No student tracking/certificate system",
    ],
    "driving school": [
        "No online slot booking — phone always busy",
        "No lesson tracking/progress report for students",
        "Not visible on Google — losing new inquiries daily",
    ],
    "ca firm": [
        "No client portal — documents shared over WhatsApp messily",
        "No automated deadline reminder for GST/ITR filings",
        "No online presence — losing referral clients who Google first",
    ],
    "lawyer": [
        "No case management system — tracking on files/diary",
        "No online appointment — clients can't book consultation easily",
        "No visible profile/reviews — losing clients to lawyers with websites",
    ],
    "event management": [
        "No portfolio website — losing inquiries to competitors with websites",
        "No online quotation/booking system — manual follow-ups delayed",
        "No vendor management tool — coordination done over WhatsApp",
    ],
    "travel agent": [
        "No itinerary builder/sender — sending packages on WhatsApp messily",
        "No booking tracking system — manual spreadsheets error-prone",
        "No reviews/testimonials page — losing trust vs. MakeMyTrip",
    ],
    "interior designer": [
        "No portfolio website — losing high-value clients who Google first",
        "No project management tool — client updates via WhatsApp",
        "No 3D visualization sharing — clients can't see designs properly",
    ],
    "digital marketing": [
        "No case study/results page — hard to convince new clients",
        "No client reporting dashboard — sending screenshots on WhatsApp",
        "Not ranking on Google themselves — credibility issue",
    ],
    "web designer": [
        "No strong portfolio site — losing premium clients",
        "No automated proposal/invoice system",
        "No testimonials/reviews page",
    ],
    "software company": [
        "No clear product page — prospects confused about what you build",
        "No lead capture form — losing interested visitors",
        "No case studies — hard to close enterprise deals",
    ],
    "boutique": [
        "No online catalog — customers can't browse before visiting",
        "No WhatsApp ordering — missing sales from existing customers",
        "Not on Google Maps with photos — losing walk-in customers",
    ],
    "jewellery shop": [
        "No online catalog — customers go to Tanishq/Malabar with websites",
        "No appointment system for customization orders",
        "No digital billing/inventory — manual tracking slow",
    ],
    "mobile repair": [
        "No online job tracking — customers call repeatedly for status",
        "No service price list online — customers go to competitor who has it",
        "Not visible on Google — losing nearby customers",
    ],
    "tailor": [
        "No measurement/order tracking system — losing orders in peak season",
        "No online booking — customers don't know if you're available",
        "No digital catalog of designs — showing physical samples inefficient",
    ],
    "hardware store": [
        "No online catalog/price list — customers visit competitor with better info",
        "No inventory system — manual billing slow, errors happen",
        "No bulk order/contractor portal — missing B2B revenue",
    ],
    "plumber": [
        "No online booking — customers call 5 plumbers and go with first responder",
        "No service area visibility on Google — losing nearby jobs",
        "No invoice/payment tracking — chasing payments manually",
    ],
    "electrician": [
        "Not visible on Google — losing urgent calls to listed competitors",
        "No online price list — customers don't know your rates",
        "No job tracking/invoice system",
    ],
    "pest control": [
        "No online booking — customers search and book competitors instantly",
        "No service reminder for yearly contracts — losing repeat business",
        "No digital service report — unprofessional vs. big companies",
    ],
    "home cleaning": [
        "No subscription/recurring booking system — daily manual scheduling",
        "No online verification/trust badges — customers afraid to let strangers in",
        "No feedback system — losing repeat customers silently",
    ],
    "ac repair": [
        "No AMC (annual maintenance contract) management system",
        "Not visible on Google — losing urgent summer calls",
        "No online spare part ordering integration",
    ],
    "automobile workshop": [
        "No service status tracking — customers call 10 times asking for car",
        "No service history per vehicle — building trust from scratch each time",
        "No online booking — losing customers who book ahead",
    ],
    "photographer": [
        "No portfolio website — losing wedding/event inquiries to competitors",
        "No online booking/availability calendar — double bookings happen",
        "No client gallery delivery system — sharing 1000 photos on WhatsApp",
    ],
    "videographer": [
        "No showreel website — clients can't see your work easily",
        "No online quote/package system — manual back and forth",
        "No project delivery portal — sharing large files via WeTransfer messily",
    ],
    "graphic designer": [
        "No portfolio site — losing clients to designers with websites",
        "No project management/feedback system — revision chaos on WhatsApp",
        "No retainer/subscription offering visible online",
    ],
    "default": [
        "No website — invisible to online customers searching on Google",
        "No app — missing smartphone-first customers",
        "Manual processes wasting 2-3 hours of staff time daily",
    ],
}


ANALYSIS_PROMPT = """You are a senior business development consultant specializing in digital transformation for Indian SMBs.

Business details:
- Name: {name}
- Type: {business_type}
- Location: {location}
- Has Website: {has_website}
- Has App: No

Your task:
1. Identify 3 specific pain points this business faces without digital tools.
2. For each, state the direct daily business loss.
3. Write a cold outreach email in professional English that:
   - Opens with a genuine observation about their business type
   - Mentions 2 specific pain points with real impact
   - Proposes a clear solution (website/app/automation)
   - Includes ROI angle (more customers, saved time, more revenue)
   - Closes with a low-pressure CTA (free 15-min discovery call)
   - Tone: confident, consultative, NOT salesy
   - MAX 150 words
   - Sign off as: "Warm regards, Business Growth Team"

Respond ONLY in this JSON format (no markdown, no extra text):
{{
  "pain_points": ["pain point 1", "pain point 2", "pain point 3"],
  "business_loss": "One line — what they lose daily without digital tools",
  "email_subject": "Professional subject line (max 8 words)",
  "email_body": "Full professional English email body",
  "whatsapp_message": "2-line professional WhatsApp message with CTA"
}}"""


def analyze_business(business: Dict[str, Any], llm_client) -> Dict[str, Any]:
    """
    Analyze a business using LLM to get pain points and generate outreach content.
    Falls back to template-based content if LLM fails.
    """
    import json, re

    btype = business.get("business_type", "default").lower()
    prompt = ANALYSIS_PROMPT.format(
        name=business.get("name", "Business"),
        business_type=btype,
        location=business.get("location", "India"),
        has_website="Yes" if business.get("has_website") else "No",
    )

    response = llm_client.generate_response(prompt)

    if response:
        # Strip markdown fences
        clean = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean.strip())
        try:
            data = json.loads(clean)
            logging.info(f"LLM analysis done for: {business.get('name')}")
            return data
        except json.JSONDecodeError:
            logging.warning(f"LLM response not valid JSON for {business.get('name')}, using fallback")

    # Fallback: use template
    fallback_points = PAIN_POINTS_MAP.get(btype, PAIN_POINTS_MAP["default"])
    name = business.get("name", "Aapka Business")
    btype_display = btype.title()

    return {
        "pain_points": fallback_points[:3],
        "business_loss": "Daily customers aur revenue loss ho raha hai bina digital presence ke",
        "email_subject": f"{name} ke liye ek important suggestion",
        "email_body": (
            f"Namaste,\n\n"
            f"Maine aapke {btype_display} ke baare mein online dekha. "
            f"Aajkal bahut se customers Google pe search karke businesses dhundtte hain, "
            f"aur bina website ke aap unhe miss kar rahe hain.\n\n"
            f"Hum aapke liye ek simple website ya app bana sakte hain jo:\n"
            f"- Online orders/bookings accept kare\n"
            f"- Google pe aapko visible banaye\n"
            f"- Customers ko automatically remind kare\n\n"
            f"Kya hum 10 minute ki baat kar sakte hain? Bilkul free consultation hai.\n\n"
            f"Thanks,\nTeam"
        ),
        "whatsapp_message": (
            f"Namaste! Aapke {btype_display} ke liye ek free website/app suggestion hai. "
            f"Kya 5 min baat ho sakti hai? 🙏"
        ),
    }
