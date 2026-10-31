"""
Sulekha Scraper
---------------
Scrapes business listings from Sulekha directory.
Returns name, phone, website presence for each business.
No API key needed — server-side rendered HTML.
"""

import time
import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE = "https://www.sulekha.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Sulekha city slugs
CITY_SLUGS = {
    "delhi": "delhi-city",
    "mumbai": "mumbai",
    "bangalore": "bangalore",
    "hyderabad": "hyderabad",
    "chennai": "chennai",
    "pune": "pune",
    "kolkata": "kolkata",
    "ahmedabad": "ahmedabad",
    "jaipur": "jaipur",
    "surat": "surat",
    "noida": "noida",
    "gurgaon": "gurgaon",
    "lucknow": "lucknow",
    "indore": "indore",
    "chandigarh": "chandigarh",
    "bhopal": "bhopal",
    "patna": "patna",
    "nagpur": "nagpur",
    "coimbatore": "coimbatore",
    "kochi": "kochi",
}

# Sulekha category slugs — local to popular, all business types
CATEGORY_SLUGS = {
    # Food & Hospitality
    "restaurant": "restaurants",
    "dhaba": "dhabas",
    "bakery": "bakeries",
    "catering": "caterers",
    "sweet shop": "sweet-shops",
    "cafe": "cafes",
    "food delivery": "food-delivery-services",
    "tiffin service": "tiffin-services",
    "hotel": "hotels",
    "banquet hall": "banquet-halls",
    "pg": "paying-guest-accommodation",

    # Beauty & Wellness
    "salon": "beauty-parlours",
    "spa": "spas",
    "gym": "gyms",
    "yoga": "yoga-classes",
    "physiotherapy": "physiotherapy-clinics",
    "dietician": "dieticians",

    # Health & Medical
    "clinic": "clinics",
    "hospital": "hospitals",
    "medical store": "medical-stores",
    "dental clinic": "dental-clinics",
    "eye clinic": "eye-clinics",
    "pathology lab": "pathology-labs",
    "ayurvedic clinic": "ayurvedic-clinics",

    # Education & Coaching
    "coaching center": "coaching-classes",
    "tuition": "home-tutors",
    "preschool": "pre-schools",
    "driving school": "driving-schools",
    "computer training": "computer-training-institutes",
    "dance classes": "dance-classes",
    "music classes": "music-classes",

    # Professional Services
    "ca firm": "chartered-accountants",
    "lawyer": "lawyers",
    "event management": "event-management-companies",
    "travel agent": "travel-agents",
    "insurance agent": "insurance-agents",
    "real estate agent": "real-estate-agents",
    "architect": "architects",
    "interior designer": "interior-designers",
    "digital marketing": "digital-marketing-companies",
    "web designer": "website-designers",
    "software company": "software-companies",

    # Retail & Shops
    "boutique": "boutiques",
    "jewellery shop": "jewellery-shops",
    "gift shop": "gift-shops",
    "mobile repair": "mobile-phone-repair-shops",
    "electronics repair": "electronics-repair-shops",
    "tailor": "tailors",
    "hardware store": "hardware-shops",
    "furniture shop": "furniture-shops",
    "optical shop": "opticians",
    "book store": "book-stores",
    "medical equipment": "medical-equipment-suppliers",

    # Home Services
    "plumber": "plumbers",
    "electrician": "electricians",
    "carpenter": "carpenters",
    "painter": "painters",
    "pest control": "pest-control-services",
    "home cleaning": "home-cleaning-services",
    "ac repair": "air-conditioner-repair-services",
    "appliance repair": "home-appliances-repair",
    "packers movers": "packers-and-movers",

    # Automobile
    "automobile workshop": "automobile-workshops",
    "car service": "car-service-centres",
    "bike repair": "two-wheeler-repair-shops",
    "car wash": "car-washing-services",

    # Photography & Creative
    "photographer": "photographers",
    "videographer": "videographers",
    "printing press": "printing-press",
    "graphic designer": "graphic-designers",
}


def _get(url: str, retries: int = 2) -> Optional[requests.Response]:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                return resp
            logging.debug(f"HTTP {resp.status_code} for {url}")
        except Exception as exc:
            logging.debug(f"Request failed ({attempt+1}): {exc}")
        time.sleep(1)
    return None


def _extract_phones(text: str) -> List[str]:
    return list(set(re.findall(r'[6-9]\d{9}', text)))


def _extract_emails(text: str) -> List[str]:
    all_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', text)
    noise = {'sulekha', 'example', '.png', '.jpg', '.css', '.js', '.svg', 'woff', 'schema'}
    return [e for e in all_emails if not any(n in e.lower() for n in noise)]


