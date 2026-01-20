from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class RepositoryCreate(BaseModel):
    url: str

class RepositoryResponse(BaseModel):
    id: int
    url: str
    name: str
    owner: str
    status: str
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
