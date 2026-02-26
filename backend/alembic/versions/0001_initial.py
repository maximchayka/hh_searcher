"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-02-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("email", sa.String, unique=True, index=True, nullable=False),
        sa.Column("hashed_password", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("hh_access_token", sa.String, nullable=True),
        sa.Column("hh_refresh_token", sa.String, nullable=True),
        sa.Column("hh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hh_resume_id", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("first_name", sa.String, nullable=True),
        sa.Column("last_name", sa.String, nullable=True),
        sa.Column("skills", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=False),
        sa.Column("raw_data", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cover_letter_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "search_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("params", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "job_tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("search_template_id", sa.Integer, sa.ForeignKey("search_templates.id"), nullable=False),
        sa.Column("cover_letter_template_id", sa.Integer, sa.ForeignKey("cover_letter_templates.id"), nullable=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("frequency", sa.String, nullable=False),
        sa.Column("custom_cron", sa.String, nullable=True),
        sa.Column("action", sa.String, default="auto_apply"),
        sa.Column("status", sa.String, default="active"),
        sa.Column("only_new", sa.Boolean, default=True),
        sa.Column("skip_applied", sa.Boolean, default=True),
        sa.Column("min_ai_match", sa.Integer, nullable=True),
        sa.Column("daily_limit", sa.Integer, default=50),
        sa.Column("per_run_limit", sa.Integer, default=20),
        sa.Column("per_company_limit", sa.Integer, default=3),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "job_task_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_task_id", sa.Integer, sa.ForeignKey("job_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vacancies_found", sa.Integer, default=0),
        sa.Column("applied_count", sa.Integer, default=0),
        sa.Column("errors_count", sa.Integer, default=0),
        sa.Column("errors_detail", sa.Text, nullable=True),
        sa.Column("status", sa.String, default="running"),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vacancy_id", sa.String, nullable=False, index=True),
        sa.Column("vacancy_title", sa.String, nullable=False),
        sa.Column("company_name", sa.String, nullable=False),
        sa.Column("salary_display", sa.String, nullable=True),
        sa.Column("vacancy_url", sa.String, nullable=False),
        sa.Column("resume_hh_id", sa.String, nullable=False),
        sa.Column("cover_letter_text", sa.Text, nullable=True),
        sa.Column("status", sa.String, default="sent"),
        sa.Column("hh_negotiation_id", sa.String, nullable=True),
        sa.Column("job_task_id", sa.Integer, sa.ForeignKey("job_tasks.id"), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("job_task_logs")
    op.drop_table("job_tasks")
    op.drop_table("search_templates")
    op.drop_table("cover_letter_templates")
    op.drop_table("resumes")
    op.drop_table("users")
