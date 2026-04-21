import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

import telegram_client
from processor import EmailProcessor

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

REQUIRED_ENV = [
    "GMAIL_CLIENT_ID",
    "GMAIL_CLIENT_SECRET",
    "GMAIL_REFRESH_TOKEN",
    "GMAIL_LABEL",
    "OPENAI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHANNEL_ID",
]


def validate_env() -> None:
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def main() -> None:
    validate_env()

    interval = int(os.environ.get("POLL_INTERVAL_SECONDS", 3600))
    logger.info("Starting scheduler, interval: %ds", interval)

    def job():
        try:
            EmailProcessor().run()
        except Exception as e:
            logger.exception("Processor failed")
            try:
                telegram_client.send_message(f"*[RyC bot] Критическая ошибка*\n\n{e}")
            except Exception:
                logger.exception("Failed to send error notification to Telegram")

    job()

    scheduler = BlockingScheduler()
    scheduler.add_job(job, "interval", seconds=interval)
    scheduler.start()


if __name__ == "__main__":
    main()
