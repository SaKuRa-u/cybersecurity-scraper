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
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent":"Mozilla/5.0"}) as client:
            try:
                logger.info(f"Fetching Kali tools list {self.LIST_URL}")
                r = await client.get(self.LIST_URL)
                r.raise_for_status()
                soup = BeautifulSoup(r.text,"html.parser")
                # Discover all tools with category via parent card
                links = {}  # url -> category
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    base = href.split("#")[0].split("?")[0].strip()
                    if base.startswith("/tools/"):
                        base = "https://www.kali.org" + base
                    # Match https://www.kali.org/tools/<tool> or https://www.kali.org/tools/<tool>/
                    m = re.match(r"^https://www\.kali\.org/tools/([^/]+)/?$", base)
                    if not m:
                        continue
                    tool_name = m.group(1)
                    # Skip non-tool pages
                    if tool_name in ["", "tools", "all-tools", "top-100"]:
                        continue
                    url = f"https://www.kali.org/tools/{tool_name}/"
                    # Skip if already captured
                    if url in links:
                        continue
                    # Find category via parent card
                    cat = "Unknown"
                    card = a.find_parent("div", class_="card")
                    if card:
                        h3 = card.find("h3")
                        if h3:
                            cat = h3.get_text(strip=True)
                        # Try subcategory label if inside subcategory
                        sub = a.find_parent("li", class_="subcategory")
                        if sub:
                            label = sub.find("label")
                            if label:
                                subcat = label.get_text(strip=True)
                                cat = f"{cat} > {subcat}" if cat != "Unknown" else subcat
                    # Fallback: try to find nearest h3 previous sibling
                    if cat == "Unknown":
                        # Walk up to find any h3 ancestor's text
                        for parent in a.parents:
                            if parent.name == "div" and parent.get("class") and "card" in parent.get("class"):
                                h3 = parent.find("h3")
                                if h3:
                                    cat = h3.get_text(strip=True)
                                    break
                    links[url] = cat
                tool_map = links
                tool_urls = sorted(tool_map.keys())
                logger.info(f"Discovered {len(tool_urls)} Kali tools (with categories)")
                # Debug: ensure nmap present
                if "https://www.kali.org/tools/nmap/" not in tool_urls:
                    logger.warning("nmap not discovered, forcing add")
                    tool_urls.append("https://www.kali.org/tools/nmap/")
                    tool_map["https://www.kali.org/tools/nmap/"] = "Information Gathering"
                if len(tool_urls) < 20:
                    logger.warning(f"Only {len(tool_urls)} tools, using fallback")
                    for t in ["nmap","metasploit-framework","burpsuite","sqlmap","wireshark","aircrack-ng","john","hashcat","nikto","hydra"]:
                        url = f"https://www.kali.org/tools/{t}/"
                        if url not in tool_map:
                            tool_map[url] = "Unknown"
                            tool_urls.append(url)
                # Fetch each tool page with known category
                semaphore = asyncio.Semaphore(5)
                async def fetch_one(url):
                    async with semaphore:
                        try:
                            name = url.rstrip("/").split("/")[-1]
                            known_cat = tool_map.get(url, "Unknown")
                            resp = await client.get(url)
                            if resp.status_code != 200:
                                return {"name": name, "category": known_cat, "description": f"Kali tool {name}", "url": url, "usage": name, "detailed_description": "", "examples": []}
                            s2 = BeautifulSoup(resp.text,"html.parser")
                            title_el = s2.find("h1") or s2.find("title")
                            title = title_el.get_text(strip=True) if title_el else name
                            # Deep extraction: get full section content
                            content_section = s2.find("section", id="content") or s2.find("div", class_="content") or s2.find("main") or s2
                            # Description: first substantial paragraphs (up to 5000 chars)
                            ps = content_section.find_all("p") if content_section else []
                            # Filter out empty and take first 8 paragraphs
                            desc_paras = [p.get_text(strip=True) for p in ps if len(p.get_text(strip=True)) > 20][:8]
                            desc = " ".join(desc_paras)[:5000] if desc_paras else f"Kali tool {name}"
                            cat = known_cat
                            if cat == "Unknown":
                                breadcrumb = s2.find("nav", class_="breadcrumb") or s2.find("ol", class_="breadcrumb")
                                if breadcrumb:
                                    cats = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
                                    if len(cats)>=2:
                                        cat = cats[-2]
                            # Detailed: all text from content_section (including headings + pre) - FULL, no arbitrary cut
                            detailed = ""
                            if content_section:
                                elements = content_section.find_all(["h1","h2","h3","h4","h5","p","pre"])
                                parts = []
                                for el in elements:  # all elements, no 120 limit
                                    txt = el.get_text(" ", strip=True)
                                    if len(txt) < 20:
                                        continue
                                    if el.name.startswith("h"):
                                        parts.append(f"\n## {txt}\n")
                                    elif el.name == "pre":
                                        parts.append(f"\n```\n{txt}\n```\n")
                                    else:
                                        parts.append(txt)
                                detailed = " ".join(parts)  # no 50k limit, store full
                            # Examples: all pre/code blocks full (no 500 char filter)
                            examples = []
                            if content_section:
                                pres = content_section.find_all("pre")
                                for pre in pres[:8]:
                                    txt = pre.get_text(" ", strip=True)
                                    if len(txt) > 30:
                                        examples.append(txt[:12000])
                                if not examples:
                                    codes = content_section.find_all("code")
                                    for c in codes[:5]:
                                        txt = c.get_text(strip=True)
                                        if 20 < len(txt) < 5000:
                                            examples.append(txt[:2000])
                            # Try to fetch official homepage for fresher context (hybrid) - ALL tools, not just nmap
                            official_desc = ""
                            try:
                                pkg_links = s2.find("div", id="package-links")
                                official_url = None
                                if pkg_links:
                                    for a in pkg_links.find_all("a", href=True):
                                        href = a["href"]
                                        # First http link that is not Kali infra = official homepage
                                        if href.startswith("http") and "kali.org" not in href and "pkg.kali.org" not in href and "gitlab.com/kalilinux" not in href and "bugs.kali.org" not in href and "edit" not in href.lower():
                                            official_url = href.split("#")[0].split("?")[0]
                                            break
                                if official_url:
                                    logger.info(f"{name} official {official_url}")
                                    # Fetch official with longer timeout (scraper can be slow, as requested)
                                    try:
                                        r2 = await client.get(official_url, timeout=30.0, follow_redirects=True, headers={"User-Agent":"Mozilla/5.0"})
                                        if r2.status_code == 200 and len(r2.text) > 500:
                                            s3 = BeautifulSoup(r2.text,"html.parser")
                                            # Remove scripts/styles
                                            for tag in s3(["script","style","nav","footer"]):
                                                tag.decompose()
                                            op = s3.find_all("p", limit=5)
                                            official_desc = " ".join([p.get_text(strip=True) for p in op if len(p.get_text(strip=True))>30])[:8000]
                                            if not examples:
                                                ocodes = s3.find_all("code", limit=5)
                                                examples = [c.get_text(strip=True)[:2000] for c in ocodes if 10 < len(c.get_text(strip=True)) < 3000][:3]
                                            if official_desc:
                                                desc = f"{desc} [Official {official_url}: {official_desc[:3000]}]"
                                                detailed = f"{detailed}\n\n--- Official {official_url} ---\n{official_desc[:8000]}"
                                    except Exception as oe:
                                        logger.debug(f"Official fetch failed for {name} ({official_url}): {oe}")
                            except Exception as e:
                                logger.debug(f"Official extract failed for {name}: {e}")
                            return {"name": name, "category": cat, "description": desc[:8000], "url": url, "usage": name, "detailed_description": detailed, "examples": examples[:8], "title": title}
                        except Exception as e:
                            logger.warning(f"fetch {url} failed: {e}")
                            name = url.rstrip("/").split("/")[-1]
                            return {"name": name, "category": tool_map.get(url,"Unknown"), "description": f"Kali tool {name}", "url": url, "usage": name, "detailed_description": "", "examples": []}
                to_fetch = tool_urls[:300]
                results = await asyncio.gather(*[fetch_one(u) for u in to_fetch])
                items = [r for r in results if r]
                logger.info(f"Fetched {len(items)} Kali tool pages (unique categories: {len(set([i['category'] for i in items]))})")
            except Exception as e:
                logger.error(f"Kali list fetch failed: {e}", exc_info=True)
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
        if "information" in low or "reconnaissance" in low: tags.append("reconnaissance")
        if "exploitation" in low: tags.append("exploitation")
        if "sniffing" in low: tags.append("sniffing")
        if "vulnerability" in low: tags.append("vulnerability-scanning")
        if "nmap" in name: tags.extend(["scanning","network"])
        if "sqlmap" in name: tags.append("sql-injection")
        return {"external_id": f"kali_{name}", "content_type": "tool_doc", "title": f"{name} - {cat}", "description": raw_item.get("description",""), "content": {"tool_name": name, "category": cat, "description": raw_item.get("description",""), "detailed_description": raw_item.get("detailed_description",""), "usage": raw_item.get("usage",""), "examples": raw_item.get("examples",[])}, "tags": tags, "url": raw_item["url"]}
