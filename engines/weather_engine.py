import os
import re
import time
import ipaddress
import logging
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("FalconAI.WeatherEngine")

API_KEY = os.getenv("OPENWEATHER_KEY", "f8a26ced25d514b94ad2d1e61bca80e1")
DEFAULT_CITY = os.getenv("WEATHER_FALLBACK_CITY", "San Francisco")

SPEAK_ON_SERVER = os.getenv("WEATHER_SPEAK", "false").lower() == "true"

IP_CACHE_TTL = 6 * 3600
IP_CACHE_MAX = 5000

WEATHER_ICONS = {
    "clear sky": "☀️",
    "few clouds": "🌤️",
    "scattered clouds": "⛅",
    "broken clouds": "☁️",
    "overcast clouds": "☁️",
    "light rain": "🌦️",
    "moderate rain": "🌧️",
    "heavy rain": "🌧️",
    "heavy intensity rain": "🌧️",
    "thunderstorm": "⛈️",
    "snow": "❄️",
    "light snow": "🌨️",
    "light intensity drizzle": "🌦️",
    "drizzle": "🌦️",
    "mist": "🌫️",
    "fog": "🌫️",
    "haze": "🌫️",
}

WMO_CODE_MAP = {
    0: ("clear sky", "☀️"),
    1: ("few clouds", "🌤️"),
    2: ("scattered clouds", "⛅"),
    3: ("overcast clouds", "☁️"),
    45: ("fog", "🌫️"),
    48: ("fog", "🌫️"),
    51: ("light intensity drizzle", "🌦️"),
    53: ("drizzle", "🌦️"),
    55: ("drizzle", "🌦️"),
    61: ("light rain", "🌦️"),
    63: ("moderate rain", "🌧️"),
    65: ("heavy rain", "🌧️"),
    71: ("light snow", "🌨️"),
    73: ("snow", "❄️"),
    75: ("snow", "❄️"),
    80: ("light rain", "🌦️"),
    81: ("moderate rain", "🌧️"),
    82: ("heavy rain", "🌧️"),
    95: ("thunderstorm", "⛈️"),
}

STOPWORDS = {
    "weather", "in", "at", "of", "for", "to", "a", "an", "the", "what", "is",
    "are", "was", "will", "be", "it", "its", "how", "like", "today", "tomorrow",
    "tonight", "now", "current", "currently", "right", "forecast", "report",
    "update", "temperature", "cold", "hot", "warm", "outside", "tell", "me",
    "about", "give", "show", "please", "do", "does", "i", "need", "check",
    "this", "week", "weekend", "rain", "raining", "sunny", "windy", "cloudy"
}