def _has_own_website(soup: BeautifulSoup) -> Optional[str]:
    """
    Check if business has its own website explicitly listed on profile.
    Only returns a URL if it's clearly labelled as the business's website.
    """
    noise_domains = [
        'sulekha', 'google', 'facebook', 'instagram', 'twitter',
        'youtube', 'justdial', 'linkedin', 'whatsapp', 'capshine',
        'schema.org', 'w3.org', 'apple.com', 'cloudflare',
    ]
    # Look for explicit "Website" label followed by a link
    for tag in soup.find_all(string=re.compile(r'^website$', re.I)):
        parent = tag.find_parent()
        if parent:
            link = parent.find_next('a', href=True)
            if link and link['href'].startswith('http'):
                href = link['href']
                if not any(d in href.lower() for d in noise_domains):
                    return href
    return None


def scrape_listing_page(category: str, city: str, page: int = 1) -> List[Dict[str, str]]:
    """
    Scrape a Sulekha listing page and return profile URLs + names.
    """
    city_slug = CITY_SLUGS.get(city.lower(), city.lower().replace(" ", "-"))
    cat_slug = CATEGORY_SLUGS.get(category.lower(), category.lower().replace(" ", "-") + "s")

    url = f"{BASE}/{cat_slug}/{city_slug}"
    if page > 1:
        url += f"/{page}"

    logging.info(f"Fetching Sulekha listing: {url}")
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Extract business names (h3 tags) and their profile links
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Profile pages follow /profile/business-name-city pattern
        if re.match(r'^/profile/', href):
            name_tag = a.find('h3') or a
            name = name_tag.get_text(strip=True)
            if name and len(name) > 3:
                results.append({
                    "name": name,
                    "profile_url": urljoin(BASE, href),
                })

    # Fallback: find all h3 names and look for nearest profile link in parent container
    if not results:
        for h3 in soup.find_all('h3'):
            name = h3.get_text(strip=True)
            if not name or len(name) < 4:
                continue
            profile_url = None
            # Walk up to find a parent that contains a /profile/ link
            for parent in h3.parents:
                link = parent.find('a', href=re.compile(r'^/profile/'))
                if link:
                    profile_url = urljoin(BASE, link['href'])
                    break
            results.append({"name": name, "profile_url": profile_url})

    logging.info(f"  Found {len(results)} listings on page {page}")
    return results


def scrape_profile_page(profile_url: str) -> Dict[str, Any]:
    """
    Scrape an individual Sulekha business profile page.
    Returns name, phones, emails, website, has_website flag.
    """
    resp = _get(profile_url)
    if not resp:
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    text = resp.text

    name_tag = soup.find('h1') or soup.find('h2')
    name = name_tag.get_text(strip=True) if name_tag else ""
    # Clean up sulekha appended city info
    name = re.split(r'\s+(burari|delhi|mumbai|bangalore|chennai|pune|kolkata)', name, flags=re.I)[0].strip()

    phones = _extract_phones(text)
    emails = _extract_emails(text)
    website = _has_own_website(soup)

    return {
        "name": name,
        "phones": phones,
        "emails": emails,
        "website": website,
        "has_website": website is not None,
        "profile_url": profile_url,
    }


def get_sulekha_businesses(
    category: str,
    city: str,
    limit: int = 10,
    pages: int = 2,
) -> List[Dict[str, Any]]:
    """
    Main entry: get businesses from Sulekha for a category+city.
    Prioritizes businesses with no website (best outreach targets).
    """
    listings: List[Dict[str, str]] = []

    for page in range(1, pages + 1):
        page_results = scrape_listing_page(category, city, page)
        listings.extend(page_results)
        if len(listings) >= limit * 2:
            break
        time.sleep(1.5)

    if not listings:
        logging.warning(f"No Sulekha listings found for {category} in {city}")
        return []

    businesses: List[Dict[str, Any]] = []
    seen: set = set()

    for listing in listings:
        if len(businesses) >= limit:
            break

        name = listing.get("name", "")
        if not name or name.lower() in seen:
            continue

        profile_url = listing.get("profile_url")
        if profile_url:
            time.sleep(1)
            details = scrape_profile_page(profile_url)
        else:
            details = {"name": name, "phones": [], "emails": [], "website": None, "has_website": False}

        # Use listing name if profile scrape didn't get a good one
        final_name = details.get("name") or name
        if not final_name or final_name.lower() in seen:
            continue

        seen.add(final_name.lower())
        phone = details.get("phones") or [None]
        phone = phone[0] if phone else None
        emails = details.get("emails") or []
        email = emails[0] if emails else None

        biz = {
            "name": final_name,
            "business_type": category,
            "location": city,
            "phone": phone,
            "email": email,
            "website": details.get("website"),
            "has_website": details.get("has_website", False),
            "source_url": profile_url or listing.get("profile_url", ""),
            "source": "sulekha",
            "contacted": False,
        }
        businesses.append(biz)
        logging.info(
            f"  [{category}] {final_name} | "
            f"phone={phone} | email={email} | website={biz['has_website']}"
        )

    # Best targets first: no website, then by phone availability
    businesses.sort(key=lambda x: (x["has_website"], x["phone"] is None))
    return businesses
