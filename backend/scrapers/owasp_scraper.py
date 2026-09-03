from typing import List, Dict, Any
import httpx, asyncio, logging, os, re
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

class OWASPScraper(BaseScraper):
    def get_source_name(self) -> str:
        return "owasp"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        result = []
        result.extend(await self._fetch_top10())
        try:
            cheats = await self._fetch_cheatsheets()
            result.extend(cheats)
            logger.info(f"OWASP total fetched {len(result)} (Top10 10 + CheatSheets {len(cheats)})")
        except Exception as e:
            logger.error(f"CheatSheet fetch failed: {e}", exc_info=True)
        return result

    async def _fetch_top10(self) -> List[Dict[str, Any]]:
        categories = [
            {"category": "A01", "title": "Broken Access Control", "url": "https://owasp.org/Top10/2021/A01_2021-Broken_Access_Control/index.html", "cwe_ids": ["CWE-200", "CWE-352"]},
            {"category": "A02", "title": "Cryptographic Failures", "url": "https://owasp.org/Top10/2021/A02_2021-Cryptographic_Failures/index.html", "cwe_ids": ["CWE-259", "CWE-327"]},
            {"category": "A03", "title": "Injection", "url": "https://owasp.org/Top10/2021/A03_2021-Injection/index.html", "cwe_ids": ["CWE-79", "CWE-89"]},
            {"category": "A04", "title": "Insecure Design", "url": "https://owasp.org/Top10/2021/A04_2021-Insecure_Design/index.html", "cwe_ids": ["CWE-209", "CWE-256"]},
            {"category": "A05", "title": "Security Misconfiguration", "url": "https://owasp.org/Top10/2021/A05_2021-Security_Misconfiguration/index.html", "cwe_ids": ["CWE-16", "CWE-611"]},
            {"category": "A06", "title": "Vulnerable and Outdated Components", "url": "https://owasp.org/Top10/2021/A06_2021-Vulnerable_and_Outdated_Components/index.html", "cwe_ids": ["CWE-1104"]},
            {"category": "A07", "title": "Identification and Authentication Failures", "url": "https://owasp.org/Top10/2021/A07_2021-Identification_and_Authentication_Failures/index.html", "cwe_ids": ["CWE-287", "CWE-384"]},
            {"category": "A08", "title": "Software and Data Integrity Failures", "url": "https://owasp.org/Top10/2021/A08_2021-Software_and_Data_Integrity_Failures/index.html", "cwe_ids": ["CWE-829", "CWE-502"]},
            {"category": "A09", "title": "Security Logging and Monitoring Failures", "url": "https://owasp.org/Top10/2021/A09_2021-Security_Logging_and_Monitoring_Failures/index.html", "cwe_ids": ["CWE-778", "CWE-117"]},
            {"category": "A10", "title": "Server-Side Request Forgery", "url": "https://owasp.org/Top10/2021/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/index.html", "cwe_ids": ["CWE-918"]},
        ]
        out = []
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for cat in categories:
                try:
                    resp = await client.get(cat["url"])
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Handle meta refresh redirect (old OWASP URLs)
                    if soup.title and "Redirecting" in soup.title.get_text():
                        link = soup.find("link", rel="canonical") or soup.find("meta", attrs={"http-equiv": "refresh"})
                        redirect = None
                        if link and link.get("href"):
                            redirect = link["href"]
                        elif link and link.get("content"):
                            m = re.search(r"url=(.+)", link["content"])
                            if m: redirect = m.group(1).strip().strip("'\"")
                        if redirect:
                            if redirect.startswith("/"):
                                redirect = "https://owasp.org" + redirect
                            logger.info(f"Following meta refresh {cat['url']} -> {redirect}")
                            resp = await client.get(redirect)
                            resp.raise_for_status()
                            soup = BeautifulSoup(resp.text, "html.parser")
                    main = soup.find("div", class_="main-content") or soup.find("main") or soup.find("article") or soup
                    elements = main.find_all(["h1","h2","h3","h4","p","pre","ul","ol","table"]) if main else []
                    parts = []
                    for el in elements:
                        txt = el.get_text(" ", strip=True)
                        if len(txt) < 20: continue
                        if el.name.startswith("h"):
                            parts.append(f"\n## {txt}\n")
                        elif el.name == "pre":
                            parts.append(f"\n```\n{txt}\n```\n")
                        elif el.name in ("ul","ol","table"):
                            parts.append(txt)
                        else:
                            parts.append(txt)
                    full = " ".join(parts)
                    # No truncation - full content for RAG
                    cat["description"] = full if full else f"OWASP Top 10 2021 - {cat['title']}"
                    cat["full_content"] = full
                    cat["year"] = 2021
                    cat["type"] = "top10"
                    out.append(dict(cat))
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Top10 {cat['url']} failed: {e}")
                    cat["description"] = f"OWASP Top 10 2021 - {cat['title']}"
                    cat["year"] = 2021
                    cat["type"] = "top10"
                    out.append(dict(cat))
        return out

    async def _fetch_cheatsheets(self) -> List[Dict[str, Any]]:
        token = os.getenv("GITHUB_TOKEN","")
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"} if token else {}
        out = []
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            r = await client.get("https://api.github.com/repos/OWASP/CheatSheetSeries")
            r.raise_for_status()
            branch = r.json().get("default_branch","master")
            tr = await client.get(f"https://api.github.com/repos/OWASP/CheatSheetSeries/git/trees/{branch}?recursive=1")
            tr.raise_for_status()
            tree = tr.json().get("tree",[])
            cheats = [n for n in tree if n.get("type")=="blob" and n.get("path","").startswith("cheatsheets/") and n.get("path","").endswith(".md")]
            logger.info(f"CheatSheetSeries has {len(cheats)} sheets")
            for node in cheats[:100]:
                path = node["path"]
                name = path.split("/")[-1].replace(".md","")
                title = name.replace("_"," ").replace("-"," ")
                try:
                    raw_url = f"https://raw.githubusercontent.com/OWASP/CheatSheetSeries/{branch}/{path}"
                    rf = await client.get(raw_url)
                    content = rf.text if rf.status_code==200 else ""
                    # No truncation - full markdown
                    desc = content.split("\n\n")[1] if "\n\n" in content and len(content.split("\n\n")[1])>50 else content[:2000]
                    out.append({
                        "category": f"CS-{name[:15]}",
                        "title": title,
                        "url": f"https://cheatsheetseries.owasp.org/cheatsheets/{name}.html",
                        "cwe_ids": [],
                        "description": desc,
                        "full_content": content,
                        "year": 2024,
                        "type": "cheatsheet",
                        "path": path
                    })
                    await asyncio.sleep(0.2)
                except Exception as e:
                    logger.warning(f"CheatSheet {path} failed: {e}")
        return out

    def normalize_item(self, raw_item: Dict) -> Dict[str, Any]:
        category = raw_item["category"]
        year = raw_item["year"]
        item_type = raw_item.get("type","top10")
        title_lower = raw_item["title"].lower()
        tags = ["owasp", f"owasp-{year}", category.lower(), item_type]
        if "access" in title_lower: tags.append("access-control")
        if "injection" in title_lower: tags.append("injection")
        if "crypto" in title_lower: tags.append("cryptography")
        if "auth" in title_lower: tags.append("authentication")
        if "config" in title_lower: tags.append("configuration")
        if "cheat" in item_type or "CS-" in category: tags.append("cheatsheet")
        if "xss" in title_lower: tags.append("xss")
        if "sql" in title_lower: tags.append("sql-injection")
        if item_type == "cheatsheet":
            ext = f"owasp_cheat_{raw_item['title'].lower().replace(' ','_')[:50]}"
        else:
            ext = f"owasp_{category}_{year}"
        content = {
            "category": category,
            "year": year,
            "type": item_type,
            "cwe_ids": raw_item.get("cwe_ids", []),
            "details": raw_item.get("description", ""),
            "full_content": raw_item.get("full_content",""),
            "path": raw_item.get("path","")
        }
        return {
            "external_id": ext,
            "content_type": "vulnerability",
            "title": f"{category}: {raw_item['title']}" if item_type=="top10" else f"CheatSheet: {raw_item['title']}",
            "description": raw_item.get("description", ""),
            "content": content,
            "tags": tags,
            "severity": "high" if item_type=="top10" else "medium",
            "url": raw_item.get("url")
        }
