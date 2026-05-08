"""Profile routes — Setup wizard for student profile, skills, and course selection."""

import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from database.models import db, Profile, UserSkill, UserCourse, log_activity
from engines.curriculum_engine import load_course_catalog

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


# Available skills for the skills picker (Expanded to include non-tech / soft skills)
AVAILABLE_SKILLS = [
    # Core Tech
    "python", "javascript", "html_css", "sql", "java", "c_plus_plus",
    "data_structures", "algorithms", "oop", "git", "linux",
    "statistics", "machine_learning", "deep_learning", "data_visualization",
    "databases", "networking", "cloud_computing", "containerization",
    "api_design", "system_design", "testing", "excel",
    "monitoring", "research_methodology", "blockchain", "smart_contracts",
    "game_development",
    "ui_design", "user_research", "prototyping", "visual_design",
    # Soft Skills & Creative
    "communication", "critical_thinking", "project_management",
    "business_analysis", "cryptography", "security_fundamentals",
    "incident_response", "linear_algebra", "react_or_frontend", "mlops",
    "english_language_fluency", "presentation_skills", "public_speaking",
    "leadership", "copywriting", "technical_writing", "seo",
    "video_editing", "graphic_design", "adobe_creative_suite", 
    "digital_marketing", "content_creation", "social_media_management",
    # Engineering / Hardware
    "robotics", "autocad", "hardware_design", "iot", "supply_chain"
]

# Tech-track interests — topic-based + activity-based
INTEREST_OPTIONS = [
    # Topic-based (existing)
    "Data Analysis", "Machine Learning", "Artificial Intelligence",
    "Web Development", "Software Development", "Cybersecurity",
    "Cloud Computing", "UX Design", "Product Management",
    "Mobile Development", "Game Development", "Database Administration",
    "Networking & Infrastructure", "DevOps & Automation", "Deep Learning",
    "Embedded Systems", "IoT", "Blockchain", "Robotics",
    "Hardware Engineering", "Data Engineering", "Enterprise Systems",
    "Quality Assurance",
    # Activity-based (new — maps to aptitude clusters in the rule engine)
    "Solving Puzzles & Logic", "Building Products", "Designing Interfaces",
    "Analyzing Data", "Securing Systems", "Working with Hardware", "Leading Teams",
]

# Tech-track majors only — non-CS engineering included because EEE/Mech have tech curricula
MAJOR_OPTIONS = [
    "Computer Science", "Software Engineering", "Information Technology",
    "Data Science", "Computer Engineering", "Cybersecurity",
    "Information Systems", "Mathematics & Statistics",
    "Electrical Engineering (EEE)", "Electronics & Communication Engineering",
    "Mechanical Engineering", "Biomedical Engineering",
    "Civil Engineering", "Chemical Engineering", "Other Tech Field",
]



@profile_bp.route("/background", methods=["GET", "POST"])
@login_required
def background():
    """Let the user choose Tech or Non-Tech background before profiling."""
    # If they already have a profile of either type, skip this step
    if current_user.profile:
        return redirect(url_for("career.results"))
    if current_user.nontech_profile:
        return redirect(url_for("nontech.intake"))

    if request.method == "POST":
        choice = request.form.get("background_type", "tech")
        session["background_type"] = choice
        if choice == "nontech":
            return redirect(url_for("nontech.intake"))
        return redirect(url_for("profile.setup"))

    return render_template("profile/background.html")


@profile_bp.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    if request.method == "POST":
        major = request.form.get("major", "").strip()
        semester = int(request.form.get("semester", 1))
        total_semesters = int(request.form.get("total_semesters", 8))
        location = request.form.get("location", "").strip()
        hours = int(request.form.get("hours_per_week", 10))
        interests = request.form.getlist("interests")
        skills = request.form.getlist("skills")
        proficiencies = request.form.getlist("proficiencies")

        # Create or update profile
        profile = current_user.profile
        if not profile:
            profile = Profile(user_id=current_user.id)
            db.session.add(profile)

        profile.major = major
        profile.semester = semester
        profile.total_semesters = total_semesters
        profile.location = location
        profile.hours_per_week = hours
        profile.set_interests(interests)

        # Update skills
        UserSkill.query.filter_by(profile_id=profile.id).delete() if profile.id else None
        db.session.flush()  # Ensure profile has an ID

        for i, skill in enumerate(skills):
            if skill:
                prof = proficiencies[i] if i < len(proficiencies) else "beginner"
                user_skill = UserSkill(
                    profile_id=profile.id,
                    skill_name=skill.lower().strip(),
                    proficiency=prof,
                )
                db.session.add(user_skill)

        db.session.commit()
        log_activity(current_user.id, "Updated Profile Preferences")
        flash("Profile saved! Now select your courses. 📚", "success")
        return redirect(url_for("profile.courses"))

    profile = current_user.profile
    existing_skills = []
    if profile and profile.skills:
        existing_skills = [(s.skill_name, s.proficiency) for s in profile.skills]

    return render_template(
        "profile/setup.html",
        profile=profile,
        available_skills=AVAILABLE_SKILLS,
        interest_options=INTEREST_OPTIONS,
        major_options=MAJOR_OPTIONS,
        existing_skills=existing_skills,
    )


@profile_bp.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    if not current_user.profile:
        flash("Please set up your profile first.", "warning")
        return redirect(url_for("profile.setup"))

    catalog = load_course_catalog()
    profile = current_user.profile

    if request.method == "POST":
        # Clear existing courses
        UserCourse.query.filter_by(profile_id=profile.id).delete()

        # Process selected courses
        for code, info in catalog.items():
            status = request.form.get(f"course_{code}")
            if status and status in ("completed", "in_progress", "upcoming"):
                course = UserCourse(
                    profile_id=profile.id,
                    course_code=code,
                    course_name=info["name"],
                    status=status,
                )
                db.session.add(course)

        db.session.commit()
        log_activity(current_user.id, "Updated Course Log")
        flash("Courses saved! Let's find your career path. 🎯", "success")
        return redirect(url_for("career.analyze"))

    # Determine which departments to show based on user's major
    major = profile.major or ""
    allowed_departments = {"Computer Science", "Mathematics", "Business"} # Core shared departments
    
    if "Mechanical" in major:
        allowed_departments.add("Mechanical Engineering")
    if "Electrical" in major or "EEE" in major:
        allowed_departments.add("Electrical Engineering")
    if "Electronics" in major or "Communication" in major:
        allowed_departments.add("Electronics Engineering")
    if "Cybersecurity" in major:
        allowed_departments.add("Cybersecurity")
    if "Data Science" in major:
        allowed_departments.add("Data Science")

    # Group filtered courses by semester for display, avoiding duplicates by name
    courses_by_semester = {}
    seen_names_by_sem = {}
    
    for code, info in catalog.items():
        dept = info.get("department", "Computer Science")
        if dept in allowed_departments:
            sem = info.get("semester", 0)
            name = info.get("name")
            
            if sem not in courses_by_semester:
                courses_by_semester[sem] = []
                seen_names_by_sem[sem] = set()
                
            if name not in seen_names_by_sem[sem]:
                courses_by_semester[sem].append({"code": code, **info})
                seen_names_by_sem[sem].add(name)

    # Get existing selections
    existing_courses = {}
    if profile.courses:
        for uc in profile.courses:
            existing_courses[uc.course_code] = uc.status

    return render_template(
        "profile/courses.html",
        courses_by_semester=dict(sorted(courses_by_semester.items())),
        existing_courses=existing_courses,
        current_semester=profile.semester,
    )
