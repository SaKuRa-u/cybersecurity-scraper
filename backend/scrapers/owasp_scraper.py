from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
import logging
import asyncio

logger = logging.getLogger(__name__)

class OWASPScraper(BaseScraper):
    def get_source_name(self) -> str:
        return "owasp"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        categories = [
            {"category": "A01", "title": "Broken Access Control", "url": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/", "cwe_ids": ["CWE-200", "CWE-352"]},
            {"category": "A02", "title": "Cryptographic Failures", "url": "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/", "cwe_ids": ["CWE-259", "CWE-327"]},
            {"category": "A03", "title": "Injection", "url": "https://owasp.org/Top10/A03_2021-Injection/", "cwe_ids": ["CWE-79", "CWE-89"]},
            {"category": "A04", "title": "Insecure Design", "url": "https://owasp.org/Top10/A04_2021-Insecure_Design/", "cwe_ids": ["CWE-209", "CWE-256"]},
            {"category": "A05", "title": "Security Misconfiguration", "url": "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/", "cwe_ids": ["CWE-16", "CWE-611"]},
            {"category": "A06", "title": "Vulnerable and Outdated Components", "url": "https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/", "cwe_ids": ["CWE-1104"]},
            {"category": "A07", "title": "Identification and Authentication Failures", "url": "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/", "cwe_ids": ["CWE-287", "CWE-384"]},
            {"category": "A08", "title": "Software and Data Integrity Failures", "url": "https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/", "cwe_ids": ["CWE-829", "CWE-502"]},
            {"category": "A09", "title": "Security Logging and Monitoring Failures", "url": "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/", "cwe_ids": ["CWE-778", "CWE-117"]},
            {"category": "A10", "title": "Server-Side Request Forgery", "url": "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/", "cwe_ids": ["CWE-918"]},
        ]
        result = []
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            for cat in categories:
                try:
                    resp = await client.get(cat["url"])
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                    main = soup.find("div", class_="main-content") or soup.find("main") or soup
                    ps = main.find_all("p", limit=3) if main else []
                    desc = " ".join([p.get_text(strip=True) for p in ps]) if ps else f"OWASP Top 10 2021 - {cat['title']}"
                    cat["description"] = desc[:1000]
                    cat["year"] = 2021
                    result.append(dict(cat))
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Failed fetch {cat['url']}: {e}")
                    cat["description"] = f"OWASP Top 10 2021 - {cat['title']}"
                    cat["year"] = 2021
                    result.append(dict(cat))
        return result

    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        category = raw_item["category"]
        year = raw_item["year"]
        title_lower = raw_item["title"].lower()
        tags = ["owasp", f"owasp-{year}", category.lower()]
        if "access" in title_lower: tags.append("access-control")
        if "injection" in title_lower: tags.append("injection")
        if "crypto" in title_lower: tags.append("cryptography")
        if "auth" in title_lower: tags.append("authentication")
        if "config" in title_lower: tags.append("configuration")
        return {
            "external_id": f"owasp_{category}_{year}",
            "content_type": "vulnerability",
            "title": f"{category}: {raw_item['title']}",
            "description": raw_item.get("description", ""),
            "content": {"category": category, "year": year, "cwe_ids": raw_item.get("cwe_ids", []), "details": raw_item.get("description", "")},
            "tags": tags,
            "severity": "high",
            "url": raw_item.get("url")
        }
