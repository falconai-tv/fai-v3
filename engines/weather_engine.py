import os
import re
import time
import ipaddress
import logging
import unicodedata
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("FalconAI.WeatherEngine")

API_KEY = os.getenv("OPENWEATHER_KEY", "")
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

STOPWORDS = {
    "weather", "in", "at", "of", "for", "to", "a", "an", "the", "what", "is",
    "are", "was", "will", "be", "it", "its", "how", "like", "today", "tomorrow",
    "tonight", "now", "current", "currently", "right", "forecast", "report",
    "update", "temperature", "cold", "hot", "warm", "outside", "tell", "me",
    "about", "give", "show", "please", "do", "does", "i", "need", "check",
    "this", "week", "weekend", "rain", "raining", "sunny", "windy", "cloudy"
}

# Fjalë shqipe që nuk janë emra qytetesh
STOPWORDS |= {
    "moti", "mot", "ne", "në", "sot", "nesër", "nesër", "neser", "si", "është",
    "eshte", "cili", "cila", "qysh", "po", "ka", "sa", "kohë", "kohe", "koha",
    "për", "per", "dua", "më", "me", "trego", "tregom", "do", "të", "te",
    "bëjë", "beje", "kam", "ndonjë", "ndonje", "temperatura", "shi", "diell",
    "bore", "ftohtë", "ftohte", "nxehtë", "nxehte", "jashtë", "jashte",
    "tani", "javën", "javen"
}

# Emra qytetesh që OpenWeather i njeh me emër tjetër
CITY_ALIASES = {
    "prishtina": "pristina",
    "prishtinë": "pristina",
    "prishtine": "pristina",
    "tiranë": "tirana",
    "tirane": "tirana",
    "shkup": "skopje",
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


def _ascii_fold(text):
    """'Prishtinë' -> 'Prishtine', 'Çakor' -> 'Cakor'."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


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
        if not city_words:
            return None
        city = " ".join(city_words)
        city = CITY_ALIASES.get(city, city)
        return city.title()

    def fetch_weather(self, city=None, lat=None, lon=None):
        params = {"appid": self.api_key, "units": "metric", "lang": "en"}

        if lat is not None and lon is not None:
            params["lat"], params["lon"] = lat, lon
            target = "coordinates"
        else:
            params["q"] = city
            target = f"'{city}'"

        response = requests.get(self.base_url, params=params, timeout=5)

        # Provo përsëri pa shenja diakritike (ë, ç) nëse qyteti nuk u gjet
        if response.status_code == 404 and params.get("q"):
            folded = _ascii_fold(params["q"])
            if folded != params["q"]:
                params["q"] = folded
                response = requests.get(self.base_url, params=params, timeout=5)

        if response.status_code == 200:
            return response.json()

        logger.warning(f"[WEATHER] OpenWeather returned HTTP {response.status_code} for {target}")
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
        icon = WEATHER_ICONS.get(desc, "🌡️")

        display = (
            f"\n{'='*38}\n"
            f"  {icon}  WEATHER IN {place.upper()}\n"
            f"{'='*38}\n"
            f"  🌡️  Temperature : {temp}°C\n"
            f"  🤔  Feels like  : {feels}°C\n"
            f"  💧  Humidity    : {humidity}%\n"
            f"  💨  Wind        : {wind} km/h\n"
            f"  📋  Condition   : {desc.capitalize()}\n"
            f"{'='*38}\n"
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
