import json
import math
import os
from datetime import datetime, timedelta

from calendar_data import TZ
from network import fetch


def condition(code, is_day=True):
    if code == 0:
        return ("Clear", "sun") if is_day else ("Clear night", "moon")
    if code in (1, 2):
        return "Partly cloudy", "sun-cloud"
    if code == 3:
        return "Overcast", "cloud"
    if code in (45, 48):
        return "Fog", "fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle", "rain"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Rain", "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow", "snow"
    if code in (95, 96, 99):
        return "Thunderstorm", "storm"
    return "Unknown", "cloud"


def normalize(data, updated):
    daily = data["daily"]
    forecast = []
    for i in range(3):
        description, icon = condition(daily["weather_code"][i])
        forecast.append({"date": daily["time"][i],
                         "day": datetime.fromisoformat(daily["time"][i]).strftime("%a"),
                         "high": round(daily["temperature_2m_max"][i]),
                         "low": round(daily["temperature_2m_min"][i]),
                         "precipitation_probability": daily["precipitation_probability_max"][i],
                         "description": description, "symbol": icon})
    current = data["current"]
    description, icon = condition(current["weather_code"], current.get("is_day", 1))
    first = forecast[0]
    return {"current": {"temperature": round(current["temperature_2m"]), "description": description,
                        "icon": icon, "high": first["high"], "low": first["low"],
                        "precipitation_probability": first["precipitation_probability"],
                        "range": f'H:{first["high"]} L:{first["low"]} Rain:{first["precipitation_probability"]}%'},
            "forecast": forecast, "last_successful_update": updated}


async def live():
    lat = float(os.environ["WEATHER_LATITUDE"])
    lon = float(os.environ["WEATHER_LONGITUDE"])
    units = os.getenv("WEATHER_UNITS", "celsius")
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Invalid weather coordinates")
    if units not in ("celsius", "fahrenheit"):
        raise ValueError("Invalid weather units")
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&temperature_unit={units}&timezone=Europe%2FLondon&forecast_days=3"
           "&current=temperature_2m,weather_code,is_day"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max")
    return normalize(json.loads(await fetch(url)), datetime.now(TZ).isoformat())
