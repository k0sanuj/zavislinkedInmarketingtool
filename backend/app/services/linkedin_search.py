"""
Service: LinkedIn Company Search

Given a company name (e.g. "Precision Dental Clinic"), searches Google and
LinkedIn to find the company's LinkedIn page URL. Returns match confidence.
"""

import asyncio
import logging
import random
import re
from typing import Optional, Tuple
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.ontology import MatchConfidence

logger = logging.getLogger(__name__)

# Google search for LinkedIn company pages
GOOGLE_SEARCH_URL = "https://www.google.com/search"
LINKEDIN_COMPANY_PATTERN = re.compile(
    r"https?://(?:www\.)?linkedin\.com/company/([a-zA-Z0-9\-_]+)"
)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


async def _random_delay():
    """Add a random delay between requests to avoid rate limiting."""
    delay = random.uniform(
        settings.SCRAPE_DELAY_MIN_SECONDS, settings.SCRAPE_DELAY_MAX_SECONDS
    )
    await asyncio.sleep(delay)


async def search_google_for_linkedin(
    company_name: str, location: Optional[str] = None
) -> Optional[str]:
    """
    Search Google for a company's LinkedIn page.

    Args:
        company_name: The company name to search for.
        location: Optional location to narrow search (e.g. "Dubai").

    Returns:
        LinkedIn company URL if found, None otherwise.
    """
    query = f'site:linkedin.com/company "{company_name}"'
    if location:
        query += f" {location}"

    params = {"q": query, "num": 5}
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        await _random_delay()
        try:
            response = await client.get(GOOGLE_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Google search failed for '{company_name}': {e}")
            return None

    soup = BeautifulSoup(response.text, "lxml")

    # Extract LinkedIn URLs from search results
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = LINKEDIN_COMPANY_PATTERN.search(href)
        if match:
            return f"https://www.linkedin.com/company/{match.group(1)}/"

    return None


async def search_linkedin_directly(
    company_name: str, li_at_cookie: str, jsessionid_cookie: Optional[str] = None
) -> Optional[str]:
    """
    Search LinkedIn's company search API directly using Sales Navigator cookies.

    Args:
        company_name: Company name to search for.
        li_at_cookie: LinkedIn li_at authentication cookie.
        jsessionid_cookie: LinkedIn JSESSIONID cookie.

    Returns:
        LinkedIn company URL if found, None otherwise.
    """
    search_url = "https://www.linkedin.com/voyager/api/search/blended"
    params = {
        "keywords": company_name,
        "origin": "GLOBAL_SEARCH_HEADER",
        "q": "all",
        "filters": "List(resultType->COMPANIES)",
        "count": 5,
        "start": 0,
    }

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "Cookie": f"li_at={li_at_cookie}",
        "csrf-token": jsessionid_cookie or "",
        "x-li-lang": "en_US",
        "x-restli-protocol-version": "2.0.0",
    }

    if jsessionid_cookie:
        headers["Cookie"] += f"; JSESSIONID={jsessionid_cookie}"

    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        await _random_delay()
        try:
            response = await client.get(search_url, params=params, headers=headers)
            if response.status_code == 401:
                logger.error("LinkedIn authentication failed — check cookies")
                return None
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"LinkedIn search failed for '{company_name}': {e}")
            return None

    data = response.json()

    # Parse the search results to find company URLs
    try:
        elements = data.get("data", {}).get("elements", [])
        for element in elements:
            items = element.get("elements", [])
            for item in items:
                entity = item.get("entity", "") or item.get("targetUrn", "")
                if "company" in entity.lower():
                    # Extract company public identifier
                    nav_url = item.get("navigationUrl", "")
                    if nav_url and "linkedin.com/company/" in nav_url:
                        return nav_url.split("?")[0]

                    # Try to build URL from entity URN
                    if entity.startswith("urn:li:company:"):
                        company_id = entity.replace("urn:li:company:", "")
                        return f"https://www.linkedin.com/company/{company_id}/"
    except (KeyError, TypeError, IndexError):
        logger.warning(f"Could not parse LinkedIn search results for '{company_name}'")

    return None


def _compute_match_confidence(
    original_name: str, linkedin_name: Optional[str]
) -> MatchConfidence:
    """Compute how closely a LinkedIn company name matches the input."""
    if not linkedin_name:
        return MatchConfidence.LOW

    original = original_name.lower().strip()
    found = linkedin_name.lower().strip()

    if original == found:
        return MatchConfidence.EXACT

    # Check if one contains the other
    if original in found or found in original:
        return MatchConfidence.HIGH

    # Check word overlap
    original_words = set(original.split())
    found_words = set(found.split())
    overlap = original_words & found_words
    if len(overlap) >= 2:
        return MatchConfidence.MEDIUM

    return MatchConfidence.LOW


async def find_company_linkedin(
    company_name: str,
    li_at_cookie: Optional[str] = None,
    jsessionid_cookie: Optional[str] = None,
    location: Optional[str] = None,
) -> Tuple[Optional[str], MatchConfidence]:
    """
    Main entry point: find a company's LinkedIn URL using multiple strategies.

    Strategy:
    1. Search Google for site:linkedin.com/company "company name"
    2. If that fails and we have LinkedIn cookies, search LinkedIn directly
    3. Compute match confidence

    Returns:
        Tuple of (linkedin_url or None, match_confidence)
    """
    # Strategy 1: Google search
    url = await search_google_for_linkedin(company_name, location=location)

    # Strategy 2: Direct LinkedIn search (if cookies available)
    if not url and li_at_cookie:
        url = await search_linkedin_directly(company_name, li_at_cookie, jsessionid_cookie)

    if not url:
        return None, MatchConfidence.NO_MATCH

    # We found a URL — now assess confidence (name comparison done later after scraping)
    return url, MatchConfidence.HIGH
