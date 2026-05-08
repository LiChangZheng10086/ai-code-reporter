import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.config import settings
from app.database import init_db, SessionLocal
from app.bot.bot import TelegramBot
from app.scheduler.tasks import start_scheduler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

bot: TelegramBot = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot
    logger.info("Starting ai-code-reporter...")

    # Init database
    init_db()
    logger.info("Database initialized")

    # Start scheduler
    start_scheduler()

    # Start Telegram Bot
    db = SessionLocal()
    try:
        bot = TelegramBot(db)
        await bot.start()
    finally:
        db.close()

    yield

    # Shutdown
    if bot:
        await bot.stop()
    logger.info("Shutdown complete")


app = FastAPI(title="ai-code-reporter", version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "llm_provider": settings.llm_provider}


@app.get("/")
async def root():
    return {
        "app": "ai-code-reporter",
        "version": "0.1.0",
        "description": "AI-powered Git repository monitoring and reporting bot",
    }
