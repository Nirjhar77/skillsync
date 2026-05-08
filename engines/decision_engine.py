"""
Decision Engine — Career comparison and trade-off analysis.
Powers the "Compare Paths" feature, giving users a side-by-side breakdown
of difficulty, salary, demand, skill overlap, and personal fit.
"""

import json


# ─────────────────────────────────────────────────
# Static enrichment data for each career slug
# (difficulty, demand score, learning curve notes)
# ─────────────────────────────────────────────────
CAREER_META = {
    "data_analyst": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 6,
        "entry_barrier": "Low",
        "best_for": "People who love patterns, spreadsheets, and storytelling with data",
        "biggest_challenge": "SQL + statistics can feel dry at first",
        "salary_range": "$55,000 - $85,000",
        "growth": "High",
    },
    "data_scientist": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 14,
        "entry_barrier": "High",
        "best_for": "Strong math/stats background who want to build predictive models",
        "biggest_challenge": "Requires linear algebra, ML theory, and heavy Python",
        "salary_range": "$85,000 - $130,000",
        "growth": "Very High",
    },
    "data_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 12,
        "entry_barrier": "High",
        "best_for": "People who love building systems and pipelines over analysis",
        "biggest_challenge": "Requires cloud + SQL + Python at advanced level",
        "salary_range": "$90,000 - $140,000",
        "growth": "Very High",
    },
    "software_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 12,
        "entry_barrier": "High",
        "best_for": "Problem solvers who love algorithms and building core systems",
        "biggest_challenge": "DSA interviews are notoriously difficult",
        "salary_range": "$80,000 - $140,000",
        "growth": "Very High",
    },
    "web_developer": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 8,
        "entry_barrier": "Low",
        "best_for": "Creative coders who want to see results visually and build products fast",
        "biggest_challenge": "JavaScript ecosystem changes fast — easy to get lost",
        "salary_range": "$65,000 - $120,000",
        "growth": "High",
    },
    "frontend_developer": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 7,
        "entry_barrier": "Low",
        "best_for": "Design-minded people who love building beautiful UIs",
        "biggest_challenge": "CSS and cross-browser compatibility can be painful",
        "salary_range": "$60,000 - $120,000",
        "growth": "High",
    },
    "backend_developer": {
        "difficulty": "Hard",
        "difficulty_score": 3,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 10,
        "entry_barrier": "Medium",
        "best_for": "Logic-focused devs who prefer building APIs and server systems",
        "biggest_challenge": "System design and scaling concepts take time to master",
        "salary_range": "$75,000 - $135,000",
        "growth": "Very High",
    },
    "mobile_developer": {
        "difficulty": "Medium",
        "difficulty_score": 3,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 9,
        "entry_barrier": "Medium",
        "best_for": "People who want to ship apps that others use daily on their phones",
        "biggest_challenge": "Platform-specific quirks (iOS vs Android) can slow you down",
        "salary_range": "$70,000 - $130,000",
        "growth": "High",
    },
    "ml_engineer": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 18,
        "entry_barrier": "Very High",
        "best_for": "Math/CS heavy students who want to build production AI systems",
        "biggest_challenge": "Requires both research-level ML and software engineering skills",
        "salary_range": "$100,000 - $160,000",
        "growth": "Very High",
    },
    "ai_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 10,
        "entry_barrier": "High",
        "best_for": "Builders who want to integrate LLMs and AI APIs into real products",
        "biggest_challenge": "Field is evolving so fast, staying current is a job in itself",
        "salary_range": "$110,000 - $180,000",
        "growth": "Very High",
    },
    "ai_automation_specialist": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 6,
        "entry_barrier": "Low",
        "best_for": "Entrepreneurs who want to build AI workflows without heavy math",
        "biggest_challenge": "Requires broad knowledge — not deep, but wide",
        "salary_range": "$75,000 - $130,000",
        "growth": "Very High",
    },
    "ux_designer": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 7,
        "entry_barrier": "Low",
        "best_for": "Empathetic creatives who think about people first, code second",
        "biggest_challenge": "Portfolio quality matters more than any certificate",
        "salary_range": "$60,000 - $110,000",
        "growth": "High",
    },
    "product_manager": {
        "difficulty": "Medium",
        "difficulty_score": 3,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 12,
        "entry_barrier": "Medium",
        "best_for": "Leaders who love strategy, user interviews, and shipping features",
        "biggest_challenge": "Usually requires some industry experience — hard to enter as a fresh grad",
        "salary_range": "$85,000 - $145,000",
        "growth": "High",
    },
    "devops_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 12,
        "entry_barrier": "High",
        "best_for": "Systems thinkers who love automation and keeping apps running 24/7",
        "biggest_challenge": "Linux, cloud, and networking all at once is a lot",
        "salary_range": "$80,000 - $140,000",
        "growth": "Very High",
    },
    "cloud_architect": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 24,
        "entry_barrier": "Very High",
        "best_for": "Senior DevOps engineers aiming for enterprise architecture roles",
        "biggest_challenge": "Requires years of experience — not typically an entry-level role",
        "salary_range": "$120,000 - $180,000",
        "growth": "Very High",
    },
    "it_support_sysadmin": {
        "difficulty": "Easy",
        "difficulty_score": 1,
        "demand": "Moderate",
        "demand_score": 2,
        "time_to_job_ready_months": 4,
        "entry_barrier": "Very Low",
        "best_for": "Students who want a quick entry into tech and grow from there",
        "biggest_challenge": "Often a stepping stone — career ceiling can feel low",
        "salary_range": "$45,000 - $75,000",
        "growth": "Moderate",
    },
    "cybersecurity_analyst": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 12,
        "entry_barrier": "High",
        "best_for": "Detail-oriented problem solvers who think like hackers",
        "biggest_challenge": "Certifications (CompTIA, CEH) are often required alongside a degree",
        "salary_range": "$65,000 - $115,000",
        "growth": "Very High",
    },
    "qa_engineer": {
        "difficulty": "Easy",
        "difficulty_score": 1,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 5,
        "entry_barrier": "Low",
        "best_for": "Methodical thinkers who enjoy breaking things to make them better",
        "biggest_challenge": "Shifting to automation testing requires Python/Selenium skills",
        "salary_range": "$55,000 - $100,000",
        "growth": "High",
    },
    "business_analyst": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 7,
        "entry_barrier": "Low",
        "best_for": "People who bridge tech and business and communicate with both sides",
        "biggest_challenge": "Without technical depth, growth can plateau quickly",
        "salary_range": "$55,000 - $95,000",
        "growth": "High",
    },
    "technical_writer": {
        "difficulty": "Easy",
        "difficulty_score": 1,
        "demand": "Moderate",
        "demand_score": 2,
        "time_to_job_ready_months": 4,
        "entry_barrier": "Very Low",
        "best_for": "Strong writers who can explain complex technology clearly",
        "biggest_challenge": "Requires both domain knowledge and writing excellence",
        "salary_range": "$60,000 - $100,000",
        "growth": "Moderate",
    },
    "digital_marketer": {
        "difficulty": "Easy",
        "difficulty_score": 1,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 4,
        "entry_barrier": "Very Low",
        "best_for": "Creative analytical minds who want to grow user bases",
        "biggest_challenge": "Algorithms change constantly — requires staying very up to date",
        "salary_range": "$55,000 - $95,000",
        "growth": "High",
    },
    "blockchain_developer": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 16,
        "entry_barrier": "Very High",
        "best_for": "Crypto enthusiasts with strong software engineering foundations",
        "biggest_challenge": "Job market is volatile — tied to crypto market cycles",
        "salary_range": "$90,000 - $160,000",
        "growth": "High",
    },
    "game_developer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 12,
        "entry_barrier": "Medium",
        "best_for": "Programmers who enjoy real-time systems, interaction design, and creative problem solving",
        "biggest_challenge": "Portfolio quality and performance skills matter a lot, and studios can be competitive",
        "salary_range": "$60,000 - $120,000",
        "growth": "High",
    },
    "sre_platform_engineer": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 18,
        "entry_barrier": "Very High",
        "best_for": "Systems thinkers who treat operations as a software problem",
        "biggest_challenge": "High pressure during outages, on-call rotations",
        "salary_range": "$100,000 - $160,000",
        "growth": "Very High",
    },
    "cloud_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 12,
        "entry_barrier": "High",
        "best_for": "People who like building robust infrastructure without managing physical servers",
        "biggest_challenge": "Cloud provider ecosystems (AWS/Azure/GCP) are massive and constantly changing",
        "salary_range": "$85,000 - $145,000",
        "growth": "Very High",
    },
    "solutions_engineer": {
        "difficulty": "Medium",
        "difficulty_score": 3,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 8,
        "entry_barrier": "Medium",
        "best_for": "Excellent communicators who love tech but don't want to code 100% of the time",
        "biggest_challenge": "Balancing technical deep-dives with sales/client expectations",
        "salary_range": "$80,000 - $135,000",
        "growth": "High",
    },
    "bi_analyst": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 6,
        "entry_barrier": "Low",
        "best_for": "Visual thinkers who love finding the story inside the numbers",
        "biggest_challenge": "Cleaning messy data before you can visualize it",
        "salary_range": "$60,000 - $100,000",
        "growth": "High",
    },
    "mlops_engineer": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 16,
        "entry_barrier": "Very High",
        "best_for": "Engineers who want to bridge the gap between ML models and production systems",
        "biggest_challenge": "Requires deep knowledge of both DevOps infrastructure and ML lifecycles",
        "salary_range": "$100,000 - $155,000",
        "growth": "Very High",
    },
    "research_engineer": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 24,
        "entry_barrier": "Very High",
        "best_for": "Academically minded individuals who want to push the boundaries of AI",
        "biggest_challenge": "Often requires a Master's or PhD to even be considered",
        "salary_range": "$110,000 - $180,000",
        "growth": "Very High",
    },
    "soc_analyst": {
        "difficulty": "Medium",
        "difficulty_score": 3,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 6,
        "entry_barrier": "Low",
        "best_for": "Vigilant people who love investigating anomalies and hunting for clues",
        "biggest_challenge": "Alert fatigue and potentially working night/weekend shifts",
        "salary_range": "$55,000 - $95,000",
        "growth": "Very High",
    },
    "penetration_tester": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 14,
        "entry_barrier": "High",
        "best_for": "Curious problem solvers who want to legally break into systems",
        "biggest_challenge": "Thinking outside the box is required, standard checklists don't cut it",
        "salary_range": "$75,000 - $130,000",
        "growth": "Very High",
    },
    "appsec_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 12,
        "entry_barrier": "High",
        "best_for": "Developers who want to specialize in securing code and architecture",
        "biggest_challenge": "Teaching other developers secure coding practices without being a blocker",
        "salary_range": "$90,000 - $145,000",
        "growth": "Very High",
    },
    "network_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 3,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 10,
        "entry_barrier": "Medium",
        "best_for": "People who like understanding how the internet physically and logically connects",
        "biggest_challenge": "High stakes — a bad network configuration can take down a whole company",
        "salary_range": "$65,000 - $115,000",
        "growth": "High",
    },
    "cloud_security_engineer": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 18,
        "entry_barrier": "Very High",
        "best_for": "Security experts who want to protect massive distributed cloud environments",
        "biggest_challenge": "Cloud configurations are notoriously complex and easy to get wrong",
        "salary_range": "$100,000 - $155,000",
        "growth": "Very High",
    },
    "product_designer": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 8,
        "entry_barrier": "Low",
        "best_for": "Creative minds who care deeply about how users interact with digital products",
        "biggest_challenge": "Subjective feedback can be frustrating; defending design choices with data is hard",
        "salary_range": "$75,000 - $130,000",
        "growth": "High",
    },
    "ux_researcher": {
        "difficulty": "Medium",
        "difficulty_score": 3,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 9,
        "entry_barrier": "Medium",
        "best_for": "Empathetic listeners who want to discover the 'why' behind user behavior",
        "biggest_challenge": "Convincing stakeholders to act on qualitative research findings",
        "salary_range": "$70,000 - $120,000",
        "growth": "High",
    },
    "technical_pm": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 14,
        "entry_barrier": "High",
        "best_for": "Former engineers who want to drive product strategy rather than write code",
        "biggest_challenge": "Leading without authority and managing complex engineering timelines",
        "salary_range": "$100,000 - $160,000",
        "growth": "Very High",
    },
    "solutions_architect": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "Very High",
        "demand_score": 5,
        "time_to_job_ready_months": 36,
        "entry_barrier": "Very High",
        "best_for": "Veterans who can see the big picture and design systems that scale",
        "biggest_challenge": "Requires years of broad experience across development, ops, and databases",
        "salary_range": "$120,000 - $175,000",
        "growth": "Very High",
    },
    "embedded_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 14,
        "entry_barrier": "High",
        "best_for": "People who want to write code that interacts directly with physical hardware",
        "biggest_challenge": "Debugging is painful; you often don't have standard print statements or screens",
        "salary_range": "$75,000 - $130,000",
        "growth": "High",
    },
    "iot_engineer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 12,
        "entry_barrier": "Medium",
        "best_for": "Innovators who want to connect physical devices to the cloud",
        "biggest_challenge": "Balancing low power consumption with network connectivity",
        "salary_range": "$70,000 - $120,000",
        "growth": "Very High",
    },
    "firmware_developer": {
        "difficulty": "Hard",
        "difficulty_score": 4,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 12,
        "entry_barrier": "High",
        "best_for": "Detail-oriented engineers who love optimization and C/C++",
        "biggest_challenge": "Working with severe memory and processing constraints",
        "salary_range": "$75,000 - $125,000",
        "growth": "High",
    },
    "robotics_engineer": {
        "difficulty": "Very Hard",
        "difficulty_score": 5,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 18,
        "entry_barrier": "Very High",
        "best_for": "Polymaths who enjoy combining mechanical, electrical, and software engineering",
        "biggest_challenge": "Math-heavy (kinematics) and highly complex debugging environments",
        "salary_range": "$85,000 - $145,000",
        "growth": "Very High",
    },
    "it_support": {
        "difficulty": "Easy",
        "difficulty_score": 1,
        "demand": "Moderate",
        "demand_score": 3,
        "time_to_job_ready_months": 3,
        "entry_barrier": "Very Low",
        "best_for": "Patient problem-solvers who want to get their foot in the tech door quickly",
        "biggest_challenge": "Dealing with frustrated users and repetitive password resets",
        "salary_range": "$40,000 - $70,000",
        "growth": "Moderate",
    },
    "technical_support_engineer": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 6,
        "entry_barrier": "Low",
        "best_for": "Tech-savvy communicators who want to solve complex puzzles for clients",
        "biggest_challenge": "High pressure situations when enterprise clients have critical outages",
        "salary_range": "$50,000 - $90,000",
        "growth": "High",
    },
    "operations_analyst": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 3,
        "time_to_job_ready_months": 5,
        "entry_barrier": "Low",
        "best_for": "Process-oriented thinkers who want to optimize how a business runs",
        "biggest_challenge": "Managing change and convincing teams to adopt new processes",
        "salary_range": "$50,000 - $85,000",
        "growth": "High",
    },
    "crm_erp_analyst": {
        "difficulty": "Medium",
        "difficulty_score": 2,
        "demand": "High",
        "demand_score": 4,
        "time_to_job_ready_months": 6,
        "entry_barrier": "Medium",
        "best_for": "Business-minded folks who want to master enterprise platforms like Salesforce/SAP",
        "biggest_challenge": "Platform updates can break existing workflows, requiring constant learning",
        "salary_range": "$55,000 - $90,000",
        "growth": "High",
    },
}


