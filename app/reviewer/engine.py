import json
import logging
from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.orm import Session

from app.llm import get_llm
from app.models import Commit, Review
from app.reviewer.prompts import REVIEW_PROMPT, RISK_ESCALATION_PROMPT, REVIEW_SYSTEM_MESSAGE

logger = logging.getLogger(__name__)


class ReviewState(TypedDict):
    commit_id: int
    diff_content: Optional[str]
    analysis: Optional[str]
    risk_level: Optional[str]
    issues: list
    suggestions: list
    score: Optional[int]
    final_review: Optional[str]


class CodeReviewer:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm(temperature=0.1)
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(ReviewState)

        builder.add_node("analyze_code", self._analyze_code)
        builder.add_node("classify_risk", self._classify_risk)
        builder.add_node("escalate", self._escalate_review)
        builder.add_node("finalize", self._finalize)
        builder.add_node("save", self._save_review)

        builder.set_entry_point("analyze_code")
        builder.add_edge("analyze_code", "classify_risk")
        builder.add_conditional_edges(
            "classify_risk",
            self._route_by_risk,
            {"escalate": "escalate", "finalize": "finalize"},
        )
        builder.add_edge("escalate", "finalize")
        builder.add_edge("finalize", "save")
        builder.add_edge("save", END)

        return builder.compile()

    def review(self, commit: Commit) -> Review:
        state = self.graph.invoke({
            "commit_id": commit.id,
            "diff_content": commit.diff_content or "",
            "analysis": None,
            "risk_level": None,
            "issues": [],
            "suggestions": [],
            "score": None,
            "final_review": None,
        })

        return (
            self.db.query(Review)
            .filter(Review.commit_id == commit.id)
            .first()
        )

    def _analyze_code(self, state: ReviewState) -> dict:
        diff = state["diff_content"]
        if not diff or len(diff.strip()) < 10:
            return {
                "analysis": json.dumps({
                    "score": 100,
                    "risk_level": "low",
                    "issues": [],
                    "summary": "无代码变更或变更为空",
                })
            }

        messages = [
            SystemMessage(content=REVIEW_SYSTEM_MESSAGE),
            HumanMessage(content=REVIEW_PROMPT.format(diff_content=diff[:8000])),
        ]
        response = self.llm.invoke(messages)
        text = response.content.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()

        try:
            json.loads(text)
        except json.JSONDecodeError:
            text = json.dumps({"score": 50, "risk_level": "medium", "issues": [], "summary": text[:500]})

        return {"analysis": text}

    def _classify_risk(self, state: ReviewState) -> dict:
        try:
            data = json.loads(state["analysis"])
        except (json.JSONDecodeError, TypeError):
            data = {"risk_level": "medium", "issues": []}

        return {
            "risk_level": data.get("risk_level", "low"),
            "issues": data.get("issues", []),
            "score": data.get("score"),
        }

    def _route_by_risk(self, state: ReviewState) -> Literal["escalate", "finalize"]:
        return "escalate" if state["risk_level"] == "high" else "finalize"

    def _escalate_review(self, state: ReviewState) -> dict:
        messages = [
            SystemMessage(content="你是一个安全的代码修复专家。"),
            HumanMessage(content=RISK_ESCALATION_PROMPT.format(review_content=state["analysis"])),
        ]
        response = self.llm.invoke(messages)
        return {"suggestions": [response.content]}

    def _finalize(self, state: ReviewState) -> dict:
        parts = [state["analysis"]]
        if state["suggestions"]:
            parts.append("=== 修复建议 ===\n" + "\n---\n".join(state["suggestions"]))
        return {"final_review": "\n\n".join(parts)}

    def _save_review(self, state: ReviewState) -> dict:
        try:
            data = json.loads(state["analysis"])
        except (json.JSONDecodeError, TypeError):
            data = {}

        review = Review(
            commit_id=state["commit_id"],
            risk_level=state["risk_level"] or data.get("risk_level", "low"),
            score=state["score"] or data.get("score"),
            issues=state["issues"] or data.get("issues", []),
            suggestions=state["suggestions"] or data.get("suggestions", []),
            review_content=state["final_review"] or state["analysis"],
        )
        self.db.add(review)
        self.db.commit()
        logger.info(f"Review saved for commit {state['commit_id']}, risk={review.risk_level}")
        return {}
