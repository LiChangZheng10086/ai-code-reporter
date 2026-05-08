from pydantic import BaseModel
from typing import Optional, list
import datetime


class UserConfigCreate(BaseModel):
    tg_bot_token: str
    tg_user_id: str


class RepositoryCreate(BaseModel):
    name: str
    git_url: str
    git_token: str
    branch: str = "main"


class RepositoryOut(BaseModel):
    id: int
    name: str
    git_url: str
    branch: str
    is_active: int
    last_fetched_at: Optional[datetime.datetime]

    model_config = {"from_attributes": True}


class CommitOut(BaseModel):
    id: int
    repo_id: int
    commit_hash: str
    author: str
    message: str
    committed_at: datetime.datetime

    model_config = {"from_attributes": True}


class ReviewOut(BaseModel):
    id: int
    commit_id: int
    risk_level: str
    score: Optional[int]
    issues: list
    suggestions: list
    review_content: str

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: int
    report_type: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    content: str
    status: str

    model_config = {"from_attributes": True}
