"""Add job_type, parent_job_id, selected_company_ids to scraper_jobs

Revision ID: 002_job_type_fields
Revises: 001_google_oauth
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002_job_type_fields"
down_revision = "001_google_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scraper_jobs", sa.Column("job_type", sa.String(50), server_default="company_discovery", nullable=False))
    op.add_column("scraper_jobs", sa.Column("parent_job_id", UUID(as_uuid=True), sa.ForeignKey("scraper_jobs.id"), nullable=True))
    op.add_column("scraper_jobs", sa.Column("selected_company_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("scraper_jobs", "selected_company_ids")
    op.drop_column("scraper_jobs", "parent_job_id")
    op.drop_column("scraper_jobs", "job_type")
