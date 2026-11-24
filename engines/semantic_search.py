import html
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from html.parser import HTMLParser

logger = logging.getLogger("FalconAI.SemanticMovieEngine")

_model = None
_EMBEDDINGS_DISABLED = False

TAXONOMY_KEYWORDS = {
    "psychological drama": ["psychological", "mind", "subconscious", "mental", "internal", "tragedy"],
    "internal grief and loss": ["grief", "loss", "mourning", "sorrow", "sits with you", "lingering"],
    "existential philosophical drama": ["meaning", "philosophy", "existential", "mortality", "reality", "isolation"],
    "slow atmospheric cinema": ["slow", "atmospheric", "cinematic", "ambient", "quiet", "melancholy", "days afterward"],
    "intellectual mystery thriller": ["twist", "puzzle", "mystery", "memory", "detective", "thriller"],
    "quiet character study": ["character", "lonely", "cold", "relationship", "drama"],
    "sci-fi dystopia": ["sci-fi", "future", "dystopia", "space", "time"],
    "crime drama": ["crime", "heist", "revenge", "courtroom"],
}

TAXONOMY = list(TAXONOMY_KEYWORDS.keys())

CURATED_FALLBACK_BY_TAXONOMY = {
    "internal grief and loss": [
        {
            "title": "Manchester by the Sea",
            "url": "https://tubitv.com/search/Manchester%20by%20the%20Sea",
            "matched_term": "internal grief and loss",
        },
        {
            "title": "Aftersun",
            "url": "https://tubitv.com/search/Aftersun",
            "matched_term": "internal grief and loss",
        },
    ],
    "psychological drama": [
        {
            "title": "Black Swan",
            "url": "https://tubitv.com/search/Black%20Swan",
            "matched_term": "psychological drama",
        },
        {
            "title": "Shutter Island",
            "url": "https://tubitv.com/search/Shutter%20Island",
            "matched_term": "psychological drama",
        },
    ],
    "intellectual mystery thriller": [
        {
            "title": "Memento",
            "url": "https://tubitv.com/search/Memento",
            "matched_term": "intellectual mystery thriller",
        },
        {
            "title": "Prisoners",
            "url": "https://tubitv.com/search/Prisoners",
            "matched_term": "intellectual mystery thriller",
        },
    ],
    "slow atmospheric cinema": [
        {
            "title": "Blade Runner 2049",
            "url": "https://tubitv.com/search/Blade%20Runner%202049",
            "matched_term": "slow atmospheric cinema",
        },
        {
            "title": "Drive",
            "url": "https://tubitv.com/search/Drive",
            "matched_term": "slow atmospheric cinema",
        },
    ],
}


def _embeddings_allowed() -> bool:
    if _EMBEDDINGS_DISABLED:
        return False
    return os.getenv("FALCONAI_ENABLE_EMBEDDINGS", "0").strip().lower() in ("1", "true", "yes")


def _get_model():
    global _model, _EMBEDDINGS_DISABLED
    if not _embeddings_allowed():
        return None
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("[SEMANTIC] Loading local embedding model...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[SEMANTIC] Model loaded.")
        except Exception as exc:
            _EMBEDDINGS_DISABLED = True
            logger.warning("[SEMANTIC] Falling back to lightweight scorer: %s", exc)
            return None
    return _model


@lru_cache(maxsize=1)
def _taxonomy_embeddings():
    model = _get_model()
    if model is None:
        return None
    return model.encode(TAXONOMY, normalize_embeddings=True)


