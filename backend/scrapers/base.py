from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import asyncpg
import logging
from datetime import datetime
from utils.hash_utils import compute_content_hash

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self, db_url: str):
        self.db_url = db_url

    @abstractmethod
    def get_source_name(self) -> str:
        pass

    @abstractmethod
    async def fetch_data(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        pass

    def compute_hash(self, content: Dict) -> str:
        return compute_content_hash(content)

    async def get_source_id(self, conn) -> int:
        name = self.get_source_name()
        sid = await conn.fetchval("SELECT id FROM sources WHERE name = $1", name)
        if not sid:
            raise ValueError(f"Source not found: {name}")
        return sid

    async def sync_to_db(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Differential sync: INSERT/UPDATE/DELETE."""
        import json
        conn = await asyncpg.connect(self.db_url)
        try:
            source_id = await self.get_source_id(conn)
            # Build maps
            fetched_map = {}
            for item in items:
                item["content_hash"] = self.compute_hash(item["content"])
                item["source_id"] = source_id
                fetched_map[item["external_id"]] = item

            existing_rows = await conn.fetch("SELECT id, external_id, content_hash FROM scraped_data WHERE source_id = $1 AND (is_deleted = false OR is_deleted IS NULL)", source_id)
            existing_map = {r["external_id"]: dict(r) for r in existing_rows}

            stats = {"inserted": 0, "updated": 0, "deleted": 0, "unchanged": 0}

            for ext_id, item in fetched_map.items():
                if ext_id not in existing_map:
                    await conn.execute("""
                        INSERT INTO scraped_data (source_id, external_id, content_type, title, description, content, tags, severity, url, content_hash, metadata, is_deleted)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,false)
                    """, item["source_id"], item["external_id"], item["content_type"], item["title"], item.get("description"), json.dumps(item["content"]), item.get("tags", []), item.get("severity"), item.get("url"), item["content_hash"], json.dumps(item.get("metadata") or {}))
                    stats["inserted"] += 1
                    logger.info(f"INSERT {ext_id}")
                else:
                    existing = existing_map[ext_id]
                    if item["content_hash"] != existing["content_hash"]:
                        await conn.execute("""
                            UPDATE scraped_data SET title=$1, description=$2, content=$3, tags=$4, severity=$5, url=$6, content_hash=$7, last_updated_at=NOW(), metadata=$8
                            WHERE id=$9
                        """, item["title"], item.get("description"), json.dumps(item["content"]), item.get("tags", []), item.get("severity"), item.get("url"), item["content_hash"], json.dumps(item.get("metadata") or {}), existing["id"])
                        stats["updated"] += 1
                        logger.info(f"UPDATE {ext_id}")
                    else:
                        stats["unchanged"] += 1

            # Deleted
            deleted_ids = set(existing_map.keys()) - set(fetched_map.keys())
            for ext_id in deleted_ids:
                eid = existing_map[ext_id]["id"]
                await conn.execute("DELETE FROM scraped_data WHERE id=$1", eid)
                stats["deleted"] += 1
                logger.info(f"DELETE {ext_id}")

            return stats
        finally:
            await conn.close()

    async def run(self) -> Dict[str, int]:
        logger.info(f"Starting scrape for {self.get_source_name()}")
        raw = await self.fetch_data()
        logger.info(f"Fetched {len(raw)} raw items")
        normalized = []
        for r in raw:
            try:
                normalized.append(self.normalize_item(r))
            except Exception as e:
                logger.error(f"Normalize failed: {e}", exc_info=True)
        logger.info(f"Normalized {len(normalized)} items")
        stats = await self.sync_to_db(normalized)
        logger.info(f"Sync done: {stats}")
        return stats
