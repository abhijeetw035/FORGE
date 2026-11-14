from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON, Float, Index, UniqueConstraint
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
    # SHA of the last commit that was fully indexed; used for incremental re-analysis
    last_indexed_sha = Column(String, nullable=True)
    # Human-readable reason shown in the UI when status == "failed"
    failed_reason = Column(Text, nullable=True)
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
    # True once this commit's raw file-change facts are stored in file_changes
    # (written in the same transaction as the commit itself).
    changes_recorded = Column(Boolean, nullable=False, default=False, server_default='false')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Idempotent writes: the same commit can never be stored twice for a repo.
    __table_args__ = (
        UniqueConstraint('repository_id', 'sha', name='uq_commits_repository_sha'),
    )

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

    # stable identity tracking fields
    body_hash      = Column(String(16), nullable=True, index=True)
    signature_hash = Column(String(16), nullable=True, index=True)
    canonical_id   = Column(String(16), nullable=True, index=True)
    qualified_name = Column(String, nullable=True)
    change_type    = Column(String(16), nullable=True)
    similarity     = Column(Float, nullable=True)

    __table_args__ = (
        Index('ix_functions_file_path_qualified_name', 'file_path', 'qualified_name'),
        UniqueConstraint('commit_id', 'file_path', 'qualified_name', 'start_line', 'body_hash', name='uq_functions_identity'),
    )

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

    # --- size ---
    loc                = Column(Integer, nullable=False, default=0, server_default='0')  # non-blank lines at HEAD

    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repository = relationship("Repository")


class FileChange(Base):
    """
    Raw per-commit, per-file facts. file_metrics is recomputed from these with
    SQL on every run, so metrics are exact and a crash/resume cannot lose history.
    """
    __tablename__ = "file_changes"

    id            = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    commit_id     = Column(Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False)
    file_path     = Column(String, nullable=False)
    author_email  = Column(String, nullable=False)    # lowercased, .mailmap-resolved
    committed_at  = Column(DateTime, nullable=False)  # UTC, naive
    lines_added   = Column(Integer, nullable=False, default=0)
    lines_deleted = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint('commit_id', 'file_path', name='uq_file_changes_commit_file'),
        Index('ix_file_changes_repo_file', 'repository_id', 'file_path'),
    )
