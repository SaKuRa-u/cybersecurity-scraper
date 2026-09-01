# Cybersecurity Data Scraper - Design Specification

**Date:** 2026-09-01  
**Status:** Draft  
**Target Phase:** A (Personal Use) → C (Production Service)

---

## Executive Summary

Platform untuk scraping cybersecurity intelligence dari multiple sources (OWASP, MITRE ATT&CK, GitHub payloads, Kali Linux tool documentation) dengan web interface untuk manual triggers, monitoring, search/filter, data management, dan analytics. Data diekspor dalam OpenSearch-compatible format untuk feeding RAG systems.

**Key Features:**
- Multi-source automated scraping with differential sync
- Web UI for manual control and monitoring
- Smart change detection (INSERT/UPDATE/DELETE/UNCHANGED)
- OpenSearch JSONL export for RAG integration
- Analytics dashboard for data coverage and trends

**Architecture:** Monolithic web app (FastAPI + React + PostgreSQL + Celery + Redis)

---

## 1. Requirements

### 1.1 Functional Requirements

**Data Sources (Phase A - All Priority):**
1. **OWASP** - vulnerability databases, Top 10, ASVS, CheatSheet Series
2. **MITRE ATT&CK** - tactics, techniques, procedures (STIX API)
3. **GitHub Payloads** - curated repos (PayloadsAllTheThings, SecLists, Exploit-DB) + CVE-linked repositories
4. **Kali Linux Tools Documentation** - tools.kali.org, man pages, GitHub repos, community sources (HackTricks, GTFOBins)

**Scraping Strategy:**
- Manual on-demand scraping via web UI (Phase A)
- Tools documentation only (not execution) - provide agent context for tool usage
- Differential sync: track changes between scrape sessions
  - New data → INSERT
  - Changed data → UPDATE
  - Unchanged data → SKIP (no action)
  - Deleted data (in DB but not in new fetch) → DELETE
- Idempotent operations

**Web Interface Requirements:**
- Dashboard with source cards and quick actions
- Manual trigger buttons per source with real-time progress
- Search & filter scraped data (by source, type, tags, full-text)
- Data management (view details, delete items, re-scrape)
- Analytics dashboard (coverage by source, data freshness, scraping trends, content types)
- Scrape session history with stats

**Export Requirements:**
- Generate OpenSearch-compatible JSONL files (bulk import format)
- Export location: `/exports` directory
- Format: `{"index": {...}}\n{"document": {...}}\n`
- Manual export trigger from UI or automatic post-scrape

### 1.2 Non-Functional Requirements

**Deployment:**
- Target: Linux server (Docker-based deployment)
- Phase A: Personal use, single user
- Phase C: Production service, multi-user, high availability

**Performance:**
- Handle 10,000+ scraped items per source
- Concurrent scraping with rate limiting (GitHub API: 5000/hour)
- Real-time progress updates via WebSocket
- Pagination (50 items/page default)

**Reliability:**
- Retry logic for transient failures (3 retries, exponential backoff)
- Graceful handling of source structure changes
- Partial scrape success (continue on item-level errors)
- Audit trail (scrape sessions log)

**Data Integrity:**
- SHA256 content hashing for change detection
- Database transactions for sync operations
- Soft deletes for audit trail

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       React Frontend                         │
│  (Scraper triggers, Progress, Search, Analytics, Data Mgmt) │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend                            │
│  • REST API endpoints                                        │
│  • WebSocket (real-time progress)                           │
│  • Authentication (future Phase C)                           │
└───────┬──────────────────────┬──────────────────────────────┘
        │                      │
        ▼                      ▼
┌──────────────┐      ┌────────────────┐
│ PostgreSQL   │      │ Celery Workers │
│              │      │ + Redis        │
│ • Scraped    │      │                │
│   data       │◄─────┤ • Scrapers     │
│ • Metadata   │      │ • Tasks        │
│ • Versions   │      │ • Scheduling   │
└──────┬───────┘      └────────────────┘
       │
       │ Export (JSONL files)
       ▼
