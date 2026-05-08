import os
import datetime
from git import Repo, GitCommandError
from app.config import settings
from sqlalchemy.orm import Session
from app.models import Repository, Commit, Review


class GitFetcher:
    def __init__(self, db: Session):
        self.db = db
        self.work_dir = settings.git_work_dir
        os.makedirs(self.work_dir, exist_ok=True)

    def _get_repo_path(self, repo_id: int, repo_name: str) -> str:
        return os.path.join(self.work_dir, f"{repo_id}_{repo_name}")

    def _build_authed_url(self, git_url: str, token: str) -> str:
        if token:
            return git_url.replace("https://", f"https://oauth2:{token}@")
        return git_url

    def clone_or_pull(self, repo: Repository) -> list[Commit]:
        local_path = self._get_repo_path(repo.id, repo.name)
        authed_url = self._build_authed_url(repo.git_url, repo.git_token)

        if os.path.exists(local_path):
            git_repo = Repo(local_path)
            origin = git_repo.remotes.origin
            origin.pull()
        else:
            git_repo = Repo.clone_from(authed_url, local_path)

        return self._get_new_commits(git_repo, repo)

    def _get_new_commits(self, git_repo: Repo, repo: Repository) -> list[Commit]:
        new_commits = []
        last_commit = (
            self.db.query(Commit)
            .filter(Commit.repo_id == repo.id)
            .order_by(Commit.committed_at.desc())
            .first()
        )

        for c in git_repo.iter_commits(rev=repo.branch):
            if last_commit and c.committed_datetime <= last_commit.committed_at:
                break
            commit = Commit(
                repo_id=repo.id,
                commit_hash=c.hexsha,
                author=str(c.author),
                message=c.message.strip(),
                diff_content=self._get_diff(git_repo, c),
                committed_at=c.committed_datetime,
            )
            self.db.add(commit)
            self.db.flush()
            new_commits.append(commit)

        repo.last_fetched_at = datetime.datetime.utcnow()
        self.db.commit()
        return new_commits

    def _get_diff(self, git_repo: Repo, commit) -> str:
        if not commit.parents:
            # Initial commit — list files instead of diff
            files = [blob.path for blob in commit.tree.traverse() if blob.type == "blob"]
            return f"初始提交，共 {len(files)} 个文件：\n" + "\n".join(files)
        diff = commit.parents[0].diff(commit, create_patch=True)
        lines = []
        for d in diff:
            if d.a_path:
                lines.append(f"--- a/{d.a_path}")
            if d.b_path:
                lines.append(f"+++ b/{d.b_path}")
            if d.diff:
                lines.append(d.diff.decode("utf-8", errors="replace"))
        return "\n".join(lines)
