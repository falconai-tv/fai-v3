import re
import json
import logging
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from functools import lru_cache

import numpy as np

logger = logging.getLogger("FalconAI.SemanticMovieEngine")

_model = None

def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[SEMANTIC] Loading local embedding model (first call only)...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[SEMANTIC] Model loaded.")
        except ImportError:
            logger.error(
                "[SEMANTIC] sentence-transformers not installed. "
                "Run: pip install sentence-transformers --break-system-packages"
            )
            raise
    return _model

TAXONOMY = [
    "psychological drama",
    "internal grief and loss",
    "existential philosophical drama",
    "slow atmospheric cinema",
    "intellectual mystery thriller",
    "quiet melancholic drama",
    "dark lonely isolation drama",
    "meditative art film",
    "emotional family drama",
    "war trauma drama",
    "moral ambiguity thriller",
    "surreal dreamlike narrative",
    "coming of age drama",
    "redemption story drama",
    "revenge thriller",
    "heist thriller",
    "epic adventure",
    "romantic drama",
    "comedy",
    "dark comedy satire",
    "documentary style film",
    "biographical drama",
    "crime drama",
    "legal courtroom drama",
    "medical drama",
    "sports drama",
    "supernatural horror",
    "psychological horror",
    "slasher horror",
    "monster creature horror",
    "sci-fi dystopia",
    "space exploration sci-fi",
    "time travel sci-fi",
    "post-apocalyptic survival",
    "political thriller",
    "espionage spy thriller",
    "social commentary drama",
    "marriage falling apart drama",
    "addiction and recovery drama",
    "grief and mourning drama",
    "childhood trauma drama",
    "identity crisis drama",
    "memory and amnesia thriller",
    "small town mystery",
    "courtroom justice drama",
    "father son relationship drama",
    "mother daughter relationship drama",
    "friendship and loss drama",
    "class inequality drama",
    "immigrant experience drama",
    "quiet character study",
]


@lru_cache(maxsize=1)
def _taxonomy_embeddings():
    model = _get_model()
    vectors = model.encode(TAXONOMY, normalize_embeddings=True)
    return vectors

def _cosine_sim_matrix(query_vec, matrix):
    return matrix @ query_vec

def expand_query_to_search_terms(query: str, top_k: int = 3):
    model = _get_model()
    query_vec = model.encode([query], normalize_embeddings=True)[0]

    tax_vecs = _taxonomy_embeddings()
    sims = _cosine_sim_matrix(query_vec, tax_vecs)

    top_indices = np.argsort(sims)[::-1][:top_k]
    terms = [(TAXONOMY[i], float(sims[i])) for i in top_indices]

    logger.info(f"[SEMANTIC] Query '{query}' -> concrete terms: {terms}")
    return terms

class TubiJSONLDParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.json_data = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            for attr, value in attrs:
                if attr == "type" and value == "application/ld+json":
                    self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            try:
                self.json_data.append(json.loads(data))
            except Exception:
                pass


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _scrape_tubi(term: str, timeout: int = 6):
    encoded = urllib.parse.quote(term)
    url = f"https://tubitv.com/search/{encoded}"
    candidates = []

    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")

        parser = TubiJSONLDParser()
        parser.feed(html)

        for block in parser.json_data:
            items = block if isinstance(block, list) else [block]
            for item in items:
                if isinstance(item, dict) and item.get("@type") in (
                    "Movie", "VideoObject", "CreativeWork"
                ):
                    link = item.get("url", url)
                    if not link.startswith("http"):
                        link = f"https://tubitv.com{link}"
                    candidates.append({
                        "title": item.get("name", "Unknown Title"),
                        "description": item.get("description", ""),
                        "url": link,
                        "matched_term": term,
                    })

        if not candidates:
            pattern = r'<a[^>]+href="(/movies/\d+/[^"]+)"[^>]*>(.*?)</a>'
            for link, raw_title in re.findall(pattern, html, re.DOTALL):
                clean_title = re.sub(r"<.*?>", "", raw_title).strip()
                if clean_title:
                    candidates.append({
                        "title": clean_title,
                        "description": "",
                        "url": f"https://tubitv.com{link}",
                        "matched_term": term,
                    })

    except Exception as e:
        logger.warning(f"[SEMANTIC] Scrape failed for '{term}': {e}")

    return candidates


def _scrape_all_terms(terms, per_term_limit=10):
    all_candidates = []
    with ThreadPoolExecutor(max_workers=len(terms) or 1) as executor:
        futures = {executor.submit(_scrape_tubi, term): term for term, _ in terms}
        for future in as_completed(futures):
            results = future.result()
            all_candidates.extend(results[:per_term_limit])

    seen = set()
    deduped = []
    for c in all_candidates:
        if c["url"] not in seen:
            seen.add(c["url"])
            deduped.append(c)

    return deduped

class SemanticMovieEngine:
    def __init__(self):
        pass

    def search(self, query: str, top_k: int = 5):
        if not query or not query.strip():
            return {"original_query": query, "results": []}

        model = _get_model()

        concrete_terms = expand_query_to_search_terms(query, top_k=3)

        candidates = _scrape_all_terms(concrete_terms)

        if not candidates:
            return {
                "original_query": query,
                "concrete_terms_used": concrete_terms,
                "results": [],
                "note": "No candidates found on Tubi for the derived search terms.",
            }

        query_vec = model.encode([query], normalize_embeddings=True)[0]

        corpus_texts = [
            f"{c['title']}. {c.get('description', '')}".strip()
            for c in candidates
        ]
        candidate_vecs = model.encode(corpus_texts, normalize_embeddings=True)
        sims = _cosine_sim_matrix(query_vec, candidate_vecs)

        ranked = sorted(
            zip(candidates, sims), key=lambda pair: pair[1], reverse=True
        )

        results = []
        for cand, score in ranked[:top_k]:
            results.append({
                "title": cand["title"],
                "platform": "Tubi TV",
                "url": cand["url"],
                "match_score": round(float(score), 3),
                "matched_via_term": cand["matched_term"],
            })

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