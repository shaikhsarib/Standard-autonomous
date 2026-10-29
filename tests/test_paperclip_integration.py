import pytest
from fastapi.testclient import TestClient
from src.api.server import app
from src.models.lead import Lead, LeadStatus, BusinessProfile, AuditReport, OutreachDraft
from src.storage.repository import lead_repo

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_pending_lead():
    lead = Lead(
        id="test_paperclip_freight_01",
        profile=BusinessProfile(
            company_name="Express Fleet Logistics",
            business_type="freight transport logistics",
            location="Navi Mumbai",
            website="https://expressfleet.in",
            phone="+91 98200 11223"
        ),
        status=LeadStatus.PENDING_APPROVAL,
        audit=AuditReport(
            load_time_seconds=1.35,
            has_ssl=True,
            is_mobile_responsive=True,
            key_flaws=["15-20% margin lost to freight brokers", "Manual quotes take 4 hours"],
            quantified_loss="Losing 8-12 spot freight contracts weekly"
        ),
        draft=OutreachDraft(
            whatsapp_message="Hi Express Fleet, skip 20% broker cuts with instant WhatsApp freight quotes. Open to a 2-min demo?",
            email_subject="Bypass broker margins for Express Fleet",
            email_body="Detailed email proposition..."
        )
    )
    lead_repo.save(lead)
    yield lead
    lead_repo.delete("test_paperclip_freight_01")

def test_paperclip_approvals_list(client, sample_pending_lead):
    res = client.get("/api/paperclip/approvals")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    target = next((item for item in items if item["lead_id"] == "test_paperclip_freight_01"), None)
    assert target is not None
    assert target["id"] == "appr_test_paperclip_freight_01"
    assert target["type"] == "outreach_dispatch"
    assert target["requester_agent"]["name"] == "CopywriterAgent"
    assert target["payload"]["company_name"] == "Express Fleet Logistics"
    assert target["payload"]["channel"] == "whatsapp"
    assert "broker" in target["payload"]["message"].lower()

def test_paperclip_approve_action(client, sample_pending_lead):
    res = client.post(
        f"/api/paperclip/approvals/appr_{sample_pending_lead.id}/approve",
        json={"channel": "whatsapp", "dry_run": True}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "approved"
    
    # Check lead status updated in repository
    updated = lead_repo.get_by_id(sample_pending_lead.id)
    assert updated.status == LeadStatus.CONTACTED

def test_paperclip_reject_action(client, sample_pending_lead):
    res = client.post(
        f"/api/paperclip/approvals/appr_{sample_pending_lead.id}/reject",
        json={"reason": "Copy too aggressive"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "rejected"
    
    updated = lead_repo.get_by_id(sample_pending_lead.id)
    assert updated.status == LeadStatus.REJECTED

def test_paperclip_heartbeat(client):
    res = client.post("/api/paperclip/heartbeat")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pulsed"
    assert "agents_notified" in data
    assert data["agents_notified"] == 12

def test_paperclip_overview(client):
    res = client.get("/api/paperclip/overview")
    assert res.status_code == 200
    data = res.json()
    assert "workforce" in data
    assert "topology" in data
    assert "recent_logs" in data
    assert data["circuit_breaker"] == "ACTIVE"

def test_paperclip_health(client):
    res = client.get("/api/paperclip/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["circuit_breaker"] == "ACTIVE"
    assert data["active_agents"] == 12

def test_paperclip_agents_schema(client):
    res = client.get("/api/paperclip/agents")
    assert res.status_code == 200
    agents = res.json()
    assert len(agents) == 12
    agent_names = [a["name"] for a in agents]
    assert "Growth Director & Swarm Master" in agent_names
    assert "Scout & Intel Lead" in agent_names
    assert "The Reality Checker" in agent_names
    assert "Paperclip Circuit Breaker" in agent_names
    assert "Hermes Closer SDR" in agent_names

def test_paperclip_decisions_and_decide(client, sample_pending_lead):
    # Test GET /api/paperclip/decisions
    res = client.get("/api/paperclip/decisions")
    assert res.status_code == 200
    decisions = res.json()
    assert len(decisions) > 0
    target_dec = next((d for d in decisions if d["metadata"]["lead_id"] == sample_pending_lead.id), None)
    assert target_dec is not None
    assert target_dec["ruleKey"] == "outreach_dispatch_ecc_verified"
    assert len(target_dec["options"]) == 2

    # Test POST /api/paperclip/decisions/{id}/decide
    dec_id = target_dec["id"]
    res_decide = client.post(
        f"/api/paperclip/decisions/{dec_id}/decide",
        json={"optionId": "approve", "inputValues": {"custom_message": "Reviewed and verified via Paperclip."}}
    )
    assert res_decide.status_code == 200
    data = res_decide.json()
    assert data["status"] == "approved"

def test_paperclip_batch_approve(client):
    res = client.post("/api/paperclip/batch-approve")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "approved_count" in data

