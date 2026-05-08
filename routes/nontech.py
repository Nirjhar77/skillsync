"""Non-Tech routes — Intake form and AI roadmap generation for non-tech background users."""

import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.models import db, NonTechProfile, Roadmap, Milestone
from engines.llm_engine import generate_nontech_roadmap, generate_career_suggestions

nontech_bp = Blueprint("nontech", __name__, url_prefix="/nontech")

# Career goals available to non-tech users entering tech
NONTECH_CAREER_OPTIONS = [
    "Digital Marketer / SEO Specialist",
    "Content Creator / YouTuber",
    "Graphic Designer",
    "UX/UI Designer",
    "Video Editor / Motion Graphics",
    "Social Media Manager",
    "Technical Writer",
    "Data Analyst (Business Focus)",
    "E-commerce Manager",
    "Product Manager",
    "IT Support Specialist",
    "Web Developer (No-Code / Low-Code)",
    "Cybersecurity Analyst",
    "Business Analyst",
    "Other (let AI decide)",
]

NONTECH_INTEREST_OPTIONS = [
    # Creative
    "Video Editing", "Graphic Design", "Photography", "Animation",
    "Music Production", "Creative Writing", "Storytelling",
    # Business & Marketing
    "Digital Marketing", "Social Media", "E-commerce", "Entrepreneurship",
    "Finance & Investing", "Business Strategy", "Sales",
    # Communication
    "Public Speaking", "Content Creation", "Blogging", "Copywriting",
    "Technical Writing", "Teaching & Education",
    # Tech-adjacent
    "Website Building", "Data & Numbers", "Gaming",
    "Hardware & Electronics", "Robotics", "3D Printing", "IoT",
]

NONTECH_SKILL_OPTIONS = [
    "Microsoft Office / Excel", "Video Editing (any tool)", "Graphic Design (Canva etc)",
    "Social Media Management", "Writing / Blogging", "Photography",
    "Basic Computer Skills", "English Language", "Customer Service",
    "Project Coordination", "Public Speaking / Presentation",
    "Research & Analysis", "Sales / Negotiation", "Teaching",
]

ENGLISH_LEVELS = ["Beginner", "Elementary", "Intermediate", "Upper-Intermediate", "Advanced", "Native / Fluent"]


@nontech_bp.route("/intake", methods=["GET", "POST"])
@login_required
def intake():
    """Non-tech intake form."""
    # If they've already done this and have a roadmap, redirect there
    existing = current_user.nontech_profile
    existing_roadmap = None
    if existing:
        existing_roadmap = Roadmap.query.filter_by(
            user_id=current_user.id, roadmap_type="nontech"
        ).order_by(Roadmap.created_at.desc()).first()
        if existing_roadmap and existing_roadmap.status == "approved":
            return redirect(url_for("nontech.roadmap_view", roadmap_id=existing_roadmap.id))

    if request.method == "POST":
        background_field = request.form.get("background_field", "").strip()
        interests = request.form.getlist("interests")
        existing_skills = request.form.getlist("existing_skills")
        hobbies = request.form.get("hobbies", "").strip()
        english_level = request.form.get("english_level", "Intermediate")
        hours_per_week = int(request.form.get("hours_per_week", 10))
        learning_goal = request.form.get("learning_goal", "").strip()

        # Save / update NonTechProfile
        profile = current_user.nontech_profile
        if not profile:
            profile = NonTechProfile(user_id=current_user.id)
            db.session.add(profile)

        profile.background_field = background_field
        # Target career is left blank initially. It will be set on the dashboard.
        profile.interests = json.dumps(interests)
        profile.existing_skills = json.dumps(existing_skills)
        profile.hobbies = hobbies
        profile.english_level = english_level
        profile.hours_per_week = hours_per_week
        profile.learning_goal = learning_goal

        db.session.commit()

        # Redirect to the new dashboard
        return redirect(url_for("nontech.dashboard"))

    return render_template(
        "nontech/intake.html",
        interest_options=NONTECH_INTEREST_OPTIONS,
        skill_options=NONTECH_SKILL_OPTIONS,
        english_levels=ENGLISH_LEVELS,
        profile=current_user.nontech_profile,
    )


