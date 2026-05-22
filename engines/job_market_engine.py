"""
Job Market Pulse Engine
=======================
Fetches live job market intelligence from TheirStack API for a given
career path. Results are cached in-memory for 6 hours to conserve
the 200 free API credits/month.

Data returned per career path:
  - total_jobs:    open roles in last 30 days
  - remote_pct:   % of listings that are remote
  - top_skills:   most-demanded tech skills in listings
  - seniority:    dominant seniority level (entry/mid/senior)
  - companies:    sample of 3 hiring companies (name + logo)
  - demand_label: "High" / "Growing" / "Steady" / "Niche"
  - cached_at:    UTC timestamp of when data was fetched
"""

import json
import time
import logging
import requests
import re
from html import unescape
from collections import Counter
from datetime import datetime
from flask import current_app

log = logging.getLogger(__name__)

# ── In-memory cache: {career_slug: {"data": {...}, "ts": epoch}} ──────────────
_CACHE: dict[str, dict] = {}
CACHE_TTL_SECONDS = 6 * 60 * 60   # 6 hours — serve without re-fetching APIs
STALE_REFRESH_SECONDS = 45 * 60   # after 45m, background refresh on next request

THEIRSTACK_BASE = "https://api.theirstack.com/v1"
REMOTIVE_BASE = "https://remotive.com/api/remote-jobs"

# ── Career path title → TheirStack job title search term ─────────────────────
# Our DB career path titles vs what recruiters write in job postings differ,
# so we map them explicitly here.
CAREER_SEARCH_MAP: dict[str, str] = {
    # AI / ML
    "ai engineer":               "AI Engineer",
    "machine learning engineer": "Machine Learning Engineer",
    "data scientist":            "Data Scientist",
    "mlops engineer":            "MLOps Engineer",
    "computer vision engineer":  "Computer Vision Engineer",
    "nlp engineer":              "NLP Engineer",

    # Data
    "data analyst":              "Data Analyst",
    "data engineer":             "Data Engineer",
    "business intelligence":     "Business Intelligence Analyst",
    "bi developer":              "BI Developer",

    # Software
    "software engineer":         "Software Engineer",
    "backend developer":         "Backend Developer",
    "full stack developer":      "Full Stack Developer",
    "frontend developer":        "Frontend Developer",
    "mobile developer":          "Mobile Developer",
    "android developer":         "Android Developer",
    "ios developer":             "iOS Developer",

    # DevOps / Cloud
    "devops engineer":           "DevOps Engineer",
    "cloud engineer":            "Cloud Engineer",
    "site reliability engineer": "Site Reliability Engineer",
    "platform engineer":         "Platform Engineer",

    # Security
    "cybersecurity analyst":     "Cybersecurity Analyst",
    "security engineer":         "Security Engineer",
    "penetration tester":        "Penetration Tester",
    "soc analyst":               "SOC Analyst",

    # Product / Design
    "product manager":           "Product Manager",
    "ui ux designer":            "UX Designer",
    "ux researcher":             "UX Researcher",

    # Blockchain / Web3
    "blockchain developer":      "Blockchain Developer",
    "smart contract developer":  "Solidity Developer",

    # Game / Embedded
    "game developer":            "Game Developer",
    "embedded systems engineer": "Embedded Systems Engineer",

    # Non-tech / Business
    "digital marketer":          "Digital Marketing Specialist",
    "content creator":           "Content Creator",
    "business analyst":          "Business Analyst",
    "project manager":           "Project Manager",
}

