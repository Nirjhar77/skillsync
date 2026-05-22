"""
Transferability Engine
======================
Computes "Career Transferability" — the % of each alternative career path's
required skills that the user has *proven* through completed roadmap milestones.

This is fundamentally different from CareerScore:
  - CareerScore  →  static, based on day-1 self-assessment
  - Transferability → dynamic, based on actual completed milestones

How it works:
  1. Each completed milestone title is scanned for skill keywords (fuzzy match).
  2. Matched keywords resolve to canonical skill keys (same keys used in
     CareerPath.required_skills JSON).
  3. For each alternative career path, we compute:
         transferability % = proven_required_skills / total_required_skills × 100
  4. Only careers above TRANSFERABILITY_THRESHOLD (30%) are returned.
  5. Results are sorted descending, capped at TOP_N careers.
"""

import re

# ── Configuration ──────────────────────────────────────────────────────────────
TRANSFERABILITY_THRESHOLD = 30   # % — only show careers above this
TOP_N_RESULTS             = 4    # max cards to display

# ── Skill Keyword → Canonical Skill Key(s) Mapping ────────────────────────────
# Keys: lowercase substrings that might appear in AI-generated milestone titles
# Values: list of canonical skill keys from CareerPath.required_skills
#
# Coverage: all 47 canonical keys found across all career paths in the DB:
#   algorithms, api_design, blockchain, business_analysis, c_plus_plus,
#   cloud_computing, communication, containerization, content_creation,
#   copywriting, critical_thinking, cryptography, data_structures,
#   data_visualization, databases, deep_learning, digital_marketing,
#   english_language_fluency, excel, game_development, git, html_css,
#   incident_response, javascript, linear_algebra, linux, machine_learning,
#   mlops, monitoring, networking, oop, project_management, prototyping,
#   python, react_or_frontend, research_methodology, security_fundamentals,
#   seo, smart_contracts, social_media_management, sql, statistics,
#   system_design, technical_writing, testing, ui_design, user_research,
#   visual_design
# ──────────────────────────────────────────────────────────────────────────────
SKILL_KEYWORD_MAP: dict[str, list[str]] = {
    # ── Python ──────────────────────────────────────────────────────────────
    "python":               ["python"],
    "flask":                ["python", "api_design"],
    "django":               ["python", "api_design", "databases"],
    "fastapi":              ["python", "api_design"],
    "pandas":               ["python", "data_visualization"],
    "numpy":                ["python", "linear_algebra"],
    "matplotlib":           ["python", "data_visualization"],
    "seaborn":              ["python", "data_visualization"],

    # ── Algorithms & Data Structures ────────────────────────────────────────
    "algorithm":            ["algorithms"],
    "algorithms":           ["algorithms"],
    "data structure":       ["data_structures"],
    "data structures":      ["data_structures"],
    "dsa":                  ["data_structures", "algorithms"],
    "sorting":              ["algorithms"],
    "searching":            ["algorithms"],
    "graph":                ["algorithms", "data_structures"],
    "tree":                 ["data_structures"],
    "linked list":          ["data_structures"],
    "dynamic programming":  ["algorithms"],
    "recursion":            ["algorithms"],
    "big o":                ["algorithms"],
    "complexity":           ["algorithms"],
    "greedy":               ["algorithms"],
    "binary search":        ["algorithms"],
    "hash":                 ["data_structures"],
    "queue":                ["data_structures"],
    "stack":                ["data_structures"],
    "heap":                 ["data_structures"],

    # ── System Design ────────────────────────────────────────────────────────
    "system design":        ["system_design"],
    "scalability":          ["system_design"],
    "load balancing":       ["system_design", "networking"],
    "microservice":         ["system_design", "api_design"],
    "distributed":          ["system_design"],
    "caching":              ["system_design", "databases"],

    # ── OOP ─────────────────────────────────────────────────────────────────
    "oop":                  ["oop"],
    "object oriented":      ["oop"],
    "class":                ["oop"],
    "inheritance":          ["oop"],
    "polymorphism":         ["oop"],
    "encapsulation":        ["oop"],
    "design pattern":       ["oop", "system_design"],
    "solid principle":      ["oop"],

    # ── Machine Learning ─────────────────────────────────────────────────────
    "machine learning":     ["machine_learning"],
    "ml":                   ["machine_learning"],
    "supervised":           ["machine_learning"],
    "unsupervised":         ["machine_learning"],
    "regression":           ["machine_learning", "statistics"],
    "classification":       ["machine_learning"],
    "clustering":           ["machine_learning"],
    "scikit":               ["machine_learning", "python"],
    "sklearn":              ["machine_learning", "python"],
    "random forest":        ["machine_learning"],
    "decision tree":        ["machine_learning"],
    "xgboost":              ["machine_learning"],
    "feature engineering":  ["machine_learning", "data_visualization"],

    # ── Deep Learning ────────────────────────────────────────────────────────
    "deep learning":        ["deep_learning"],
    "neural network":       ["deep_learning"],
    "tensorflow":           ["deep_learning", "machine_learning"],
    "pytorch":              ["deep_learning", "machine_learning"],
    "keras":                ["deep_learning"],
    "cnn":                  ["deep_learning"],
    "rnn":                  ["deep_learning"],
    "lstm":                 ["deep_learning"],
    "transformer":          ["deep_learning"],
    "nlp":                  ["deep_learning", "machine_learning"],
    "natural language":     ["deep_learning", "machine_learning"],
    "computer vision":      ["deep_learning"],
    "generative":           ["deep_learning"],
    "llm":                  ["deep_learning", "machine_learning"],

    # ── Statistics & Linear Algebra ─────────────────────────────────────────
    "statistic":            ["statistics"],
    "probability":          ["statistics"],
    "hypothesis":           ["statistics"],
    "linear algebra":       ["linear_algebra"],
    "matrix":               ["linear_algebra"],
    "vector":               ["linear_algebra"],
    "calculus":             ["linear_algebra"],
    "bayesian":             ["statistics"],
    "a/b test":             ["statistics"],
    "distribution":         ["statistics"],

    # ── SQL & Databases ──────────────────────────────────────────────────────
    "sql":                  ["sql", "databases"],
    "database":             ["databases"],
    "postgresql":           ["sql", "databases"],
    "mysql":                ["sql", "databases"],
    "sqlite":               ["sql", "databases"],
    "mongodb":              ["databases"],
    "nosql":                ["databases"],
    "redis":                ["databases"],
    "orm":                  ["databases"],
    "query":                ["sql"],
    "join":                 ["sql"],
    "schema":               ["databases", "sql"],

    # ── Data Visualization ──────────────────────────────────────────────────
    "visualization":        ["data_visualization"],
    "dashboard":            ["data_visualization"],
    "tableau":              ["data_visualization"],
    "power bi":             ["data_visualization"],
    "chart":                ["data_visualization"],
    "plot":                 ["data_visualization"],

    # ── Excel ───────────────────────────────────────────────────────────────
    "excel":                ["excel"],
    "spreadsheet":          ["excel"],
    "pivot table":          ["excel"],

    # ── API Design ──────────────────────────────────────────────────────────
    "api":                  ["api_design"],
    "rest":                 ["api_design"],
    "restful":              ["api_design"],
    "graphql":              ["api_design"],
    "endpoint":             ["api_design"],
    "postman":              ["api_design"],
    "swagger":              ["api_design"],
    "http":                 ["api_design", "networking"],
    "webhook":              ["api_design"],

    # ── Web: HTML/CSS & JavaScript ──────────────────────────────────────────
    "html":                 ["html_css"],
    "css":                  ["html_css"],
    "responsive":           ["html_css"],
    "javascript":           ["javascript"],
    "typescript":           ["javascript"],
    "es6":                  ["javascript"],
    "dom":                  ["javascript", "html_css"],
    "node":                 ["javascript", "api_design"],
    "express":              ["javascript", "api_design"],

    # ── Frontend / React ────────────────────────────────────────────────────
    "react":                ["react_or_frontend", "javascript"],
    "vue":                  ["react_or_frontend", "javascript"],
    "angular":              ["react_or_frontend", "javascript"],
    "svelte":               ["react_or_frontend", "javascript"],
    "next.js":              ["react_or_frontend", "javascript"],
    "frontend":             ["react_or_frontend"],
    "component":            ["react_or_frontend"],
    "state management":     ["react_or_frontend"],

    # ── UI Design ──────────────────────────────────────────────────────────
    "ui design":            ["ui_design"],
    "figma":                ["ui_design", "prototyping"],
    "wireframe":            ["ui_design", "prototyping"],
    "user interface":       ["ui_design"],

    # ── User Research & UX ─────────────────────────────────────────────────
    "user research":        ["user_research"],
    "usability":            ["user_research"],
    "ux":                   ["user_research", "ui_design"],
    "persona":              ["user_research"],
    "interview":            ["user_research", "communication"],
    "survey":               ["user_research"],

    # ── Visual Design ───────────────────────────────────────────────────────
    "visual design":        ["visual_design"],
    "typography":           ["visual_design"],
    "color theory":         ["visual_design"],
    "branding":             ["visual_design"],
    "adobe":                ["visual_design"],
    "illustrator":          ["visual_design"],

    # ── Prototyping ─────────────────────────────────────────────────────────
    "prototype":            ["prototyping"],
    "mockup":               ["prototyping", "ui_design"],
    "sketch":               ["prototyping", "ui_design"],

    # ── Git & Version Control ────────────────────────────────────────────────
    "git":                  ["git"],
    "github":               ["git"],
    "gitlab":               ["git"],
    "version control":      ["git"],
    "branch":               ["git"],
    "pull request":         ["git"],
    "merge":                ["git"],

    # ── Cloud Computing ──────────────────────────────────────────────────────
    "cloud":                ["cloud_computing"],
    "aws":                  ["cloud_computing"],
    "azure":                ["cloud_computing"],
    "gcp":                  ["cloud_computing"],
    "google cloud":         ["cloud_computing"],
    "serverless":           ["cloud_computing"],
    "lambda":               ["cloud_computing"],
    "s3":                   ["cloud_computing"],

    # ── Containerization & MLOps ─────────────────────────────────────────────
    "docker":               ["containerization"],
    "container":            ["containerization"],
    "kubernetes":           ["containerization", "cloud_computing"],
    "mlops":                ["mlops", "cloud_computing"],
    "pipeline":             ["mlops"],
    "ci/cd":                ["mlops", "containerization"],
    "cicd":                 ["mlops", "containerization"],
    "model deploy":         ["mlops", "cloud_computing"],
    "airflow":              ["mlops"],

    # ── Linux & Monitoring ───────────────────────────────────────────────────
    "linux":                ["linux"],
    "bash":                 ["linux"],
    "shell":                ["linux"],
    "command line":         ["linux"],
    "terminal":             ["linux"],
    "monitoring":           ["monitoring"],
    "prometheus":           ["monitoring"],
    "grafana":              ["monitoring"],
    "log":                  ["monitoring"],

    # ── Networking ──────────────────────────────────────────────────────────
    "networking":           ["networking"],
    "tcp":                  ["networking"],
    "ip":                   ["networking"],
    "dns":                  ["networking"],
    "protocol":             ["networking"],
    "firewall":             ["networking", "security_fundamentals"],
    "vpn":                  ["networking"],

    # ── Security ────────────────────────────────────────────────────────────
    "security":             ["security_fundamentals"],
    "cryptography":         ["cryptography", "security_fundamentals"],
    "encryption":           ["cryptography"],
    "owasp":                ["security_fundamentals"],
    "penetration":          ["security_fundamentals"],
    "vulnerability":        ["security_fundamentals"],
    "incident":             ["incident_response"],
    "forensic":             ["incident_response"],
    "soc":                  ["incident_response", "security_fundamentals"],

    # ── C++ ─────────────────────────────────────────────────────────────────
    "c++":                  ["c_plus_plus"],
    "cpp":                  ["c_plus_plus"],
    "c/c++":                ["c_plus_plus"],
    "pointer":              ["c_plus_plus"],
    "memory management":    ["c_plus_plus"],
    "embedded":             ["c_plus_plus"],

    # ── Game Development ─────────────────────────────────────────────────────
    "game":                 ["game_development"],
    "unity":                ["game_development"],
    "unreal":               ["game_development"],
    "physics engine":       ["game_development"],
    "shader":               ["game_development"],

    # ── Blockchain ───────────────────────────────────────────────────────────
    "blockchain":           ["blockchain", "cryptography"],
    "solidity":             ["blockchain", "smart_contracts"],
    "smart contract":       ["smart_contracts", "blockchain"],
    "ethereum":             ["blockchain", "smart_contracts"],
    "web3":                 ["blockchain"],
    "defi":                 ["blockchain"],

    # ── Testing ──────────────────────────────────────────────────────────────
    "test":                 ["testing"],
    "unit test":            ["testing"],
    "pytest":               ["testing", "python"],
    "jest":                 ["testing", "javascript"],
    "tdd":                  ["testing"],
    "qa":                   ["testing"],
    "automation test":      ["testing"],
    "selenium":             ["testing"],

    # ── Project & Business ───────────────────────────────────────────────────
    "project management":   ["project_management"],
    "agile":                ["project_management"],
    "scrum":                ["project_management"],
    "kanban":               ["project_management"],
    "sprint":               ["project_management"],
    "backlog":              ["project_management"],
    "jira":                 ["project_management"],
    "business analysis":    ["business_analysis"],
    "requirement":          ["business_analysis"],
    "requirements":         ["business_analysis"],
    "stakeholder":          ["business_analysis"],
    "user story":           ["business_analysis", "project_management"],
    "use case":             ["business_analysis"],
    "process model":        ["business_analysis"],
    "workflow":             ["business_analysis", "project_management"],
    "process improvement":  ["business_analysis"],
    "business process":     ["business_analysis"],
    "erp":                  ["business_analysis"],
    "crm":                  ["business_analysis"],

    # ── Critical Thinking ─────────────────────────────────────────────────────
    # NOTE: these are thin by nature — the AI rarely uses "critical thinking"
    # as a title but DOES use analytical/reasoning phrasing.
    "critical thinking":    ["critical_thinking"],
    "analytical":           ["critical_thinking"],
    "reasoning":            ["critical_thinking"],
    "logical":              ["critical_thinking", "algorithms"],
    "problem analysis":     ["critical_thinking"],
    "decision making":      ["critical_thinking"],
    "structured thinking":  ["critical_thinking"],
    "case study":           ["critical_thinking", "business_analysis"],
    "deduction":            ["critical_thinking"],
    "cognitive":            ["critical_thinking"],

    # ── Communication ─────────────────────────────────────────────────────────
    "communication":        ["communication"],
    "presentation":         ["communication"],
    "collaboration":        ["communication"],
    "active listening":     ["communication"],
    "report writing":       ["communication", "technical_writing"],
    "feedback":             ["communication"],
    "public speaking":      ["communication"],
    "negotiation":          ["communication"],

    # ── SEO & Digital Marketing ───────────────────────────────────────────────
    "seo":                  ["seo"],
    "search engine optimization": ["seo"],
    "search engine":        ["seo", "digital_marketing"],
    "keyword research":     ["seo", "digital_marketing"],
    "on-page":              ["seo"],
    "off-page":             ["seo"],
    "ranking":              ["seo"],
    "google search":        ["seo", "digital_marketing"],
    "backlink":             ["seo"],
    "content":              ["content_creation"],
    "blog":                 ["content_creation", "copywriting"],
    "copywriting":          ["copywriting"],
    "social media":         ["social_media_management"],
    "instagram":            ["social_media_management"],
    "linkedin":             ["social_media_management"],
    "community":            ["social_media_management"],
    "scheduling":           ["social_media_management"],
    "hootsuite":            ["social_media_management"],
    "buffer":               ["social_media_management"],
    "digital marketing":    ["digital_marketing"],
    "email marketing":      ["digital_marketing", "copywriting"],
    "ad campaign":          ["digital_marketing"],
    "funnel":               ["digital_marketing"],
    "google analytics":     ["digital_marketing", "seo"],
    "analytics":            ["digital_marketing", "data_visualization"],
    "audience":             ["social_media_management"],

    # ── Technical Writing ────────────────────────────────────────────────────
    "technical writing":    ["technical_writing"],
    "documentation":        ["technical_writing"],
    "readme":               ["technical_writing", "git"],
    "api documentation":    ["technical_writing", "api_design"],
    "writing":              ["technical_writing"],

    # ── Language ─────────────────────────────────────────────────────────────
    "english":              ["english_language_fluency"],
    "communication skill":  ["english_language_fluency", "communication"],
    "ielts":                ["english_language_fluency"],
    "grammar":              ["english_language_fluency"],
    "business english":     ["english_language_fluency", "communication"],

    # ── ML/DL evaluation & tuning phrasing ───────────────────────────────────
    "model evaluation":     ["machine_learning"],
    "model performance":    ["machine_learning"],
    "hyperparameter":       ["machine_learning"],
    "overfitting":          ["machine_learning"],
    "cross validation":     ["machine_learning"],
    "confusion matrix":     ["machine_learning"],
    "precision":            ["machine_learning"],
    "recall":               ["machine_learning"],
    "f1 score":             ["machine_learning"],
    "ensemble":             ["machine_learning"],
    "boosting":             ["machine_learning"],
    "bagging":              ["machine_learning"],
    "gradient descent":     ["machine_learning", "linear_algebra"],
    "backpropagation":      ["deep_learning"],
    "activation function":  ["deep_learning"],
    "fine-tuning":          ["deep_learning", "machine_learning"],
    "fine tuning":          ["deep_learning", "machine_learning"],
    "bert":                 ["deep_learning"],
    "gpt":                  ["deep_learning"],
    "hugging face":         ["deep_learning"],
    "recommendation system": ["machine_learning"],
    "recommendation":       ["machine_learning"],

    # ── System concurrency & advanced patterns ────────────────────────────────
    "concurrency":          ["system_design", "c_plus_plus"],
    "multithreading":       ["system_design", "c_plus_plus"],
    "concurrent":           ["system_design"],
    "thread":               ["system_design"],
    "asynchronous":         ["system_design", "javascript"],
    "async":                ["javascript", "python"],
    "event loop":           ["javascript"],
    "clean code":           ["oop", "testing"],
    "refactor":             ["oop", "testing"],

    # ── Security tools & techniques ───────────────────────────────────────────
    "xss":                  ["security_fundamentals"],
    "sql injection":        ["security_fundamentals", "sql"],
    "authentication":       ["security_fundamentals", "api_design"],
    "jwt":                  ["security_fundamentals", "api_design"],
    "oauth":                ["security_fundamentals", "api_design"],
    "penetration testing":  ["security_fundamentals"],
    "ctf":                  ["security_fundamentals"],
    "nmap":                 ["security_fundamentals", "networking"],
    "wireshark":            ["networking", "security_fundamentals"],
    "malware":              ["security_fundamentals", "incident_response"],
    "threat":               ["security_fundamentals", "incident_response"],
    "triage":               ["incident_response"],
    "threat detection":     ["incident_response", "security_fundamentals"],
    "security operations":  ["incident_response", "security_fundamentals"],

    # ── Cloud specifics ───────────────────────────────────────────────────────
    "terraform":            ["cloud_computing", "containerization"],
    "ansible":              ["containerization", "linux"],
    "jenkins":              ["mlops", "containerization"],
    "github actions":       ["git", "mlops"],
    "vpc":                  ["cloud_computing", "networking"],
    "ec2":                  ["cloud_computing"],
    "rds":                  ["cloud_computing", "databases"],
    "firebase":             ["databases", "cloud_computing"],
    "dynamodb":             ["databases", "cloud_computing"],
    "elasticsearch":        ["databases"],

    # ── Python advanced ───────────────────────────────────────────────────────
    "jupyter":              ["python", "data_visualization"],
    "notebook":             ["python"],
    "virtual environment":  ["python"],

    # ── Web extras ────────────────────────────────────────────────────────────
    "tailwind":             ["html_css"],
    "bootstrap":            ["html_css"],
    "sass":                 ["html_css"],
    "webpack":              ["javascript", "react_or_frontend"],
    "vite":                 ["javascript", "react_or_frontend"],
    "redux":                ["react_or_frontend"],
    "hooks":                ["react_or_frontend"],
    "websocket":            ["javascript", "networking"],

    # ── C++ extras ───────────────────────────────────────────────────────────
    "stl":                  ["c_plus_plus"],
    "smart pointer":        ["c_plus_plus"],
    "raii":                 ["c_plus_plus"],
    "template":             ["c_plus_plus"],

    # ── Research methodology ──────────────────────────────────────────────────
    "research":             ["research_methodology"],
    "literature review":    ["research_methodology"],
    "academic":             ["research_methodology"],
    "paper":                ["research_methodology"],
    "experiment":           ["research_methodology"],
    "publication":          ["research_methodology"],
    "methodology":          ["research_methodology"],
}



