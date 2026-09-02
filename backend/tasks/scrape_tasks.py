import os
import asyncio
import logging
from celery import Task
from celery_app import celery_app
import asyncpg

from scrapers.owasp_scraper import OWASPScraper
from scrapers.mitre_attack_scraper import MITREAttackScraper
from scrapers.github_scraper import GitHubScraper
from scrapers.kali_docs_scraper import KaliDocsScraper

logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "owasp": OWASPScraper,
    "mitre_attack": MITREAttackScraper,
    "github_payloads": GitHubScraper,
    "kali_docs": KaliDocsScraper,
}

def get_db_url():
    url = os.getenv("DATABASE_URL", "postgresql://scraper_user:password@postgres:5432/cybersec_scraper")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url

@celery_app.task(bind=True, max_retries=2, soft_time_limit=1800, time_limit=2000)
def scrape_source_task(self, source_id: int, session_id: int):
    """Sync Celery task wrapper for async scraper."""
    async def _run():
        db_url = get_db_url()
        # Get source name
        conn = await asyncpg.connect(db_url)
        try:
            row = await conn.fetchrow("SELECT name, display_name FROM sources WHERE id=$1", source_id)
            if not row:
                raise ValueError(f"Source {source_id} not found")
            source_name = row["name"]
            logger.info(f"Starting scrape {source_name} session {session_id}")
            # Update session to running
            await conn.execute("UPDATE scrape_sessions SET status='running', task_id=$1 WHERE id=$2", self.request.id, session_id)
            # Choose scraper
            scraper_cls = SCRAPER_MAP.get(source_name)
            if not scraper_cls:
                raise ValueError(f"No scraper for {source_name}")
            # Need DB url for scraper (asyncpg DSN)
            async_db_url = os.getenv("DATABASE_URL", "postgresql://scraper_user:password@postgres:5432/cybersec_scraper")
            if async_db_url.startswith("postgresql://"):
                async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://", 1) if "asyncpg" not in async_db_url else async_db_url
            # Actually BaseScraper expects asyncpg DSN with postgresql:// (it uses asyncpg.connect)
            # Use raw postgresql:// for asyncpg
            raw_url = os.getenv("DATABASE_URL", "postgresql://scraper_user:password@postgres:5432/cybersec_scraper")
            if raw_url.startswith("postgresql+asyncpg://"):
                raw_url = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
            scraper = scraper_cls(raw_url)
            stats = await scraper.run()
            # Update session completed
            await conn.execute("""
                UPDATE scrape_sessions SET status='completed', completed_at=NOW(),
                items_found=$1, items_inserted=$2, items_updated=$3, items_deleted=$4
                WHERE id=$5
            """, sum(stats.values()), stats["inserted"], stats["updated"], stats["deleted"], session_id)
            await conn.execute("UPDATE sources SET last_scraped_at=NOW(), scrape_count = scrape_count + 1 WHERE id=$1", source_id)
            logger.info(f"Completed {source_name}: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Scrape failed: {e}", exc_info=True)
            try:
                await conn.execute("UPDATE scrape_sessions SET status='failed', completed_at=NOW(), error_message=$1 WHERE id=$2", str(e), session_id)
            except:
                pass
            raise
        finally:
            await conn.close()

    # Run async
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()
