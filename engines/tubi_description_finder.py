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

BROAD_CONTEXT_WORDS = {
    "market", "company", "building", "house", "young", "working", "moving",
    "internal", "physical", "tragedy", "couple", "people"
}

CONCEPT_EXPANSIONS = {
    "internal": ["grief", "emotional", "guilt", "drama", "psychological"],
    "tragedy": ["grief", "loss", "mourning", "drama"],
    "afterward": ["aftermath", "grief", "drama"],
    "isolated": ["alone", "solitude", "survival", "drama"],
    "lonely": ["alone", "solitude", "melancholy", "drama"],
    "haunting": ["psychological", "mystery", "thriller", "drama"],
    "mind": ["psychological", "memory", "mystery"],
    "future": ["sci-fi", "science", "technology", "space"],
    "crash": ["recession", "wall", "finance", "crisis", "bank"],
    "stock": ["wall", "finance", "trader", "trading", "shares"],
    "woods": ["forest", "cabin", "remote", "thriller"],
    "thriller": ["suspense", "horror", "mystery", "psychological"],
}

MEDIA_POSITIVE_TERMS = {
    "film", "movie", "documentary", "directed", "director", "starring",
    "screenplay", "written", "released", "drama", "thriller", "comedy",
    "actor", "actress", "cinema", "biopic", "chronicles", "follows", "character",
    "horror", "suspense", "mystery"
}

COMPANY_PENALTY_TERMS = {
    "company", "headquartered", "founded", "startup", "software",
    "platform", "website", "app", "valuation", "venture", "ceo", "shareholders",
    "investors", "accelerator", "co-founders", "mentors"
}

