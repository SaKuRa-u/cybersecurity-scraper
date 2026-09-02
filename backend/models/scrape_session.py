from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from database import Base


class ScrapeSession(Base):
    __tablename__ = "scrape_sessions"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(255), unique=True)
    status = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    items_found = Column(Integer, default=0)
    items_inserted = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_deleted = Column(Integer, default=0)
    error_message = Column(Text)
    triggered_by = Column(String(100), default="manual")
