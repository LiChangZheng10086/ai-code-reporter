import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models import UserConfig, Repository

logger = logging.getLogger(__name__)


class ProjectManager:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(self, tg_user_id: str, tg_bot_token: str) -> UserConfig:
        user = self.db.query(UserConfig).filter(UserConfig.tg_user_id == tg_user_id).first()
        if not user:
            user = UserConfig(tg_user_id=tg_user_id, tg_bot_token=tg_bot_token)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        else:
            user.tg_bot_token = tg_bot_token
            self.db.commit()
        return user

    def add_repository(self, user_id: int, name: str, git_url: str, git_token: str, branch: str = "main") -> Repository:
        repo = Repository(
            user_id=user_id,
            name=name,
            git_url=git_url,
            git_token=git_token,
            branch=branch,
            is_active=1,
        )
        self.db.add(repo)
        self.db.commit()
        self.db.refresh(repo)

        # Set as active if first project
        user = self.db.query(UserConfig).filter(UserConfig.id == user_id).first()
        if user and user.active_project_id is None:
            user.active_project_id = repo.id
            self.db.commit()

        return repo

    def get_user_repositories(self, user_id: int) -> list[Repository]:
        return (
            self.db.query(Repository)
            .filter(Repository.user_id == user_id, Repository.is_active == 1)
            .all()
        )

    def switch_project(self, user_id: int, repo_id: int) -> bool:
        repo = (
            self.db.query(Repository)
            .filter(Repository.id == repo_id, Repository.user_id == user_id, Repository.is_active == 1)
            .first()
        )
        if not repo:
            return False
        user = self.db.query(UserConfig).filter(UserConfig.id == user_id).first()
        if user:
            user.active_project_id = repo.id
            self.db.commit()
            return True
        return False

    def remove_repository(self, user_id: int, repo_id: int) -> bool:
        repo = (
            self.db.query(Repository)
            .filter(Repository.id == repo_id, Repository.user_id == user_id)
            .first()
        )
        if not repo:
            return False
        repo.is_active = 0
        user = self.db.query(UserConfig).filter(UserConfig.id == user_id).first()
        if user and user.active_project_id == repo.id:
            other = (
                self.db.query(Repository)
                .filter(Repository.user_id == user_id, Repository.is_active == 1)
                .first()
            )
            user.active_project_id = other.id if other else None
        self.db.commit()
        return True

    def get_active_project(self, user_id: int) -> Optional[Repository]:
        user = self.db.query(UserConfig).filter(UserConfig.id == user_id).first()
        if not user or not user.active_project_id:
            return None
        return (
            self.db.query(Repository)
            .filter(Repository.id == user.active_project_id, Repository.is_active == 1)
            .first()
        )
