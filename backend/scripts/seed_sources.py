"""Seed initial sources into database (raw SQL, no ORM needed)."""
import asyncio
import os
import sys

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://scraper_user:password@postgres:5432/cybersec_scraper"
)
# asyncpg needs without driver prefix
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def seed_sources():
    """Seed initial sources via direct SQL."""

    sources = [
        ("owasp", "OWASP Top 10", "https://owasp.org/Top10/", "scrapers.owasp_scraper.OWASPScraper", True),
        ("mitre_attack", "MITRE ATT&CK", "https://attack.mitre.org", "scrapers.mitre_attack_scraper.MITREAttackScraper", True),
        ("github_payloads", "GitHub Payloads", "https://github.com", "scrapers.github_scraper.GitHubScraper", True),
        ("kali_docs", "Kali Linux Tools", "https://www.kali.org/tools/", "scrapers.kali_docs_scraper.KaliDocsScraper", True),
    ]

    # Parse DATABASE_URL for asyncpg
    # asyncpg accepts DSN string directly
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"✗ Failed to connect to DB: {e}")
        print(f"  DATABASE_URL={DATABASE_URL}")
        sys.exit(1)

    try:
        for name, display_name, url, scraper_module, enabled in sources:
            exists = await conn.fetchval("SELECT id FROM sources WHERE name = $1", name)
            if exists:
                print(f"Source '{name}' already exists, skipping...")
                continue

            await conn.execute(
                """
                INSERT INTO sources (name, display_name, url, scraper_module, enabled)
                VALUES ($1, $2, $3, $4, $5)
                """,
                name, display_name, url, scraper_module, enabled
            )
            print(f"Added source: {display_name}")

        print("\n✓ Sources seeded successfully!")

    except Exception as e:
        print(f"\n✗ Failed to seed sources: {e}")
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_sources())
