import datetime
import re
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Commit, Review, Report
from app.bot.project_manager import ProjectManager


def _parse_time_range(time_range: str) -> tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    time_range = time_range.strip()

    if "昨天" in time_range:
        start = (now - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0)
        end = start.replace(hour=23, minute=59, second=59)
        return start, end
    elif "今天" in time_range or "今日" in time_range:
        start = now.replace(hour=0, minute=0, second=0)
        return start, now
    elif "本周" in time_range or "这周" in time_range:
        start = (now - datetime.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
        return start, now
    elif "上周" in time_range:
        start = (now - datetime.timedelta(days=now.weekday() + 7)).replace(hour=0, minute=0, second=0)
        end = (start + datetime.timedelta(days=7)).replace(hour=0, minute=0, second=0)
        return start, end
    elif "本月" in time_range or "这个月" in time_range:
        start = now.replace(day=1, hour=0, minute=0, second=0)
        return start, now
    elif "上月" in time_range or "上个月" in time_range:
        month = now.month - 1
        year = now.year
        if month == 0:
            month = 12
            year -= 1
        start = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0)
        end = now.replace(day=1, hour=0, minute=0, second=0)
        return start, end
    return None, None


class DataRetriever:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.pm = ProjectManager(db)

    def query_commits(self, repo_id: Optional[int], time_range: str = "", keyword: str = "") -> list[Commit]:
        since, until = _parse_time_range(time_range)
        query = self.db.query(Commit)

        if repo_id:
            query = query.filter(Commit.repo_id == repo_id)
        else:
            repos = self.pm.get_user_repositories(self.user_id)
            repo_ids = [r.id for r in repos]
            if not repo_ids:
                return []
            query = query.filter(Commit.repo_id.in_(repo_ids))

        if since:
            query = query.filter(Commit.committed_at >= since)
        if until:
            query = query.filter(Commit.committed_at <= until)
        if keyword:
            query = query.filter(
                Commit.author.contains(keyword) | Commit.message.contains(keyword)
            )

        return query.order_by(Commit.committed_at.desc()).limit(20).all()

    def query_reviews(self, repo_id: Optional[int], time_range: str = "") -> list[Review]:
        since, until = _parse_time_range(time_range)
        query = self.db.query(Review).join(Commit, Review.commit_id == Commit.id)

        if repo_id:
            query = query.filter(Commit.repo_id == repo_id)
        elif repo_id is None:
            repos = self.pm.get_user_repositories(self.user_id)
            repo_ids = [r.id for r in repos]
            if repo_ids:
                query = query.filter(Commit.repo_id.in_(repo_ids))

        if since:
            query = query.filter(Commit.committed_at >= since)
        if until:
            query = query.filter(Commit.committed_at <= until)

        return query.order_by(Review.created_at.desc()).limit(20).all()

    def query_reports(self, repo_id: Optional[int], report_type: str = "") -> list[Report]:
        query = self.db.query(Report).filter(Report.user_id == self.user_id)
        if repo_id:
            query = query.filter(Report.repo_id == repo_id)
        if report_type:
            query = query.filter(Report.report_type == report_type)
        return query.order_by(Report.created_at.desc()).limit(5).all()

    def query_reports_by_period(
        self, repo_id: Optional[int], since: datetime.datetime, until: datetime.datetime, report_type: str = ""
    ) -> list[Report]:
        """按时间范围查找已生成的报告。"""
        query = self.db.query(Report).filter(
            Report.user_id == self.user_id,
            Report.period_start >= since,
            Report.period_end <= until,
        )
        if repo_id:
            query = query.filter(Report.repo_id == repo_id)
        if report_type:
            query = query.filter(Report.report_type == report_type)
        return query.order_by(Report.created_at.desc()).limit(5).all()
