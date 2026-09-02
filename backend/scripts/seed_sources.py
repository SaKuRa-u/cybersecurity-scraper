"""Seed initial sources into database."""
import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.source import Source

# DATABASE_URL from env, fallback to default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://scraper_user:password@postgres:5432/cybersec_scraper"
)
# Use async driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


async def seed_sources():
    """Seed initial sources into database."""

    engine = create_async_engine(DATABASE_URL)

    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    sources = [
        {
            "name": "owasp",
            "display_name": "OWASP Top 10",
            "url": "https://owasp.org/Top10/",
            "scraper_module": "scrapers.owasp_scraper.OWASPScraper",
            "enabled": True
        },
        {
            "name": "mitre_attack",
            "display_name": "MITRE ATT&CK",
            "url": "https://attack.mitre.org",
            "scraper_module": "scrapers.mitre_attack_scraper.MITREAttackScraper",
            "enabled": True
        },
        {
            "name": "github_payloads",
            "display_name": "GitHub Payloads",
            "url": "https://github.com",
            "scraper_module": "scrapers.github_scraper.GitHubScraper",
            "enabled": True
        },
        {
            "name": "kali_docs",
            "display_name": "Kali Linux Tools",
            "url": "https://www.kali.org/tools/",
            "scraper_module": "scrapers.kali_docs_scraper.KaliDocsScraper",
            "enabled": True
        }
    ]

    async with AsyncSessionLocal() as session:
        try:
            for source_data in sources:
                result = await session.execute(
                    select(Source).where(Source.name == source_data["name"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"Source '{source_data['name']}' already exists, skipping...")
                    continue

                source = Source(**source_data)
                session.add(source)
                print(f"Added source: {source_data['display_name']}")

            await session.commit()
            print("\n✓ Sources seeded successfully!")

        except Exception as e:
            print(f"\n✗ Failed to seed sources: {e}")
            await session.rollback()
            sys.exit(1)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_sources())
