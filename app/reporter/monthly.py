import datetime
import logging
from typing import Optional

from app.models import Repository, Report
from app.reporter.base import BaseReporter
from app.reporter.templates import REPORT_TEMPLATES

logger = logging.getLogger(__name__)


class MonthlyReporter(BaseReporter):
    def generate(self, repo: Repository, year: Optional[int] = None, month: Optional[int] = None) -> Optional[Report]:
        today = datetime.date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month

        since = datetime.datetime(year, month, 1)
        if month == 12:
            until = datetime.datetime(year + 1, 1, 1)
        else:
            until = datetime.datetime(year, month + 1, 1)

        commits, reviews = self._get_commits_and_reviews(repo.id, since, until)
        if not commits:
            logger.info(f"No commits for {repo.name} in {year}-{month:02d}")
            return None

        context = self._build_context(commits, reviews)
        summary, suggestions = self._llm_summarize(context, "月结")

        authors = set(c.author for c in commits)
        high_risk_count = sum(1 for r in reviews if r.risk_level == "high")
        tech_debt = (
            f"本月发现 {high_risk_count} 个高风险问题，"
            f"共审核 {len(reviews)} 次提交。{summary}"
        )

        content = REPORT_TEMPLATES["monthly"].format(
            month=f"{year}-{month:02d}",
            project_name=repo.name,
            milestones=summary,
            commit_count=len(commits),
            review_count=len(reviews),
            author_count=len(authors),
            tech_debt=tech_debt,
            next_month_plan=suggestions,
        )

        report = Report(
            user_id=repo.user_id,
            repo_id=repo.id,
            report_type="monthly",
            period_start=since,
            period_end=until,
            content=content,
            status="pending",
        )
        self.db.add(report)
        self.db.commit()
        logger.info(f"Monthly report created for {repo.name}")
        return report
