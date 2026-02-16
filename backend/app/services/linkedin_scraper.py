"""
Service: LinkedIn Company & Employee Scraper

Given a LinkedIn company URL, scrapes:
1. Company profile data (name, description, industry, employee count, etc.)
2. Employee list with job titles, filtered by target roles.

Uses LinkedIn cookies (Sales Navigator) for authenticated access.
"""

import asyncio
import logging
import random
from typing import Optional, List, Dict, Any

import httpx

from app.core.config import settings
from app.core.ontology import MatchConfidence

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _build_headers(li_at_cookie: str, jsessionid_cookie: Optional[str] = None) -> dict:
    """Build authenticated headers for LinkedIn API requests."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "Cookie": f"li_at={li_at_cookie}",
        "x-li-lang": "en_US",
        "x-restli-protocol-version": "2.0.0",
    }
    if jsessionid_cookie:
        headers["Cookie"] += f"; JSESSIONID={jsessionid_cookie}"
        headers["csrf-token"] = jsessionid_cookie
    return headers


async def _random_delay():
    delay = random.uniform(
        settings.SCRAPE_DELAY_MIN_SECONDS, settings.SCRAPE_DELAY_MAX_SECONDS
    )
    await asyncio.sleep(delay)


def _extract_company_slug(url: str) -> str:
    """Extract company slug or ID from LinkedIn URL."""
    url = url.rstrip("/")
    parts = url.split("/company/")
    if len(parts) > 1:
        return parts[1].split("/")[0].split("?")[0]
    raise ValueError(f"Invalid LinkedIn company URL: {url}")


async def scrape_company_profile(
    linkedin_url: str,
    li_at_cookie: str,
    jsessionid_cookie: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Scrape a company's LinkedIn profile page.

    Returns dict with: name, description, industry, employee_count,
    headquarters, website, logo_url, linkedin_company_id
    """
    slug = _extract_company_slug(linkedin_url)
    api_url = f"https://www.linkedin.com/voyager/api/organization/companies?decorationId=com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-12&q=universalName&universalName={slug}"

    headers = _build_headers(li_at_cookie, jsessionid_cookie)

    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        await _random_delay()
        try:
            response = await client.get(api_url, headers=headers)
            if response.status_code == 404:
                logger.warning(f"Company not found on LinkedIn: {slug}")
                return None
            if response.status_code == 401:
                logger.error("LinkedIn auth failed — check cookies")
                return None
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to scrape company {slug}: {e}")
            return None

    data = response.json()

    try:
        elements = data.get("elements", [])
        if not elements:
            return None

        company = elements[0]
        return {
            "linkedin_company_id": str(company.get("entityUrn", "")).split(":")[-1],
            "name_on_linkedin": company.get("name", ""),
            "description": company.get("description", ""),
            "industry": (company.get("companyIndustries", [{}]) or [{}])[0].get("localizedName", ""),
            "employee_count": company.get("staffCount", 0),
            "headquarters": _extract_headquarters(company),
            "website": company.get("companyPageUrl", ""),
            "logo_url": _extract_logo(company),
            "raw_data": company,
        }
    except (KeyError, TypeError, IndexError) as e:
        logger.error(f"Failed to parse company data for {slug}: {e}")
        return None


def _extract_headquarters(company: dict) -> str:
    """Extract headquarters string from company data."""
    hq = company.get("headquarter", {}) or {}
    parts = [
        hq.get("city", ""),
        hq.get("geographicArea", ""),
        hq.get("country", ""),
    ]
    return ", ".join(p for p in parts if p)


def _extract_logo(company: dict) -> Optional[str]:
    """Extract logo URL from company data."""
    logo = company.get("logo", {}) or {}
    image = logo.get("image", {}) or {}
    artifacts = image.get("rootUrl", "")
    return artifacts if artifacts else None