def _is_public_ip(ip):
    if not ip:
        return False
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def _valid_coords(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None, None


class WeatherEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self._ip_cache = {}

        if not self.api_key:
            logger.warning("[WEATHER] OPENWEATHER_KEY is not set.")

    def get_city_from_ip(self, ip=None):
        public = _is_public_ip(ip)

        if public:
            cached = self._ip_cache.get(ip)
            if cached and time.time() - cached[1] < IP_CACHE_TTL:
                return cached[0]
            url = f"https://ipapi.co/{ip}/json/"
        else:
            url = "https://ipapi.co/json/"

        city = ""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                city = (response.json().get("city") or "").strip()
            else:
                logger.warning(f"[WEATHER] IP lookup returned HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"[WEATHER] IP lookup failed: {e}")

        if not city:
            logger.info(f"[WEATHER] No city from IP, using default '{DEFAULT_CITY}'")
            return DEFAULT_CITY

        if public:
            if len(self._ip_cache) >= IP_CACHE_MAX:
                self._ip_cache.clear()
            self._ip_cache[ip] = (city, time.time())

        logger.info(f"[WEATHER] IP detected city: {city}")
        return city

    def extract_city(self, query):
        words = re.findall(r"[^\W\d_]+(?:['-][^\W\d_]+)*", (query or "").lower())
        city_words = [w for w in words if w not in STOPWORDS and len(w) > 1]
        return " ".join(city_words).title() if city_words else None

    def fetch_weather(self, city=None, lat=None, lon=None):
        if self.api_key:
            params = {"appid": self.api_key, "units": "metric", "lang": "en"}
            if lat is not None and lon is not None:
                params["lat"], params["lon"] = lat, lon
                target = "coordinates"
            elif city:
                params["q"] = city
                target = f"'{city}'"
            else:
                target = "unknown"

            try:
                response = requests.get(self.base_url, params=params, timeout=5)
                if response.status_code == 200:
                    return response.json()
                logger.warning(f"[WEATHER] OpenWeather returned HTTP {response.status_code} for {target}")
            except Exception as e:
                logger.warning(f"[WEATHER] OpenWeather request failed for {target}: {e}")

        return self.fetch_open_meteo(city=city, lat=lat, lon=lon)

    def fetch_open_meteo(self, city=None, lat=None, lon=None):
        try:
            resolved_name = city or "Current Location"
            resolved_country = ""

            if lat is None or lon is None:
                if not city:
                    return None
                geo_resp = requests.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": city, "count": 1, "language": "en", "format": "json"},
                    timeout=5,
                )
                if geo_resp.status_code != 200:
                    logger.warning(f"[WEATHER] Open-Meteo geocoding HTTP {geo_resp.status_code} for '{city}'")
                    return None
                results = (geo_resp.json() or {}).get("results") or []
                if not results:
                    logger.warning(f"[WEATHER] Open-Meteo found no location for '{city}'")
                    return None
                place = results[0]
                lat = place.get("latitude")
                lon = place.get("longitude")
                resolved_name = place.get("name") or city
                resolved_country = place.get("country_code") or ""

            wx_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code",
                    "wind_speed_unit": "kmh",
                    "timezone": "auto",
                },
                timeout=5,
            )
            if wx_resp.status_code != 200:
                logger.warning(f"[WEATHER] Open-Meteo forecast HTTP {wx_resp.status_code}")
                return None

            cur = (wx_resp.json() or {}).get("current") or {}
            if "temperature_2m" not in cur:
                return None

            code = cur.get("weather_code", 0)
            desc, icon = WMO_CODE_MAP.get(code, ("clear sky", "🌤️"))

            return {
                "name": resolved_name,
                "sys": {"country": resolved_country},
                "main": {
                    "temp": cur.get("temperature_2m", 0),
                    "feels_like": cur.get("apparent_temperature", cur.get("temperature_2m", 0)),
                    "humidity": cur.get("relative_humidity_2m", 0),
                },
                "wind": {
                    "speed": (cur.get("wind_speed_10m", 0)) / 3.6,
                },
                "weather": [{"description": desc}],
                "_icon_override": icon,
            }
        except Exception as e:
            logger.error(f"[WEATHER] Open-Meteo fallback error: {e}")
            return None

    def build_response(self, data, source="query"):
        city = data.get("name") or "your area"
        country = (data.get("sys") or {}).get("country", "")
        place = f"{city}, {country}" if country else city

        temp = round(data["main"]["temp"])
        feels = round(data["main"]["feels_like"])
        humidity = data["main"]["humidity"]
        wind = round((data.get("wind") or {}).get("speed", 0) * 3.6, 1)
        desc = data["weather"][0]["description"]
        icon = data.get("_icon_override") or WEATHER_ICONS.get(desc, "🌡️")

        display = (
            f"### {icon} Weather in {place}\n\n"
            f"| Metric | Value |\n"
            f"| :--- | :--- |\n"
            f"| **Condition** | {desc.capitalize()} |\n"
            f"| **Temperature** | {temp}°C |\n"
            f"| **Feels Like** | {feels}°C |\n"
            f"| **Humidity** | {humidity}% |\n"
            f"| **Wind** | {wind} km/h |\n"
        )

        voice_text = (
            f"The weather in {place} is {desc}. "
            f"Temperature is {temp} degrees Celsius, "
            f"feels like {feels} degrees. "
            f"Humidity is {humidity} percent "
            f"and wind speed is {wind} kilometers per hour."
        )

        return {
            "type": "weather",
            "data": {
                "city": city,
                "country": country,
                "temp": temp,
                "feels_like": feels,
                "humidity": humidity,
                "wind": wind,
                "description": desc,
                "icon": icon,
                "location_source": source,
                "text": display,
                "markdown_table": display,
                "voice_text": voice_text,
            },
        }

    def process(self, query, ip=None, lat=None, lon=None):
        try:
            lat, lon = _valid_coords(lat, lon)
            city = self.extract_city(query)

            if city:
                source = "query"
                raw = self.fetch_weather(city=city)
            elif lat is not None:
                source = "gps"
                raw = self.fetch_weather(lat=lat, lon=lon)
            else:
                source = "ip"
                city = self.get_city_from_ip(ip)
                raw = self.fetch_weather(city=city)

            logger.info(f"[WEATHER] Fetched via {source}")

            if not raw:
                return self.error_response(query, city if source == "query" else None)

            result = self.build_response(raw, source)

            if SPEAK_ON_SERVER:
                try:
                    from utils.voice import speak
                    speak(result["data"]["voice_text"])
                except Exception:
                    pass

            return result

        except Exception as e:
            logger.error(f"[WEATHER ERROR] {e}")
            return self.error_response(query)

    def get_weather(self, query, ip=None, lat=None, lon=None):
        return self.process(query, ip=ip, lat=lat, lon=lon)

    def get_forecast(self, query, ip=None, lat=None, lon=None):
        return self.process(query, ip=ip, lat=lat, lon=lon)

    def error_response(self, query, city=None):
        if city:
            text = f"Sorry, I couldn't find weather for '{city}'. Check the spelling or try another city."
        else:
            text = "Sorry, I couldn't get the weather. Please try again."

        return {
            "type": "weather",
            "data": {
                "text": text,
                "voice_text": text,
            },
        }
