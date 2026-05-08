import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.project_manager import ProjectManager
from app.conversation.engine import ConversationEngine

logger = logging.getLogger(__name__)

HELP_TEXT = """🤖 *ai-code-reporter 使用帮助*

*命令列表：*
/start - 重新开始配置向导
/addproject <名称 | 地址 | Token | 分支> - 添加 Git 仓库
/projects - 查看所有已接入项目
/switch <编号> - 切换当前活动项目
/removeproject <编号> - 移除指定项目
/report - 查看当前项目最新报告
/help - 显示此帮助

*💬 自然语言查询示例：*
• \"昨天有谁提交了代码？\"
• \"上周发现了哪些严重问题？\"
• \"给我看上个月的月结报告\"
• \"查一下 user1 的提交记录\"
• \"帮我查 project-a 的审核记录\"
• \"这个项目是做什么的？\"

*⏰ 定时推送：*
• 日结：每天 18:00
• 周结：每周一 09:00
• 月结：每月 1 号 09:00

*🔧 快速入门：*
1. 添加仓库 → `/addproject 项目名 | 仓库地址 | Token`
2. 查看项目 → `/projects`
3. 切换项目 → `/switch 1`
4. 等待报告自动推送，或直接问我问题
"""


class BotHandlers:
    def __init__(self, db, project_manager: ProjectManager, conversation_engine: ConversationEngine):
        self.db = db
        self.pm = project_manager
        self.conv = conversation_engine

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user_id = str(update.effective_user.id)
        tg_bot_token = context.bot.token
        user = self.pm.get_or_create_user(tg_user_id, tg_bot_token)

        repos = self.pm.get_user_repositories(user.id)
        if repos:
            text = (
                f"👋 欢迎回来！你已接入 {len(repos)} 个项目。\n\n"
                f"当前活动项目：{self.pm.get_active_project(user.id).name if self.pm.get_active_project(user.id) else '无'}\n\n"
                f"• 输入 /projects 查看所有项目\n"
                f"• 输入 /addproject 添加新仓库\n"
                f"• 直接问我问题，例如：\"昨天有谁提交了？\""
            )
            await update.message.reply_text(text)
            return

        welcome = (
            f"👋 *你好！欢迎使用 ai-code-reporter！*\n\n"
            f"我是你的 AI 代码报告助手，可以帮你：\n\n"
            f"📦 *监控 Git 仓库* — 接入仓库后自动追踪每次提交\n"
            f"🔍 *AI 代码审查* — 每次提交自动分析代码质量、Bug、安全\n"
            f"📋 *自动报告* — 每天 18:00 日结 / 每周一 09:00 周结 / 每月 1 号月结\n"
            f"💬 *智能问答* — 直接用自然语言查询历史数据\n\n"
            f"*现在开始第一步：添加你的 Git 仓库*\n\n"
            f"发送：\n"
            f"`/addproject 项目名称 | 仓库地址 | 访问令牌`\n\n"
            f"例如：\n"
            f"`/addproject myapp | https://github.com/user/repo.git | ghp_xxxxxx`\n\n"
            f"或者输入 /help 查看完整帮助"
        )
        await update.message.reply_text(welcome)

    async def cmd_addproject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user_id = str(update.effective_user.id)
        user = self.pm.get_or_create_user(tg_user_id, context.bot.token)

        args = " ".join(context.args)
        if not args or "|" not in args:
            text = (
                "⚠️ *格式不正确*\n\n"
                "正确格式：\n"
                "`/addproject 项目名称 | 仓库地址 | Git Token | 分支(可选)`\n\n"
                "例如：\n"
                "`/addproject myapp | https://github.com/user/repo.git | ghp_xxxxxx | main`\n\n"
                "💡 *如何获取 Git Token？*\n"
                "• GitHub：Settings → Developer settings → Personal access tokens → Generate new token\n"
                "• 只需要勾选 repo 相关的只读权限即可"
            )
            await update.message.reply_text(text)
            return

        parts = [p.strip() for p in args.split("|")]
        if len(parts) < 3:
            await update.message.reply_text("至少需要：名称 | 仓库地址 | Git Token")
            return

        name, git_url, git_token = parts[0], parts[1], parts[2]
        branch = parts[3] if len(parts) > 3 else "main"

        try:
            repo = self.pm.add_repository(user.id, name, git_url, git_token, branch)
        except Exception as e:
            await update.message.reply_text(f"❌ 项目添加失败：{str(e)[:200]}")
            return

        active = self.pm.get_active_project(user.id)
        active_text = "（当前活动项目）" if active and active.id == repo.id else ""

        success_text = (
            f"✅ *项目添加成功！* {active_text}\n\n"
            f"📁 名称：`{repo.name}`\n"
            f"🔗 仓库：`{repo.git_url}`\n"
            f"🌿 分支：`{repo.branch}`\n"
            f"🆔 编号：`{repo.id}`\n\n"
            f"系统将自动开始监控此仓库：\n"
            f"• 每 30 分钟拉取最新代码\n"
            f"• 新提交自动触发 AI 审核\n"
            f"• 到时间自动推送报告到这里\n\n"
            f"你可以继续添加更多项目，或直接问我问题！"
        )
        await update.message.reply_text(success_text)

    async def cmd_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user_id = str(update.effective_user.id)
        user = self.pm.get_or_create_user(tg_user_id, context.bot.token)
        repos = self.pm.get_user_repositories(user.id)
        active = self.pm.get_active_project(user.id)

        if not repos:
            await update.message.reply_text(
                "📭 *还没有接入任何项目*\n\n"
                "使用以下命令添加你的第一个仓库：\n"
                "`/addproject 项目名称 | 仓库地址 | Git Token`"
            )
            return

        lines = ["📁 *已接入项目：*\n"]
        for r in repos:
            marker = " ⬅️ 当前" if active and active.id == r.id else ""
            lines.append(f"`{r.id}.` *{r.name}*{marker}")
            lines.append(f"   🔗 `{r.git_url}`")
            lines.append(f"   🌿 {r.branch}  📅 最后检查：{r.last_fetched_at or '尚未拉取'}")
        lines.append("\n💡 切换项目：`/switch <编号>`")
        await update.message.reply_text("\n".join(lines))

    async def cmd_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user_id = str(update.effective_user.id)
        user = self.pm.get_or_create_user(tg_user_id, context.bot.token)

        if not context.args:
            repos = self.pm.get_user_repositories(user.id)
            if not repos:
                await update.message.reply_text("还没有项目，请先 /addproject 添加仓库。")
                return
            text = "请指定项目 ID。可用项目：\n" + "\n".join(
                f"`{r.id}` - {r.name}" for r in repos
            ) + "\n\n用法：`/switch <编号>`"
            await update.message.reply_text(text)
            return

        try:
            repo_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("项目 ID 必须是数字")
            return

        if self.pm.switch_project(user.id, repo_id):
            repo_name = self.pm.get_active_project(user.id).name
            await update.message.reply_text(f"✅ 已切换到项目：*{repo_name}*")
        else:
            await update.message.reply_text("❌ 项目不存在或无权访问")

    async def cmd_removeproject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user_id = str(update.effective_user.id)
        user = self.pm.get_or_create_user(tg_user_id, context.bot.token)

        if not context.args:
            await update.message.reply_text("请指定项目 ID：`/removeproject <编号>`")
            return

        try:
            repo_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("项目 ID 必须是数字")
            return

        if self.pm.remove_repository(user.id, repo_id):
            await update.message.reply_text(f"🗑️ 已移除项目 `{repo_id}`")
        else:
            await update.message.reply_text("❌ 项目不存在")

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user_id = str(update.effective_user.id)
        user = self.pm.get_or_create_user(tg_user_id, context.bot.token)
        active = self.pm.get_active_project(user.id)

        if not active:
            await update.message.reply_text(
                "当前没有活动项目。\n"
                "请先 /addproject 添加仓库，或 /switch 切换到已有项目。"
            )
            return

        from app.models import Report
        report = (
            self.db.query(Report)
            .filter(Report.repo_id == active.id)
            .order_by(Report.created_at.desc())
            .first()
        )
        if report:
            text = (
                f"📋 *[{report.report_type.upper()}] {active.name}*\n"
                f"📅 {report.period_start.date()} ~ {report.period_end.date()}\n\n"
                f"{report.content[:3000]}"
            )
            await update.message.reply_text(text)
        else:
            await update.message.reply_text(
                f"📭 *{active.name}* 暂无报告。\n\n"
                "你可以直接在对话中告诉我，例如：\"看看今天的日报\""
            )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🤖 *ai-code-reporter 使用帮助*\n\n"
            "*命令列表：*\n"
            "`/start` - 重新开始配置向导\n"
            "`/addproject` - 添加 Git 仓库\n"
            "`/projects` - 查看所有项目\n"
            "`/switch <编号>` - 切换项目\n"
            "`/removeproject <编号>` - 移除项目\n"
            "`/report` - 查看最新报告\n"
            "`/help` - 查看帮助\n\n"
            "*💬 对话查询示例：*\n"
            "• \"昨天谁提交了代码？\"\n"
            "• \"上周发现了哪些严重问题？\"\n"
            "• \"给我看上个月的月结报告\"\n\n"
            "*⏰ 定时推送：*\n"
            "• 日结：每天 18:00\n"
            "• 周结：每周一 09:00\n"
            "• 月结：每月 1 号 09:00\n\n"
            "*📖 快速入门：*\n"
            "1️⃣ `/addproject 项目名 | 仓库地址 | Token`\n"
            "2️⃣ `/projects` 查看\n"
            "3️⃣ `/switch 1` 切换\n"
            "4️⃣ 等报告推送或直接问我"
        )
        await update.message.reply_text(text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language conversation queries."""
        tg_user_id = str(update.effective_user.id)
        user = self.pm.get_or_create_user(tg_user_id, context.bot.token)
        user_message = update.message.text.strip()

        # Route to conversation engine — AI handles all responses naturally
        response = await self.conv.process_message(user.id, user_message)
        max_len = 4000
        if len(response) > max_len:
            response = response[:max_len] + "\n\n...（内容过长已截断）"
        await update.message.reply_text(response)
