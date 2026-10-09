import pytest

from app.email.models import DailyMagazine
from app.email.renderer import render_html
from app.llm.base import LLMResponse
from app.news.researcher import NewsResearcher
from app.research.models import Source
from app.research.researcher import TopicResearcher
from app.story.generator import StoryGenerator
from app.story.models import CuriosityStory
from app.topics.models import TopicCandidate


class FakeSearch:
    def search(self, query, *, max_results):
        return [Source("Primary source", "https://example.com/a", "Evidence A"), Source("Second source", "https://example.com/b", "Evidence B")]


class FakeLLM:
    def generate_structured(self, prompt, *, task):
        if task == "research_synthesis":
            return {"overview": "A documented phenomenon.", "key_claims": ["It began in 1949.", "It has practical effects."], "uncertainty": "Dates vary slightly by source."}
        return {"items": [{"headline": "A meaningful development", "summary": "A concise factual update.", "significance": "It affects many people.", "source_indexes": [0, 1]}]}
    def generate(self, prompt, *, task):
        return LLMResponse("A compelling opening.\n\nA clear explanation.", "fake", "fake-model", {})


def test_research_story_and_news_are_source_grounded():
    topic = TopicCandidate("Kaprekar's constant", "Number puzzle", "Mathematics", "kaprekars-constant")
    llm, search = FakeLLM(), FakeSearch()
    brief = TopicResearcher(search, llm, max_results=5).research(topic)
    story = StoryGenerator(llm).generate(topic, brief)
    news = NewsResearcher(search, llm, max_results=5).recent_developments()

    assert brief.sources[0].url == "https://example.com/a"
    assert "clear explanation" in story.body
    assert len(news) == 1 and len(news[0].sources) == 2


def test_story_generator_keeps_structured_editorial_sections():
    class StructuredStoryLLM(FakeLLM):
        def generate_structured(self, prompt, *, task):
            if task == "story_generation":
                return {
                    "title": "A number that settles into one value",
                    "hook": "Even messy inputs collapse into a single result.",
                    "sections": [
                        {"heading": "The procedure", "content": "Start with any four-digit number and repeat the subtraction. The method is simple enough to do by hand: reorder the digits from largest to smallest, subtract the opposite arrangement, and keep going. For example, 3524 becomes 5432 - 2345 = 3087. From there, 8730 - 0378 = 8352, and then 8532 - 2358 = 6174. Once 6174 appears, the process cycles back to itself, which is why this puzzle is more than a cute trick. It is a tiny system with a stubborn destination. The striking fact is that many different numbers collapse into the same value, which gives the procedure a kind of mathematical gravity. The procedural elegance matters because the rule is easy to state but harder to predict from the outset. A reader can test it on four-digit numbers and see how quickly the sequence compresses into a single stable outcome. That is the first half of the delight: the procedure is memorable, and it feels almost like an algorithmic lock. The reason it lingers is that the rule is simple enough to teach quickly, yet the pattern is not obvious until you actually work through a few examples. That gap between simplicity and surprise is where the curiosity lives. It turns a numerical trick into a miniature lesson about order emerging from complexity without any external force guiding it."},
                        {"heading": "Why it matters", "content": "This matters because it shows a larger idea: simple rules can produce stable behavior even when the starting point is messy. In mathematics, scientists and engineers often care about systems that converge, settle, or return to a repeatable state. Kaprekar's routine is a clean, teachable example of that principle. It gives ordinary readers a way to see convergence without needing a heavy formal proof. The result is memorable because it feels almost magical while still being completely explainable by a clear rule. That is why it remains such a good educational example. It also hints at something bigger: many natural systems are not fully random, even when their beginning conditions look chaotic. A tiny deterministic process can still reveal a stable pattern hidden beneath the surface. In a world full of noisy data, this routine reminds us that hidden order can be found by watching a process long enough and paying attention to where it settles."},
                    ],
                    "takeaway": "Simple rules can create hidden order.",
                    "sources": [{"title": "Primary source", "url": "https://example.com/source"}],
                }
            return super().generate_structured(prompt, task=task)

    topic = TopicCandidate("Kaprekar's constant", "Number puzzle", "Mathematics", "kaprekars-constant")
    story = StoryGenerator(StructuredStoryLLM()).generate(topic, type("Brief", (), {"overview": "A documented phenomenon.", "key_claims": ["It converges."], "uncertainty": "Minor variation exists.", "sources": [Source("Primary source", "https://example.com/source", "")]})())

    assert story.hook == "Even messy inputs collapse into a single result."
    assert story.sections[0]["heading"] == "The procedure"
    assert story.takeaway == "Simple rules can create hidden order."


def test_renderer_uses_editorial_sections_and_palette():
    source = Source("A source", "https://example.com", "")
    stories = [CuriosityStory(
        "Topic 1",
        "History",
        "First paragraph.\n\nSecond paragraph.",
        "Remember this.",
        [source],
        hook="A surprising historical pattern.",
        sections=[{"heading": "What happened", "content": "First paragraph.\n\nSecond paragraph."}],
    ) for _ in range(3)]
    html = render_html(DailyMagazine("Good morning <friend>", stories, [], "Why do some clocks run backwards?"))

    assert "#4997A9" in html
    assert "#E4DFBF" in html
    assert "What happened" in html
    assert "Tomorrow's rabbit hole" in html
    assert "Your Daily Curiosity" in html
    assert "Good morning &lt;friend&gt;" in html


def test_renderer_creates_safe_gmail_html_with_three_stories():
    source = Source("A source", "https://example.com", "")
    stories = [CuriosityStory(f"Topic {number}", "History", "First paragraph.\n\nSecond paragraph.", "Remember this.", [source]) for number in range(1, 4)]
    html = render_html(DailyMagazine("Good morning <friend>", stories, [], "Why do some clocks run backwards?"))

    assert "Your Daily Curiosity" in html
    assert "Good morning &lt;friend&gt;" in html
    assert html.count("Takeaway:") == 3
    assert "What Happened in the Last 24 Hours" not in html


def test_renderer_requires_exactly_three_stories():
    with pytest.raises(ValueError, match="exactly three"):
        render_html(DailyMagazine("Hello", [], [], "Question?"))
