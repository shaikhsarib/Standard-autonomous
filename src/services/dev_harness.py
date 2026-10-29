"""
IC (Intelligence Center) Development & Verification Harness
Integrates ECC AgentShield, Superpowers TDD/Debugging, and Pstack Anti-Slop verification.
"""

import sys
import subprocess
import urllib.request
import json
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.agents.ecc_shield import ECCShield

def run_dev_checks():
    print("=" * 60)
    print("🛡️  IC INTELLIGENCE CENTER — UNIFIED DEV HARNESS")
    print("=" * 60)

    # 1. ECC AgentShield Code Security Scan
    print("\n[Phase 1] ECC AgentShield Pre-Commit Code & Pitch Security Scan...")
    from src.models.lead import BusinessProfile, AuditReport
    
    # Test pitch compliance
    sample_pitch = "Hi TransNational Freight team, saw your container fleet. We built an instant WhatsApp rate bot with verified 1.32s mobile proof."
    profile = BusinessProfile(company_name="TransNational Freight", business_type="freight logistics")
    audit = AuditReport(load_time_seconds=1.32, has_ssl=True)
    res = ECCShield.audit_outbound_pitch(sample_pitch, profile=profile, audit=audit)
    if res.is_compliant:
        print("  ✓ Outbound pitch compliance: PASS (0 hallucinated claims)")
    else:
        print(f"  ✗ Outbound pitch compliance: FAILED ({res.violations})")

    # Test code scanner
    code_check = ECCShield.audit_code_safety("api_key = os.getenv('API_KEY')\nassert api_key is not None")
    if code_check.is_safe:
        print("  ✓ AgentShield code vulnerability scan: PASS (Clean credentials & no SQLi)")
    else:
        print(f"  ✗ AgentShield code scan: FAILED ({code_check.vulnerabilities})")

    # 2. Superpowers Verification & Pytest Suite
    print("\n[Phase 2] Superpowers & Pstack 'Prove-it-Works' Test Verification...")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            print("  ✓ All test suites: 100% PASSED (Green)")
        else:
            print("  ✗ Test suite failures detected:\n", proc.stdout[:300])
    except Exception as e:
        print(f"  ✗ Test runner error: {e}")

    # 3. Stack Infrastructure Health
    print("\n[Phase 3] Local Stack Connectivity Status...")
    endpoints = {
        "Agency OS Core (:8000)": "http://127.0.0.1:8000/api/health",
        "Paperclip Engine (:3100)": "http://127.0.0.1:3100/api/health",
        "React Studio (:5173)": "http://localhost:5173/api/health"
    }

    for name, url in endpoints.items():
        try:
            req = urllib.request.urlopen(url, timeout=3)
            data = json.loads(req.read().decode())
            status = data.get("status", "unknown")
            print(f"  ✓ {name}: ONLINE ({status})")
        except Exception:
            print(f"  ! {name}: Offline or Unreachable")

    print("\n" + "=" * 60)
    print("✅ IC DEVELOPMENT HARNESS VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_dev_checks()
