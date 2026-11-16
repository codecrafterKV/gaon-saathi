"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-11-11 01:48:40.698464
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Initial Gaon Saathi schema. Note: there is intentionally no table for reporters.
    op.create_table('admin_users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('must_change_password', sa.Boolean(), nullable=False),
    sa.Column('failed_login_count', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("role IN ('admin', 'reviewer', 'viewer')", name='ck_admin_users_role'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('authorities',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('department', sa.String(length=200), nullable=True),
    sa.Column('level', sa.String(length=24), nullable=False),
    sa.Column('state', sa.String(length=80), nullable=True),
    sa.Column('district', sa.String(length=120), nullable=True),
    sa.Column('grievance_channel', sa.String(length=200), nullable=True),
    sa.Column('website', sa.String(length=300), nullable=True),
    sa.Column('office_contact', sa.String(length=500), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("level IN ('gram_panchayat', 'block', 'district', 'state', 'national', 'other')", name='ck_authorities_level'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('spent_challenges',
    sa.Column('nonce', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('nonce')
    )
    with op.batch_alter_table('spent_challenges', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_spent_challenges_expires_at'), ['expires_at'], unique=False)

    op.create_table('admin_audit_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('admin_id', sa.Integer(), nullable=True),
    sa.Column('actor_username', sa.String(length=50), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('target_type', sa.String(length=32), nullable=True),
    sa.Column('target_ref', sa.String(length=64), nullable=True),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['admin_id'], ['admin_users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('admin_audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_admin_audit_logs_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_admin_audit_logs_admin_id'), ['admin_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_admin_audit_logs_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_admin_audit_logs_target_ref'), ['target_ref'], unique=False)

    op.create_table('admin_sessions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('admin_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['admin_id'], ['admin_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    with op.batch_alter_table('admin_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_admin_sessions_admin_id'), ['admin_id'], unique=False)

    op.create_table('app_settings',
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('value', sa.JSON(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['updated_by_id'], ['admin_users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('complaints',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('public_id', sa.String(length=24), nullable=False),
    sa.Column('tracking_token_hash', sa.String(length=64), nullable=False),
    sa.Column('category', sa.String(length=40), nullable=False),
    sa.Column('village', sa.String(length=120), nullable=False),
    sa.Column('district', sa.String(length=120), nullable=False),
    sa.Column('state', sa.String(length=80), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('approximate_location', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('public_message', sa.String(length=500), nullable=True),
    sa.Column('verification_status', sa.String(length=24), nullable=False),
    sa.Column('verification_findings', sa.Text(), nullable=True),
    sa.Column('authority_id', sa.Integer(), nullable=True),
    sa.Column('resolution_summary', sa.Text(), nullable=True),
    sa.Column('info_requested', sa.Boolean(), nullable=False),
    sa.Column('has_unread_update', sa.Boolean(), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("category IN ('public_space_encroachment', 'illegal_tree_cutting', 'development_fund_misuse', 'road_drainage', 'ration_distribution', 'public_resource_misuse', 'corruption_governance', 'other')", name='ck_complaints_category'),
    sa.CheckConstraint("status IN ('received', 'under_review', 'evidence_verification', 'action_in_progress', 'forwarded', 'resolved', 'rejected', 'closed')", name='ck_complaints_status'),
    sa.CheckConstraint("verification_status IN ('pending', 'verified', 'unverified', 'needs_more_info')", name='ck_complaints_verification_status'),
    sa.CheckConstraint('length(village) > 0 AND length(district) > 0 AND length(state) > 0', name='ck_complaints_location_present'),
    sa.ForeignKeyConstraint(['authority_id'], ['authorities.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('public_id')
    )
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.create_index('ix_complaints_category', ['category'], unique=False)
        batch_op.create_index('ix_complaints_district_village', ['district', 'village'], unique=False)
        batch_op.create_index('ix_complaints_is_demo', ['is_demo'], unique=False)
        batch_op.create_index('ix_complaints_status', ['status'], unique=False)
        batch_op.create_index('ix_complaints_submitted_at', ['submitted_at'], unique=False)

    op.create_table('complaint_forwardings',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('complaint_id', sa.Uuid(), nullable=False),
    sa.Column('authority_id', sa.Integer(), nullable=True),
    sa.Column('authority_name', sa.String(length=200), nullable=False),
    sa.Column('channel', sa.String(length=24), nullable=False),
    sa.Column('submitted_on', sa.Date(), nullable=False),
    sa.Column('reference_number', sa.String(length=120), nullable=True),
    sa.Column('acknowledgement_details', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("channel IN ('online_portal', 'email', 'letter', 'in_person', 'helpline', 'other')", name='ck_forwardings_channel'),
    sa.ForeignKeyConstraint(['authority_id'], ['authorities.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_id'], ['admin_users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('complaint_forwardings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_complaint_forwardings_complaint_id'), ['complaint_id'], unique=False)

    op.create_table('complaint_notes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('complaint_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("kind IN ('internal_note', 'follow_up', 'verification', 'evidence_request', 'reporter_update')", name='ck_notes_kind'),
    sa.ForeignKeyConstraint(['author_id'], ['admin_users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('complaint_notes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_complaint_notes_complaint_id'), ['complaint_id'], unique=False)

    op.create_table('complaint_status_history',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('complaint_id', sa.Uuid(), nullable=False),
    sa.Column('from_status', sa.String(length=32), nullable=True),
    sa.Column('to_status', sa.String(length=32), nullable=False),
    sa.Column('internal_note', sa.Text(), nullable=False),
    sa.Column('public_message', sa.String(length=500), nullable=True),
    sa.Column('changed_by_id', sa.Integer(), nullable=True),
    sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("to_status IN ('received', 'under_review', 'evidence_verification', 'action_in_progress', 'forwarded', 'resolved', 'rejected', 'closed')", name='ck_history_to_status'),
    sa.ForeignKeyConstraint(['changed_by_id'], ['admin_users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('complaint_status_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_complaint_status_history_complaint_id'), ['complaint_id'], unique=False)

    op.create_table('evidence_files',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('complaint_id', sa.Uuid(), nullable=False),
    sa.Column('storage_key', sa.String(length=64), nullable=False),
    sa.Column('display_name', sa.String(length=64), nullable=False),
    sa.Column('media_kind', sa.String(length=8), nullable=False),
    sa.Column('mime_type', sa.String(length=64), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('metadata_stripped', sa.Boolean(), nullable=False),
    sa.Column('scan_status', sa.String(length=16), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("media_kind IN ('image', 'video', 'pdf')", name='ck_evidence_media_kind'),
    sa.CheckConstraint("scan_status IN ('clean', 'not_scanned', 'error')", name='ck_evidence_scan_status'),
    sa.CheckConstraint("source IN ('initial', 'supplement', 'demo')", name='ck_evidence_source'),
    sa.CheckConstraint('size_bytes > 0', name='ck_evidence_size_positive'),
    sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('storage_key')
    )
    with op.batch_alter_table('evidence_files', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_evidence_files_complaint_id'), ['complaint_id'], unique=False)




def downgrade() -> None:
    # Initial Gaon Saathi schema. Note: there is intentionally no table for reporters.
    with op.batch_alter_table('evidence_files', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_evidence_files_complaint_id'))

    op.drop_table('evidence_files')
    with op.batch_alter_table('complaint_status_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_complaint_status_history_complaint_id'))

    op.drop_table('complaint_status_history')
    with op.batch_alter_table('complaint_notes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_complaint_notes_complaint_id'))

    op.drop_table('complaint_notes')
    with op.batch_alter_table('complaint_forwardings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_complaint_forwardings_complaint_id'))

    op.drop_table('complaint_forwardings')
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.drop_index('ix_complaints_submitted_at')
        batch_op.drop_index('ix_complaints_status')
        batch_op.drop_index('ix_complaints_is_demo')
        batch_op.drop_index('ix_complaints_district_village')
        batch_op.drop_index('ix_complaints_category')

    op.drop_table('complaints')
    op.drop_table('app_settings')
    with op.batch_alter_table('admin_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_admin_sessions_admin_id'))

    op.drop_table('admin_sessions')
    with op.batch_alter_table('admin_audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_admin_audit_logs_target_ref'))
        batch_op.drop_index(batch_op.f('ix_admin_audit_logs_created_at'))
        batch_op.drop_index(batch_op.f('ix_admin_audit_logs_admin_id'))
        batch_op.drop_index(batch_op.f('ix_admin_audit_logs_action'))

    op.drop_table('admin_audit_logs')
    with op.batch_alter_table('spent_challenges', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_spent_challenges_expires_at'))

    op.drop_table('spent_challenges')
    op.drop_table('authorities')
    op.drop_table('admin_users')

