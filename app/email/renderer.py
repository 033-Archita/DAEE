"""Editorial-style HTML email for the Daily Curiosity publication."""

from __future__ import annotations

from html import escape
from urllib.parse import urlparse

from app.email.models import DailyMagazine
from app.research.models import Source

PRIMARY_TEAL = "#4997A9"
PARCHMENT = "#E4DFBF"
ACCENT_PINK = "#F68299"
TEXT_DEEP = "#253238"
MUTED = "#5A6A6F"


def _safe_url(url: str) -> str:
    return url if urlparse(url).scheme in {"http", "https"} else "#"


def _paragraphs(text: str) -> str:
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not parts:
        return ""
    return "".join(
        f'<p style="margin:0 0 18px; font-size:16px; line-height:1.8; color:{TEXT_DEEP};">{escape(part)}</p>'
        for part in parts
    )


def _sources(sources: list[Source]) -> str:
    if not sources:
        return ""
    links = "".join(
        f'<li style="margin:0 0 8px; color:{TEXT_DEEP};"><a href="{escape(_safe_url(source.url), quote=True)}" style="color:{PRIMARY_TEAL}; text-decoration:none;">{escape(source.title)}</a></li>'
        for source in sources[:6]
    )
    return (
        f'<div style="margin-top:18px"><p style="font-size:12px;letter-spacing:1.2px;text-transform:uppercase;color:{MUTED};margin:0 0 10px"><strong>Sources</strong></p>'
        f'<ul style="margin:0;padding-left:18px">{links}</ul></div>'
    )


def _render_sections(story) -> str:
    sections = story.sectioned_body()
    if not sections:
        return _paragraphs(story.body)
    rendered = []
    for section in sections:
        heading = str(section.get("heading") or "What to know").strip()
        content = str(section.get("content") or "").strip()
        rendered.append(
            f'<div style="margin-top:22px"><p style="margin:0 0 8px;color:{PRIMARY_TEAL};font-size:12px;letter-spacing:1.2px;text-transform:uppercase;font-weight:bold">{escape(heading)}</p>{_paragraphs(content)}</div>'
        )
    return "".join(rendered)


def render_html(magazine: DailyMagazine) -> str:
    """Render exactly three curiosity stories and an optional compact news section."""
    if len(magazine.stories) != 3:
        raise ValueError("A daily magazine must contain exactly three curiosity stories.")
    stories = ""
    for number, story in enumerate(magazine.stories, start=1):
        hook = story.hook.strip() if story.hook else ""
        hook_html = f'<p style="margin:0 0 20px; font-size:16px; line-height:1.75; color:{TEXT_DEEP}; font-style:italic;">{escape(hook)}</p>' if hook else ""
        stories += (
            f'<section style="padding:26px 0; border-bottom:1px solid #d7d0b1"><p style="margin:0 0 10px; color:{ACCENT_PINK}; font-size:12px; letter-spacing:2px; text-transform:uppercase; font-weight:bold">{number}</p>'
            f'<p style="margin:0 0 8px; color:{PRIMARY_TEAL}; font-size:12px; letter-spacing:1.2px; text-transform:uppercase; font-weight:bold">{escape(story.category)}</p>'
            f'<h2 style="font-size:30px; line-height:1.15; margin:0 0 18px; color:{TEXT_DEEP}; font-weight:700">{escape(story.title)}</h2>{hook_html}{_render_sections(story)}'
            f'<p style="margin:22px 0 0; padding:14px 16px; background:#f3efe0; border-left:4px solid {ACCENT_PINK}; color:{TEXT_DEEP}; font-size:15px; line-height:1.7"><strong style="color:{PRIMARY_TEAL}">Takeaway:</strong> {escape(story.takeaway)}</p>{_sources(story.sources)}</section>'
        )
    news = ""
    if magazine.news:
        items = "".join(
            f'<li style="margin:0 0 18px; padding-bottom:12px; border-bottom:1px solid #d7d0b1"><p style="margin:0 0 8px"><strong style="color:{TEXT_DEEP}; font-size:17px">{escape(item.headline)}</strong></p>'
            f'<p style="margin:0 0 8px; color:{TEXT_DEEP}; font-size:15px; line-height:1.7">{escape(item.summary)}</p>'
            f'{f"<p style=\"margin:0 0 8px; color:{MUTED}; font-size:14px; line-height:1.6\"><strong>Why it matters:</strong> {escape(item.significance)}</p>" if item.significance else ""}'
            f'{_sources(item.sources)}</li>'
            for item in magazine.news
        )
        news = f'<section style="padding:28px 0; border-bottom:1px solid #d7d0b1"><p style="margin:0 0 14px; color:{PRIMARY_TEAL}; font-size:12px; letter-spacing:1.5px; text-transform:uppercase; font-weight:bold">What Happened in the Last 24 Hours?</p><ul style="padding-left:18px; margin:0; list-style:none">{items}</ul></section>'
    return (
        '<!doctype html><html><body style="margin:0;background:#E4DFBF;font-family:Arial,Helvetica,sans-serif;color:#253238;">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:720px;background:#f8f3e7;border:1px solid #d7d0b1"><tr><td style="padding:34px 30px">'
        f'<p style="margin:0 0 12px; color:{ACCENT_PINK}; font-size:12px; letter-spacing:2px; text-transform:uppercase; font-weight:bold">Daily briefing</p>'
        f'<h1 style="font-size:34px; margin:0 0 10px; color:{TEXT_DEEP}; font-weight:700; line-height:1.1">Your Daily Curiosity</h1>'
        f'<p style="font-size:16px; line-height:1.7; color:{TEXT_DEEP}; margin:0 0 10px">{escape(magazine.greeting)}</p>{stories}{news}'
        f'<section style="padding:28px 0 0"><p style="margin:0 0 10px; color:{ACCENT_PINK}; font-size:12px; letter-spacing:1.7px; text-transform:uppercase; font-weight:bold">Tomorrow\'s rabbit hole</p><p style="font-size:20px; line-height:1.5; margin:0; color:{TEXT_DEEP};"><strong style="color:{PRIMARY_TEAL}">🐇</strong> {escape(magazine.rabbit_hole_question)}</p></section>'
        '</td></tr></table></td></tr></table></body></html>'
    )
