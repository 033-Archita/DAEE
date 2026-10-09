import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from app.email.gmail import GmailSender
from app.llm.base import LLMResponse
from app.orchestration.workflow import DailyWorkflow
from app.research.models import Source
from app.story.models import CuriosityStory
from app.topics.models import TopicCandidate


class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def read(self): return json.dumps(self.payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False


def test_gmail_sender_refreshes_token_and_sends_html():
    sender = GmailSender(client_id="client", client_secret="secret", refresh_token="refresh", recipient="me@example.com")
    with patch("app.email.gmail.urlopen", side_effect=[FakeResponse({"access_token": "token"}), FakeResponse({"id": "gmail-id"})]) as urlopen:
        assert sender.send_html(subject="Test", html="<h1>Hello</h1>", message_id="<test@example.com>") == "gmail-id"
    assert urlopen.call_count == 2
    assert "Bearer token" in urlopen.call_args_list[1].args[0].headers["Authorization"]


class FakeDailyRuns:
    def __init__(self, run): self.run, self.completed, self.sent = run, False, False
    def start(self, date): return self.run
    def begin_email_delivery(self, date): return True
    def mark_email_sent(self, date, message_id): self.sent = message_id
    def mark_completed(self, date): self.completed = True
    def mark_failed(self, date, reason): raise AssertionError("unexpected failure")


def test_workflow_completes_after_one_safe_email_delivery():
    topic = TopicCandidate("Topic", "Summary", "History", "topic")
    run = SimpleNamespace(status="started", topics=[topic, topic, topic])
    daily_runs = FakeDailyRuns(run)
    source = Source("Source", "https://example.com", "")
    services = SimpleNamespace(
        topic_generator=SimpleNamespace(refill_if_needed=lambda: []),
        daily_runs=daily_runs,
        redis=SimpleNamespace(client=SimpleNamespace(hgetall=lambda key: {})),
        topic_researcher=SimpleNamespace(research=lambda topic: SimpleNamespace()),
        story_generator=SimpleNamespace(generate=lambda topic, brief: CuriosityStory(topic.title, topic.category, "A story.", "A takeaway.", [source])),
        news_researcher=SimpleNamespace(recent_developments=lambda: []),
        llm=SimpleNamespace(generate=lambda prompt, task: LLMResponse("Why this?", "fake", "fake", {})),
        gmail_sender=SimpleNamespace(send_html=lambda **kwargs: "gmail-123"),
    )

    result = DailyWorkflow(services, timezone="Asia/Kolkata").run(datetime(2026, 8, 11, 5, tzinfo=UTC))

    assert result.status == "completed"
    assert daily_runs.sent == "gmail-123"
    assert daily_runs.completed is True
