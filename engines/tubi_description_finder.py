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
    "looking", "find", "watch", "something", "someone", "guy", "man", "woman",
    "person", "thing", "story", "plot", "scene", "called", "named"
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
    def __init__(self, timeout: int = 5):
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

    def _fetch_html(self, url: str, max_bytes: int = 1_500_000) -> str:
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read(max_bytes).decode("utf-8", errors="ignore")

    def extract_keywords(self, description_query: str, max_terms: int = 4) -> list[str]:
        tokens = re.findall(r"\b[a-zA-Z]{3,}\b", (description_query or "").lower())
        scored = []
        seen = set()
        for tok in tokens:
            if tok in STOP_WORDS or tok in seen:
                continue
            seen.add(tok)
            # Fjalët më të gjata shpesh janë më specifike për komplotin
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

    def _fetch_movie_page_description(self, movie_url: str) -> str:
        try:
            page_html = self._fetch_html(movie_url, max_bytes=800_000)
            parser = _TubiMetaParser()
            parser.feed(page_html)

            for block in parser.jsonld_blocks:
                for item in self._iter_media_items(block):
                    desc = html.unescape(str(item.get("description") or "")).strip()
                    if len(desc) > 20:
                        return desc

            if len(parser.meta_desc) > 20:
                return parser.meta_desc
        except Exception as exc:
            logger.debug("Could not fetch movie detail page %s: %s", movie_url, exc)
        return ""

    def _search_tubi_for_term(self, term: str) -> list[dict]:
        encoded = urllib.parse.quote(term)
        search_url = f"https://tubitv.com/search/{encoded}"
        candidates = []

        try:
            raw_html = self._fetch_html(search_url)
            parser = _TubiMetaParser()
            parser.feed(raw_html)

            for block in parser.jsonld_blocks:
                for item in self._iter_media_items(block):
                    title = html.unescape(str(item.get("name") or "")).strip()
                    if not title:
                        continue
                    desc = html.unescape(str(item.get("description") or "")).strip()
                    url = str(item.get("url") or search_url).strip()
                    if url.startswith("/"):
                        url = f"https://tubitv.com{url}"
                    candidates.append({
                        "title": title,
                        "description": desc,
                        "url": url,
                        "matched_keyword": term,
                    })

            if not candidates:
                pattern = r'<a[^>]+href="(/movies/\d+/[^"]+)"[^>]*>(.*?)</a>'
                for link, raw_title in re.findall(pattern, raw_html, re.DOTALL | re.IGNORECASE):
                    clean_title = html.unescape(re.sub(r"<.*?>", " ", raw_title))
                    clean_title = re.sub(r"\s+", " ", clean_title).strip()
                    slug_words = link.split("/")[-1].replace("-", " ")
                    if len(clean_title) >= 2:
                        candidates.append({
                            "title": clean_title,
                            "description": slug_words,
                            "url": f"https://tubitv.com{link}",
                            "matched_keyword": term,
                        })
        except Exception as exc:
            logger.warning("Tubi search failed for keyword '%s': %s", term, exc)

        return candidates

    def _score_match(self, query: str, candidate: dict) -> tuple[float, list[str]]:
        q_tokens = {
            w for w in re.findall(r"\b[a-z]{3,}\b", (query or "").lower())
            if w not in STOP_WORDS
        }
        title = (candidate.get("title") or "").lower()
        desc = (candidate.get("description") or "").lower()
        combined = f"{title} {desc}"

        matched_words = sorted(w for w in q_tokens if w in combined)
        desc_hits = sum(1 for w in matched_words if w in desc)
        title_hits = sum(1 for w in matched_words if w in title)

        score = (desc_hits * 2.0) + (title_hits * 1.2)
        if len(desc) > 30 and desc_hits > 0:
            score += 1.0

        return round(score, 2), matched_words

    def find_by_description(self, description_query: str, top_k: int = 3) -> dict:
        keywords = self.extract_keywords(description_query, max_terms=3)
        search_terms = keywords if keywords else [description_query.strip()]

        collected = []
        seen_urls = set()

        for term in search_terms:
            for item in self._search_tubi_for_term(term):
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    collected.append(item)
            if len(collected) >= 12:
                break

        # Plotëso përshkrimin për disa kandidatë kryesorë nëse mungon në listën e kërkimit
        for item in collected[:4]:
            if len(item.get("description") or "") < 25 and "/movies/" in item.get("url", ""):
                full_desc = self._fetch_movie_page_description(item["url"])
                if full_desc:
                    item["description"] = full_desc

        scored = []
        for item in collected:
            score, matched_words = self._score_match(description_query, item)
            scored.append({
                "title": item["title"],
                "platform": "Tubi TV",
                "url": item["url"],
                "description": item.get("description", ""),
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
