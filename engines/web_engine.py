import re
import requests
import xml.etree.ElementTree as ET
import logging
from bs4 import BeautifulSoup

from engines.semantic_movie_engine import SemanticMovieEngine

logger = logging.getLogger("FalconAI.WebEngine")


class WebEngine:
    def __init__(self):
        self.timeout = 5

        self.semantic_movie_engine = SemanticMovieEngine()

        self.feeds = {
            "world": [
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
                "http://rss.cnn.com/rss/edition_world.rss",
                "https://www.aljazeera.com/xml/rss/all.rss",
                "https://www.theguardian.com/world/rss"
            ],
            "europe": [
                "https://www.euronews.com/rss?format=mrss",
                "https://www.france24.com/en/rss",
                "https://www.dw.com/en/top-stories/s-9097/rss",
                "https://www.ansa.it/sito/ansait_rss.xml",
                "https://elpais.com/rss/elpais/inenglish.xml"
            ],
            "asia": [
                "https://www.japantimes.co.jp/feed/",
                "https://www.channelnewsasia.com/api/v1/rss-outlets/cna-en",
                "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
                "https://www.scmp.com/rss/2/feed",
                "https://www.koreatimes.co.kr/www/rss/rss.xml"
            ],
            "americas": [
                "https://www.cbc.ca/cnews/rss/topstories.rss",
                "https://rss.usatoday.com/newsheadlines",
                "https://www.buenosairestimes.com/rss",
                "https://braziljournal.com/feed/",
                "https://www.eluniversal.com.mx/rss.xml"
            ],
            "africa": [
                "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
                "https://www.news24.com/news24/rss",
                "https://www.theeastafrican.co.ke/tea/rss",
                "https://apanews.net/en/rss"
            ],
            "oceania": [
                "https://www.abc.net.au/news/feed/51120/rss.xml",
                "https://www.rnz.co.nz/rss/national.rss",
                "https://www.smh.com.au/rss/feed.xml"
            ],
            "politics": [
                "https://feeds.bbci.co.uk/news/politics/rss.xml",
                "https://rss.politico.com/politics-news.xml",
                "https://www.theguardian.com/politics/rss",
                "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml"
            ],
            "business": [
                "https://feeds.bbci.co.uk/news/business/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
                "https://www.cnbc.com/id/10001147/device/rss/rss.html",
                "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"
            ],
            "technology": [
                "https://feeds.bbci.co.uk/news/technology/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
                "https://feeds.feedburner.com/TechCrunch",
                "https://www.theverge.com/rss/index.xml",
                "https://www.wired.com/feed/rss"
            ],
            "war": [
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
                "https://www.aljazeera.com/xml/rss/all.rss",
                "https://www.theguardian.com/world/rss"
            ],
            "balkan": [
                "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
                "https://www.trtworld.com/rss",
                "https://exit.al/feed/",
                "https://www.koha.net/rss",
                "https://top-channel.tv/feed/",
                "https://www.balkaninsight.com/feed/"
            ],
            "sports": [
                "https://feeds.bbci.co.uk/sport/rss.xml",
                "https://www.skysports.com/rss/12040",
                "https://www.theguardian.com/sport/rss"
            ],
            "health": [
                "https://feeds.bbci.co.uk/news/health/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
                "https://www.theguardian.com/society/health/rss"
            ],
            "general": [
                "https://feeds.bbci.co.uk/news/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
                "http://rss.cnn.com/rss/edition.rss",
                "https://www.theguardian.com/international/rss"
            ]
        }

        self.intent_category = {
            "watch_news": "world",
            "watch_war": "war",
            "watch_balkan_news": "balkan",
            "tech_news": "technology",
            "sports_news": "sports",
            "business_news": "business",
            "person_search": "world",
            "weather_query": "general",
            "general_search": "general"
        }

    def process(self, text: str, intent: str = None, category: str = None):
        try:
            if intent == "watch_movie" or any(
                word in text.lower() for word in ["play movie", "shiko filmin", "search movie"]
            ):
                return self.handle_movie_intent(text)

            return self.run_news_engine(text, intent, category)

        except Exception as e:
            logger.error(f"[WEB ERROR] {str(e)}")
            return self.error_response()

    def search(self, text: str, intent: str = None, category: str = None):
        return self.process(text, intent, category)

    def handle_movie_intent(self, query):
        try:
            result = self.semantic_movie_engine.search(query, top_k=5)
            results = result.get("results", [])

            if not results:
                logger.warning(f"[VOD] SemanticMovieEngine found nothing for '{query}'")
                return self.fallback_movie_response(query)

            top_match = results[0]
            alternatives = results[1:]

            return {
                "type": "web_movie",
                "data": {
                    "query": query,
                    "title": top_match["title"],
                    "platform": top_match["platform"],
                    "stream_url": top_match["url"],
                    "auto_play": True,
                    "alternatives": alternatives,
                    "falcon_ai": f"Opening {top_match['title']} on {top_match['platform']}."
                }
            }
        except Exception as e:
            logger.error(f"[VOD ERROR] SemanticMovieEngine failed: {e}")
            return self.fallback_movie_response(query)

    def fallback_movie_response(self, query):
        movie_name = re.sub(
            r'\b(play|watch|shiko|movie|film|search|find|me gjej)\b',
            '', query, flags=re.I
        ).strip()
        search_url = f"https://tubitv.com/search/{movie_name.replace(' ', '%20')}"
        return {
            "type": "web_movie",
            "data": {
                "query": movie_name,
                "platform": "tubi",
                "stream_url": search_url,
                "auto_play": False,
                "falcon_ai": f"Search for '{movie_name}' on Tubi."
            }
        }

    def run_news_engine(self, query, intent=None, category=None):
        if category is None:
            if intent and intent in self.intent_category:
                category = self.intent_category[intent]
            else:
                q_lower = query.lower()
                if any(w in q_lower for w in ["war", "conflict", "middle east", "gaza", "ukraine", "israel", "fight"]):
                    category = "war"
                elif any(w in q_lower for w in ["europe", "germany", "france", "uk", "italy", "spain", "eu"]):
                    category = "europe"
                elif any(w in q_lower for w in ["asia", "china", "japan", "india", "korea", "singapore"]):
                    category = "asia"
                elif any(w in q_lower for w in ["america", "usa", "canada", "brazil", "mexico", "argentina"]):
                    category = "americas"
                elif any(w in q_lower for w in ["africa", "kenya", "south africa"]):
                    category = "africa"
                elif any(w in q_lower for w in ["australia", "zealand", "oceania"]):
                    category = "oceania"
                elif any(w in q_lower for w in ["balkan", "kosova", "albania", "prishtine", "tirane", "serbia"]):
                    category = "balkan"
                elif any(w in q_lower for w in ["tech", "ai", "software", "apple", "google", "phone", "code"]):
                    category = "technology"
                elif any(w in q_lower for w in ["sport", "football", "match", "cup", "score", "game"]):
                    category = "sports"
                elif any(w in q_lower for w in ["business", "stock", "market", "economy", "money", "crypto"]):
                    category = "business"
                elif any(w in q_lower for w in ["politics", "government", "election", "president", "parliament"]):
                    category = "politics"
                else:
                    category = "world"

        logger.info(f"[WEB NEWS] Category resolved: {category} for query: '{query}'")

        articles = self.fetch_articles(category)
        keywords = self.extract_keywords(query)
        filtered = self.filter_articles(articles, keywords)

        # FLEKSIBILITET: Nëse filtrimi del bosh, mos kthe gabim, por merr artikujt e parë direkt nga RSS
        if not filtered and articles:
            logger.info("[WEB NEWS] Filter returned nothing, using latest raw articles as fallback.")
            filtered = articles[:3]

        if not filtered and category != "general":
            logger.info("[WEB NEWS] Falling back to 'general' or 'world' feeds.")
            fallback_articles = self.fetch_articles("general") or self.fetch_articles("world")
            if fallback_articles:
                filtered = fallback_articles[:3]

        if not filtered:
            return self.fallback_response(query)

        return self.format_response(filtered[:3], query)

    def fetch_articles(self, category):
        articles = []
        feeds = self.feeds.get(category, self.feeds["world"])

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }

        for url in feeds:
            try:
                response = requests.get(url, timeout=7, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"[RSS HTTP {response.status_code}] {url}")
                    continue

                root = ET.fromstring(response.content)

                for item in root.findall(".//item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    desc = item.findtext("description", "")

                    if title and link:
                        articles.append({
                            "title": title.strip(),
                            "link": link.strip(),
                            "description": desc.strip()
                        })
            except Exception as e:
                logger.warning(f"[RSS FAIL] {url} -> {str(e)}")
                continue

        if not articles:
            logger.warning("[WEB NEWS] All RSS feeds failed or timed out. Using emergency fallback articles.")
            articles = [
                {
                    "title": "Global Markets and Tech Updates: Latest Developments",
                    "link": "https://www.bbc.com/news",
                    "description": "Explore the latest updates across world news, technology, and international relations."
                },
                {
                    "title": "International Relations and Security Briefing",
                    "link": "https://www.reuters.com",
                    "description": "Continuous coverage of diplomatic talks, global events, and regional updates."
                }
            ]

        return articles

    def fetch_full_article(self, url):
        try:
            response = requests.get(url, timeout=8, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            })

            if response.status_code != 200:
                return ""

            soup = BeautifulSoup(response.content, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "figure", "figcaption", "iframe", "form"]):
                tag.decompose()

            article_body = (
                soup.find("article") or
                soup.find("div", class_=re.compile(r"article|content|story|body|post", re.I)) or
                soup.find("main")
            )

            target = article_body if article_body else soup
            paragraphs = target.find_all("p")
            texts = [
                p.get_text().strip()
                for p in paragraphs
                if len(p.get_text().strip()) > 40
            ]

            full_text = " ".join(texts)

            if len(full_text) > 1500:
                full_text = full_text[:1500].rsplit(' ', 1)[0] + '...'

            return full_text.strip()

        except Exception as e:
            logger.warning(f"[ARTICLE FAIL] {url} -> {str(e)}")
            return ""

    def extract_keywords(self, text):
        stopwords = {
            "what", "happened", "in", "the", "is", "right", "now",
            "tell", "me", "about", "latest", "news", "from", "can",
            "you", "show", "give", "get", "find", "please", "today",
            "happening", "going", "on", "any", "update", "updates"
        }
        return [w for w in text.lower().split() if w not in stopwords and len(w) > 2]

    def filter_articles(self, articles, keywords):
        if not keywords:
            return articles[:3]

        scored = []
        for article in articles:
            text = (article["title"] + " " + article.get("description", "")).lower()
            score = sum(1 for kw in keywords if kw in text)
            # Pranojmë çdo artikull duke i dhënë prioritet atyre që kanë score më të lartë,
            # kështu që nuk do të kthejmë kurrë listë bosh nëse ka artikuj në RSS.
            scored.append((score, article))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [a[1] for a in scored]

    def clean_description(self, desc):
        if not desc:
            return ""
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = re.sub(r'&[a-zA-Z]+;', ' ', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()
        if len(desc) > 300:
            desc = desc[:300].rsplit(' ', 1)[0] + '...'
        return desc

    def format_response(self, articles, query):
        response_text = f"Here's what's happening related to '{query}':\n\n"
        voice_parts = [f"Here's what's happening related to {query}."]

        for i, art in enumerate(articles, 1):
            title = art['title'].strip()
            full_text = self.fetch_full_article(art['link'])
            desc = full_text if full_text else self.clean_description(art.get('description', ''))

            response_text += f"{i}. {title}\n"
            if desc:
                response_text += f"   {desc}\n"
            response_text += "\n"

            voice_parts.append(f"Article {i}. {title}. {desc}")

        return {
            "type": "web",
            "data": {
                "query": query,
                "articles": articles,
                "text": response_text,
                "voice_text": " ".join(voice_parts)
            }
        }

    def fallback_response(self, query):
        fallback_arts = [
            {
                "title": f"Latest updates regarding {query}",
                "link": "https://www.google.com/search?q=" + query.replace(" ", "+"),
                "description": f"Here is an overview of recent news and reports related to {query}."
            }
        ]
        return {
            "type": "web",
            "data": {
                "query": query,
                "articles": fallback_arts,
                "text": f"Here are the latest updates related to '{query}':\n\n1. Latest updates regarding {query}\n   Here is an overview of recent reports.",
                "voice_text": f"Here are the latest updates related to {query}."
            }
        }

    def error_response(self):
        return {
            "type": "web",
            "data": {
                "text": "Something went wrong while fetching news."
            }
        }
