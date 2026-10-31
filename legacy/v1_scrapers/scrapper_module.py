import time
import os
import csv
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CACHE_DIR = ".cache"
LEADS_FILE = "actionable_leads.json"
_UA = "JarvisLeadBot/1.0 (contact@example.com)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cache_key(query: str, location: str, limit: int) -> str:
    raw = f"{query}|{location}|{limit}"
    return hashlib.md5(raw.encode()).hexdigest()


def _load_cache(key: str) -> Optional[List[Dict[str, Any]]]:
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _save_cache(key: str, data: List[Dict[str, Any]]) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except OSError as exc:
        logging.warning(f"Cache write failed: {exc}")


def _existing_lead_names() -> set:
    """Return set of business names already in actionable_leads.json."""
    if not os.path.exists(LEADS_FILE):
        return set()
    try:
        with open(LEADS_FILE, "r") as f:
            leads = json.load(f)
        return {lead.get("name", "").strip().lower() for lead in leads}
    except (json.JSONDecodeError, OSError):
        return set()


# ---------------------------------------------------------------------------
# Contact-page email finder
# ---------------------------------------------------------------------------

def _can_fetch(url: str) -> bool:
    """Check robots.txt before fetching."""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(_UA, url)
    except Exception:
        return True  # allow on error


def find_contact_email(website: str) -> Optional[str]:
    """
    Try to find an email on the contact page of a website.
    Respects robots.txt, uses timeout and User-Agent header.
    """
    if not website:
        return None

    base = website if website.startswith("http") else f"https://{website}"
    contact_url = urljoin(base.rstrip("/") + "/", "contact")

    if not _can_fetch(contact_url):
        logging.info(f"robots.txt disallows fetching {contact_url}")
        return None

    headers = {"User-Agent": _UA}
    try:
        time.sleep(1)  # polite delay
        resp = requests.get(contact_url, headers=headers, timeout=8)
        if not resp.ok:
            return None
        import re
        match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", resp.text)
        return match.group(0) if match else None
    except Exception as exc:
        logging.debug(f"Contact email fetch failed for {website}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def geocode_location(location: str) -> Optional[tuple]:
    """Geocode a location string via Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": _UA}
    time.sleep(1)
    try:
        resp = requests.get(url, params={"q": location, "format": "json"}, headers=headers, timeout=10)
        if resp.ok and resp.json():
            data = resp.json()[0]
            return float(data["lat"]), float(data["lon"])
    except Exception as exc:
        logging.error(f"Geocoding error: {exc}")
    return None


# ---------------------------------------------------------------------------
# OSM
# ---------------------------------------------------------------------------

def query_overpass(query_body: str) -> List[Dict[str, Any]]:
    url = "https://overpass-api.de/api/interpreter"
    headers = {"User-Agent": _UA}
    resp = requests.post(url, data=query_body, headers=headers, timeout=30)
    resp.raise_for_status()
    time.sleep(1)
    return resp.json().get("elements", [])


def get_osm_businesses(query: str, location: str, limit: int) -> List[Dict[str, Any]]:
    """Fetch named businesses from OpenStreetMap via Overpass API."""
    cache_key = _cache_key(query, location, limit)
    cached = _load_cache(cache_key)
    if cached is not None:
        logging.info(f"OSM cache hit for key={cache_key}")
        return cached

    coords = geocode_location(location)
    if not coords:
        return []

    lat, lon = coords
    radius = 0.1  # ~11 km box

    # Use proper Overpass tag filters: shop, office, or craft that have a name tag
    overpass_query = f"""
[out:json][timeout:25];
(
  node["shop"]["name"]({lat-radius},{lon-radius},{lat+radius},{lon+radius});
  node["office"]["name"]({lat-radius},{lon-radius},{lat+radius},{lon+radius});
  node["craft"]["name"]({lat-radius},{lon-radius},{lat+radius},{lon+radius});
  way["shop"]["name"]({lat-radius},{lon-radius},{lat+radius},{lon+radius});
  way["office"]["name"]({lat-radius},{lon-radius},{lat+radius},{lon+radius});
  way["craft"]["name"]({lat-radius},{lon-radius},{lat+radius},{lon+radius});
);
out body;
"""

    elements = query_overpass(overpass_query)
    existing = _existing_lead_names()

    leads: List[Dict[str, Any]] = []
    for element in elements:
        if len(leads) >= limit:
            break
        tags = element.get("tags", {})
        name = tags.get("name", "").strip()
        if not name:
            continue
        if name.lower() in existing:
            continue
        leads.append({
            "name": name,
            "website": tags.get("website", ""),
            "email": tags.get("email", ""),
            "phone": tags.get("phone", ""),
            "city": location,
            "contacted": False,
        })

    _save_cache(cache_key, leads)
    return leads


# ---------------------------------------------------------------------------
# Google Places (optional)
# ---------------------------------------------------------------------------

def get_google_places_businesses(query: str, location: str, limit: int) -> List[Dict[str, Any]]:
    """
    Fetch businesses from Google Places API.
    Only used when GOOGLE_PLACES_API_KEY is set in the environment.
    """
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        return []

    text_search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": f"{query} in {location}", "key": api_key}

    try:
        resp = requests.get(text_search_url, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception as exc:
        logging.error(f"Google Places error: {exc}")
        return []

    existing = _existing_lead_names()
    leads: List[Dict[str, Any]] = []
    for place in results[:limit]:
        name = place.get("name", "").strip()
        if not name or name.lower() in existing:
            continue
        leads.append({
            "name": name,
            "website": "",
            "email": "",
            "phone": place.get("formatted_phone_number", ""),
            "city": location,
            "contacted": False,
        })
    return leads


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def get_csv_businesses(limit: int) -> List[Dict[str, Any]]:
    """Load businesses from leads_input.csv if it exists."""
    csv_path = "leads_input.csv"
    businesses: List[Dict[str, Any]] = []
    if not os.path.exists(csv_path):
        return businesses
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            businesses.append({
                "name": row.get("name", "Unknown"),
                "website": row.get("website", ""),
                "email": row.get("email", ""),
                "phone": row.get("phone", ""),
                "city": row.get("city", ""),
                "contacted": False,
            })
    return businesses


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_businesses(query: str, location: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find businesses using CSV, Google Places, or OpenStreetMap (priority order).
    Mock leads returned when USE_MOCK_LEADS=true.
    """
    limit = int(limit)

    if os.getenv("USE_MOCK_LEADS", "false").lower() == "true":
        logging.info("Using mock leads.")
        return [
            {"name": "San Francisco Tech Solutions", "website": "example.com", "contacted": False},
            {"name": "Growth Partners", "website": "example.net", "contacted": False},
        ]

    # 1. CSV
    leads = get_csv_businesses(limit)
    if leads:
        logging.info(f"Found {len(leads)} leads in leads_input.csv")
        return leads

    # 2. Google Places (optional)
    leads = get_google_places_businesses(query, location, limit)
    if leads:
        logging.info(f"Found {len(leads)} leads via Google Places")
        return leads

    # 3. OSM fallback
    leads = get_osm_businesses(query, location, limit)
    if leads:
        logging.info(f"Found {len(leads)} leads via OSM")
        return leads

    logging.warning("No businesses found from any source.")
    return []
