"""End-to-end local daily run; scheduling remains external to this module."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.bootstrap import ApplicationServices
from app.email.models import DailyMagazine
from app.email.renderer import render_html


@dataclass(frozen=True)
class WorkflowResult:
    date: str
    status: str
    gmail_message_id: str | None = None


class DailyWorkflow:
    def __init__(self, services: ApplicationServices, *, timezone: str) -> None:
        self._services, self._timezone = services, ZoneInfo(timezone)
        self._logger = logging.getLogger(__name__)

    def run(self, now: datetime | None = None) -> WorkflowResult:
        date = (now.astimezone(self._timezone) if now else datetime.now(self._timezone)).date().isoformat()
        self._logger.info("Daily run started", extra={"event": "daily_run_started"})
        try:
            self._services.topic_generator.refill_if_needed()
            run = self._services.daily_runs.start(date)
            state = self._services.redis.client.hgetall(f"daily:run:{date}")
            if run.status == "completed":
                return WorkflowResult(date=date, status="already_completed")
            if state.get("email_status") == "sent":
                self._services.daily_runs.mark_completed(date)
                return WorkflowResult(date=date, status="completed_after_retry", gmail_message_id=state.get("gmail_message_id"))
            briefs = [self._services.topic_researcher.research(topic) for topic in run.topics]
            stories = [self._services.story_generator.generate(topic, brief) for topic, brief in zip(run.topics, briefs, strict=True)]
            news = self._services.news_researcher.recent_developments()
            rabbit_hole = self._services.llm.generate(
                "Write one intriguing, standalone rabbit-hole question that naturally follows from today's curiosity themes. "
                "Keep it under 25 words, it should feel like a prompt for the next morning's exploration, not a generic fact question.",
                task="rabbit_hole",
            ).text.strip()
            html = render_html(DailyMagazine(greeting="Good morning — here are three ideas worth carrying through your day.", stories=stories, news=news, rabbit_hole_question=rabbit_hole))
        except Exception as error:
            self._services.daily_runs.mark_failed(date, type(error).__name__)
            self._logger.exception("Daily run failed before email delivery", extra={"event": "daily_run_failed"})
            raise
        if not self._services.daily_runs.begin_email_delivery(date):
            self._logger.warning("Email delivery already claimed", extra={"event": "email_delivery_skipped"})
            return WorkflowResult(date=date, status="delivery_pending")
        try:
            message_id = self._services.gmail_sender.send_html(subject=f"Your Daily Curiosity — {date}", html=html, message_id=f"<daily-curiosity-{date}@daily-curiosity.local>")
        except Exception as error:
            self._services.daily_runs.mark_email_send_failed(date, type(error).__name__)
            self._services.daily_runs.mark_failed(date, type(error).__name__)
            self._logger.exception("Email delivery failed", extra={"event": "email_send_failed"})
            raise
        self._services.daily_runs.mark_email_sent(date, message_id)
        self._services.daily_runs.mark_completed(date)
        self._logger.info("Daily run completed", extra={"event": "daily_run_completed"})
        return WorkflowResult(date=date, status="completed", gmail_message_id=message_id)