GENERIC_CONCEPT_TITLES = {
    "organizational founder",
    "founder",
    "entrepreneurship",
    "venture capital",
    "stock market",
    "financial market",
    "market trader",
    "insider trading",
    "entrepreneurs first",
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
            rank = len(tok) + (4.0 if tok not in BROAD_CONTEXT_WORDS else 0.0)
            scored.append((tok, rank))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored[:max_terms]]

    def _expand_abstract_terms(self, keywords: list[str], query: str) -> list[str]:
        q_tokens = set(re.findall(r"\b[a-z]{3,}\b", (query or "").lower()))
        seed_words = set(keywords) | q_tokens
        expanded = list(keywords)
        seen = set(expanded)

        for word in seed_words:
            for extra in CONCEPT_EXPANSIONS.get(word, []):
                if extra not in seen and extra not in STOP_WORDS:
                    seen.add(extra)
                    expanded.append(extra)
                if len(expanded) >= 7:
                    return expanded
        return expanded

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

    def _query_wikipedia_entries(self, search_query: str) -> list[dict]:
        api_url = (
            "https://en.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(search_query)}&srlimit=10&format=json"
        )
        raw_json = self._fetch_text(api_url, max_bytes=700_000)
        payload = json.loads(raw_json)
        entries = (payload.get("query") or {}).get("search") or []
        results = []

        for entry in entries:
            raw_title = html.unescape(str(entry.get("title") or "")).strip()
            snippet = html.unescape(re.sub(r"<.*?>", " ", str(entry.get("snippet") or ""))).strip()
            snippet = re.sub(r"\s+", " ", snippet)
            if not raw_title or not snippet:
                continue
            if any(bad in raw_title.lower() for bad in ("list of ", "category:", "wikipedia:")):
                continue

            is_explicit_media_page = bool(
                re.search(
                    r"\((?:[^)]*\b)?(?:film|movie|documentary)(?:\b[^)]*)?\)\s*$",
                    raw_title,
                    re.IGNORECASE,
                )
            )
            clean_title = (
                re.sub(r"\s*\([^)]*\)\s*$", "", raw_title).strip() or raw_title
            )

            if clean_title.lower() in GENERIC_CONCEPT_TITLES and not is_explicit_media_page:
                continue

            results.append({
                "title": clean_title,
                "description": snippet,
                "url": f"https://tubitv.com/search/{urllib.parse.quote(clean_title)}",
                "source": "Live Open Web / Wikipedia",
                "is_explicit_media_page": is_explicit_media_page,
            })
        return results

    def _search_open_web_movie_descriptions(self, search_terms: list[str]) -> list[dict]:
        """Kërkon dinamikisht në Wikipedia API për filma ose dokumentarë që përputhen me përshkrimin."""
        if not search_terms:
            return []

        core_terms = " ".join(search_terms[:4])
        primary_query = f"({core_terms}) (film OR movie OR documentary)"

        try:
            candidates = self._query_wikipedia_entries(primary_query)
            if not candidates and len(search_terms) >= 2:
                fallback_terms = " ".join(search_terms[:2])
                candidates = self._query_wikipedia_entries(f"({fallback_terms}) (film OR movie)")
            return candidates
        except Exception as exc:
            logger.warning("Open web movie search failed for '%s': %s", primary_query, exc)
            return []

    def _score_description_match(
        self, query: str, expanded_terms: list[str], candidate: dict
    ) -> tuple[float, list[str]]:
        q_tokens = {
            w for w in re.findall(r"\b[a-z]{3,}\b", (query or "").lower())
            if w not in STOP_WORDS
        }
        all_target_tokens = q_tokens | set(expanded_terms)

        desc = (candidate.get("description") or "").lower()
        title = (candidate.get("title") or "").lower()
        combined = f"{title} {desc}"
        combined_words = set(re.findall(r"\b[a-z]{3,}\b", combined))

        matched = sorted(w for w in all_target_tokens if w in combined_words)
        desc_hits = sum(1 for w in matched if w in desc)
        expanded_hits = sum(1 for term in expanded_terms if term in desc)

        if desc_hits == 0 and expanded_hits == 0:
            return 0.0, []

        high_signal_tokens = {w for w in q_tokens if len(w) >= 5 and w not in BROAD_CONTEXT_WORDS}
        if high_signal_tokens and not (high_signal_tokens & combined_words):
            return 0.0, []

        media_hits = len(combined_words & MEDIA_POSITIVE_TERMS)
        company_hits = len(combined_words & COMPANY_PENALTY_TERMS)
        broad_only_hits = sum(1 for w in matched if w in BROAD_CONTEXT_WORDS)

        # Penalizo emra personash/biografi që nuk kanë sinjale filmi/dokumentari
        looks_like_person_bio = (
            not candidate.get("is_explicit_media_page")
            and media_hits == 0
            and len(title.split()) in (2, 3)
            and bool(re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}$", candidate.get("title") or ""))
        )

        multi_match_bonus = (desc_hits - 1) * 2.0 if desc_hits >= 2 else -1.5
        specificity_bonus = sum(min(len(w) / 10.0, 1.0) for w in matched if w not in BROAD_CONTEXT_WORDS)
        media_bonus = (3.5 if candidate.get("is_explicit_media_page") else 0.0) + min(media_hits * 0.8, 2.4)
        company_penalty = (
            company_hits * 3.0
            if media_hits == 0 and not candidate.get("is_explicit_media_page")
            else company_hits * 1.0
        )
        broad_penalty = broad_only_hits * 1.0
        bio_penalty = 8.0 if looks_like_person_bio else 0.0

        score = (
            (desc_hits * 2.5)
            + (expanded_hits * 1.4)
            + multi_match_bonus
            + specificity_bonus
            + media_bonus
            - company_penalty
            - broad_penalty
            - bio_penalty
        )

        if score <= 0:
            return 0.0, []

        return round(score, 2), matched

    def find_by_description(self, description_query: str, top_k: int = 3) -> dict:
        keywords = self.extract_keywords(description_query, max_terms=5)
        expanded_terms = self._expand_abstract_terms(keywords, description_query)

        candidates = self._search_tubi_candidates(expanded_terms)
        candidates.extend(self._search_open_web_movie_descriptions(expanded_terms))

        seen_titles = set()
        scored = []

        for cand in candidates:
            norm_title = cand["title"].lower()
            if norm_title in seen_titles:
                continue
            score, matched_words = self._score_description_match(description_query, expanded_terms, cand)
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
