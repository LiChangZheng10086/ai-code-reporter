import datetime
import logging
from typing import Optional

from app.models import Repository, Report
from app.reporter.base import BaseReporter
from app.reporter.templates import REPORT_TEMPLATES

logger = logging.getLogger(__name__)


class DailyReporter(BaseReporter):
    def generate(self, repo: Repository, date: Optional[datetime.date] = None) -> Optional[Report]:
        if date is None:
            date = datetime.date.today()
        since = datetime.datetime.combine(date, datetime.time.min)
        until = datetime.datetime.combine(date, datetime.time.max)

        commits, reviews = self._get_commits_and_reviews(repo.id, since, until)
        if not commits:
            logger.info(f"No commits for {repo.name} on {date}")
            return None

        context = self._build_context(commits, reviews)
        summary, suggestions = self._llm_summarize(context, "日结")

        authors = set(c.author for c in commits)
        issues_text = "\n".join(
            f"- [{r.risk_level}] {r.issues[0]['description'] if r.issues else r.review_content[:100]}"
            for r in reviews if r.issues
        ) if reviews else "无"

        content = REPORT_TEMPLATES["daily"].format(
            date=date.isoformat(),
            project_name=repo.name,
            commit_count=len(commits),
            authors=", ".join(authors),
            file_count=sum(len(c.diff_content or "") for c in commits),
            review_summary=summary,
            issues=issues_text or "无重大问题",
            summary=suggestions,
        )

        report = Report(
            user_id=repo.user_id,
            repo_id=repo.id,
            report_type="daily",
            period_start=since,
            period_end=until,
            content=content,
            status="pending",
        )
        self.db.add(report)
        self.db.commit()
        logger.info(f"Daily report created for {repo.name}")
        return report