def _keyword_taxonomy_scores(query: str):
    q = (query or "").lower()
    scores = []
    for label in TAXONOMY:
        kws = TAXONOMY_KEYWORDS[label]
        hits = sum(1.0 for kw in kws if kw in q)
        if "internal" in q and "grief" in label:
            hits += 2.0
        if ("sits with you" in q or "days afterward" in q) and ("atmospheric" in label or "grief" in label):
            hits += 1.5
        scores.append((label, hits))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def expand_query_to_search_terms(query: str, top_k: int = 3):
    model = _get_model()
    tax_vecs = _taxonomy_embeddings()

    if model is not None and tax_vecs is not None:
        try:
            query_vec = model.encode([query], normalize_embeddings=True)[0]
            sims = tax_vecs @ query_vec
            top_indices = sorted(range(len(sims)), key=lambda idx: float(sims[idx]), reverse=True)[:top_k]
            terms = [(TAXONOMY[i], float(sims[i])) for i in top_indices]
            logger.info("[SEMANTIC] Query '%s' -> concrete terms: %s", query, terms)
            return terms
        except Exception as exc:
            logger.warning("[SEMANTIC] Embedding inference failed, using keyword fallback: %s", exc)

    ranked = _keyword_taxonomy_scores(query)
    terms = [(label, round(score * 0.25 + 0.1, 3)) for label, score in ranked[:top_k]]
    logger.info("[SEMANTIC] Query '%s' -> keyword terms: %s", query, terms)
    return terms


def _term_to_tubi_query(term: str) -> str:
    kws = TAXONOMY_KEYWORDS.get(term)
    if kws:
        return " ".join(kws[:2])
    words = [w for w in re.findall(r"\b[a-z]{3,}\b", (term or "").lower()) if w not in {"and", "the", "film", "drama"}]
    return " ".join(words[:2]) or "drama"


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


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _iter_jsonld_items(block):
    if isinstance(block, list):
        for entry in block:
            yield from _iter_jsonld_items(entry)
    elif isinstance(block, dict):
        if "@graph" in block:
            yield from _iter_jsonld_items(block["@graph"])
        item_type = block.get("@type")
        types = item_type if isinstance(item_type, list) else [item_type]
        if any(t in ("Movie", "VideoObject", "CreativeWork") for t in types):
            yield block


def _scrape_tubi(term: str, timeout: int = 4):
    tubi_q = _term_to_tubi_query(term)
    encoded = urllib.parse.quote(tubi_q)
    url = f"https://tubitv.com/search/{encoded}"
    candidates = []

    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_html = response.read(1_500_000).decode("utf-8", errors="ignore")

        parser = TubiJSONLDParser()
        parser.feed(raw_html)

        for block in parser.json_data:
            for item in _iter_jsonld_items(block):
                title = html.unescape(str(item.get("name") or "")).strip()
                if not title:
                    continue
                link = str(item.get("url") or url).strip()
                if not link.startswith("http"):
                    link = f"https://tubitv.com{link}"
                candidates.append({
                    "title": title,
                    "description": html.unescape(str(item.get("description") or "")).strip(),
                    "url": link,
                    "matched_term": term,
                    "source": "Tubi JSON-LD",
                })

        if not candidates:
            pattern = r'<a[^>]+href="(/movies/\d+/[^"]+)"[^>]*>(.*?)</a>'
            for link, raw_title in re.findall(pattern, raw_html, re.DOTALL | re.IGNORECASE):
                clean_title = html.unescape(re.sub(r"<.*?>", " ", raw_title))
                clean_title = re.sub(r"\s+", " ", clean_title).strip()
                if len(clean_title) >= 2:
                    candidates.append({
                        "title": clean_title,
                        "description": "",
                        "url": f"https://tubitv.com{link}",
                        "matched_term": term,
                        "source": "Tubi DOM",
                    })
    except Exception as exc:
        logger.warning("[SEMANTIC] Scrape failed for '%s' (%s): %s", term, tubi_q, exc)

    return candidates