# Tech slug → readable label (TheirStack uses lowercase hyphenated slugs)
TECH_SLUG_LABELS: dict[str, str] = {
    "python":            "Python",
    "javascript":        "JavaScript",
    "typescript":        "TypeScript",
    "java":              "Java",
    "golang":            "Go",
    "rust":              "Rust",
    "cpp":               "C++",
    "c-sharp":           "C#",
    "react":             "React",
    "vue":               "Vue",
    "angular":           "Angular",
    "node-js":           "Node.js",
    "django":            "Django",
    "fastapi":           "FastAPI",
    "flask":             "Flask",
    "docker":            "Docker",
    "kubernetes":        "Kubernetes",
    "terraform":         "Terraform",
    "aws":               "AWS",
    "microsoft-azure":   "Azure",
    "google-cloud":      "GCP",
    "postgresql":        "PostgreSQL",
    "mysql":             "MySQL",
    "mongodb":           "MongoDB",
    "redis":             "Redis",
    "power-bi":          "Power BI",
    "tableau":           "Tableau",
    "looker":            "Looker",
    "pandas":            "Pandas",
    "numpy":             "NumPy",
    "tensorflow":        "TensorFlow",
    "pytorch":           "PyTorch",
    "scikit-learn":      "Scikit-Learn",
    "langchain":         "LangChain",
    "openai":            "OpenAI",
    "microsoft-excel":   "Excel",
    "supabase":          "Supabase",
    "graphql":           "GraphQL",
    "linux":             "Linux",
    "powershell":        "PowerShell",
    "active-directory":  "Active Directory",
    "crowdstrike":       "CrowdStrike",
    "jenkins":           "Jenkins",
    "github-actions":    "GitHub Actions",
    "solidity":          "Solidity",
    "unity":             "Unity",
    "unreal-engine":     "Unreal Engine",
}

# Noise slugs to exclude (vendor tools, office apps, irrelevant)
_SKIP_SLUGS = {
    "gmail", "mode", "paypal", "slack", "notion", "zoom",
    "microsoft-office", "google-workspace", "jira", "confluence",
    "salesforce", "hubspot", "stripe", "twilio",
}


def _get_search_term(career_title: str) -> str:
    """Map a DB career path title to a TheirStack job title search term."""
    key = career_title.lower().strip()
    if key in CAREER_SEARCH_MAP:
        return CAREER_SEARCH_MAP[key]
    # Fallback: use the title as-is
    return career_title


def _humanize_seniority(seniority_counts: dict) -> str:
    """Convert seniority counter to a human label."""
    if not seniority_counts:
        return "Mixed"
    top = max(seniority_counts, key=seniority_counts.get)
    labels = {
        "entry_level": "Entry Level",
        "junior":      "Junior",
        "mid_level":   "Mid Level",
        "senior":      "Senior",
        "lead":        "Lead / Staff",
        "manager":     "Manager",
    }
    return labels.get(top, top.replace("_", " ").title())


def _demand_label(total: int) -> str:
    """Convert total job count to a demand label."""
    if total >= 20000: return "Very High"
    if total >= 8000:  return "High"
    if total >= 3000:  return "Growing"
    if total >= 500:   return "Steady"
    return "Niche"


def _demand_color(label: str) -> str:
    return {
        "Very High": "#34d399",
        "High":      "#34d399",
        "Growing":   "#00d4ff",
        "Steady":    "#f59e0b",
        "Niche":     "#94a3b8",
    }.get(label, "#94a3b8")


def _remote_demand_label(total: int) -> str:
    """Demand thresholds for Remotive's remote-only result set."""
    if total >= 150:
        return "High"
    if total >= 50:
        return "Growing"
    if total >= 12:
        return "Steady"
    return "Niche"


def _parse_salary_usd(raw_salary: str | None) -> int | None:
    """Parse simple Remotive salary strings such as '$120k - $180k'."""
    if not raw_salary:
        return None
    cleaned = raw_salary.lower().replace(",", "")
    values: list[int] = []
    for number, suffix in re.findall(r"\$?\s*(\d{2,6})(k)?", cleaned):
        value = int(number)
        if suffix or value < 1000:
            value *= 1000
        if 20000 <= value <= 500000:
            values.append(value)
    return round(sum(values) / len(values)) if values else None


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"<[^>]+>", " ", unescape(value)).lower()


def _infer_seniority_from_title(title: str) -> str:
    lower = title.lower()
    if any(word in lower for word in ("intern", "graduate", "entry")):
        return "Entry Level"
    if any(word in lower for word in ("junior", "jr.")):
        return "Junior"
    if any(word in lower for word in ("principal", "staff", "lead", "head")):
        return "Lead / Staff"
    if any(word in lower for word in ("senior", "sr.")):
        return "Senior"
    return "Mid Level"


