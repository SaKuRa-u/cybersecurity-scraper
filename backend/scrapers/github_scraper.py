from typing import List, Dict, Any
import os, hashlib, logging, asyncio
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

class GitHubScraper(BaseScraper):
    CURATED = ["swisskyrepo/PayloadsAllTheThings","danielmiessler/SecLists","offensive-security/exploitdb"]
    def get_source_name(self) -> str: return "github_payloads"
    async def fetch_data(self) -> List[Dict[str, Any]]:
        token = os.getenv("GITHUB_TOKEN","")
        headers = {"Authorization": f"token {token}"} if token else {}
        import httpx
        items=[]
        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            for repo in self.CURATED:
                try:
                    # Get repo info for stars
                    r = await client.get(f"https://api.github.com/repos/{repo}")
                    r.raise_for_status()
                    stars = r.json().get("stargazers_count",0)
                    # List contents root (limit)
                    r2 = await client.get(f"https://api.github.com/repos/{repo}/contents")
                    if r2.status_code!=200: continue
                    for content in r2.json()[:20]:
                        if content.get("type")=="file" and content.get("name","").endswith((".md",".txt",".html")):
                            try:
                                # fetch file content via download_url
                                dl = content.get("download_url")
                                if not dl: continue
                                rf = await client.get(dl)
                                text = rf.text[:4000] if rf.status_code==200 else ""
                                items.append({"repo": repo, "file_path": content.get("path"), "stars": stars, "content": text, "url": content.get("html_url"), "sha": content.get("sha")})
                            except Exception as e:
                                logger.warning(f"fetch file failed {e}")
                    await asyncio.sleep(1)
                    # rate limit check
                    rl = await client.get("https://api.github.com/rate_limit")
                    if rl.status_code==200:
                        rem = rl.json()["resources"]["core"]["remaining"]
                        if rem < 10: logger.warning(f"Rate limit low {rem}"); break
                except Exception as e:
                    logger.error(f"GitHub repo {repo} failed: {e}")
        logger.info(f"GitHub fetched {len(items)}")
        return items
    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        fp = raw_item["file_path"]
        repo = raw_item["repo"]
        h = hashlib.md5(fp.encode()).hexdigest()[:8]
        ext = f"github_{repo.replace('/','_')}_{h}"
        tags=["github","payload"]
        low=fp.lower()
        if "xss" in low: tags.append("xss")
        if "sql" in low: tags.append("sql-injection")
        if "rce" in low: tags.append("rce")
        if "xxe" in low: tags.append("xxe")
        return {
            "external_id": ext,
            "content_type": "payload",
            "title": f"{fp} - {repo}",
            "description": f"Payload from {repo}",
            "content": {"repo": repo, "file_path": fp, "stars": raw_item["stars"], "payload_content": raw_item["content"], "sha": raw_item.get("sha")},
            "tags": tags,
            "url": raw_item["url"]
        }