┌──────────────┐
│ /exports     │
│ (OpenSearch  │
│  bulk format)│
└──────────────┘
```

### 2.2 Component Responsibilities

**Frontend (React + Vite + TailwindCSS):**
- Manual scraper triggers per source
- Real-time progress via WebSocket
- Search & filter scraped data
- Data management (view, delete, re-scrape)
- Analytics dashboard (coverage, freshness, stats)
- Session history

**Backend (FastAPI + Python 3.11):**
- REST API for CRUD operations
- Task management (enqueue/status/cancel)
- WebSocket server for live updates
- Data export orchestration

**Task Queue (Celery + Redis):**
- Async scraping tasks
- Retry logic & error handling
- Progress tracking
- Task prioritization

**Database (PostgreSQL 15):**
- Scraped data storage (JSONB for flexible schema)
- Metadata (source, timestamp, hash)
- Differential sync tracking
- Audit trail (scrape sessions, export logs)

**Scrapers (Python modules):**
- Modular per source (OWASP, MITRE, GitHub, Kali)
- Differential sync logic
- Data normalization to common schema
- Rate limiting & error handling

### 2.3 Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | React 18 + Vite | Modern, fast dev experience, component-based |
| | TailwindCSS | Utility-first CSS, rapid UI development |
| | Recharts | Analytics charts |
| | Axios | HTTP client |
| **Backend** | FastAPI | Async, fast, auto API docs, Python ecosystem |
| | SQLAlchemy 2.0 | ORM with async support |
| | Pydantic | Data validation |
| | Alembic | Database migrations |
| **Task Queue** | Celery + Redis | Proven, robust task queue, good monitoring |
| **Database** | PostgreSQL 15 | JSONB support, GIN indexes, reliable |
| **Scraping** | httpx | Async HTTP client |
| | BeautifulSoup4 | HTML parsing |
| | PyGithub | GitHub API wrapper |
| **Deployment** | Docker Compose | Container orchestration, easy deployment |

---

## 3. Database Schema

### 3.1 Schema Design

```sql
-- Sources (OWASP, ATT&CK, GitHub, Kali)
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,  -- 'owasp', 'mitre_attack', 'github_payloads', 'kali_docs'
    display_name VARCHAR(200) NOT NULL,
    url TEXT,
    scraper_module VARCHAR(100) NOT NULL,  -- Python module name
    enabled BOOLEAN DEFAULT true,
    last_scraped_at TIMESTAMP,
    scrape_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Scraped data (polymorphic - different sources, different fields)
CREATE TABLE scraped_data (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    external_id VARCHAR(500) NOT NULL,  -- unique ID from source (e.g., CVE-2024-1234, T1059)
    content_type VARCHAR(100) NOT NULL,  -- 'vulnerability', 'technique', 'payload', 'tool_doc'
    title TEXT NOT NULL,
    description TEXT,
    content JSONB NOT NULL,  -- flexible schema per source type
    tags TEXT[],  -- array untuk search
    severity VARCHAR(50),  -- for vulnerabilities
    url TEXT,  -- source URL
    content_hash VARCHAR(64) NOT NULL,  -- SHA256 for change detection
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_updated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT false,
    metadata JSONB,  -- extra fields per source
    UNIQUE(source_id, external_id)
);

-- Scrape sessions (audit trail)
CREATE TABLE scrape_sessions (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    task_id VARCHAR(255) UNIQUE,  -- Celery task ID
    status VARCHAR(50) NOT NULL,  -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    items_found INTEGER DEFAULT 0,
    items_inserted INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_deleted INTEGER DEFAULT 0,
    error_message TEXT,
    triggered_by VARCHAR(100) DEFAULT 'manual'  -- 'manual', 'scheduled', 'api'
);

-- Export logs (to OpenSearch)
CREATE TABLE export_logs (
    id SERIAL PRIMARY KEY,
    scrape_session_id INTEGER REFERENCES scrape_sessions(id) ON DELETE CASCADE,
    exported_at TIMESTAMP DEFAULT NOW(),
    items_exported INTEGER,
    export_file_path TEXT,
    export_format VARCHAR(50),  -- 'jsonl', 'json'
    status VARCHAR(50),
    error_message TEXT
);

