"""Command-line entry point for configuration checks, a demo render, or one complete daily run."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.bootstrap import build_services
from app.config import ConfigurationError, get_settings
from app.email.models import DailyMagazine
from app.email.renderer import render_html
from app.logging_config import configure_logging
from app.memory.mongo import MongoConnectionError, MongoRepository
from app.news.models import NewsItem
from app.orchestration.workflow import DailyWorkflow
from app.research.models import Source
from app.story.models import CuriosityStory


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Daily Curiosity Agent.")
    parser.add_argument("--check", action="store_true", help="Validate configuration and MongoDB Atlas without generating or sending anything.")
    parser.add_argument("--demo", action="store_true", help="Render a sample HTML email without MongoDB, API calls, or Gmail.")
    parser.add_argument("--demo-output", default="daily-curiosity-demo.html", help="File path for the demo HTML output.")
    args = parser.parse_args()

    if args.demo:
        output_path = Path(args.demo_output)
        magazine = DailyMagazine(
            greeting="Good morning — here are three ideas worth carrying through your day.",
            stories=[
                CuriosityStory(
                    title="Why the Dvorak keyboard still feels like a better idea",
                    category="Design",
                    body="The QWERTY layout was not designed for speed. It was created to slow typists down on early typewriters so the mechanical arms would not jam. The Dvorak layout, developed later, places the most common letters on the home row and keeps the most-used combinations within easy reach. That sounds like a small ergonomic tweak, but it reveals something larger: a default design choice can outlive its historical context and keep shaping modern behavior long after the original problem disappears.\n\nIn practical terms, Dvorak is not magic. It is a more deliberate arrangement of letters for speed and comfort. It also makes the point that the tools we accept as natural are often simply the ones we inherited. When an interface is optimized for a different era, it can quietly impose costs on everyone who uses it.\n\nThe reason this remains interesting is not because Dvorak was a perfect invention, but because it demonstrates how invisible defaults become normal. A layout that was once a technical workaround remains a reminder that efficiency is not just about raw speed; it is also about the everyday friction of the systems we live with.\n\nThe broader lesson is that modern interfaces often reflect historical accidents more than deliberate choices. When we see a conventional arrangement that feels awkward, the real question is not whether it is 'bad' but why it became standard in the first place. Dvorak is a good example of a system that was improved, but not necessarily adopted, because a default can be hard to uproot even when a better one exists.",
                    hook="A keyboard layout designed for Victorian-era typewriters still shapes the way modern hands move across the keys.",
                    sections=[
                        {"heading": "The hidden design problem", "content": "The QWERTY layout was not created because it was the most efficient arrangement. It was designed to prevent early mechanical typewriters from jamming by placing common letters apart. Over time, that compromise became normal. This is one of the easiest ways to see how historical constraints can become invisible defaults."},
                        {"heading": "Why Dvorak changed the equation", "content": "The Dvorak layout was built around a different principle: put the most-used letters in the home row and keep frequent letter pairs accessible. The result is a layout that can reduce finger travel and make touch typing feel more natural. It is not a dramatic transformation, but it is a concrete demonstration that there is often a better fit than the one we inherited."},
                        {"heading": "Why it still matters", "content": "The interesting part is not that Dvorak is universally superior in every setting. It is that the default interface we accept is often an old compromise we never stopped to question. In technology, many systems work this way: the familiar version persists because it is familiar, not because it is optimal."},
                    ],
                    takeaway="The most important lesson is not about keyboards alone. It is about how old design decisions can become the quiet architecture of everyday life, even when better options exist.",
                    sources=[Source("Wikipedia: Dvorak keyboard layout", "https://en.wikipedia.org/wiki/Dvorak_Simplified_Keyboard", ""), Source("Keyboard layout history", "https://www.w3.org/2022/09/keyboard-layouts.html", "")],
                ),
                CuriosityStory(
                    title="How a four-digit trick quietly reveals order inside chaos",
                    category="Mathematics",
                    body="Kaprekar's constant starts with a simple procedure: take any 4-digit number with at least two different digits, reorder the digits to make the largest and smallest versions, subtract the smaller from the larger, and repeat. At first glance, it looks like a quirky puzzle. But the reason it captivates mathematicians is that it behaves like a tiny system with hidden structure.\n\nTake 3524. Rearranged as 5432 and 2345, the subtraction is 3087. Now repeat the process: 8730 - 0378 = 8352. Then 8532 - 2358 = 6174. Once the number reaches 6174, the process settles into a cycle: 7641 - 1467 = 6174, and from there the same result appears again.\n\nThat is the surprising part. A whole range of starting numbers, even messy ones, eventually collapse into the same value. The system is not random at all; it has a stable attractor. In other words, many different paths converge to one outcome. That makes it feel like a tiny mathematical gravity well.\n\nThe deeper fascination is that the procedure is simple enough for a child to carry out, but the behavior is not obvious from the start. It is a reminder that complex-looking patterns can emerge from elementary rules. Mathematicians like this because it gives a concrete example of how rough, chaotic-looking inputs can still settle into a predictable state.\n\nIt also matters beyond the puzzle itself. The idea of convergence is central to many fields: computer science, dynamical systems, statistics, and even economics. The world may look messy, but some systems keep drawing themselves back toward a stable pattern. Kaprekar's routine is an elegant and visual way to see that principle in action.",
                    hook="A number puzzle that feels like a trick turns out to be a miniature lesson in how systems settle into order.",
                    sections=[
                        {"heading": "The process", "content": "Choose any 4-digit number with at least two different digits. Order the digits to make the biggest and smallest versions. Subtract the smaller number from the larger. Repeat. The sequence is not arbitrary, and the same destination keeps appearing in many different starting cases."},
                        {"heading": "The striking convergence", "content": "For example, 3524 becomes 3087, then 8352, then 6174. Once 6174 is reached, the process locks in. This is the defining curiosity of Kaprekar's routine: a broad range of inputs collapse into one outcome."},
                        {"heading": "Why it matters", "content": "The lesson is not just that arithmetic can be surprising. It is that simple systems often reveal a deeper structure once you watch them long enough. Mathematicians use that idea to understand stability, attractors, and convergence in far more complex domains."},
                    ],
                    takeaway="The puzzle is really a lesson in hidden order: small rules can produce large structure, and even messy-looking systems often settle into a surprisingly stable pattern.",
                    sources=[Source("Kaprekar's routine", "https://en.wikipedia.org/wiki/Kaprekar%27s_routine", ""), Source("Number theory and digits", "https://mathworld.wolfram.com/KaprekarRoutine.html", "")],
                ),
                CuriosityStory(
                    title="Why a policy meant to reduce a problem can accidentally make it worse",
                    category="Economics",
                    body="The cobra effect is the classic example of an incentive accidentally creating the very problem it was meant to solve. In colonial India, the British government offered a bounty for dead cobras. The policy was meant to reduce the cobra population, but the result was not simply fewer snakes. Some people began breeding cobras to collect the reward, turning the policy into a supply chain for the thing it was trying to eliminate.\n\nThat is the unsettling part: the system responded to the incentive, not the underlying goal. The official intention was to reduce the number of cobras in the wild. The actual behavior of the people involved was shaped by what the policy paid for. Once breeding became profitable, the incentive rewired the local economy.\n\nThis example matters because it is not a one-off historical anecdote. It shows how policy design can fail when the incentive structure is misaligned with the real goal. A reward based on the visible symptom can encourage more of the symptom, even if the broader objective is to improve the situation. In economics and public policy, this is why incentives are so important. A system can look logical on paper and still produce perverse outcomes when people adapt to the rules.\n\nThe broader lesson is that good intentions are not enough. If a reward is tied to the wrong metric, people will optimize for the metric, not for the real outcome. This is why economists so often stress the difference between a goal and a measurable proxy. The policy may have been built around a simple solution, but human behavior is rarely so simple.\n\nThe cobra effect is memorable because it shows the world in miniature: rules shape behavior, behavior changes the system, and the system may end up defeating the policy's intention. That is why well-designed incentives matter so much in markets, organizations, and governments.",
                    hook="A bounty intended to cut a problem down ended up creating more of it — and that is exactly why the lesson still matters.",
                    sections=[
                        {"heading": "What happened", "content": "The policy paid people for dead cobras, but the reward was attached to outcomes that could be gamed. As a result, some individuals turned the program into a breeding scheme, which made the problem worse rather than better."},
                        {"heading": "Why incentives matter", "content": "The real issue was not hostility to the policy but the way it changed behavior. Once profit depended on producing the target outcome, the system began optimizing for the reward rather than the original intention."},
                        {"heading": "The wider lesson", "content": "Modern policy, product design, and business incentives all face the same risk. A well-meaning metric can produce the wrong behavior if it is disconnected from the real objective."},
                    ],
                    takeaway="The cobra effect is not just a historical curiosity; it is a warning that incentives can distort a system far more powerfully than good intentions ever can.",
                    sources=[Source("Cobra effect", "https://en.wikipedia.org/wiki/Cobra_effect", ""), Source("Behavioral economics and incentives", "https://www.behavioraleconomics.com/", "")],
                ),
            ],
            news=[NewsItem(headline="A short policy update from the field", summary="This demo uses an example briefing that keeps the daily news section concise and readable.", significance="It highlights the difference between a rich curiosity article and a quick briefing summary.", sources=[Source("Demo brief source", "https://example.com/demo-news", "")])],
            rabbit_hole_question="Why do so many everyday systems settle into defaults that feel older than the people using them?",
        )
        output_path.write_text(render_html(magazine), encoding="utf-8")
        print(f"Demo email written to {output_path}")
        return 0

    try:
        settings = get_settings()
    except ConfigurationError as error:
        print(f"Configuration error: {error}")
        return 2

    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Phase 1 startup", extra={"event": "app_started"})

    repository = MongoRepository(settings.mongo_uri, settings.mongo_database)
    try:
        repository.connect()
    except MongoConnectionError as error:
        logger.error(str(error), extra={"event": "mongo_connection_failed"})
        return 1

    logger.info(
        "MongoDB Atlas connection verified",
        extra={"event": "mongo_connected"},
    )
    if args.check:
        return 0
    try:
        result = DailyWorkflow(build_services(settings), timezone=settings.timezone).run()
    except Exception:
        logger.exception("Daily workflow failed", extra={"event": "daily_workflow_failed"})
        return 1
    logger.info(f"Daily workflow result: {result.status}", extra={"event": "daily_workflow_result"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
