from typing import List, Dict, Any
import httpx, asyncio, logging, re
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
logger=logging.getLogger(__name__)
class KaliDocsScraper(BaseScraper):
    LIST_URL = "https://www.kali.org/tools/"
    def get_source_name(self): return "kali_docs"
    async def fetch_data(self):
        items=[]
        # First fetch the full tools listing page to discover all tools dynamically
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent":"Mozilla/5.0"}) as client:
            try:
                logger.info(f"Fetching Kali tools list {self.LIST_URL}")
                r = await client.get(self.LIST_URL)
                r.raise_for_status()
                soup = BeautifulSoup(r.text,"html.parser")
                # kali.org/tools page has cards/links to /tools/{tool}/
                links=set()
                for a in soup.find_all("a", href=True):
                    href=a["href"]
                    # Match /tools/<name>/  but not /tools/ itself and not category anchors
                    if re.match(r"^https://www\.kali\.org/tools/[^/]+/$", href) or re.match(r"^/tools/[^/]+/$", href):
                        # Normalize to absolute
                        if href.startswith("/"):
                            href="https://www.kali.org"+href
                        # Skip docs parent pages
                        if href.rstrip("/") == "https://www.kali.org/tools":
                            continue
                        links.add(href)
                # Also try alternative selector: find all h3/a inside tool listing
                if len(links) < 50:
                    for a in soup.select("a[href*='/tools/']"):
                        href=a.get("href","")
                        if "/tools/" in href and href.count("/")>=4:
                            if href.startswith("/"): href="https://www.kali.org"+href
                            if href.startswith("https://www.kali.org/tools/") and href != "https://www.kali.org/tools/":
                                links.add(href.rstrip("/")+"/")
                tool_urls = sorted(links)
                logger.info(f"Discovered {len(tool_urls)} Kali tools")
                # Fallback to hardcoded if discovery failed
                if len(tool_urls) < 20:
                    logger.warning(f"Only {len(tool_urls)} tools discovered, using fallback list")
                    tool_urls=[]
                    for t in ["nmap","metasploit-framework","burpsuite","sqlmap","wireshark","aircrack-ng","john","hashcat","nikto","hydra"]:
                        tool_urls.append(f"https://www.kali.org/tools/{t}/")
                # Now fetch each tool page (limit to 200 for safety, but Kali has ~400)
                # To keep time reasonable, fetch all but with concurrency limit
                semaphore = asyncio.Semaphore(5)
                async def fetch_one(url):
                    async with semaphore:
                        try:
                            # Extract tool name from URL
                            name = url.rstrip("/").split("/")[-1]
                            resp = await client.get(url)
                            if resp.status_code != 200:
                                logger.warning(f"Kali {name} status {resp.status_code}")
                                return {"name": name, "category": "Unknown", "description": f"Kali tool {name}", "url": url, "usage": name, "detailed_description": "", "examples": []}
                            s2 = BeautifulSoup(resp.text,"html.parser")
                            # Title and description
                            title_el = s2.find("h1") or s2.find("title")
                            title = title_el.get_text(strip=True) if title_el else name
                            # Try to find description: first p under content
                            content = s2.find("div", class_="content") or s2.find("main") or s2
                            ps = content.find_all("p", limit=3) if content else []
                            desc = " ".join([p.get_text(strip=True) for p in ps])[:1200] if ps else f"Kali tool {name}"
                            # Try to find category breadcrumb
                            cat = "Unknown"
                            breadcrumb = s2.find("nav", class_="breadcrumb") or s2.find("ol", class_="breadcrumb")
                            if breadcrumb:
                                cats = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
                                if len(cats)>=2:
                                    cat = cats[-2]
                            # Detailed + examples
                            detailed = " ".join([p.get_text(strip=True) for p in ps]) if ps else ""
                            codes = s2.find_all("code")
                            examples = [c.get_text(strip=True) for c in codes[:3] if len(c.get_text(strip=True))<500]
                            return {"name": name, "category": cat, "description": desc[:800], "url": url, "usage": name, "detailed_description": detailed[:1000], "examples": examples, "title": title}
                        except Exception as e:
                            logger.warning(f"fetch {url} failed: {e}")
                            name = url.rstrip("/").split("/")[-1]
                            return {"name": name, "category": "Unknown", "description": f"Kali tool {name}", "url": url, "usage": name, "detailed_description": "", "examples": []}
                # Limit to 150 for time, but you can increase to 400
                to_fetch = tool_urls[:250]
                results = await asyncio.gather(*[fetch_one(u) for u in to_fetch])
                items = [r for r in results if r]
                logger.info(f"Fetched {len(items)} Kali tool pages")
            except Exception as e:
                logger.error(f"Kali list fetch failed: {e}", exc_info=True)
                # Fallback minimal
                for t in ["nmap","sqlmap","burpsuite"]:
                    items.append({"name": t, "category": "Unknown", "description": f"Kali tool {t}", "url": f"https://www.kali.org/tools/{t}/", "usage": t, "detailed_description": "", "examples": []})
        return items
    def normalize_item(self, raw_item):
        name=raw_item["name"]
        cat=raw_item.get("category","Unknown")
        tags=["kali","tool", name.lower()]
        low=cat.lower()
        if "web" in low: tags.append("web-security")
        if "password" in low: tags.append("password-cracking")
        if "wireless" in low: tags.append("wireless")
        if "information" in low: tags.append("reconnaissance")
        if "exploitation" in low: tags.append("exploitation")
        if "sniffing" in low: tags.append("sniffing")
        # Add tags from name
        if "nmap" in name: tags.extend(["scanning","network"])
        if "sqlmap" in name: tags.append("sql-injection")
        return {"external_id": f"kali_{name}", "content_type": "tool_doc", "title": f"{name} - {cat}", "description": raw_item.get("description",""), "content": {"tool_name": name, "category": cat, "description": raw_item.get("description",""), "detailed_description": raw_item.get("detailed_description",""), "usage": raw_item.get("usage",""), "examples": raw_item.get("examples",[])}, "tags": tags, "url": raw_item["url"]}