-- Indexes for performance
CREATE INDEX idx_scraped_data_source ON scraped_data(source_id);
CREATE INDEX idx_scraped_data_external_id ON scraped_data(external_id);
CREATE INDEX idx_scraped_data_content_type ON scraped_data(content_type);
CREATE INDEX idx_scraped_data_tags ON scraped_data USING GIN(tags);
CREATE INDEX idx_scraped_data_content ON scraped_data USING GIN(content);
CREATE INDEX idx_scrape_sessions_status ON scrape_sessions(status);
CREATE INDEX idx_scrape_sessions_source ON scrape_sessions(source_id);
```

### 3.2 JSONB Content Structure Examples

**OWASP Vulnerability:**
```json
{
  "category": "A01",
  "year": 2021,
  "cwe_ids": ["CWE-22", "CWE-23"],
  "examples": ["Path traversal in file upload", "..."],
  "mitigation": "Validate and sanitize file paths",
  "references": ["https://owasp.org/..."]
}
```

**MITRE ATT&CK Technique:**
```json
{
  "tactic": "Execution",
  "technique_id": "T1059",
  "sub_technique": "001",
  "platforms": ["Windows", "Linux"],
  "description": "Adversaries may abuse command...",
  "detection": "Monitor process execution...",
  "mitigations": ["M1038", "M1026"]
}
```

**GitHub Payload:**
```json
{
  "repo": "swisskyrepo/PayloadsAllTheThings",
  "file_path": "XSS Injection/README.md",
  "stars": 54321,
  "cve": "CVE-2024-1234",
  "payload_content": "<script>alert('XSS')</script>",
  "last_commit_date": "2026-08-15"
}
```

**Kali Tool Documentation:**
```json
{
  "tool_name": "nmap",
  "category": "Information Gathering",
  "description": "Network exploration and security auditing",
  "usage": "nmap [Scan Type] [Options] {target}",
  "examples": [
    "nmap -sV -p 1-65535 192.168.1.1",
    "nmap -sS -O target.com"
  ],
  "man_page": "Full man page content...",
  "source_urls": ["https://nmap.org", "https://tools.kali.org/..."]
}
```

---

## 4. Scraper Architecture

### 4.1 Base Scraper Interface

```python
# backend/scrapers/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseScraper(ABC):
    def __init__(self, session_id: int, db_connection):
        self.session_id = session_id
        self.db = db_connection
        self.source_name = self.get_source_name()
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return source identifier"""
        pass
    
    @abstractmethod
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch raw data from source"""
        pass
    
    @abstractmethod
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        """Transform raw data to standard schema"""
        pass
    
    def compute_hash(self, content: Dict) -> str:
        """Generate SHA256 hash for change detection"""
        pass
    
    async def sync_to_db(self, items: List[Dict]):
        """Differential sync logic"""
        pass
    
    async def run(self) -> Dict[str, int]:
        """Main execution: fetch → normalize → sync"""
        raw_data = await self.fetch_data()
        normalized = [self.normalize_item(item) for item in raw_data]
        stats = await self.sync_to_db(normalized)
        return stats
```

### 4.2 Differential Sync Algorithm

```python
async def sync_to_db(self, fetched_items: List[Dict]):
    """
    Smart sync that detects:
    - NEW: in fetched, not in DB → INSERT
    - UPDATED: in both, different hash → UPDATE
    - UNCHANGED: in both, same hash → SKIP
    - DELETED: in DB, not in fetched → DELETE
    """
    
    # 1. Build lookup of fetched items by external_id
    fetched_map = {item['external_id']: item for item in fetched_items}
    
    # 2. Fetch existing items from DB for this source
    existing = await self.db.get_by_source(self.source_name)
    existing_map = {row['external_id']: row for row in existing}
    
    stats = {'inserted': 0, 'updated': 0, 'deleted': 0, 'unchanged': 0}
    
    # 3. Process fetched items
    for ext_id, item in fetched_map.items():
        if ext_id not in existing_map:
            # NEW → INSERT
            await self.db.insert(item)
            stats['inserted'] += 1
        else:
            existing_item = existing_map[ext_id]
            if item['content_hash'] != existing_item['content_hash']:
                # CHANGED → UPDATE
                await self.db.update(ext_id, item)
                stats['updated'] += 1
            else:
                # UNCHANGED → SKIP
                stats['unchanged'] += 1
    
    # 4. Find deleted items (in DB but not in fetched)
    deleted_ids = set(existing_map.keys()) - set(fetched_map.keys())
    for ext_id in deleted_ids:
        await self.db.delete(ext_id)
        stats['deleted'] += 1
    
    return stats
