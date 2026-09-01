# Cybersecurity Data Scraper

Automated scraping platform for cybersecurity intelligence from OWASP, MITRE ATT&CK, GitHub payloads, and Kali Linux tool documentation. Export to OpenSearch-compatible format for RAG systems.

## Features

- **Multi-Source Scraping**: OWASP, MITRE ATT&CK, GitHub, Kali docs
- **Smart Differential Sync**: Auto-detect changes (INSERT/UPDATE/DELETE)
- **Web UI**: Manual triggers, progress monitoring, search & filter
- **Analytics Dashboard**: Coverage, freshness, trends
- **OpenSearch Export**: JSONL bulk format for vector database
- **Async Processing**: Celery task queue with retry logic
- **Full-Text Search**: PostgreSQL + GIN indexes

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Celery, Redis
- **Frontend**: React 18, Vite, TailwindCSS, Recharts
- **Database**: PostgreSQL 15
- **Deployment**: Docker Compose

## Quick Start

### Prerequisites

- Docker & Docker Compose v2+
- 4 CPU cores, 8 GB RAM, 50 GB disk (recommended)
- Linux server (Ubuntu 22.04+ or Debian 11+)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/SaKuRa-u/cybersecurity-scraper
cd cybersecurity-scraper

# 2. Run setup script
chmod +x setup.sh
./setup.sh

# 3. Access application
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

## Configuration

Edit `.env` after running setup:
- `DATABASE_PASSWORD` - PostgreSQL password
- `SECRET_KEY` - Flask secret key (32+ chars)
- `GITHUB_TOKEN` - GitHub PAT for higher rate limits (optional)

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │◄────►│   FastAPI    │◄────►│ PostgreSQL  │
│  Frontend   │ HTTP │   Backend    │      │  Database   │
└─────────────┘      └──────┬───────┘      └─────────────┘
                            │
                            ├─────►  Celery Workers
                            │        (Scrapers)
                            │
                            └─────►  Redis
                                     (Task Queue)
```

## Data Export

```bash
# Export to OpenSearch format
curl -X POST "http://localhost:8000/api/export/opensearch?format=jsonl"
```

## Documentation

- [Design Specification](docs/superpowers/specs/2026-09-01-cybersecurity-data-scraper-design.md)
- [Implementation Plan](docs/superpowers/plans/2026-09-01-cybersecurity-data-scraper.md)

## Development

```bash
# Backend tests
docker-compose exec backend pytest tests/ -v

# Frontend dev server
cd frontend
npm run dev

# View logs
docker-compose logs -f backend
```

## License

MIT

## Support

- Issues: GitHub Issues
- API Docs: http://localhost:8000/docs
                 └─────►  Redis
                                     (Task Queue)
```

## Data Export

Export scraped data to OpenSearch format:

```bash
# Via API
curl -X POST "http://localhost:8000/api/export/opensearch?format=jsonl"

# Output: exports/opensearch_export_YYYYMMDD_HHMMSS.jsonl
```

Import to OpenSearch:

```bash
curl -X POST "localhost:9200/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @exports/opensearch_export_20260901_120000.jsonl
```

## Documentation

- [Design Specification](docs/superpowers/specs/2026-09-01-cybersecurity-data-scraper-design.md)
- [Implementation Plan](docs/superpowers/plans/2026-09-01-cybersecurity-data-scraper.md)
- [API Reference](http://localhost:8000/docs)

## Development

```bash
# Backend tests
docker-compose exec backend pytest tests/ -v

# Frontend dev server
cd frontend
npm run dev

# View logs
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Database shell
docker-compose exec postgres psql -U scraper_user -d cybersec_scraper
```

## Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart backend

# View all logs
docker-compose logs -f

# Run migrations
docker-compose exec backend alembic upgrade head

# Seed sources again
docker-compose exec backend python -m scripts.seed_sources

# Export data manually
docker-compose exec backend python -c "
from services.export_service import ExportService
from sqlalchemy import create_engine, select
from models import ScrapedData
# ... export logic
"
```

## Troubleshooting

### Services won't start

```bash
docker-compose logs backend
docker-compose restart backend
```

### Database connection failed

```bash
# Check PostgreSQL
docker-compose ps postgres

# Verify credentials
cat .env | grep DATABASE
```

### Scrape fails immediately

```bash
# Check Celery worker
docker-compose logs celery_worker

# Common fixes:
# - Add GITHUB_TOKEN for rate limits
# - Check network connectivity
# - Verify source URLs accessible
```

### Frontend can't connect

```bash
# Check backend health
curl http://localhost:8000/health

# Should return: {"status":"healthy",...}
```

## Production Deployment

See [Deployment Guide](docs/02-deployment.md) for:
- Nginx reverse proxy setup
- SSL/TLS with Let's Encrypt
- Firewall configuration
- Monitoring & backups
- Security hardening

## Contributing

1. Follow implementation plan in `docs/superpowers/plans/`
2. Each task has step-by-step instructions
3. Run tests before committing
4. Follow existing code style

## License

MIT

## Support

- Issues: GitHub Issues
- Documentation: `/docs` directory
- API Docs: http://localhost:8000/docs
