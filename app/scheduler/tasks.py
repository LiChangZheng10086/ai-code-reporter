import datetime
import json
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Repository, Report, UserConfig
from app.git_monitor.fetcher import GitFetcher
from app.reviewer.engine import CodeReviewer
from app.reporter.daily import DailyReporter
from app.reporter.weekly import WeeklyReporter
from app.reporter.monthly import MonthlyReporter

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def get_active_repos(db: Session) -> list[Repository]:
    return db.query(Repository).filter(Repository.is_active == 1).all()


async def _notify_user(db: Session, repo: Repository, commits_with_reviews: list):
    """向用户推送新提交和代码审核结果。"""
    user = db.query(UserConfig).filter(UserConfig.id == repo.user_id).first()
    if not user:
        return

    lines = [
        f"📦 {repo.name} 有新的代码提交！",
        "━━━━━━━━━━━━━━━━━",
    ]

    for commit, review in commits_with_reviews:
        lines.append("")
        lines.append(f"📝 Commit {commit.commit_hash[:8]}")
        lines.append(f"👤 提交人: {commit.author}")
        lines.append(f"💬 信息: {commit.message.strip()[:200]}")
        lines.append(f"🕐 {commit.committed_at.strftime('%m-%d %H:%M')}")

        if review:
            risk_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(review.risk_level, "⚪")
            lines.append(f"{risk_icon} 审核: 风险 {review.risk_level} | 评分 {review.score or 'N/A'}")

            if review.issues:
                text = json.dumps(review.issues, ensure_ascii=False)[:500]
                lines.append(f"⚠️ 发现的问题: {text}")
            else:
                lines.append("✅ 未发现明显问题")

            if review.suggestions:
                sugs = "; ".join(str(s)[:200] for s in review.suggestions)
                lines.append(f"💡 优化建议: {sugs[:500]}")
        else:
            lines.append("⏳ 代码审核中...")

    message = "\n".join(lines)

    # Lazy import to avoid circular dependency with main.py
    from app.main import bot as bot_instance
    if bot_instance and bot_instance.application:
        try:
            await bot_instance.application.bot.send_message(
                chat_id=user.tg_user_id,
                text=message,
            )
        except Exception as e:
            logger.error(f"Failed to send notification to user {user.id}: {e}")


async def fetch_and_review():
    """
    拉取所有活跃仓库的最新提交并执行代码审核，
    有更新时向用户推送通知。
    """
    db = SessionLocal()
    try:
        repos = get_active_repos(db)
        fetcher = GitFetcher(db)
        reviewer = CodeReviewer(db)

        for repo in repos:
            try:
                new_commits = fetcher.clone_or_pull(repo)
                if not new_commits:
                    continue

                logger.info(f"Fetched {len(new_commits)} new commits for {repo.name}")
                notification_commits = []

                for commit in new_commits:
                    try:
                        review = reviewer.review(commit)
                        notification_commits.append((commit, review))
                    except Exception as e:
                        logger.error(f"Review failed for commit {commit.id}: {e}")
                        notification_commits.append((commit, None))

                await _notify_user(db, repo, notification_commits)

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

    # Git fetch & review: every 1 minute (for testing)
    scheduler.add_job(fetch_and_review, "interval", minutes=1, id="fetch_review")

    # Daily report: 18:00
    scheduler.add_job(generate_daily_report, "cron", hour=18, minute=0, id="daily_report")

    # Weekly report: Monday 09:00
    scheduler.add_job(generate_weekly_report, "cron", day_of_week="mon", hour=9, minute=0, id="weekly_report")

    # Monthly report: 1st day 09:00
    scheduler.add_job(generate_monthly_report, "cron", day=1, hour=9, minute=0, id="monthly_report")

    scheduler.start()
    logger.info("Scheduler started: fetch every 30min, daily 18:00, weekly Mon 09:00, monthly 1st 09:00")