```

### 4.3 Scraper Implementations

**1. OWASP Scraper (`owasp_scraper.py`):**
- **Sources:** OWASP Top 10, ASVS, CheatSheet Series
- **Method:** HTTP requests + BeautifulSoup parsing
- **external_id:** `owasp_{category}_{year}` (e.g., `owasp_A01_2021`)
- **Rate Limiting:** Respectful delays between requests
- **Challenges:** Multiple document formats, version tracking

**2. MITRE ATT&CK Scraper (`mitre_attack_scraper.py`):**
- **Source:** MITRE ATT&CK STIX API (official JSON endpoint)
- **Method:** REST API calls (structured data)
- **external_id:** Technique ID (e.g., `T1059.001`)
- **Rate Limiting:** API has no strict limits, but polite delays
- **Challenges:** Nested sub-techniques, tactic mapping

**3. GitHub Scraper (`github_scraper.py`):**
- **Sources:**
  - Curated repos: PayloadsAllTheThings, SecLists, Exploit-DB
  - CVE-linked: GitHub search API for CVE references
- **Method:** GitHub REST API + git clone for file contents
- **external_id:** `github_{owner}_{repo}_{file_path_hash}`
- **Rate Limiting:** GitHub API (5000 requests/hour with token)
- **Challenges:** Large repos, binary files, rate limits

**4. Kali Docs Scraper (`kali_docs_scraper.py`):**
- **Sources:**
  - tools.kali.org (official tool listings)
  - Man pages (scraped or API)
  - GitHub repos (official tool repositories)
  - Community: HackTricks, GTFOBins, LOLBAS
- **Method:** Multi-source aggregation with deduplication
- **external_id:** `kali_{tool_name}_{source_hash}`
- **Rate Limiting:** Per-source rate limits
- **Challenges:** Inconsistent formats, duplicate tools across sources

### 4.4 Progress Tracking

Scrapers emit progress via Celery task state:

```python
from celery import current_task

current_task.update_state(
    state='PROGRESS',
    meta={
        'current': 50,
        'total': 200,
        'status': 'Fetching MITRE techniques...',
        'stats': {
            'inserted': 5,
            'updated': 3,
            'deleted': 0
        }
    }
)
```

Frontend receives updates via WebSocket in real-time.

---

## 5. API Design

### 5.1 REST API Endpoints

**Sources:**
```
GET    /api/sources                    # List all sources with stats
GET    /api/sources/{id}               # Source detail + last scrape info
POST   /api/sources/{id}/scrape        # Trigger manual scrape
DELETE /api/sources/{id}/sessions/{session_id}  # Cancel running scrape
```

**Data:**
```
GET    /api/data                       # List scraped data (paginated, filterable)
        Query params: ?page=1&per_page=50&source=mitre_attack
                     &content_type=technique&search=privilege+escalation
                     &tags=windows&sort_by=last_updated_at&order=desc
GET    /api/data/{id}                  # Single item detail
DELETE /api/data/{id}                  # Delete item
POST   /api/data/{id}/rescrape         # Re-scrape single item's source
```

**Sessions:**
```
GET    /api/sessions                   # Scrape history (paginated)
GET    /api/sessions/{id}              # Session detail with stats
```

**Analytics:**
```
GET    /api/analytics/overview         # Dashboard stats
        Response: {total_items, sources_count, last_scrape, active_sessions}
GET    /api/analytics/coverage         # Coverage per source
        Response: [{source, count, last_scraped, percentage}]
GET    /api/analytics/trends           # Scraping trends over time
        Response: [{date, scrapes, items_added}]
```

**Export:**
```
POST   /api/export/opensearch          # Manual export to JSONL
        Body: {session_id?, source_id?, format: 'jsonl'|'json'}
        Response: {file_path, items_exported, format}
GET    /api/export/logs                # Export history
```

**WebSocket:**
```
WS     /ws/scrape-progress             # Real-time scrape updates
        Message format: {
            type: 'progress' | 'completed' | 'failed',
            session_id: 123,
            data: {current, total, status, stats}
        }
