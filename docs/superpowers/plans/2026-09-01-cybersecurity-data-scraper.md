# Cybersecurity Data Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cybersecurity intelligence scraping platform with web UI for collecting data from OWASP, MITRE ATT&CK, GitHub payloads, and Kali documentation, with OpenSearch-compatible export.

**Architecture:** Monolithic web app with FastAPI backend, React frontend, PostgreSQL database, Celery task queue, and Redis broker. Differential sync algorithm tracks changes (INSERT/UPDATE/DELETE/UNCHANGED) between scrape sessions.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Celery, Redis, PostgreSQL 15, React 18, Vite, TailwindCSS, Docker Compose

**Spec:** `docs/superpowers/specs/2026-09-01-cybersecurity-data-scraper-design.md`

## Global Constraints

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (for frontend)
- Docker Compose v2+
- All scraping must be polite (rate limits, retry delays)
- SHA256 hashing for change detection
- Database transactions for sync operations
- No authentication in Phase A (single user)
- Export format: OpenSearch JSONL bulk import
- Pagination: 50 items/page default
- Retry: 3 attempts, exponential backoff (2s, 4s, 8s)

---

## Task 1: Project Scaffolding & Docker Setup

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `frontend/package.json`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `Makefile`

**Interfaces:**
- Consumes: None (bootstrap task)
- Produces: Docker infrastructure for all services

- [ ] **Step 1: Create backend requirements file**

Create `backend/requirements.txt`:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.12.1
celery==5.3.4
redis==5.0.1
httpx==0.25.1
beautifulsoup4==4.12.2
lxml==4.9.3
PyGithub==2.1.1
pydantic==2.5.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
websockets==12.0
```

- [ ] **Step 2: Create backend Dockerfile**

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create frontend package.json**

Create `frontend/package.json`:

```json
{
  "name": "cybersec-scraper-ui",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.2",
    "recharts": "^2.10.3",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.3.5",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}
```

- [ ] **Step 4: Create frontend Dockerfile**

Create `frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 5: Create nginx configuration**

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

- [ ] **Step 6: Create docker-compose.yml**

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: scraper_postgres
    environment:
      POSTGRES_DB: ${DATABASE_NAME:-cybersec_scraper}
      POSTGRES_USER: ${DATABASE_USER:-scraper_user}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD:-password}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER:-scraper_user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: scraper_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: scraper_backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    volumes:
      - ./backend:/app
      - ./exports:/app/exports
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: scraper_celery_worker
    command: celery -A celery_app worker --loglevel=info --concurrency=4
    volumes:
      - ./backend:/app
      - ./exports:/app/exports
      - ./logs:/app/logs
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: scraper_celery_beat
    command: celery -A celery_app beat --loglevel=info
    volumes:
      - ./backend:/app
      - ./logs:/app/logs
    env_file:
      - .env
    depends_on:
      - redis
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: scraper_frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

- [ ] **Step 7: Create environment template**

Create `.env.example`:

```bash
# Database
DATABASE_URL=postgresql://scraper_user:password@postgres:5432/cybersec_scraper
DATABASE_NAME=cybersec_scraper
DATABASE_USER=scraper_user
DATABASE_PASSWORD=password
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
CELERY_WORKER_CONCURRENCY=4

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
SECRET_KEY=change-me-to-random-string
LOG_LEVEL=INFO

# External APIs
GITHUB_TOKEN=
MITRE_API_KEY=

# Scraper Config
SCRAPER_CONCURRENT_REQUESTS=5
SCRAPER_RETRY_MAX=3
SCRAPER_RETRY_BACKOFF=2

# Export
EXPORT_DIR=/app/exports
EXPORT_FORMAT=jsonl
OPENSEARCH_INDEX_NAME=cybersec_knowledge
```

- [ ] **Step 8: Create .gitignore**

Create `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
*.egg-info/
dist/
build/

# Node
node_modules/
dist/
.npm

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/
*.log

# Exports
exports/*.jsonl
exports/*.json

# Database
*.db
*.sqlite

# Docker
.dockerignore

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 9: Create Makefile for helper commands**

Create `Makefile`:

```makefile
.PHONY: up down build logs shell-backend shell-db migrate seed test

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

shell-backend:
	docker-compose exec backend bash

shell-db:
	docker-compose exec postgres psql -U scraper_user -d cybersec_scraper

migrate:
	docker-compose exec backend alembic upgrade head

seed:
	docker-compose exec backend python -m scripts.seed_sources

test:
	docker-compose exec backend pytest tests/ -v
```

- [ ] **Step 10: Create directory structure**

```bash
mkdir -p backend/{api,models,scrapers,services,tasks,utils,schemas,tests}
mkdir -p frontend/src/{components,hooks,services,styles}
mkdir -p exports logs alembic/versions
```

- [ ] **Step 11: Verify Docker setup**

```bash
docker-compose config
```

Expected: Valid YAML output with no errors

- [ ] **Step 12: Commit**

```bash
git add .
git commit -m "feat: add project scaffolding and Docker setup"
```

---

## Task 2: Database Models & Migrations

**Files:**
- Create: `backend/config.py`
- Create: `backend/database.py`
- Create: `backend/models/__init__.py`
- Create: `backend/models/source.py`
- Create: `backend/models/scraped_data.py`
- Create: `backend/models/scrape_session.py`
- Create: `backend/models/export_log.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/001_initial_schema.py`

**Interfaces:**
- Consumes: `DATABASE_URL` from `.env`, Docker infrastructure from Task 1
- Produces: SQLAlchemy models (`Source`, `ScrapedData`, `ScrapeSession`, `ExportLog`), database connection (`get_db()`)

- [ ] **Step 1: Write config module**

Create `backend/config.py`:

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"
    SECRET_KEY: str
    LOG_LEVEL: str = "INFO"
    
    GITHUB_TOKEN: str = ""
    MITRE_API_KEY: str = ""
    
    SCRAPER_CONCURRENT_REQUESTS: int = 5
    SCRAPER_RETRY_MAX: int = 3
    SCRAPER_RETRY_BACKOFF: int = 2
    
    EXPORT_DIR: str = "/app/exports"
    EXPORT_FORMAT: str = "jsonl"
    OPENSEARCH_INDEX_NAME: str = "cybersec_knowledge"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

- [ ] **Step 2: Write database connection module**

Create `backend/database.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    echo=False
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **Step 3: Write Source model**

Create `backend/models/source.py`:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from database import Base

class Source(Base):
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    url = Column(String)
    scraper_module = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime)
    scrape_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Write ScrapedData model**

Create `backend/models/scraped_data.py`:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from database import Base

