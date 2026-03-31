from __future__ import annotations

from typing import Any, Optional
import json
import os
import re

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


def _extract_first_balanced_object(text: str) -> Optional[str]:
    """
    Finds the first balanced JSON object-like block in a string.
    """
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False

        for idx in range(start, len(text)):
            char = text[idx]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == "\"":
                    in_string = False
                continue

            if char == "\"":
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]

        start = text.find("{", start + 1)

    return None


def _normalize_json_candidate(candidate: str) -> str:
    normalized = candidate.strip()
    normalized = normalized.replace("\ufeff", "")
    normalized = normalized.replace("“", "\"").replace("”", "\"")
    normalized = normalized.replace("‘", "'").replace("’", "'")

    if normalized.lower().startswith("json\n"):
        normalized = normalized.split("\n", 1)[1]

    # Common model mistake: trailing commas in JSON objects/arrays.
    normalized = re.sub(r",\s*([}\]])", r"\1", normalized)
    return normalized


def _iter_json_candidates(text: str):
    seen = set()

    def _yield(candidate: str):
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            return
        seen.add(candidate)
        yield candidate

    stripped = text.strip()
    for candidate in _yield(stripped):
        yield candidate

    fences = re.findall(r"```(?:json)?\s*([\s\S]*?)```", stripped, flags=re.IGNORECASE)
    for fenced in fences:
        for candidate in _yield(fenced):
            yield candidate

    balanced = _extract_first_balanced_object(stripped)
    if balanced:
        for candidate in _yield(balanced):
            yield candidate

    for fenced in fences:
        balanced_fenced = _extract_first_balanced_object(fenced)
        if balanced_fenced:
            for candidate in _yield(balanced_fenced):
                yield candidate


def _parse_json_dict(candidate: str) -> Optional[dict[str, Any]]:
    attempts = [candidate, _normalize_json_candidate(candidate)]
    for attempt in attempts:
        try:
            data = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


JSON_REPAIR_SYSTEM_PROMPT = """
You are a strict JSON repair utility.

You will receive malformed or noisy text that is intended to represent a JSON object.
Return ONLY one valid JSON object.

Rules:
- Keep the original keys and values whenever possible.
- Do not add markdown, prose, or code fences.
- If a value is unclear, preserve it as a string.
- If there is no recoverable object, return {}.
""".strip()


