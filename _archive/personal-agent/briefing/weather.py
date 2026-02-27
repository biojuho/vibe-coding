from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import requests

try:
    from execution.api_usage_tracker import log_api_call
except Exception:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from execution.api_usage_tracker import log_api_call
    except Exception:  # pragma: no cover - optional integration
        def log_api_call(**_kwargs):
            return None


logger = logging.getLogger(__name__)


def _get_with_retry(url: str, timeout: int = 8, retries: int = 2) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "Joolife-Agent/1.0"},
            )
            log_api_call(
                provider="weather",
                endpoint=f"GET {url}",
                caller_script="projects/personal-agent/briefing/weather.py",
            )
            return resp
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(0.8 * (2 ** attempt))
    raise last_error if last_error else RuntimeError("Unknown weather request failure")

def get_weather(city="Seoul"):
    """
    Fetches weather information from wttr.in properly handling text format.
    """
    try:
        # format=3: One-line output (e.g., "Seoul: ☀️ +15°C")
        url = f"https://wttr.in/{city}?format=3"
        response = _get_with_retry(url=url)
        if response.status_code == 200:
            return response.text.strip()
        return "Weather service is temporarily unavailable."
    except Exception as e:
        logger.warning(f"Weather fetch failed for city={city}: {e}")
        return "Weather data is currently unavailable."

def get_weather_data(city="Seoul"):
    """
    Fetches structured weather data (JSON) from wttr.in.
    Returns dict: {'temp_C': str, 'condition': str, 'location': str}
    """
    try:
        url = f"https://wttr.in/{city}?format=j1"
        response = _get_with_retry(url=url)
        if response.status_code == 200:
            data = response.json()
            current = data['current_condition'][0]
            area = data['nearest_area'][0]['areaName'][0]['value']
            return {
                'temp': f"{current['temp_C']}°C",
                'condition': current['weatherDesc'][0]['value'],
                'location': area,
                'humidity': f"{current['humidity']}%",
                'wind': f"{current['windspeedKmph']}km/h"
            }
        return None
    except Exception as e:
        logger.warning(f"Weather JSON fetch failed for city={city}: {e}")
        return None
