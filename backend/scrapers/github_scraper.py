from typing import List, Dict, Any
import os, hashlib, logging, asyncio
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

class GitHubScraper(BaseScraper):
    """
    Deep scraper: uses Git Trees API (recursive=1) to get ALL files in one request per repo.
    Falls back to /contents traversal if tree API fails.
    """
    CURATED = ["swisskyrepo/PayloadsAllTheThings","danielmiessler/SecLists","offensive-security/exploitdb"]
    # Payload-relevant extensions; keep md/txt/json/yaml/py/sh etc.
    ALLOWED_EXT = {".md",".txt",".json",".yaml",".yml",".py",".sh",".js",".html",".xml",".csv",".sql",".php"}
    MAX_FILES_PER_REPO = 800  # safety limit

    def get_source_name(self) -> str: return "github_payloads"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        token = os.getenv("GITHUB_TOKEN","")
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"} if token else {}
        import httpx
        items=[]
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for repo in self.CURATED:
                try:
                    logger.info(f"GitHub deep fetch {repo}")
                    # 1. Get default branch
                    r = await client.get(f"https://api.github.com/repos/{repo}")
                    r.raise_for_status()
                    data = r.json()
                    stars = data.get("stargazers_count",0)
                    branch = data.get("default_branch","master")
                    # 2. Get full tree recursively
                    tr = await client.get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1")
                    if tr.status_code != 200:
                        logger.warning(f"Tree API failed {repo}: {tr.status_code}, fallback to contents")
                        items.extend(await self._fallback_contents(client, repo, stars))
                        continue
                    tree = tr.json().get("tree",[])
                    logger.info(f"{repo} tree has {len(tree)} objects")
                    # Filter blobs with allowed ext
                    count=0
                    for node in tree:
                        if node.get("type")!="blob": continue
                        path = node.get("path","")
                        # skip hidden, binary, large
                        if any(skip in path.lower() for skip in [".git", "node_modules", ".png",".jpg",".jpeg",".gif",".zip",".tar",".gz",".exe",".bin"]):
                            continue
                        ext = "." + path.split(".")[-1].lower() if "." in path else ""
                        if ext not in self.ALLOWED_EXT and not path.endswith("README"):
                            continue
                        if count >= self.MAX_FILES_PER_REPO: break
                        # Fetch file content via raw.githubusercontent or download via API
                        # Use raw url for speed: https://raw.githubusercontent.com/{repo}/{branch}/{path}
                        raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
                        try:
                            rf = await client.get(raw_url)
                            text = rf.text if rf.status_code==200 else ""
                        except: text=""
                        items.append({"repo": repo, "file_path": path, "stars": stars, "content": text, "url": f"https://github.com/{repo}/blob/{branch}/{path}", "sha": node.get("sha")})
                        count+=1
                    logger.info(f"{repo} collected {count} payload files")
                    await asyncio.sleep(0.5)
                    # Rate limit check
                    rl = await client.get("https://api.github.com/rate_limit")
                    if rl.status_code==200:
                        rem = rl.json()["resources"]["core"]["remaining"]
                        if rem < 20:
                            logger.warning(f"Rate limit low {rem}, sleeping 60s")
                            await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"GitHub {repo} failed: {e}", exc_info=True)
        logger.info(f"GitHub deep fetched total {len(items)}")
        return items

    async def _fallback_contents(self, client, repo, stars):
        """Fallback: list root contents (old behavior)"""
        items=[]
        try:
            r2 = await client.get(f"https://api.github.com/repos/{repo}/contents")
            if r2.status_code!=200: return items
            for content in r2.json()[:30]:
                if content.get("type")=="file":
                    items.append({"repo": repo, "file_path": content.get("path"), "stars": stars, "content": "", "url": content.get("html_url"), "sha": content.get("sha")})
        except Exception as e:
            logger.warning(f"Fallback failed {repo}: {e}")
        return items

    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        fp = raw_item["file_path"]
        repo = raw_item["repo"]
        h = hashlib.md5(f"{repo}:{fp}".encode()).hexdigest()[:8]
        ext = f"github_{repo.replace('/','_')}_{h}"
        tags=["github","payload"]
        low=fp.lower()
        if "xss" in low: tags.append("xss")
        if "sql" in low or "sqli" in low: tags.append("sql-injection")
        if "rce" in low: tags.append("rce")
        if "xxe" in low: tags.append("xxe")
        if "lfi" in low or "rfi" in low or "traversal" in low: tags.append("lfi")
        if "ssti" in low: tags.append("ssti")
        if "ssrf" in low: tags.append("ssrf")
        return {
            "external_id": ext,
            "content_type": "payload",
            "title": f"{fp} - {repo}",
            "description": f"Payload from {repo}",
            "content": {"repo": repo, "file_path": fp, "stars": raw_item["stars"], "payload_content": raw_item["content"], "sha": raw_item.get("sha")},
            "tags": tags,
            "url": raw_item["url"]
        }
