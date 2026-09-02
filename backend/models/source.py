from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from database import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    url = Column(String)
    scraper_module = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime)
    scrape_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
