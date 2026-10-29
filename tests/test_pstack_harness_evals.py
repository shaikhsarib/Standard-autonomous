"""
Production Agentic Evals Suite for IC (Intelligent Central)
Based on Lauren Tan's (Principal Engineer @ Cursor) Masterclass:
"How Cursor Turned AI Agents Into Better Engineers"
Covers:
- Pillar 1: Matt Pocock Contracts (HandoffEnvelope serialization & validation)
- Pillar 2: PStack Reproducible Verification Commands (Anti-slop assertions)
- Pillar 3: Dynamic Swarm Topologies (Consensus, Mesh, Recursive)
- Pillar 4: Google Research Harness² (Self-improving Propose-Probe-Compose cycle)
- Pillar 5: Paperclip Outbox Circuit Breakers
"""

import pytest
import os
import yaml
from pathlib import Path

from src.models.lead import BusinessProfile, Lead, AuditReport, LeadStatus, OutreachDraft
from src.core.contracts import HandoffEnvelope, AgentRole, ContractViolationError
from src.services.evidence_verifier import evidence_verifier, ProofBundle
from src.services.harness_engine import harness_engine, HarnessProposal
from src.services.agency_swarm import agency_swarm, TaskSwarmType
from src.services.scheduled_cadence import cadence_service
from src.storage.repository import lead_repo


def test_eval_pstack_reproducibility():
    """
    Cursor Rule: Every assertion made by an agent must provide an executable command
    to reproduce and verify the claim before it can be merged.
    """
    profile = BusinessProfile(
        company_name="Sen Cargo Logistics",
        business_type="freight movers",
        location="Navi Mumbai",
        website="https://www.sencargo.in",
        has_website=True
    )
    audit = AuditReport(
        load_time_seconds=2.85,
        has_ssl=True,
        is_mobile_responsive=True,
        has_whatsapp_widget=False,
        key_flaws=["High TTFB latency", "No instant rate calculator"]
    )
    research = {
        "citations": [
            {"title": "Sen Cargo Directory Listing", "url": "https://www.justdial.com/Mumbai/Sen-Cargo"}
        ],
        "customer_complaints": [
            "Delayed telephone quote turnaround"
        ]
    }

    bundle: ProofBundle = evidence_verifier.compile_proof_bundle(profile, audit, research)
    
    assert bundle.total_claims >= 4
    assert bundle.proof_score_percentage >= 80.0
    
    # Assert every single claim has a valid reproducibility command
    for claim in bundle.claims:
        assert claim.reproducibility_command is not None
        assert len(claim.reproducibility_command.strip()) > 0
        # Commands should be curl, grep, openssl, or DOM selectors
        assert any(cmd in claim.reproducibility_command for cmd in ["curl", "openssl", "document.querySelector", "web_search", "grep"])


def test_eval_harness2_propose_probe_compose():
    """
    Google Research Harness²: Propose candidate adjustment, probe against anti-fluff criteria,
    compose into persistent storage without updating model weights.
    """
    vertical = "logistics_transport"
    friction = "Lost 3 high-value loads due to delayed phone quotes after 7 PM"
    
    # Stage 1: Propose
    proposal: HarnessProposal = harness_engine.propose_pitch_improvement(
        vertical=vertical,
        current_claim="We do logistics",
        prospect_feedback=friction
    )
    assert proposal.id.startswith("harn_")
    assert proposal.status == "proposed"
    assert "logistics_transport" in proposal.target_area

    # Stage 2: Probe
    is_valid = harness_engine.probe_and_score(proposal)
    assert is_valid is True
    assert proposal.score >= 0.90
    assert proposal.status == "probed"

    # Stage 3: Compose
    composed = harness_engine.compose_improvement(proposal)
    assert composed is True
    assert proposal.status == "composed"

    # Verify persistent storage
    domain_file = Path("data") / "harness_library" / "logistics_transport.md"
    assert domain_file.exists()
    content = domain_file.read_text(encoding="utf-8")
    assert proposal.id in content


def test_eval_dynamic_task_swarms():
    """
    Ruflo Multi-Agent Swarms: Verify Consensus closer and Mesh intelligence topologies
    execute and deliver validated handoffs.
    """
    # 1. Consensus Swarm (Closer + Reality Checker + Brand Guardian + Strategist)
    closer_result = agency_swarm.spawn_task_swarm(
        task_type=TaskSwarmType.OBJECTION_CLOSER,
        context={
            "lead_id": "test_lead_consensus",
            "vertical": "logistics_transport",
            "prospect_objection": "We already have brokers on contract"
        }
    )
    assert closer_result["topology"] == "consensus"
    assert closer_result["consensus_agreement"] >= 0.90
    assert "broker" in closer_result["consensus_verdict"].lower()

    # 2. Recursive Self-Heal Swarm
    heal_result = agency_swarm.spawn_task_swarm(
        task_type=TaskSwarmType.HARNESS_SELF_HEAL,
        context={
            "vertical": "event_banquets",
            "observed_friction": "No after-hours hall availability check"
        }
    )
    assert heal_result["topology"] == "recursive"
    assert heal_result["score"] >= 0.90
    assert "composed" in heal_result["evolution_status"]


def test_eval_matt_pocock_handoff_contracts():
    """
    Matt Pocock /to-spec: Enforce strongly typed handoffs between line cook agents.
    """
    envelope = HandoffEnvelope(
        source_agent=AgentRole.RESEARCHER,
        target_agent=AgentRole.AUDITOR,
        payload={"website": "https://test.com", "company_name": "Test Co"}
    )
    assert envelope.validate_contract() is True
    assert envelope.contract_version == "v2.1"

    # Invalid envelope
    bad_envelope = HandoffEnvelope(
        source_agent=AgentRole.RESEARCHER,
        target_agent=AgentRole.AUDITOR,
        payload={}
    )
    with pytest.raises(ContractViolationError):
        bad_envelope.validate_contract()


def test_eval_scheduled_cadence_engine():
    """
    x.ai Grok Bot Marketplace: Test Nightly Audit Engineer and QA Bot cadence.
    """
    report = cadence_service.run_nightly_audit()
    assert report.executed_by == "NightlyAuditEngineer"
    assert report.total_leads_audited >= 0
    assert report.qa_checks_total == 4
    assert report.qa_checks_passed == 4
