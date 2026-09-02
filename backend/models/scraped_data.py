from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from database import Base


class ScrapedData(Base):
    __tablename__ = "scraped_data"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(500), nullable=False, index=True)
    content_type = Column(String(100), nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    content = Column(JSONB, nullable=False)
    tags = Column(ARRAY(String), default=list)
    severity = Column(String(50))
    url = Column(Text)
    content_hash = Column(String(64), nullable=False)
    first_seen_at = Column(DateTime, server_default=func.now())
    last_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    metadata_json = Column("metadata", JSONB)
