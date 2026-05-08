import json
import logging
from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.orm import Session

from app.llm import get_llm
from app.bot.project_manager import ProjectManager
from app.conversation.memory import ConversationMemory
from app.conversation.retriever import DataRetriever, _parse_time_range
from app.conversation.prompts import (
    CLASSIFY_INTENT_PROMPT,
    EXTRACT_PARAMS_PROMPT,
    QUERY_RESPONSE_PROMPT,
)
from app.git_monitor.fetcher import GitFetcher
from app.reviewer.engine import CodeReviewer

logger = logging.getLogger(__name__)


class ConvState(TypedDict):
    user_id: int
    message: str
    intent: Optional[str]
    params: Optional[dict]
    data: Optional[str]
    response: Optional[str]


class ConversationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm(temperature=0.3)
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(ConvState)

        builder.add_node("classify_intent", self._classify_intent)
        builder.add_node("extract_params", self._extract_params)
        builder.add_node("retrieve_data", self._retrieve_data)
        builder.add_node("generate_response", self._generate_response)
        builder.add_node("chitchat_response", self._chitchat_response)
        builder.add_node("refuse_response", self._refuse_response)
        builder.add_node("check_update", self._check_update)

        builder.set_entry_point("classify_intent")
        builder.add_conditional_edges(
            "classify_intent",
            self._route_intent,
            {"query": "extract_params", "chitchat": "chitchat_response", "refuse": "refuse_response", "update": "check_update"},
        )
        builder.add_edge("extract_params", "retrieve_data")
        builder.add_edge("retrieve_data", "generate_response")
        builder.add_edge("generate_response", END)
        builder.add_edge("chitchat_response", END)
        builder.add_edge("refuse_response", END)
        builder.add_edge("check_update", END)

        return builder.compile()

    async def process_message(self, user_id: int, message: str) -> str:
        state = self.graph.invoke({
            "user_id": user_id,
            "message": message,
            "intent": None,
            "params": None,
            "data": None,
            "response": None,
        })
        return state["response"]

    def _classify_intent(self, state: ConvState) -> dict:
        prompt = CLASSIFY_INTENT_PROMPT.format(message=state["message"])
        resp = self.llm.invoke([HumanMessage(content=prompt)])
        intent = resp.content.strip().lower()
        valid = ("list_commits", "list_reviews", "get_report", "check_update", "chitchat", "refuse")
        if intent not in valid:
            # Default to list_commits when uncertain, so bot tries to help
            intent = "list_commits"
        return {"intent": intent}

    def _route_intent(self, state: ConvState) -> Literal["query", "chitchat", "refuse", "update"]:
        intent = state["intent"]
        if intent in ("list_commits", "list_reviews", "get_report"):
            return "query"
        if intent == "check_update":
            return "update"
        return intent  # chitchat or refuse

    def _refuse_response(self, state: ConvState) -> dict:
        # Check user's repo status for tailored redirect
        from app.bot.project_manager import ProjectManager
        pm = ProjectManager(self.db)
        repos = pm.get_user_repositories(state["user_id"])
        repo_status = f"用户已接入 {len(repos)} 个项目：{[r.name for r in repos]}" if repos else "用户尚未接入任何 Git 仓库"

        system_msg = f"""你是 ai-code-reporter 的 AI 助手，一个专注于 Git 仓库监控和代码报告的工具。

【当前用户状态】{repo_status}

【核心原则】
- 用户当前的问题涉及黄、赌、毒、暴力、违法或政治敏感内容
- 你必须礼貌但坚定地拒绝回答
- 拒绝后自然地引导用户回到 Bot 的核心功能上
- 根据用户状态调整引导方式：无仓库则引导添加仓库，有仓库则引导查询或查看报告
- 不要重复相同的句式，每次回复要有变化
- 语气友好、专业

【回复示例】（只是参考，不要照抄）：
• "这个话题我没办法帮你，不如来看看你的 Git 仓库最近有什么新提交？"
• "我们还是聊点工作相关的吧，比如你的项目代码审核情况怎么样？"
• "抱歉，我只能专注于代码相关的问题。要不要试试查看今天的日结报告？"

【Bot 的功能简介】
- 接入 Git 仓库自动追踪提交
- AI 代码审查
- 日结/周结/月结报告推送
- 自然语言查询历史数据
- 多项目管理

请根据以上要求，用自然、不重复的方式回复用户。"""
        prompt = f"用户消息：{state['message']}\n\n请回复："
        resp = self.llm.invoke([
            SystemMessage(content=system_msg),
            HumanMessage(content=prompt),
        ])
        return {"response": resp.content}

    def _check_update(self, state: ConvState) -> dict:
        """立即拉取远程代码，检查是否有新提交。"""
        pm = ProjectManager(self.db)
        repos = pm.get_user_repositories(state["user_id"])

        if not repos:
            return {"response": "你还没有添加任何 Git 仓库，请先使用 /addproject 添加仓库。"}

        active = pm.get_active_project(state["user_id"])
        if not active:
            return {"response": "当前没有活动项目。请先使用 /switch 切换到要检查的项目，或指定项目名称。"}

        fetcher = GitFetcher(self.db)
        reviewer = CodeReviewer(self.db)

        try:
            new_commits = fetcher.clone_or_pull(active)
        except Exception as e:
            logger.error(f"Git fetch failed for {active.name}: {e}")
            return {"response": f"❌ 拉取 {active.name} 代码失败：{str(e)[:200]}"}

        if not new_commits:
            return {"response": f"✅ {active.name} 当前已经是最新，没有新的代码提交。"}

        lines = [
            f"📦 *{active.name}* 检测到 {len(new_commits)} 个新提交！",
            "━━━━━━━━━━━━━━━━━",
        ]

        for commit in new_commits:
            try:
                review = reviewer.review(commit)
            except Exception as e:
                review = None
                logger.error(f"Review failed for commit {commit.id}: {e}")

            lines.append("")
            lines.append(f"📝 Commit `{commit.commit_hash[:8]}`")
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

        mem = ConversationMemory(self.db, state["user_id"])
        mem.add_message("user", state["message"])
        mem.add_message("assistant", "\n".join(lines))

        # Also generate today's daily report so data is persisted
        try:
            from app.reporter.daily import DailyReporter
            report = DailyReporter(self.db).generate(active)
            if report:
                logger.info(f"Daily report updated for {active.name}")
        except Exception as e:
            logger.error(f"Failed to generate daily report after update: {e}")

        return {"response": "\n".join(lines)}

    def _generate_report_on_demand(self, state: ConvState, repo_id: Optional[int], time_range: str) -> str:
        """当没有预生成报告时，按需生成（含指定时间范围）。"""
        from app.reporter.daily import DailyReporter
        from app.reporter.weekly import WeeklyReporter
        from app.reporter.monthly import MonthlyReporter

        pm = ProjectManager(self.db)
        repos = pm.get_user_repositories(state["user_id"])
        target_repo = next((r for r in repos if r.id == repo_id), repos[0] if repos else None)
        if not target_repo:
            return "暂无报告，且没有可用的项目来生成报告。"

        # Determine report type from time_range
        report_type = "daily"
        if any(kw in time_range for kw in ("周", "week", "星期")):
            report_type = "weekly"
        elif any(kw in time_range for kw in ("月", "month")):
            report_type = "monthly"

        # Parse time range to extract period for report generation
        since, until = _parse_time_range(time_range) if time_range else (None, None)

        try:
            if report_type == "daily":
                reporter = DailyReporter(self.db)
                date = since.date() if since else None
                report = reporter.generate(target_repo, date=date)
            elif report_type == "weekly":
                reporter = WeeklyReporter(self.db)
                if since:
                    iso = since.isocalendar()
                    report = reporter.generate(target_repo, year=iso[0], week=iso[1])
                else:
                    report = reporter.generate(target_repo)
            else:  # monthly
                reporter = MonthlyReporter(self.db)
                if since:
                    report = reporter.generate(target_repo, year=since.year, month=since.month)
                else:
                    report = reporter.generate(target_repo)

            if report:
                return (
                    f"📋 *[{report.report_type.upper()}] {target_repo.name}*\n"
                    f"📅 {report.period_start.date()} ~ {report.period_end.date()}\n\n"
                    f"{report.content[:3000]}"
                )
            return f"该时间段内 {target_repo.name} 没有提交记录，无法生成报告。"
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return f"生成报告失败：{str(e)[:200]}"

    def _extract_params(self, state: ConvState) -> dict:
        prompt = EXTRACT_PARAMS_PROMPT.format(message=state["message"])
        resp = self.llm.invoke([HumanMessage(content=prompt)])
        try:
            params = json.loads(resp.content)
        except (json.JSONDecodeError, TypeError):
            params = {"time_range": "", "project": "", "keyword": ""}
        return {"params": params}

    def _retrieve_data(self, state: ConvState) -> dict:
        params = state["params"]
        retriever = DataRetriever(self.db, state["user_id"])
        pm = ProjectManager(self.db)

        # Determine repo context
        repo_id = None
        if params.get("project"):
            repos = pm.get_user_repositories(state["user_id"])
            for r in repos:
                if params["project"].lower() in r.name.lower():
                    repo_id = r.id
                    break
        if repo_id is None:
            active = pm.get_active_project(state["user_id"])
            repo_id = active.id if active else None

        # If no repo at all, return a helpful message
        repos = pm.get_user_repositories(state["user_id"])
        if not repos:
            data = "用户还没有添加任何 Git 仓库。请先使用 /addproject 命令添加仓库。"

            mem = ConversationMemory(self.db, state["user_id"])
            mem.add_message("user", state["message"])
            return {"data": data}

        intent = state["intent"]
        if intent == "list_commits":
            commits = retriever.query_commits(repo_id, params.get("time_range", ""), params.get("keyword", ""))
            if not commits:
                data = "没有找到匹配的提交记录。"
            else:
                lines = [f"共找到 {len(commits)} 条提交："]
                for c in commits:
                    lines.append(f"- [{c.committed_at.strftime('%m-%d %H:%M')}] {c.author}: {c.message[:100]}")
                data = "\n".join(lines)
        elif intent == "list_reviews":
            reviews = retriever.query_reviews(repo_id, params.get("time_range", ""))
            if not reviews:
                data = "没有找到审核记录。"
            else:
                lines = [f"共找到 {len(reviews)} 条审核记录："]
                for r in reviews:
                    issues = json.dumps(r.issues, ensure_ascii=False) if r.issues else "无问题"
                    lines.append(f"- 风险:{r.risk_level} 评分:{r.score} 问题:{issues[:200]}")
                data = "\n".join(lines)
        elif intent == "get_report":
            time_range = params.get("time_range", "")
            since, until = _parse_time_range(time_range) if time_range else (None, None)

            # Determine report type from user's request
            report_type = "daily"
            if any(kw in time_range for kw in ("周", "week", "星期")):
                report_type = "weekly"
            elif any(kw in time_range for kw in ("月", "month")):
                report_type = "monthly"

            if since and until:
                # User specified a time range — try to find existing report for that period
                reports = retriever.query_reports_by_period(repo_id, since, until, report_type)
                if reports:
                    # Show existing report for this period
                    r = reports[0]
                    data = (
                        f"📋 *[{r.report_type.upper()}] {r.period_start.date()} ~ {r.period_end.date()}*\n\n"
                        f"{r.content[:3000]}"
                    )
                else:
                    data = self._generate_report_on_demand(state, repo_id, time_range)
            else:
                # No specific time range — show latest report for current period
                reports = retriever.query_reports(repo_id, report_type)
                if reports:
                    r = reports[0]
                    data = (
                        f"📋 *[{r.report_type.upper()}] {r.period_start.date()} ~ {r.period_end.date()}*\n\n"
                        f"{r.content[:3000]}"
                    )
                else:
                    data = self._generate_report_on_demand(state, repo_id, time_range)
        else:
            data = ""

        # Save to memory
        mem = ConversationMemory(self.db, state["user_id"])
        mem.add_message("user", state["message"], repo_id)

        return {"data": data}

    def _generate_response(self, state: ConvState) -> dict:
        prompt = QUERY_RESPONSE_PROMPT.format(
            question=state["message"],
            data=state["data"],
        )
        resp = self.llm.invoke([HumanMessage(content=prompt)])

        # Save assistant response
        mem = ConversationMemory(self.db, state["user_id"])
        mem.add_message("assistant", resp.content)

        return {"response": resp.content}

    def _chitchat_response(self, state: ConvState) -> dict:
        mem = ConversationMemory(self.db, state["user_id"])
        history = mem.get_session_context()

        # Check user's repo status so AI can tailor the response
        from app.bot.project_manager import ProjectManager
        pm = ProjectManager(self.db)
        repos = pm.get_user_repositories(state["user_id"])
        repo_status = f"用户已接入 {len(repos)} 个项目：{[r.name for r in repos]}" if repos else "用户尚未接入任何 Git 仓库"

        user_context = f"【当前用户状态】{repo_status}"

        system_msg = f"""你是 ai-code-reporter 的 AI 助手，一个专注于 Git 仓库监控和代码报告的工具。

{user_context}

【身份定位】
你是一个懂技术、说话自然的 AI 助手，核心任务是把用户引导到 Git 监控和代码报告的功能上。

【回复规则】
- 打招呼（你好、hi）：热情回应后，自然引出 Bot 的功能介绍，像朋友推荐工具一样
- 询问功能（你能做什么）：详细介绍核心功能，语气热情，举具体例子
- 无关话题（天气、新闻、娱乐等）：礼貌地把话题拉回到工作上，不要生硬拒绝
- 【绝对禁止】涉及黄赌毒暴力违法内容：坚定拒绝，不解释不纠缠
- 禁止重复：不要每次都用同样的句式，保持回复的多样性

【回复风格参考】（根据具体情况灵活使用，不要照搬）：
• 打招呼场景："嘿！欢迎来玩～我可以帮你盯着 Git 仓库的每一次变动，自动做代码审查，还能按时给你出报告。要不要先加个项目试试？"
• 问功能场景："我的核心本事是帮你管 Git 仓库——自动追踪提交、AI 审查代码、每天傍晚给你送日结报告。你只要说一句'昨天谁提交了'我就能帮你查出来。"
• 无关话题场景："哈哈这个我不太在行，我比较擅长跟代码打交道。对了，你的项目最近有新的提交吗？我可以帮你看看审核结果。"
• 拒绝违禁："抱歉，这个我没法聊。咱们还是专注代码相关的事情吧。"

【Bot 核心功能要点】
- Git 仓库监控：接入仓库自动追踪每次提交
- AI 代码审核：每次新提交自动审查代码质量、Bug、安全
- 定时报告：每天18:00日结 / 每周一09:00周结 / 每月1号月结
- 自然语言查询：用中文问就能查历史数据，如"昨天谁提交了代码？"
- 多项目管理：支持多个仓库，/switch 切换

【常用命令】
/start /addproject /projects /switch /removeproject /report /help

每次都根据用户的具体消息自然应对，不要死板地背说明书。"""
        prompt = f"历史对话：\n{history}\n\n用户说：{state['message']}\n\n请回复："
        resp = self.llm.invoke([
            SystemMessage(content=system_msg),
            HumanMessage(content=prompt),
        ])

        mem.add_message("user", state["message"])
        mem.add_message("assistant", resp.content)

        return {"response": resp.content}
