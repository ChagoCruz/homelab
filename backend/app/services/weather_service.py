from __future__ import annotations

from datetime import datetime
from typing import Any

import ephem
import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

GRAND_RAPIDS_LAT = 42.9634
GRAND_RAPIDS_LON = -85.6681


def weather_code_to_text(code: int) -> str:
    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Light rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Light snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Light rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Light snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(code, "Unknown")


def get_moon_phase_percent() -> float:
    moon = ephem.Moon(datetime.utcnow())
    return float(moon.phase)


def moon_phase_name(phase: float) -> str:
    if phase < 1:
        return "New Moon"
    elif phase < 25:
        return "Waxing Crescent"
    elif phase < 26:
        return "First Quarter"
    elif phase < 50:
        return "Waxing Gibbous"
    elif phase < 51:
        return "Full Moon"
    elif phase < 75:
        return "Waning Gibbous"
    elif phase < 76:
        return "Last Quarter"
    else:
        return "Waning Crescent"


def fetch_daily_weather(lat: float = GRAND_RAPIDS_LAT, lon: float = GRAND_RAPIDS_LON) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,sunrise,sunset",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "windspeed_unit": "mph",
        "timezone": "America/Detroit",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    daily = data["daily"]
    weather_code = int(daily["weathercode"][0])
    phase_percent = get_moon_phase_percent()

    return {
        "weather_date": daily["time"][0],
        "weather_code": weather_code,
        "weather_summary": weather_code_to_text(weather_code),
        "temp_max_f": daily["temperature_2m_max"][0],
        "temp_min_f": daily["temperature_2m_min"][0],
        "sunrise": daily["sunrise"][0],
        "sunset": daily["sunset"][0],
        "moon_phase_percent": round(phase_percent, 2),
        "moon_phase_name": moon_phase_name(phase_percent),
        "raw_payload": data,
    }