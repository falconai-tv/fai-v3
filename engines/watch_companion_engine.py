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
from urllib.parse import urljoin

import numpy as np
import requests

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("FalconAI.WatchCompanion")


def _find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return ""


FFMPEG = _find_ffmpeg()

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")
VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

SAMPLE_RATE = 16000
BYTES_PER_SECOND = SAMPLE_RATE * 2
AUDIO_CHUNK_SECONDS = 10
SILENCE_RMS = 120.0
MAX_STREAM_FAILURES = 6
IDLE_TIMEOUT = 600
REAPER_INTERVAL = 30
VISION_CACHE_SECONDS = 15
MAX_CONTEXT_CHARS = 1800
FIRST_FRAME_WAIT_SECONDS = 12

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


def _detect_ocr() -> tuple:
    """Returns (ocr_available, ocr_lang)."""
    if pytesseract is None:
        return False, "eng"
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return False, "eng"
    try:
        available = set(pytesseract.get_languages(config=""))
    except Exception:
        return True, "eng"
    langs = [l for l in ("eng", "sqi") if l in available]
    return True, ("+".join(langs) if langs else "eng")


def _pick_low_variant(url: str) -> str:
    """
    If the URL is an HLS master playlist, return the lowest-bandwidth variant
    that has video. Otherwise return the URL unchanged.
    Much cheaper to decode on small CPUs.
    """
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if r.status_code != 200 or "#EXT-X-STREAM-INF" not in r.text:
            return url

        lines = r.text.splitlines()
        candidates = []
        for i, line in enumerate(lines):
            if not line.startswith("#EXT-X-STREAM-INF"):
                continue
            m = re.search(r"BANDWIDTH=(\d+)", line)
            bw = int(m.group(1)) if m else 10 ** 12
            has_video = "RESOLUTION=" in line
            for nxt in lines[i + 1:]:
                nxt = nxt.strip()
                if nxt and not nxt.startswith("#"):
                    candidates.append((not has_video, bw, urljoin(url, nxt)))
                    break

        if not candidates:
            return url

        candidates.sort()
        chosen = candidates[0][2]
        logger.info(f"[WATCH] Using low variant: {chosen}")
        return chosen
    except Exception as e:
        logger.warning(f"[WATCH] Could not resolve HLS variant: {e}")
        return url


