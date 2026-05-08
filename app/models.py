import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from app.database import Base


class UserConfig(Base):
    __tablename__ = "user_configs"

    id = Column(Integer, primary_key=True, index=True)
    tg_bot_token = Column(String(255), nullable=False)
    tg_user_id = Column(String(255), nullable=False, unique=True)
    active_project_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_configs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    git_url = Column(String(512), nullable=False)
    git_token = Column(String(512), nullable=False)
    branch = Column(String(255), default="main")
    is_active = Column(Integer, default=1)
    last_fetched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    commit_hash = Column(String(64), nullable=False, unique=True)
    author = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    diff_content = Column(Text, nullable=True)
    committed_at = Column(DateTime, nullable=False)
    fetched_at = Column(DateTime, default=datetime.datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id"), nullable=False)
    risk_level = Column(String(16), default="low")
    score = Column(Integer, nullable=True)
    issues = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    review_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_configs.id"), nullable=False)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    report_type = Column(String(16), nullable=False)  # daily / weekly / monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(16), default="pending")  # pending / sent / failed
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_configs.id"), nullable=False)
    session_id = Column(String(64), nullable=False)
    role = Column(String(16), nullable=False)  # user / assistant
    message = Column(Text, nullable=False)
    repo_context = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