def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for consistent matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _make_pattern(keyword: str) -> str:
    """
    Build a regex pattern with correct word boundaries.

    \b only works when the character adjacent to the boundary is a word char
    (a-z, A-Z, 0-9, _). For keywords like 'c++' that end in non-word chars,
    we use lookahead/lookbehind instead to avoid false negatives.
    """
    escaped = re.escape(keyword)
    start = r"\b" if re.match(r"^\w", keyword) else r"(?<![\w])"
    end   = r"\b" if re.search(r"\w$", keyword) else r"(?![\w])"
    return start + escaped + end


# Pre-compile all patterns once for performance
_COMPILED_PATTERNS: dict[str, re.Pattern] = {
    kw: re.compile(_make_pattern(kw), re.IGNORECASE)
    for kw in SKILL_KEYWORD_MAP
}


def extract_skills_from_milestone(title: str) -> set[str]:
    """
    Given a milestone title (AI-generated free text), return a set of
    canonical skill keys that the milestone likely covers.

    Uses longest-match-first fuzzy keyword scanning to avoid shorter
    fragments matching before longer, more specific phrases.

    Example:
        "Learn Data Structures and Algorithms"  →  {"data_structures", "algorithms"}
        "Build REST API with Flask"             →  {"api_design", "python"}
        "Complete C++ Fundamentals"             →  {"c_plus_plus"}
    """
    normalized = _normalize(title)
    found: set[str] = set()

    # Sort keywords longest-first so "data structures" matches before "data"
    sorted_keywords = sorted(_COMPILED_PATTERNS.keys(), key=len, reverse=True)

    for keyword in sorted_keywords:
        if _COMPILED_PATTERNS[keyword].search(normalized):
            found.update(SKILL_KEYWORD_MAP[keyword])

    return found


