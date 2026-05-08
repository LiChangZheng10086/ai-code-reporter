from typing import Optional
from sqlalchemy.orm import Session
from app.models import Repository, Commit


class GitParser:
    def __init__(self, db: Session):
        self.db = db

    def get_repo_by_id(self, repo_id: int) -> Optional[Repository]:
        return self.db.query(Repository).filter(Repository.id == repo_id).first()

    def get_commits_since(self, repo_id: int, since, until=None):
        query = self.db.query(Commit).filter(
            Commit.repo_id == repo_id,
            Commit.committed_at >= since,
        )
        if until:
            query = query.filter(Commit.committed_at <= until)
        return query.order_by(Commit.committed_at.asc()).all()

    def get_commit_by_hash(self, repo_id: int, commit_hash: str) -> Optional[Commit]:
        return (
            self.db.query(Commit)
            .filter(Commit.repo_id == repo_id, Commit.commit_hash == commit_hash)
            .first()
        )
