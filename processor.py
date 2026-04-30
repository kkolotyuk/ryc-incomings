import logging
import os

import gmail_client
import telegram_client
from analyzer import analyze_email

logger = logging.getLogger(__name__)

MAX_EMAIL_AGE_DAYS = 30


class EmailProcessor:
    def __init__(self, max_emails: int | None = None, mark_as_processed: bool = True):
        self.max_emails = max_emails
        self.mark_as_processed = mark_as_processed

        source_label = os.environ["GMAIL_LABEL"]
        self._service = gmail_client.get_service()
        self._source_label_id = gmail_client.get_label_id(self._service, source_label)
        self._processed_label_id = gmail_client.get_or_create_label(
            self._service, source_label + gmail_client.PROCESSED_LABEL_SUFFIX
        )

    def run(self) -> None:
        logger.info("Starting email check")

        emails = gmail_client.fetch_unprocessed_emails(
            self._service, self._source_label_id, self._processed_label_id,
            max_age_days=MAX_EMAIL_AGE_DAYS,
            limit=self.max_emails,
        )

        logger.info("Found %d email(s) to process", len(emails))

        for email in emails:
            try:
                logger.info("Processing: %s", email.subject)
                analysis = analyze_email(email)
                text = telegram_client.format_summary(email.date, email.subject, analysis)
                telegram_client.send_message(text)
                if self.mark_as_processed:
                    gmail_client.mark_as_processed(self._service, email.message_id, self._processed_label_id)
                logger.info("Done: %s", email.subject)
            except Exception as e:
                logger.exception("Failed to process email: %s", email.subject)
                self._notify_error(f"Ошибка при обработке письма '{email.subject}':\n{e}")

    def _notify_error(self, message: str) -> None:
        try:
            safe = telegram_client.escape_markdown(message)
            telegram_client.send_message(f"*\\[RyC bot\\] Ошибка*\n\n{safe}")
        except Exception:
            logger.exception("Failed to send error notification to Telegram")
