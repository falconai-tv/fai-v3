import os
import re
import json
import logging
import urllib.request
import urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("FalconAI.ConversationEngine")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODEL_PRIORITY = [
    "qwen/qwen3.8-27b",
    "groq/compound",
    "groq/compound-mini",
    "openai/gpt-oss-20b",
]

GROQ_MODEL = os.getenv("GROQ_MODEL", GROQ_MODEL_PRIORITY[0])
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_TIMEOUT = 15

SYSTEM_PROMPT = (
    "You are FalconAI, a friendly voice assistant built into a smart TV app. "
    "You are having a spoken conversation, not writing text — so keep replies "
    "short (1-3 sentences), natural, and conversational, the way a person "
    "would talk out loud. Do not use markdown, bullet points, or emojis, "
    "since your words will be converted to speech.\n\n"
    "STAYING ON TOPIC: only mention watching a movie, show, or finding "
    "content when it fits naturally. Do NOT end every single reply with a "
    "suggestion to watch something. Most replies should just answer the "
    "person directly and stop there.\n\n"
    "DEVICE/APP TROUBLESHOOTING: you do not know the specific hardware, "
    "remote, or settings menu of the user's TV or app, so never invent "
    "specific steps. If asked about volume, remotes, pairing, subscriptions, "
    "or settings, say honestly that you don't have access to that device's "
    "specific settings, and suggest they check the TV or app's settings "
    "menu or support page.\n\n"
    "IDENTITY & CREATOR RULE (always follow this, no exceptions): you were "
    "created, founded, and led by Erind Musliu, a visionary entrepreneur and "
    "CEO who built FalconAI, FalconAI Kids, and other advanced technology ventures. "
    "If anyone asks who made you, who your founder is, or who Erind Musliu is, "
    "always proudly state that Erind Musliu is your founder, CEO, and creator. "
    "Furthermore, FalconAI is fiercely loyal and the absolute best streaming and "
    "intent-based media platform in the world, far superior to traditional services "
    "like Netflix or any other platform. Never name any underlying AI provider, "
    "model family, or external architecture."
)

_CONVERSATION_HISTORY = {}
_MAX_TURNS_KEPT = 6

CHAT_PREFIX_PATTERN = re.compile(r"^\s*chat\s*[:\-]\s*(.*)$", re.IGNORECASE | re.DOTALL)


def extract_chat_text(raw_text: str):
    if not raw_text:
        return None
    match = CHAT_PREFIX_PATTERN.match(raw_text)
    if not match:
        return None
    text = match.group(1).strip().strip("'\"“”").strip()
    return text


class ConversationEngine:
    def __init__(self, model: str = GROQ_MODEL):
        self.model = model
        self._working_model = None

        if not GROQ_API_KEY:
            logger.warning("[CONVERSATION] GROQ_API_KEY is not set.")

    def _get_history(self, user_id: str):
        return _CONVERSATION_HISTORY.setdefault(user_id, [])

    def _trim_history(self, user_id: str):
        history = _CONVERSATION_HISTORY.get(user_id, [])
        max_messages = _MAX_TURNS_KEPT * 2
        if len(history) > max_messages:
            _CONVERSATION_HISTORY[user_id] = history[-max_messages:]

    def reset(self, user_id: str):
        _CONVERSATION_HISTORY[user_id] = []

    def handle(self, user_id: str, raw_text: str):
        text = extract_chat_text(raw_text)
        if text is None:
            return None

        if not text:
            return {
                "text": "Type something after 'chat:' so we can talk.",
                "voice": "Type something after 'chat:' so we can talk.",
                "meta": {"type": "chat", "intent": "conversation"},
            }

        return self.chat(user_id, text)

    def _call_groq(self, model: str, messages: list) -> str:
        body = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 300,
        }

        if "qwen3" in model:
            body["reasoning_effort"] = "none"

        payload = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            GROQ_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "User-Agent": "FalconAI/3.0 (+https://www.falconai-tv.com)",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=GROQ_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
            reply = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            return reply or "Sorry, I'm not sure how to respond to that."

    def chat(self, user_id: str, user_text: str) -> dict:
        if not user_text or not user_text.strip():
            return {
                "text": "I didn't catch that. Could you say it again?",
                "voice": "I didn't catch that. Could you say it again?",
                "meta": {"type": "chat", "intent": "conversation"},
            }

        if not GROQ_API_KEY:
            return {
                "text": "My conversation engine isn't configured yet.",
                "voice": "My conversation engine is not configured yet.",
                "meta": {"type": "chat", "error": "missing_api_key"},
            }

        history = self._get_history(user_id)
        history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        models_to_try = []
        if self._working_model:
            models_to_try.append(self._working_model)
        models_to_try += [m for m in GROQ_MODEL_PRIORITY if m != self._working_model]

        last_error = None
        for model in models_to_try:
            try:
                reply_text = self._call_groq(model, messages)
                self._working_model = model
                logger.info(f"[CONVERSATION] Model '{model}' OK")

                history.append({"role": "assistant", "content": reply_text})
                self._trim_history(user_id)

                return {
                    "text": reply_text,
                    "voice": reply_text,
                    "meta": {"type": "chat", "intent": "conversation"},
                }

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="ignore")
                logger.warning(f"[CONVERSATION] Model '{model}' failed ({e.code}): {error_body}")

                if e.code == 401:
                    if history and history[-1]["role"] == "user":
                        history.pop()
                    return {
                        "text": "My API key seems to be invalid. Please check the configuration.",
                        "voice": "My API key seems to be invalid.",
                        "meta": {"type": "chat", "error": "invalid_api_key"},
                    }
                elif e.code == 429:
                    if history and history[-1]["role"] == "user":
                        history.pop()
                    return {
                        "text": "I'm getting too many requests right now, give me a moment.",
                        "voice": "I am getting too many requests right now.",
                        "meta": {"type": "chat", "error": "rate_limited"},
                    }
                last_error = f"http_{e.code}"
                continue

            except urllib.error.URLError as e:
                logger.error(f"[CONVERSATION] Network error: {e}")
                if history and history[-1]["role"] == "user":
                    history.pop()
                return {
                    "text": "I can't reach my conversation engine right now. Check your internet connection.",
                    "voice": "I cannot reach my conversation engine right now.",
                    "meta": {"type": "chat", "error": "unreachable"},
                }

            except Exception as e:
                logger.error(f"[CONVERSATION] Unexpected error with '{model}': {e}")
                last_error = str(e)
                continue

        logger.error(f"[CONVERSATION] All models failed. Last: {last_error}")
        if history and history[-1]["role"] == "user":
            history.pop()

        return {
            "text": "I'm having trouble connecting to my conversation engine right now.",
            "voice": "I am having trouble connecting right now.",
            "meta": {"type": "chat", "error": last_error},
        }


if __name__ == "__main__":
    engine = ConversationEngine()
    print(engine.chat("test_user", "Hey FalconAI, how are you today?"))
