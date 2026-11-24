import cv2
import time
import logging
import threading

try:
    import pytesseract
except ImportError:
    pytesseract = None

from core.channel_registry import CHANNELS, find_best_channel, _to_dict

logger = logging.getLogger("FalconAI.SmartChannelFinder")

SCAN_SECONDS = 3.5
MAX_SCAN_CANDIDATES = 3
MAX_PARALLEL = 3
MIN_SCORE = 0.25


def _ocr_available() -> bool:
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


OCR_ENABLED = _ocr_available()


def _ocr_frame(frame) -> str:
    if not OCR_ENABLED:
        return ""
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if w < 640:
            gray = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        return pytesseract.image_to_string(gray).lower()
    except Exception:
        return ""


def _score_text(ocr_text: str, query_keywords: list) -> float:
    if not ocr_text or not query_keywords:
        return 0.0
    matches = sum(1 for kw in query_keywords if kw in ocr_text)
    return min(matches / len(query_keywords), 1.0)


def _scan_channel(channel, query_keywords: list, result_bucket: dict, bucket_lock: threading.Lock):
    cap = None
    try:
        cap = cv2.VideoCapture(channel.url)
        if not cap.isOpened():
            with bucket_lock:
                result_bucket[channel.name] = 0.0
            return

        scores = []
        start = time.time()
        frame_count = 0

        while time.time() - start < SCAN_SECONDS:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.25)
                continue

            frame_count += 1
            if frame_count % 4 != 0:
                continue

            ocr_text = _ocr_frame(frame)
            if ocr_text:
                scores.append(_score_text(ocr_text, query_keywords))

        avg_score = (sum(scores) / len(scores)) if scores else 0.0
        with bucket_lock:
            result_bucket[channel.name] = float(avg_score)
        logger.debug(f"[SCAN] {channel.name}: score={avg_score:.2f}")

    except Exception as e:
        logger.warning(f"[SCAN] Error scanning {channel.name}: {e}")
        with bucket_lock:
            result_bucket[channel.name] = 0.0
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def _extract_keywords(query: str) -> list:
    stop_words = {
        "i", "want", "to", "watch", "see", "show", "me", "a", "an", "the",
        "play", "open", "find", "get", "some", "any", "please", "dua", "te", "të",
        "shoh", "gjej", "hap", "luaj", "mi", "shiko", "nje", "një", "ndonje", "ndonjë",
        "qka", "çka", "cfare", "çfarë", "po", "jep", "jepet", "transmetohet",
        "can", "you", "could", "would", "like", "something", "about", "on",
        "channel", "kanal", "kanali", "tv", "live", "stream", "program", "emision"
    }
    words = query.lower().split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    return keywords if keywords else words


