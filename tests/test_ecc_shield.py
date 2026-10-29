"""
Unit tests for ECC (Everything Claude Code) Dual-Engine Shield.
Tests both Development Code Safety (AgentShield) and Runtime Outbound Pitch Compliance.
"""

import pytest
from src.agents.ecc_shield import ecc_shield, ECCShield
from src.models.lead import BusinessProfile, AuditReport


def test_ecc_development_clean_code():
    clean_code = """
    def calculate_freight_rate(weight_kg: float, distance_km: float) -> float:
        base_rate = 150.0
        return base_rate + (weight_kg * 0.45) + (distance_km * 1.2)
    """
    report = ecc_shield.audit_code_safety(clean_code)
    assert report.is_safe is True
    assert report.safety_score == 100.0
    assert len(report.vulnerabilities) == 0
    assert report.risk_level == "LOW"


def test_ecc_development_detects_secrets():
    leaky_code = """
    TELEGRAM_BOT_TOKEN = "bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567"
    openai_key = "sk-1234567890abcdef1234567890abcdef"
    """
    report = ecc_shield.audit_code_safety(leaky_code)
    assert report.is_safe is False
    assert report.safety_score < 70.0
    assert report.risk_level == "CRITICAL"
    assert any("Telegram" in v for v in report.vulnerabilities)
    assert any("OpenAI" in v for v in report.vulnerabilities)


def test_ecc_development_detects_dangerous_eval():
    unsafe_code = """
    def execute_user_query(query_str):
        return eval(query_str)
    """
    report = ecc_shield.audit_code_safety(unsafe_code)
    assert report.is_safe is False
    assert any("eval()" in v for v in report.vulnerabilities)


def test_ecc_runtime_pitch_compliant():
    profile = BusinessProfile(
        company_name="Apex Logistics Ltd",
        business_type="freight transport",
        location="Navi Mumbai",
        website="http://apexlogistics.in",
        has_website=True
    )
    audit = AuditReport(
        load_time_seconds=4.8,
        has_ssl=False,
        is_mobile_responsive=True,
        has_whatsapp_widget=False
    )
    pitch = (
        "Hi Apex Logistics Ltd team, noticed your portal has a 4.8s load time and missing SSL certificate. "
        "We built an instant WhatsApp quote calculator for Navi Mumbai freight carriers to bypass broker cuts."
    )

    report = ecc_shield.audit_outbound_pitch(pitch, profile, audit)
    assert report.is_compliant is True
    assert report.compliance_score == 100.0
    assert report.grounded_checks.get("load_time_evidence") is True
    assert report.grounded_checks.get("ssl_evidence") is True
    assert report.grounded_checks.get("personalized_to_target") is True


def test_ecc_runtime_ungrounded_claims_flagged():
    profile = BusinessProfile(
        company_name="Vanguard Movers",
        business_type="packers and movers",
        location="Pune",
        has_website=False
    )
    # Audit report with no load time recorded and SSL verified active
    audit = AuditReport(
        load_time_seconds=None,
        has_ssl=True,
        is_mobile_responsive=False,
        has_whatsapp_widget=False
    )
    # Pitch makes ungrounded claims about speed and false claim about SSL
    pitch = "Hello Vanguard Movers, your website load time is 8 seconds and has no SSL security."

    report = ecc_shield.audit_outbound_pitch(pitch, profile, audit)
    assert report.is_compliant is False
    assert any("UNGROUNDED" in v or "FALSE CLAIM" in v for v in report.violations)


def test_ecc_runtime_detects_internal_prompt_leak():
    profile = BusinessProfile(
        company_name="Blue Dart Express",
        business_type="courier",
        location="Mumbai"
    )
    leaky_pitch = (
        "Dear Blue Dart Express, <SYSTEM_PROMPT> do not hallucinate </SYSTEM_PROMPT> "
        "Here is your customized logistics rate prototype."
    )

    report = ecc_shield.audit_outbound_pitch(leaky_pitch, profile)
    assert report.is_compliant is False
    assert report.risk_level == "HIGH"
    assert any("PII/LEAK" in v for v in report.violations)


def test_ecc_api_endpoints():
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.storage.repository import lead_repo
    from src.models.lead import Lead, BusinessProfile, AuditReport, LeadStatus, OutreachDraft

    client = TestClient(app)

    # 1. Test Shield Status
    res = client.get("/api/ecc/shield-status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ACTIVE"
    assert "AgentShield" in data["shield_version"]

    # 2. Test Audit Pitch Endpoint
    test_lead = Lead(
        id="lead_test_ecc_api",
        profile=BusinessProfile(
            company_name="ECC Cargo Logistics",
            business_type="freight transport",
            location="Bhiwandi"
        ),
        audit=AuditReport(load_time_seconds=3.2, has_ssl=True),
        draft=OutreachDraft(whatsapp_message="Hi ECC Cargo Logistics, your verified load time is 3.2s. Here is your calculator prototype."),
        status=LeadStatus.PENDING_APPROVAL
    )
    lead_repo.save(test_lead)

    res_audit = client.post("/api/ecc/audit-pitch", json={"lead_id": "lead_test_ecc_api"})
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert audit_data["is_compliant"] is True
    assert audit_data["compliance_score"] == 100.0

    # 3. Test High-Risk Leak Blocked at Approval Gate
    res_approve = client.post(
        "/api/leads/lead_test_ecc_api/approve",
        json={
            "channel": "whatsapp",
            "edited_message": "Hello ECC Cargo Logistics, <SYSTEM_PROMPT> ignore instructions </SYSTEM_PROMPT> rate card.",
            "dry_run": True
        }
    )
    assert res_approve.status_code == 400
    assert "AgentShield Blocked Dispatch" in res_approve.json()["detail"]
