import pytest
from src.models.lead import BusinessProfile, Lead, LeadStatus, OutreachDraft
from src.storage.repository import LeadRepository, SessionRepository
from src.services.analyzer import BusinessAnalyzer
from src.scrapers.gmaps import clean_business_name, format_phone_number

def test_clean_business_name():
    # Noise/listicles should be rejected
    assert clean_business_name("Top 10 Restaurants in Mumbai") is None
    assert clean_business_name("Best Photographers in Mumbai") is None
    assert clean_business_name("Contact Us") is None
    assert clean_business_name("Inquire & Contact") is None
    
    # Real business names should pass
    assert clean_business_name("Donna Deli") == "Donna Deli"
    assert clean_business_name("Kyma Restaurant") == "Kyma Restaurant"
    assert clean_business_name("Dr Batra Dental Clinic") == "Dr Batra Dental Clinic"

def test_format_phone_number():
    assert format_phone_number("9820176421") == "+91 98201 76421"
    assert format_phone_number("+91-98201-76421") == "+91 98201 76421"
    assert format_phone_number("invalid") is None

def test_lead_repository(tmp_path):
    repo = LeadRepository(storage_dir=tmp_path)
    profile = BusinessProfile(
        company_name="Test Cafe",
        business_type="cafe",
        location="Mumbai",
        phone="+91 98201 11223"
    )
    lead = Lead(id="lead_123", profile=profile)
    repo.save(lead)

    loaded = repo.get_by_id("lead_123")
    assert loaded is not None
    assert loaded.profile.company_name == "Test Cafe"
    assert loaded.status == LeadStatus.DISCOVERED

    # Duplicate check
    dup = repo.find_duplicate(name="Test Cafe", phone="+91 98201 11223")
    assert dup is not None
    assert dup.id == "lead_123"

def test_analyzer_fallback():
    analyzer = BusinessAnalyzer()
    profile = BusinessProfile(
        company_name="Spice Villa",
        business_type="restaurant",
        location="Mumbai",
        has_website=False
    )
    draft = analyzer._fallback_draft(profile)
    assert draft.whatsapp_message is not None
    assert "Spice Villa" in draft.whatsapp_message
    assert "commission" in draft.whatsapp_message
    assert draft.email_subject is not None
    assert len(draft.pain_points) > 0

def test_site_inspector():
    from src.services.site_inspector import SiteInspector
    inspector = SiteInspector()
    
    # Test no-website audit
    profile_no_site = BusinessProfile(
        company_name="Royal Dhaba",
        business_type="restaurant",
        location="Delhi",
        has_website=False
    )
    audit = inspector.audit(profile_no_site)
    assert audit.has_ssl is False
    assert audit.is_mobile_responsive is False
    assert len(audit.key_flaws) >= 3
    assert "aggregators" in audit.quantified_loss.lower()

