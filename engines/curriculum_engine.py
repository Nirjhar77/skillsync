"""
Curriculum Engine — Cross-references student courses against career skill requirements.
Identifies which skills are already covered by the student's academic curriculum
so the rule engine and LLM can skip or de-prioritize them.
"""

import json
import os
from flask import current_app


SKILL_ALIASES = {
    "c++": "c_plus_plus",
    "cpp": "c_plus_plus",
    "c_cpp": "c_plus_plus",
    "c/c++": "c_plus_plus",
    "cplusplus": "c_plus_plus",
}


def _normalize_skill_key(skill):
    key = (skill or "").strip().lower()
    return SKILL_ALIASES.get(key, key)


def load_course_catalog():
    """Load the pre-populated course catalog from JSON."""
    data_path = os.path.join(current_app.config["DATA_DIR"], "course_catalog.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("courses", {})


def get_course_skills(course_code, catalog=None):
    """Get skills covered by a specific course."""
    if catalog is None:
        catalog = load_course_catalog()
    course = catalog.get(course_code, {})
    return course.get("skills_covered", {})


def check_skill_coverage(user_courses, career_required_skills):
    """
    Check which career-required skills are already covered by the student's courses.

    Args:
        user_courses: list of UserCourse objects (with course_code and status)
        career_required_skills: dict of {skill: {weight, level}} from career path

    Returns:
        dict: {
            skill_name: {
                "covered": True/False,
                "source_course": "CS301" or None,
                "course_name": "Probability & Statistics" or None,
                "student_level": "intermediate" or None,
                "required_level": "intermediate",
                "coverage_type": "completed" / "upcoming" / None
            }
        }
    """
    catalog = load_course_catalog()

    # Build a map of all skills the student has from courses
    # Track both the skill level and which course provides it
    student_course_skills = {}

    for uc in user_courses:
        course_info = catalog.get(uc.course_code, {})
        course_skills = course_info.get("skills_covered", {})

        for skill, level in course_skills.items():
            skill = _normalize_skill_key(skill)
            level_rank = _level_to_rank(level)
            existing_rank = _level_to_rank(student_course_skills.get(skill, {}).get("level"))

            # Keep the highest level across all courses
            if level_rank > existing_rank:
                student_course_skills[skill] = {
                    "level": level,
                    "course_code": uc.course_code,
                    "course_name": course_info.get("name", uc.course_code),
                    "status": uc.status,
                }

    # Now check each required skill against what courses provide
    coverage = {}
    for skill, req_info in career_required_skills.items():
        skill = _normalize_skill_key(skill)
        required_level = req_info.get("level", "beginner") if isinstance(req_info, dict) else "beginner"

        if skill in student_course_skills:
            scs = student_course_skills[skill]
            student_level_rank = _level_to_rank(scs["level"])
            required_level_rank = _level_to_rank(required_level)

            coverage[skill] = {
                "covered": student_level_rank >= required_level_rank,
                "partially_covered": student_level_rank > 0,
                "source_course": scs["course_code"],
                "course_name": scs["course_name"],
                "student_level": scs["level"],
                "required_level": required_level,
                "coverage_type": scs["status"],
            }
        else:
            coverage[skill] = {
                "covered": False,
                "partially_covered": False,
                "source_course": None,
                "course_name": None,
                "student_level": None,
                "required_level": required_level,
                "coverage_type": None,
            }

    return coverage


def get_upcoming_courses(user_courses, current_semester, catalog=None):
    """
    Get courses the student will take in upcoming semesters.

    Args:
        user_courses: list of UserCourse objects
        current_semester: int
        catalog: optional pre-loaded catalog

    Returns:
        list of dicts with course info and skills
    """
    if catalog is None:
        catalog = load_course_catalog()

    upcoming = []
    for uc in user_courses:
        if uc.status == "upcoming":
            course_info = catalog.get(uc.course_code, {})
            upcoming.append({
                "code": uc.course_code,
                "name": course_info.get("name", uc.course_code),
                "semester": course_info.get("semester", current_semester + 1),
                "skills": course_info.get("skills_covered", {}),
            })

    # Also add catalog courses from future semesters not yet selected
    return upcoming


def identify_skill_gaps(coverage):
    """
    From a coverage dict, return only the skills that are NOT fully covered.

    Returns:
        dict of {skill: required_level} for uncovered skills
    """
    gaps = {}
    for skill, info in coverage.items():
        if not info["covered"]:
            gaps[skill] = info["required_level"]
    return gaps


def get_covered_skills(coverage):
    """Return skills that ARE covered by curriculum."""
    covered = {}
    for skill, info in coverage.items():
        if info["covered"]:
            covered[skill] = {
                "level": info["student_level"],
                "source": info["course_name"],
                "type": info["coverage_type"],
            }
    return covered


def _level_to_rank(level):
    """Convert proficiency level string to numeric rank for comparison."""
    ranks = {"beginner": 1, "intermediate": 2, "advanced": 3}
    return ranks.get(level, 0) if level else 0