def calculate_skill_overlap(career_a_skills: dict, career_b_skills: dict) -> dict:
    """
    Calculate the skill overlap between two career paths.
    Returns shared skills and unique skills for each path.
    """
    keys_a = set(career_a_skills.keys())
    keys_b = set(career_b_skills.keys())

    shared = list(keys_a & keys_b)
    only_a = list(keys_a - keys_b)
    only_b = list(keys_b - keys_a)

    total_unique = len(keys_a | keys_b)
    overlap_pct = round((len(shared) / total_unique) * 100) if total_unique > 0 else 0

    return {
        "shared_skills": shared,
        "only_in_a": only_a,
        "only_in_b": only_b,
        "overlap_percentage": overlap_pct,
    }


def get_personal_fit(profile, career_slug: str, score_details: dict) -> dict:
    """
    Calculate personal fit metrics for a user vs a career path.
    Returns readiness %, matched/gap counts, and estimated time to job-ready.
    """
    meta = CAREER_META.get(career_slug, {})
    score = score_details.get("score", 0)
    matched = score_details.get("matched_skills", [])
    gaps = score_details.get("gap_skills", [])
    curriculum = score_details.get("covered_by_curriculum", {})

    # Estimate months to job-ready: base from meta, adjusted by skill gaps
    base_months = meta.get("time_to_job_ready_months", 12)
    gap_count = len(gaps)
    adjusted_months = max(1, base_months - (len(matched) * 0.5) + (gap_count * 1.5))
    adjusted_months = round(min(adjusted_months, base_months * 1.5))

    return {
        "readiness_score": score,
        "matched_count": len(matched),
        "gap_count": gap_count,
        "curriculum_covered_count": len(curriculum),
        "estimated_months_to_ready": adjusted_months,
        "difficulty": meta.get("difficulty", "Unknown"),
        "difficulty_score": meta.get("difficulty_score", 3),
        "demand": meta.get("demand", "High"),
        "demand_score": meta.get("demand_score", 3),
        "entry_barrier": meta.get("entry_barrier", "Medium"),
        "best_for": meta.get("best_for", ""),
        "biggest_challenge": meta.get("biggest_challenge", ""),
        "salary_range": meta.get("salary_range", "Varies"),
        "growth": meta.get("growth", "High"),
    }