def _extract_remotive_skills(job: dict) -> list[str]:
    """Extract known tech labels from Remotive tags and descriptions."""
    text_parts = [
        str(job.get("title") or ""),
        " ".join(str(tag) for tag in (job.get("tags") or [])),
        _strip_html(job.get("description")),
    ]
    haystack = " ".join(text_parts).lower()
    found: list[str] = []
    for slug, label in TECH_SLUG_LABELS.items():
        candidates = {slug.replace("-", " "), label.lower()}
        if label == "C++":
            candidates.add("c++")
        if label == "C#":
            candidates.add("c#")
        if any(re.search(rf"(?<![a-z0-9+#]){re.escape(term)}(?![a-z0-9+#])", haystack) for term in candidates):
            found.append(slug)
    return found


def _fetch_remotive_pulse(career_title: str, search_term: str) -> dict | None:
    """
    Fallback live market signal from Remotive's public remote jobs API.
    This keeps the dashboard useful when TheirStack credits are exhausted.
    """
    try:
        resp = requests.get(
            REMOTIVE_BASE,
            params={"search": search_term, "limit": 50},
            timeout=12,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Remotive API error for '%s': %s", career_title, exc)
        return None

    raw = resp.json()
    jobs = raw.get("jobs", []) or []
    if not jobs:
        return None

    total = int(raw.get("job-count") or raw.get("total-job-count") or len(jobs))
    tech_counter: Counter = Counter()
    seniority_counter: Counter = Counter()
    companies: list[dict] = []
    salary_values: list[int] = []

    for job in jobs[:50]:
        tech_counter.update(_extract_remotive_skills(job))
        seniority_counter[_infer_seniority_from_title(job.get("title", ""))] += 1
        parsed_salary = _parse_salary_usd(job.get("salary"))
        if parsed_salary:
            salary_values.append(parsed_salary)

        company_name = job.get("company_name")
        if company_name and len(companies) < 4:
            if not any(c["name"] == company_name for c in companies):
                companies.append({
                    "name": company_name,
                    "logo": job.get("company_logo_url") or job.get("company_logo") or "",
                    "domain": "",
                })

    top_skills = []
    for slug, count in tech_counter.most_common(8):
        label = TECH_SLUG_LABELS.get(slug, slug.replace("-", " ").title())
        top_skills.append({"slug": slug, "label": label, "count": count})
        if len(top_skills) == 5:
            break

    demand_lbl = _remote_demand_label(total)
    avg_salary = round(sum(salary_values) / len(salary_values)) if salary_values else None

    return {
        "career_title": career_title,
        "search_term": search_term,
        "total_jobs": total,
        "remote_pct": 100,
        "top_skills": top_skills,
        "seniority": _humanize_seniority(dict(seniority_counter)),
        "companies": companies[:3],
        "avg_salary_usd": avg_salary,
        "demand_label": demand_lbl,
        "demand_color": _demand_color(demand_lbl),
        "cached_at_ts": int(time.time()),
        "source": "Remotive",
    }


def _fetch_adzuna_pulse(career_title: str, search_term: str) -> dict | None:
    """
    Fetch job market intelligence from Adzuna API.
    Provides a high-quality global/US count and salary data when TheirStack is down/exhausted.
    """
    app_id = current_app.config.get("ADZUNA_APP_ID", "")
    app_key = current_app.config.get("ADZUNA_API_KEY", "")
    if not app_id or not app_key:
        log.warning("Adzuna API credentials not configured.")
        return None

    # Adzuna endpoint for US jobs (most representative global search volume)
    # Using page 1, 25 results per page
    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": search_term,
        "results_per_page": 25,
        "content-type": "application/json"
    }

    try:
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Adzuna API error for '%s': %s", career_title, exc)
        return None

    raw = resp.json()
    jobs = raw.get("results", []) or []
    total = int(raw.get("count", 0))

    if not total and not jobs:
        return None

    # Aggregate stats
    tech_counter: Counter = Counter()
    seniority_counter: Counter = Counter()
    remote_count = 0
    companies: list[dict] = []
    salary_values: list[float] = []

    for job in jobs:
        # Check description and title for tech skills
        title = job.get("title", "")
        desc = job.get("description", "")
        full_text = f"{title} {desc}".lower()

        # Simple extraction of skills
        for slug, label in TECH_SLUG_LABELS.items():
            candidates = {slug.replace("-", " "), label.lower()}
            if label == "C++":
                candidates.add("c++")
            if label == "C#":
                candidates.add("c#")
            if any(re.search(rf"(?<![a-z0-9+#]){re.escape(term)}(?![a-z0-9+#])", full_text) for term in candidates):
                tech_counter[slug] += 1

        # Seniority
        seniority_counter[_infer_seniority_from_title(title)] += 1

        # Remote: Adzuna often indicates remote in title, description, or category
        if any(word in full_text for word in ("remote", "telecommute", "work from home", "wfh")):
            remote_count += 1

        # Salary
        sal_min = job.get("salary_min")
        sal_max = job.get("salary_max")
        if sal_min and sal_max:
            salary_values.append((float(sal_min) + float(sal_max)) / 2)
        elif sal_min:
            salary_values.append(float(sal_min))
        elif sal_max:
            salary_values.append(float(sal_max))

        # Companies
        company = job.get("company", {})
        company_name = company.get("display_name")
        if company_name and len(companies) < 4:
            if not any(c["name"] == company_name for c in companies):
                companies.append({
                    "name": company_name,
                    "logo": "",  # Adzuna doesn't provide logo URLs directly in results
                    "domain": "",
                })

    top_skills = []
    for slug, count in tech_counter.most_common(8):
        label = TECH_SLUG_LABELS.get(slug, slug.replace("-", " ").title())
        top_skills.append({"slug": slug, "label": label, "count": count})
        if len(top_skills) == 5:
            break

    remote_pct = round(remote_count / len(jobs) * 100) if jobs else 0
    avg_salary = round(sum(salary_values) / len(salary_values)) if salary_values else None
    seniority = _humanize_seniority(dict(seniority_counter))
    
    # We can use the standard TheirStack overall demand label threshold since Adzuna is global
    demand_lbl = _demand_label(total)

    return {
        "career_title": career_title,
        "search_term": search_term,
        "total_jobs": total,
        "remote_pct": remote_pct,
        "top_skills": top_skills,
        "seniority": seniority,
        "companies": companies[:3],
        "avg_salary_usd": avg_salary,
        "demand_label": demand_lbl,
        "demand_color": _demand_color(demand_lbl),
        "cached_at_ts": int(time.time()),
        "source": "Adzuna",
    }


