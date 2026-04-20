import logging
import os

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]

    response = requests.post(
        TELEGRAM_API.format(token=token),
        json={
            "chat_id": channel_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )
    response.raise_for_status()
    logger.info("Telegram message sent, response: %s", response.json().get("ok"))


def format_summary(email_date: str, subject: str, analysis: dict) -> str:
    child = analysis.get("child")
    child_str = f" — {child}" if child else ""

    lines = [
        f"*Письмо от школы{child_str}*",
        f"",
        f"*Дата:* {email_date}",
        f"*Тема:* {subject}",
        f"",
        f"*О чём:*",
        analysis.get("summary", "—"),
    ]

    actions = analysis.get("actions") or []
    if actions:
        lines += ["", "*Что нужно сделать:*"]
        for action in actions:
            lines.append(f"• {action}")

    deadlines = analysis.get("deadlines") or []
    if deadlines:
        lines += ["", "*Дедлайны:*"]
        for deadline in deadlines:
            lines.append(f"• {deadline}")

    money = analysis.get("money")
    if money:
        lines += ["", f"*Деньги:* {money}"]

    return "\n".join(lines)
