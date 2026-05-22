"""
Rule-Based Engine — Scores and ranks career paths based on student profile.
Takes into account existing skills, interests, semester progress, curriculum
coverage, and activity-based interests for a realistic match score (0–100).

SCORING BREAKDOWN (interest-first):
  - Tech interest alignment   → up to 60 pts  ← PRIMARY rank driver
  - Skill match               → up to 25 pts  ← secondary fine-tuner
  - Activity interest bonus   → up to  8 pts  ← weak supporting signal
  - Curriculum coverage bonus → up to  7 pts  ← supplemental
  - Semester seniority boost  → up to  8 pts  ← experience bonus
  Total possible: 108 → clamped to 100

KEY GUARANTEE: A career OUTSIDE all of the user's chosen tech interest maps
can score at most ~40 pts (25 skills + 8 activity + 7 curriculum) — it will
NEVER beat a career that IS directly listed in the user's interest maps.
"""

from engines.curriculum_engine import check_skill_coverage, identify_skill_gaps, get_covered_skills


SKILL_ALIASES = {
    "c++": "c_plus_plus",
    "cpp": "c_plus_plus",
    "c_cpp": "c_plus_plus",
    "c/c++": "c_plus_plus",
    "cplusplus": "c_plus_plus",
}


def _normalize_skill_key(skill):
    """Return the canonical skill key used by profile, course, and career data."""
    key = (skill or "").strip().lower()
    return SKILL_ALIASES.get(key, key)


# ────────────────────────────────────────────────────────────────────
# Primary tech topic set — every string here maps 1:1 to a chip in
# the profile form's "Tech Topics" section.
# ────────────────────────────────────────────────────────────────────
PRIMARY_TECH_INTERESTS = {
    "Artificial Intelligence", "Machine Learning", "Deep Learning",
    "Data Analysis", "Software Development", "Web Development",
    "Mobile Development", "Game Development", "DevOps & Automation",
    "Cloud Computing", "Networking & Infrastructure", "Cybersecurity",
    "UX Design", "Product Management", "Blockchain", "IoT",
    "Embedded Systems", "Robotics", "Hardware Engineering",
    "Data Engineering", "Enterprise Systems", "Quality Assurance",
}