def _scrape_all_terms(terms, per_term_limit=8):
    all_candidates = []
    workers = min(len(terms) or 1, 2)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_scrape_tubi, term): term for term, _ in terms}
        for future in as_completed(futures):
            try:
                results = future.result(timeout=6)
                all_candidates.extend(results[:per_term_limit])
            except Exception as exc:
                logger.warning("[SEMANTIC] Worker timeout/error: %s", exc)

    seen = set()
    deduped = []
    for c in all_candidates:
        if c["url"] not in seen:
            seen.add(c["url"])
            deduped.append(c)

    return deduped


def _lexical_score(query: str, cand: dict) -> float:
    q_tokens = set(re.findall(r"\b[a-z]{3,}\b", (query or "").lower()))
    corpus = f"{cand.get('title', '')} {cand.get('description', '')} {cand.get('matched_term', '')}".lower()
    corpus_tokens = set(re.findall(r"\b[a-z]{3,}\b", corpus))
    overlap = len(q_tokens & corpus_tokens)
    bonus = 0.25 if any(k in corpus for k in ("drama", "thriller", "mystery")) else 0.0
    return round(min(0.99, 0.35 + overlap * 0.1 + bonus), 3)


class SemanticMovieEngine:
    def __init__(self):
        pass

    def search(self, query: str, top_k: int = 5):
        if not query or not query.strip():
            return {"original_query": query, "results": []}

        concrete_terms = expand_query_to_search_terms(query, top_k=2)
        candidates = _scrape_all_terms(concrete_terms, per_term_limit=6)

        if not candidates:
            primary_term = concrete_terms[0][0] if concrete_terms else "psychological drama"
            fallback_items = CURATED_FALLBACK_BY_TAXONOMY.get(
                primary_term, CURATED_FALLBACK_BY_TAXONOMY["psychological drama"]
            )
            return {
                "original_query": query,
                "concrete_terms_used": [t for t, _ in concrete_terms],
                "results": [
                    {
                        "title": item["title"],
                        "platform": "Tubi TV",
                        "url": item["url"],
                        "match_score": 0.75,
                        "matched_via_term": item["matched_term"],
                        "source": "Curated Fallback",
                    }
                    for item in fallback_items[:top_k]
                ],
                "note": "Used curated fallback because Tubi returned no direct candidates.",
            }

        model = _get_model()
        if model is not None:
            try:
                query_vec = model.encode([query], normalize_embeddings=True)[0]
                corpus_texts = [f"{c['title']}. {c.get('description', '')}".strip() for c in candidates]
                candidate_vecs = model.encode(corpus_texts, normalize_embeddings=True)
                sims = candidate_vecs @ query_vec
                ranked = sorted(zip(candidates, sims), key=lambda pair: float(pair[1]), reverse=True)
                results = [
                    {
                        "title": cand["title"],
                        "platform": "Tubi TV",
                        "url": cand["url"],
                        "match_score": round(float(score), 3),
                        "matched_via_term": cand["matched_term"],
                        "source": cand.get("source", "Tubi"),
                    }
                    for cand, score in ranked[:top_k]
                ]
                return {
                    "original_query": query,
                    "concrete_terms_used": [t for t, _ in concrete_terms],
                    "results": results,
                }
            except Exception as exc:
                logger.warning("[SEMANTIC] Candidate embedding failed, using lexical score: %s", exc)

        ranked_lex = sorted(
            ((cand, _lexical_score(query, cand)) for cand in candidates),
            key=lambda pair: pair[1],
            reverse=True,
        )
        results = [
            {
                "title": cand["title"],
                "platform": "Tubi TV",
                "url": cand["url"],
                "match_score": score,
                "matched_via_term": cand["matched_term"],
                "source": cand.get("source", "Tubi"),
            }
            for cand, score in ranked_lex[:top_k]
        ]
        return {
            "original_query": query,
            "concrete_terms_used": [t for t, _ in concrete_terms],
            "results": results,
        }


if __name__ == "__main__":
    engine = SemanticMovieEngine()
    q = "A film where the tragedy is internal, not physical — something that sits with you for days afterward"
    res = engine.search(q)
    print(json.dumps(res, indent=2))
