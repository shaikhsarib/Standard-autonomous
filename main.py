import argparse
import sys
import logging
import os
import time
from dotenv import load_dotenv

from core.engine import LeadGenerationEngine
from core.schemas import BusinessProfile
from services.llm_client import ProductionLLMClient
from scrapers.scrapper_module import find_businesses
from delivery.delivery_module import deliver_lead

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_chat(engine: LeadGenerationEngine, profile: BusinessProfile, simulation: bool = False) -> None:
    """Execute the chat loop and handle lead delivery."""
    session = engine.create_session(profile)
    print(f"\n--- Starting chat for {profile.company_name} ---")

    response = engine.generate_next_response(session)
    print(f"Bot: {response}")

    try:
        if simulation:
            inputs = [
                "Hi, what do you offer?",
                "My budget is around $3000.",
                "Sounds interesting, here is my email rohit@example.com.",
                "exit",
            ]
            for user_input in inputs:
                print(f"You (simulation): {user_input}")
                if user_input == "exit":
                    break
                response = engine.generate_next_response(session, user_input)
                print(f"Bot: {response}")
                time.sleep(1)
        else:
            while True:
                user_input = input("You (type 'exit' to stop): ")
                if user_input.lower() == "exit":
                    break
                response = engine.generate_next_response(session, user_input)
                print(f"Bot: {response}")

    except KeyboardInterrupt:
        print("\nChat stopped by user.")

    print("\n--- Extracting lead data ---")
    lead = engine.extract_lead(session)
    if lead and lead.qualified and lead.contact_email:
        print(f"Lead extracted: {lead.contact_name} ({lead.contact_email}), Interest: {lead.interest_level}")

        lead_data = {
            "name": lead.contact_name,
            "website": profile.website,
            "budget": lead.budget,
            "email": lead.contact_email,
            "interest_level": lead.interest_level,
            "summary": lead.summary,
        }

        print("\n--- Delivering lead ---")
        delivery_status = deliver_lead(lead_data)
        print(f"Delivery status: {delivery_status}")
    else:
        print("No qualified lead with email extracted.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Advanced Lead Gen Chatbot CLI")
    parser.add_argument("--query", type=str, default="software development")
    parser.add_argument("--location", type=str, default="San Francisco")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode")
    parser.add_argument("--mock", action="store_true", help="Use mock leads")
    args = parser.parse_args()

    if args.mock:
        os.environ["USE_MOCK_LEADS"] = "true"

    try:
        llm_client = ProductionLLMClient()
        engine = LeadGenerationEngine(llm_client)
    except Exception as exc:
        logging.error(f"Initialization error: {exc}")
        sys.exit(1)

    print(f"Finding businesses for '{args.query}' in '{args.location}'...")
    leads = find_businesses(args.query, args.location, args.limit)

    if not leads:
        print("No businesses found.")
        return

    for lead_profile in leads:
        profile = BusinessProfile(
            company_name=lead_profile["name"],
            website=lead_profile.get("website"),
            industry=args.query,
            pain_points=[],
        )
        run_chat(engine, profile, args.simulate)


if __name__ == "__main__":
    main()
