import datetime
from sqlalchemy.orm import Session
from app.models import ConversationHistory


class ConversationMemory:
    def __init__(self, db: Session, user_id: int, max_history: int = 10):
        self.db = db
        self.user_id = user_id
        self.max_history = max_history

    def _session_id(self) -> str:
        today = datetime.date.today().isoformat()
        return f"user_{self.user_id}_{today}"

    def add_message(self, role: str, message: str, repo_context: int = None):
        record = ConversationHistory(
            user_id=self.user_id,
            session_id=self._session_id(),
            role=role,
            message=message,
            repo_context=repo_context,
        )
        self.db.add(record)
        self.db.commit()

    def get_history(self) -> list[dict]:
        records = (
            self.db.query(ConversationHistory)
            .filter(
                ConversationHistory.user_id == self.user_id,
                ConversationHistory.session_id == self._session_id(),
            )
            .order_by(ConversationHistory.created_at.desc())
            .limit(self.max_history)
            .all()
        )
        return [
            {"role": r.role, "message": r.message} for r in reversed(records)
        ]

    def get_session_context(self) -> str:
        history = self.get_history()
        if not history:
            return "无历史对话记录"
        lines = []
        for h in history:
            prefix = "用户" if h["role"] == "user" else "助手"
            lines.append(f"{prefix}: {h['message'][:200]}")
        return "\n".join(lines)
