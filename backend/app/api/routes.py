"""
API Routes

REST endpoints for the Zavis LinkedIn Marketing Tool.
Maps HTTP operations to ontology Actions.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.ontology import (
    LinkedInAccount, DataSource, Company, CompanyLinkedIn,
    Employee, MatchResult, ScraperJob, Schedule,
)
from app.core.ontology import ObjectStatus
from app.schemas.schemas import (
    LinkedInAccountCreate, LinkedInAccountResponse,
    DataSourceCreate, DataSourceResponse,
    CompanyResponse, EmployeeResponse,
    ScraperJobCreate, ScraperJobResponse, ScraperJobLaunchResponse,
    JobSummary, RoleMatchRequest, RoleMatchSuggestion,
)
from app.services import job_orchestrator
from app.services.ai_matcher import suggest_related_roles
from app.services.google_sheets import get_sheet_tabs, get_sheet_columns

router = APIRouter()


# ---------------------------------------------------------------------------
# LinkedIn Accounts
# ---------------------------------------------------------------------------
@router.post("/linkedin-accounts", response_model=LinkedInAccountResponse)
async def create_linkedin_account(
    data: LinkedInAccountCreate, db: AsyncSession = Depends(get_db)
):
    """Connect a LinkedIn / Sales Navigator account."""
    account = LinkedInAccount(
        name=data.name,
        email=data.email,
        li_at_cookie=data.li_at_cookie,
        jsessionid_cookie=data.jsessionid_cookie,
        is_sales_navigator=data.is_sales_navigator,
        status=ObjectStatus.ACTIVE,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.get("/linkedin-accounts", response_model=List[LinkedInAccountResponse])
async def list_linkedin_accounts(db: AsyncSession = Depends(get_db)):
    """List all connected LinkedIn accounts."""
    result = await db.execute(select(LinkedInAccount))
    return result.scalars().all()


@router.delete("/linkedin-accounts/{account_id}")
async def delete_linkedin_account(
    account_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    account = await db.get(LinkedInAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Data Sources
# ---------------------------------------------------------------------------
@router.post("/data-sources", response_model=DataSourceResponse)
async def create_data_source(
    data: DataSourceCreate, db: AsyncSession = Depends(get_db)
):
    """Create a data source (Google Sheet or manual URL list)."""
    ds = DataSource(
        name=data.name,
        source_type=data.source_type,
        google_sheet_url=data.google_sheet_url,
        sheet_tab_name=data.sheet_tab_name,
        column_name=data.column_name,
        column_type=data.column_type,
        status=ObjectStatus.PENDING,
    )
    db.add(ds)
    await db.flush()

    # Ingest data immediately
    try:
        await job_orchestrator.ingest_data_source(db, ds.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.refresh(ds)
    return ds


@router.post("/data-sources/upload-csv", response_model=DataSourceResponse)
async def upload_csv_data_source(
    name: str = Form(...),
    column_name: str = Form(...),
    column_type: str = Form(default="company_name"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV file as a data source."""
    import os
    import tempfile

    # Save uploaded file
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    ds = DataSource(
        name=name,
        source_type="csv_upload",
        column_name=column_name,
        column_type=column_type,
        raw_data={"file_path": tmp_path, "original_filename": file.filename},
        status=ObjectStatus.PENDING,
    )
    db.add(ds)
    await db.flush()

    try:
        await job_orchestrator.ingest_data_source(db, ds.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.refresh(ds)
    return ds


@router.get("/data-sources", response_model=List[DataSourceResponse])
async def list_data_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource))
    return result.scalars().all()


@router.get("/data-sources/{ds_id}/companies", response_model=List[CompanyResponse])
async def list_data_source_companies(
    ds_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Company)
        .options(selectinload(Company.linkedin_profile))
        .where(Company.data_source_id == ds_id)
    )
    companies = result.scalars().all()
    return [
        CompanyResponse(
            id=c.id,
            name=c.name,
            original_input=c.original_input,
            status=c.status,
            linkedin_url=c.linkedin_profile.linkedin_url if c.linkedin_profile else None,
            match_confidence=c.linkedin_profile.match_confidence if c.linkedin_profile else None,
            employee_count=c.linkedin_profile.employee_count if c.linkedin_profile else None,
        )
        for c in companies
    ]


@router.get("/sheets/tabs")
async def get_google_sheet_tabs(url: str):
    """Get tabs from a Google Sheet URL."""
    try:
        tabs = get_sheet_tabs(url)
        return {"tabs": tabs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sheets/columns")
async def get_google_sheet_columns(url: str, tab: Optional[str] = None):
    """Get column headers from a Google Sheet."""
    try:
        columns = get_sheet_columns(url, tab)
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Scraper Jobs
# ---------------------------------------------------------------------------
@router.post("/scraper-jobs", response_model=ScraperJobResponse)
async def create_scraper_job(
    data: ScraperJobCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new scraper job configuration."""
    job = await job_orchestrator.create_scraper_job(db, data)
    await db.refresh(job)
    return job


@router.get("/scraper-jobs", response_model=List[ScraperJobResponse])
async def list_scraper_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScraperJob).options(selectinload(ScraperJob.data_source))
    )
    return result.scalars().all()


@router.get("/scraper-jobs/{job_id}", response_model=ScraperJobResponse)
async def get_scraper_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/scraper-jobs/{job_id}/launch", response_model=ScraperJobLaunchResponse)
async def launch_scraper_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Launch a scraper job (start scraping)."""
    try:
        return await job_orchestrator.launch_job(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/scraper-jobs/{job_id}/pause")
async def pause_scraper_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Pause/disable a scraper job."""
    try:
        job = await job_orchestrator.pause_job(db, job_id)
        return {"status": "paused", "job_id": str(job.id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scraper-jobs/{job_id}/summary", response_model=JobSummary)
async def get_job_summary(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a detailed summary of job results."""
    try:
        return await job_orchestrator.get_job_summary(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scraper-jobs/{job_id}/employees", response_model=List[EmployeeResponse])
async def get_job_employees(
    job_id: uuid.UUID,
    matched_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Get all scraped employees for a job."""
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get companies -> linkedin profiles -> employees
    result = await db.execute(
        select(Employee)
        .join(CompanyLinkedIn)
        .join(Company)
        .options(
            selectinload(Employee.match_result),
            selectinload(Employee.company_linkedin),
        )
        .where(Company.data_source_id == job.data_source_id)
    )
    employees = result.scalars().all()

    response = []
    for emp in employees:
        mr = emp.match_result
        if matched_only and (not mr or not mr.is_match):
            continue

        response.append(EmployeeResponse(
            id=emp.id,
            full_name=emp.full_name,
            first_name=emp.first_name,
            last_name=emp.last_name,
            job_title=emp.job_title,
            linkedin_url=emp.linkedin_url,
            location=emp.location,
            email=emp.email,
            company_name=emp.company_linkedin.name_on_linkedin if emp.company_linkedin else None,
            is_match=mr.is_match if mr else None,
            match_confidence=mr.confidence if mr else None,
            match_reasoning=mr.reasoning if mr else None,
        ))

    return response


# ---------------------------------------------------------------------------
# AI Role Matching
# ---------------------------------------------------------------------------
@router.post("/ai/suggest-roles", response_model=RoleMatchSuggestion)
async def ai_suggest_roles(data: RoleMatchRequest):
    """Use AI to suggest related job titles for targeting."""
    roles, reasoning = await suggest_related_roles(data.job_titles)
    return RoleMatchSuggestion(suggested_roles=roles, reasoning=reasoning)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "zavis-linkedin-tool"}
