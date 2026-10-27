import os
import re
import logging
from core.brain import Brain
from core.router import Router
from core.memory import save_interaction
from core.processor import process_response
from engines.library_engine import LibraryEngine
from engines.conversation_engine import ConversationEngine
from core.channel_registry import (
    find_best_channel, get_albanian_channels, CHANNELS
)
from core.smart_channel_finder import SmartChannelFinder

logger = logging.getLogger("FalconAI.Agent")


def _matches_trigger(text: str, trigger: str) -> bool:
    pattern = r'\b' + re.escape(trigger) + r'\b'
    return re.search(pattern, text) is not None


def _any_trigger(text: str, triggers) -> bool:
    return any(_matches_trigger(text, t) for t in triggers)


MUSIC_TRIGGERS = [
    "play", "këngë", "song", "music", "lësho", "luaj", "dëgjo", "listen",
    "hip hop", "jazz", "rock", "rap", "pop", "electronic", "beat"
]

CHANNEL_TRIGGERS = [
    "open", "watch", "shiko", "channel", "kanal", "tv", "live",
    "stream", "hap", "show me", "put on", "turn on", "launch",
    "live tv", "live channel", "transmeton"
]

CHANNEL_KEYWORDS = [
    "dw", "bbc", "rtk", "rtv", "kohavision", "nasa", "alsat", "euronews",
    "trt", "fox", "abc", "nbc", "cbs", "bloomberg", "france 24",
    "ora news", "report tv", "rtsh", "vizion", "klan", "news 24",
    "syri", "tv arta", "t7", "tv arbëria", "tv dielli", "vevo", "zdf",
    "ard", "srf", "rts", "nasa tv", "al jazeera", "sky news", "cnn",
    "red bull tv", "animal kingdom"
]

LIST_TRIGGERS = [
    "show live channels", "list channels", "show channels",
    "what channels", "cilat kanale", "kanalet live",
    "all channels", "available channels", "show me channels",
    "live channels", "live channel"
]

NEWS_TRIGGERS = [
    "what happened", "lajme", "current events", "breaking news", "headlines",
    "today's news", "lajmet e fundit"
]

WEATHER_TRIGGERS = ["weather", "moti", "forecast", "temperatura"]

SPORT_TRIGGERS = [
    "football score", "basketball score", "live score",
    "match result", "fifa", "nba", "premier league result"
]

COMMAND_SIGNALS = (
    MUSIC_TRIGGERS + CHANNEL_TRIGGERS + NEWS_TRIGGERS +
    WEATHER_TRIGGERS + SPORT_TRIGGERS + LIST_TRIGGERS +
    ["find", "gjej", "search", "kerko", "who is", "what is",
     "background", "sfond", "wallpaper"]
)

CONTENT_DESCRIPTION_PHRASES = [
    "show me something", "i want to watch", "dua te shoh", "gjej dicka",
    "find something", "something about", "dicka per", "transmeton",
    "who is showing", "cili transmeton", "ku ka", "where can i watch",
    "show me news about", "show me a channel with", "find a channel",
    "find channel", "any channel about", "channel about"
]


class Agent:
    def __init__(self, music_engine=None, web_engine=None, weather_engine=None,
                 sports_engine=None, library_engine=None, conversation_engine=None):
        self.brain = Brain()
        self.library_engine = library_engine if library_engine else LibraryEngine()
        self.web_engine = web_engine
        self.conversation_engine = (
            conversation_engine if conversation_engine else ConversationEngine()
        )
        self.router = Router(
            web_engine=self.web_engine,
            library_engine=self.library_engine,
            music_engine=music_engine,
            weather_engine=weather_engine,
            sports_engine=sports_engine
        )
        self.channel_finder = SmartChannelFinder(channels=CHANNELS)

    def handle_request(self, user_input: str, user_id: str = "default_user") -> dict:
        if not user_input or not user_input.strip():
            return {"text": "Please provide a valid instruction.", "voice": "Please provide a valid instruction.", "meta": {"type": "fallback"}}

        if self.conversation_engine and hasattr(self.conversation_engine, "handle"):
            try:
                chat_result = self.conversation_engine.handle(user_id, user_input)
                if chat_result is not None:
                    return chat_result
            except Exception as e:
                logger.error(f"[AGENT] Chat handling failed: {e}")

        cleaned = user_input.strip().lower()

        greetings = ["hello", "hi", "hey", "përshëndetje", "ckemi", "si je", "how are you", "who are you", "kush je ti"]
        if (cleaned in greetings or _any_trigger(cleaned, greetings)) and len(cleaned) < 25:
            return {"text": "Hello! I am FalconAI, your advanced AI assistant. How can I help you today?", "voice": "Hello! I am FalconAI.", "type": "chat", "meta": {"type": "chat", "intent": "greeting"}}

        if _any_trigger(cleaned, LIST_TRIGGERS):
            channels = get_albanian_channels()[:8]
            return {"type": "channel_list", "data": {"text": f"Here are some live channels: {', '.join(ch['name'] for ch in channels)}", "voice": "Here are some live channels.", "channels": channels}}

        if _any_trigger(cleaned, NEWS_TRIGGERS) and self.web_engine:
            result = self.web_engine.search(user_input)
            if result:
                return result

        if _any_trigger(cleaned, CONTENT_DESCRIPTION_PHRASES):
            logger.info(f"[AGENT] Content scan: '{user_input}'")
            return self.channel_finder.find(user_input)

        has_channel_trigger = _any_trigger(cleaned, CHANNEL_TRIGGERS)
        has_channel_keyword = _any_trigger(cleaned, CHANNEL_KEYWORDS)
        is_music = _any_trigger(cleaned, MUSIC_TRIGGERS)

        if (has_channel_trigger or has_channel_keyword):
            if is_music and not has_channel_keyword:
                return self._handle_music(user_input)
            return self.channel_finder.find(user_input)

        if is_music:
            return self._handle_music(user_input)

        tech_topics = ["kotlin", "java", "python", "clean code", "architecture", "cryptography"]
        if _any_trigger(cleaned, tech_topics):
            learned = self.library_engine.learn_and_extract(cleaned)
            if learned:
                return {"text": learned, "voice": "Here is what I learned.", "meta": {"type": "learned_knowledge"}}

        try:
            brain_output = self.brain.process(user_id="default", text=user_input, router=self.router)
            raw_result = brain_output["result"] if isinstance(brain_output, dict) and "result" in brain_output else {"text": str(brain_output), "voice": str(brain_output)}
            save_interaction(query=user_input, intent="general", meta={})
            return process_response(raw_result)
        except Exception as e:
            logger.error(f"[AGENT] Critical error: {e}")
            return {"text": "An unexpected error occurred.", "voice": "An unexpected error occurred.", "meta": {"type": "error"}}

    def _handle_music(self, user_input: str) -> dict:
        if self.router.music_engine:
            try:
                result = self.router.music_engine.play(user_input)
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
        return {"text": f"Duke analizuar tekstin/frazën për: {user_input}...", "voice": "Playing music.", "type": "music", "meta": {"type": "music", "intent": "play_music"}}