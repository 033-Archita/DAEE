"""Explicit application wiring, kept separate from business logic."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.email.gmail import GmailSender
from app.news.researcher import NewsResearcher
from app.research.researcher import TopicResearcher
from app.research.search import TavilySearchProvider
from app.story.generator import StoryGenerator
from app.llm.providers import cloudflare, mistral, openrouter
from app.llm.router import LLMRouter
from app.memory.health import ProviderHealthRepository
from app.memory.mongo import MongoRepository
from app.orchestration.daily_run import DailyRunService
from app.topics.generator import TopicGenerator
from app.topics.repository import TopicRepository


@dataclass(frozen=True)
class ApplicationServices:
    redis: MongoRepository
    topics: TopicRepository
    topic_generator: TopicGenerator
    daily_runs: DailyRunService
    topic_researcher: TopicResearcher
    news_researcher: NewsResearcher
    story_generator: StoryGenerator
    llm: LLMRouter
    gmail_sender: GmailSender


def build_services(settings: Settings) -> ApplicationServices:
    """Connect MongoDB Atlas and assemble services from configuration."""
    redis_repository = MongoRepository(settings.mongo_uri, settings.mongo_database)
    redis_repository.connect()
    providers = {
        "cloudflare": cloudflare(settings.cloudflare_account_id, settings.cloudflare_api_token, settings.cloudflare_model),
        "openrouter": openrouter(settings.openrouter_api_key, settings.openrouter_model),
        "mistral": mistral(settings.mistral_api_key, settings.mistral_model),
    }
    router = LLMRouter(providers, settings.llm_provider_order, ProviderHealthRepository(redis_repository))
    topics = TopicRepository(redis_repository)
    search = TavilySearchProvider(settings.tavily_api_key)
    return ApplicationServices(
        redis=redis_repository,
        topics=topics,
        topic_generator=TopicGenerator(router, topics, pool_size=settings.pool_size, low_watermark=settings.low_watermark),
        daily_runs=DailyRunService(redis_repository, topics),
        topic_researcher=TopicResearcher(search, router, max_results=settings.tavily_max_results),
        news_researcher=NewsResearcher(search, router, max_results=settings.tavily_max_results),
        story_generator=StoryGenerator(router),
        llm=router,
        gmail_sender=GmailSender(client_id=settings.gmail_oauth_client_id, client_secret=settings.gmail_oauth_client_secret, refresh_token=settings.gmail_refresh_token, recipient=settings.gmail_recipient),
    )
