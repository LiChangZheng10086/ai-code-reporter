import datetime
import logging
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.orm import Session

from app.llm import get_llm
from app.models import Commit, Review, Report, Repository
from app.git_monitor.parser import GitParser
from app.reporter.templates import REPORT_TEMPLATES

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "你是一个专业的软件工程报告撰写专家，擅长总结代码变更和团队进展。"


class BaseReporter:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm(temperature=0.3)
        self.parser = GitParser(db)

    def _get_commits_and_reviews(self, repo_id: int, since, until) -> tuple[list, list]:
        commits = self.parser.get_commits_since(repo_id, since, until)
        commit_ids = [c.id for c in commits]
        reviews = (
            self.db.query(Review)
            .filter(Review.commit_id.in_(commit_ids))
            .all()
        ) if commit_ids else []
        return commits, reviews

    def _build_context(self, commits: list[Commit], reviews: list[Review]) -> str:
        review_map = {r.commit_id: r for r in reviews}
        lines = []
        for c in commits:
            review = review_map.get(c.id)
            risk = review.risk_level if review else "unreviewed"
            issues_count = len(review.issues) if review and review.issues else 0
            lines.append(
                f"- [{risk}] {c.committed_at.strftime('%m-%d %H:%M')} "
                f"{c.author}: {c.message[:80]}"
                f"{' (' + str(issues_count) + ' issues)' if issues_count else ''}"
            )
        return "\n".join(lines)

    def _llm_summarize(self, context: str, report_type: str) -> tuple[str, str]:
        prompt = (
            f"以下是一个Git仓库在{report_type}周期内的提交和审核记录，"
            f"请生成一份{report_type}总结和针对性的改进建议：\n\n{context}"
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = self.llm.invoke(messages)
        text = response.content
        # Split into summary and suggestions
        parts = text.split("\n\n", 1)
        summary = parts[0]
        suggestions = parts[1] if len(parts) > 1 else ""
        return summary, suggestions

    def generate(self, repo: Repository, report_type: str) -> Optional[Report]:
        raise NotImplementedError
