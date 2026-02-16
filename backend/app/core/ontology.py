"""
Palantir Ontology Framework Primitives

This module implements the core ontology concepts:
- ObjectType: Every entity in the system is a typed object with properties.
- LinkType: Relationships between objects are first-class, typed, and directional.
- Action: Mutations flow through defined actions that validate and transform state.
- Pipeline: Chains of actions that execute in sequence on object graphs.

The database schema below IS the ontology — objects aren't just rows, they carry
semantic type information, and the system reasons about them through their
relationships and available actions.
"""

from enum import Enum


class ObjectTypeEnum(str, Enum):
    """All object types in the ontology."""
    SCRAPER_JOB = "scraper_job"
    DATA_SOURCE = "data_source"
    COMPANY = "company"
    COMPANY_LINKEDIN = "company_linkedin"
    EMPLOYEE = "employee"
    LINKEDIN_ACCOUNT = "linkedin_account"
    SCHEDULE = "schedule"
    MATCH_RESULT = "match_result"


class LinkTypeEnum(str, Enum):
    """All link types (relationships) in the ontology."""
    USES_SOURCE = "uses_source"           # ScraperJob -> DataSource
    AUTHENTICATED_BY = "authenticated_by"  # ScraperJob -> LinkedInAccount
    SCHEDULED_BY = "scheduled_by"          # ScraperJob -> Schedule
    CONTAINS = "contains"                  # DataSource -> Company
    RESOLVED_TO = "resolved_to"            # Company -> CompanyLinkedIn
    HAS_EMPLOYEES = "has_employees"        # CompanyLinkedIn -> Employee
    EVALUATED_BY = "evaluated_by"          # Employee -> MatchResult


class ActionTypeEnum(str, Enum):
    """Actions that can be performed on objects."""
    CREATE_SCRAPER_JOB = "create_scraper_job"
    CONNECT_DATA_SOURCE = "connect_data_source"
    RESOLVE_COMPANY = "resolve_company"
    SCRAPE_EMPLOYEES = "scrape_employees"
    EVALUATE_MATCH = "evaluate_match"
    LAUNCH_JOB = "launch_job"
    PAUSE_JOB = "pause_job"
    RESUME_JOB = "resume_job"


class ObjectStatus(str, Enum):
    """Universal status for any object in the ontology."""
    PENDING = "pending"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    NOT_FOUND = "not_found"


class MatchConfidence(str, Enum):
    """Confidence level for company/role matches."""
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NO_MATCH = "no_match"