class SmartChannelFinder:
    def __init__(self, channels=None):
        self.channels = channels or CHANNELS

    def find(self, user_query: str) -> dict:
        cleaned = (user_query or "").strip().lower()
        if not cleaned:
            return self._not_found_response(user_query)

        registry_match = find_best_channel(cleaned)
        if registry_match and self._is_confident_name_match(cleaned, registry_match):
            logger.info(f"[FINDER] Named match: {registry_match['name']}")
            return self._stream_response(registry_match)

        keywords = _extract_keywords(cleaned)
        if not keywords:
            return self._not_found_response(user_query)

        # 1. Provo përputhje të fortë nga metadata / tags / kategori pa hapur video
        best_meta_channel, meta_score = self._best_metadata_match(keywords)
        if best_meta_channel and meta_score >= 0.6:
            logger.info(f"[FINDER] Metadata match: {best_meta_channel.name} (score={meta_score:.2f})")
            return self._stream_response(_to_dict(best_meta_channel))

        # 2. Vetëm nëse ka OCR aktiv, skano një grup të vogël kandidatësh
        if not OCR_ENABLED:
            if best_meta_channel and meta_score > 0:
                return self._stream_response(_to_dict(best_meta_channel))
            if registry_match:
                return self._stream_response(registry_match)
            return self._not_found_response(user_query)

        candidates = self._pick_candidates(keywords)
        logger.info(f"[FINDER] Scanning {len(candidates)} channels: {[c.name for c in candidates]}")

        result_bucket = {}
        bucket_lock = threading.Lock()

        for i in range(0, len(candidates), MAX_PARALLEL):
            batch = candidates[i:i + MAX_PARALLEL]
            batch_threads = []
            for ch in batch:
                t = threading.Thread(
                    target=_scan_channel,
                    args=(ch, keywords, result_bucket, bucket_lock),
                    daemon=True,
                )
                t.start()
                batch_threads.append(t)
            for t in batch_threads:
                t.join(timeout=SCAN_SECONDS + 2)

        if not result_bucket:
            if registry_match:
                return self._stream_response(registry_match)
            return self._not_found_response(user_query)

        best_name = max(result_bucket, key=result_bucket.get)
        best_score = result_bucket[best_name]
        logger.info(f"[FINDER] Best match: {best_name} (score={best_score:.2f})")

        if best_score < MIN_SCORE:
            if best_meta_channel and meta_score > 0:
                return self._stream_response(_to_dict(best_meta_channel))
            if registry_match:
                logger.info(f"[FINDER] Score too low, using registry fallback: {registry_match['name']}")
                return self._stream_response(registry_match)
            return self._not_found_response(user_query)

        winner = next((ch for ch in self.channels if ch.name == best_name), None)
        if winner:
            return self._stream_response(_to_dict(winner))

        return self._not_found_response(user_query)

    def _best_metadata_match(self, keywords: list):
        best_ch = None
        best_score = 0.0
        for ch in self.channels:
            haystack_parts = [
                (ch.name or "").lower(),
                (getattr(ch, "category", "") or "").lower(),
                " ".join(t.lower() for t in (getattr(ch, "tags", None) or [])),
            ]
            haystack = " ".join(haystack_parts)
            if not haystack.strip():
                continue
            hits = sum(1 for kw in keywords if kw in haystack)
            score = hits / len(keywords)
            if score > best_score:
                best_score = score
                best_ch = ch
        return best_ch, best_score

    def _is_confident_name_match(self, query: str, match: dict) -> bool:
        name_words = match["name"].lower().split()
        query_words = query.lower().split()
        overlap = sum(1 for w in name_words if w in query_words)
        return overlap >= max(1, len(name_words) // 2)

    def _pick_candidates(self, keywords: list):
        tag_matches = []
        fallback = []

        for ch in self.channels:
            tags = getattr(ch, "tags", None) or []
            cat = getattr(ch, "category", "") or ""
            tag_overlap = sum(1 for kw in keywords if any(kw in t.lower() for t in tags))
            if tag_overlap > 0:
                tag_matches.append((tag_overlap, ch))
            elif cat in ("news", "entertainment"):
                fallback.append(ch)

        tag_matches.sort(key=lambda x: x[0], reverse=True)
        candidates = [ch for _, ch in tag_matches[:MAX_SCAN_CANDIDATES]]

        if len(candidates) < MAX_SCAN_CANDIDATES:
            needed = MAX_SCAN_CANDIDATES - len(candidates)
            seen = {ch.name for ch in candidates}
            for ch in fallback:
                if ch.name not in seen:
                    candidates.append(ch)
                    seen.add(ch.name)
                    needed -= 1
                    if needed <= 0:
                        break

        return candidates

    def _stream_response(self, channel: dict) -> dict:
        return {
            "type": "video_stream",
            "data": {
                "name": channel["name"],
                "url": channel["url"],
                "autoplay": True,
                "text": f"Opening {channel['name']}...",
                "voice": f"Opening {channel['name']}."
            }
        }

    def _not_found_response(self, query: str) -> dict:
        return {
            "type": "channel",
            "data": {
                "text": f"I scanned available channels but couldn't find content matching '{query}'. Try being more specific.",
                "voice": "I couldn't find a channel matching your request."
            }
        }
