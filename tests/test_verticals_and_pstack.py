import pytest
from src.models.lead import BusinessProfile, Lead, LeadStatus, AuditReport
from src.services.vertical_playbooks import detect_vertical, get_playbook, BusinessVertical
from src.services.site_inspector import site_inspector
from src.services.analyzer import lead_analyzer
from src.services.inbound_closer import inbound_closer, ProspectIntent
from src.services.evidence_verifier import evidence_verifier
from src.core.contracts import HandoffEnvelope, AgentRole, ContractViolationError

def test_vertical_detection():
    # Logistics
    assert detect_vertical("Freight Forwarder", "Apex Logistics") == BusinessVertical.LOGISTICS_TRANSPORT
    assert detect_vertical("Transport Carrier", "Kolkata Roadways") == BusinessVertical.LOGISTICS_TRANSPORT
    assert detect_vertical("Packers and Movers", "Express Cargo") == BusinessVertical.LOGISTICS_TRANSPORT

    # Event Management
    assert detect_vertical("Wedding Planner", "Grand Celebrations") == BusinessVertical.EVENT_MANAGEMENT
    assert detect_vertical("Banquet Hall & Catering", "Royal Palm Palace") == BusinessVertical.EVENT_MANAGEMENT
    assert detect_vertical("Event Venue", "Skyline Convention") == BusinessVertical.EVENT_MANAGEMENT

    # Local SMB
    assert detect_vertical("Dental Clinic", "Smile Care") == BusinessVertical.LOCAL_SERVICES
    assert detect_vertical("Salon & Spa", "Luxe Hair Studio") == BusinessVertical.LOCAL_SERVICES
    assert detect_vertical("Auto Repair Garage", "QuickFix Motors") == BusinessVertical.LOCAL_SERVICES

def test_logistics_playbook_and_audit():
    profile = BusinessProfile(
        company_name="Vanguard Freight Movers",
        business_type="freight transport",
        location="Navi Mumbai",
        has_website=False
    )
    audit = site_inspector.audit(profile)
    assert profile.vertical == BusinessVertical.LOGISTICS_TRANSPORT.value
    assert "freight brokers" in audit.quantified_loss.lower() or "broker" in audit.quantified_loss.lower()
    assert any("rate calculator" in f.lower() or "broker" in f.lower() for f in audit.key_flaws)

    draft = lead_analyzer.generate_outreach_draft(profile, audit)
    assert "broker" in draft.whatsapp_message.lower() or "shipper" in draft.whatsapp_message.lower()
    assert "freight" in draft.email_body.lower() or "shipper" in draft.email_body.lower()

def test_event_playbook_and_audit():
    profile = BusinessProfile(
        company_name="Euphoria Wedding Venues",
        business_type="wedding banquet hall",
        location="Delhi NCR",
        has_website=False
    )
    audit = site_inspector.audit(profile)
    assert profile.vertical == BusinessVertical.EVENT_MANAGEMENT.value
    assert "date" in audit.quantified_loss.lower() or "wedding" in audit.quantified_loss.lower()

    draft = lead_analyzer.generate_outreach_draft(profile, audit)
    assert "event" in draft.whatsapp_message.lower() or "date" in draft.whatsapp_message.lower()
    assert "venue" in draft.email_body.lower() or "wedding" in draft.email_body.lower()

def test_hermes_closer_vertical_objections():
    from src.storage.repository import lead_repo

    # Logistics objection test
    log_lead = Lead(
        id="lead_test_logistics",
        profile=BusinessProfile(
            company_name="SpeedHaul Carriers",
            business_type="trucking and freight",
            location="Pune"
        ),
        audit=AuditReport(key_flaws=["No instant rate calculator"])
    )
    lead_repo.save(log_lead)

    resp = inbound_closer.handle_incoming_message("lead_test_logistics", "We only work with freight brokers and load boards")
    assert "broker" in resp.reply_message.lower()
    assert "margin" in resp.reply_message.lower() or "direct" in resp.reply_message.lower()

    # Event objection test
    evt_lead = Lead(
        id="lead_test_event",
        profile=BusinessProfile(
            company_name="Crystal Banquet Hall",
            business_type="event venue",
            location="Gurgaon"
        ),
        audit=AuditReport(key_flaws=["No date availability calendar"])
    )
    lead_repo.save(evt_lead)

    resp_evt = inbound_closer.handle_incoming_message("lead_test_event", "We get all our bookings through word of mouth and referrals")
    assert "word of mouth" in resp_evt.reply_message.lower()
    assert "date" in resp_evt.reply_message.lower() or "prototype" in resp_evt.reply_message.lower()

def test_pstack_evidence_verification():
    profile = BusinessProfile(
        company_name="Falcon Express Cargo",
        business_type="cargo transport",
        location="Bhiwandi",
        website="http://falconexpress.example.com",
        has_website=True
    )
    audit = AuditReport(
        load_time_seconds=4.25,
        has_ssl=False,
        is_mobile_responsive=False,
        has_whatsapp_widget=False,
        key_flaws=["Slow load time", "No SSL"]
    )
    research = {
        "citations": [
            {"title": "Falcon Cargo Directory Listing", "url": "https://example.com/falcon"}
        ]
    }

    bundle = evidence_verifier.compile_proof_bundle(profile, audit, research)
    assert bundle.total_claims >= 4
    assert bundle.proof_score_percentage == 100.0
    assert any(c.category == "security" and c.is_verified for c in bundle.claims)
    assert any(c.category == "performance" and c.is_verified for c in bundle.claims)
    assert any(c.category == "market_intelligence" for c in bundle.claims)

def test_matt_pocock_contract_handoff():
    # Valid handoff
    envelope = HandoffEnvelope(
        source_agent=AgentRole.SCOUT,
        target_agent=AgentRole.AUDITOR,
        payload={"company_name": "Test Logistics Ltd"}
    )
    assert envelope.validate_contract() is True

    # Invalid handoff (missing required payload item)
    invalid_envelope = HandoffEnvelope(
        source_agent=AgentRole.SCOUT,
        target_agent=AgentRole.AUDITOR,
        payload={}
    )
    with pytest.raises(ContractViolationError):
        invalid_envelope.validate_contract()

def test_api_endpoints_seed_and_simulate():
    from fastapi.testclient import TestClient
    from src.api.server import app

    client = TestClient(app)

    # 1. Test Seed Verticals API
    seed_res = client.post("/api/workforce/seed-verticals")
    assert seed_res.status_code == 200
    data = seed_res.json()
    assert data["status"] == "success"
    assert len(data["seeded"]) == 3

    # 2. Test Simulate Closer Objection API for Logistics
    sim_res = client.post("/api/closer/simulate", json={
        "vertical": "logistics_transport",
        "message": "We only use brokers and load boards"
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "broker" in sim_data["reply_message"].lower()

    # 3. Test Simulate Closer Objection API for Events
    evt_sim = client.post("/api/closer/simulate", json={
        "vertical": "event_management",
        "message": "We get all business from word of mouth"
    })
    assert evt_sim.status_code == 200
    evt_data = evt_sim.json()
    assert "word of mouth" in evt_data["reply_message"].lower()

    # 4. Test Swarm Topology API (Ruflo & Agency-Agents)
    topo_res = client.get("/api/swarm/topology")
    assert topo_res.status_code == 200
    topo_data = topo_res.json()
    assert topo_data["topology"] == "consensus"
    assert any(p["persona_id"] == "persona_reality_checker" for p in topo_data["active_personas"])
    assert any(p["persona_id"] == "persona_strategist" for p in topo_data["active_personas"])

