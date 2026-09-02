import asyncio
import asyncpg
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_conn():
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return await asyncpg.connect(url)

@router.websocket("/ws/scrape-progress")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")
    try:
        while True:
            # Send current sessions status every 2 seconds
            try:
                conn = await get_conn()
                rows = await conn.fetch("""
                    SELECT ss.id, ss.status, ss.items_inserted, ss.items_updated, ss.items_deleted, ss.items_found,
                           s.display_name, s.name
                    FROM scrape_sessions ss
                    JOIN sources s ON s.id = ss.source_id
                    ORDER BY ss.started_at DESC LIMIT 10
                """)
                await conn.close()
                # Check if any running/pending
                active = [dict(r) for r in rows if r["status"] in ("pending", "running")]
                payload = {
                    "type": "sessions",
                    "data": [dict(r) for r in rows],
                    "active": active,
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(payload, default=str))
            except Exception as e:
                logger.error(f"WS send failed: {e}")
                try:
                    await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                except:
                    pass
            # Wait 2s or until client sends ping
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                # Got ping, respond pong and continue
                await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