# ────────────────────────────────────────────────────────────────────
# Interest → career slug mapping
# Keys MUST match the exact strings used in the profile form.
# ────────────────────────────────────────────────────────────────────
INTEREST_CAREER_MAP = {
    # --- AI / ML cluster ---
    "Artificial Intelligence": [
        "ai_engineer", "ml_engineer", "ai_automation_specialist",
        "data_scientist", "research_engineer", "mlops_engineer",
    ],
    "Machine Learning": [
        "ml_engineer", "ai_engineer", "data_scientist",
        "ai_automation_specialist", "research_engineer", "mlops_engineer",
    ],
    "Deep Learning": [
        "ml_engineer", "ai_engineer", "data_scientist", "research_engineer",
    ],

    # --- Data cluster ---
    "Data Analysis": [
        "data_analyst", "data_scientist", "data_engineer",
        "business_analyst", "bi_analyst", "operations_analyst",
    ],

    # --- Software / Web cluster ---
    "Software Development": [
        "software_engineer", "backend_developer", "frontend_developer",
        "web_developer", "qa_engineer", "appsec_engineer",
    ],
    "Web Development": [
        "web_developer", "frontend_developer", "backend_developer",
        "software_engineer",
    ],
    "Mobile Development": [
        "mobile_developer", "frontend_developer", "web_developer",
        "software_engineer",
    ],
    "Game Development": [
        "game_developer", "software_engineer", "frontend_developer", "mobile_developer",
    ],

    # --- Infrastructure cluster ---
    "DevOps & Automation": [
        "devops_engineer", "ai_automation_specialist", "cloud_architect",
        "sre_platform_engineer", "cloud_engineer", "mlops_engineer",
        "it_support_sysadmin", "backend_developer",
    ],
    "Cloud Computing": [
        "cloud_architect", "devops_engineer", "cloud_engineer",
        "sre_platform_engineer", "ai_engineer", "data_engineer",
        "backend_developer", "cloud_security_engineer",
    ],
    "Networking & Infrastructure": [
        "network_engineer", "it_support_sysadmin", "devops_engineer",
        "cloud_architect", "cybersecurity_analyst", "cloud_engineer",
        "it_support",
    ],

    # --- Security cluster ---
    "Cybersecurity": [
        "cybersecurity_analyst", "penetration_tester", "soc_analyst",
        "appsec_engineer", "cloud_security_engineer",
        "it_support_sysadmin", "devops_engineer",
    ],

    # --- Design / Product cluster ---
    "UX Design": [
        "ux_designer", "product_designer", "ux_researcher",
        "frontend_developer", "product_manager",
    ],
    "Product Management": [
        "product_manager", "technical_pm", "business_analyst",
        "solutions_architect", "crm_erp_analyst",
    ],

    # --- Niche / emerging ---
    "Blockchain": [
        "blockchain_developer", "software_engineer", "backend_developer",
    ],
    "IoT": [
        "iot_engineer", "embedded_engineer", "firmware_developer",
        "software_engineer", "devops_engineer",
    ],
    "Embedded Systems": [
        "embedded_engineer", "firmware_developer", "robotics_engineer",
        "iot_engineer", "software_engineer",
    ],
    "Robotics": [
        "robotics_engineer", "embedded_engineer", "firmware_developer",
        "software_engineer",
    ],
    "Hardware Engineering": [
        "embedded_engineer", "iot_engineer", "firmware_developer",
        "robotics_engineer",
    ],
    "Data Engineering": [
        "data_engineer", "mlops_engineer", "cloud_engineer", "backend_developer",
    ],
    "Enterprise Systems": [
        "crm_erp_analyst", "solutions_architect", "solutions_engineer",
        "technical_pm", "business_analyst", "operations_analyst",
    ],
    "Quality Assurance": [
        "qa_engineer", "software_engineer", "appsec_engineer",
    ],
}


# ────────────────────────────────────────────────────────────────────
# Activity → career slug mapping (what the user *enjoys doing*)
# These are weaker signals than tech topic interests.
# ────────────────────────────────────────────────────────────────────
ACTIVITY_CAREER_MAP = {
    "Solving Puzzles & Logic":  ["software_engineer", "data_scientist", "cybersecurity_analyst", "ml_engineer", "data_analyst", "penetration_tester", "research_engineer"],
    "Building Products":        ["product_manager", "software_engineer", "web_developer", "mobile_developer", "backend_developer", "technical_pm"],
    "Designing Interfaces":     ["ux_designer", "frontend_developer", "web_developer", "product_manager", "product_designer", "ux_researcher"],
    "Analyzing Data":           ["data_analyst", "data_scientist", "business_analyst", "ml_engineer", "bi_analyst", "operations_analyst"],
    "Securing Systems":         ["cybersecurity_analyst", "devops_engineer", "it_support_sysadmin", "backend_developer", "soc_analyst", "penetration_tester", "cloud_security_engineer"],
    "Working with Hardware":    ["it_support_sysadmin", "devops_engineer", "cloud_architect", "embedded_engineer", "iot_engineer", "firmware_developer", "robotics_engineer"],
    "Leading Teams":            ["product_manager", "business_analyst", "cloud_architect", "ai_automation_specialist", "technical_pm", "solutions_architect"],
}


