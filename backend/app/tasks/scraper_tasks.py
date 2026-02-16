"""
Celery Tasks: Scraper Job Orchestration

Two-phase scraping pipeline:
Phase 1: Company Discovery — find LinkedIn URLs and company profiles
Phase 2: Employee Scraping — scrape employees from selected companies
"""

import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.tasks.celery_app import celery_app
from app.core.ontology import ObjectStatus, MatchConfidence
from app.services.linkedin_search import find_company_linkedin
from app.services.linkedin_scraper import scrape_company_profile, scrape_company_employees
from app.services.ai_matcher import evaluate_role_match

logger = logging.getLogger(__name__)


def _get_sync_session():
    """Get a synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL_SYNC)
    return Session(engine)


# ---------------------------------------------------------------------------
# Phase 1: Company Discovery
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, name="app.tasks.scraper_tasks.run_company_discovery")
def run_company_discovery(self, job_id: str):
    """Find LinkedIn URLs and scrape company profiles only (no employees)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_company_discovery_async(self, job_id))
    finally:
        loop.close()


async def _run_company_discovery_async(task, job_id: str):
    """Phase 1: Find LinkedIn URLs and scrape basic company data."""
    from app.models.ontology import ScraperJob, Company, CompanyLinkedIn

    session = _get_sync_session()

    try:
        job = session.get(ScraperJob, uuid.UUID(job_id))
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = ObjectStatus.PROCESSING
        job.last_launched_at = datetime.utcnow()
        session.commit()

        # Get LinkedIn credentials
        linkedin_account = job.linkedin_account
        li_at = linkedin_account.li_at_cookie
        jsessionid = linkedin_account.jsessionid_cookie

        # Get companies from data source
        companies = (
            session.query(Company)
            .filter(Company.data_source_id == job.data_source_id)
            .all()
        )

        total = len(companies)
        matched = 0
        not_found = 0

        for i, company in enumerate(companies):
            if i >= job.max_companies_per_launch:
                break

            task.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": min(total, job.max_companies_per_launch),
                    "company": company.name,
                    "phase": "company_discovery",
                },
            )

            try:
                if company.status == ObjectStatus.COMPLETED:
                    continue

                company.status = ObjectStatus.PROCESSING
                session.commit()

                # Step 1: Find LinkedIn URL
                linkedin_url, confidence = await find_company_linkedin(
                    company.name,
                    li_at_cookie=li_at,
                    jsessionid_cookie=jsessionid,
                )

                if not linkedin_url:
                    company.status = ObjectStatus.NOT_FOUND
                    not_found += 1
                    session.commit()
                    continue

                # Step 2: Scrape company profile (name, employee count, industry, etc.)
                profile_data = await scrape_company_profile(linkedin_url, li_at, jsessionid)

                company_linkedin = CompanyLinkedIn(
                    company_id=company.id,
                    linkedin_url=linkedin_url,
                    match_confidence=confidence,
                    **(profile_data or {}),
                )
                session.add(company_linkedin)
                session.flush()

                # Refine confidence based on name comparison
                if profile_data and profile_data.get("name_on_linkedin"):
                    from app.services.linkedin_search import _compute_match_confidence
                    refined = _compute_match_confidence(
                        company.name, profile_data["name_on_linkedin"]
                    )
                    company_linkedin.match_confidence = refined

                company.status = ObjectStatus.COMPLETED
                matched += 1
                session.commit()

            except Exception as e:
                logger.error(f"Error discovering company '{company.name}': {e}")
                company.status = ObjectStatus.FAILED
                session.commit()
                continue

        # Update job stats
        job.companies_processed = min(total, job.max_companies_per_launch)
        job.companies_matched = matched
        job.companies_not_found = not_found
        job.status = ObjectStatus.COMPLETED
        session.commit()

        logger.info(
            f"Discovery job {job_id} completed: {matched}/{total} companies matched, "
            f"{not_found} not found"
        )

    except Exception as e:
        logger.error(f"Discovery job {job_id} failed: {e}")
        try:
            job = session.get(ScraperJob, uuid.UUID(job_id))
            if job:
                job.status = ObjectStatus.FAILED
                job.last_error = str(e)
                session.commit()
        except Exception:
            pass
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Phase 2: Employee Scraping
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, name="app.tasks.scraper_tasks.run_employee_scraping")
def run_employee_scraping(self, job_id: str):
    """Scrape employees from selected companies using Sales Navigator."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_employee_scraping_async(self, job_id))
    finally:
        loop.close()


async def _run_employee_scraping_async(task, job_id: str):
    """Phase 2: Scrape employees from pre-discovered companies."""
    from app.models.ontology import (
        ScraperJob, Company, CompanyLinkedIn, Employee, MatchResult
    )

    session = _get_sync_session()

    try:
        job = session.get(ScraperJob, uuid.UUID(job_id))
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = ObjectStatus.PROCESSING
        job.last_launched_at = datetime.utcnow()
        session.commit()

        # Get LinkedIn credentials
        linkedin_account = job.linkedin_account
        li_at = linkedin_account.li_at_cookie
        jsessionid = linkedin_account.jsessionid_cookie

        # Get selected companies (only ones with LinkedIn profiles)
        selected_ids = job.selected_company_ids or []
        companies = (
            session.query(Company)
            .filter(Company.id.in_([uuid.UUID(cid) for cid in selected_ids]))
            .all()
        )

        total = len(companies)
        employees_scraped = 0

        for i, company in enumerate(companies):
            task.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": total,
                    "company": company.name,
                    "phase": "employee_scraping",
                },
            )

            try:
                # Get the company's LinkedIn profile
                company_linkedin = (
                    session.query(CompanyLinkedIn)
                    .filter(CompanyLinkedIn.company_id == company.id)
                    .first()
                )
                if not company_linkedin:
                    continue

                linkedin_url = company_linkedin.linkedin_url

                # Scrape employees
                employees = await scrape_company_employees(
                    linkedin_url,
                    li_at,
                    jsessionid,
                    max_employees=job.max_employees_per_company,
                    target_titles=job.target_job_titles,
                )

                for emp_data in employees:
                    raw = emp_data.pop("raw_data", None)
                    employee = Employee(
                        company_linkedin_id=company_linkedin.id,
                        raw_data=raw,
                        **emp_data,
                    )
                    session.add(employee)
                    session.flush()

                    # AI role matching
                    if job.use_ai_matching and job.target_job_titles:
                        is_match, conf, reasoning, matched_role = await evaluate_role_match(
                            employee.job_title,
                            job.target_job_titles,
                            custom_prompt=job.ai_matching_prompt,
                        )
                        match_result = MatchResult(
                            employee_id=employee.id,
                            target_roles=job.target_job_titles,
                            is_match=is_match,
                            confidence=conf,
                            reasoning=reasoning,
                            matched_role=matched_role,
                            score=1.0 if conf == MatchConfidence.EXACT else 0.8 if conf == MatchConfidence.HIGH else 0.5 if conf == MatchConfidence.MEDIUM else 0.2,
                        )
                        session.add(match_result)

                    employees_scraped += 1

                session.commit()

            except Exception as e:
                logger.error(f"Error scraping employees for '{company.name}': {e}")
                session.commit()
                continue

        # Update job stats
        job.companies_processed = total
        job.employees_scraped = employees_scraped
        job.status = ObjectStatus.COMPLETED
        session.commit()

        logger.info(
            f"Employee scraping job {job_id} completed: {employees_scraped} employees from {total} companies"
        )

    except Exception as e:
        logger.error(f"Employee scraping job {job_id} failed: {e}")
        try:
            job = session.get(ScraperJob, uuid.UUID(job_id))
            if job:
                job.status = ObjectStatus.FAILED
                job.last_error = str(e)
                session.commit()
        except Exception:
            pass
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Legacy: Combined task (kept for backward compatibility with existing jobs)
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, name="app.tasks.scraper_tasks.run_scraper_job")
def run_scraper_job(self, job_id: str):
    """Route to appropriate task based on job_type."""
    from app.models.ontology import ScraperJob
    session = _get_sync_session()
    try:
        job = session.get(ScraperJob, uuid.UUID(job_id))
        if not job:
            return
        job_type = job.job_type or "company_discovery"
    finally:
        session.close()

    if job_type == "employee_scraping":
        run_employee_scraping(job_id)
    else:
        run_company_discovery(job_id)


# ---------------------------------------------------------------------------
# Scheduled job checker
# ---------------------------------------------------------------------------
@celery_app.task(name="app.tasks.scraper_tasks.check_scheduled_jobs")
def check_scheduled_jobs():
    """Periodic task: check for scheduled jobs that need to run."""
    from app.models.ontology import ScraperJob, Schedule

    session = _get_sync_session()
    try:
        now = datetime.utcnow()
        jobs = (
            session.query(ScraperJob)
            .join(Schedule)
            .filter(
                ScraperJob.is_enabled == True,
                ScraperJob.status != ObjectStatus.PROCESSING,
                Schedule.is_active == True,
                Schedule.next_run_at <= now,
            )
            .all()
        )

        for job in jobs:
            logger.info(f"Launching scheduled job: {job.name} ({job.id})")
            run_scraper_job.delay(str(job.id))

            # Update next_run_at based on frequency
            schedule = job.schedule
            if schedule:
                schedule.last_run_at = now
                _compute_next_run(schedule)

        session.commit()
    finally:
        session.close()


def _compute_next_run(schedule):
    """Compute the next run time for a schedule."""
    from datetime import timedelta

    now = datetime.utcnow()
    if schedule.frequency == "once":
        schedule.is_active = False
        schedule.next_run_at = None
    elif schedule.frequency == "daily":
        schedule.next_run_at = now + timedelta(hours=24 // max(schedule.times_per_day, 1))
    elif schedule.frequency == "weekly":
        schedule.next_run_at = now + timedelta(weeks=1)
    elif schedule.frequency == "monthly":
        schedule.next_run_at = now + timedelta(days=30)
