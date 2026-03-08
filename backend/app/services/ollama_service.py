import os
import requests
from typing import Any

OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


def generate_weekly_report(metrics: dict[str, Any]) -> str:
    system_prompt = (
        "You are a careful health analytics assistant. "
        "Summarize structured health data clearly and cautiously. "
        "Do not diagnose or give medical advice. "
        "Use language like 'associated with', 'tends to', or 'may indicate'. "
        "Return a short report with a short summary paragraph, "
        "three bullet observations, and one gentle suggestion."
    )

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Weekly metrics:\n{metrics}"},
            ],
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]