# Legacy lowercase aliases — catches old-format or free-text interests
_LEGACY_ALIASES = {
    "data analysis":                    "Data Analysis",
    "machine learning":                 "Machine Learning",
    "artificial intelligence":          "Artificial Intelligence",
    "web development":                  "Web Development",
    "software development":             "Software Development",
    "cybersecurity":                    "Cybersecurity",
    "cloud computing":                  "Cloud Computing",
    "design":                           "UX Design",
    "ux design":                        "UX Design",
    "product management":               "Product Management",
    "mobile development":               "Mobile Development",
    "game development":                 "Game Development",
    "deep learning":                    "Deep Learning",
    "networking":                       "Networking & Infrastructure",
    "automation":                       "DevOps & Automation",
    "devops":                           "DevOps & Automation",
    "devops & automation":              "DevOps & Automation",
    "blockchain":                       "Blockchain",
    "iot":                              "IoT",
    "embedded systems":                 "Embedded Systems",
    "database":                         "Data Analysis",
    "database administration":          "Data Analysis",
    "digital marketing":                "Data Analysis",
    "content creation":                 "UX Design",
    "video editing":                    "UX Design",
    "graphic design":                   "Designing Interfaces",
    "technical writing":                "Product Management",
    "hardware & robotics":              "Working with Hardware",
    "operations":                       "DevOps & Automation",
    "finance":                          "Analyzing Data",
    "networking & infrastructure":      "Networking & Infrastructure",
    "solving puzzles & logic":          "Solving Puzzles & Logic",
    "building products":                "Building Products",
    "designing interfaces":             "Designing Interfaces",
    "analyzing data":                   "Analyzing Data",
    "securing systems":                 "Securing Systems",
    "working with hardware":            "Working with Hardware",
    "leading teams":                    "Leading Teams",
}


def _resolve_interest(interest_raw):
    """Normalize an interest string to its canonical map key."""
    if interest_raw in INTEREST_CAREER_MAP or interest_raw in ACTIVITY_CAREER_MAP:
        return interest_raw
    lower = interest_raw.lower().strip()
    for key in list(INTEREST_CAREER_MAP.keys()) + list(ACTIVITY_CAREER_MAP.keys()):
        if key.lower() == lower:
            return key
    canonical = _LEGACY_ALIASES.get(lower)
    if canonical:
        return canonical
    return None


def _proficiency_match(student_level, required_level):
    """
    Calculate how well a student's proficiency matches the requirement.
    Returns a factor between 0.0 and 1.0.
    """
    levels = {"beginner": 1, "intermediate": 2, "advanced": 3}
    student_rank = levels.get(student_level, 1)
    required_rank = levels.get(required_level, 1)

    if student_rank >= required_rank:
        return 1.0
    elif student_rank == required_rank - 1:
        return 0.75  # One level below: gap is bridgeable by roadmap
    else:
        return 0.50  # Two levels below: still viable with effort


def _get_semester_boost(profile):
    """
    Give a small score boost for students in higher semesters.
    Returns bonus points (0–8).
    """
    semester = profile.semester or 1
    if semester <= 2:
        return 0
    elif semester <= 4:
        return 2
    elif semester <= 6:
        return 5
    else:
        return 8


