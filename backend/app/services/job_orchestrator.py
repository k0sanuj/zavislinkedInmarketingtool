"""
Service: Job Orchestrator

High-level operations for creating, launching, and managing scraper jobs.
Supports two-phase workflow:
  Phase 1: Company Discovery — find LinkedIn URLs and company profiles
  Phase 2: Employee Scraping — scrape employees from selected companies
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ontology import (
    ScraperJob, DataSource, Company, CompanyLinkedIn,
    LinkedInAccount, Schedule, Employee, MatchResult,
    GoogleOAuthToken,
)
from app.core.ontology import ObjectStatus, MatchConfidence
from app.schemas.schemas import (
    ScraperJobCreate, CompanyDiscoveryCreate, EmployeeScrapingCreate,
    ScraperJobResponse, ScraperJobLaunchResponse,
    JobSummary, CompanySearchResult, CompanyDetailResponse,
)
from app.services.google_sheets import read_column_values, read_csv_column
from app.tasks.scraper_tasks import run_scraper_job

logger = logging.getLogger(__name__)


async def create_company_discovery_job(
    db: AsyncSession, data: CompanyDiscoveryCreate
) -> ScraperJob:
    """Create a Phase 1 company discovery job."""
    job = ScraperJob(
        name=data.name,
        job_type="company_discovery",
        data_source_id=data.data_source_id,
        linkedin_account_id=data.linkedin_account_id,
        max_companies_per_launch=data.max_companies_per_launch,
        status=ObjectStatus.PENDING,
    )
    db.add(job)
    await db.flush()
    return job


async def create_employee_scraping_job(
    db: AsyncSession, data: EmployeeScrapingCreate
) -> ScraperJob:
    """Create a Phase 2 employee scraping job from selected companies."""
    # Get parent job to inherit data_source_id
    parent = await db.get(ScraperJob, data.parent_job_id)
    if not parent:
        raise ValueError(f"Parent job {data.parent_job_id} not found")

    job = ScraperJob(
        name=data.name,
        job_type="employee_scraping",
        parent_job_id=data.parent_job_id,
        data_source_id=parent.data_source_id,
        linkedin_account_id=data.linkedin_account_id,
        selected_company_ids=[str(cid) for cid in data.selected_company_ids],
        target_job_titles=data.target_job_titles,
        max_employees_per_company=data.max_employees_per_company,
        use_ai_matching=data.use_ai_matching,
        ai_matching_prompt=data.ai_matching_prompt,
        status=ObjectStatus.PENDING,
    )
    db.add(job)
    await db.flush()
    return job


async def create_scraper_job(
    db: AsyncSession, job_data: ScraperJobCreate
) -> ScraperJob:
    """Legacy: Create a combined scraper job."""
    schedule = None
    if job_data.schedule_frequency != "once":
        schedule = Schedule(
            frequency=job_data.schedule_frequency,
            times_per_day=job_data.schedule_times_per_day,
            next_run_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(schedule)
        await db.flush()

    job = ScraperJob(
        name=job_data.name,
        job_type="company_discovery",
        data_source_id=job_data.data_source_id,
        linkedin_account_id=job_data.linkedin_account_id,
        schedule_id=schedule.id if schedule else None,
        max_employees_per_company=job_data.max_employees_per_company,
        max_companies_per_launch=job_data.max_companies_per_launch,
        target_job_titles=job_data.target_job_titles,
        use_ai_matching=job_data.use_ai_matching,
        ai_matching_prompt=job_data.ai_matching_prompt,
        status=ObjectStatus.PENDING,
    )
    db.add(job)
    await db.flush()
    return job


async def ingest_data_source(db: AsyncSession, data_source_id: uuid.UUID) -> DataSource:
    """
    Action: CONNECT_DATA_SOURCE
    Reads companies from the data source and creates Company objects.
    """
    ds = await db.get(DataSource, data_source_id)
    if not ds:
        raise ValueError(f"DataSource {data_source_id} not found")

    try:
        if ds.source_type == "google_sheet" and ds.google_sheet_url:
            result = await db.execute(
                select(GoogleOAuthToken).order_by(GoogleOAuthToken.created_at.desc()).limit(1)
            )
            token = result.scalar_one_or_none()
            if not token:
                raise ValueError("Google account not connected. Please connect your Google account first.")
            token_data = {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "token_uri": token.token_uri,
                "scopes": token.scopes,
            }
            values, count = read_column_values(
                ds.google_sheet_url, ds.column_name, token_data, ds.sheet_tab_name
            )
        elif ds.source_type == "csv_upload" and ds.raw_data:
            values, count = read_csv_column(ds.raw_data.get("file_path", ""), ds.column_name)
        elif ds.source_type == "manual" and ds.raw_data:
            values = ds.raw_data.get("values", [])
            count = len(values)
        else:
            raise ValueError(f"Unsupported data source type: {ds.source_type}")

        for i, value in enumerate(values):
            company = Company(
                data_source_id=ds.id,
                name=value,
                original_input=value,
                row_index=i,
                status=ObjectStatus.PENDING,
            )
            db.add(company)

        ds.row_count = count
        ds.status = ObjectStatus.COMPLETED
        await db.flush()
        return ds

    except Exception as e:
        ds.status = ObjectStatus.FAILED
        await db.flush()
        raise


async def launch_job(db: AsyncSession, job_id: uuid.UUID) -> ScraperJobLaunchResponse:
    """Dispatch a job to the Celery task queue."""
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    if job.status == ObjectStatus.PROCESSING:
        return ScraperJobLaunchResponse(
            job_id=job.id,
            status="already_running",
            message="Job is already running",
        )

    job.is_enabled = True
    job.status = ObjectStatus.PENDING
    await db.flush()

    task = run_scraper_job.delay(str(job.id))

    return ScraperJobLaunchResponse(
        job_id=job.id,
        status="launched",
        message=f"Job '{job.name}' has been launched",
        task_id=task.id,
    )


async def pause_job(db: AsyncSession, job_id: uuid.UUID) -> ScraperJob:
    """Pause a job."""
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    job.is_enabled = False
    job.status = ObjectStatus.PAUSED
    await db.flush()
    return job


async def get_job_companies(
    db: AsyncSession, job_id: uuid.UUID, filter_type: str = "all"
) -> List[CompanyDetailResponse]:
    """Get companies for a job with rich LinkedIn data, filtered by type."""
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    result = await db.execute(
        select(Company)
        .options(selectinload(Company.linkedin_profile))
        .where(Company.data_source_id == job.data_source_id)
    )
    companies = result.scalars().all()

    response = []
    for c in companies:
        lp = c.linkedin_profile
        has_linkedin = lp is not None

        if filter_type == "with_linkedin" and not has_linkedin:
            continue
        if filter_type == "without_linkedin" and has_linkedin:
            continue

        response.append(CompanyDetailResponse(
            id=c.id,
            name=c.name,
            original_input=c.original_input,
            status=c.status if c.status != ObjectStatus.NOT_FOUND else "not_found",
            linkedin_url=lp.linkedin_url if lp else None,
            name_on_linkedin=lp.name_on_linkedin if lp else None,
            match_confidence=lp.match_confidence if lp else None,
            employee_count=lp.employee_count if lp else None,
            industry=lp.industry if lp else None,
            headquarters=lp.headquarters if lp else None,
            website=lp.website if lp else None,
            description=lp.description if lp else None,
        ))

    return response


async def get_job_summary(db: AsyncSession, job_id: uuid.UUID) -> JobSummary:
    """Get a summary of a scraper job's results."""
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    result = await db.execute(
        select(Company)
        .options(selectinload(Company.linkedin_profile))
        .where(Company.data_source_id == job.data_source_id)
    )
    companies = result.scalars().all()

    with_results = []
    without_results = []
    close_matches = 0

    for company in companies:
        lp = company.linkedin_profile
        if lp:
            with_results.append(CompanySearchResult(
                company_name=company.name,
                linkedin_url=lp.linkedin_url,
                match_confidence=lp.match_confidence,
                name_on_linkedin=lp.name_on_linkedin,
                status=company.status,
            ))
            if lp.match_confidence in (MatchConfidence.MEDIUM, MatchConfidence.LOW):
                close_matches += 1
        else:
            without_results.append(CompanySearchResult(
                company_name=company.name,
                linkedin_url=None,
                match_confidence="no_match",
                name_on_linkedin=None,
                status=company.status,
            ))

    matching_employees = 0
    if job.use_ai_matching:
        result = await db.execute(
            select(MatchResult)
            .where(MatchResult.is_match == True)
        )
        matching_employees = len(result.scalars().all())

    return JobSummary(
        total_companies=len(companies),
        companies_matched=len(with_results),
        companies_not_found=len(without_results),
        close_matches=close_matches,
        employees_scraped=job.employees_scraped,
        matching_employees=matching_employees,
        companies_with_results=with_results,
        companies_without_results=without_results,
    )