async def scrape_company_employees(
    linkedin_url: str,
    li_at_cookie: str,
    jsessionid_cookie: Optional[str] = None,
    max_employees: int = 30,
    target_titles: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Scrape employees from a company's LinkedIn page.

    Args:
        linkedin_url: Company LinkedIn URL.
        li_at_cookie: Auth cookie.
        jsessionid_cookie: CSRF cookie.
        max_employees: Maximum employees to scrape.
        target_titles: If provided, filter employees by these job title keywords.

    Returns:
        List of employee dicts with: full_name, first_name, last_name,
        job_title, linkedin_url, linkedin_member_id, location, profile_image_url
    """
    slug = _extract_company_slug(linkedin_url)
    headers = _build_headers(li_at_cookie, jsessionid_cookie)

    employees = []
    start = 0
    count = 10  # LinkedIn's page size

    while len(employees) < max_employees:
        # Build search URL — search for people at this company
        keywords_filter = ""
        if target_titles:
            title_query = " OR ".join(f'"{t}"' for t in target_titles)
            keywords_filter = f"&keywords={title_query}"

        api_url = (
            f"https://www.linkedin.com/voyager/api/search/blended"
            f"?keywords=&origin=FACETED_SEARCH"
            f"&q=all"
            f"&filters=List(currentCompany->{slug},resultType->PEOPLE)"
            f"&count={count}&start={start}"
            f"{keywords_filter}"
        )

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            await _random_delay()
            try:
                response = await client.get(api_url, headers=headers)
                if response.status_code in (401, 403):
                    logger.error("LinkedIn auth failed during employee scraping")
                    break
                response.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(f"Employee scraping failed for {slug}: {e}")
                break

        data = response.json()

        try:
            elements = data.get("data", {}).get("elements", [])
            people_elements = []
            for element in elements:
                people_elements.extend(element.get("elements", []))

            if not people_elements:
                break

            for person in people_elements:
                if len(employees) >= max_employees:
                    break

                title = person.get("title", {}).get("text", "") or ""
                name = person.get("title", {}).get("text", "") or ""

                # Parse from snippetText or headline
                headline = person.get("headline", {}).get("text", "") or ""

                employee = {
                    "full_name": _extract_name(person),
                    "first_name": _extract_first_name(person),
                    "last_name": _extract_last_name(person),
                    "job_title": headline,
                    "linkedin_url": _extract_profile_url(person),
                    "linkedin_member_id": _extract_member_id(person),
                    "location": person.get("subline", {}).get("text", ""),
                    "profile_image_url": _extract_profile_image(person),
                    "raw_data": person,
                }
                employees.append(employee)

        except (KeyError, TypeError, IndexError) as e:
            logger.error(f"Failed to parse employee data: {e}")
            break

        start += count

        # If we got fewer results than requested, we've exhausted the list
        if len(people_elements) < count:
            break

    return employees


def _extract_name(person: dict) -> str:
    title = person.get("title", {})
    if isinstance(title, dict):
        return title.get("text", "Unknown")
    return str(title) if title else "Unknown"


def _extract_first_name(person: dict) -> Optional[str]:
    name = _extract_name(person)
    parts = name.split(" ", 1)
    return parts[0] if parts else None


def _extract_last_name(person: dict) -> Optional[str]:
    name = _extract_name(person)
    parts = name.split(" ", 1)
    return parts[1] if len(parts) > 1 else None


def _extract_profile_url(person: dict) -> Optional[str]:
    nav_url = person.get("navigationUrl", "")
    if nav_url:
        return nav_url.split("?")[0]
    return None


def _extract_member_id(person: dict) -> Optional[str]:
    urn = person.get("targetUrn", "") or person.get("objectUrn", "")
    if urn and "member:" in urn:
        return urn.split("member:")[-1]
    return None


def _extract_profile_image(person: dict) -> Optional[str]:
    image = person.get("image", {}) or {}
    attrs = image.get("attributes", []) or []
    if attrs:
        mini_profile = attrs[0].get("miniProfile", {}) or {}
        picture = mini_profile.get("picture", {}) or {}
        root_url = picture.get("rootUrl", "")
        artifacts = picture.get("artifacts", []) or []
        if root_url and artifacts:
            largest = artifacts[-1]
            return root_url + largest.get("fileIdentifyingUrlPathSegment", "")
    return None
