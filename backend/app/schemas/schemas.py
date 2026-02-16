"""Pydantic schemas for API request/response validation."""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.core.ontology import ObjectStatus, MatchConfidence


# ---------------------------------------------------------------------------
# LinkedInAccount
# ---------------------------------------------------------------------------
class LinkedInAccountCreate(BaseModel):
    name: str
    email: Optional[str] = None
    li_at_cookie: str
    jsessionid_cookie: Optional[str] = None
    is_sales_navigator: bool = False


class LinkedInAccountResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: Optional[str]
    is_sales_navigator: bool
    status: str
    connected_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# DataSource
# ---------------------------------------------------------------------------
class DataSourceCreate(BaseModel):
    name: str
    source_type: str = Field(description="google_sheet, csv_upload, or manual")
    google_sheet_url: Optional[str] = None
    sheet_tab_name: Optional[str] = None
    column_name: Optional[str] = None
    column_type: str = Field(default="company_name", description="company_name or linkedin_url")


class DataSourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    google_sheet_url: Optional[str]
    column_name: Optional[str]
    column_type: str
    row_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    original_input: str
    status: str
    linkedin_url: Optional[str] = None
    match_confidence: Optional[str] = None
    employee_count: Optional[int] = None

    class Config:
        from_attributes = True


class CompanySearchResult(BaseModel):
    company_name: str
    linkedin_url: Optional[str]
    match_confidence: str
    name_on_linkedin: Optional[str]
    status: str


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------
class EmployeeResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    first_name: Optional[str]
    last_name: Optional[str]
    job_title: Optional[str]
    linkedin_url: Optional[str]
    location: Optional[str]
    email: Optional[str]
    company_name: Optional[str] = None
    is_match: Optional[bool] = None
    match_confidence: Optional[str] = None
    match_reasoning: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# ScraperJob
# ---------------------------------------------------------------------------
class ScraperJobCreate(BaseModel):
    name: str
    data_source_id: uuid.UUID
    linkedin_account_id: uuid.UUID
    max_employees_per_company: int = 30
    max_companies_per_launch: int = 50
    target_job_titles: Optional[List[str]] = None
    use_ai_matching: bool = True
    ai_matching_prompt: Optional[str] = None
    schedule_frequency: str = Field(default="once", description="once, daily, weekly, monthly")
    schedule_times_per_day: int = 1


class ScraperJobResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    is_enabled: bool
    companies_processed: int
    companies_matched: int
    companies_not_found: int
    employees_scraped: int
    data_source: Optional[DataSourceResponse] = None
    created_at: datetime
    last_launched_at: Optional[datetime]
    last_error: Optional[str]

    class Config:
        from_attributes = True


class ScraperJobLaunchResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str
    task_id: Optional[str] = None


# ---------------------------------------------------------------------------
# AI Role Matching
# ---------------------------------------------------------------------------
class RoleMatchRequest(BaseModel):
    job_titles: List[str] = Field(description="Target job titles to match against")
    prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt for AI matching, e.g. 'Find clinic administrators and practice managers'"
    )


class RoleMatchSuggestion(BaseModel):
    suggested_roles: List[str]
    reasoning: str


# ---------------------------------------------------------------------------
# Job Summary / Stats
# ---------------------------------------------------------------------------
class JobSummary(BaseModel):
    total_companies: int
    companies_matched: int
    companies_not_found: int
    close_matches: int
    employees_scraped: int
    matching_employees: int
    companies_with_results: List[CompanySearchResult]
    companies_without_results: List[CompanySearchResult]
