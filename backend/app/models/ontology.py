"""
Palantir Ontology-Based Database Models

Every table represents an Object Type in the ontology. Foreign keys represent
Link Types. The database IS the ontology — it encodes what objects exist, how
they relate, and what states they can be in. Actions (services) operate on
these objects through well-defined state transitions.

Object Graph:
    ScraperJob ──uses──> DataSource ──contains──> Company ──resolved_to──> CompanyLinkedIn
        │                                                                       │
        ├──authenticated_by──> LinkedInAccount                          has_employees
        │                                                                       │
        └──scheduled_by──> Schedule                                       Employee
                                                                               │
                                                                        evaluated_by
                                                                               │
                                                                         MatchResult
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.ontology import ObjectStatus, MatchConfidence


# ---------------------------------------------------------------------------
# Object Type: GoogleOAuthToken
# Stores Google OAuth 2.0 tokens for Google Sheets access.
# ---------------------------------------------------------------------------
class GoogleOAuthToken(Base):
    __tablename__ = "google_oauth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_uri: Mapped[str] = mapped_column(Text, default="https://oauth2.googleapis.com/token")
    scopes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Object Type: LinkedInAccount
# Represents a connected LinkedIn / Sales Navigator account.
# ---------------------------------------------------------------------------
class LinkedInAccount(Base):
    __tablename__ = "linkedin_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    li_at_cookie: Mapped[str] = mapped_column(Text)
    jsessionid_cookie: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_sales_navigator: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(
        Enum(ObjectStatus, name="object_status", create_constraint=False),
        default=ObjectStatus.ACTIVE,
    )
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Reverse links
    scraper_jobs: Mapped[List["ScraperJob"]] = relationship(back_populates="linkedin_account")


# ---------------------------------------------------------------------------
# Object Type: DataSource
# A Google Sheet, uploaded CSV, or manual URL list.
# ---------------------------------------------------------------------------
class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))  # "google_sheet", "csv_upload", "manual"
    google_sheet_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_sheet_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sheet_tab_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    column_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # column with company names or URLs
    column_type: Mapped[str] = mapped_column(String(50), default="company_name")  # "company_name" or "linkedin_url"
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # cached sheet data
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        Enum(ObjectStatus, name="object_status", create_constraint=False),
        default=ObjectStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Links
    companies: Mapped[List["Company"]] = relationship(back_populates="data_source", cascade="all, delete-orphan")
    scraper_jobs: Mapped[List["ScraperJob"]] = relationship(back_populates="data_source")


# ---------------------------------------------------------------------------
# Object Type: Company
# A clinic/company extracted from a data source.
# ---------------------------------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    name: Mapped[str] = mapped_column(String(500))
    original_input: Mapped[str] = mapped_column(Text)  # exact value from sheet
    row_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(ObjectStatus, name="object_status", create_constraint=False),
        default=ObjectStatus.PENDING,
    )
    search_query_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Links
    data_source: Mapped["DataSource"] = relationship(back_populates="companies")
    linkedin_profile: Mapped[Optional["CompanyLinkedIn"]] = relationship(
        back_populates="company", uselist=False, cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Object Type: CompanyLinkedIn
# The resolved LinkedIn company page for a Company.
# ---------------------------------------------------------------------------
class CompanyLinkedIn(Base):
    __tablename__ = "company_linkedin_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), unique=True)
    linkedin_url: Mapped[str] = mapped_column(Text)
    linkedin_company_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name_on_linkedin: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    headquarters: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    match_confidence: Mapped[str] = mapped_column(
        Enum(MatchConfidence, name="match_confidence", create_constraint=False),
        default=MatchConfidence.HIGH,
    )
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Links
    company: Mapped["Company"] = relationship(back_populates="linkedin_profile")
    employees: Mapped[List["Employee"]] = relationship(back_populates="company_linkedin", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Object Type: Employee
# An employee scraped from a company's LinkedIn page.
# ---------------------------------------------------------------------------
class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_linkedin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_linkedin_profiles.id"))
    full_name: Mapped[str] = mapped_column(String(500))
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_member_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Links
    company_linkedin: Mapped["CompanyLinkedIn"] = relationship(back_populates="employees")
    match_result: Mapped[Optional["MatchResult"]] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Object Type: MatchResult
# AI evaluation of whether an employee's role matches target criteria.
# ---------------------------------------------------------------------------
class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), unique=True)
    target_roles: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # list of roles we searched for
    is_match: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[str] = mapped_column(
        Enum(MatchConfidence, name="match_confidence", create_constraint=False),
        default=MatchConfidence.NO_MATCH,
    )
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI explanation
    matched_role: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Links
    employee: Mapped["Employee"] = relationship(back_populates="match_result")


# ---------------------------------------------------------------------------
# Object Type: Schedule
# Timing configuration for recurring scraping jobs.
# ---------------------------------------------------------------------------
class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    frequency: Mapped[str] = mapped_column(String(50))  # "once", "daily", "weekly", "monthly"
    times_per_day: Mapped[int] = mapped_column(Integer, default=1)
    preferred_hour_utc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0=Mon, 6=Sun
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Reverse links
    scraper_jobs: Mapped[List["ScraperJob"]] = relationship(back_populates="schedule")


# ---------------------------------------------------------------------------
# Object Type: ScraperJob
# The top-level orchestrator — a configured scraping task that ties together
# a data source, LinkedIn account, schedule, and behavior settings.
# ---------------------------------------------------------------------------
class ScraperJob(Base):
    __tablename__ = "scraper_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))

    # Job type: "company_discovery" or "employee_scraping"
    job_type: Mapped[str] = mapped_column(String(50), default="company_discovery")
    # For employee_scraping jobs: link back to the discovery job
    parent_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("scraper_jobs.id"), nullable=True)
    # For employee_scraping: which companies to scrape (list of company UUID strings)
    selected_company_ids: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Link: uses DataSource
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"))
    # Link: authenticated_by LinkedInAccount
    linkedin_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("linkedin_accounts.id"))
    # Link: scheduled_by Schedule
    schedule_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("schedules.id"), nullable=True)

    # Behavior configuration
    max_employees_per_company: Mapped[int] = mapped_column(Integer, default=30)
    max_companies_per_launch: Mapped[int] = mapped_column(Integer, default=50)
    target_job_titles: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # filter list
    use_ai_matching: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_matching_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # State
    status: Mapped[str] = mapped_column(
        Enum(ObjectStatus, name="object_status", create_constraint=False),
        default=ObjectStatus.PENDING,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # on/off toggle
    companies_processed: Mapped[int] = mapped_column(Integer, default=0)
    companies_matched: Mapped[int] = mapped_column(Integer, default=0)
    companies_not_found: Mapped[int] = mapped_column(Integer, default=0)
    employees_scraped: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_launched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships (Link Types)
    data_source: Mapped["DataSource"] = relationship(back_populates="scraper_jobs")
    linkedin_account: Mapped["LinkedInAccount"] = relationship(back_populates="scraper_jobs")
    schedule: Mapped[Optional["Schedule"]] = relationship(back_populates="scraper_jobs")
    parent_job: Mapped[Optional["ScraperJob"]] = relationship(remote_side="ScraperJob.id")