@nontech_bp.route("/dashboard")
@login_required
def dashboard():
    """Show the Non-Tech AI Dashboard where users wait for suggestions."""
    if not current_user.nontech_profile:
        return redirect(url_for("nontech.intake"))
    
    # If they already have a target_career AND an approved roadmap, they don't need this dashboard unless they reset
    # But it's fine to show it anyway if they navigate here
    return render_template("nontech/dashboard.html", profile=current_user.nontech_profile)


@nontech_bp.route("/dashboard/generate_suggestions", methods=["POST"])
@login_required
def generate_suggestions():
    """API endpoint to generate career suggestions."""
    nt_profile = current_user.nontech_profile
    if not nt_profile:
        return jsonify({"error": "Profile not found"}), 404

    data, error = generate_career_suggestions(nt_profile)
    if error:
        return jsonify({"error": error}), 500

    return jsonify({"success": True, "suggestions": data.get("suggestions", [])})


@nontech_bp.route("/dashboard/select_career", methods=["POST"])
@login_required
def select_career():
    """API endpoint to save the selected career and initialize a roadmap generation."""
    nt_profile = current_user.nontech_profile
    if not nt_profile:
        return jsonify({"error": "Profile not found"}), 404

    data = request.get_json()
    chosen_career = data.get("career_title", "").strip()
    if not chosen_career:
        return jsonify({"error": "No career title provided"}), 400

    nt_profile.target_career = chosen_career

    # Create a new blank roadmap entry for this career
    roadmap = Roadmap(
        user_id=current_user.id,
        career_path_id=None,
        roadmap_type="nontech",
        content=None,
        status="generating",
    )
    db.session.add(roadmap)
    db.session.commit()

    return jsonify({
        "success": True, 
        "redirect": url_for("nontech.roadmap_generate", roadmap_id=roadmap.id)
    })


@nontech_bp.route("/roadmap/generate/<int:roadmap_id>")
@login_required
def roadmap_generate(roadmap_id):
    """Show loading screen while AI generates the roadmap."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        flash("Roadmap not found.", "error")
        return redirect(url_for("nontech.intake"))
    return render_template("nontech/roadmap.html", roadmap=roadmap, generating=True)


@nontech_bp.route("/roadmap/do_generate/<int:roadmap_id>", methods=["POST"])
@login_required
def do_generate(roadmap_id):
    """API endpoint — calls LLM to generate the roadmap."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Roadmap not found"}), 404

    nt_profile = current_user.nontech_profile
    if not nt_profile:
        return jsonify({"error": "Non-tech profile not found"}), 404

    roadmap_data, error = generate_nontech_roadmap(nt_profile)

    if error:
        roadmap.status = "error"
        roadmap.content = json.dumps({"error": error})
        db.session.commit()
        return jsonify({"error": error}), 500

    roadmap.content = json.dumps(roadmap_data)
    roadmap.status = "approved"

    # Create milestones
    for m in roadmap_data.get("milestones", []):
        milestone = Milestone(
            roadmap_id=roadmap.id,
            title=m.get("title", "Untitled"),
            description=m.get("description", ""),
            resource_url=m.get("resource_url", ""),
            resource_type=m.get("resource_type", "article"),
            estimated_hours=m.get("estimated_hours", 1),
            order=m.get("order", 0),
        )
        db.session.add(milestone)

    db.session.commit()

    return jsonify({
        "success": True,
        "redirect": url_for("nontech.roadmap_view", roadmap_id=roadmap.id),
    })


@nontech_bp.route("/roadmap/<int:roadmap_id>")
@login_required
def roadmap_view(roadmap_id):
    """View completed non-tech roadmap."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        flash("Roadmap not found.", "error")
        return redirect(url_for("nontech.intake"))

    roadmap_data = json.loads(roadmap.content) if roadmap.content else {}
    nt_profile = current_user.nontech_profile

    total = len(roadmap.milestones)
    completed = sum(1 for m in roadmap.milestones if m.completed)
    progress = int((completed / total) * 100) if total > 0 else 0

    return render_template(
        "nontech/roadmap.html",
        roadmap=roadmap,
        roadmap_data=roadmap_data,
        nt_profile=nt_profile,
        generating=False,
        progress=progress,
        completed_count=completed,
        total_count=total,
    )