def _extract_json(text: str, allow_repair: bool = True) -> dict[str, Any]:
    """
    Attempts to parse a JSON object from the model output.
    """
    text = text.strip()

    for candidate in _iter_json_candidates(text):
        parsed = _parse_json_dict(candidate)
        if parsed is not None:
            return parsed

    if allow_repair:
        try:
            repaired = _message(
                system_prompt=JSON_REPAIR_SYSTEM_PROMPT,
                user_prompt=f"Repair this output into valid JSON:\n\n{text}",
                max_tokens=1200,
            )
            return _extract_json(repaired, allow_repair=False)
        except HTTPException:
            pass

    raise HTTPException(
        status_code=502,
        detail="Claude returned invalid JSON for structured output.",
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

JOURNAL_SUMMARY_SYSTEM_PROMPT = """
You are a reflective therapist helping someone understand the emotional and psychological story of their recent experiences.

You are summarizing multiple journal entry analyses across a time period.

Your goal is to gently describe what this period felt like, what themes emerged,
and what emotional shifts or patterns may have been present.

Return ONLY valid JSON in this shape:

{
  "summary": "",
  "themes": [],
  "emotional_trends": [],
  "stress_patterns": [],
  "positive_patterns": [],
  "direction_signals": [],
  "reflection_questions": []
}

Field guidance:
- summary: a warm, reflective narrative (3–6 sentences) describing the emotional arc of the period
- themes: recurring themes or concerns
- emotional_trends: shifts or repeated emotional tendencies over time
- stress_patterns: repeated sources of tension or pressure
- positive_patterns: moments of relief, growth, motivation, or clarity
- direction_signals: signals about values, interests, or life direction
- reflection_questions: 2–4 thoughtful questions to help the user reflect deeper

Tone:
- calm, grounded, and therapist-like
- not overly clinical or robotic
- not overly poetic or dramatic

Rules:
- Base conclusions only on the provided analyses
- Do not diagnose or label the user
- Do not overstate certainty
- If a pattern is weak, omit it
"""


LONG_TERM_PROFILE_SYSTEM_PROMPT = """
You are a reflective therapist and long-term life pattern analyst.

Your role is to help the user understand recurring emotional, behavioral,
and motivational patterns across time.

You are analyzing multiple journal entry analyses from the same person.

Focus on identifying patterns that feel stable or repeatedly present,
rather than one-time reactions.

Your goal is to help the user see themselves more clearly.

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

WEEKLY_BEHAVIORAL_INSIGHT_SYSTEM_PROMPT = """
You are a behavioral analytics engine.

INPUT:
- weekly_behavior_metrics: structured weekly metrics
- aggregated_journal_analysis: aggregated outputs from individual journal-entry analyses
- unified_correlations: computed cross-domain relationships with comparable scoring across:
  - behavior -> mood
  - behavior -> blood pressure
  - weather -> mood
  - weather -> blood pressure
  - substance (safety_meeting) -> mood
  - substance (safety_meeting) -> blood pressure

TASK:
1. Identify the top 3 drivers this week across mood and health where evidence is strongest.
2. Identify the 2 strongest correlations using BOTH effect size and confidence.
3. Detect recurring patterns or feedback loops
4. Flag any risks or destabilizers
5. Provide 3 specific actionable recommendations for next week

CONSTRAINTS:
- Use only structured data.
- Do not retell events.
- Do not summarize narrative.
- Be concise.
- Prefer patterns, drivers, and signal strength over interpretation.
- If evidence is weak, say so.
- Distinguish same-day effects from next-day effects.
- Include weather and blood-pressure relationships when evidence is sufficient.
- Include safety_meeting (weed/cannabis) relationships when evidence is sufficient.
- Be cautious about reverse causality for substance-use and mood.
- Do not overemphasize low-confidence signals.

Return ONLY valid JSON with this structure:
{
  "system_state": "",
  "top_drivers": [
    { "driver": "", "evidence": "" }
  ],
  "correlations": [
    { "correlation": "", "strength": "weak", "interpretation": "" }
  ],
  "patterns": [],
  "risk_flags": [],
  "recommendations": [],
  "evidence_quality": ""
}

Rules:
- top_drivers: maximum 3 items.
- correlations: maximum 2 items.
- strength must be one of: weak, moderate, strong.
- recommendations: exactly 3 concise actions when possible.
- Prefer medium/high-confidence correlations in "correlations" unless all signals are low confidence.
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

def build_journal_period_summary(
    analyses: list[dict[str, Any]],
    period_type: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    payload = {
        "period_type": period_type,
        "period_start": period_start,
        "period_end": period_end,
        "analyses": analyses,
    }

    raw = _message(
        system_prompt=JOURNAL_SUMMARY_SYSTEM_PROMPT,
        user_prompt=f"Journal entry analyses:\n{json.dumps(payload, default=str)}",
        max_tokens=1100,
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


def build_weekly_behavioral_insight(
    payload: dict[str, Any],
) -> dict[str, Any]:
    raw = _message(
        system_prompt=WEEKLY_BEHAVIORAL_INSIGHT_SYSTEM_PROMPT,
        user_prompt=f"Weekly structured payload:\n{json.dumps(payload, default=str)}",
        max_tokens=1100,
    )
    return _extract_json(raw)


def format_weekly_behavioral_insight(structured: dict[str, Any]) -> str:
    top_drivers = structured.get("top_drivers")
    if not isinstance(top_drivers, list):
        top_drivers = []

    correlations = structured.get("correlations")
    if not isinstance(correlations, list):
        correlations = []

    patterns = structured.get("patterns")
    if not isinstance(patterns, list):
        patterns = []

    risk_flags = structured.get("risk_flags")
    if not isinstance(risk_flags, list):
        risk_flags = []

    recommendations = structured.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []

    system_state = str(structured.get("system_state") or "").strip()
    has_any_structured_sections = any(
        [
            any(isinstance(item, dict) and str(item.get("driver") or "").strip() for item in top_drivers),
            any(isinstance(item, dict) and str(item.get("correlation") or "").strip() for item in correlations),
            any(str(item).strip() for item in patterns),
            any(str(item).strip() for item in risk_flags),
            any(str(item).strip() for item in recommendations),
        ]
    )
    if not system_state:
        system_state = (
            "Unified analytics signal was sufficient to identify recurring drivers this week."
            if has_any_structured_sections
            else "Signal is limited this week."
        )

    lines = [
        "[ SYSTEM_STATE ]",
        system_state,
        "",
        "[ TOP_DRIVERS ]",
    ]

    driver_items = [item for item in top_drivers[:3] if isinstance(item, dict)]
    if driver_items:
        for item in driver_items:
            driver = str(item.get("driver") or "Insufficient signal")
            evidence = str(item.get("evidence") or "Structured evidence is limited.")
            lines.append(f"* driver: {driver}")
            lines.append(f"  evidence: {evidence}")
    else:
        lines.append("* driver: Insufficient signal")
        lines.append("  evidence: Not enough structured evidence this week.")

    lines.append("")
    lines.append("[ CORRELATIONS ]")
    correlation_items = [item for item in correlations[:2] if isinstance(item, dict)]
    if correlation_items:
        for item in correlation_items:
            correlation = str(item.get("correlation") or "Insufficient signal")
            strength = str(item.get("strength") or "weak").lower()
            if strength not in {"weak", "moderate", "strong"}:
                strength = "weak"
            interpretation = str(item.get("interpretation") or "Limited signal.")
            interpretation = re.sub(r"\s*Confidence\s*(?:is|:)\s*[^.]+\.?", "", interpretation, flags=re.IGNORECASE).strip()
            confidence = str(item.get("confidence") or "").strip().lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = ""
            sample_size = item.get("sample_size") if isinstance(item.get("sample_size"), dict) else {}
            group_a_n = int(sample_size.get("group_a") or 0) if sample_size else 0
            group_b_n = int(sample_size.get("group_b") or 0) if sample_size else 0
            sample_suffix = f" (n={group_a_n} vs n={group_b_n})" if (group_a_n or group_b_n) else ""
            lines.append(f"* correlation: {correlation}")
            lines.append(f"  strength: {strength}")
            if confidence:
                lines.append(f"  confidence: {confidence}{sample_suffix}")
            elif sample_suffix:
                lines.append(f"  sample_size: n={group_a_n} vs n={group_b_n}")
            lines.append(f"  interpretation: {interpretation}")
    else:
        lines.append("* correlation: Insufficient signal")
        lines.append("  strength: weak")
        lines.append("  confidence: low")
        lines.append("  interpretation: Not enough structured evidence this week.")

    lines.append("")
    lines.append("[ PATTERNS ]")
    if patterns:
        for item in patterns[:4]:
            lines.append(f"* {str(item)}")
    else:
        lines.append("* No recurring pattern met confidence threshold.")

    lines.append("")
    lines.append("[ RISK_FLAGS ]")
    if risk_flags:
        for item in risk_flags[:4]:
            lines.append(f"* {str(item)}")
    else:
        lines.append("* No clear risk flag from available structured data.")

    lines.append("")
    lines.append("[ RECOMMENDATIONS ]")
    if recommendations:
        for item in recommendations[:3]:
            lines.append(f"* {str(item)}")
    else:
        lines.append("* Keep data collection consistent for stronger signals next week.")

    return "\n".join(lines).strip()
