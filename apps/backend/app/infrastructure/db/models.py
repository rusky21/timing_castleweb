from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, JSON,
    ForeignKey, Table, Column, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.domain.entities import LeadStatus, CaseCategory


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Association Table for Many-to-Many: Case <-> Tag
case_tags = Table(
    "case_tags",
    Base.metadata,
    Column("case_id", Integer, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status
    status: Mapped[LeadStatus] = mapped_column(
        SQLEnum(LeadStatus),
        default=LeadStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Security & Metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    
    # GeoIP & Enrichment
    geo_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    geo_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    geo_isp: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    
    # Operations
    handled_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    cases: Mapped[List["Case"]] = relationship(
        "Case", secondary=case_tags, back_populates="tags", lazy="selectin"
    )


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    client_name: Mapped[str] = mapped_column(String(150), nullable=False)
    year: Mapped[int] = mapped_column(Integer, default=2026, nullable=False)
    category: Mapped[CaseCategory] = mapped_column(
        SQLEnum(CaseCategory), default=CaseCategory.SAAS, nullable=False, index=True
    )
    
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    solution_fe: Mapped[str] = mapped_column(Text, nullable=False)
    solution_be: Mapped[str] = mapped_column(Text, nullable=False)
    results_summary: Mapped[str] = mapped_column(Text, nullable=False)
    
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    live_url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    gallery_images: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    client_review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_author: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    tags: Mapped[List[Tag]] = relationship(
        Tag, secondary=case_tags, back_populates="cases", lazy="selectin"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Blacklist(Base):
    __tablename__ = "blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    contact: Mapped[Optional[str]] = mapped_column(String(200), unique=True, nullable=True, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
