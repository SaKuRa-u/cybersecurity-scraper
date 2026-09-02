"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('scraper_module', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('last_scraped_at', sa.DateTime(), nullable=True),
        sa.Column('scrape_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sources_id'), 'sources', ['id'], unique=False)
    op.create_index(op.f('ix_sources_name'), 'sources', ['name'], unique=True)
    
    op.create_table(
        'scraped_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scraped_data_id'), 'scraped_data', ['id'], unique=False)
    op.create_index(op.f('ix_scraped_data_source_id'), 'scraped_data', ['source_id'], unique=False)
    op.create_index(op.f('ix_scraped_data_external_id'), 'scraped_data', ['external_id'], unique=False)
    op.create_index(op.f('ix_scraped_data_content_type'), 'scraped_data', ['content_type'], unique=False)
    op.create_index('ix_scraped_data_tags', 'scraped_data', ['tags'], unique=False, postgresql_using='gin')
    op.create_index('ix_scraped_data_content', 'scraped_data', ['content'], unique=False, postgresql_using='gin')
    
    op.create_table(
        'scrape_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('items_found', sa.Integer(), nullable=True),
        sa.Column('items_inserted', sa.Integer(), nullable=True),
        sa.Column('items_updated', sa.Integer(), nullable=True),
        sa.Column('items_deleted', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('triggered_by', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scrape_sessions_id'), 'scrape_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_scrape_sessions_source_id'), 'scrape_sessions', ['source_id'], unique=False)
    op.create_index(op.f('ix_scrape_sessions_status'), 'scrape_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_scrape_sessions_task_id'), 'scrape_sessions', ['task_id'], unique=True)
    
    op.create_table(
        'export_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scrape_session_id', sa.Integer(), nullable=True),
        sa.Column('exported_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('items_exported', sa.Integer(), nullable=True),
        sa.Column('export_file_path', sa.Text(), nullable=True),
        sa.Column('export_format', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['scrape_session_id'], ['scrape_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_export_logs_id'), 'export_logs', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_export_logs_id'), table_name='export_logs')
    op.drop_table('export_logs')
    op.drop_index(op.f('ix_scrape_sessions_task_id'), table_name='scrape_sessions')
    op.drop_index(op.f('ix_scrape_sessions_status'), table_name='scrape_sessions')
    op.drop_index(op.f('ix_scrape_sessions_source_id'), table_name='scrape_sessions')
    op.drop_index(op.f('ix_scrape_sessions_id'), table_name='scrape_sessions')
    op.drop_table('scrape_sessions')
    op.drop_index('ix_scraped_data_content', table_name='scraped_data', postgresql_using='gin')
    op.drop_index('ix_scraped_data_tags', table_name='scraped_data', postgresql_using='gin')
    op.drop_index(op.f('ix_scraped_data_content_type'), table_name='scraped_data')
    op.drop_index(op.f('ix_scraped_data_external_id'), table_name='scraped_data')
    op.drop_index(op.f('ix_scraped_data_source_id'), table_name='scraped_data')
    op.drop_index(op.f('ix_scraped_data_id'), table_name='scraped_data')
    op.drop_table('scraped_data')
    op.drop_index(op.f('ix_sources_name'), table_name='sources')
    op.drop_index(op.f('ix_sources_id'), table_name='sources')
    op.drop_table('sources')
