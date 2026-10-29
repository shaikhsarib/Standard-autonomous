"""
ECC (Everything Claude Code) Dual-Engine Shield.
Implements AgentShield for development code auditing and runtime outbound SDR compliance.
Source: https://github.com/affaan-m/ECC by Affaan Mustafa.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.models.lead import BusinessProfile, AuditReport

logger = logging.getLogger(__name__)


class ECCCodeSafetyReport(BaseModel):
    is_safe: bool
    safety_score: float = 100.0
    vulnerabilities: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, CRITICAL


class ECCPitchComplianceReport(BaseModel):
    is_compliant: bool
    compliance_score: float = 100.0
    violations: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    grounded_checks: Dict[str, bool] = Field(default_factory=dict)


class ECCShield:
    """
    ECC AgentShield & Compliance Verifier.
    Works in dual mode:
    1. Development Code Safety Verification
    2. Runtime Outbound Outreach Pitch Compliance
    """

    # Secret key regex patterns
    SECRET_PATTERNS = [
        (r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*=\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", "Hardcoded API secret token"),
        (r"AIzaSy[0-9A-Za-z_-]{33}", "Google / Gemini API Key pattern"),
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key pattern"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
        (r"(?i)(?:bot)?[0-9]{8,12}:[a-zA-Z0-9_-]{30,50}", "Telegram Bot Token"),
    ]

    # Dangerous code execution patterns
    DANGEROUS_CODE_PATTERNS = [
        (r"(?<!def\s)\beval\(", "Unsafe dynamic eval() execution"),
        (r"(?<!def\s)\bexec\(", "Unsafe dynamic exec() execution"),
        (r"os\.system\s*\(\s*['\"][^'\"]*(?:rm\s+-rf|del\s+/f|format\s+)[^'\"]*['\"]\)", "Dangerous system destruction command"),
        (r"(?i)SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*=\s*['\"]\s*\+\s*", "Potential raw SQL string concatenation / SQLi risk"),
    ]

    # Prompt / Internal leak patterns
    INTERNAL_LEAK_PATTERNS = [
        (r"<SYSTEM_PROMPT>", "Internal system prompt tag leak"),
        (r"\{[\"']intent[\"']\s*:\s*[\"']", "Raw JSON intent payload leaked in pitch"),
        (r"<scratchpad>", "Agent scratchpad token leaked in client copy"),
        (r"<memory>", "Internal agent memory tag leaked in copy"),
        (r"Traceback\s+\(most\s+recent\s+call\s+last\):", "Python stack trace leaked in pitch"),
    ]

    # Spam / Aggressive sales words
    SPAM_PATTERNS = [
        (r"(?i)\bguaranteed\s+(?:millions?|\$?[0-9]+k\s+in\s+[0-9]+\s+days)\b", "Unsubstantiated financial guarantee claim"),
        (r"!{3,}", "Excessive exclamation marks (Spam filter trigger)"),
        (r"(?i)\bact\s+now\s+or\s+lose\s+everything\b", "High-pressure aggressive sales tactic"),
    ]

    # --------------------------------------------------------------------------
    # 1. DEVELOPMENT HARNESS: CODE SAFETY AUDIT
    # --------------------------------------------------------------------------
    @classmethod
    def audit_code_safety(cls, code: str) -> ECCCodeSafetyReport:
        """Audits source code for leaked secrets, dangerous execution, or SQLi."""
        vulnerabilities = []

        # Check secrets
        for pattern, desc in cls.SECRET_PATTERNS:
            if re.search(pattern, code):
                vulnerabilities.append(f"CRITICAL: {desc} detected.")

        # Check dangerous execution
        for pattern, desc in cls.DANGEROUS_CODE_PATTERNS:
            if re.search(pattern, code):
                vulnerabilities.append(f"HIGH: {desc} detected.")

        safety_score = max(0.0, 100.0 - (len(vulnerabilities) * 35.0))
        risk_level = "CRITICAL" if any("CRITICAL" in v for v in vulnerabilities) else ("MEDIUM" if vulnerabilities else "LOW")
        is_safe = len(vulnerabilities) == 0

        return ECCCodeSafetyReport(
            is_safe=is_safe,
            safety_score=safety_score,
            vulnerabilities=vulnerabilities,
            risk_level=risk_level
        )

    # --------------------------------------------------------------------------
    # 2. RUNTIME AGENCY OS: OUTBOUND SDR PITCH COMPLIANCE
    # --------------------------------------------------------------------------
    @classmethod
    def audit_outbound_pitch(
        cls,
        pitch_text: str,
        profile: BusinessProfile,
        audit: Optional[AuditReport] = None
    ) -> ECCPitchComplianceReport:
        """
        Audits an outbound SDR pitch (Email or WhatsApp) before dispatch.
        Guarantees anti-slop, grounded evidence, zero internal leaks, and compliance.
        """
        violations = []
        grounded_checks = {}

        # 1. Check for Internal Leaks / Stack Traces
        for pattern, desc in cls.INTERNAL_LEAK_PATTERNS:
            if re.search(pattern, pitch_text):
                violations.append(f"PII/LEAK: {desc} in pitch draft.")

        # 2. Check for Spam / Aggressive Slop
        for pattern, desc in cls.SPAM_PATTERNS:
            if re.search(pattern, pitch_text):
                violations.append(f"SPAM/SLOP: {desc}.")

        # 3. Grounded Technical Verification
        # If pitch claims the site is slow / load time, verify audit report
        if re.search(r"(?i)\b(?:load\s*time|speed|seconds?\s*to\s*load|slow\s*site)\b", pitch_text):
            if audit and audit.load_time_seconds and audit.load_time_seconds > 0:
                grounded_checks["load_time_evidence"] = True
            else:
                grounded_checks["load_time_evidence"] = False
                violations.append("UNGROUNDED CLAIM: Pitch claims site speed issue but no empirical load time was recorded.")

        # If pitch claims SSL / Security vulnerability, verify audit report
        if re.search(r"(?i)\b(?:no\s*ssl|missing\s*ssl|without\s*ssl|not\s*secure|insecure\s*site)\b", pitch_text):
            if audit:
                if audit.has_ssl is False:
                    grounded_checks["ssl_evidence"] = True
                else:
                    grounded_checks["ssl_evidence"] = False
                    violations.append("FALSE CLAIM: Pitch claims site lacks SSL, but audit verified SSL is active.")
            else:
                grounded_checks["ssl_evidence"] = False
                violations.append("UNGROUNDED CLAIM: Pitch claims SSL flaw but no SSL inspection was performed.")

        # If pitch claims lack of WhatsApp widget, verify audit report
        if re.search(r"(?i)\b(?:whatsapp\s*button|instant\s*quote\s*widget|chat\s*link)\b", pitch_text):
            if audit and audit.has_whatsapp_widget is not None:
                grounded_checks["whatsapp_evidence"] = True
            else:
                grounded_checks["whatsapp_evidence"] = False

        # 4. Target Identity Verification
        # Check that pitch actually addresses the recipient's business context or domain
        name_tokens = [t.lower() for t in profile.company_name.split() if len(t) > 2]
        pitch_lower = pitch_text.lower()
        has_business_name = any(token in pitch_lower for token in name_tokens)
        grounded_checks["personalized_to_target"] = has_business_name
        if not has_business_name:
            violations.append("GENERIC PITCH: Company name does not appear in the pitch copy.")

        # 5. Length & Formatting Integrity
        if len(pitch_text.strip()) < 20:
            violations.append("MALFORMED: Pitch is too short to be viable copy (<20 chars).")

        compliance_score = max(0.0, 100.0 - (len(violations) * 20.0))
        is_compliant = len(violations) == 0
        risk_level = "HIGH" if any("LEAK" in v for v in violations) else ("MEDIUM" if violations else "LOW")

        return ECCPitchComplianceReport(
            is_compliant=is_compliant,
            compliance_score=compliance_score,
            violations=violations,
            risk_level=risk_level,
            grounded_checks=grounded_checks
        )


# Global singleton instance
ecc_shield = ECCShield()
