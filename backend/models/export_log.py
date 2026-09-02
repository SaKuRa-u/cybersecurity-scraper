from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from database import Base


class ExportLog(Base):
    __tablename__ = "export_logs"

    id = Column(Integer, primary_key=True, index=True)
    scrape_session_id = Column(Integer, ForeignKey("scrape_sessions.id", ondelete="CASCADE"))
    exported_at = Column(DateTime, server_default=func.now())
    items_exported = Column(Integer)
    export_file_path = Column(Text)
    export_format = Column(String(50))
    status = Column(String(50))
    error_message = Column(Text)