def _get_fallback_pulse(career_title: str, search_term: str) -> dict | None:
    """Try Adzuna first as the high-volume fallback, then Remotive as final resort."""
    adzuna_id = current_app.config.get("ADZUNA_APP_ID", "")
    adzuna_key = current_app.config.get("ADZUNA_API_KEY", "")
    if adzuna_id and adzuna_key:
        log.info("Trying Adzuna fallback for '%s'", career_title)
        pulse = _fetch_adzuna_pulse(career_title, search_term)
        if pulse:
            return pulse

    log.info("Trying Remotive fallback for '%s'", career_title)
    return _fetch_remotive_pulse(career_title, search_term)


def fetch_job_pulse(career_title: str) -> dict | None:
    """
    Fetch job market intelligence for a career path title.
    Returns cached data if fresh (< 6h), otherwise fetches from TheirStack.

    Returns None on API failure (UI should show a fallback state).
    """
    cache_key = career_title.lower().strip()

    # ── Serve from cache if fresh ─────────────────────────────────────────────
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL_SECONDS:
        log.debug("Job pulse cache HIT for: %s", career_title)
        return cached["data"]

    # ── Fetch from TheirStack ─────────────────────────────────────────────────
    api_key = current_app.config.get("THEIRSTACK_API_KEY", "")
    search_term = _get_search_term(career_title)
    if not api_key:
        fallback = _get_fallback_pulse(career_title, search_term)
        if fallback:
            _CACHE[cache_key] = {"data": fallback, "ts": time.time()}
            _persist_db_cache(cache_key, career_title, fallback)
            return fallback
        log.warning("Neither TheirStack nor fallback credentials set — skipping job pulse")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "job_title_or":         [search_term],
        "posted_at_max_age_days": 30,
        "limit":                 25,   # enough for stats; low credit cost
        "page":                  0,
        "order_by":              [{"field": "date_posted", "desc": True}],
        "include_total_results": True,
        "blur_company_data":     True,
    }

    try:
        resp = requests.post(
            f"{THEIRSTACK_BASE}/jobs/search",
            headers=headers,
            json=payload,
            timeout=12,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("TheirStack API error for '%s': %s", career_title, exc)
        fallback = _get_fallback_pulse(career_title, search_term)
        if fallback:
            _CACHE[cache_key] = {"data": fallback, "ts": time.time()}
            _persist_db_cache(cache_key, career_title, fallback)
        return fallback

    raw = resp.json()
    jobs = raw.get("data", [])

    # ── Total count: TheirStack stores it in metadata or top-level ────────────
    total = (
        raw.get("total")
        or raw.get("metadata", {}).get("total_results")
        or raw.get("total_results")
        or len(jobs)
    )

    if not jobs:
        fallback = _get_fallback_pulse(career_title, search_term)
        if fallback:
            _CACHE[cache_key] = {"data": fallback, "ts": time.time()}
            _persist_db_cache(cache_key, career_title, fallback)
        return fallback

    # ── Aggregate stats ───────────────────────────────────────────────────────
    tech_counter: Counter = Counter()
    seniority_counter: Counter = Counter()
    remote_count = 0
    companies: list[dict] = []
    salary_values: list[float] = []

    for job in jobs:
        # Technology slugs (filtered)
        for slug in job.get("technology_slugs", []):
            if slug not in _SKIP_SLUGS:
                tech_counter[slug] += 1

        # Seniority
        if job.get("seniority"):
            seniority_counter[job["seniority"]] += 1

        # Remote
        if job.get("remote"):
            remote_count += 1

        # Salary
        sal = job.get("avg_annual_salary_usd") or job.get("min_annual_salary_usd")
        if sal:
            salary_values.append(float(sal))

        # Companies (collect up to 4 unique, with logo)
        co = None if job.get("has_blurred_data") else job.get("company_object")
        if co and co.get("name") and len(companies) < 4:
            if not any(c["name"] == co["name"] for c in companies):
                companies.append({
                    "name":   co["name"],
                    "logo":   co.get("logo", ""),
                    "domain": co.get("domain", ""),
                })

    # Top 5 skills (skip empty labels)
    top_skills = []
    for slug, count in tech_counter.most_common(8):
        label = TECH_SLUG_LABELS.get(slug, slug.replace("-", " ").title())
        top_skills.append({"slug": slug, "label": label, "count": count})
        if len(top_skills) == 5:
            break

    remote_pct  = round(remote_count / len(jobs) * 100) if jobs else 0
    avg_salary  = round(sum(salary_values) / len(salary_values)) if salary_values else None
    seniority   = _humanize_seniority(dict(seniority_counter))
    demand_lbl  = _demand_label(total)

    result = {
        "career_title":  career_title,
        "search_term":   search_term,
        "total_jobs":    total,
        "remote_pct":    remote_pct,
        "top_skills":    top_skills,
        "seniority":     seniority,
        "companies":     companies[:3],
        "avg_salary_usd": avg_salary,
        "demand_label":  demand_lbl,
        "demand_color":  _demand_color(demand_lbl),
        "cached_at_ts":  int(time.time()),
        "source":        "TheirStack",
    }

    # ── Store in cache ────────────────────────────────────────────────────────
    _CACHE[cache_key] = {"data": result, "ts": time.time()}
    _persist_db_cache(cache_key, career_title, result)
    log.info("Job pulse cached for '%s': %d jobs, %d skills", career_title, total, len(top_skills))
    return result


def _persist_db_cache(cache_key: str, career_title: str, data: dict) -> None:
    """Write snapshot to SQLite so data survives process restarts."""
    try:
        from database.models import db, JobMarketPulseCache

        payload = json.dumps(data)
        source = data.get("source") or "unknown"
        row = JobMarketPulseCache.query.filter_by(cache_key=cache_key).first()
        if row:
            row.career_title = career_title
            row.payload = payload
            row.source = source
            row.fetched_at = datetime.utcnow()
        else:
            db.session.add(JobMarketPulseCache(
                cache_key=cache_key,
                career_title=career_title,
                payload=payload,
                source=source,
            ))
        db.session.commit()
    except Exception as exc:
        log.warning("Job pulse DB cache write failed for '%s': %s", career_title, exc)
        try:
            from database.models import db
            db.session.rollback()
        except Exception:
            pass


def _load_db_cache(cache_key: str) -> tuple[dict | None, float]:
    """Return (payload dict, age_seconds) or (None, inf)."""
    try:
        from database.models import JobMarketPulseCache

        row = JobMarketPulseCache.query.filter_by(cache_key=cache_key).first()
        if not row:
            return None, float("inf")
        data = row.get_data()
        if not data:
            return None, float("inf")
        if row.fetched_at:
            data.setdefault("cached_at_ts", int(row.fetched_at.timestamp()))
        age = time.time() - (row.fetched_at.timestamp() if row.fetched_at else time.time())
        return data, age
    except Exception as exc:
        log.warning("Job pulse DB cache read failed: %s", exc)
        return None, float("inf")


def _synthetic_pulse(career_title: str) -> dict:
    """Last-resort card content from career-path skills when all APIs are down."""
    search_term = _get_search_term(career_title)
    top_skills: list[dict] = []
    try:
        from database.models import CareerPath

        key = career_title.lower().strip()
        career = None
        for cp in CareerPath.query.all():
            if cp.title.lower().strip() == key:
                career = cp
                break
        if career:
            required = career.get_required_skills() or {}
            for sk in list(required.keys())[:6]:
                label = TECH_SLUG_LABELS.get(sk, sk.replace("_", " ").title())
                top_skills.append({"slug": sk, "label": label, "count": 1})
    except Exception:
        pass

    if not top_skills:
        top_skills = [
            {"slug": "python", "label": "Python", "count": 1},
            {"slug": "communication", "label": "Communication", "count": 1},
        ]

    return {
        "career_title": career_title,
        "search_term": search_term,
        "total_jobs": 0,
        "remote_pct": 0,
        "top_skills": top_skills[:5],
        "seniority": "Mid Level",
        "companies": [],
        "avg_salary_usd": None,
        "demand_label": "Updating",
        "demand_color": "#94a3b8",
        "cached_at_ts": int(time.time()),
        "source": "Estimated",
        "is_live": False,
        "is_stale": True,
        "refresh_pending": True,
    }


def _annotate_pulse(data: dict, *, age_seconds: float, tried_refresh: bool) -> dict:
    out = dict(data)
    source = (out.get("source") or "").strip()
    out["is_live"] = bool(source) and source.lower() not in ("estimated", "unknown")
    out["is_stale"] = age_seconds > CACHE_TTL_SECONDS
    out["refresh_pending"] = tried_refresh and not out["is_live"] and out.get("total_jobs", 0) == 0
    if out.get("cached_at_ts"):
        out["cached_age_minutes"] = max(0, int(age_seconds // 60))
    return out


def get_job_pulse(career_title: str, force_refresh: bool = False) -> dict:
    """
    Resilient job market payload for the dashboard.

    Order: memory cache → live API (if stale/forced) → DB cache → synthetic estimate.
    Always returns a dict suitable for rendering.
    """
    if not career_title or not str(career_title).strip():
        return _synthetic_pulse("General")

    cache_key = career_title.lower().strip()
    now = time.time()

    if not force_refresh:
        mem = _CACHE.get(cache_key)
        if mem and (now - mem["ts"]) < CACHE_TTL_SECONDS:
            return _annotate_pulse(mem["data"], age_seconds=now - mem["ts"], tried_refresh=False)

    db_data, db_age = _load_db_cache(cache_key)
    should_fetch = force_refresh or db_data is None or db_age >= STALE_REFRESH_SECONDS

    if should_fetch:
        live = fetch_job_pulse(career_title)
        if live:
            _CACHE[cache_key] = {"data": live, "ts": time.time()}
            return _annotate_pulse(live, age_seconds=0, tried_refresh=True)

    if db_data:
        _CACHE[cache_key] = {"data": db_data, "ts": time.time() - db_age}
        return _annotate_pulse(db_data, age_seconds=db_age, tried_refresh=should_fetch)

    synthetic = _synthetic_pulse(career_title)
    _persist_db_cache(cache_key, career_title, synthetic)
    _CACHE[cache_key] = {"data": synthetic, "ts": time.time()}
    return _annotate_pulse(synthetic, age_seconds=0, tried_refresh=should_fetch)