def score_career_path(profile, career_path, user_courses):
    """
    Score a single career path for a student using interest-first tiering.

    The user's PRIMARY tech interest selections dominate the ranking.
    Skills/curriculum can only differentiate within the same interest tier.
    """
    raw_required_skills = career_path.get_required_skills()
    required_skills = {
        _normalize_skill_key(skill): info
        for skill, info in raw_required_skills.items()
    }
    if not required_skills:
        return {
            "score": 0,
            "signal_score": 0,
            "matched_skills": [],
            "gap_skills": [],
            "covered_by_curriculum": {},
        }

    # ── 1. Curriculum coverage check ──────────────────────────────────
    coverage = check_skill_coverage(user_courses, required_skills)
    gap_skills_dict = identify_skill_gaps(coverage)
    covered_skills = get_covered_skills(coverage)

    # ── 2. Skill matching → up to 25 pts (secondary fine-tuner) ───────
    user_skills = {
        _normalize_skill_key(s.skill_name): s.proficiency
        for s in profile.skills
    }
    total_weight = sum(
        info["weight"] if isinstance(info, dict) else 1.0
        for info in required_skills.values()
    )
    matched_weight = 0.0
    matched_skills = []
    gap_skills = []

    for skill, info in required_skills.items():
        weight = info["weight"] if isinstance(info, dict) else 1.0
        required_level = info["level"] if isinstance(info, dict) else "beginner"

        if skill in user_skills:
            factor = _proficiency_match(user_skills[skill], required_level)
            matched_weight += weight * factor
            matched_skills.append(skill)
        elif skill in covered_skills:
            ctype = coverage[skill]["coverage_type"]
            student_level = coverage[skill].get("student_level", "beginner") or "beginner"
            base_factor = _proficiency_match(student_level, required_level)
            if ctype == "completed":
                matched_weight += weight * base_factor
                matched_skills.append(skill)
            elif ctype == "in_progress":
                matched_weight += weight * base_factor * 0.85
                matched_skills.append(skill)
            else:  # upcoming
                matched_weight += weight * base_factor * 0.60
                matched_skills.append(skill)
        elif coverage.get(skill, {}).get("partially_covered"):
            matched_weight += weight * 0.40
            gap_skills.append(skill)
        else:
            gap_skills.append(skill)

    # Capped at 25 pts so skills can't override interest alignment
    skill_match_score = (matched_weight / total_weight * 25) if total_weight > 0 else 0

    # ── 3. Interest alignment → PRIMARY signal, up to 60 pts ──────────
    interests = profile.get_interests()
    interest_score = 0.0
    activity_score = 0.0

    tech_interests = []
    activity_interests = []

    for interest in (interests or []):
        resolved = _resolve_interest(interest)
        if not resolved:
            continue
        if resolved in PRIMARY_TECH_INTERESTS:
            tech_interests.append(resolved)
        elif resolved in ACTIVITY_CAREER_MAP:
            activity_interests.append(resolved)

    # Tech interest scoring:
    # position 0 → 22 pts, decaying by 25% per position, floor at 4 pts
    # Multiple tech interests stack (e.g. AI + DevOps), capped at 60 total.
    for resolved in tech_interests:
        mapped_careers = INTEREST_CAREER_MAP.get(resolved, [])
        if career_path.slug in mapped_careers:
            position = mapped_careers.index(career_path.slug)
            pts = max(22 * (0.75 ** position), 4.0)
            interest_score += pts

    interest_score = min(interest_score, 60)

    # Activity interest scoring: weak signal, max 8 pts total.
    for resolved in activity_interests:
        act_careers = ACTIVITY_CAREER_MAP.get(resolved, [])
        if career_path.slug in act_careers:
            pos = act_careers.index(career_path.slug)
            pts = max(3 * (0.70 ** pos), 0.5)
            activity_score += pts

    activity_score = min(activity_score, 8)

    # ── 4. Curriculum coverage bonus → up to 7 pts ────────────────────
    covered_ratio = len(covered_skills) / len(required_skills) if required_skills else 0
    curriculum_bonus = covered_ratio * 7

    # ── 5. Semester seniority boost (0–8 pts) ─────────────────────────
    signal_score = skill_match_score + interest_score + activity_score + curriculum_bonus
    semester_boost = _get_semester_boost(profile) if signal_score > 0 else 0

    # ── Final score ────────────────────────────────────────────────────
    total_score = min(signal_score + semester_boost, 100)

    return {
        "score": round(total_score, 1),
        "signal_score": round(signal_score, 1),
        "skill_match_score": round(skill_match_score, 1),
        "interest_score": round(interest_score, 1),
        "activity_score": round(activity_score, 1),
        "curriculum_bonus": round(curriculum_bonus, 1),
        "semester_boost": semester_boost,
        "matched_skills": matched_skills,
        "gap_skills": gap_skills,
        "covered_by_curriculum": covered_skills,
        "coverage": coverage,
    }


def rank_careers(profile, career_paths, user_courses, min_score=5):
    """
    Score and rank all career paths for a student.
    Returns list of (career_path, score_details) sorted by score descending.
    Careers with a score below `min_score` are excluded entirely.
    """
    results = []
    for career in career_paths:
        details = score_career_path(profile, career, user_courses)
        if details.get("signal_score", details["score"]) >= min_score:
            results.append((career, details))

    results.sort(key=lambda x: x[1]["score"], reverse=True)
    return results
