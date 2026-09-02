"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        'projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('query', sa.Text, nullable=False),
        sa.Column('query_model', JSONB),
        sa.Column('geography', JSONB),
        sa.Column('languages', ARRAY(sa.String)),
        sa.Column('audience', ARRAY(sa.String)),
        sa.Column('intent', ARRAY(sa.String)),
        sa.Column('source_types', ARRAY(sa.String)),
        sa.Column('scoring_profile', sa.String(50), server_default='lead_generation'),
        sa.Column('max_discovery_depth', sa.Integer, server_default='3'),
        sa.Column('max_sources', sa.Integer, server_default='500'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    op.create_table(
        'discovery_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('current_stage', sa.String(50)),
        sa.Column('progress', sa.Float, server_default='0.0'),
        sa.Column('stats', JSONB, server_default='{}'),
        sa.Column('error', sa.Text),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    op.create_table(
        'sources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('telegram_id', sa.Integer, unique=True),
        sa.Column('username', sa.String(255)),
        sa.Column('title', sa.String(512)),
        sa.Column('description', sa.Text),
        sa.Column('source_type', sa.String(20)),
        sa.Column('member_count', sa.Integer),
        sa.Column('linked_chat_id', sa.Integer),
        sa.Column('has_pinned_messages', sa.Boolean, server_default='false'),
        sa.Column('pinned_messages', JSONB, server_default='[]'),
        sa.Column('recent_messages', JSONB, server_default='[]'),
        sa.Column('recent_messages_fetched_at', sa.DateTime(timezone=True)),
        sa.Column('topic_analysis', JSONB),
        sa.Column('language_analysis', JSONB),
        sa.Column('geography_analysis', JSONB),
        sa.Column('audience_analysis', JSONB),
        sa.Column('intent_analysis', JSONB),
        sa.Column('activity_analysis', JSONB),
        sa.Column('commercial_analysis', JSONB),
        sa.Column('embedding', ARRAY(sa.Float)),
        sa.Column('status', sa.String(30), server_default='discovered'),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('last_analyzed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    op.create_index('idx_sources_telegram_id', 'sources', ['telegram_id'])
    op.create_index('idx_sources_username', 'sources', ['username'])
    op.create_index('idx_sources_status', 'sources', ['status'])
    op.create_index('idx_sources_source_type', 'sources', ['source_type'])

    op.execute("""
        ALTER TABLE sources ADD COLUMN fts_vector TSVECTOR
        GENERATED ALWAYS AS (
            to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(description, ''))
        ) STORED
    """)
    op.create_index('idx_sources_fts', 'sources', ['fts_vector'], postgresql_using='gin')

    op.create_table(
        'source_scores',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('source_id', UUID(as_uuid=True), sa.ForeignKey('sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('discovery_run_id', UUID(as_uuid=True), sa.ForeignKey('discovery_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('total_score', sa.Float, nullable=False),
        sa.Column('breakdown', JSONB, nullable=False),
        sa.Column('scoring_profile', sa.String(50)),
        sa.Column('scored_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('source_id', 'project_id', 'discovery_run_id'),
    )
    op.create_index('idx_source_scores_project', 'source_scores', ['project_id'])
    op.create_index('idx_source_scores_total', 'source_scores', ['total_score'])

    op.create_table(
        'source_links',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('source_id', UUID(as_uuid=True), sa.ForeignKey('sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_source_id', UUID(as_uuid=True), sa.ForeignKey('sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('edge_type', sa.String(20), nullable=False),
        sa.Column('confidence', sa.Float, server_default='0.5'),
        sa.Column('context', sa.Text),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.UniqueConstraint('source_id', 'target_source_id', 'edge_type'),
    )
    op.create_index('idx_source_links_source', 'source_links', ['source_id'])
    op.create_index('idx_source_links_target', 'source_links', ['target_source_id'])

    op.create_table(
        'query_variants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('discovery_run_id', UUID(as_uuid=True), sa.ForeignKey('discovery_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('variant_text', sa.Text, nullable=False),
        sa.Column('variant_type', sa.String(30)),
        sa.Column('priority', sa.Integer, server_default='5'),
        sa.Column('executed', sa.Boolean, server_default='false'),
        sa.Column('results_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_query_variants_run', 'query_variants', ['discovery_run_id'])

    op.create_table(
        'discovery_candidates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('discovery_run_id', UUID(as_uuid=True), sa.ForeignKey('discovery_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(20)),
        sa.Column('username', sa.String(255)),
        sa.Column('telegram_id', sa.Integer),
        sa.Column('invite_link', sa.Text),
        sa.Column('url', sa.Text),
        sa.Column('title', sa.Text),
        sa.Column('discovered_via', sa.String(50)),
        sa.Column('discovery_query', sa.Text),
        sa.Column('confidence', sa.Float, server_default='0.5'),
        sa.Column('raw_data', JSONB, server_default='{}'),
        sa.Column('resolved', sa.Boolean, server_default='false'),
        sa.Column('resolved_source_id', UUID(as_uuid=True), sa.ForeignKey('sources.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_candidates_run', 'discovery_candidates', ['discovery_run_id'])
    op.create_index('idx_candidates_resolved', 'discovery_candidates', ['resolved'])

    op.create_table(
        'scoring_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('weights', JSONB, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_default', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    op.execute("""
        INSERT INTO scoring_profiles (name, weights, description, is_default) VALUES
        ('lead_generation', '{"topic": 0.30, "geography": 0.15, "language": 0.10, "audience": 0.15, "intent": 0.10, "activity": 0.10, "freshness": 0.05, "commercial": 0.07, "quality": 0.03}', 'Optimized for finding chats with commercial intent and lead potential', true),
        ('market_research', '{"topic": 0.35, "geography": 0.15, "language": 0.10, "audience": 0.10, "intent": 0.05, "activity": 0.10, "freshness": 0.05, "commercial": 0.03, "quality": 0.07}', 'Optimized for broad topic coverage', false),
        ('news_monitoring', '{"topic": 0.25, "geography": 0.20, "language": 0.15, "audience": 0.05, "intent": 0.05, "activity": 0.15, "freshness": 0.10, "commercial": 0.00, "quality": 0.05}', 'Optimized for active, fresh news sources', false);
    """)

    op.create_table(
        'source_reviews',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('source_id', UUID(as_uuid=True), sa.ForeignKey('sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('reason', sa.Text),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    op.create_table(
        'discovery_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('discovery_run_id', UUID(as_uuid=True), sa.ForeignKey('discovery_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('payload', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_events_run', 'discovery_events', ['discovery_run_id'])


def downgrade() -> None:
    op.drop_table('discovery_events')
    op.drop_table('source_reviews')
    op.drop_table('scoring_profiles')
    op.drop_table('discovery_candidates')
    op.drop_table('query_variants')
    op.drop_table('source_links')
    op.drop_table('source_scores')
    op.drop_table('sources')
    op.drop_table('discovery_runs')
    op.drop_table('projects')