def compute_transferability(
    completed_milestones: list,
    all_career_paths: list,
    active_career_path_id: int | None,
) -> list[dict]:
    """
    Compute how transferable the user's proven skills are to each alternative
    career path.

    Args:
        completed_milestones: list of Milestone objects where completed=True
        all_career_paths:     list of all CareerPath objects from the DB
        active_career_path_id: ID of the user's current active career path
                               (excluded from results — no point comparing
                               yourself to yourself)

    Returns:
        List of dicts (top N, above threshold, sorted descending):
        [
            {
                "title":            "ML Engineer",
                "slug":             "ml_engineer",
                "transferability":  72,          # int %
                "shared":           5,           # proven skills that match
                "required":         7,           # total required skills
                "shared_skills":    ["python", "machine_learning", ...],
            },
            ...
        ]
    """
    # Step 1: Build the union of all proven skill keys from completed milestones
    proven_skills: set[str] = set()
    for milestone in completed_milestones:
        proven_skills.update(extract_skills_from_milestone(milestone.title))

    # Step 2: Score each alternative career path
    results = []
    for career in all_career_paths:
        # Skip the user's active path — no value in comparing to yourself
        if career.id == active_career_path_id:
            continue

        required = career.get_required_skills()  # {skill_key: {weight, level}}
        if not required:
            continue

        required_keys = set(required.keys())
        shared_keys   = proven_skills & required_keys

        # Weight-aware transferability: heavier skills count more
        total_weight  = sum(
            float(info.get("weight", 1.0)) if isinstance(info, dict) else 1.0
            for info in required.values()
        )
        shared_weight = sum(
            float(required[sk].get("weight", 1.0)) if isinstance(required[sk], dict) else 1.0
            for sk in shared_keys
        )

        if total_weight == 0:
            continue

        pct = round(shared_weight / total_weight * 100)

        if pct < TRANSFERABILITY_THRESHOLD:
            continue

        results.append({
            "title":           career.title,
            "slug":            career.slug,
            "transferability": pct,
            "shared":          len(shared_keys),
            "required":        len(required_keys),
            "shared_skills":   sorted(shared_keys),
        })

    # Step 3: Sort by transferability descending, return top N
    results.sort(key=lambda x: x["transferability"], reverse=True)
    return results[:TOP_N_RESULTS]
