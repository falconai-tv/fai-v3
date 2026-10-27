import cv2
import time
import logging
import threading
import numpy as np

import pytesseract

from core.channel_registry import CHANNELS, find_best_channel, _to_dict

logger = logging.getLogger("FalconAI.SmartChannelFinder")

SCAN_SECONDS = 6
MAX_PARALLEL = 8
MIN_SCORE = 0.25

def _ocr_frame(frame) -> str:
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

def _scan_channel(channel, query_keywords: list, result_bucket: dict):
    cap = None
    try:
        cap = cv2.VideoCapture(channel.url)
        if not cap.isOpened():
            result_bucket[channel.name] = 0.0
            return

        scores = []
        start = time.time()
        frame_count = 0

        while time.time() - start < SCAN_SECONDS:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.3)
                continue

            frame_count += 1

            if frame_count % 3 != 0:
                continue

            ocr_text = _ocr_frame(frame)
            score = _score_text(ocr_text, query_keywords)
            scores.append(score)

        result_bucket[channel.name] = float(np.mean(scores)) if scores else 0.0
        logger.debug(f"[SCAN] {channel.name}: score={result_bucket[channel.name]:.2f}")

    except Exception as e:
        logger.warning(f"[SCAN] Error scanning {channel.name}: {e}")
        result_bucket[channel.name] = 0.0
    finally:
        if cap is not None:
            cap.release()


def _extract_keywords(query: str) -> list:
    stop_words = {
        "i", "want", "to", "watch", "see", "show", "me", "a", "an", "the",
        "play", "open", "find", "get", "some", "any", "please", "dua", "te",
        "shoh", "gjej", "hap", "luaj", "mi", "shiko", "nje", "ndonje",
        "can", "you", "could", "would", "like", "something", "about", "on",
        "channel", "kanal", "tv", "live", "stream", "news", "lajme"
    }
    words = query.lower().split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    return keywords if keywords else words


class SmartChannelFinder:
    def __init__(self, channels=None):
        self.channels = channels or CHANNELS

    def find(self, user_query: str) -> dict:
        cleaned = user_query.strip().lower()

        registry_match = find_best_channel(cleaned)
        if registry_match and self._is_confident_name_match(cleaned, registry_match):
            logger.info(f"[FINDER] Named match: {registry_match['name']}")
            return self._stream_response(registry_match)

        logger.info(f"[FINDER] No name match for '{user_query}' — starting content scan")
        keywords = _extract_keywords(cleaned)

        if not keywords:
            return self._not_found_response(user_query)

        candidates = self._pick_candidates(keywords)
        logger.info(f"[FINDER] Scanning {len(candidates)} channels: {[c.name for c in candidates]}")

        result_bucket = {}
        threads = []

        for i in range(0, len(candidates), MAX_PARALLEL):
            batch = candidates[i:i + MAX_PARALLEL]
            batch_threads = []
            for ch in batch:
                t = threading.Thread(
                    target=_scan_channel,
                    args=(ch, keywords, result_bucket),
                    daemon=True
                )
                t.start()
                batch_threads.append(t)
            for t in batch_threads:
                t.join(timeout=SCAN_SECONDS + 3)
            threads.extend(batch_threads)

        if not result_bucket:
            return self._not_found_response(user_query)

        best_name = max(result_bucket, key=result_bucket.get)
        best_score = result_bucket[best_name]

        logger.info(f"[FINDER] Best match: {best_name} (score={best_score:.2f})")

        if best_score < MIN_SCORE:
            if registry_match:
                logger.info(f"[FINDER] Score too low, using registry fallback: {registry_match['name']}")
                return self._stream_response(registry_match)
            return self._not_found_response(user_query)

        winner = next((ch for ch in self.channels if ch.name == best_name), None)
        if winner:
            return self._stream_response(_to_dict(winner))

        return self._not_found_response(user_query)

    def _is_confident_name_match(self, query: str, match: dict) -> bool:
        name_words = match["name"].lower().split()
        query_words = query.lower().split()
        overlap = sum(1 for w in name_words if w in query_words)

        return overlap >= max(1, len(name_words) // 2)

    def _pick_candidates(self, keywords: list):
        tag_matches = []
        fallback = []

        for ch in self.channels:
            if not ch.tags:
                continue
            tag_overlap = sum(1 for kw in keywords if any(kw in tag for tag in ch.tags))
            if tag_overlap > 0:
                tag_matches.append((tag_overlap, ch))
            elif ch.category in ("news", "entertainment"):
                fallback.append(ch)

        tag_matches.sort(key=lambda x: x[0], reverse=True)
        candidates = [ch for _, ch in tag_matches[:MAX_PARALLEL]]

        if len(candidates) < MAX_PARALLEL:
            needed = MAX_PARALLEL - len(candidates)
            already_names = {ch.name for ch in candidates}
            for ch in fallback:
                if ch.name not in already_names:
                    candidates.append(ch)
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