```

### 5.2 Response Schemas

**Source Schema:**
```json
{
  "id": 1,
  "name": "mitre_attack",
  "display_name": "MITRE ATT&CK",
  "url": "https://attack.mitre.org",
  "enabled": true,
  "last_scraped_at": "2026-09-01T12:00:00Z",
  "scrape_count": 15,
  "stats": {
    "total_items": 1234,
    "last_session_status": "completed"
  }
}
```

**Scraped Data Schema:**
```json
{
  "id": 456,
  "source": "mitre_attack",
  "external_id": "T1059.001",
  "content_type": "technique",
  "title": "PowerShell",
  "description": "Adversaries may abuse PowerShell...",
  "tags": ["execution", "windows", "scripting"],
  "severity": null,
  "url": "https://attack.mitre.org/techniques/T1059/001/",
  "first_seen_at": "2026-08-01T10:00:00Z",
  "last_updated_at": "2026-09-01T12:00:00Z"
}
```

**Session Schema:**
```json
{
  "id": 789,
  "source": {
    "id": 1,
    "name": "mitre_attack",
    "display_name": "MITRE ATT&CK"
  },
  "status": "completed",
  "started_at": "2026-09-01T12:00:00Z",
  "completed_at": "2026-09-01T12:05:34Z",
  "duration_seconds": 334,
  "stats": {
    "items_found": 250,
    "inserted": 12,
    "updated": 5,
    "deleted": 2,
    "unchanged": 231
  },
  "triggered_by": "manual"
}
```

---

## 6. Export Service

### 6.1 OpenSearch JSONL Export

Export scraped data to OpenSearch bulk import format:

```python
# backend/services/export_service.py

class ExportService:
    """Export scraped data to OpenSearch-compatible format"""
    
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
        
        return str(filepath)
```

### 6.2 Document Format

Each document exported contains:

```json
{
  "id": "mitre_attack_T1059.001",
  "source": "mitre_attack",
  "external_id": "T1059.001",
  "title": "PowerShell",
  "description": "Adversaries may abuse PowerShell commands...",
  "content": "# PowerShell\n\n**Tactic:** Execution...",
  "content_type": "technique",
  "tags": ["execution", "windows", "scripting"],
  "url": "https://attack.mitre.org/techniques/T1059/001/",
  "scraped_at": "2026-09-01T12:00:00Z",
  "metadata": {
    "tactic": "Execution",
    "technique_id": "T1059",
    "sub_technique": "001",
    "platforms": ["Windows"]
  }
}
```

**Content field formatting** for optimal RAG retrieval:
- Structured markdown with headers
- Source-specific context (tactic, CWE, tool usage, etc.)
- Code blocks for payloads
- Tags appended for keyword search

### 6.3 OpenSearch Import Command

After export, import to OpenSearch:

```bash
# Using curl
curl -X POST "localhost:9200/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @exports/opensearch_export_20260901_120000.jsonl

# Or using OpenSearch Python client
from opensearchpy import OpenSearch
client = OpenSearch([{'host': 'localhost', 'port': 9200}])
with open('exports/opensearch_export_20260901_120000.jsonl') as f:
    client.bulk(body=f.read())
