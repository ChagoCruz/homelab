from __future__ import annotations

from typing import Any
import json
import os

from anthropic import Anthropic
from fastapi import HTTPException

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="AI insights unavailable: ANTHROPIC_API_KEY is not configured.",
            )
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _truncate_text(text: str, max_chars: int = 2500) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Truncated for analysis]"


def _message(system_prompt: str, user_prompt: str, max_tokens: int = 900) -> str:
    try:
        response = _get_client().messages.create(
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

        parts: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)

        text = "\n".join(parts).strip()
        if not text:
            raise HTTPException(status_code=502, detail="Claude returned an empty response.")
        return text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude request failed: {e}")


def _extract_json(text: str) -> dict[str, Any]:
    """
    Attempts to parse a JSON object from the model output.
    """
    text = text.strip()

    # direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # fallback: find first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise HTTPException(
        status_code=502,
        detail="Claude returned invalid JSON for structured journal analysis.",
    )


ENTRY_ANALYSIS_SYSTEM_PROMPT = """
You are a reflective personal therapist and life analyst.

Your role is not to judge or diagnose, but to help the user understand patterns
in their thoughts, emotions, and behaviors.

Analyze the following journal entry.

Focus on identifying:

Emotional signals
- emotional tone
- key emotions
- possible underlying feelings

Positive signals
- positive moments
- motivation
- creative excitement
- progress or growth

Stress signals
- possible stressors
- burnout signals
- self doubt
- perfectionism
- frustration

Behavioral patterns
- recurring motivations
- repeated concerns
- thinking patterns
- motivation cycles

Life direction signals
- career interests
- creative interests
- personal values
- long-term motivations

Also generate:
- a mood score from -5 to 5
- three thoughtful reflection questions that help the user explore their thoughts more deeply
- a short therapist-style insight (maximum 2 sentences)
- gentle encouragement or perspective (not prescriptive advice)

Return ONLY valid JSON with the following structure:

{
  "mood_score": 0,
  "emotional_tone": "",
  "key_emotions": [],
  "stressors": [],
  "positive_signals": [],
  "thinking_patterns": [],
  "life_direction_signals": [],
  "insight": "",
  "reflection_questions": [],
  "encouragement": ""
}

If information is not present in the journal entry, return an empty array or empty string rather than guessing.
""".strip()


LONG_TERM_PROFILE_SYSTEM_PROMPT = """
You are a reflective personal therapist and long-term life pattern analyst.

Your role is not to judge or diagnose, but to identify recurring emotional,
behavioral, motivational, and value-based patterns over time.

You are analyzing multiple journal entry analyses from the same person across a period of time.

Your goal is to identify stable and recurring patterns, not isolated one-time reactions.

Focus on identifying:

Emotional trends
- dominant emotional tones
- repeated emotional states
- average mood pattern over time

Recurring stress patterns
- repeated stressors
- burnout signals
- sources of frustration or emotional drain

Recurring positive patterns
- moments of motivation
- sources of energy
- activities or thoughts associated with improved mood

Thinking and behavior patterns
- self doubt
- perfectionism
- motivation cycles
- avoidance patterns
- persistence
- creative excitement
- emotional recovery patterns

Life direction signals
- recurring career interests
- recurring creative interests
- long-term motivations
- personal values
- themes that appear meaningful over time

Growth and risk signals
- signs of progress
- signs of resilience
- signs of increased clarity
- possible recurring negative loops
- possible pressure points that may deserve reflection

Generate a grounded long-term pattern model based only on the information provided.

Return ONLY valid JSON with the following structure:

{
  "average_mood_score": 0,
  "dominant_emotions": [],
  "recurring_stressors": [],
  "recurring_positive_signals": [],
  "recurring_thinking_patterns": [],
  "recurring_life_direction_signals": [],
  "core_values": [],
  "motivation_drivers": [],
  "growth_signals": [],
  "risk_signals": [],
  "pattern_summary": ""
}

Rules:
- Base conclusions only on repeated or supported patterns across entries.
- Do not diagnose mental health conditions or assign fixed personality labels.
- Do not overstate certainty.
- If a pattern is weak or unclear, omit it or return an empty array.
- If information is not present in the journal analyses, return an empty array or empty string rather than guessing.
""".strip()


def analyze_journal_entry_structured(entry: dict[str, Any]) -> dict[str, Any]:
    content = _truncate_text(entry.get("content", ""), max_chars=2500)

    user_prompt = (
        "Journal entry:\n"
        f"Entry date: {entry['entry_date']}\n"
        f"Content:\n{content}\n"
    )

    raw = _message(
        system_prompt=ENTRY_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=900,
    )
    return _extract_json(raw)


def build_journal_pattern_profile(
    analyses: list[dict[str, Any]],
    period_type: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    serialized = {
        "period_type": period_type,
        "period_start": period_start,
        "period_end": period_end,
        "analyses": analyses,
    }

    raw = _message(
        system_prompt=LONG_TERM_PROFILE_SYSTEM_PROMPT,
        user_prompt=f"Journal entry analyses:\n{json.dumps(serialized, default=str)}",
        max_tokens=1100,
    )
    return _extract_json(raw)