import html
import json
import logging
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

logger = logging.getLogger("FalconAI.TubiSemanticEngine")

NOISE_TITLE_PATTERNS = (
    r"\bvs\.?\b",
    r"\beagles\b",
    r"\bcowboys\b",
    r"\bnfl\b",
    r"\bsuper bowl\b",
    r"\bhighlights?\b",
    r"\bepisode\s+\d+\b",
)

CURATED_FALLBACK_MOVIES = {
    "internal_tragedy": [
        {
            "title": "Manchester by the Sea",
            "description": "An uncle is asked to take care of his teenage nephew after the boy's father dies, confronting deep internal grief.",
            "url": "https://tubitv.com/search/Manchester%20by%20the%20Sea",
        },
        {
            "title": "Aftersun",
            "description": "A daughter reflects on the shared joy and private melancholy of a holiday she took with her father.",
            "url": "https://tubitv.com/search/Aftersun",
        },
    ],
    "existential": [
        {
            "title": "Arrival",
            "description": "A linguist works with the military to communicate with alien lifeforms, reshaping her perception of time and memory.",
            "url": "https://tubitv.com/search/Arrival",
        },
        {
            "title": "Solaris",
            "description": "A psychologist travels to a space station orbiting a mysterious ocean planet that mirrors human memory.",
            "url": "https://tubitv.com/search/Solaris",
        },
    ],
    "intellectual_thriller": [
        {
            "title": "Memento",
            "description": "A man with short-term memory loss uses notes and tattoos to track down his wife's killer.",
            "url": "https://tubitv.com/search/Memento",
        },
        {
            "title": "Prisoners",
            "description": "When his daughter and her friend go missing, a desperate father takes matters into his own hands.",
            "url": "https://tubitv.com/search/Prisoners",
        },
    ],
    "atmospheric": [
        {
            "title": "Blade Runner 2049",
            "description": "A young blade runner's discovery of a long-buried secret leads him to track down former blade runner Rick Deckard.",
            "url": "https://tubitv.com/search/Blade%20Runner%202049",
        },
        {
            "title": "Drive",
            "description": "A mysterious Hollywood stuntman and mechanic moonlights as a getaway driver in a tense, neon-lit drama.",
            "url": "https://tubitv.com/search/Drive",
        },
    ],
}


def _is_noisy_title(title: str) -> bool:
    low = (title or "").strip().lower()
    if not low or len(low) < 2:
        return True
    return any(re.search(pat, low) for pat in NOISE_TITLE_PATTERNS)


class TubiJSONLDParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.json_data = []
        self.in_script = False
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attrs_dict = dict(attrs)
            if attrs_dict.get("type") == "application/ld+json":
                self.in_script = True
                self._buf = []

    def handle_endtag(self, tag):
        if tag == "script" and self.in_script:
            self.in_script = False
            raw = "".join(self._buf).strip()
            self._buf = []
            if raw:
                try:
                    self.json_data.append(json.loads(raw))
                except Exception:
                    pass

    def handle_data(self, data):
        if self.in_script:
            self._buf.append(data)