@dataclass
class _WatchSession:
    session_id: str
    channel_url: str
    channel_name: str = ""
    program_title: str = ""
    epg_info: str = ""
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
        self._ffmpeg_available = bool(FFMPEG)
        self._ocr_ok, self._ocr_lang = _detect_ocr()
        self._shutdown = threading.Event()

        if not self._ffmpeg_available:
            logger.warning("[WATCH] ffmpeg not found - audio and video streaming will be limited")
        else:
            logger.info(f"[WATCH] Using ffmpeg at: {FFMPEG}")

        if not self._ocr_ok:
            logger.warning("[WATCH] tesseract not found - OCR disabled, using vision only")

        self._reaper = threading.Thread(target=self._reaper_loop, daemon=True)
        self._reaper.start()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(self, session_id: str, channel_url: str, channel_name: str = "",
                      capture_interval: float = 5.0, language: str = None,
                      enable_audio: bool = True, enable_vision: bool = True,
                      program_title: str = "", epg_info: str = "") -> dict:
        self.stop_session(session_id)

        has_key = bool(os.getenv("GROQ_API_KEY"))
        audio_on = bool(enable_audio and self._ffmpeg_available and has_key)
        vision_on = bool(enable_vision and has_key and VISION_MODEL)

        session = _WatchSession(
            session_id=session_id,
            channel_url=channel_url,
            channel_name=channel_name,
            program_title=program_title or "",
            epg_info=epg_info or "",
            language=language,
            capture_interval=max(2.0, float(capture_interval)),
            audio_enabled=audio_on,
            vision_enabled=vision_on,
        )

        workers = [self._video_loop]
        if self._ocr_ok:
            workers.append(self._ocr_loop)
        if audio_on:
            workers += [self._audio_reader_loop, self._transcribe_loop]

        for target in workers:
            t = threading.Thread(target=target, args=(session,), daemon=True)
            session.threads.append(t)

        with self._sessions_lock:
            self._sessions[session_id] = session

        self._reset_watch_history(session_id)

        for t in session.threads:
            t.start()

        logger.info(
            f"[WATCH] Started '{session_id}' on '{channel_name}' "
            f"program='{program_title}' audio={audio_on} vision={vision_on} ocr={self._ocr_ok}"
        )

        return {
            "status": "started",
            "session_id": session_id,
            "channel_name": channel_name,
            "program_title": program_title,
            "epg_info": epg_info,
            "features": {"ocr": self._ocr_ok, "audio": audio_on, "vision": vision_on},
        }

    def update_program_context(self, session_id: str, program_title: str = None, epg_info: str = None):
        with self._sessions_lock:
            session = self._sessions.get(session_id)
        if not session:
            return
        with session.lock:
            if program_title is not None and program_title != "":
                session.program_title = program_title
            if epg_info is not None and epg_info != "":
                session.epg_info = epg_info
            session.last_activity = time.time()

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
            frame_age = (
                int(time.time() - session.latest_jpeg_time)
                if session.latest_jpeg_time else None
            )
            return {
                "status": "active",
                "session_id": session_id,
                "channel_name": session.channel_name,
                "program_title": session.program_title,
                "epg_info": session.epg_info,
                "video_ok": session.video_ok,
                "audio_ok": session.audio_ok,
                "audio_enabled": session.audio_enabled,
                "vision_enabled": session.vision_enabled,
                "vision_model": VISION_MODEL,
                "ocr_enabled": self._ocr_ok,
                "ffmpeg": FFMPEG or None,
                "has_frame": session.latest_jpeg is not None,
                "frame_age_seconds": frame_age,
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

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def debug_grab(self, url: str, timeout: int = 25, use_low_variant: bool = True) -> dict:
        if not FFMPEG:
            return {"error": "ffmpeg not found"}

        resolved = _pick_low_variant(url) if use_low_variant else url
        cmd = [
            FFMPEG, "-nostdin", "-loglevel", "info",
            "-user_agent", USER_AGENT,
            "-i", resolved,
            "-an", "-frames:v", "1",
            "-vf", "scale=640:-2",
            "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
        ]
        t0 = time.time()
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return {
                "resolved_url": resolved,
                "returncode": p.returncode,
                "jpeg_bytes": len(p.stdout),
                "seconds": round(time.time() - t0, 1),
                "stderr_tail": p.stderr.decode("utf-8", "ignore")[-1500:],
            }
        except subprocess.TimeoutExpired as e:
            return {
                "resolved_url": resolved,
                "error": "timeout",
                "seconds": timeout,
                "stderr_tail": (e.stderr or b"").decode("utf-8", "ignore")[-1500:],
            }
        except Exception as e:
            return {"resolved_url": resolved, "error": str(e)}

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    @staticmethod
    def _drain_stderr(proc, sid: str):
        try:
            for line in iter(proc.stderr.readline, b""):
                msg = line.decode("utf-8", errors="ignore").strip()
                if msg:
                    logger.warning(f"[WATCH][ffmpeg:{sid}] {msg}")
        except Exception:
            pass

    def _publish_frame(self, s: _WatchSession, frame):
        try:
            self._store_jpeg(s, frame)
        except Exception as e:
            logger.warning(f"[WATCH] Could not store frame: {e}")

        s.video_ok = True
        if self._ocr_ok:
            s.pending_frame = frame
            s.frame_ready.set()

    def _store_jpeg(self, s: _WatchSession, frame):
        h, w = frame.shape[:2]
        if w > 640:
            frame = cv2.resize(frame, (640, int(h * 640 / w)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ok:
            with s.lock:
                s.latest_jpeg = buf.tobytes()
                s.latest_jpeg_time = time.time()

    def _video_loop(self, s: _WatchSession):
        failures = 0
        video_url = _pick_low_variant(s.channel_url)

        while not s.stop_event.is_set():
            if not self._ffmpeg_available:
                self._video_loop_cv2(s, video_url)
                return

            cmd = [
                FFMPEG, "-nostdin", "-loglevel", "warning",
                "-user_agent", USER_AGENT,
                "-rw_timeout", "10000000",
                "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
                "-probesize", "2000000", "-analyzeduration", "2000000",
                "-i", video_url,
                "-an",
                "-vf", f"fps=1/{s.capture_interval},scale=960:-2",
                "-q:v", "5",
                "-f", "image2pipe", "-vcodec", "mjpeg",
                "pipe:1",
            ]

            proc = None
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                s.ffmpeg_video_proc = proc
                threading.Thread(
                    target=self._drain_stderr, args=(proc, s.session_id), daemon=True
                ).start()
                buffer = bytearray()

                while not s.stop_event.is_set():
                    chunk = proc.stdout.read1(65536)
                    if not chunk:
                        break
                    buffer.extend(chunk)

                    while True:
                        start = buffer.find(b"\xff\xd8")
                        if start == -1:
                            buffer.clear()
                            break
                        end = buffer.find(b"\xff\xd9", start + 2)
                        if end == -1:
                            if start > 0:
                                del buffer[:start]
                            break

                        jpeg_data = bytes(buffer[start:end + 2])
                        del buffer[:end + 2]

                        frame = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            failures = 0
                            self._publish_frame(s, frame)
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

    def _video_loop_cv2(self, s: _WatchSession, url: str = None):
        url = url or s.channel_url
        cap = None
        failures = 0
        last_pick = 0.0
        try:
            while not s.stop_event.is_set():
                if cap is None:
                    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
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
                if now - last_pick >= s.capture_interval:
                    ok, frame = cap.retrieve()
                    if ok and frame is not None:
                        self._publish_frame(s, frame)
                        last_pick = now
        except Exception as e:
            logger.error(f"[WATCH] Video loop CV2 crashed for '{s.session_id}': {e}")
        finally:
            s.video_ok = False
            if cap is not None:
                cap.release()

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

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
                text = self._extract_text(frame)
                if text:
                    self._push_screen(s, text)
            except Exception as e:
                logger.warning(f"[WATCH] OCR cycle failed: {e}")

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

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def _audio_reader_loop(self, s: _WatchSession):
        failures = 0
        chunk_bytes = BYTES_PER_SECOND * AUDIO_CHUNK_SECONDS
        while not s.stop_event.is_set():
            cmd = [
                FFMPEG, "-nostdin", "-loglevel", "error",
                "-user_agent", USER_AGENT,
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

    # ------------------------------------------------------------------
    # Vision
    # ------------------------------------------------------------------

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
                timeout=25,
            )
            if r.status_code != 200:
                logger.warning(f"[WATCH] Vision error {r.status_code} ({VISION_MODEL}): {r.text[:200]}")
                return ""
            desc = (r.json()["choices"][0]["message"]["content"] or "").strip()
            if desc:
                logger.info(f"[WATCH] Vision description ({VISION_MODEL}): {desc[:100]}")
            return desc
        except Exception as e:
            logger.warning(f"[WATCH] Vision request failed ({VISION_MODEL}): {e}")
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
        if not jpeg or now - jpeg_time > 45:
            return ""

        description = self._describe_image(jpeg)
        if description:
            with s.lock:
                s.vision_cache = {"time": time.time(), "text": description}
        return description

    # ------------------------------------------------------------------
    # Context + ask
    # ------------------------------------------------------------------

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

    def _watch_user_id(self, session_id: str) -> str:
        return f"{session_id}_watch"

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

    def _wait_for_first_frame(self, s: _WatchSession):
        deadline = time.time() + FIRST_FRAME_WAIT_SECONDS
        while time.time() < deadline and not s.stop_event.is_set():
            with s.lock:
                if s.latest_jpeg:
                    return
            time.sleep(0.3)

    def ask(self, session_id: str, user_id: str, question: str, image_b64: str = None,
            program_title: str = None, epg_info: str = None) -> dict:
        with self._sessions_lock:
            session = self._sessions.get(session_id)

        if not session:
            return {
                "text": "I'm not currently watching anything with you — start playing a channel first.",
                "voice": "I'm not currently watching anything with you.",
                "meta": {"type": "watch_companion", "error": "no_active_session"},
            }

        if program_title is not None or epg_info is not None:
            self.update_program_context(session_id, program_title=program_title, epg_info=epg_info)

        session.last_activity = time.time()

        if not image_b64 and session.vision_enabled:
            self._wait_for_first_frame(session)

        visual = self._get_visual_context(session, image_b64)
        context, sources = self._build_context(session, visual)

        with session.lock:
            prog_title = session.program_title
            prog_info = session.epg_info

        epg_parts = []
        if prog_title:
            epg_parts.append(f"Current program/show: {prog_title}")
            sources.append("epg_title")
        if prog_info:
            epg_parts.append(f"Program details: {prog_info}")
            sources.append("epg_info")

        epg_line = (" | ".join(epg_parts) + "\n") if epg_parts else ""
        header = f"The user is watching '{session.channel_name or 'a live channel'}' right now."

        if context or epg_line:
            augmented = (
                f"[{header}\n{epg_line}{context}\n"
                f"Use this only where it is clearly relevant. It may contain recognition noise. "
                f"Never mention transcripts, OCR, or captured text; answer naturally as if watching along. "
                f"Answer in the same language as the user's question. "
                f"If the context does not answer the question, say you can't tell from what's on right now.]\n"
                f"The user asks: {question}"
            )
        else:
            augmented = (
                f"[{header} Nothing readable or audible has been captured yet, so you cannot know "
                f"what is on screen. Answer in the same language as the user's question, and say briefly "
                f"if you can't tell from what's on right now.]\n"
                f"The user asks: {question}"
            )

        watch_uid = self._watch_user_id(session_id)
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
    print(engine.start_session(
        "test_session",
        "https://example.com/fake-stream.m3u8",
        "Test Channel",
        language="en",
        program_title="Evening News",
        epg_info="Live market & global briefing",
    ))
    time.sleep(2)
    print(engine.get_status("test_session"))
    print(engine.ask("test_session", "test_user", "what's happening right now?"))
    engine.shutdown()
