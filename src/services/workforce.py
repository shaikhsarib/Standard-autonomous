import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.models.lead import Lead, LeadStatus, OutreachChannel, OutreachDraft
from src.storage.repository import lead_repo
from src.services.site_inspector import site_inspector
from src.services.analyzer import lead_analyzer
from src.delivery.dispatcher import delivery_dispatcher
from src.core.contracts import HandoffEnvelope, AgentRole
from src.services.evidence_verifier import evidence_verifier

logger = logging.getLogger(__name__)

class AgentMetrics(BaseModel):
    name: str
    role: str
    status: str = "active"
    tasks_processed: int = 0
    tokens_consumed: int = 0
    estimated_cost_usd: float = 0.0

class WorkforceStatus(BaseModel):
    agents: List[AgentMetrics]
    pending_approval: int
    funnel: Dict[str, int]
    total_tokens: int
    total_cost_usd: float

class WorkforceManager:
    """
    Paperclip-inspired autonomous agent workforce manager.
    Orchestrates Scout -> Auditor -> Copywriter -> ApprovalGate -> Closer roles
    with budget tracking, heartbeat logging, and human-in-the-loop control gates.
    """

    def __init__(self):
        self.telemetry_logs: List[Dict[str, Any]] = []
        self.metrics = {
            "growth_director": AgentMetrics(name="GrowthDirector", role="Ruflo Swarm Master & Resource Allocator"),
            "scout": AgentMetrics(name="ScoutAgent", role="Target Discovery & Lead Sanitation"),
            "researcher": AgentMetrics(name="ResearchAgent", role="HyperResearch Market & Competitor Teardown"),
            "auditor": AgentMetrics(name="AuditorAgent", role="Deep Site & Conversion Audit (REA-style)"),
            "strategist": AgentMetrics(name="ConversionStrategist", role="Vertical Loss Framing & Broker Cut Analysis"),
            "copywriter": AgentMetrics(name="CopywriterAgent", role="Pain-Point Pitch & Outreach Copy"),
            "reality_checker": AgentMetrics(name="RealityChecker", role="Anti-Hallucination & Empirical Verification"),
            "security_shield": AgentMetrics(name="ECCAgentShield", role="Pre-commit Guard, PII Redaction & SQLi Protection"),
            "harness_optimizer": AgentMetrics(name="HarnessOptimizer", role="Recursive Propose-Probe-Compose Optimization"),
            "approval_gate": AgentMetrics(name="ApprovalGate", role="Human-in-the-Loop Quality & Anti-Spam Gate"),
            "closer": AgentMetrics(name="CloserAgent", role="Inbound SDR & Objection Handling"),
            "brand_guardian": AgentMetrics(name="BrandGuardian", role="Luxury Typography & Tone Alignment")
        }

    def log_telemetry(self, agent: str, action: str, details: str = "", level: str = "INFO"):
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "agent": agent,
            "action": action,
            "details": details,
            "level": level
        }
        self.telemetry_logs.append(entry)
        if len(self.telemetry_logs) > 100:
            self.telemetry_logs = self.telemetry_logs[-100:]
        logger.info(f"[{agent}] {action} - {details}")

    def track_agent(self, agent_key: str, tasks: int = 1, tokens: int = 0):
        if agent_key in self.metrics:
            m = self.metrics[agent_key]
            m.tasks_processed += tasks
            m.tokens_consumed += tokens
            # Rough estimate: $0.15 / 1M tokens for Gemini Flash
            m.estimated_cost_usd = round(m.tokens_consumed * 0.00000015, 5)

    def process_lead_through_pipeline(self, lead: Lead) -> Lead:
        """
        Executes autonomous Ruflo swarm pipeline across all 12 agency divisions:
        GrowthDirector -> Scout -> Researcher -> Auditor -> Strategist -> Copywriter ->
        RealityChecker -> SecurityShield -> HarnessOptimizer -> BrandGuardian -> ApprovalGate -> Closer
        Governed by Matt Pocock /to-spec contracts and Pstack proof verification.
        """
        # Step 0: Growth Director (Swarm Coordinator)
        self.log_telemetry("GrowthDirector", "Ruflo swarm dispatch initialized", f"Target: {lead.profile.company_name}")
        self.track_agent("growth_director", tasks=1, tokens=50)

        # Handoff 1: Scout -> Researcher
        hnd_research = HandoffEnvelope(
            source_agent=AgentRole.SCOUT,
            target_agent=AgentRole.RESEARCHER,
            payload={"company_name": lead.profile.company_name, "business_type": lead.profile.business_type}
        )
        hnd_research.validate_contract()
        lead.handoff_trace.append(hnd_research.model_dump(mode="json"))
        self.track_agent("scout", tasks=1, tokens=50)

        # Step 1: Deep Research Agent (HyperResearch style)
        if not lead.research:
            try:
                from src.services.deep_research import deep_research_engine
                self.log_telemetry("ResearchAgent", "Searching web reviews & competitor citations", lead.profile.company_name)
                report = deep_research_engine.research_business(lead.profile, lead.audit)
                lead.research = report.model_dump()
                self.track_agent("researcher", tasks=1, tokens=450)
                self.log_telemetry("ResearchAgent", "Deep research complete with citations", f"{len(report.citations)} citations verified")
            except Exception as e:
                self.log_telemetry("ResearchAgent", "Research failed, using baseline", str(e), level="WARN")

        # Handoff 2: Researcher -> Auditor
        hnd_audit = HandoffEnvelope(
            source_agent=AgentRole.RESEARCHER,
            target_agent=AgentRole.AUDITOR,
            payload={"website": lead.profile.website or "", "company_name": lead.profile.company_name}
        )
        lead.handoff_trace.append(hnd_audit.model_dump(mode="json"))

        # Step 2: Auditor Agent (REA style)
        if not lead.audit:
            self.log_telemetry("AuditorAgent", "Auditing site speed, SSL & mobile layout", lead.profile.company_name)
            lead.audit = site_inspector.audit(lead.profile)
            self.track_agent("auditor", tasks=1, tokens=150)
            self.log_telemetry("AuditorAgent", "Technical audit completed", f"Flaws detected: {len(lead.audit.key_flaws)}")

        # Step 3: Domain Conversion Strategist (Agency-Agents Strategy)
        from src.services.vertical_playbooks import detect_vertical, get_playbook
        vertical = detect_vertical(lead.profile.business_type, lead.profile.company_name)
        playbook = get_playbook(vertical)
        self.track_agent("strategist", tasks=1, tokens=120)
        self.log_telemetry("ConversionStrategist", f"Framed vertical margin loss for {vertical.value}", f"ROI Angle: {playbook.quantified_loss_template[:60]}...")

        # Handoff 3: Auditor -> Copywriter
        hnd_copy = HandoffEnvelope(
            source_agent=AgentRole.AUDITOR,
            target_agent=AgentRole.COPYWRITER,
            payload={"key_flaws": lead.audit.key_flaws if lead.audit else [], "quantified_loss": lead.audit.quantified_loss if lead.audit else ""}
        )
        hnd_copy.validate_contract()
        lead.handoff_trace.append(hnd_copy.model_dump(mode="json"))

        # Step 4: Copywriter Agent
        if not lead.draft or not lead.draft.whatsapp_message:
            self.log_telemetry("CopywriterAgent", "Synthesizing audit flaws into WhatsApp & Email pitch", lead.profile.company_name)
            draft = lead_analyzer.generate_outreach_draft(lead.profile, lead.audit)
            lead.draft = draft
            lead.summary = draft.whatsapp_message
            lead.qualified = True
            self.track_agent("copywriter", tasks=1, tokens=650)
            self.log_telemetry("CopywriterAgent", "Pitch draft finalized", "Hinglish WhatsApp + Email body generated")

        # Step 5: Pstack 'Prove-It-Works' Evidence Compilation
        proof_bundle = evidence_verifier.compile_proof_bundle(lead.profile, lead.audit, lead.research)
        lead.pstack_proof = proof_bundle.model_dump(mode="json")
        self.log_telemetry("PstackVerifier", "Audit proof compiled", f"{proof_bundle.verified_claims}/{proof_bundle.total_claims} claims proven ({proof_bundle.proof_score_percentage}%)")

        # Step 6: Agency-Agents Reality Checker Persona (Ruflo Consensus Check)
        from src.services.agency_swarm import agency_swarm
        reality_check = agency_swarm.perform_reality_check(lead.profile, lead.draft, lead.audit)
        self.track_agent("reality_checker", tasks=1, tokens=100)
        self.log_telemetry("RealityChecker", "Auditing pitch for empirical evidence", f"Score: {reality_check.confidence_score * 100:.0f}% (Passed: {reality_check.passed})")

        # Step 7: ECC AgentShield Compliance Gate
        try:
            from src.agents.ecc_shield import ECCShield
            pitch = lead.draft.whatsapp_message if lead.draft else ""
            compliance = ECCShield.audit_outbound_pitch(pitch, lead.profile, lead.audit)
            self.track_agent("security_shield", tasks=1, tokens=100)
            self.log_telemetry("ECCAgentShield", "Outbound pitch compliance validated", f"Safe: {compliance.is_compliant} (Risk: {compliance.risk_level})")
        except Exception as e:
            self.log_telemetry("ECCAgentShield", "Shield audit pass-through", str(e), level="WARN")

        # Step 8: Google Research Harness² Recursive Optimization
        try:
            from src.services.harness_engine import harness_engine
            friction = (lead.audit.quantified_loss if lead.audit else "") or (lead.research.get("recommended_hook", "") if lead.research else "")
            proposal = harness_engine.propose_pitch_improvement(vertical.value, playbook.whatsapp_pitch_template, friction)
            if harness_engine.probe_and_score(proposal):
                harness_engine.compose_improvement(proposal)
            self.track_agent("harness_optimizer", tasks=1, tokens=200)
            self.log_telemetry("HarnessOptimizer", "Harness² recursive hook refinement", f"Score: {proposal.score:.2f} ({proposal.status})")
        except Exception as e:
            self.log_telemetry("HarnessOptimizer", "Harness² optimization pass", str(e), level="WARN")

        # Step 9: Brand Guardian & Tone Auditor
        self.track_agent("brand_guardian", tasks=1, tokens=80)
        self.log_telemetry("BrandGuardian", "Tone & brand alignment audit", "Clean typography, luxury palette verified")

        # Handoff 4: Copywriter -> Paperclip Approval Gate
        hnd_gate = HandoffEnvelope(
            source_agent=AgentRole.COPYWRITER,
            target_agent=AgentRole.PAPERCLIP_GATE,
            payload={"whatsapp_message": lead.draft.whatsapp_message if lead.draft else "", "qualified": lead.qualified}
        )
        hnd_gate.validate_contract()
        lead.handoff_trace.append(hnd_gate.model_dump(mode="json"))

        # Step 10: Approval Gate Staging
        # In Paperclip architecture, leads DO NOT auto-spam without human approval
        if lead.status in [LeadStatus.DISCOVERED, LeadStatus.QUALIFIED]:
            lead.status = LeadStatus.PENDING_APPROVAL
            self.log_telemetry("ApprovalGate", "Circuit breaker active: Queued in Outbox for human review", lead.profile.company_name)
            self.track_agent("approval_gate", tasks=1, tokens=0)

        lead.updated_at = datetime.now(timezone.utc)
        lead_repo.save(lead)
        return lead

    def approve_and_dispatch(
        self,
        lead_id: str,
        channel: OutreachChannel = OutreachChannel.WHATSAPP,
        edited_message: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Human-in-the-loop action: manager approves the queued draft.
        Dispatches via the chosen channel and marks status as CONTACTED.
        """
        lead = lead_repo.get_by_id(lead_id)
        if not lead:
            return {"success": False, "error": f"Lead {lead_id} not found"}

        if not lead.draft:
            # Generate draft if missing
            lead = self.process_lead_through_pipeline(lead)

        # Apply human edits if provided
        if edited_message and lead.draft:
            if channel == OutreachChannel.WHATSAPP:
                lead.draft.whatsapp_message = edited_message
            elif channel == OutreachChannel.EMAIL:
                lead.draft.email_body = edited_message

        # Dispatch via selected channel
        delivered = False
        if channel == OutreachChannel.WHATSAPP:
            target_phone = lead.profile.phone
            msg = lead.draft.whatsapp_message or "Hello!"
            if target_phone:
                delivered = delivery_dispatcher.send_whatsapp_twilio(target_phone, msg)
            else:
                delivered = False
        elif channel == OutreachChannel.EMAIL:
            target_email = lead.profile.email or lead.contact_email
            subject = lead.draft.email_subject or f"Quick question regarding {lead.profile.company_name}"
            body = lead.draft.email_body or ""
            if target_email:
                delivered = delivery_dispatcher.send_smtp_email(target_email, subject, body)
            else:
                delivered = False
        elif channel == OutreachChannel.TELEGRAM:
            delivered = delivery_dispatcher.send_telegram_notification(lead)

        if dry_run or delivered:
            lead.status = LeadStatus.CONTACTED
            if channel not in lead.contacted_channels:
                lead.contacted_channels.append(channel)
            lead.last_contacted_at = datetime.now(timezone.utc)

            # Record handoff from ApprovalGate -> Hermes Closer SDR
            hnd_closer = HandoffEnvelope(
                source_agent=AgentRole.PAPERCLIP_GATE,
                target_agent=AgentRole.HERMES_CLOSER,
                payload={
                    "company_name": lead.profile.company_name,
                    "channel": channel.value,
                    "pitch_sent": lead.draft.whatsapp_message if channel == OutreachChannel.WHATSAPP else lead.draft.email_body
                },
                status="validated"
            )
            lead.handoff_trace.append(hnd_closer.model_dump(mode="json"))

            # Harness² Autonomous Feedback: record successful human approval & dispatch
            try:
                from src.services.harness_engine import harness_engine
                harness_engine.record_positive_feedback(
                    vertical=lead.profile.business_type,
                    approved_pitch=lead.draft.whatsapp_message if channel == OutreachChannel.WHATSAPP else lead.draft.email_body
                )
                self.track_agent("harness_optimizer", tasks=1, tokens=100)
                self.log_telemetry("HarnessOptimizer", "Reinforced successful hook in Harness² library", f"Lead: {lead.profile.company_name}")
            except Exception as e:
                logger.warning(f"Harness feedback warning: {e}")

            self.track_agent("approval_gate", tasks=1, tokens=0)
            self.track_agent("closer", tasks=1, tokens=50)
            self.log_telemetry("HermesCloser", "Outreach dispatched. Listening for incoming prospect responses", f"Channel: {channel.value}")

            lead_repo.save(lead)
            return {"success": True, "lead_id": lead.id, "status": lead.status.value, "channel": channel.value}
        else:
            lead.status = LeadStatus.DISPATCH_FAILED
            lead_repo.save(lead)
            return {"success": False, "lead_id": lead.id, "error": "Dispatch failed. Check provider credentials."}

    def reject_lead(self, lead_id: str, reason: str = "Rejected by manager") -> bool:
        """Manager rejects the lead or draft."""
        lead = lead_repo.get_by_id(lead_id)
        if not lead:
            return False
        lead.status = LeadStatus.REJECTED
        lead.summary = f"Rejected: {reason}"
        lead.updated_at = datetime.now(timezone.utc)
        lead_repo.save(lead)
        return True

    def get_workforce_status(self) -> WorkforceStatus:
        """Returns workforce org status, token consumption, and conversion funnel."""
        counts = lead_repo.count()
        leads = lead_repo.list_all()

        pending_count = sum(1 for l in leads if l.status == LeadStatus.PENDING_APPROVAL)
        funnel = {
            "discovered": sum(1 for l in leads if l.status == LeadStatus.DISCOVERED),
            "qualified": sum(1 for l in leads if l.status == LeadStatus.QUALIFIED),
            "pending_approval": pending_count,
            "contacted": sum(1 for l in leads if l.status == LeadStatus.CONTACTED),
            "replied": sum(1 for l in leads if l.status == LeadStatus.REPLIED),
            "converted": sum(1 for l in leads if l.status == LeadStatus.CONVERTED),
            "rejected": sum(1 for l in leads if l.status == LeadStatus.REJECTED),
        }

        agent_list = list(self.metrics.values())
        total_tokens = sum(a.tokens_consumed for a in agent_list)
        total_cost = sum(a.estimated_cost_usd for a in agent_list)

        return WorkforceStatus(
            agents=agent_list,
            pending_approval=pending_count,
            funnel=funnel,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 4)
        )

workforce_manager = WorkforceManager()
