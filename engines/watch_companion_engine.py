import os

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "timeout;5000000")

import io
import re
import cv2
import time
import wave
import queue
import base64
import shutil
import logging
import threading
import subprocess
from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pytesseract
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("FalconAI.WatchCompanion")

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")
VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

SAMPLE_RATE = 16000
BYTES_PER_SECOND = SAMPLE_RATE * 2
AUDIO_CHUNK_SECONDS = 10
SILENCE_RMS = 120.0
MAX_STREAM_FAILURES = 6
IDLE_TIMEOUT = 600
REAPER_INTERVAL = 30
VISION_CACHE_SECONDS = 15
MAX_CONTEXT_CHARS = 1800

HALLUCINATIONS = (
    "thank you for watching",
    "thanks for watching",
    "subtitles by",
    "amara.org",
    "please subscribe",
    "like and subscribe",
    "thank you.",
    "thanks.",
    "mbeshtetur nga",
    "titrat nga",
)


def _clean_words(raw_text: str) -> str:
    tokens = re.findall(r"\S+", raw_text or "")
    good = []
    for token in tokens:
        if len(token) <= 2:
            continue
        letters = sum(1 for c in token if c.isalpha())
        if letters / len(token) >= 0.7:
            good.append(token)
    return " ".join(good) if len(good) >= 3 else ""


def _similarity_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    set_a, set_b = set(a.lower().split()), set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / max(len(set_a), len(set_b))


