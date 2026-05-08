"""
News Blueprint — Career-aware Tech Intelligence Feed.

Uses GNews API (free tier, 100 req/day) for articles with images.
Falls back to Hacker News API (no key needed) if GNews is unavailable.
Results are cached in-memory for 30 minutes to protect rate limits.
"""

import json
import time
import urllib.request
import urllib.parse
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

news_bp = Blueprint("news", __name__, url_prefix="/news")

# ── In-memory cache: {cache_key: {"data": [...], "ts": timestamp}} ──
_cache = {}
CACHE_TTL = 1800  # 30 minutes


# ── Career → GNews search query mapping ─────────────────────────────
CAREER_QUERY_MAP = {
    "data_analyst":             "data analytics OR business intelligence OR SQL",
    "data_scientist":           "data science OR machine learning OR AI research",
    "data_engineer":            "data engineering OR Apache Spark OR data pipeline",
    "software_engineer":        "software engineering OR programming OR developer",
    "web_developer":            "web development OR JavaScript OR React OR Next.js",
    "frontend_developer":       "frontend development OR CSS OR React OR UI engineering",
    "backend_developer":        "backend development OR API OR microservices OR Python",
    "mobile_developer":         "mobile app development OR Flutter OR React Native OR iOS Android",
    "ml_engineer":              "machine learning engineer OR MLOps OR deep learning",
    "ai_engineer":              "AI engineering OR large language model OR LLM OR generative AI",
    "ai_automation_specialist": "AI automation OR workflow automation OR AI agents",
    "ux_designer":              "UX design OR UI design OR Figma OR user research",
    "product_manager":          "product management OR product strategy OR roadmap",
    "devops_engineer":          "DevOps OR CI/CD OR Kubernetes OR Docker OR infrastructure",
    "cloud_architect":          "cloud computing OR AWS OR Azure OR GCP OR cloud architecture",
    "it_support_sysadmin":      "IT support OR systems administration OR Linux sysadmin",
    "cybersecurity_analyst":    "cybersecurity OR information security OR hacking OR infosec",
    "qa_engineer":              "software testing OR QA engineering OR test automation",
    "business_analyst":         "business analysis OR requirements engineering OR enterprise software",
    "technical_writer":         "technical writing OR developer documentation OR API docs",
    "digital_marketer":         "digital marketing OR SEO OR content marketing OR social media",
    "blockchain_developer":     "blockchain OR Web3 OR smart contracts OR cryptocurrency",
}

# ── Tech category → GNews query ─────────────────────────────────────
CATEGORY_QUERIES = {
    "ai":         "artificial intelligence OR machine learning OR generative AI",
    "software":   "software development OR programming OR open source",
    "cloud":      "cloud computing OR AWS OR Azure OR serverless",
    "security":   "cybersecurity OR data breach OR hacking OR infosec",
    "hardware":   "hardware OR chip OR semiconductor OR GPU OR processor",
    "startup":    "startup OR tech company OR venture capital OR funding",
    "web3":       "blockchain OR Web3 OR cryptocurrency OR NFT",
    "design":     "UX design OR product design OR Figma OR user experience",
    "data":       "data science OR big data OR analytics OR database",
    "career":     "tech career OR job market OR software engineer salary OR hiring",
}


