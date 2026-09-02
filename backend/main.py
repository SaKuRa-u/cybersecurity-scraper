import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncpg

from config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
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
    allow_origins=settings.cors_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to get DB connection
async def get_conn():
    # Convert DATABASE_URL to asyncpg DSN
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return await asyncpg.connect(url)

@app.get("/health")
async def health_check():
    health = {"status": "healthy", "database": "unknown", "redis": "unknown"}
    # DB check
    try:
        conn = await get_conn()
        await conn.execute("SELECT 1")
        await conn.close()
        health["database"] = "connected"
    except Exception as e:
        logger.error(f"DB health failed: {e}")
        health["database"] = "disconnected"
        health["status"] = "unhealthy"
    # Redis check (optional)
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health["redis"] = "connected"
    except Exception as e:
        logger.warning(f"Redis health failed: {e}")
        health["redis"] = "disconnected"
    return health

@app.get("/api/sources")
async def list_sources():
    try:
        conn = await get_conn()
        rows = await conn.fetch("""
            SELECT s.*, 
                   (SELECT COUNT(*) FROM scraped_data WHERE source_id = s.id AND COALESCE(is_deleted, false) = false) as total_items,
                   (SELECT status FROM scrape_sessions WHERE source_id = s.id ORDER BY started_at DESC LIMIT 1) as last_session_status
            FROM sources s ORDER BY s.id
        """)
        await conn.close()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "name": r["name"],
                "display_name": r["display_name"],
                "url": r["url"],
                "enabled": r["enabled"],
                "scraper_module": r["scraper_module"],
                "last_scraped_at": r["last_scraped_at"].isoformat() if r["last_scraped_at"] else None,
                "scrape_count": r["scrape_count"] or 0,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "total_items": r["total_items"] or 0,
                "last_session_status": r["last_session_status"]
            })
        return result
    except Exception as e:
        logger.error(f"list_sources failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/sources/{source_id}")
async def get_source(source_id: int):
    try:
        conn = await get_conn()
        row = await conn.fetchrow("SELECT * FROM sources WHERE id = $1", source_id)
        if not row:
            await conn.close()
            return JSONResponse(status_code=404, content={"detail": "Source not found"})
        total = await conn.fetchval("SELECT COUNT(*) FROM scraped_data WHERE source_id = $1 AND COALESCE(is_deleted, false) = false", source_id)
        last_status = await conn.fetchval("SELECT status FROM scrape_sessions WHERE source_id = $1 ORDER BY started_at DESC LIMIT 1", source_id)
        await conn.close()
        return {
            "id": row["id"],
            "name": row["name"],
            "display_name": row["display_name"],
            "url": row["url"],
            "enabled": row["enabled"],
            "scraper_module": row["scraper_module"],
            "last_scraped_at": row["last_scraped_at"].isoformat() if row["last_scraped_at"] else None,
            "scrape_count": row["scrape_count"] or 0,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "total_items": total or 0,
            "last_session_status": last_status
        }
    except Exception as e:
        logger.error(f"get_source failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/sources/{source_id}/scrape")
async def trigger_scrape(source_id: int):
    try:
        conn = await get_conn()
        row = await conn.fetchrow("SELECT * FROM sources WHERE id = $1", source_id)
        if not row:
            await conn.close()
            return JSONResponse(status_code=404, content={"detail": "Source not found"})
        # Create a pending session
        session_id = await conn.fetchval("""
            INSERT INTO scrape_sessions (source_id, status, triggered_by)
            VALUES ($1, 'pending', 'manual') RETURNING id
        """, source_id)
        await conn.close()
        # Try to enqueue Celery task
        try:
            from tasks.scrape_tasks import scrape_source_task
            task = scrape_source_task.delay(source_id, session_id)
            task_id = task.id
            logger.info(f"Enqueued scrape for {row['display_name']} session {session_id} task {task_id}")
        except Exception as ce:
            logger.warning(f"Celery enqueue failed, fallback to mock: {ce}")
            task_id = f"mock-{session_id}"
        return {
            "session_id": session_id,
            "task_id": task_id,
            "status": "pending",
            "message": f"Scrape queued for {row['display_name']}"
        }
    except Exception as e:
        logger.error(f"trigger_scrape failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/data")
