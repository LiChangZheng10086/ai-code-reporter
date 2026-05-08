import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Repository, Report
from app.git_monitor.fetcher import GitFetcher
from app.reviewer.engine import CodeReviewer
from app.reporter.daily import DailyReporter
from app.reporter.weekly import WeeklyReporter
from app.reporter.monthly import MonthlyReporter

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def get_active_repos(db: Session) -> list[Repository]:
    return db.query(Repository).filter(Repository.is_active == 1).all()


async def fetch_and_review():
    """
    定时拉取所有活跃仓库的最新提交并执行代码审核。
    建议每 30 分钟执行一次。
    """
    db = SessionLocal()
    try:
        repos = get_active_repos(db)
        fetcher = GitFetcher(db)
        reviewer = CodeReviewer(db)

        for repo in repos:
            try:
                new_commits = fetcher.clone_or_pull(repo)
                logger.info(f"Fetched {len(new_commits)} new commits for {repo.name}")
                for commit in new_commits:
                    try:
                        reviewer.review(commit)
                    except Exception as e:
                        logger.error(f"Review failed for commit {commit.id}: {e}")
            except Exception as e:
                logger.error(f"Fetch failed for {repo.name}: {e}")
    finally:
        db.close()


async def generate_daily_report():
    """每天 18:00 生成日结报告"""
    db = SessionLocal()
    try:
        repos = get_active_repos(db)
        reporter = DailyReporter(db)
        for repo in repos:
            try:
                today = datetime.date.today()
                # Check if already generated today
                existing = (
                    db.query(Report)
                    .filter(
                        Report.repo_id == repo.id,
                        Report.report_type == "daily",
                        Report.period_start >= datetime.datetime.combine(today, datetime.time.min),
                    )
                    .first()
                )
                if existing:
                    logger.info(f"Daily report already exists for {repo.name}")
                    continue
                reporter.generate(repo, today)
            except Exception as e:
                logger.error(f"Daily report failed for {repo.name}: {e}")
    finally:
        db.close()


async def generate_weekly_report():
    """每周一 09:00 生成周结报告"""
    db = SessionLocal()
    try:
        repos = get_active_repos(db)
        reporter = WeeklyReporter(db)
        for repo in repos:
            try:
                reporter.generate(repo)
            except Exception as e:
                logger.error(f"Weekly report failed for {repo.name}: {e}")
    finally:
        db.close()


async def generate_monthly_report():
    """每月 1 号生成月结报告"""
    db = SessionLocal()
    try:
        repos = get_active_repos(db)
        reporter = MonthlyReporter(db)
        for repo in repos:
            try:
                reporter.generate(repo)
            except Exception as e:
                logger.error(f"Monthly report failed for {repo.name}: {e}")
    finally:
        db.close()


def start_scheduler():
    init_db()

    # Git fetch & review: every 30 minutes
    scheduler.add_job(fetch_and_review, "interval", minutes=30, id="fetch_review")

    # Daily report: 18:00
    scheduler.add_job(generate_daily_report, "cron", hour=18, minute=0, id="daily_report")

    # Weekly report: Monday 09:00
    scheduler.add_job(generate_weekly_report, "cron", day_of_week="mon", hour=9, minute=0, id="weekly_report")

    # Monthly report: 1st day 09:00
    scheduler.add_job(generate_monthly_report, "cron", day=1, hour=9, minute=0, id="monthly_report")

    scheduler.start()
    logger.info("Scheduler started: fetch every 30min, daily 18:00, weekly Mon 09:00, monthly 1st 09:00")
