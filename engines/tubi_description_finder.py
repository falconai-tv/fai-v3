import html
import json
import logging
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

logger = logging.getLogger("FalconAI.TubiDescriptionFinder")

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "about", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just", "don",
    "now", "movie", "film", "title", "name", "forgot", "forget", "remember",
    "looking", "find", "watch", "something", "someone", "anyone", "everyone",
    "everything", "guy", "man", "woman", "person", "thing", "story", "plot",
    "scene", "called", "named", "days", "afterward", "sits", "with", "you",
    "your", "me", "it", "that", "this", "which", "who", "whom", "whose",
    "trying", "get", "back"
}

NOISE_TITLES = {
    "eagles vs. cowboys",
    "eagles vs cowboys",
}


class _TubiMetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.jsonld_blocks = []
        self.meta_desc = ""
        self._in_jsonld = False
        self._buf = []

    def handle_starttag(self, tag, attrs):
        attrs_map = {k.lower(): v for k, v in attrs if k}
        if tag.lower() == "script" and attrs_map.get("type") == "application/ld+json":
            self._in_jsonld = True
            self._buf = []
        elif tag.lower() == "meta":
            m_name = (attrs_map.get("name") or attrs_map.get("property") or "").lower()
            if m_name in ("description", "og:description", "twitter:description"):
                content = (attrs_map.get("content") or "").strip()
                if len(content) > len(self.meta_desc):
                    self.meta_desc = html.unescape(content)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._in_jsonld:
            self._in_jsonld = False
            raw = "".join(self._buf).strip()
            self._buf = []
            if raw:
                try:
                    self.jsonld_blocks.append(json.loads(raw))
                except Exception:
                    pass

    def handle_data(self, data):
        if self._in_jsonld:
            self._buf.append(data)


class TubiDescriptionFinder:
    def __init__(self, timeout: int = 4):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _fetch_text(self, url: str, max_bytes: int = 1_500_000) -> str:
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read(max_bytes).decode("utf-8", errors="ignore")

    def extract_keywords(self, description_query: str, max_terms: int = 5) -> list[str]:
        tokens = re.findall(r"\b[a-zA-Z]{3,}\b", (description_query or "").lower())
        scored = []
        seen = set()
        for tok in tokens:
            if tok in STOP_WORDS or tok in seen:
                continue
            seen.add(tok)
            scored.append((tok, len(tok)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored[:max_terms]]

    def _iter_media_items(self, block):
        if isinstance(block, list):
            for item in block:
                yield from self._iter_media_items(item)
        elif isinstance(block, dict):
            if "@graph" in block:
                yield from self._iter_media_items(block["@graph"])
            item_type = block.get("@type")
            types = item_type if isinstance(item_type, list) else [item_type]
            if any(t in ("Movie", "VideoObject", "CreativeWork", "TVSeries") for t in types):
                yield block

    def _search_tubi_candidates(self, keywords: list[str]) -> list[dict]:
        candidates = []
        terms_to_try = [" ".join(keywords[:2])] if len(keywords) >= 2 else keywords[:1]
        for term in terms_to_try:
            if not term:
                continue
            url = f"https://tubitv.com/search/{urllib.parse.quote(term)}"
            try:
                raw_html = self._fetch_text(url)
                parser = _TubiMetaParser()
                parser.feed(raw_html)
                for block in parser.jsonld_blocks:
                    for item in self._iter_media_items(block):
                        title = html.unescape(str(item.get("name") or "")).strip()
                        if not title or title.lower() in NOISE_TITLES:
                            continue
                        desc = html.unescape(str(item.get("description") or "")).strip()
                        if not desc:
                            continue
                        candidates.append({
                            "title": title,
                            "description": desc,
                            "url": f"https://tubitv.com/search/{urllib.parse.quote(title)}",
                            "source": "Tubi JSON-LD",
                        })
            except Exception as exc:
                logger.debug("Tubi candidate fetch skipped for '%s': %s", term, exc)
        return candidates

    def _search_open_web_movie_descriptions(self, keywords: list[str]) -> list[dict]:
        """Kërkon dinamikisht në Wikipedia API për filma që përputhen me përshkrimin."""
        if not keywords:
            return []

        search_query = " ".join(keywords[:4]) + " film"
        api_url = (
            "https://en.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(search_query)}&srlimit=8&format=json"
        )
        candidates = []

        try:
            raw_json = self._fetch_text(api_url, max_bytes=600_000)
            payload = json.loads(raw_json)
            entries = (payload.get("query") or {}).get("search") or []

            for entry in entries:
                title = html.unescape(str(entry.get("title") or "")).strip()
                snippet = html.unescape(re.sub(r"<.*?>", " ", str(entry.get("snippet") or ""))).strip()
                snippet = re.sub(r"\s+", " ", snippet)
                if not title or not snippet:
                    continue
                if any(bad in title.lower() for bad in ("list of ", "category:", "wikipedia:")):
                    continue
                clean_title = re.sub(r"\s*\([^)]*film[^)]*\)\s*$", "", title, flags=re.IGNORECASE).strip() or title
                candidates.append({
                    "title": clean_title,
                    "description": snippet,
                    "url": f"https://tubitv.com/search/{urllib.parse.quote(clean_title)}",
                    "source": "Live Open Web / Wikipedia",
                })
        except Exception as exc:
            logger.warning("Open web movie search failed for '%s': %s", search_query, exc)

        return candidates

    def _score_description_match(
        self, query: str, keywords: list[str], candidate: dict
    ) -> tuple[float, list[str]]:
        q_tokens = {
            w for w in re.findall(r"\b[a-z]{3,}\b", (query or "").lower())
            if w not in STOP_WORDS
        }
        desc = (candidate.get("description") or "").lower()
        title = (candidate.get("title") or "").lower()
        combined = f"{title} {desc}"

        matched = sorted(w for w in q_tokens if w in combined)
        desc_hits = sum(1 for w in matched if w in desc)
        kw_hits = sum(1 for kw in keywords if kw in desc)

        if desc_hits == 0 and kw_hits == 0:
            return 0.0, []

        multi_match_bonus = (desc_hits - 1) * 2.0 if desc_hits >= 2 else -1.5
        specificity_bonus = sum(min(len(w) / 10.0, 1.0) for w in matched)
        score = (desc_hits * 2.5) + (kw_hits * 1.5) + multi_match_bonus + specificity_bonus

        if score <= 0:
            return 0.0, []

        return round(score, 2), matched

    def find_by_description(self, description_query: str, top_k: int = 3) -> dict:
        keywords = self.extract_keywords(description_query, max_terms=5)
        candidates = self._search_tubi_candidates(keywords)
        candidates.extend(self._search_open_web_movie_descriptions(keywords))

        seen_titles = set()
        scored = []

        for cand in candidates:
            norm_title = cand["title"].lower()
            if norm_title in seen_titles:
                continue
            score, matched_words = self._score_description_match(description_query, keywords, cand)
            if score <= 0:
                continue
            seen_titles.add(norm_title)
            scored.append({
                "title": cand["title"],
                "platform": "Tubi TV",
                "url": cand["url"],
                "description": cand["description"],
                "source": cand.get("source", "Live Search"),
                "matched_keywords": matched_words,
                "score": score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        return {
            "query": description_query,
            "extracted_keywords": keywords,
            "results": scored[:top_k],
        }


if __name__ == "__main__":
    finder = TubiDescriptionFinder()
    q = "A film where the tragedy is internal, not physical — something that sits with you for days afterward"
    print(json.dumps(finder.find_by_description(q), indent=2))
