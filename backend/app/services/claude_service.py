from typing import Any
import os

from anthropic import Anthropic
from fastapi import HTTPException

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY is not set")

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def _truncate_text(text: str, max_chars: int = 2500) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Truncated for analysis]"


def _message(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )

        parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)

        text = "\n".join(parts).strip()

        if not text:
            raise HTTPException(status_code=502, detail="Claude returned an empty response.")

        return text

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude request failed: {e}")


def generate_journal_entry_analysis(entry: dict[str, Any]) -> str:
    content = _truncate_text(entry.get("content", ""), max_chars=2500)

    system_prompt = (
        "You are a reflective journaling assistant for a personal analytics app. "
        "Do not diagnose mental health conditions. "
        "Do not sound like a therapist. "
        "Identify themes, emotional tone, possible stressors, positive signals, and one reflection question. "
        "Be grounded, concise, and specific to the text. "
        "Keep the total response under 250 words. "
        "Return markdown with these exact headings: "
        "Summary, Themes, Emotional tone, Possible stressors, Positive signals, Reflection question."
    )

    user_prompt = (
        "Analyze this single journal entry.\n\n"
        f"Entry date: {entry['entry_date']}\n"
        f"Word count: {entry['word_count']}\n\n"
        f"Content:\n{content}"
    )

    return _message(system_prompt, user_prompt, max_tokens=500)


def generate_journal_period_summary(entries: list[dict[str, Any]]) -> str:
    serialized_entries = []

    for entry in entries:
        serialized_entries.append(
            {
                "journal_id": entry["journal_id"],
                "entry_date": str(entry["entry_date"]),
                "word_count": entry["word_count"],
                "content": _truncate_text(entry.get("content", ""), max_chars=1800),
            }
        )

    system_prompt = (
        "You are a reflective journaling assistant for a personal analytics app. "
        "Do not diagnose or moralize. "
        "Summarize recurring themes across multiple journal entries. "
        "Highlight repeated concerns, positive momentum, shifts in tone, and one useful reflection question. "
        "Keep the response under 300 words. "
        "Return markdown with these exact headings: "
        "Weekly summary, Recurring themes, Tone shifts, Positive momentum, Reflection question."
    )

    user_prompt = (
        "Analyze these journal entries from one period.\n\n"
        f"{serialized_entries}"
    )

    return _message(system_prompt, user_prompt, max_tokens=650)


def generate_weekly_health_insight(metrics: dict[str, Any]) -> str:
    system_prompt = (
        "You are a careful health analytics assistant. "
        "Summarize structured health data clearly and cautiously. "
        "Do not diagnose or give medical advice. "
        "Use language like 'associated with', 'tends to', or 'may indicate'. "
        "Return a short report with a summary paragraph, three bullet observations, and one gentle suggestion."
    )

    user_prompt = f"Weekly health metrics:\n{metrics}"

    return _message(system_prompt, user_prompt, max_tokens=500)