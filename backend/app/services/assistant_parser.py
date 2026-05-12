import json
import os
from typing import Literal

import requests
from pydantic import BaseModel, Field


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


class AssistantParse(BaseModel):
    intent: Literal[
        "estimate_calories",
        "add_diet_entry",
        "weekly_calorie_average",
        "highest_calorie_days",
        "weekly_summary",
        "blood_pressure_trend",
        "workout_mood_correlation",
        "confirm_action",
        "unknown",
    ] = Field(description="The user's intended assistant action.")

    foods: list[str] = Field(default_factory=list)
    meal: str | None = None
    date_range: str | None = None
    confirmation: Literal["yes", "no"] | None = None
    original_message: str


def _schema_for_ollama() -> dict:
    schema = AssistantParse.model_json_schema()

    # Ollama structured outputs can use JSON schema, but keeping the schema simple
    # tends to make smaller local models behave better.
    return {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "estimate_calories",
                    "add_diet_entry",
                    "weekly_calorie_average",
                    "highest_calorie_days",
                    "weekly_summary",
                    "blood_pressure_trend",
                    "workout_mood_correlation",
                    "confirm_action",
                    "unknown",
                ],
            },
            "foods": {
                "type": "array",
                "items": {"type": "string"},
            },
            "meal": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
            },
            "date_range": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
            },
            "confirmation": {
                "anyOf": [
                    {"type": "string", "enum": ["yes", "no"]},
                    {"type": "null"},
                ],
            },
            "original_message": {
                "type": "string",
            },
        },
        "required": [
            "intent",
            "foods",
            "meal",
            "date_range",
            "confirmation",
            "original_message",
        ],
    }


def parse_assistant_message(message: str) -> AssistantParse:
    prompt = f"""
You are the local parser for Santiago's Homelab Life Terminal assistant.

Your job is to convert a messy user message into structured JSON.

Valid intents:
- estimate_calories: user asks for a calorie estimate.
- add_diet_entry: user directly asks to log/add food.
- weekly_calorie_average: user asks average calories for a week/date range.
- highest_calorie_days: user asks highest calorie days.
- weekly_summary: user asks to summarize last week/this week.
- blood_pressure_trend: user asks about blood pressure trend.
- workout_mood_correlation: user asks whether workouts affected mood.
- confirm_action: user confirms/rejects a previous pending action.
- unknown: anything else.

Rules:
- Return JSON only.
- Do not answer the question.
- Do not estimate calories.
- Extract food items separately when possible.
- "Culvers four pc and large fry" should become ["Culver's 4 piece tenders", "large fry"].
- "add that", "yes", "log it", "use that" usually means confirm_action with confirmation "yes".
- "add that for lunch", "use that for lunch", "log that for lunch", and "yes for lunch" mean confirm_action with confirmation "yes" and meal "lunch".
- Same rule applies for breakfast, dinner, and snack.
- "no", "don't add it", "cancel that" means confirm_action with confirmation "no".
- Extract meal if the user says breakfast, lunch, dinner, or snack.
- Keep date_range as plain text, like "this week", "last week", or null.
- If the user describes one combined meal like "chicken and rice", keep it as one food item: ["chicken and rice"].
- Only split foods when they are clearly separate menu items, like "Culver's four piece tenders and large fry".
- If the user sends only a food phrase with no explicit calories, treat it as estimate_calories.
- Examples:
  - "chicken and rice" => estimate_calories
  - "bean burrito" => estimate_calories
  - "culvers four pc and large fry" => estimate_calories
- Only use add_diet_entry when the user explicitly says they want to log/add/save something, or includes calories directly.
- Examples:
  - "log chicken and rice for lunch" => add_diet_entry
  - "add chicken and rice 650 calories" => add_diet_entry
  - "save a bean burrito for dinner" => add_diet_entry

User message:
{message}
""".strip()

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": _schema_for_ollama(),
            "stream": False,
            "options": {
                "temperature": 0
            },
        },
        timeout=60,
    )

    response.raise_for_status()

    raw_text = response.json().get("response", "")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Ollama returned invalid JSON: {raw_text}") from exc

    data["original_message"] = message

    return AssistantParse(**data)