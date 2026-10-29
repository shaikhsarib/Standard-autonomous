"""
Core Contracts & Handoff Specifications.
Implements Matt Pocock's skills architecture (/to-spec, /handoff)
for strictly-typed, verifiable multi-agent communication.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

class AgentRole(str, Enum):
    GROWTH_DIRECTOR = "growth_director_agent"
    SCOUT = "scout_agent"
    RESEARCHER = "researcher_agent"
    AUDITOR = "auditor_agent"
    CONVERSION_STRATEGIST = "conversion_strategist_agent"
    COPYWRITER = "copywriter_agent"
    REALITY_CHECKER = "reality_checker_agent"
    SECURITY_SHIELD = "security_shield_agent"
    HARNESS_OPTIMIZER = "harness_optimizer_agent"
    PAPERCLIP_GATE = "paperclip_approval_gate"
    HERMES_CLOSER = "hermes_closer_agent"
    BRAND_GUARDIAN = "brand_guardian_agent"

class HandoffStatus(str, Enum):
    INITIATED = "initiated"
    VALIDATED = "validated"
    REJECTED = "rejected"
    COMPLETED = "completed"

class ContractViolationError(Exception):
    """Raised when an agent produces output violating its strict specification."""
    pass

class ProofArtifact(BaseModel):
    """Pstack prove-it-works evidence attachment."""
    artifact_type: str  # "url_probe", "search_citation", "mobile_screenshot", "dom_element"
    uri_or_path: str
    verified: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)

class HandoffEnvelope(BaseModel):
    """
    Matt Pocock /handoff contract envelope.
    Ensures safe, strongly typed state handoff across agent boundaries.
    """
    handoff_id: str = Field(default_factory=lambda: f"hnd_{uuid.uuid4().hex[:8]}")
    source_agent: AgentRole
    target_agent: AgentRole
    contract_version: str = "v2.1"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: HandoffStatus = HandoffStatus.INITIATED
    payload: Dict[str, Any]
    proof_artifacts: List[ProofArtifact] = Field(default_factory=list)
    validation_notes: Optional[str] = None

    def validate_contract(self) -> bool:
        """Enforces schema invariants based on source and target roles."""
        if not self.payload:
            raise ContractViolationError(f"Handoff from {self.source_agent} to {self.target_agent} contains empty payload.")

        # Scout -> Auditor/Researcher: must include valid business profile
        if self.source_agent == AgentRole.SCOUT:
            if "company_name" not in self.payload:
                raise ContractViolationError("Scout payload must provide 'company_name'.")

        # Auditor -> Copywriter: must include audit findings
        if self.source_agent == AgentRole.AUDITOR:
            if "key_flaws" not in self.payload:
                raise ContractViolationError("Auditor payload must provide 'key_flaws'.")

        # Copywriter -> Paperclip Gate: must include actionable pitch & CTA
        if self.source_agent == AgentRole.COPYWRITER:
            if "whatsapp_message" not in self.payload:
                raise ContractViolationError("Copywriter payload must include 'whatsapp_message'.")

        self.status = HandoffStatus.VALIDATED
        return True
