from pydantic import BaseModel, EmailStr, field_validator
from utils.url_validation import validate_repo_url
from datetime import datetime
from typing import Optional, List

# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Repository Schemas
class RepositoryCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        # Allowlist (SSRF): only https://<allowed host>/owner/repo
        return validate_repo_url(v)

class RepositoryResponse(BaseModel):
    id: int
    url: str
    name: str
    owner: str
    status: str
    failed_reason: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class CommitResponse(BaseModel):
    id: int
    sha: str
    author: Optional[str]
    message: Optional[str]
    timestamp: Optional[datetime]
    processed: bool
    
    class Config:
        from_attributes = True

class FunctionResponse(BaseModel):
    id: int
    name: str
    file_path: str
    start_line: Optional[int]
    end_line: Optional[int]
    complexity: Optional[int]
    lines_of_code: Optional[int]
    
    class Config:
        from_attributes = True

class RepositoryDetail(RepositoryResponse):
    commits: List[CommitResponse] = []

class CommitDetail(CommitResponse):
    functions: List[FunctionResponse] = []