async def list_data(page: int = 1, per_page: int = 50, source: str = None, content_type: str = None, search: str = None, tags: str = None, sort_by: str = "last_updated_at", order: str = "desc"):
    try:
        conn = await get_conn()
        # Build where clause
        where = ["COALESCE(is_deleted, false) = false"]
        params = []
        idx = 1
        if source:
            # need source_id
            sid = await conn.fetchval("SELECT id FROM sources WHERE name = $1", source)
            if sid:
                where.append(f"source_id = ${idx}")
                params.append(sid)
                idx += 1
            else:
                await conn.close()
                return {"items": [], "total": 0, "page": page, "per_page": per_page, "pages": 0}
        if content_type:
            where.append(f"content_type = ${idx}")
            params.append(content_type)
            idx += 1
        if search:
            where.append(f"(title ILIKE ${idx} OR description ILIKE ${idx} OR external_id ILIKE ${idx})")
            params.append(f"%{search}%")
            idx += 1
        # Note: tags filter simplified
        where_sql = " AND ".join(where)
        # Count
        count_query = f"SELECT COUNT(*) FROM scraped_data WHERE {where_sql}"
        total = await conn.fetchval(count_query, *params) if params else await conn.fetchval(count_query)
        # Sort
        allowed_sort = {"title": "title", "last_updated_at": "last_updated_at", "first_seen_at": "first_seen_at"}
        sort_col = allowed_sort.get(sort_by, "last_updated_at")
        order_sql = "DESC" if order == "desc" else "ASC"
        offset = (page - 1) * per_page
        query = f"SELECT * FROM scraped_data WHERE {where_sql} ORDER BY {sort_col} {order_sql} LIMIT ${idx} OFFSET ${idx+1}"
        params_with_page = params + [per_page, offset]
        rows = await conn.fetch(query, *params_with_page) if where else await conn.fetch(f"SELECT * FROM scraped_data WHERE {where_sql} ORDER BY {sort_col} {order_sql} LIMIT $1 OFFSET $2", per_page, offset)
        # Need source names
        items = []
        for r in rows:
            sname = await conn.fetchval("SELECT name FROM sources WHERE id = $1", r["source_id"])
            items.append({
                "id": r["id"],
                "source": sname,
                "external_id": r["external_id"],
                "content_type": r["content_type"],
                "title": r["title"],
                "description": r["description"],
                "content": r["content"],
                "tags": r["tags"] or [],
                "severity": r["severity"],
                "url": r["url"],
                "first_seen_at": r["first_seen_at"].isoformat() if r["first_seen_at"] else None,
                "last_updated_at": r["last_updated_at"].isoformat() if r["last_updated_at"] else None
            })
        await conn.close()
        pages = (total + per_page - 1) // per_page if per_page else 0
        return {"items": items, "total": total or 0, "page": page, "per_page": per_page, "pages": pages}
    except Exception as e:
        logger.error(f"list_data failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/sessions")
async def list_sessions(limit: int = 50):
    try:
        conn = await get_conn()
        rows = await conn.fetch("""
            SELECT ss.*, s.name as source_name, s.display_name as source_display_name
            FROM scrape_sessions ss
            JOIN sources s ON s.id = ss.source_id
            ORDER BY ss.started_at DESC LIMIT $1
        """, limit)
        await conn.close()
        result = []
        for r in rows:
            duration = None
            if r["completed_at"] and r["started_at"]:
                duration = int((r["completed_at"] - r["started_at"]).total_seconds())
            result.append({
                "id": r["id"],
                "source_id": r["source_id"],
                "source_name": r["source_name"],
                "source_display_name": r["source_display_name"],
                "task_id": r["task_id"],
                "status": r["status"],
                "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                "duration_seconds": duration,
                "items_found": r["items_found"] or 0,
                "items_inserted": r["items_inserted"] or 0,
                "items_updated": r["items_updated"] or 0,
                "items_deleted": r["items_deleted"] or 0,
                "error_message": r["error_message"],
                "triggered_by": r["triggered_by"]
            })
        return result
    except Exception as e:
        logger.error(f"list_sessions failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/analytics/overview")
