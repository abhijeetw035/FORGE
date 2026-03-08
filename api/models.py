from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    repositories = relationship("Repository", back_populates="owner_user", cascade="all, delete-orphan")

class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable for migration compatibility
    url = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    owner = Column(String, nullable=False)  # keeping this for backward compatibility (GitHub repo owner)
    clone_path = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner_user = relationship("User", back_populates="repositories")
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
    
    commit = relationship("Commit", back_populates="functions")


class FileMetrics(Base):
    """
    Aggregated per-file metrics computed across the full commit history.
    Populated by the miner; read by the API for risk prediction.
    """
    __tablename__ = "file_metrics"

    id                 = Column(Integer, primary_key=True, index=True)
    repository_id      = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    file_path          = Column(String, nullable=False, index=True)

    # commit-history features
    churn              = Column(Integer, default=0)
    lines_added        = Column(Integer, default=0)
    lines_deleted      = Column(Integer, default=0)
    file_age_days      = Column(Float,   default=0.0)
    commit_frequency   = Column(Float,   default=0.0)
    recent_churn       = Column(Integer, default=0)
    author_count       = Column(Integer, default=1)
    ownership_entropy  = Column(Float,   default=0.0)
    dependency_count   = Column(Integer, default=0)

    # AST-derived (avg complexity across all functions in this file)
    avg_complexity     = Column(Float,   default=0.0)

    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repository = relationship("Repository")
