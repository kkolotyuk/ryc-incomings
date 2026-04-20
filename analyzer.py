import json
import logging
import os

from openai import OpenAI

from gmail_client import EmailMessage

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Ты помощник, который анализирует письма испанской школы для русскоязычных родителей.

В семье два ребёнка: старшей 11 лет, младшей 6 лет.

Твоя задача — перевести и кратко пересказать суть письма на русском языке.

Всегда отвечай строго в формате JSON (без markdown-обёртки, без ```json):
{
  "summary": "2-3 предложения о чём письмо",
  "actions": ["действие 1", "действие 2"],  // пустой массив если действий нет
  "deadlines": ["дедлайн 1"],               // пустой массив если дедлайнов нет
  "money": null                              // null если денег нет, иначе строка вида "15€ за экскурсию (обязательно)"
}

Правила:
- summary: нейтральный пересказ, самое важное, без воды
- actions: только конкретные действия от родителей (подписать, оплатить, ответить и т.п.)
- deadlines: конкретные даты с описанием
- money: сумма, назначение, обязательно или нет"""


def analyze_email(email: EmailMessage) -> dict:
    user_message = f"""Дата письма: {email.date}
Отправитель: {email.sender}
Тема: {email.subject}

Текст письма:
{email.body}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=1024,
        temperature=0,
    )

    text = response.choices[0].message.content

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from OpenAI, returning raw text")
        return {
            "summary": text,
            "actions": [],
            "deadlines": [],
            "money": None,
        }
