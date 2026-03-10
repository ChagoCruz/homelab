import json
import os
import requests
from typing import Any

OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


def _chat(messages: list[dict[str, str]]) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "messages": messages,
        },
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


def generate_weekly_report(metrics: dict[str, Any]) -> str:
    system_prompt = (
        "You are a careful health analytics assistant. "
        "Summarize structured health data clearly and cautiously. "
        "Do not diagnose or give medical advice. "
        "Use language like 'associated with', 'tends to', or 'may indicate'. "
        "Return a short report with a short summary paragraph, "
        "three bullet observations, and one gentle suggestion."
    )
    return _chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Weekly metrics:\n{metrics}"},
    ])


def generate_journal_entry_analysis(entry: dict[str, Any]) -> str:
    system_prompt = (
        "You are a reflective journaling assistant for a personal analytics app. "
        "Do not diagnose mental health conditions. "
        "Do not sound like a therapist or give crisis advice unless explicitly asked. "
        "Identify themes, emotional tone, stressors, positive signals, and one reflection question. "
        "Be grounded, concise, and specific to the text. "
        "Return markdown with these exact headings: "
        "Summary, Themes, Emotional tone, Possible stressors, Positive signals, Reflection question."
    )

    user_prompt = (
        "Analyze this single journal entry.\n\n"
        f"Entry date: {entry['entry_date']}\n"
        f"Word count: {entry['word_count']}\n\n"
        f"Content:\n{entry['content']}"
    )

    return _chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])


def generate_journal_period_summary(entries: list[dict[str, Any]]) -> str:
    system_prompt = (
        "You are a reflective journaling assistant for a personal analytics app. "
        "Do not diagnose or moralize. "
        "Summarize recurring themes across multiple journal entries. "
        "Highlight repeated concerns, positive momentum, shifts in tone, and one useful reflection question. "
        "Return markdown with these exact headings: "
        "Weekly summary, Recurring themes, Tone shifts, Positive momentum, Reflection question."
    )

    serialized = json.dumps(entries, default=str, indent=2)

    return _chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze these journal entries from one period:\n{serialized}"},
    ])