```

---

## 7. Frontend Design

### 7.1 Pages & Components

**1. Dashboard (Home)**
- Stats cards: total items, sources count, last scrape time
- Quick action buttons: Scrape All, View Data, Analytics
- Source cards with individual scrape buttons and status indicators
- Real-time progress for running scrapes (progress bar, current status)

**2. Data Browser (Search & Filter)**
- Filter dropdowns: Source, Content Type
- Tag filter (autocomplete)
- Full-text search box
- Results table (paginated): title, source, type, last updated, actions
- Item detail modal: full content, metadata, tags, URL, timestamps
- Bulk actions: delete selected

**3. Analytics Dashboard**
- Coverage by source (bar chart)
- Data freshness (pie chart: fresh <7d, stale >30d, very stale >60d)
- Scraping activity timeline (line chart: scrapes per day, last 30 days)
- Content type distribution (bar chart)
- Stats summary cards

**4. Session History**
- Scrape sessions list (newest first)
- Per session: source, timestamp, duration, status (success/failed/partial)
- Stats: items found, inserted, updated, deleted
- Error messages for failed sessions
- Retry button for failed scrapes

### 7.2 Real-Time Progress (WebSocket)

When scrape triggered, UI shows:

```
┌─────────────────────────────────────┐
│ Scraping MITRE ATT&CK...            │
│ ████████████░░░░░░░░ 65%            │
│ Processing technique T1548...       │
│ Found: 234 | New: 8 | Updated: 12  │
└─────────────────────────────────────┘
```

WebSocket message:
```json
{
  "type": "progress",
  "session_id": 123,
  "data": {
    "current": 234,
    "total": 360,
    "percentage": 65,
    "status": "Processing technique T1548...",
    "stats": {
      "inserted": 8,
      "updated": 12,
      "deleted": 0
    }
  }
}
```

---

## 8. Error Handling & Resilience

### 8.1 Error Categories

```python
ERROR_CATEGORIES = {
    'network': ['ConnectionError', 'Timeout', 'DNSError'],
    'auth': ['Unauthorized', 'Forbidden', 'APIKeyInvalid'],
    'rate_limit': ['RateLimitError', 'TooManyRequests'],
    'parsing': ['ParseError', 'InvalidJSON', 'SchemaValidationError'],
    'data': ['EmptyResponse', 'MalformedData']
}
```

### 8.2 Retry Strategy

```python
RETRY_CONFIG = {
    'max_retries': 3,
    'backoff_factor': 2,  # 2s, 4s, 8s
    'retryable_errors': [
        'ConnectionError',
        'Timeout',
        'RateLimitError',
        'HTTPError_5xx'
    ]
}
```

### 8.3 Failure Scenarios

1. **Network failures** → Retry with exponential backoff, log error after max retries
2. **Rate limiting** (GitHub) → Respect `X-RateLimit-*` headers, queue for later, notify user
3. **Source structure changed** → Log parse error with context, skip item, continue with others
4. **Partial scrape failure** → Save successfully scraped items, mark session as 'partial', log errors
5. **Database connection lost** → Celery auto-retry task (max 3), preserve fetched data in memory

### 8.4 Celery Task Configuration

```python
@celery.task(
    bind=True,
    max_retries=3,
    soft_time_limit=1800,  # 30 min
    time_limit=2000,
    autoretry_for=(ConnectionError, Timeout),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def scrape_task(self, source_id: int, session_id: int):
    try:
        scraper = get_scraper(source_id)
        stats = await scraper.run()
        
        # Auto-export on success
        await export_to_opensearch(session_id)
        
        return stats
    except Exception as e:
        await db.update_session_error(session_id, str(e))
        raise
```

### 8.5 Logging & Monitoring

Structured logs for debugging:

```json
{
  "timestamp": "2026-09-01T16:00:00Z",
  "session_id": 123,
  "source": "mitre_attack",
  "level": "ERROR",
  "error_type": "ParseError",
  "message": "Failed to parse technique T1234",
  "context": {
    "url": "https://attack.mitre.org/...",
    "raw_data_sample": "...",
    "traceback": "..."
  }
}
```

---

## 9. Deployment

### 9.1 Project Structure

```
scrape/
├── backend/
│   ├── main.py                    # FastAPI entry
│   ├── config.py                  # Environment config
│   ├── database.py                # PostgreSQL connection
│   ├── celery_app.py              # Celery setup
│   ├── models/                    # SQLAlchemy models
│   ├── api/                       # API routes
│   ├── scrapers/                  # Scraper modules
│   ├── services/                  # Business logic
│   ├── tasks/                     # Celery tasks
│   ├── schemas/                   # Pydantic schemas
│   ├── utils/                     # Helpers
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── styles/
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   └── nginx.conf
├── exports/                       # OpenSearch exports
├── logs/
├── alembic/                       # DB migrations
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── Makefile
└── README.md
```

### 9.2 Docker Compose

**Services:**
- `postgres` - PostgreSQL 15 database
- `redis` - Redis 7 for Celery broker/backend
- `backend` - FastAPI application (4 workers)
- `celery_worker` - Celery worker (4 concurrency)
- `celery_beat` - Celery scheduler (future scheduled scrapes)
- `frontend` - React app served via Nginx

### 9.3 Environment Configuration

Key environment variables (see `.env.example` for full list):

```bash
# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/cybersec_scraper

# Redis
REDIS_URL=redis://redis:6379/0

# API Keys
GITHUB_TOKEN=ghp_xxxxx

# Export
EXPORT_DIR=/app/exports
EXPORT_FORMAT=jsonl
OPENSEARCH_INDEX_NAME=cybersec_knowledge

# Celery
CELERY_WORKER_CONCURRENCY=4
```

### 9.4 Installation Steps

```bash
# 1. Clone & setup
git clone <repo>
cd scrape

# 2. Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# 3. Start services
docker-compose up -d

# 4. Run migrations
docker-compose exec backend alembic upgrade head

# 5. Seed initial sources
docker-compose exec backend python -m scripts.seed_sources

# 6. Access
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

### 9.5 Server Requirements

**Recommended for Phase A (Personal Use):**
```
CPU: 4 cores
RAM: 8 GB
Disk: 50 GB SSD
OS: Ubuntu 22.04 LTS or Debian 11+
Docker: 20.10+ with Docker Compose v2
```

**Estimated Resource Usage:**
```
PostgreSQL:   ~512 MB RAM, ~2-5 GB disk (grows with data)
Redis:        ~128 MB RAM
FastAPI:      ~256 MB RAM per worker (4 workers = 1 GB)
Celery:       ~512 MB RAM per worker (4 workers = 2 GB)
Frontend:     ~100 MB RAM (Nginx)
Total:        ~4 GB RAM, ~10 GB disk (data grows to ~1-3 GB)
```

**Data Size Estimates:**
- OWASP: ~50 MB
- MITRE ATT&CK: ~200 MB
- GitHub Payloads: ~500 MB - 2 GB
- Kali Docs: ~100 MB
- Total: ~1-3 GB scraped data

---

## 10. Testing Strategy

### 10.1 Test Coverage

```
backend/tests/
├── unit/
│   ├── test_scrapers.py            # Scraper logic, differential sync
│   ├── test_hash_utils.py          # Hash generation
│   └── test_export_service.py      # JSONL format validation
├── integration/
│   ├── test_api_endpoints.py       # REST API tests
│   ├── test_scraper_flow.py        # End-to-end scraping
│   └── test_websocket.py           # Real-time updates
└── fixtures/
    ├── sample_owasp.json
    ├── sample_mitre.json
    └── sample_github.json
```

### 10.2 Key Test Scenarios

1. **Differential Sync:**
   - New items → INSERT
   - Changed items → UPDATE
   - Unchanged items → SKIP
   - Deleted items → DELETE
   - Idempotency (run twice = same result)

2. **Scraper Parsing:**
   - Valid data → success
   - Malformed data → graceful error
   - Empty response → handle correctly
   - Large datasets → pagination

3. **API Endpoints:**
   - CRUD operations
   - Filtering & search
   - Pagination
   - Error responses (404, 400, 500)

4. **Export Format:**
   - Valid JSONL structure
   - OpenSearch bulk import compatibility
   - UTF-8 encoding
   - Special characters handling

5. **Error Handling:**
   - Network timeout → retry
   - Rate limit → queue
   - Parse error → skip item, continue
   - Database error → rollback transaction

---

## 11. Documentation

### 11.1 Documentation Structure

```
docs/
├── 01-getting-started.md          # Installation, configuration, first run
├── 02-architecture.md             # System overview, components, data flow
├── 03-scrapers.md                 # Scraper details, adding new scrapers
├── 04-api-reference.md            # Endpoints, schemas, examples
├── 05-export-to-opensearch.md     # Export formats, import to OpenSearch
├── 06-deployment.md               # Server setup, Docker, SSL, monitoring
├── 07-development.md              # Local dev setup, code structure, testing
└── 08-troubleshooting.md          # Common issues, logs, debug mode
```

### 11.2 README.md Highlights

```markdown
# Cybersecurity Data Scraper

Automated scraping platform for cybersecurity intelligence (OWASP, MITRE ATT&CK, 
GitHub payloads, Kali tools). Export to OpenSearch for RAG systems.

## Features
- Multi-source scraping with differential sync
- Web UI for manual control & monitoring
- Analytics dashboard
- OpenSearch JSONL export

## Quick Start
docker-compose up -d
# Access: http://localhost:3000

## Tech Stack
Python 3.11 • FastAPI • React 18 • PostgreSQL 15 • Celery • Redis
```

---

## 12. Future Enhancements (Phase C)

**Out of scope for Phase A, planned for Phase C:**

1. **Authentication & Authorization:**
   - User registration/login
   - Role-based access control
   - API keys for programmatic access

2. **Scheduled Scraping:**
   - Cron-like scheduling per source
   - Auto-scrape on data staleness threshold

3. **Advanced Features:**
   - Custom scraper plugins (user-defined sources)
   - Webhook notifications (Discord, Slack)
   - Data deduplication across sources
   - Machine learning for data classification

4. **RAG Integration:**
   - Direct OpenSearch push (not just file export)
   - LangChain integration module
   - BGE reranker integration
   - MCP adapter for Hermes Agent

5. **Scalability:**
   - Horizontal scaling (multiple workers)
   - Load balancer
   - CDN for frontend
   - Metrics & monitoring (Prometheus, Grafana)

---

## 13. Success Criteria

**Phase A (Personal Use) is successful when:**

1. ✅ All 4 data sources scrape successfully (OWASP, MITRE, GitHub, Kali)
2. ✅ Differential sync correctly identifies INSERT/UPDATE/DELETE/UNCHANGED
3. ✅ Web UI allows manual triggers and shows real-time progress
4. ✅ Search & filter works across all scraped data
5. ✅ Analytics dashboard shows accurate coverage and trends
6. ✅ Export generates valid OpenSearch JSONL files
7. ✅ System runs stable on server for 30+ days
8. ✅ Documentation is clear enough for deployment without support

**Acceptance Tests:**
- Scrape all sources → verify 1000+ items collected
- Re-scrape same source → verify UNCHANGED dominates, minimal DB writes
- Delete item from source → verify DELETE on next scrape
- Export data → import to OpenSearch → verify searchable
- Trigger 4 concurrent scrapes → verify no deadlocks

---

## 14. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GitHub rate limiting | High | High | Use authenticated API, respect limits, queue excess requests |
| Source structure changes | Medium | Medium | Robust parsing with fallbacks, error notifications |
| Large GitHub repos (>1GB) | High | Low | Skip binary files, limit clone depth, stream processing |
| Celery task failures | Medium | Medium | Retry logic, dead letter queue, monitoring |
| Database growth (>10GB) | Low | Medium | Partition old data, archival strategy (Phase C) |
| Server resource exhaustion | High | Low | Resource limits per container, monitoring, alerts |

---

## Appendix A: Technology Rationale

**Why FastAPI over Flask/Django?**
- Async native (critical for I/O-bound scraping)
- Auto-generated API docs (OpenAPI/Swagger)
- Fast development with Pydantic validation
- Modern Python 3.11 features

**Why PostgreSQL over MongoDB?**
- JSONB gives flexibility like MongoDB but with ACID guarantees
- GIN indexes for fast JSON queries
- Better for structured queries (analytics)
- Mature, battle-tested

**Why Celery over alternatives (RQ, Dramatiq)?**
- Industry standard, proven at scale
- Rich monitoring tools (Flower)
- Retry logic, chaining, scheduling built-in
- Large ecosystem

**Why React over Vue/Svelte?**
- Larger ecosystem, more libraries (Recharts, etc.)
- Better TypeScript support
- Familiarity for most developers
- Component reusability

---

## Appendix B: Data Source Details

### OWASP
- **URLs:** owasp.org/www-project-top-ten, cheatsheetseries.owasp.org
- **Update Frequency:** Irregular (major updates yearly)
- **Format:** HTML, Markdown
- **Estimated Items:** ~500 vulnerabilities, 100+ cheat sheets

### MITRE ATT&CK
- **URL:** attack.mitre.org/resources/attack-data-and-tools
- **API:** STIX 2.0 JSON (official)
- **Update Frequency:** Quarterly
- **Format:** Structured JSON
- **Estimated Items:** ~600 techniques + sub-techniques

### GitHub Payloads
- **Curated Repos:**
  - swisskyrepo/PayloadsAllTheThings (~50k stars)
  - danielmiessler/SecLists (~50k stars)
  - offensive-security/exploitdb (~10k stars)
- **CVE Search:** GitHub API search for `CVE-` mentions
- **Update Frequency:** Daily (community contributions)
- **Estimated Items:** 5,000 - 20,000 payloads

### Kali Linux Tools
- **Sources:**
  - tools.kali.org (official listing, ~300 tools)
  - Man pages (via man-db or APIs)
  - GitHub (official tool repos)
  - HackTricks.xyz (usage examples)
  - GTFOBins.github.io (living-off-the-land binaries)
- **Update Frequency:** Per distro release (quarterly) + tool updates
- **Estimated Items:** ~400 tools with documentation

---

**End of Design Specification**