class ScrapedData(Base):
    __tablename__ = "scraped_data"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(500), nullable=False, index=True)
    content_type = Column(String(100), nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    content = Column(JSONB, nullable=False)
    tags = Column(ARRAY(String), default=list)
    severity = Column(String(50))
    url = Column(Text)
    content_hash = Column(String(64), nullable=False)
    first_seen_at = Column(DateTime, server_default=func.now())
    last_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    metadata = Column(JSONB)
    
    __table_args__ = (
        {'extend_existing': True}
    )
```

- [ ] **Step 5: Write ScrapeSession model**

Create `backend/models/scrape_session.py`:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from database import Base

class ScrapeSession(Base):
    __tablename__ = "scrape_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(255), unique=True)
    status = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    items_found = Column(Integer, default=0)
    items_inserted = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_deleted = Column(Integer, default=0)
    error_message = Column(Text)
    triggered_by = Column(String(100), default="manual")
```

- [ ] **Step 6: Write ExportLog model**

Create `backend/models/export_log.py`:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from database import Base

class ExportLog(Base):
    __tablename__ = "export_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    scrape_session_id = Column(Integer, ForeignKey("scrape_sessions.id", ondelete="CASCADE"))
    exported_at = Column(DateTime, server_default=func.now())
    items_exported = Column(Integer)
    export_file_path = Column(Text)
    export_format = Column(String(50))
    status = Column(String(50))
    error_message = Column(Text)
```

- [ ] **Step 7: Create models __init__.py**

Create `backend/models/__init__.py`:

```python
from models.source import Source
from models.scraped_data import ScrapedData
from models.scrape_session import ScrapeSession
from models.export_log import ExportLog

__all__ = ["Source", "ScrapedData", "ScrapeSession", "ExportLog"]
```

- [ ] **Step 8: Create alembic.ini**

Create `alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql://scraper_user:password@localhost:5432/cybersec_scraper

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 9: Create alembic env.py**

Create `alembic/env.py`:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from database import Base
from models import Source, ScrapedData, ScrapeSession, ExportLog
from config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 10: Create initial migration**

Create `alembic/versions/001_initial_schema.py`:

```python
"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
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

def downgrade() -> None:
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
```

- [ ] **Step 11: Copy .env.example to .env**

```bash
cp .env.example .env
```

- [ ] **Step 12: Start database**

```bash
docker-compose up -d postgres
```

Expected: PostgreSQL container running

- [ ] **Step 13: Run migrations**

```bash
docker-compose exec backend alembic upgrade head
```

Expected: Tables created successfully

- [ ] **Step 14: Verify schema**

```bash
docker-compose exec postgres psql -U scraper_user -d cybersec_scraper -c "\dt"
```

Expected: List shows sources, scraped_data, scrape_sessions, export_logs tables

- [ ] **Step 15: Commit**

```bash
git add backend/config.py backend/database.py backend/models/ alembic.ini alembic/
git commit -m "feat: add database models and migrations"
```

---

## Task 3: Celery Setup & Base Scraper

**Files:**
- Create: `backend/celery_app.py`
- Create: `backend/utils/__init__.py`
- Create: `backend/utils/hash_utils.py`
- Create: `backend/scrapers/__init__.py`
- Create: `backend/scrapers/base.py`

**Interfaces:**
- Consumes: `settings.CELERY_BROKER_URL`, `settings.REDIS_URL`, models from Task 2
- Produces: `celery_app` instance, `BaseScraper` abstract class with methods `get_source_name()`, `fetch_data()`, `normalize_item()`, `compute_hash()`, `sync_to_db()`, `run()`

- [ ] **Step 1: Write hash utility**

Create `backend/utils/hash_utils.py`:

```python
import hashlib
import json
from typing import Dict, Any

def compute_content_hash(content: Dict[Any, Any]) -> str:
    """Generate SHA256 hash of content for change detection"""
    content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
```

- [ ] **Step 2: Write utils __init__.py**

Create `backend/utils/__init__.py`:

```python
from utils.hash_utils import compute_content_hash

__all__ = ["compute_content_hash"]
```

- [ ] **Step 3: Write Celery app configuration**

Create `backend/celery_app.py`:

```python
from celery import Celery
from config import settings

celery_app = Celery(
    "cybersec_scraper",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.scrape_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=2000,
    task_soft_time_limit=1800,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
```

- [ ] **Step 4: Write base scraper interface**

Create `backend/scrapers/base.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime
from models import ScrapedData
from utils import compute_content_hash
import logging

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self, session_id: int, db: AsyncSession):
        self.session_id = session_id
        self.db = db
        self.source_name = self.get_source_name()
        self.source_id: Optional[int] = None
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return source identifier (e.g., 'owasp', 'mitre_attack')"""
        pass
    
    @abstractmethod
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch raw data from source"""
        pass
    
    @abstractmethod
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        """
        Transform raw data to standard schema.
        
        Returns dict with keys:
        - external_id: str
        - content_type: str
        - title: str
        - description: str (optional)
        - content: dict (JSONB)
        - tags: list[str]
        - severity: str (optional)
        - url: str (optional)
        """
        pass
    
    def compute_hash(self, content: Dict) -> str:
        """Generate SHA256 hash for change detection"""
        return compute_content_hash(content)
    
    async def get_source_id(self) -> int:
        """Get source ID from database"""
        if self.source_id:
            return self.source_id
        
        from models import Source
        result = await self.db.execute(
            select(Source.id).where(Source.name == self.source_name)
        )
        self.source_id = result.scalar_one()
        return self.source_id
    
    async def sync_to_db(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Differential sync logic:
        - NEW: in fetched, not in DB → INSERT
        - UPDATED: in both, different hash → UPDATE
        - UNCHANGED: in both, same hash → SKIP
        - DELETED: in DB, not in fetched → DELETE
        
        Returns stats: {inserted, updated, deleted, unchanged}
        """
        source_id = await self.get_source_id()
        
        # Build lookup of fetched items
        fetched_map = {}
        for item in items:
            item['content_hash'] = self.compute_hash(item['content'])
            item['source_id'] = source_id
            fetched_map[item['external_id']] = item
        
        # Fetch existing items from DB
        result = await self.db.execute(
            select(ScrapedData).where(
                ScrapedData.source_id == source_id,
                ScrapedData.is_deleted == False
            )
        )
        existing = result.scalars().all()
        existing_map = {row.external_id: row for row in existing}
        
        stats = {'inserted': 0, 'updated': 0, 'deleted': 0, 'unchanged': 0}
        
        # Process fetched items
        for ext_id, item in fetched_map.items():
            if ext_id not in existing_map:
                # NEW → INSERT
                new_item = ScrapedData(**item)
                self.db.add(new_item)
                stats['inserted'] += 1
                logger.info(f"INSERT: {ext_id}")
            else:
                existing_item = existing_map[ext_id]
                if item['content_hash'] != existing_item.content_hash:
                    # CHANGED → UPDATE
                    await self.db.execute(
                        update(ScrapedData)
                        .where(ScrapedData.id == existing_item.id)
                        .values(
                            title=item['title'],
                            description=item.get('description'),
                            content=item['content'],
                            tags=item.get('tags', []),
                            severity=item.get('severity'),
                            url=item.get('url'),
                            content_hash=item['content_hash'],
                            last_updated_at=datetime.utcnow()
                        )
                    )
                    stats['updated'] += 1
                    logger.info(f"UPDATE: {ext_id}")
                else:
                    # UNCHANGED → SKIP
                    stats['unchanged'] += 1
        
        # Find deleted items
        deleted_ids = set(existing_map.keys()) - set(fetched_map.keys())
        for ext_id in deleted_ids:
            existing_item = existing_map[ext_id]
            await self.db.execute(
                delete(ScrapedData).where(ScrapedData.id == existing_item.id)
            )
            stats['deleted'] += 1
            logger.info(f"DELETE: {ext_id}")
        
        await self.db.commit()
        return stats
    
    async def run(self) -> Dict[str, int]:
        """Main execution: fetch → normalize → sync"""
        logger.info(f"Starting scrape for {self.source_name}")
        
        try:
            raw_data = await self.fetch_data()
            logger.info(f"Fetched {len(raw_data)} items from {self.source_name}")
            
            normalized = []
            for raw_item in raw_data:
                try:
                    normalized_item = self.normalize_item(raw_item)
                    normalized.append(normalized_item)
                except Exception as e:
                    logger.error(f"Failed to normalize item: {e}", exc_info=True)
                    continue
            
            logger.info(f"Normalized {len(normalized)} items")
            
            stats = await self.sync_to_db(normalized)
            logger.info(f"Sync complete: {stats}")
            
            return stats
        except Exception as e:
            logger.error(f"Scraper failed: {e}", exc_info=True)
            raise
```

- [ ] **Step 5: Create scrapers __init__.py**

Create `backend/scrapers/__init__.py`:

```python
from scrapers.base import BaseScraper

__all__ = ["BaseScraper"]
```

- [ ] **Step 6: Test hash utility**

Create `backend/tests/test_hash_utils.py`:

```python
import pytest
from utils.hash_utils import compute_content_hash

def test_compute_hash_same_content():
    content1 = {"key": "value", "number": 123}
    content2 = {"number": 123, "key": "value"}
    
    hash1 = compute_content_hash(content1)
    hash2 = compute_content_hash(content2)
    
    assert hash1 == hash2
    assert len(hash1) == 64

def test_compute_hash_different_content():
    content1 = {"key": "value1"}
    content2 = {"key": "value2"}
    
    hash1 = compute_content_hash(content1)
    hash2 = compute_content_hash(content2)
    
    assert hash1 != hash2
```

- [ ] **Step 7: Run hash utility test**

```bash
docker-compose exec backend pytest tests/test_hash_utils.py -v
```

Expected: 2 tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/celery_app.py backend/utils/ backend/scrapers/ backend/tests/
git commit -m "feat: add Celery setup and base scraper interface"
```

---

## Task 4: OWASP Scraper Implementation

**Files:**
- Create: `backend/scrapers/owasp_scraper.py`
- Create: `backend/tests/test_owasp_scraper.py`
- Create: `backend/tests/fixtures/sample_owasp.json`

**Interfaces:**
- Consumes: `BaseScraper` from Task 3
- Produces: `OWASPScraper` class with methods implementing abstract methods from `BaseScraper`

- [ ] **Step 1: Write failing test for OWASP scraper**

Create `backend/tests/test_owasp_scraper.py`:

```python
import pytest
from scrapers.owasp_scraper import OWASPScraper

@pytest.mark.asyncio
async def test_owasp_scraper_normalize():
    scraper = OWASPScraper(session_id=1, db=None)
    
    raw_item = {
        "category": "A01",
        "year": 2021,
        "title": "Broken Access Control",
        "description": "Access control enforces policy...",
        "cwe_ids": ["CWE-22", "CWE-23"],
        "url": "https://owasp.org/Top10/A01_2021/"
    }
    
    normalized = scraper.normalize_item(raw_item)
    
    assert normalized['external_id'] == "owasp_A01_2021"
    assert normalized['content_type'] == "vulnerability"
    assert normalized['title'] == "Broken Access Control"
    assert normalized['content']['category'] == "A01"
    assert normalized['content']['year'] == 2021
    assert "access-control" in normalized['tags']
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker-compose exec backend pytest tests/test_owasp_scraper.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'scrapers.owasp_scraper'"

- [ ] **Step 3: Implement OWASP scraper**

Create `backend/scrapers/owasp_scraper.py`:

```python
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
import logging
import asyncio

logger = logging.getLogger(__name__)

class OWASPScraper(BaseScraper):
    """Scraper for OWASP Top 10 and related resources"""
    
    OWASP_TOP10_URL = "https://owasp.org/Top10/"
    
    def get_source_name(self) -> str:
        return "owasp"
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch OWASP Top 10 data"""
        items = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch OWASP Top 10 2021
            items.extend(await self._fetch_top10_2021(client))
            
            # Add delay to be polite
            await asyncio.sleep(2)
        
        return items
    
    async def _fetch_top10_2021(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """Fetch OWASP Top 10 2021 categories"""
        categories = [
            {
                "category": "A01",
                "title": "Broken Access Control",
                "url": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                "cwe_ids": ["CWE-200", "CWE-201", "CWE-352"]
            },
            {
                "category": "A02",
                "title": "Cryptographic Failures",
                "url": "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/",
                "cwe_ids": ["CWE-259", "CWE-327", "CWE-331"]
            },
            {
                "category": "A03",
                "title": "Injection",
                "url": "https://owasp.org/Top10/A03_2021-Injection/",
                "cwe_ids": ["CWE-79", "CWE-89", "CWE-73"]
            },
            {
                "category": "A04",
                "title": "Insecure Design",
                "url": "https://owasp.org/Top10/A04_2021-Insecure_Design/",
                "cwe_ids": ["CWE-209", "CWE-256", "CWE-501"]
            },
            {
                "category": "A05",
                "title": "Security Misconfiguration",
                "url": "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/",
                "cwe_ids": ["CWE-16", "CWE-611"]
            },
            {
                "category": "A06",
                "title": "Vulnerable and Outdated Components",
                "url": "https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/",
                "cwe_ids": ["CWE-1104"]
            },
            {
                "category": "A07",
                "title": "Identification and Authentication Failures",
                "url": "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/",
                "cwe_ids": ["CWE-297", "CWE-287", "CWE-384"]
            },
            {
                "category": "A08",
                "title": "Software and Data Integrity Failures",
                "url": "https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/",
                "cwe_ids": ["CWE-829", "CWE-494", "CWE-502"]
            },
            {
                "category": "A09",
                "title": "Security Logging and Monitoring Failures",
                "url": "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/",
                "cwe_ids": ["CWE-778", "CWE-117", "CWE-223"]
            },
            {
                "category": "A10",
                "title": "Server-Side Request Forgery",
                "url": "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/",
                "cwe_ids": ["CWE-918"]
            }
        ]
        
        result = []
        for cat in categories:
            try:
                response = await client.get(cat["url"])
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract description
                description = ""
                main_content = soup.find('div', class_='main-content')
                if main_content:
                    paragraphs = main_content.find_all('p', limit=3)
                    description = ' '.join([p.get_text(strip=True) for p in paragraphs])
                
                cat['description'] = description
                cat['year'] = 2021
                result.append(cat)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to fetch {cat['url']}: {e}")
                # Still include category with minimal data
                cat['description'] = f"OWASP Top 10 2021 - {cat['title']}"
                cat['year'] = 2021
                result.append(cat)
        
        return result
    
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        """Transform OWASP data to standard schema"""
        category = raw_item['category']
        year = raw_item['year']
        
        # Generate tags from title
        title_lower = raw_item['title'].lower()
        tags = ['owasp', f'owasp-{year}', category.lower()]
        
        # Add specific tags based on title
        if 'access' in title_lower:
            tags.append('access-control')
        if 'injection' in title_lower:
            tags.append('injection')
        if 'crypto' in title_lower:
            tags.append('cryptography')
        if 'auth' in title_lower:
            tags.append('authentication')
        if 'config' in title_lower:
            tags.append('configuration')
        
        return {
            'external_id': f"owasp_{category}_{year}",
            'content_type': 'vulnerability',
            'title': f"{category}: {raw_item['title']}",
            'description': raw_item.get('description', ''),
            'content': {
                'category': category,
                'year': year,
                'cwe_ids': raw_item.get('cwe_ids', []),
                'details': raw_item.get('description', '')
            },
            'tags': tags,
            'severity': 'high',
            'url': raw_item.get('url')
        }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
docker-compose exec backend pytest tests/test_owasp_scraper.py -v
```

Expected: 1 test passes

- [ ] **Step 5: Update scrapers __init__.py**

Modify `backend/scrapers/__init__.py`:

```python
from scrapers.base import BaseScraper
from scrapers.owasp_scraper import OWASPScraper

__all__ = ["BaseScraper", "OWASPScraper"]
```

- [ ] **Step 6: Commit**

```bash
git add backend/scrapers/owasp_scraper.py backend/tests/ backend/scrapers/__init__.py
git commit -m "feat: add OWASP scraper implementation"
```

---

---

## Task 5: MITRE ATT&CK Scraper Implementation

**Files:**
- Create: `backend/scrapers/mitre_attack_scraper.py`
- Create: `backend/tests/test_mitre_scraper.py`

**Interfaces:**
- Consumes: `BaseScraper` from Task 3
- Produces: `MITREAttackScraper` class implementing `BaseScraper`

- [ ] **Step 1: Write failing test for MITRE scraper**

Create `backend/tests/test_mitre_scraper.py`:

```python
import pytest
from scrapers.mitre_attack_scraper import MITREAttackScraper

@pytest.mark.asyncio
async def test_mitre_scraper_normalize():
    scraper = MITREAttackScraper(session_id=1, db=None)
    
    raw_item = {
        "id": "attack-pattern--d1fcf083-a721-4223-aedf-bf8960798d62",
        "type": "attack-pattern",
        "name": "PowerShell",
        "description": "Adversaries may abuse PowerShell commands...",
        "x_mitre_version": "1.3",
        "external_references": [
            {
                "source_name": "mitre-attack",
                "external_id": "T1059.001"
            }
        ],
        "x_mitre_platforms": ["Windows"],
        "kill_chain_phases": [
            {"kill_chain_name": "mitre-attack", "phase_name": "execution"}
        ]
    }
    
    normalized = scraper.normalize_item(raw_item)
    
    assert normalized['external_id'] == "T1059.001"
    assert normalized['content_type'] == "technique"
    assert normalized['title'] == "PowerShell"
    assert "execution" in normalized['tags']
```

- [ ] **Step 2: Run test to verify failure**

```bash
docker-compose exec backend pytest tests/test_mitre_scraper.py -v
```

Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement MITRE ATT&CK scraper**

Create `backend/scrapers/mitre_attack_scraper.py`:

```python
from typing import List, Dict, Any
import httpx
from scrapers.base import BaseScraper
import logging
import json

logger = logging.getLogger(__name__)

class MITREAttackScraper(BaseScraper):
    """Scraper for MITRE ATT&CK Framework"""
    
    MITRE_STIX_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    
    def get_source_name(self) -> str:
        return "mitre_attack"
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch MITRE ATT&CK data via STIX 2.0 JSON"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(self.MITRE_STIX_URL)
                response.raise_for_status()
                
                stix_data = response.json()
                
                # Filter for attack-pattern objects (techniques)
                techniques = [
                    obj for obj in stix_data.get('objects', [])
                    if obj.get('type') == 'attack-pattern' and not obj.get('revoked', False)
                ]
                
                logger.info(f"Fetched {len(techniques)} MITRE ATT&CK techniques")
                return techniques
                
            except Exception as e:
                logger.error(f"Failed to fetch MITRE ATT&CK data: {e}")
                raise
    
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        """Transform MITRE ATT&CK STIX data to standard schema"""
        
        # Extract technique ID
        technique_id = None
        for ref in raw_item.get('external_references', []):
            if ref.get('source_name') == 'mitre-attack':
                technique_id = ref.get('external_id')
                break
        
        if not technique_id:
            raise ValueError(f"No technique ID found for {raw_item.get('name')}")
        
        # Extract tactic from kill chain phases
        tactics = []
        for phase in raw_item.get('kill_chain_phases', []):
            if phase.get('kill_chain_name') == 'mitre-attack':
                tactics.append(phase.get('phase_name'))
        
        # Build tags
        tags = ['mitre-attack', technique_id.lower()]
        tags.extend(tactics)
        
        platforms = raw_item.get('x_mitre_platforms', [])
        tags.extend([p.lower() for p in platforms])
        
        # Determine if sub-technique
        is_sub_technique = '.' in technique_id
        parent_technique = technique_id.split('.')[0] if is_sub_technique else None
        
        return {
            'external_id': technique_id,
            'content_type': 'technique',
            'title': raw_item['name'],
            'description': raw_item.get('description', ''),
            'content': {
                'technique_id': technique_id,
                'parent_technique': parent_technique,
                'is_sub_technique': is_sub_technique,
                'tactics': tactics,
                'platforms': platforms,
                'description': raw_item.get('description', ''),
                'mitre_version': raw_item.get('x_mitre_version')
            },
            'tags': tags,
            'url': f"https://attack.mitre.org/techniques/{technique_id.replace('.', '/')}/"
        }
```

- [ ] **Step 4: Run test to verify pass**

```bash
docker-compose exec backend pytest tests/test_mitre_scraper.py -v
```

Expected: 1 test passes

- [ ] **Step 5: Update scrapers __init__.py**

```python
from scrapers.base import BaseScraper
from scrapers.owasp_scraper import OWASPScraper
from scrapers.mitre_attack_scraper import MITREAttackScraper

__all__ = ["BaseScraper", "OWASPScraper", "MITREAttackScraper"]
```

- [ ] **Step 6: Commit**

```bash
git add backend/scrapers/mitre_attack_scraper.py backend/tests/test_mitre_scraper.py backend/scrapers/__init__.py
git commit -m "feat: add MITRE ATT&CK scraper implementation"
```

---

## Task 6: GitHub Payloads Scraper Implementation

**Files:**
- Create: `backend/scrapers/github_scraper.py`
- Create: `backend/tests/test_github_scraper.py`

**Interfaces:**
- Consumes: `BaseScraper` from Task 3, `settings.GITHUB_TOKEN`
- Produces: `GitHubScraper` class implementing `BaseScraper`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_github_scraper.py`:

```python
import pytest
from scrapers.github_scraper import GitHubScraper

@pytest.mark.asyncio
async def test_github_scraper_normalize():
    scraper = GitHubScraper(session_id=1, db=None)
    
    raw_item = {
        "repo": "swisskyrepo/PayloadsAllTheThings",
        "file_path": "XSS Injection/README.md",
        "stars": 54321,
        "content": "<script>alert('XSS')</script>",
        "url": "https://github.com/swisskyrepo/PayloadsAllTheThings"
    }
    
    normalized = scraper.normalize_item(raw_item)
    
    assert normalized['content_type'] == "payload"
    assert "xss" in normalized['tags']
    assert normalized['content']['repo'] == "swisskyrepo/PayloadsAllTheThings"
```

- [ ] **Step 2: Run test to verify failure**

```bash
docker-compose exec backend pytest tests/test_github_scraper.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement GitHub scraper**

Create `backend/scrapers/github_scraper.py`:

```python
from typing import List, Dict, Any
from github import Github, RateLimitExceededException
from scrapers.base import BaseScraper
from config import settings
import logging
import asyncio
import hashlib

logger = logging.getLogger(__name__)

class GitHubScraper(BaseScraper):
    """Scraper for GitHub payload repositories"""
    
    CURATED_REPOS = [
        "swisskyrepo/PayloadsAllTheThings",
        "danielmiessler/SecLists",
        "offensive-security/exploitdb"
    ]
    
    def get_source_name(self) -> str:
        return "github_payloads"
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch payload files from curated GitHub repos"""
        
        if not settings.GITHUB_TOKEN:
            logger.warning("No GitHub token configured, using anonymous access (60 req/hour)")
            g = Github()
        else:
            g = Github(settings.GITHUB_TOKEN)
        
        items = []
        
        for repo_name in self.CURATED_REPOS:
            try:
                logger.info(f"Fetching from {repo_name}")
                repo = g.get_repo(repo_name)
                
                # Get README and key payload files (limit for Phase A)
                contents = repo.get_contents("")
                
                for content in contents[:50]:  # Limit to first 50 items
                    if content.type == "file" and content.name.endswith(('.md', '.txt', '.html')):
                        try:
                            file_content = content.decoded_content.decode('utf-8')
                            
                            items.append({
                                'repo': repo_name,
                                'file_path': content.path,
                                'stars': repo.stargazers_count,
                                'content': file_content[:5000],  # Limit content size
                                'url': content.html_url,
                                'sha': content.sha
                            })
                            
                        except Exception as e:
                            logger.warning(f"Failed to decode {content.path}: {e}")
                            continue
                
                logger.info(f"Fetched {len(items)} items from {repo_name}")
                
                # Rate limit check
                rate_limit = g.get_rate_limit()
                if rate_limit.core.remaining < 100:
                    logger.warning(f"Rate limit low: {rate_limit.core.remaining} remaining")
                    await asyncio.sleep(5)
                
            except RateLimitExceededException:
                logger.error(f"Rate limit exceeded for {repo_name}")
                break
            except Exception as e:
                logger.error(f"Failed to fetch {repo_name}: {e}")
                continue
        
        return items
    
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        """Transform GitHub data to standard schema"""
        
        file_path = raw_item['file_path']
        repo = raw_item['repo']
        
        # Generate external_id from repo + file path hash
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        external_id = f"github_{repo.replace('/', '_')}_{path_hash}"
        
        # Extract tags from file path
        tags = ['github', 'payload']
        
        path_lower = file_path.lower()
        if 'xss' in path_lower:
            tags.append('xss')
        if 'sql' in path_lower:
            tags.append('sql-injection')
        if 'xxe' in path_lower:
            tags.append('xxe')
        if 'rce' in path_lower or 'command' in path_lower:
            tags.append('rce')
        
        title = f"{file_path} - {repo}"
        
        return {
            'external_id': external_id,
            'content_type': 'payload',
            'title': title,
            'description': f"Payload from {repo}",
            'content': {
                'repo': repo,
                'file_path': file_path,
                'stars': raw_item['stars'],
                'payload_content': raw_item['content'],
                'sha': raw_item.get('sha')
            },
            'tags': tags,
            'url': raw_item['url']
        }
```

- [ ] **Step 4: Run test to verify pass**

```bash
docker-compose exec backend pytest tests/test_github_scraper.py -v
```

Expected: 1 test passes

- [ ] **Step 5: Update scrapers __init__.py**

```python
from scrapers.base import BaseScraper
from scrapers.owasp_scraper import OWASPScraper
from scrapers.mitre_attack_scraper import MITREAttackScraper
from scrapers.github_scraper import GitHubScraper

__all__ = ["BaseScraper", "OWASPScraper", "MITREAttackScraper", "GitHubScraper"]
```

- [ ] **Step 6: Commit**

```bash
git add backend/scrapers/github_scraper.py backend/tests/test_github_scraper.py backend/scrapers/__init__.py
git commit -m "feat: add GitHub payloads scraper implementation"
```

---

## Task 7: Kali Docs Scraper Implementation

**Files:**
- Create: `backend/scrapers/kali_docs_scraper.py`
- Create: `backend/tests/test_kali_scraper.py`

**Interfaces:**
- Consumes: `BaseScraper` from Task 3
- Produces: `KaliDocsScraper` class implementing `BaseScraper`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_kali_scraper.py`:

```python
import pytest
from scrapers.kali_docs_scraper import KaliDocsScraper

@pytest.mark.asyncio
async def test_kali_scraper_normalize():
    scraper = KaliDocsScraper(session_id=1, db=None)
    
    raw_item = {
        "tool_name": "nmap",
        "category": "Information Gathering",
        "description": "Network exploration and security auditing",
        "usage": "nmap [Scan Type] [Options] {target}",
        "url": "https://tools.kali.org/information-gathering/nmap"
    }
    
    normalized = scraper.normalize_item(raw_item)
    
    assert normalized['external_id'] == "kali_nmap"
    assert normalized['content_type'] == "tool_doc"
    assert "nmap" in normalized['tags']
```

- [ ] **Step 2: Run test to verify failure**

```bash
docker-compose exec backend pytest tests/test_kali_scraper.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement Kali docs scraper**

Create `backend/scrapers/kali_docs_scraper.py`:

```python
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
import logging
import asyncio

logger = logging.getLogger(__name__)

class KaliDocsScraper(BaseScraper):
    """Scraper for Kali Linux tools documentation"""
    
    TOOLS_KALI_URL = "https://www.kali.org/tools/"
    
    # Hardcoded popular tools (Phase A - will expand in Phase C)
    POPULAR_TOOLS = [
        {
            "name": "nmap",
            "category": "Information Gathering",
            "description": "Network exploration tool and security / port scanner",
            "url": "https://www.kali.org/tools/nmap/",
            "usage": "nmap [Scan Type...] [Options] {target specification}"
        },
        {
            "name": "metasploit-framework",
            "category": "Exploitation Tools",
            "description": "Advanced open-source platform for developing, testing, and executing exploits",
            "url": "https://www.kali.org/tools/metasploit-framework/",
            "usage": "msfconsole"
        },
        {
            "name": "burpsuite",
            "category": "Web Application Analysis",
            "description": "Integrated platform for performing security testing of web applications",
            "url": "https://www.kali.org/tools/burpsuite/",
            "usage": "burpsuite"
        },
        {
            "name": "sqlmap",
            "category": "Web Application Analysis",
            "description": "Automatic SQL injection and database takeover tool",
            "url": "https://www.kali.org/tools/sqlmap/",
            "usage": "sqlmap -u <URL> [options]"
        },
        {
            "name": "wireshark",
            "category": "Sniffing & Spoofing",
            "description": "Network protocol analyzer",
            "url": "https://www.kali.org/tools/wireshark/",
            "usage": "wireshark"
        },
        {
            "name": "aircrack-ng",
            "category": "Wireless Attacks",
            "description": "WiFi security auditing tools suite",
            "url": "https://www.kali.org/tools/aircrack-ng/",
            "usage": "aircrack-ng [options] <input file(s)>"
        },
        {
            "name": "john",
            "category": "Password Attacks",
            "description": "John the Ripper password cracker",
            "url": "https://www.kali.org/tools/john/",
            "usage": "john [options] [password files]"
        },
        {
            "name": "hashcat",
            "category": "Password Attacks",
            "description": "Advanced password recovery utility",
            "url": "https://www.kali.org/tools/hashcat/",
            "usage": "hashcat [options]... hash|hashfile [dictionary|mask|directory]..."
        },
        {
            "name": "nikto",
            "category": "Web Application Analysis",
            "description": "Web server scanner",
            "url": "https://www.kali.org/tools/nikto/",
            "usage": "nikto -h <target>"
        },
        {
            "name": "hydra",
            "category": "Password Attacks",
            "description": "Parallelized login cracker",
            "url": "https://www.kali.org/tools/hydra/",
            "usage": "hydra [options] target service"
        }
    ]
    
    def get_source_name(self) -> str:
        return "kali_docs"
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch Kali tools documentation"""
        items = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for tool in self.POPULAR_TOOLS:
                try:
                    response = await client.get(tool['url'])
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract detailed description
                    content_div = soup.find('div', class_='content')
                    if content_div:
                        paragraphs = content_div.find_all('p', limit=5)
                        detailed_desc = ' '.join([p.get_text(strip=True) for p in paragraphs])
                        tool['detailed_description'] = detailed_desc
                    
                    # Extract examples if present
                    code_blocks = soup.find_all('code')
                    examples = [code.get_text(strip=True) for code in code_blocks[:3]]
                    tool['examples'] = examples
                    
                    items.append(tool)
                    
                    await asyncio.sleep(1)  # Be polite
                    
                except Exception as e:
                    logger.error(f"Failed to fetch {tool['name']}: {e}")
                    # Still include basic tool info
                    items.append(tool)
        
        return items
    
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        """Transform Kali tool data to standard schema"""
        
        tool_name = raw_item['name']
        category = raw_item['category']
        
        tags = ['kali', 'tool', tool_name.lower()]
        
        # Add category-based tags
        cat_lower = category.lower()
        if 'web' in cat_lower:
            tags.append('web-security')
        if 'password' in cat_lower:
            tags.append('password-cracking')
        if 'wireless' in cat_lower:
            tags.append('wireless')
        if 'information' in cat_lower:
            tags.append('reconnaissance')
        if 'exploitation' in cat_lower:
            tags.append('exploitation')
        
        return {
            'external_id': f"kali_{tool_name}",
            'content_type': 'tool_doc',
            'title': f"{tool_name} - {category}",
            'description': raw_item['description'],
            'content': {
                'tool_name': tool_name,
                'category': category,
                'description': raw_item['description'],
                'detailed_description': raw_item.get('detailed_description', ''),
                'usage': raw_item['usage'],
                'examples': raw_item.get('examples', [])
            },
            'tags': tags,
            'url': raw_item['url']
        }
```

- [ ] **Step 4: Run test to verify pass**

```bash
docker-compose exec backend pytest tests/test_kali_scraper.py -v
```

Expected: 1 test passes

- [ ] **Step 5: Update scrapers __init__.py**

```python
from scrapers.base import BaseScraper
from scrapers.owasp_scraper import OWASPScraper
from scrapers.mitre_attack_scraper import MITREAttackScraper
from scrapers.github_scraper import GitHubScraper
from scrapers.kali_docs_scraper import KaliDocsScraper

__all__ = [
    "BaseScraper",
    "OWASPScraper",
    "MITREAttackScraper",
    "GitHubScraper",
    "KaliDocsScraper"
]
```

- [ ] **Step 6: Commit**

```bash
git add backend/scrapers/kali_docs_scraper.py backend/tests/test_kali_scraper.py backend/scrapers/__init__.py
git commit -m "feat: add Kali Linux docs scraper implementation"
```

---

## Task 8: Celery Tasks & Error Handling

**Files:**
- Create: `backend/tasks/__init__.py`
- Create: `backend/tasks/scrape_tasks.py`
- Create: `backend/utils/error_handler.py`

**Interfaces:**
- Consumes: All scrapers from Tasks 4-7, `celery_app` from Task 3, models from Task 2
- Produces: `scrape_source_task(source_id, session_id)` Celery task

- [ ] **Step 1: Write error handler utility**

Create `backend/utils/error_handler.py`:

```python
import logging
from typing import Dict, Any
from celery import Task
from functools import wraps

logger = logging.getLogger(__name__)

ERROR_CATEGORIES = {
    'network': ['ConnectionError', 'Timeout', 'DNSError', 'httpx.ConnectError'],
    'auth': ['Unauthorized', 'Forbidden', 'APIKeyInvalid'],
    'rate_limit': ['RateLimitExceededException', 'TooManyRequests'],
    'parsing': ['ParseError', 'JSONDecodeError', 'ValueError'],
    'data': ['EmptyResponse', 'MalformedData']
}

def categorize_error(error: Exception) -> str:
    """Categorize error type for reporting"""
    error_name = type(error).__name__
    
    for category, error_types in ERROR_CATEGORIES.items():
        if any(err_type in error_name for err_type in error_types):
            return category
    
    return 'unknown'

def retry_on_network_error(max_retries=3, backoff_factor=2):
    """Decorator for retrying on network errors"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    category = categorize_error(e)
                    
                    if category in ['network', 'rate_limit'] and attempt < max_retries - 1:
                        delay = backoff_factor ** attempt
                        logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        raise
            
        return wrapper
    return decorator
```

- [ ] **Step 2: Write scrape task**

Create `backend/tasks/scrape_tasks.py`:

```python
from celery import Task
from celery_app import celery_app
from database import AsyncSessionLocal
from models import Source, ScrapeSession
from scrapers import OWASPScraper, MITREAttackScraper, GitHubScraper, KaliDocsScraper
from sqlalchemy import select, update
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    'owasp': OWASPScraper,
    'mitre_attack': MITREAttackScraper,
    'github_payloads': GitHubScraper,
    'kali_docs': KaliDocsScraper
}

class ScrapeTask(Task):
    """Custom task with progress tracking"""
    
    def update_progress(self, session_id: int, current: int, total: int, status: str, stats: dict = None):
        """Update task state with progress"""
        self.update_state(
            state='PROGRESS',
            meta={
                'session_id': session_id,
                'current': current,
                'total': total,
                'percentage': int((current / total) * 100) if total > 0 else 0,
                'status': status,
                'stats': stats or {}
            }
        )

@celery_app.task(
    bind=True,
    base=ScrapeTask,
    max_retries=3,
    soft_time_limit=1800,
    time_limit=2000,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
async def scrape_source_task(self, source_id: int, session_id: int):
    """Execute scraping for a source"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Update session status
            await db.execute(
                update(ScrapeSession)
                .where(ScrapeSession.id == session_id)
                .values(status='running', task_id=self.request.id)
            )
            await db.commit()
            
            # Get source
            result = await db.execute(
                select(Source).where(Source.id == source_id)
            )
            source = result.scalar_one()
            
            logger.info(f"Starting scrape for {source.name} (session {session_id})")
            
            # Get scraper class
            scraper_class = SCRAPER_MAP.get(source.name)
            if not scraper_class:
                raise ValueError(f"No scraper found for source: {source.name}")
            
            # Initialize scraper
            scraper = scraper_class(session_id=session_id, db=db)
            
            # Update progress
            self.update_progress(session_id, 0, 100, f"Starting {source.display_name} scrape...")
            
            # Run scraper
            stats = await scraper.run()
            
            # Update session with results
            await db.execute(
                update(ScrapeSession)
                .where(ScrapeSession.id == session_id)
                .values(
                    status='completed',
                    completed_at=datetime.utcnow(),
                    items_found=sum(stats.values()),
                    items_inserted=stats['inserted'],
                    items_updated=stats['updated'],
                    items_deleted=stats['deleted']
                )
            )
            
            # Update source last_scraped_at
            await db.execute(
                update(Source)
                .where(Source.id == source_id)
                .values(
                    last_scraped_at=datetime.utcnow(),
                    scrape_count=Source.scrape_count + 1
                )
            )
            
            await db.commit()
            
            logger.info(f"Completed scrape for {source.name}: {stats}")
            
            # Final progress update
            self.update_progress(session_id, 100, 100, "Completed", stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Scrape task failed: {e}", exc_info=True)
            
            # Update session with error
            await db.execute(
                update(ScrapeSession)
                .where(ScrapeSession.id == session_id)
                .values(
                    status='failed',
                    completed_at=datetime.utcnow(),
                    error_message=str(e)
                )
            )
            await db.commit()
            
            raise
```

- [ ] **Step 3: Create tasks __init__.py**

Create `backend/tasks/__init__.py`:

```python
from tasks.scrape_tasks import scrape_source_task

__all__ = ["scrape_source_task"]
```

- [ ] **Step 4: Test error handler**

Create `backend/tests/test_error_handler.py`:

```python
import pytest
from utils.error_handler import categorize_error

def test_categorize_network_error():
    error = ConnectionError("Network unreachable")
    category = categorize_error(error)
    assert category == "network"

def test_categorize_json_error():
    import json
    error = json.JSONDecodeError("", "", 0)
    category = categorize_error(error)
    assert category == "parsing"
```

- [ ] **Step 5: Run test**

```bash
docker-compose exec backend pytest tests/test_error_handler.py -v
```

Expected: 2 tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/tasks/ backend/utils/error_handler.py backend/tests/test_error_handler.py
git commit -m "feat: add Celery tasks and error handling"
```

---

## Task 9: Export Service (OpenSearch JSONL)

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/export_service.py`
- Create: `backend/tests/test_export_service.py`

**Interfaces:**
- Consumes: `ScrapedData` model from Task 2, `settings.EXPORT_DIR`
- Produces: `ExportService` class with method `export_to_jsonl(items, index_name, filename) -> str`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_export_service.py`:

```python
import pytest
import json
from pathlib import Path
from services.export_service import ExportService
from datetime import datetime

@pytest.fixture
def sample_items():
    return [
        {
            'source': 'owasp',
            'external_id': 'A01_2021',
            'title': 'Broken Access Control',
            'description': 'Test description',
            'content': {'category': 'A01'},
            'tags': ['owasp', 'access-control'],
            'url': 'https://example.com',
            'last_updated_at': datetime(2026, 9, 1)
        }
    ]

def test_export_to_jsonl(tmp_path, sample_items):
    service = ExportService(export_dir=str(tmp_path))
    
    filepath = service.export_to_jsonl(sample_items, 'test_index', 'test_export.jsonl')
    
    assert Path(filepath).exists()
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    assert len(lines) == 2
    
    index_meta = json.loads(lines[0])
    assert index_meta['index']['_index'] == 'test_index'
    
    doc = json.loads(lines[1])
    assert doc['title'] == 'Broken Access Control'
```

- [ ] **Step 2: Run test to verify failure**

```bash
docker-compose exec backend pytest tests/test_export_service.py -v
```

Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement export service**

Create `backend/services/export_service.py`:

```python
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ExportService:
    """Export scraped data to OpenSearch-compatible format"""
    
    def __init__(self, export_dir: str = "/app/exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_jsonl(
        self, 
        items: List[Dict], 
        index_name: str = "cybersec_knowledge",
        filename: Optional[str] = None
    ) -> str:
        """
        Export items to OpenSearch bulk import format (JSONL)
        
        Format:
        {"index": {"_index": "index_name", "_id": "doc_id"}}
        {"field1": "value1", "field2": "value2"}
        """
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"opensearch_export_{timestamp}.jsonl"
        
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in items:
                # Index action line
                index_meta = {
                    "index": {
                        "_index": index_name,
                        "_id": f"{item['source']}_{item['external_id']}"
                    }
                }
                f.write(json.dumps(index_meta) + '\n')
                
                # Document line
                doc = self._format_document(item)
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        
        logger.info(f"Exported {len(items)} items to {filepath}")
        return str(filepath)
    
    def export_to_json(
        self,
        items: List[Dict],
        filename: Optional[str] = None
    ) -> str:
        """Export as single JSON array (alternative format)"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.json"
        
        filepath = self.export_dir / filename
        
        documents = [self._format_document(item) for item in items]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(items)} items to {filepath}")
        return str(filepath)
    
    def _format_document(self, item: Dict) -> Dict:
        """Format item for OpenSearch ingestion"""
        
        doc = {
            'id': f"{item['source']}_{item['external_id']}",
            'source': item['source'],
            'external_id': item['external_id'],
            'title': item['title'],
            'description': item.get('description', ''),
            'content': self._format_content_text(item),
            'content_type': item.get('content_type', ''),
            'tags': item.get('tags', []),
            'url': item.get('url'),
            'scraped_at': item['last_updated_at'].isoformat() if item.get('last_updated_at') else None,
            'metadata': item.get('content', {})
        }
        
        if item.get('severity'):
            doc['severity'] = item['severity']
        
        return doc
    
    def _format_content_text(self, item: Dict) -> str:
        """Format content as searchable text"""
        
        parts = [f"# {item['title']}\n"]
        
        if item.get('description'):
            parts.append(f"{item['description']}\n")
        
        content = item.get('content', {})
        content_type = item.get('content_type', '')
        
        if content_type == 'technique':
            parts.append(f"**Tactic:** {content.get('tactic', 'N/A')}")
            parts.append(f"**Technique ID:** {content.get('technique_id', 'N/A')}")
            if content.get('platforms'):
                parts.append(f"**Platforms:** {', '.join(content['platforms'])}")
            if content.get('description'):
                parts.append(f"\n{content['description']}")
                
        elif content_type == 'vulnerability':
            parts.append(f"**Category:** {content.get('category', 'N/A')}")
            if content.get('cwe_ids'):
                parts.append(f"**CWE:** {', '.join(content['cwe_ids'])}")
            if content.get('details'):
                parts.append(f"\n{content['details']}")
                
        elif content_type == 'payload':
            parts.append(f"**Repository:** {content.get('repo', 'N/A')}")
            if content.get('file_path'):
                parts.append(f"**File:** {content['file_path']}")
            if content.get('payload_content'):
                parts.append(f"\n```\n{content['payload_content'][:500]}\n```")
                
        elif content_type == 'tool_doc':
            parts.append(f"**Tool:** {content.get('tool_name', 'N/A')}")
            parts.append(f"**Category:** {content.get('category', 'N/A')}")
            if content.get('usage'):
                parts.append(f"\n**Usage:**\n{content['usage']}")
            if content.get('examples'):
                parts.append(f"\n**Examples:**\n" + '\n'.join(content['examples'][:3]))
        
        if item.get('tags'):
            parts.append(f"\n**Tags:** {', '.join(item['tags'])}")
        
        return '\n'.join(parts)
```

- [ ] **Step 4: Create services __init__.py**

Create `backend/services/__init__.py`:

```python
from services.export_service import ExportService

__all__ = ["ExportService"]
```

- [ ] **Step 5: Run test to verify pass**

```bash
docker-compose exec backend pytest tests/test_export_service.py -v
```

Expected: 1 test passes

- [ ] **Step 6: Commit**

```bash
git add backend/services/ backend/tests/test_export_service.py
git commit -m "feat: add OpenSearch JSONL export service"
```

---

## Task 10: FastAPI Application & Health Endpoint

**Files:**
- Create: `backend/main.py`
- Create: `backend/schemas/__init__.py`
- Create: `backend/schemas/health.py`

**Interfaces:**
- Consumes: `settings` from Task 2, `database` from Task 2
- Produces: FastAPI app instance with `/health` endpoint

- [ ] **Step 1: Write health schema**

Create `backend/schemas/health.py`:

```python
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
```

- [ ] **Step 2: Create schemas __init__.py**

Create `backend/schemas/__init__.py`:

```python
from schemas.health import HealthResponse

__all__ = ["HealthResponse"]
```

- [ ] **Step 3: Write FastAPI application**

Create `backend/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import engine
from sqlalchemy import text
import redis
import logging

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cybersecurity Data Scraper API",
    description="API for scraping cybersecurity intelligence",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    health = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }
    
    # Check database
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health["database"] = "disconnected"
        health["status"] = "unhealthy"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health["redis"] = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health["redis"] = "disconnected"
        health["status"] = "unhealthy"
    
    return health

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    await engine.dispose()
```

- [ ] **Step 4: Test health endpoint locally**

```bash
docker-compose up -d postgres redis backend
```

- [ ] **Step 5: Call health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: JSON response with `{"status": "healthy", "database": "connected", "redis": "connected"}`

- [ ] **Step 6: Check API docs**

Open browser: `http://localhost:8000/docs`

Expected: Swagger UI with /health endpoint

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/schemas/
git commit -m "feat: add FastAPI application with health endpoint"
```

---

## Task 11: Sources API Endpoints

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/api/sources.py`
- Create: `backend/schemas/source.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: `Source`, `ScrapeSession` models, `get_db()` from Task 2, `scrape_source_task` from Task 8
- Produces: API endpoints: `GET /api/sources`, `GET /api/sources/{id}`, `POST /api/sources/{id}/scrape`

- [ ] **Step 1: Write source schemas**

Create `backend/schemas/source.py`:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SourceBase(BaseModel):
    name: str
    display_name: str
    url: Optional[str] = None
    enabled: bool = True

class SourceResponse(SourceBase):
    id: int
    scraper_module: str
    last_scraped_at: Optional[datetime]
    scrape_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class SourceWithStats(SourceResponse):
    total_items: int = 0
    last_session_status: Optional[str] = None
```

- [ ] **Step 2: Write sources API**

Create `backend/api/sources.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import Source, ScrapeSession, ScrapedData
from schemas.source import SourceResponse, SourceWithStats
from tasks.scrape_tasks import scrape_source_task
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["sources"])

@router.get("", response_model=List[SourceWithStats])
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all sources with stats"""
    
    result = await db.execute(select(Source))
    sources = result.scalars().all()
    
    sources_with_stats = []
    for source in sources:
        # Get total items count
        count_result = await db.execute(
            select(func.count(ScrapedData.id))
            .where(ScrapedData.source_id == source.id, ScrapedData.is_deleted == False)
        )
        total_items = count_result.scalar() or 0
        
        # Get last session status
        session_result = await db.execute(
            select(ScrapeSession)
            .where(ScrapeSession.source_id == source.id)
            .order_by(ScrapeSession.started_at.desc())
            .limit(1)
        )
        last_session = session_result.scalar_one_or_none()
        
        source_dict = {
            "id": source.id,
            "name": source.name,
            "display_name": source.display_name,
            "url": source.url,
            "enabled": source.enabled,
            "scraper_module": source.scraper_module,
            "last_scraped_at": source.last_scraped_at,
            "scrape_count": source.scrape_count,
            "created_at": source.created_at,
            "total_items": total_items,
            "last_session_status": last_session.status if last_session else None
        }
        
        sources_with_stats.append(source_dict)
    
    return sources_with_stats

@router.get("/{source_id}", response_model=SourceWithStats)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """Get source detail with stats"""
    
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Get stats
    count_result = await db.execute(
        select(func.count(ScrapedData.id))
        .where(ScrapedData.source_id == source.id, ScrapedData.is_deleted == False)
    )
    total_items = count_result.scalar() or 0
    
    session_result = await db.execute(
        select(ScrapeSession)
        .where(ScrapeSession.source_id == source.id)
        .order_by(ScrapeSession.started_at.desc())
        .limit(1)
    )
    last_session = session_result.scalar_one_or_none()
    
    return {
        "id": source.id,
        "name": source.name,
        "display_name": source.display_name,
        "url": source.url,
        "enabled": source.enabled,
        "scraper_module": source.scraper_module,
        "last_scraped_at": source.last_scraped_at,
        "scrape_count": source.scrape_count,
        "created_at": source.created_at,
        "total_items": total_items,
        "last_session_status": last_session.status if last_session else None
    }

@router.post("/{source_id}/scrape")
async def trigger_scrape(source_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger manual scrape for a source"""
    
    # Verify source exists
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    if not source.enabled:
        raise HTTPException(status_code=400, detail="Source is disabled")
    
    # Create scrape session
    session = ScrapeSession(
        source_id=source_id,
        status='pending',
        triggered_by='manual'
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Enqueue Celery task
    task = scrape_source_task.apply_async(args=[source_id, session.id])
    
    logger.info(f"Triggered scrape for {source.name} (session {session.id}, task {task.id})")
    
    return {
        "session_id": session.id,
        "task_id": task.id,
        "status": "pending",
        "message": f"Scrape started for {source.display_name}"
    }
```

- [ ] **Step 3: Register router in main.py**

Modify `backend/main.py`, add after CORS middleware:

```python
from api import sources

app.include_router(sources.router)
```

- [ ] **Step 4: Create API __init__.py**

Create `backend/api/__init__.py`:

```python
from api import sources

__all__ = ["sources"]
```

- [ ] **Step 5: Test list sources endpoint**

```bash
curl http://localhost:8000/api/sources
```

Expected: JSON array (empty or with seeded sources)

- [ ] **Step 6: Commit**

```bash
git add backend/api/ backend/schemas/source.py backend/main.py
git commit -m "feat: add sources API endpoints"
```

---

*Plan continues with Tasks 12-20 covering Data API, Analytics, WebSocket, Frontend, Seed Script, and Integration Testing. The pattern established above will be followed for remaining tasks.*

**Remaining Tasks Summary:**
- Task 12: Data API (GET /api/data with filters, DELETE)
- Task 13: Sessions & Analytics API
- Task 14: WebSocket Progress Updates
- Task 15: Frontend Setup (Vite, TailwindCSS, React Router)
- Task 16: Dashboard Component
- Task 17: Data Browser Component
- Task 18: Analytics Component
- Task 19: Seed Script & README
- Task 20: Integration Tests & Deployment Verification

Each task follows TDD: write failing test → implement → verify pass → commit.

---

## Self-Review Checklist

**1. Spec coverage:**
✅ Database models (Task 2)
✅ All 4 scrapers (Tasks 4-7)
✅ Celery tasks (Task 8)
✅ Export service (Task 9)
✅ API endpoints started (Tasks 10-11)
⚠️ Frontend components (Tasks 15-18) - outlined but not fully detailed
⚠️ WebSocket (Task 14) - outlined but not fully detailed
⚠️ Seed script (Task 19) - outlined
⚠️ Integration tests (Task 20) - outlined

**2. Placeholder scan:**
✅ No TBDs or TODOs in Tasks 1-11
⚠️ Tasks 12-20 are summarized but need full detail

**3. Type consistency:**
✅ Models match between tasks
✅ Function signatures consistent
✅ Schema names align

**Action:** Tasks 1-11 are complete and ready for execution. Tasks 12-20 need full expansion before execution.

---

## Execution Options

**Plan saved to `docs/superpowers/plans/2026-09-01-cybersecurity-data-scraper.md`**

This plan is **partially complete** (Tasks 1-11 detailed, Tasks 12-20 outlined).

**Option 1: Execute Tasks 1-11 now, expand Tasks 12-20 later**
- Implement backend foundation (Tasks 1-11)
- Return for frontend planning

**Option 2: Complete full plan first (all 20 tasks detailed)**
- I'll expand Tasks 12-20 with same detail level
- Then execute all tasks

**Which approach?**
