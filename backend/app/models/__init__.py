import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return uuid.uuid4()


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    query = Column(Text, nullable=False)
    query_model = Column(JSONB)
    geography = Column(JSONB)
    languages = Column(ARRAY(String))
    audience = Column(ARRAY(String))
    intent = Column(ARRAY(String))
    source_types = Column(ARRAY(String))
    scoring_profile = Column(String(50), default="lead_generation")
    max_discovery_depth = Column(Integer, default=3)
    max_sources = Column(Integer, default=500)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    runs = relationship("DiscoveryRun", back_populates="project", cascade="all, delete-orphan")
    scores = relationship("SourceScore", back_populates="project", cascade="all, delete-orphan")
    reviews = relationship("SourceReview", back_populates="project", cascade="all, delete-orphan")


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending")
    current_stage = Column(String(50))
    progress = Column(Float, default=0.0)
    stats = Column(JSONB, default={})
    error = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    project = relationship("Project", back_populates="runs")
    events = relationship("DiscoveryEvent", back_populates="run", cascade="all, delete-orphan")
    variants = relationship("QueryVariant", back_populates="run", cascade="all, delete-orphan")
    candidates = relationship("DiscoveryCandidate", back_populates="run", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    telegram_id = Column(Integer, unique=True)
    username = Column(String(255))
    title = Column(String(512))
    description = Column(Text)
    source_type = Column(String(20))
    member_count = Column(Integer)
    linked_chat_id = Column(Integer)
    has_pinned_messages = Column(Boolean, default=False)
    pinned_messages = Column(JSONB, default=[])
    recent_messages = Column(JSONB, default=[])
    recent_messages_fetched_at = Column(DateTime(timezone=True))

    topic_analysis = Column(JSONB)
    language_analysis = Column(JSONB)
    geography_analysis = Column(JSONB)
    audience_analysis = Column(JSONB)
    intent_analysis = Column(JSONB)
    activity_analysis = Column(JSONB)
    commercial_analysis = Column(JSONB)

    embedding = Column(ARRAY(Float))
    fts_vector = Column(TSVECTOR)

    status = Column(String(30), default="discovered")
    first_seen_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_analyzed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    scores = relationship("SourceScore", back_populates="source", cascade="all, delete-orphan")
    reviews = relationship("SourceReview", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_sources_telegram_id", "telegram_id"),
        Index("idx_sources_username", "username"),
        Index("idx_sources_status", "status"),
        Index("idx_sources_source_type", "source_type"),
    )


class SourceScore(Base):
    __tablename__ = "source_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    discovery_run_id = Column(UUID(as_uuid=True), ForeignKey("discovery_runs.id", ondelete="CASCADE"), nullable=False)
    total_score = Column(Float, nullable=False)
    breakdown = Column(JSONB, nullable=False)
    scoring_profile = Column(String(50))
    scored_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    source = relationship("Source", back_populates="scores")
    project = relationship("Project", back_populates="scores")

    __table_args__ = (
        UniqueConstraint("source_id", "project_id", "discovery_run_id"),
        Index("idx_source_scores_project", "project_id"),
        Index("idx_source_scores_total", "total_score"),
    )


class SourceLink(Base):
    __tablename__ = "source_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    target_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    edge_type = Column(String(20), nullable=False)
    confidence = Column(Float, default=0.5)
    context = Column(Text)
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    link_metadata = Column(JSONB, default={})

    __table_args__ = (
        UniqueConstraint("source_id", "target_source_id", "edge_type"),
        Index("idx_source_links_source", "source_id"),
        Index("idx_source_links_target", "target_source_id"),
    )


class QueryVariant(Base):
    __tablename__ = "query_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    discovery_run_id = Column(UUID(as_uuid=True), ForeignKey("discovery_runs.id", ondelete="CASCADE"), nullable=False)
    variant_text = Column(Text, nullable=False)
    variant_type = Column(String(30))
    priority = Column(Integer, default=5)
    executed = Column(Boolean, default=False)
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    run = relationship("DiscoveryRun", back_populates="variants")


class DiscoveryCandidate(Base):
    __tablename__ = "discovery_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    discovery_run_id = Column(UUID(as_uuid=True), ForeignKey("discovery_runs.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(20))
    username = Column(String(255))
    telegram_id = Column(Integer)
    invite_link = Column(Text)
    url = Column(Text)
    title = Column(Text)
    discovered_via = Column(String(50))
    discovery_query = Column(Text)
    confidence = Column(Float, default=0.5)
    raw_data = Column(JSONB, default={})
    resolved = Column(Boolean, default=False)
    resolved_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    run = relationship("DiscoveryRun", back_populates="candidates")

    __table_args__ = (
        Index("idx_candidates_run", "discovery_run_id"),
        Index("idx_candidates_resolved", "resolved"),
    )


class ScoringProfile(Base):
    __tablename__ = "scoring_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name = Column(String(50), unique=True, nullable=False)
    weights = Column(JSONB, nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class SourceReview(Base):
    __tablename__ = "source_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(20), nullable=False)
    reason = Column(Text)
    reviewed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    source = relationship("Source", back_populates="reviews")
    project = relationship("Project", back_populates="reviews")


class DiscoveryEvent(Base):
    __tablename__ = "discovery_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    discovery_run_id = Column(UUID(as_uuid=True), ForeignKey("discovery_runs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    run = relationship("DiscoveryRun", back_populates="events")

    __table_args__ = (
        Index("idx_events_run", "discovery_run_id"),
    )
