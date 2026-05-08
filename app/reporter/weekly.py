import datetime
import logging
from typing import Optional

from app.models import Repository, Report
from app.reporter.base import BaseReporter
from app.reporter.templates import REPORT_TEMPLATES

logger = logging.getLogger(__name__)


class WeeklyReporter(BaseReporter):
    def generate(self, repo: Repository, year: Optional[int] = None, week: Optional[int] = None) -> Optional[Report]:
        today = datetime.date.today()
        if year is None:
            year = today.isocalendar()[0]
        if week is None:
            week = today.isocalendar()[1]

        since = datetime.datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u")
        until = since + datetime.timedelta(days=7)

        commits, reviews = self._get_commits_and_reviews(repo.id, since, until)
        if not commits:
            logger.info(f"No commits for {repo.name} in week {week}")
            return None

        context = self._build_context(commits, reviews)
        summary, suggestions = self._llm_summarize(context, "周结")

        authors = set(c.author for c in commits)
        pending = [
            r for r in reviews
            if r.risk_level in ("high", "medium") and r.suggestions
        ]
        pending_text = "\n".join(
            f"- [{r.risk_level}] {r.issues[0]['description'] if r.issues else ''}"
            for r in pending
        ) if pending else "无遗留问题"

        content = REPORT_TEMPLATES["weekly"].format(
            week_range=f"{since.date()} ~ {until.date()}",
            project_name=repo.name,
            commit_count=len(commits),
            authors=", ".join(authors),
            review_count=len(reviews),
            quality_trend=summary,
            pending_issues=pending_text,
            suggestions=suggestions,
        )

        report = Report(
            user_id=repo.user_id,
            repo_id=repo.id,
            report_type="weekly",
            period_start=since,
            period_end=until,
            content=content,
            status="pending",
        )
        self.db.add(report)
        self.db.commit()
        logger.info(f"Weekly report created for {repo.name}")
        return report