class AdvancedTubiSemanticEngine:
    def __init__(self):
        self.cognitive_weights = {
            "internal_tragedy": [
                "internal", "psychological", "mind", "subconscious",
                "grief", "silent", "melancholy", "breakdown", "tragedy",
            ],
            "existential": [
                "meaning", "philosophy", "universe", "time",
                "reality", "mortality", "truth", "isolation",
            ],
            "intellectual_thriller": [
                "twist", "puzzle", "complex", "mystery",
                "manipulation", "detective", "memory", "thriller",
            ],
            "atmospheric": [
                "slow", "dark", "cinematic", "ambient",
                "lonely", "cold", "visuals", "drama",
            ],
        }

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _parse_abstract_intent(self, query: str):
        q_lower = (query or "").lower()
        vector = {dim: 0.0 for dim in self.cognitive_weights}
        tokens = re.findall(r"\b[a-z]{3,}\b", q_lower)

        for token in tokens:
            for dim, keywords in self.cognitive_weights.items():
                if token in keywords:
                    vector[dim] += 2.0

        if "internal" in q_lower or "not physical" in q_lower or "sits with you" in q_lower:
            vector["internal_tragedy"] += 5.0
            vector["existential"] += 3.0

        if "days afterward" in q_lower or "lingering" in q_lower:
            vector["atmospheric"] += 3.5
            vector["intellectual_thriller"] += 2.0

        if all(v == 0.0 for v in vector.values()):
            vector["atmospheric"] = 2.0
            vector["intellectual_thriller"] = 1.5

        return vector

    def _build_search_terms(self, query: str, intent_vector: dict) -> str:
        top_dims = sorted(intent_vector.items(), key=lambda kv: kv[1], reverse=True)
        terms = []
        for dim, score in top_dims[:2]:
            if score > 0 and self.cognitive_weights.get(dim):
                terms.append(self.cognitive_weights[dim][0])
        if terms:
            return " ".join(terms)
        words = [
            w for w in re.findall(r"\b[a-zA-Z]{4,}\b", query or "")
            if w.lower() not in {"film", "movie", "good", "watch", "something"}
        ]
        return " ".join(words[:3]) or "drama thriller"

    def _iter_jsonld_items(self, block):
        if isinstance(block, list):
            for entry in block:
                yield from self._iter_jsonld_items(entry)
        elif isinstance(block, dict):
            if "@graph" in block:
                yield from self._iter_jsonld_items(block["@graph"])
            item_type = block.get("@type")
            types = item_type if isinstance(item_type, list) else [item_type]
            if any(t in ("Movie", "VideoObject", "CreativeWork") for t in types):
                yield block

    def search_tubi_deep(self, query: str, top_k: int = 3):
        intent_vector = self._parse_abstract_intent(query)
        search_terms = self._build_search_terms(query, intent_vector)
        encoded_query = urllib.parse.quote(search_terms)
        search_url = f"https://tubitv.com/search/{encoded_query}"
        scraped_candidates = []

        try:
            req = urllib.request.Request(search_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                raw_bytes = response.read(2_000_000)
                html_doc = raw_bytes.decode("utf-8", errors="ignore")

                parser = TubiJSONLDParser()
                parser.feed(html_doc)

                for block in parser.json_data:
                    for item in self._iter_jsonld_items(block):
                        title = html.unescape(str(item.get("name") or "")).strip()
                        if _is_noisy_title(title):
                            continue
                        desc = html.unescape(str(item.get("description") or "")).strip()
                        url = str(item.get("url") or search_url).strip()
                        if url.startswith("/"):
                            url = f"https://tubitv.com{url}"
                        scraped_candidates.append({
                            "title": title,
                            "description": desc,
                            "url": url,
                            "source": "Tubi TV JSON-LD",
                        })

                if not scraped_candidates:
                    pattern = r'<a[^>]+href="(/movies/\d+/[^"]+)"[^>]*>(.*?)</a>'
                    matches = re.findall(pattern, html_doc, re.DOTALL | re.IGNORECASE)
                    seen_urls = set()
                    for link, raw_title in matches:
                        if link in seen_urls:
                            continue
                        clean_title = html.unescape(re.sub(r"<.*?>", " ", raw_title))
                        clean_title = re.sub(r"\s+", " ", clean_title).strip()
                        if _is_noisy_title(clean_title):
                            continue
                        seen_urls.add(link)
                        scraped_candidates.append({
                            "title": clean_title,
                            "description": f"Tubi movie match for {search_terms}",
                            "url": f"https://tubitv.com{link}",
                            "source": "Tubi TV DOM Scrape",
                        })
        except Exception as exc:
            logger.warning("Tubi fetch failed for '%s': %s", search_terms, exc)

        if not scraped_candidates:
            top_dim = max(intent_vector.items(), key=lambda kv: kv[1])[0]
            for item in CURATED_FALLBACK_MOVIES.get(top_dim, CURATED_FALLBACK_MOVIES["atmospheric"]):
                scraped_candidates.append({
                    "title": item["title"],
                    "description": item["description"],
                    "url": item["url"],
                    "source": "Curated Semantic Fallback",
                })

        scored_results = []
        for cand in scraped_candidates:
            score = 1.0
            corpus = f"{cand['title']} {cand['description']}".lower()

            for dim, weight in intent_vector.items():
                if weight > 0:
                    for kw in self.cognitive_weights[dim]:
                        if kw in corpus:
                            score += weight * 1.5

            if any(word in corpus for word in ("drama", "psychological", "tragedy")):
                score += 3.0

            scored_results.append({
                "title": cand["title"],
                "platform": "Tubi TV",
                "url": cand["url"],
                "description": cand.get("description", ""),
                "source": cand["source"],
                "match_score": round(score, 2),
                "reasoning": f"Mapped via cognitive intent vector ({search_terms}).",
            })

        scored_results.sort(key=lambda x: x["match_score"], reverse=True)
        return {
            "original_query": query,
            "search_terms": search_terms,
            "cognitive_intent_vector": intent_vector,
            "results": scored_results[:top_k],
        }