def _age_label(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 5:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    return f"{seconds // 60}m ago"


def _is_hallucination(text: str) -> bool:
    lowered = text.lower().strip()
    if len(lowered.split()) < 3:
        return True
    return any(phrase in lowered for phrase in HALLUCINATIONS)


def _detect_ocr_lang() -> str:
    try:
        available = set(pytesseract.get_languages(config=""))
    except Exception:
        return "eng"
    langs = [l for l in ("eng", "sqi") if l in available]
    return "+".join(langs) if langs else "eng"


@dataclass
class _WatchSession:
    session_id: str
    channel_url: str
    channel_name: str = ""
    language: str = None
    capture_interval: float = 5.0
    audio_enabled: bool = True
    vision_enabled: bool = True
    screen_buffer: deque = field(default_factory=lambda: deque(maxlen=12))
    speech_buffer: deque = field(default_factory=lambda: deque(maxlen=10))
    latest_jpeg: bytes = None
    latest_jpeg_time: float = 0.0
    pending_frame: object = None
    vision_cache: dict = field(default_factory=dict)
    stop_event: threading.Event = field(default_factory=threading.Event)
    frame_ready: threading.Event = field(default_factory=threading.Event)
    audio_queue: queue.Queue = field(default_factory=lambda: queue.Queue(maxsize=3))
    ffmpeg_proc: subprocess.Popen = None
    ffmpeg_video_proc: subprocess.Popen = None
    threads: list = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    started_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    video_ok: bool = False
    audio_ok: bool = False


class WatchCompanionEngine:
    def __init__(self, conversation_engine):
        self.conversation_engine = conversation_engine
        self._sessions = {}
        self._sessions_lock = threading.Lock()
        self._ffmpeg_available = shutil.which("ffmpeg") is not None
        self._ocr_lang = _detect_ocr_lang()
        self._shutdown = threading.Event()

        if not self._ffmpeg_available:
            logger.warning("[WATCH] ffmpeg not found - audio and video streaming will be limited")

        self._reaper = threading.Thread(target=self._reaper_loop, daemon=True)
        self._reaper.start()

    def start_session(self, session_id: str, channel_url: str, channel_name: str = "",
                      capture_interval: float = 5.0, language: str = None,
                      enable_audio: bool = True, enable_vision: bool = True) -> dict:
        self.stop_session(session_id)

        audio_on = bool(enable_audio and self._ffmpeg_available and os.getenv("GROQ_API_KEY"))
        vision_on = bool(enable_vision and os.getenv("GROQ_API_KEY") and VISION_MODEL)

        session = _WatchSession(
            session_id=session_id,
            channel_url=channel_url,
            channel_name=channel_name,
            language=language,
            capture_interval=max(2.0, float(capture_interval)),
            audio_enabled=audio_on,
            vision_enabled=vision_on,
        )

        workers = [self._video_loop, self._ocr_loop]
        if audio_on:
            workers += [self._audio_reader_loop, self._transcribe_loop]

        for target in workers:
            t = threading.Thread(target=target, args=(session,), daemon=True)
            session.threads.append(t)

        with self._sessions_lock:
            self._sessions[session_id] = session

        for t in session.threads:
            t.start()

        self._reset_watch_history(session_id)
        logger.info(f"[WATCH] Started '{session_id}' on '{channel_name}' audio={audio_on} vision={vision_on}")

        return {
            "status": "started",
            "session_id": session_id,
            "channel_name": channel_name,
            "features": {"ocr": True, "audio": audio_on, "vision": vision_on},
        }

    def stop_session(self, session_id: str) -> dict:
        with self._sessions_lock:
            session = self._sessions.pop(session_id, None)

        if not session:
            return {"status": "not_found", "session_id": session_id}

        session.stop_event.set()
        session.frame_ready.set()
        
        for proc in [session.ffmpeg_proc, session.ffmpeg_video_proc]:
            if proc is not None:
                try:
                    proc.kill()
                except Exception:
                    pass

        logger.info(f"[WATCH] Stopped '{session_id}'")
        return {"status": "stopped", "session_id": session_id}

    def shutdown(self):
        self._shutdown.set()
        with self._sessions_lock:
            ids = list(self._sessions.keys())
        for sid in ids:
            self.stop_session(sid)

    def is_active(self, session_id: str) -> bool:
        with self._sessions_lock:
            return session_id in self._sessions

    def get_status(self, session_id: str) -> dict:
        with self._sessions_lock:
            session = self._sessions.get(session_id)
        if not session:
            return {"status": "not_found", "session_id": session_id}
        with session.lock:
            return {
                "status": "active",
                "session_id": session_id,
                "channel_name": session.channel_name,
                "video_ok": session.video_ok,
                "audio_ok": session.audio_ok,
                "audio_enabled": session.audio_enabled,
                "vision_enabled": session.vision_enabled,
                "screen_entries": len(session.screen_buffer),
                "speech_entries": len(session.speech_buffer),
                "uptime_seconds": int(time.time() - session.started_at),
            }

    def _reaper_loop(self):
        while not self._shutdown.wait(REAPER_INTERVAL):
            now = time.time()
            with self._sessions_lock:
                stale = [sid for sid, s in self._sessions.items()
                         if now - s.last_activity > IDLE_TIMEOUT]
            for sid in stale:
                logger.info(f"[WATCH] Idle timeout for '{sid}'")
                self.stop_session(sid)

    def _video_loop(self, s: _WatchSession):
        """Përdor FFmpeg subprocess për të lexuar stream-in HLS (.m3u8) dhe nxjerr frames si MJPEG pipe"""
        failures = 0
        while not s.stop_event.is_set():
            if not self._ffmpeg_available:
                # Fallback te cv2.VideoCapture nëse ffmpeg nuk gjendet
                self._video_loop_cv2(s)
                return

            cmd = [
                "ffmpeg", "-nostdin", "-loglevel", "error",
                "-rw_timeout", "8000000",
                "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
                "-i", s.channel_url,
                "-vf", f"fps=1/{s.capture_interval}",
                "-f", "image2pipe",
                "-vcodec", "mjpeg",
                "pipe:1"
            ]

            proc = None
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                s.ffmpeg_video_proc = proc
                buffer = bytearray()
                got_frame = False

                while not s.stop_event.is_set():
                    chunk = proc.stdout.read(4096)
                    if not chunk:
                        break
                    buffer.extend(chunk)

                    while True:
                        start = buffer.find(b'\xff\xd8')
                        end = buffer.find(b'\xff\xd9')
                        if start != -1 and end != -1 and end > start:
                            jpeg_data = bytes(buffer[start:end+2])
                            del buffer[:end+2]

                            frame = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
                            if frame is not None:
                                got_frame = True
                                failures = 0
                                s.video_ok = True
                                with s.lock:
                                    s.latest_jpeg = jpeg_data
                                    s.latest_jpeg_time = time.time()

                                s.pending_frame = frame
                                s.frame_ready.set()
                        else:
                            break
            except Exception as e:
                logger.warning(f"[WATCH] Video pipe error for '{s.session_id}': {e}")
            finally:
                if proc:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                s.ffmpeg_video_proc = None

            if s.stop_event.is_set():
                break

            s.video_ok = False
            failures += 1
            if failures >= MAX_STREAM_FAILURES:
                logger.warning(f"[WATCH] Video stream unreachable for '{s.session_id}'")
                self._push_screen(s, "(The video stream could not be read.)", force=True)
                break
            s.stop_event.wait(min(2 * failures, 10))

    def _video_loop_cv2(self, s: _WatchSession):
        """Fallback metodë me OpenCV VideoCapture nëse ffmpeg mungon"""
        cap = None
        failures = 0
        last_pick = 0.0
        try:
            while not s.stop_event.is_set():
                if cap is None:
                    cap = cv2.VideoCapture(s.channel_url, cv2.CAP_FFMPEG)
                    if not cap.isOpened():
                        cap.release()
                        cap = None
                        failures += 1
                        s.video_ok = False
                        if failures >= MAX_STREAM_FAILURES:
                            break
                        s.stop_event.wait(min(2 * failures, 10))
                        continue

                if not cap.grab():
                    cap.release()
                    cap = None
                    failures += 1
                    s.video_ok = False
                    if failures >= MAX_STREAM_FAILURES:
                        break
                    s.stop_event.wait(2)
                    continue

                failures = 0
                s.video_ok = True

                now = time.time()
                if now - last_pick >= s.capture_interval and not s.frame_ready.is_set():
                    ok, frame = cap.retrieve()
                    if ok and frame is not None:
                        s.pending_frame = frame
                        s.frame_ready.set()
                        last_pick = now
        except Exception as e:
            logger.error(f"[WATCH] Video loop CV2 crashed for '{s.session_id}': {e}")
        finally:
            s.video_ok = False
            if cap is not None:
                cap.release()

    def _ocr_loop(self, s: _WatchSession):
        while not s.stop_event.is_set():
            if not s.frame_ready.wait(timeout=1):
                continue
            frame = s.pending_frame
            s.pending_frame = None
            s.frame_ready.clear()
            if frame is None or s.stop_event.is_set():
                continue

            try:
                self._store_jpeg(s, frame)
                text = self._extract_text(frame)
                if text:
                    self._push_screen(s, text)
            except Exception as e:
                logger.warning(f"[WATCH] OCR cycle failed: {e}")

    def _store_jpeg(self, s: _WatchSession, frame):
        h, w = frame.shape[:2]
        if w > 640:
            frame = cv2.resize(frame, (640, int(h * 640 / w)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ok:
            with s.lock:
                s.latest_jpeg = buf.tobytes()
                s.latest_jpeg_time = time.time()

    def _extract_text(self, frame) -> str:
        h = frame.shape[0]
        bottom = frame[int(h * 0.6):, :]
        text = self._ocr(bottom)
        if len(text.split()) < 3:
            text = self._ocr(frame)
        return text

    def _ocr(self, image) -> str:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if w > 1280:
            gray = cv2.resize(gray, (1280, int(h * 1280 / w)), interpolation=cv2.INTER_AREA)
        elif w < 960:
            gray = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        raw = pytesseract.image_to_string(gray, lang=self._ocr_lang, config="--psm 6")
        return _clean_words(raw)

    def _push_screen(self, s: _WatchSession, text: str, force: bool = False):
        with s.lock:
            if not force:
                recent = list(s.screen_buffer)[-3:]
                if any(_similarity_ratio(text, e["text"]) > 0.7 for e in recent):
                    return
            s.screen_buffer.append({"time": time.time(), "text": text})

    def _audio_reader_loop(self, s: _WatchSession):
        failures = 0
        chunk_bytes = BYTES_PER_SECOND * AUDIO_CHUNK_SECONDS
        while not s.stop_event.is_set():
            cmd = [
                "ffmpeg", "-nostdin", "-loglevel", "error",
                "-rw_timeout", "8000000",
                "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
                "-i", s.channel_url,
                "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "pipe:1",
            ]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.error(f"[WATCH] Could not start ffmpeg: {e}")
                return

            s.ffmpeg_proc = proc
            got_data = False

            try:
                while not s.stop_event.is_set():
                    data = self._read_exact(proc, chunk_bytes, s.stop_event)
                    if len(data) < BYTES_PER_SECOND * 2:
                        break
                    got_data = True
                    failures = 0
                    s.audio_ok = True
                    if s.audio_queue.full():
                        try:
                            s.audio_queue.get_nowait()
                        except queue.Empty:
                            pass
                    s.audio_queue.put(data)
            except Exception as e:
                logger.warning(f"[WATCH] Audio read error: {e}")
            finally:
                try:
                    proc.kill()
                except Exception:
                    pass
                s.ffmpeg_proc = None

            if s.stop_event.is_set():
                break

            s.audio_ok = False
            if not got_data:
                failures += 1
                if failures >= MAX_STREAM_FAILURES:
                    logger.warning(f"[WATCH] Audio stream unavailable for '{s.session_id}'")
                    return
            s.stop_event.wait(min(2 * (failures + 1), 10))

    @staticmethod
    def _read_exact(proc, size: int, stop_event: threading.Event) -> bytes:
        buf = bytearray()
        while len(buf) < size and not stop_event.is_set():
            chunk = proc.stdout.read(min(65536, size - len(buf)))
            if not chunk:
                break
            buf.extend(chunk)
        return bytes(buf)

    def _transcribe_loop(self, s: _WatchSession):
        while not s.stop_event.is_set():
            try:
                pcm = s.audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                samples = np.frombuffer(pcm, dtype=np.int16)
                if samples.size == 0:
                    continue
                rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
                if rms < SILENCE_RMS:
                    continue

                text = self._transcribe(self._to_wav(pcm), s.language)
                if not text or _is_hallucination(text):
                    continue

                with s.lock:
                    last = s.speech_buffer[-1]["text"] if s.speech_buffer else ""
                    if _similarity_ratio(text, last) > 0.85:
                        continue
                    s.speech_buffer.append({"time": time.time(), "text": text})
            except Exception as e:
                logger.warning(f"[WATCH] Transcription cycle failed: {e}")

    @staticmethod
    def _to_wav(pcm: bytes) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm)
        return buf.getvalue()

    def _transcribe(self, wav_bytes: bytes, language: str) -> str:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            return ""

        data = {"model": WHISPER_MODEL, "response_format": "json", "temperature": "0"}
        if language:
            data["language"] = language

        for attempt in range(2):
            try:
                r = requests.post(
                    GROQ_STT_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": ("chunk.wav", wav_bytes, "audio/wav")},
                    data=data,
                    timeout=30,
                )
            except requests.RequestException as e:
                logger.warning(f"[WATCH] STT request failed: {e}")
                return ""

            if r.status_code == 429:
                time.sleep(3 * (attempt + 1))
                continue
            if r.status_code != 200:
                logger.warning(f"[WATCH] STT error {r.status_code}: {r.text[:200]}")
                return ""

            return (r.json().get("text") or "").strip()

        return ""

    def _describe_image(self, jpeg_bytes: bytes) -> str:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key or not VISION_MODEL or not jpeg_bytes:
            return ""

        encoded = base64.b64encode(jpeg_bytes).decode("ascii")
        payload = {
            "model": VISION_MODEL,
            "temperature": 0.2,
            "max_tokens": 120,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "Describe in one or two short sentences what is visible on this TV screen: "
                        "people, setting, action, graphics. Do not speculate beyond what you see."
                    )},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                ],
            }],
        }

        try:
            r = requests.post(
                GROQ_CHAT_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=20,
            )
            if r.status_code != 200:
                logger.warning(f"[WATCH] Vision error {r.status_code}: {r.text[:200]}")
                return ""
            return (r.json()["choices"][0]["message"]["content"] or "").strip()
        except Exception as e:
            logger.warning(f"[WATCH] Vision request failed: {e}")
            return ""

    def _get_visual_context(self, s: _WatchSession, image_b64: str) -> str:
        if image_b64:
            try:
                if "," in image_b64[:100]:
                    image_b64 = image_b64.split(",", 1)[1]
                return self._describe_image(base64.b64decode(image_b64))
            except Exception as e:
                logger.warning(f"[WATCH] Bad client image: {e}")

        if not s.vision_enabled:
            return ""

        with s.lock:
            cached = s.vision_cache.get("text")
            cached_time = s.vision_cache.get("time", 0.0)
            jpeg = s.latest_jpeg
            jpeg_time = s.latest_jpeg_time

        now = time.time()
        if cached and now - cached_time < VISION_CACHE_SECONDS:
            return cached
        if not jpeg or now - jpeg_time > 30:
            return ""

        description = self._describe_image(jpeg)
        if description:
            with s.lock:
                s.vision_cache = {"time": time.time(), "text": description}
        return description

    def _build_context(self, s: _WatchSession, visual: str):
        now = time.time()
        with s.lock:
            speech = list(s.speech_buffer)[-6:]
            screen = list(s.screen_buffer)[-5:]

        parts = []
        sources = []

        if speech:
            lines = [f"({_age_label(now - e['time'])}) {e['text']}" for e in speech]
            parts.append("Recently spoken on the channel: " + " ".join(lines))
            sources.append("audio")

        if screen:
            lines = [f"({_age_label(now - e['time'])}) {e['text']}" for e in screen]
            parts.append("Text visible on screen: " + " | ".join(lines))
            sources.append("screen_text")

        if visual:
            parts.append("What the screen looks like: " + visual)
            sources.append("vision")

        context = "\n".join(parts)
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[-MAX_CONTEXT_CHARS:]

        return context, sources

    def _watch_user_id(self, user_id: str) -> str:
        return f"{user_id}_watch"

    def _reset_watch_history(self, session_id: str):
        try:
            self.conversation_engine.reset(self._watch_user_id(session_id))
        except Exception:
            pass

    def _scrub_history(self, watch_uid: str, augmented: str, question: str):
        try:
            from engines.conversation_engine import _CONVERSATION_HISTORY
            history = _CONVERSATION_HISTORY.get(watch_uid, [])
            for msg in reversed(history):
                if msg.get("role") == "user" and msg.get("content") == augmented:
                    msg["content"] = question
                    break
        except Exception:
            pass

    def ask(self, session_id: str, user_id: str, question: str, image_b64: str = None) -> dict:
        with self._sessions_lock:
            session = self._sessions.get(session_id)

        if not session:
            return {
                "text": "I'm not currently watching anything with you — start playing a channel first.",
                "voice": "I'm not currently watching anything with you.",
                "meta": {"type": "watch_companion", "error": "no_active_session"},
            }

        session.last_activity = time.time()

        visual = self._get_visual_context(session, image_b64)
        context, sources = self._build_context(session, visual)

        header = f"The user is watching '{session.channel_name or 'a live channel'}' right now."

        if context:
            augmented = (
                f"[{header}\n{context}\n"
                f"Use this only where it is clearly relevant. It may contain recognition noise. "
                f"Never mention transcripts, OCR, or captured text; answer naturally as if watching along. "
                f"If the context does not answer the question, say you can't tell from what's on right now.]\n"
                f"The user asks: {question}"
            )
        else:
            augmented = (
                f"[{header} Nothing readable or audible has been captured yet, so you cannot know "
                f"what is on screen. Say so briefly if the question depends on it.]\n"
                f"The user asks: {question}"
            )

        watch_uid = self._watch_user_id(user_id)
        result = self.conversation_engine.chat(watch_uid, augmented)
        self._scrub_history(watch_uid, augmented, question)

        meta = result.setdefault("meta", {})
        meta["type"] = "watch_companion"
        meta["context_sources"] = sources
        return result


if __name__ == "__main__":
    class _FakeConversationEngine:
        def chat(self, user_id, user_text):
            return {"text": f"[FAKE REPLY to]: {user_text}", "voice": "fake reply", "meta": {}}

        def reset(self, user_id):
            pass

    engine = WatchCompanionEngine(_FakeConversationEngine())
    print(engine.start_session("test_session", "https://example.com/fake-stream.m3u8", "Test Channel", language="en"))
    time.sleep(2)
    print(engine.get_status("test_session"))
    print(engine.ask("test_session", "test_user", "what's happening right now?"))
    engine.shutdown()