def _fetch_url(url):
    """Simple HTTP GET with a 8s timeout, returns parsed JSON or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SkillSync/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        current_app.logger.warning(f"[News] HTTP fetch failed: {e}")
        return None


def _from_cache(key):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None


def _to_cache(key, data):
    _cache[key] = {"data": data, "ts": time.time()}


# ────────────────────────────────────────────────────────────────────
# GNews fetcher
# ────────────────────────────────────────────────────────────────────
def fetch_gnews(query, max_results=10, lang="en"):
    """Fetch articles from GNews API. Returns list of article dicts."""
    api_key = current_app.config.get("GNEWS_API_KEY", "")
    if not api_key:
        return []

    cache_key = f"gnews:{query}:{max_results}"
    cached = _from_cache(cache_key)
    if cached is not None:
        return cached

    encoded_q = urllib.parse.quote(query)
    url = (
        f"https://gnews.io/api/v4/search"
        f"?q={encoded_q}&lang={lang}&max={max_results}"
        f"&sortby=publishedAt&token={api_key}"
    )
    data = _fetch_url(url)
    if not data or "articles" not in data:
        return []

    articles = []
    for a in data["articles"]:
        articles.append({
            "title":       a.get("title", ""),
            "description": a.get("description", ""),
            "url":         a.get("url", "#"),
            "image":       a.get("image", ""),
            "source":      a.get("source", {}).get("name", "Unknown"),
            "published_at": a.get("publishedAt", "")[:10],
            "provider":    "gnews",
        })

    _to_cache(cache_key, articles)
    return articles


# ────────────────────────────────────────────────────────────────────
# Hacker News fetcher (no API key — always available as fallback)
# ────────────────────────────────────────────────────────────────────
def fetch_hackernews(limit=20):
    """Fetch top HN stories. No images but always free & reliable."""
    cache_key = f"hn:top:{limit}"
    cached = _from_cache(cache_key)
    if cached is not None:
        return cached

    ids_data = _fetch_url("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not ids_data:
        return []

    articles = []
    for story_id in ids_data[:limit]:
        story = _fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        if not story or story.get("type") != "story":
            continue
        articles.append({
            "title":        story.get("title", ""),
            "description":  f"💬 {story.get('score', 0)} points · {story.get('descendants', 0)} comments on Hacker News",
            "url":          story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            "image":        "",
            "source":       "Hacker News",
            "published_at": "",
            "provider":     "hackernews",
        })
        if len(articles) >= limit:
            break

    _to_cache(cache_key, articles)
    return articles


# ────────────────────────────────────────────────────────────────────
# Smart fetch — tries GNews first, falls back to HN
# ────────────────────────────────────────────────────────────────────
def smart_fetch(query, limit=12):
    articles = fetch_gnews(query, max_results=limit)
    if not articles:
        # No GNews key or quota exceeded — fall back to HN
        articles = fetch_hackernews(limit=limit)
    return articles


def _get_career_query():
    """Derive a GNews search query from the user's current career target."""
    if not current_user.is_authenticated:
        return "technology"

    # Nontech path
    if current_user.nontech_profile and not current_user.profile:
        target = (current_user.nontech_profile.target_career or "").lower()
        for slug, q in CAREER_QUERY_MAP.items():
            if any(word in target for word in slug.split("_")):
                return q
        return "technology career"

    # Tech path — look at the latest approved roadmap
    roadmaps = getattr(current_user, "roadmaps", [])
    for rm in reversed(roadmaps):
        if rm.status == "approved" and rm.career_path:
            slug = rm.career_path.slug
            if slug in CAREER_QUERY_MAP:
                return CAREER_QUERY_MAP[slug]

    return "software engineering technology"


# ────────────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────────────
@news_bp.route("/")
@login_required
def feed():
    """Main news feed page."""
    career_query = _get_career_query()

    # "For You" section — career-targeted
    for_you = smart_fetch(career_query, limit=6)

    # Trending tech — broad
    trending = smart_fetch("technology innovation AI", limit=12)

    # Active category filter (from query param)
    active_category = request.args.get("category", "")
    category_articles = []
    if active_category and active_category in CATEGORY_QUERIES:
        category_articles = smart_fetch(CATEGORY_QUERIES[active_category], limit=12)

    # Search results
    search_query = request.args.get("q", "").strip()
    search_results = []
    if search_query:
        search_results = smart_fetch(search_query, limit=16)

    # Resolve career display name
    career_label = "Tech"
    if current_user.nontech_profile and not current_user.profile:
        career_label = current_user.nontech_profile.target_career or "Tech"
    else:
        roadmaps = getattr(current_user, "roadmaps", [])
        for rm in reversed(roadmaps):
            if rm.status == "approved" and rm.career_path:
                career_label = rm.career_path.title
                break

    has_gnews = bool(current_app.config.get("GNEWS_API_KEY", ""))

    return render_template(
        "news/feed.html",
        for_you=for_you,
        trending=trending,
        category_articles=category_articles,
        search_results=search_results,
        categories=CATEGORY_QUERIES,
        active_category=active_category,
        search_query=search_query,
        career_label=career_label,
        has_gnews=has_gnews,
    )


@news_bp.route("/api/fetch")
@login_required
def api_fetch():
    """AJAX endpoint for live search / category filtering."""
    q = request.args.get("q", "technology").strip()
    limit = min(int(request.args.get("limit", 12)), 30)
    articles = smart_fetch(q, limit=limit)
    return jsonify({"articles": articles, "count": len(articles)})
