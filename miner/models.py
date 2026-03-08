from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    clone_path = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")

class Commit(Base):
    __tablename__ = "commits"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    sha = Column(String, nullable=False, index=True)
    author = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    repository = relationship("Repository", back_populates="commits")
    functions = relationship("Function", back_populates="commit", cascade="all, delete-orphan")

class Function(Base):
    __tablename__ = "functions"
    
    id = Column(Integer, primary_key=True, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    start_line = Column(Integer)
    end_line = Column(Integer)
    complexity = Column(Integer)
    lines_of_code = Column(Integer)
    parameters = Column(JSON)
    return_type = Column(String)
    ast_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── stable identity hashes (added for cross-commit function tracking) ──
    # body_hash      : SHA-256[:16] of normalised function body — same after
    #                  moves, reformats, or indentation-only changes.
    # signature_hash : SHA-256[:16] of "<lang>:<name>(<params>)" — stable
    #                  across body changes; changes on rename/param edit.
    # canonical_id   : SHA-256[:16] of (signature_hash + body_hash) — the
    #                  primary cross-commit identity key used to track a
    #                  function without relying on line numbers.
    body_hash      = Column(String(16), nullable=True, index=True)
    signature_hash = Column(String(16), nullable=True, index=True)
    canonical_id   = Column(String(16), nullable=True, index=True)

    commit = relationship("Commit", back_populates="functions")


class FileMetrics(Base):
    """
    Aggregated per-file metrics computed across the full commit history.
    Stored once per (repository, file_path) and refreshed on re-analysis.
    """
    __tablename__ = "file_metrics"

    id                 = Column(Integer, primary_key=True, index=True)
    repository_id      = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    file_path          = Column(String, nullable=False, index=True)

    # --- commit-history features ---
    churn              = Column(Integer, default=0)       # total commits touching the file
    lines_added        = Column(Integer, default=0)       # cumulative insertions
    lines_deleted      = Column(Integer, default=0)       # cumulative deletions
    file_age_days      = Column(Float,   default=0.0)     # days between first & last commit
    commit_frequency   = Column(Float,   default=0.0)     # commits per day
    recent_churn       = Column(Integer, default=0)       # commits in last 90 days
    author_count       = Column(Integer, default=1)       # distinct authors
    ownership_entropy  = Column(Float,   default=0.0)     # Shannon entropy of authorship fractions
    dependency_count   = Column(Integer, default=0)       # import/require statements at HEAD

    # --- AST-derived (populated from Function records) ---
    avg_complexity     = Column(Float,   default=0.0)

    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repository = relationship("Repository")
