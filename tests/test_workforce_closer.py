import pytest
from src.models.lead import BusinessProfile, Lead, LeadStatus, OutreachChannel, AuditReport, OutreachDraft
from src.storage.repository import lead_repo
from src.services.workforce import workforce_manager
from src.services.inbound_closer import inbound_closer, ProspectIntent

def test_intent_classification():
    # Price
    assert inbound_closer.classify_intent("What are your charges and fees?") == ProspectIntent.PRICE_OBJECTION
    assert inbound_closer.classify_intent("Kitna paisa lagega?") == ProspectIntent.PRICE_OBJECTION
    
    # Agency
    assert inbound_closer.classify_intent("We already have an agency handling this") == ProspectIntent.AGENCY_OBJECTION
    assert inbound_closer.classify_intent("Hamare paas agency hai") == ProspectIntent.AGENCY_OBJECTION
    
    # Demo / Interested
    assert inbound_closer.classify_intent("Can you show me a demo or portfolio?") == ProspectIntent.INTERESTED
    assert inbound_closer.classify_intent("Yes, please tell me more") == ProspectIntent.INTERESTED
    
    # Unsubscribe
    assert inbound_closer.classify_intent("Stop sending messages!") == ProspectIntent.UNSUBSCRIBE
    assert inbound_closer.classify_intent("Unsubscribe me please") == ProspectIntent.UNSUBSCRIBE
    
    # Not interested
    assert inbound_closer.classify_intent("Not interested at all") == ProspectIntent.NOT_INTERESTED

def test_workforce_pipeline_and_approval_gate():
    profile = BusinessProfile(
        company_name="Grand Cafe Mumbai",
        business_type="cafe",
        location="Bandra, Mumbai",
        phone="+91 98201 55667",
        has_website=False
    )
    lead = Lead(id="test_lead_wf_01", profile=profile)
    lead_repo.save(lead)

    # 1. Process through workforce pipeline
    processed = workforce_manager.process_lead_through_pipeline(lead)
    assert processed.status == LeadStatus.PENDING_APPROVAL
    assert processed.audit is not None
    assert processed.draft is not None
    assert processed.draft.whatsapp_message is not None

    # 2. Check workforce status
    wf_status = workforce_manager.get_workforce_status()
    assert wf_status.pending_approval >= 1
    assert any(a.name == "ApprovalGate" for a in wf_status.agents)
    assert any(a.name == "AuditorAgent" for a in wf_status.agents)

    # 3. Approve and dispatch (dry-run)
    res = workforce_manager.approve_and_dispatch(
        lead_id="test_lead_wf_01",
        channel=OutreachChannel.WHATSAPP,
        edited_message="Personalized message from manager",
        dry_run=True
    )
    assert res["success"] is True
    
    updated = lead_repo.get_by_id("test_lead_wf_01")
    assert updated.status == LeadStatus.CONTACTED
    assert OutreachChannel.WHATSAPP in updated.contacted_channels
    assert updated.draft.whatsapp_message == "Personalized message from manager"

def test_inbound_closer_handling():
    profile = BusinessProfile(
        company_name="Urban Glow Salon",
        business_type="salon",
        location="Mumbai",
        phone="+91 98201 77889",
        has_website=False
    )
    lead = Lead(id="test_lead_wf_02", profile=profile)
    lead.audit = AuditReport(key_flaws=["No online booking system", "Missing WhatsApp direct widget"])
    lead_repo.save(lead)

    # Simulate price objection
    resp = inbound_closer.handle_incoming_message("test_lead_wf_02", "Kitna charge karte ho monthly?")
    assert resp.intent == ProspectIntent.PRICE_OBJECTION
    assert resp.booking_link_included is True
    assert "calendly" in resp.reply_message.lower()

    # Verify conversation thread recorded in lead
    updated = lead_repo.get_by_id("test_lead_wf_02")
    assert len(updated.conversation_history) == 2
    assert updated.conversation_history[0]["sender"] == "prospect"
    assert updated.conversation_history[1]["sender"] == "closer_agent"

def test_reject_lead():
    profile = BusinessProfile(
        company_name="Duplicate Store",
        business_type="retail",
        location="Delhi"
    )
    lead = Lead(id="test_lead_wf_03", profile=profile)
    lead_repo.save(lead)

    ok = workforce_manager.reject_lead("test_lead_wf_03", reason="Invalid phone number")
    assert ok is True

    updated = lead_repo.get_by_id("test_lead_wf_03")
    assert updated.status == LeadStatus.REJECTED
    assert "Invalid phone number" in updated.summary
