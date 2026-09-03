from typing import List, Dict, Any
import httpx
from scrapers.base import BaseScraper
import logging

logger = logging.getLogger(__name__)

class MITREAttackScraper(BaseScraper):
    URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    def get_source_name(self) -> str: return "mitre_attack"
    async def fetch_data(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(self.URL)
            resp.raise_for_status()
            data = resp.json()
            techniques = [o for o in data.get("objects", []) if o.get("type")=="attack-pattern" and not o.get("revoked")]
            logger.info(f"Fetched {len(techniques)} techniques")
            return techniques
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        tid = None
        for ref in raw_item.get("external_references", []):
            if ref.get("source_name")=="mitre-attack":
                tid = ref.get("external_id")
                break
        if not tid: raise ValueError(f"No TID for {raw_item.get('name')}")
        tactics = [p["phase_name"] for p in raw_item.get("kill_chain_phases", []) if p.get("kill_chain_name")=="mitre-attack"]
        tags = ["mitre-attack", tid.lower()] + tactics + [p.lower() for p in raw_item.get("x_mitre_platforms",[])]
        is_sub = "." in tid
        return {
            "external_id": tid,
            "content_type": "technique",
            "title": raw_item["name"],
            "description": raw_item.get("description",""),
            "content": {"technique_id": tid, "is_sub_technique": is_sub, "tactics": tactics, "platforms": raw_item.get("x_mitre_platforms",[]), "description": raw_item.get("description",""), "mitre_version": raw_item.get("x_mitre_version")},
            "tags": tags,
            "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"
        }