async def analytics_overview():
    try:
        conn = await get_conn()
        total = await conn.fetchval("SELECT COUNT(*) FROM scraped_data WHERE COALESCE(is_deleted, false) = false") or 0
        sources_count = await conn.fetchval("SELECT COUNT(*) FROM sources") or 0
        last_scrape = await conn.fetchval("SELECT MAX(last_scraped_at) FROM sources")
        active = await conn.fetchval("SELECT COUNT(*) FROM scrape_sessions WHERE status IN ('pending','running')") or 0
        await conn.close()
        return {
            "total_items": total,
            "sources_count": sources_count,
            "last_scrape": last_scrape.isoformat() if last_scrape else None,
            "active_sessions": active
        }
    except Exception as e:
        logger.error(f"analytics_overview failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/analytics/coverage")
async def analytics_coverage():
    try:
        conn = await get_conn()
        rows = await conn.fetch("SELECT id, name, display_name, last_scraped_at FROM sources")
        total = await conn.fetchval("SELECT COUNT(*) FROM scraped_data WHERE COALESCE(is_deleted, false) = false") or 0
        await conn.close() if False else None
        result = []
        # need per source count - reopen? we closed? fix
        conn2 = await get_conn()
        for r in rows:
            count = await conn2.fetchval("SELECT COUNT(*) FROM scraped_data WHERE source_id = $1 AND COALESCE(is_deleted, false) = false", r["id"]) or 0
            perc = (count / total * 100) if total else 0
            result.append({
                "source": r["name"],
                "display_name": r["display_name"],
                "count": count,
                "last_scraped": r["last_scraped_at"].isoformat() if r["last_scraped_at"] else None,
                "percentage": round(perc, 2)
            })
        await conn2.close()
        return result
    except Exception as e:
        logger.error(f"analytics_coverage failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/analytics/trends")
async def analytics_trends():
    try:
        conn = await get_conn()
        rows = await conn.fetch("""
            SELECT DATE(started_at) as d, COUNT(*) as scrapes, COALESCE(SUM(items_inserted),0) as items_added
            FROM scrape_sessions
            WHERE started_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(started_at)
            ORDER BY d ASC
        """)
        await conn.close()
        return [{"date": r["d"].isoformat(), "scrapes": r["scrapes"], "items_added": r["items_added"]} for r in rows]
    except Exception as e:
        logger.error(f"analytics_trends failed: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/export/opensearch")
async def export_opensearch(source_id: int = None, format: str = "jsonl"):
    try:
        import json, pathlib, datetime
        conn = await get_conn()
        if source_id:
            rows = await conn.fetch("SELECT * FROM scraped_data WHERE source_id = $1 AND COALESCE(is_deleted, false) = false", source_id)
        else:
            rows = await conn.fetch("SELECT * FROM scraped_data WHERE COALESCE(is_deleted, false) = false")
        await conn.close()
        # Build export dir
        export_dir = pathlib.Path(settings.EXPORT_DIR)
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"opensearch_export_{timestamp}.jsonl" if format == "jsonl" else f"export_{timestamp}.json"
        filepath = export_dir / filename
        # Need source names
        conn2 = await get_conn()
        with open(filepath, 'w', encoding='utf-8') as f:
            for r in rows:
                sname = await conn2.fetchval("SELECT name FROM sources WHERE id = $1", r["source_id"])
                doc = {
                    "id": f"{sname}_{r['external_id']}",
                    "source": sname,
                    "external_id": r["external_id"],
                    "title": r["title"],
                    "description": r["description"],
                    "content_type": r["content_type"],
                    "tags": r["tags"] or [],
                    "url": r["url"],
                    "scraped_at": r["last_updated_at"].isoformat() if r["last_updated_at"] else None,
                    "metadata": r["content"]
                }
                if format == "jsonl":
                    meta = {"index": {"_index": settings.OPENSEARCH_INDEX_NAME, "_id": doc["id"]}}
                    f.write(json.dumps(meta) + "\n")
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                else:
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        await conn2.close()
        return {"file_path": str(filepath), "items_exported": len(rows), "format": format}
    except Exception as e:
        logger.error(f"export failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.on_event("startup")
async def startup():
    logger.info("API starting up...")
    # Fix legacy rows where is_deleted is NULL
    try:
        conn = await get_conn()
        await conn.execute("UPDATE scraped_data SET is_deleted = false WHERE is_deleted IS NULL")
        await conn.close()
        logger.info("Fixed NULL is_deleted rows")
    except Exception as e:
        logger.warning(f"Startup fix failed: {e}")

@app.on_event("shutdown")
async def shutdown():
    logger.info("API shutting down...")
