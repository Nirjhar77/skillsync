"""
Rule-Based Engine — Scores and ranks career paths based on student profile.
Takes into account existing skills, interests, semester progress, curriculum
coverage, and activity-based interests for a realistic match score (0–100).

SCORING BREAKDOWN (revised):
  - Skill match (direct + curriculum)  → up to 40 pts
  - Interest alignment                  → up to 35 pts
  - Activity/aptitude alignment         → up to 15 pts
  - Curriculum coverage bonus           → up to 10 pts
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
        "devops_engineer", "cloud_architect", "ai_automation_specialist",
        "it_support_sysadmin", "backend_developer", "sre_platform_engineer",
        "cloud_engineer", "mlops_engineer",
    ],
    "Cloud Computing": [
        "cloud_architect", "devops_engineer", "backend_developer",
        "data_engineer", "ai_engineer", "cloud_engineer", "sre_platform_engineer",
        "cloud_security_engineer",
    ],
    "Networking & Infrastructure": [
        "it_support_sysadmin", "devops_engineer", "cloud_architect",
        "cybersecurity_analyst", "network_engineer", "cloud_engineer",
        "it_support",
    ],

    # --- Security cluster ---
    "Cybersecurity": [
        "cybersecurity_analyst", "it_support_sysadmin", "devops_engineer",
        "soc_analyst", "penetration_tester", "appsec_engineer", "cloud_security_engineer",
    ],

    # --- Design / Product cluster ---
    "UX Design": [
        "ux_designer", "frontend_developer", "product_manager", "product_designer",
        "ux_researcher",
    ],
    "Product Management": [
        "product_manager", "business_analyst", "ux_designer", "technical_pm",
        "solutions_architect", "crm_erp_analyst",
    ],

    # --- Niche / emerging ---
    "Blockchain": [
        "blockchain_developer", "software_engineer", "backend_developer",
    ],
    "IoT": [
        "software_engineer", "devops_engineer", "it_support_sysadmin", "iot_engineer",
        "embedded_engineer", "firmware_developer",
    ],
    "Embedded Systems": [
        "software_engineer", "devops_engineer", "qa_engineer", "embedded_engineer",
        "firmware_developer", "robotics_engineer",
    ],
    "Robotics": [
        "robotics_engineer", "embedded_engineer", "firmware_developer", "software_engineer",
    ],
    "Hardware Engineering": [
        "embedded_engineer", "iot_engineer", "firmware_developer", "robotics_engineer",
    ],
    "Data Engineering": [
        "data_engineer", "mlops_engineer", "cloud_engineer", "backend_developer",
    ],
    "Enterprise Systems": [
        "crm_erp_analyst", "solutions_architect", "solutions_engineer", "technical_pm",
        "business_analyst", "operations_analyst",
    ],
    "Quality Assurance": [
        "qa_engineer", "software_engineer", "appsec_engineer",
    ],

    # ─── NEW: Activity-based interests ───────────────────────────────
    "Solving Puzzles & Logic": [
        "software_engineer", "cybersecurity_analyst", "data_scientist",
        "ml_engineer", "data_analyst", "penetration_tester", "research_engineer",
        "appsec_engineer", "robotics_engineer",
    ],
    "Building Products": [
        "product_manager", "software_engineer", "web_developer",
        "mobile_developer", "backend_developer", "business_analyst",
        "technical_pm", "product_designer",
    ],
    "Designing Interfaces": [
        "ux_designer", "frontend_developer", "web_developer",
        "mobile_developer", "product_manager", "product_designer", "ux_researcher",
    ],
    "Analyzing Data": [
        "data_analyst", "data_scientist", "business_analyst",
        "data_engineer", "ml_engineer", "bi_analyst", "operations_analyst",
    ],
    "Securing Systems": [
        "cybersecurity_analyst", "devops_engineer", "it_support_sysadmin",
        "cloud_architect", "backend_developer", "soc_analyst", "penetration_tester",
        "cloud_security_engineer", "appsec_engineer", "network_engineer",
    ],
    "Working with Hardware": [
        "it_support_sysadmin", "devops_engineer", "cloud_architect",
        "qa_engineer", "embedded_engineer", "iot_engineer", "firmware_developer",
        "robotics_engineer", "it_support",
    ],
    "Leading Teams": [
        "product_manager", "business_analyst", "cloud_architect",
        "devops_engineer", "ai_automation_specialist", "technical_pm",
        "solutions_architect", "solutions_engineer",
    ],
}


# ────────────────────────────────────────────────────────────────────
# Activity → career slug mapping (separate so bonuses don't stack)
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
    """Normalize an interest string to its canonical INTEREST_CAREER_MAP key."""
    if interest_raw in INTEREST_CAREER_MAP:
        return interest_raw
    lower = interest_raw.lower().strip()
    for key in INTEREST_CAREER_MAP:
        if key.lower() == lower:
            return key
    canonical = _LEGACY_ALIASES.get(lower)
    if canonical and canonical in INTEREST_CAREER_MAP:
        return canonical
    return None


def _proficiency_match(student_level, required_level):
    """
    Calculate how well a student's proficiency matches the requirement.
    Returns a factor between 0.0 and 1.0.
    
    KEY FIX: Be more lenient — a beginner who needs intermediate still scores
    reasonably well, because the roadmap exists to close that gap.
    """
    levels = {"beginner": 1, "intermediate": 2, "advanced": 3}
    student_rank = levels.get(student_level, 1)  # Default 1 (beginner) not 0
    required_rank = levels.get(required_level, 1)

    if student_rank >= required_rank:
        return 1.0
    elif student_rank == required_rank - 1:
        return 0.75  # One level below: was 0.6, now 0.75 (gap is bridgeable)
    else:
        return 0.50  # Two levels below: was 0.3, now 0.5 (still viable)


def _get_semester_boost(profile):
    """
    Give a small score boost for students in higher semesters who simply
    haven't added all their skills manually — they are more prepared.
    Returns bonus points (0–8).
    """
    semester = profile.semester or 1
    # Semesters 1-2: no boost; 3-4: +2; 5-6: +5; 7-8: +8
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
    Score a single career path for a student.

    Returns:
        dict with score breakdown.
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

    # ── 2. Skill matching → up to 40 pts ──────────────────────────────
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
            # Student explicitly listed this skill
            factor = _proficiency_match(user_skills[skill], required_level)
            matched_weight += weight * factor
            matched_skills.append(skill)
        elif skill in covered_skills:
            # Skill is covered by a course they've taken/are taking
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
            # Partially covered: give 40% of the weight
            matched_weight += weight * 0.40
            gap_skills.append(skill)
        else:
            gap_skills.append(skill)

    skill_match_score = (matched_weight / total_weight * 40) if total_weight > 0 else 0

    # ── 3. Interest alignment → up to 35 pts ──────────────────────────
    interests = profile.get_interests()
    interest_score = 0.0
    activity_score = 0.0

    if interests:
        for interest in interests:
            resolved = _resolve_interest(interest)
            if not resolved:
                continue

            # Check if this is an activity-based interest (double map)
            is_activity = resolved in ACTIVITY_CAREER_MAP

            # Interest map scoring
            mapped_careers = INTEREST_CAREER_MAP.get(resolved, [])
            if career_path.slug in mapped_careers:
                position = mapped_careers.index(career_path.slug)
                position_factor = max(1.0 - (position * 0.18), 0.3)
                interest_score += 10 * position_factor

            # Activity map bonus (separate pool)
            if is_activity:
                act_careers = ACTIVITY_CAREER_MAP.get(resolved, [])
                if career_path.slug in act_careers:
                    pos = act_careers.index(career_path.slug)
                    activity_score += 5 * max(1.0 - (pos * 0.2), 0.3)

    interest_score = min(interest_score, 35)
    activity_score = min(activity_score, 15)

    # ── 4. Curriculum coverage bonus → up to 10 pts ───────────────────
    covered_ratio = len(covered_skills) / len(required_skills) if required_skills else 0
    curriculum_bonus = covered_ratio * 10

    # ── 5. Semester seniority boost (0–8 pts) ─────────────────────────
    signal_score = skill_match_score + interest_score + activity_score + curriculum_bonus
    semester_boost = _get_semester_boost(profile) if signal_score > 0 else 0

    # ── Final score ────────────────────────────────────────────────────
    total_score = min(
        signal_score + semester_boost,
        100
    )

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