def compare_careers(profile, career_a, career_b, score_a: dict, score_b: dict) -> dict:
    """
    Generate a full side-by-side comparison of two career paths for a given user.

    Args:
        profile: User's profile object
        career_a: CareerPath DB object (first path)
        career_b: CareerPath DB object (second path)
        score_a: Score details dict from rule engine for career A
        score_b: Score details dict from rule engine for career B

    Returns:
        dict: Full comparison object ready for rendering in the template
    """
    skills_a = career_a.get_required_skills()
    skills_b = career_b.get_required_skills()

    overlap = calculate_skill_overlap(skills_a, skills_b)
    fit_a = get_personal_fit(profile, career_a.slug, score_a)
    fit_b = get_personal_fit(profile, career_b.slug, score_b)

    # Determine winner in each dimension
    def winner(val_a, val_b, lower_is_better=False):
        if lower_is_better:
            if val_a < val_b:
                return "a"
            elif val_b < val_a:
                return "b"
        else:
            if val_a > val_b:
                return "a"
            elif val_b > val_a:
                return "b"
        return "tie"

    verdicts = {
        "readiness": winner(fit_a["readiness_score"], fit_b["readiness_score"]),
        "salary": winner(
            int(fit_a["salary_range"].replace("$", "").replace(",", "").split(" - ")[1]) if " - " in fit_a["salary_range"] else 0,
            int(fit_b["salary_range"].replace("$", "").replace(",", "").split(" - ")[1]) if " - " in fit_b["salary_range"] else 0,
        ),
        "time_to_ready": winner(fit_a["estimated_months_to_ready"], fit_b["estimated_months_to_ready"], lower_is_better=True),
        "difficulty": winner(fit_a["difficulty_score"], fit_b["difficulty_score"], lower_is_better=True),
        "demand": winner(fit_a["demand_score"], fit_b["demand_score"]),
    }

    return {
        "career_a": {
            "slug": career_a.slug,
            "title": career_a.title,
            "category": career_a.category,
            "description": career_a.description,
            "fit": fit_a,
            "score": score_a.get("score", 0),
            "matched_skills": score_a.get("matched_skills", []),
            "gap_skills": score_a.get("gap_skills", []),
        },
        "career_b": {
            "slug": career_b.slug,
            "title": career_b.title,
            "category": career_b.category,
            "description": career_b.description,
            "fit": fit_b,
            "score": score_b.get("score", 0),
            "matched_skills": score_b.get("matched_skills", []),
            "gap_skills": score_b.get("gap_skills", []),
        },
        "overlap": overlap,
        "verdicts": verdicts,
    }
