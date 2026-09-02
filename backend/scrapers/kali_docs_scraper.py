from typing import List, Dict, Any
import httpx, asyncio, logging
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
logger=logging.getLogger(__name__)
class KaliDocsScraper(BaseScraper):
    POPULAR=[{"name":"nmap","category":"Information Gathering","description":"Network exploration tool","url":"https://www.kali.org/tools/nmap/","usage":"nmap [Scan Type] [Options] {target}"},{"name":"metasploit-framework","category":"Exploitation Tools","description":"Advanced platform for exploits","url":"https://www.kali.org/tools/metasploit-framework/","usage":"msfconsole"},{"name":"burpsuite","category":"Web Application Analysis","description":"Platform for security testing web apps","url":"https://www.kali.org/tools/burpsuite/","usage":"burpsuite"},{"name":"sqlmap","category":"Web Application Analysis","description":"Automatic SQL injection tool","url":"https://www.kali.org/tools/sqlmap/","usage":"sqlmap -u <URL> [options]"},{"name":"wireshark","category":"Sniffing & Spoofing","description":"Network protocol analyzer","url":"https://www.kali.org/tools/wireshark/","usage":"wireshark"},{"name":"aircrack-ng","category":"Wireless Attacks","description":"WiFi security auditing suite","url":"https://www.kali.org/tools/aircrack-ng/","usage":"aircrack-ng [options] <input>"},{"name":"john","category":"Password Attacks","description":"John the Ripper","url":"https://www.kali.org/tools/john/","usage":"john [options] [password files]"},{"name":"hashcat","category":"Password Attacks","description":"Advanced password recovery","url":"https://www.kali.org/tools/hashcat/","usage":"hashcat [options]... hash"},{"name":"nikto","category":"Web Application Analysis","description":"Web server scanner","url":"https://www.kali.org/tools/nikto/","usage":"nikto -h <target>"},{"name":"hydra","category":"Password Attacks","description":"Parallelized login cracker","url":"https://www.kali.org/tools/hydra/","usage":"hydra [options] target service"}]
    def get_source_name(self): return "kali_docs"
    async def fetch_data(self):
        items=[]
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            for tool in self.POPULAR:
                try:
                    r=await client.get(tool["url"])
                    r.raise_for_status()
                    soup=BeautifulSoup(r.text,"html.parser")
                    content=soup.find("div", class_="content") or soup
                    ps=content.find_all("p", limit=3) if content else []
                    tool["detailed_description"]=" ".join([p.get_text(strip=True) for p in ps])[:1000]
                    codes=soup.find_all("code")
                    tool["examples"]=[c.get_text(strip=True) for c in codes[:3]]
                    items.append(dict(tool))
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"kali fetch {tool['name']} failed: {e}")
                    items.append(dict(tool))
        return items
    def normalize_item(self, raw_item):
        name=raw_item["name"]
        cat=raw_item["category"]
        tags=["kali","tool", name.lower()]
        low=cat.lower()
        if "web" in low: tags.append("web-security")
        if "password" in low: tags.append("password-cracking")
        if "wireless" in low: tags.append("wireless")
        if "information" in low: tags.append("reconnaissance")
        return {"external_id": f"kali_{name}", "content_type": "tool_doc", "title": f"{name} - {cat}", "description": raw_item["description"], "content": {"tool_name": name, "category": cat, "description": raw_item["description"], "detailed_description": raw_item.get("detailed_description",""), "usage": raw_item["usage"], "examples": raw_item.get("examples",[])}, "tags": tags, "url": raw_item["url"]}
