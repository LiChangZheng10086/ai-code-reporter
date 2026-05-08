import logging
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from sqlalchemy.orm import Session

from app.config import settings
from app.bot.handlers import BotHandlers
from app.bot.project_manager import ProjectManager
from app.conversation.engine import ConversationEngine

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, db: Session):
        self.db = db
        self.project_manager = ProjectManager(db)
        self.conversation_engine = ConversationEngine(db)
        self.handlers = BotHandlers(db, self.project_manager, self.conversation_engine)
        self.application = None

    async def start(self):
        if not settings.tg_bot_token:
            logger.warning("TG_BOT_TOKEN not set, bot not started")
            return

        self.application = Application.builder().token(settings.tg_bot_token).build()

        # Register commands
        self.application.add_handler(CommandHandler("start", self.handlers.cmd_start))
        self.application.add_handler(CommandHandler("addproject", self.handlers.cmd_addproject))
        self.application.add_handler(CommandHandler("projects", self.handlers.cmd_projects))
        self.application.add_handler(CommandHandler("switch", self.handlers.cmd_switch))
        self.application.add_handler(CommandHandler("removeproject", self.handlers.cmd_removeproject))
        self.application.add_handler(CommandHandler("report", self.handlers.cmd_report))
        self.application.add_handler(CommandHandler("help", self.handlers.cmd_help))

        # Text message handler for conversation
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message))

        await self.application.initialize()

        # Register command list so Telegram shows suggestions when typing /
        commands = [
            BotCommand("start", "绑定 TG 账号，开始使用"),
            BotCommand("addproject", "添加 Git 仓库（名称 | 地址 | Token | 分支）"),
            BotCommand("projects", "查看所有已接入项目"),
            BotCommand("switch", "切换当前活动项目，如 /switch 1"),
            BotCommand("removeproject", "移除指定项目，如 /removeproject 1"),
            BotCommand("report", "查看当前项目最新报告"),
            BotCommand("help", "查看帮助信息"),
        ]
        await self.application.bot.set_my_commands(commands)

        await self.application.start()

        # Start polling for Telegram updates
        if self.application.updater:
            await self.application.updater.start_polling()

        logger.info("Telegram Bot started and polling")

    async def stop(self):
        if self.application:
            if self.application.updater:
                await self.application.updater.stop()
            await self.application.stop()
