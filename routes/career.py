"""Career routes — Analyze, view results, select career, generate roadmap."""

import json
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.models import db, CareerPath, CareerScore, Roadmap, Milestone, UserCourse, CareerProject, log_activity
from engines.rule_engine import rank_careers
from engines.llm_engine import generate_roadmap, generate_tech_career_suggestions, generate_visual_guide, explain_topic, generate_career_projects
from engines.decision_engine import compare_careers

career_bp = Blueprint("career", __name__, url_prefix="/career")

# Minimum score to include a career path in results (filters out irrelevant 0% matches)
MIN_SCORE_THRESHOLD = 5


def _clean_phase_copy(phase_number, title, description=""):
    """Keep generated phase labels concise and dashboard-friendly."""
    clean_title = (title or "").strip()
    clean_desc = (description or "").strip()
    title_l = clean_title.lower()

    if phase_number == 4 or ("portfolio" in title_l and "project" in title_l):
        clean_title = "Portfolio"
        if not clean_desc or "portfolio of projects" in clean_desc.lower():
            clean_desc = "Build and present projects that prove your skills."

    return clean_title or f"Phase {phase_number}", clean_desc


@career_bp.route("/analyze")
@login_required
def analyze():
    """Run the rule engine and redirect to results."""
    profile = current_user.profile
    if not profile:
        flash("Please set up your profile first.", "warning")
        return redirect(url_for("profile.setup"))

    if not profile.courses:
        flash("Please select your courses first.", "warning")
        return redirect(url_for("profile.courses"))

    # Get all career paths
    career_paths = CareerPath.query.all()
    if not career_paths:
        flash("No career paths found. Please seed the database.", "error")
        return redirect(url_for("profile.setup"))

    # Run rule engine
    user_courses = profile.courses
    results = rank_careers(profile, career_paths, user_courses)

    # Save scores to database — skip careers with 0 or negligible scores
    CareerScore.query.filter_by(user_id=current_user.id).delete()
    saved_count = 0
    for career, details in results:
        if details.get("signal_score", details["score"]) < MIN_SCORE_THRESHOLD:
            continue  # Don't persist meaningless matches
        score = CareerScore(
            user_id=current_user.id,
            career_path_id=career.id,
            score=details["score"],
            matched_skills=json.dumps(details["matched_skills"]),
            gap_skills=json.dumps(details["gap_skills"]),
            curriculum_covered=json.dumps(details["covered_by_curriculum"]),
        )
        db.session.add(score)
        saved_count += 1

    db.session.commit()
    return redirect(url_for("career.results"))


@career_bp.route("/results")
@login_required
def results():
    """Display ranked career paths grouped into smart fit categories."""
    profile = current_user.profile
    if not profile:
        return redirect(url_for("profile.setup"))

    scores = (
        CareerScore.query.filter_by(user_id=current_user.id)
        .order_by(CareerScore.score.desc())
        .all()
    )

    # Build enriched results list
    career_results = []
    for cs in scores:
        career = cs.career_path
        career_results.append({
            "career": career,
            "score": cs.score,
            "matched_skills": json.loads(cs.matched_skills) if cs.matched_skills else [],
            "gap_skills": json.loads(cs.gap_skills) if cs.gap_skills else [],
            "curriculum_covered": json.loads(cs.curriculum_covered) if cs.curriculum_covered else {},
        })

    # ── Categorise into 4 smart buckets ──────────────────────────────
    # Thresholds are relative to the top score so they adapt to the user's profile
    top_score = career_results[0]["score"] if career_results else 100

    best_fit      = []   # score >= 65% OR within 10 pts of top score
    adjacent_fit  = []   # score 40–64
    stretch_path  = []   # score 20–39
    wildcard      = []   # score 10–19 — show max 2

    for r in career_results:
        s = r["score"]
        if s >= 65 or (top_score > 0 and s >= top_score * 0.85):
            best_fit.append(r)
        elif s >= 40:
            adjacent_fit.append(r)
        elif s >= 20:
            stretch_path.append(r)
        elif s >= 10 and len(wildcard) < 2:
            wildcard.append(r)

    return render_template(
        "career/results.html",
        results=career_results,       # kept for backward compat (compare btn etc.)
        best_fit=best_fit,
        adjacent_fit=adjacent_fit,
        stretch_path=stretch_path,
        wildcard=wildcard,
        profile=profile,
    )


@career_bp.route("/roadmap/<int:roadmap_id>/guide")
@login_required
def guide_view(roadmap_id):
    """Render the Visual Guide — roadmap.sh-style interactive node graph."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        flash("Roadmap not found.", "error")
        return redirect(url_for("career.results"))

    career = db.session.get(CareerPath, roadmap.career_path_id)

    # Parse guide content; generate on-demand if missing (old roadmaps)
    guide_data = {}
    needs_generation = False
    if roadmap.guide_content:
        try:
            guide_data = json.loads(roadmap.guide_content)
        except Exception:
            needs_generation = True
    else:
        needs_generation = True

    return render_template(
        "career/guide.html",
        roadmap=roadmap,
        career=career,
        guide_data=guide_data,
        needs_generation=needs_generation,
    )


@career_bp.route("/roadmap/<int:roadmap_id>/guide/generate", methods=["POST"])
@login_required
def guide_generate(roadmap_id):
    """On-demand guide generation for old roadmaps that don't have guide_content."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404

    career = db.session.get(CareerPath, roadmap.career_path_id)
    guide_data, error = generate_visual_guide(career)
    if error:
        return jsonify({"error": error}), 500

    roadmap.guide_content = json.dumps(guide_data)
    db.session.commit()
    return jsonify({"success": True})


@career_bp.route("/roadmap/<int:roadmap_id>/explain-topic", methods=["POST"])
@login_required
def explain_topic_api(roadmap_id):
    """Live AI explanation when user clicks a topic node in the Visual Guide."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404

    career = db.session.get(CareerPath, roadmap.career_path_id)
    body = request.get_json() or {}
    topic_label   = body.get("topic", "").strip()
    section_label = body.get("section", "").strip()

    if not topic_label:
        return jsonify({"error": "No topic provided"}), 400

    explanation, error = explain_topic(career.title, topic_label, section_label)
    if error:
        return jsonify({"error": error}), 500

    return jsonify(explanation)
@career_bp.route("/overview/<int:career_id>")
@login_required
def overview(career_id):
    """Show AI-generated detailed overview of a specific career."""
    career_path = CareerPath.query.get_or_404(career_id)
    
    from engines.llm_engine import analyze_career_overview
    overview_data, error = analyze_career_overview(career_path)
    
    if error:
        flash(f"Failed to generate career insights: {error}", "danger")
        return redirect(url_for('career.results'))
        
    return render_template(
        "career/overview.html",
        career=career_path,
        overview_data=overview_data
    )

@career_bp.route("/ai_suggest", methods=["POST"])
@login_required
def ai_suggest():
    """Generate AI-powered custom career suggestions for a Tech user."""
    profile = current_user.profile
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    data, error = generate_tech_career_suggestions(profile, profile.courses)
    if error:
        return jsonify({"error": error}), 500

    return jsonify({"success": True, "suggestions": data.get("suggestions", [])})


@career_bp.route("/ai_select", methods=["POST"])
@login_required
def ai_select():
    """Handle selection of an AI-suggested custom career path."""
    profile = current_user.profile
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    data = request.get_json()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()

    if not title:
        return jsonify({"error": "Missing career title"}), 400

    # Check if this exact title already exists
    existing_path = CareerPath.query.filter_by(title=title).first()
    
    if not existing_path:
        # Generate a slug from the title (e.g. "AI Engineer" → "ai_engineer")
        import re
        auto_slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        new_path = CareerPath(
            slug=auto_slug,
            title=title,
            description=description,
            required_skills="{}",
            recommended_tools="[]",
            avg_salary_range="Varies",
            growth_outlook="High",
        )
        db.session.add(new_path)
        db.session.flush()  # Get ID
        career_path_id = new_path.id
    else:
        career_path_id = existing_path.id

    # Create generating roadmap entry
    roadmap = Roadmap(
        user_id=current_user.id,
        career_path_id=career_path_id,
        roadmap_type="tech",
        content=None,
        status="generating",
    )
    db.session.add(roadmap)
    db.session.commit()

    return jsonify({
        "success": True,
        "redirect": url_for("career.roadmap_generate", roadmap_id=roadmap.id)
    })


@career_bp.route("/select/<int:career_id>", methods=["POST"])
@login_required
def select(career_id):
    """Select a career path and trigger roadmap generation."""
    career = db.session.get(CareerPath, career_id)
    if not career:
        flash("Career path not found.", "error")
        return redirect(url_for("career.results"))

    profile = current_user.profile

    # Get the score details for this career
    cs = CareerScore.query.filter_by(
        user_id=current_user.id, career_path_id=career_id
    ).first()

    if not cs:
        flash("Please analyze your career matches first.", "warning")
        return redirect(url_for("career.analyze"))

    score_details = {
        "score": cs.score,
        "matched_skills": json.loads(cs.matched_skills) if cs.matched_skills else [],
        "gap_skills": json.loads(cs.gap_skills) if cs.gap_skills else [],
        "covered_by_curriculum": json.loads(cs.curriculum_covered) if cs.curriculum_covered else {},
    }

    # Create a roadmap entry with "generating" status
    roadmap = Roadmap(
        user_id=current_user.id,
        career_path_id=career_id,
        content=None,
        status="generating",
    )
    db.session.add(roadmap)
    db.session.commit()

    return redirect(url_for("career.roadmap_generate", roadmap_id=roadmap.id))


@career_bp.route("/roadmap/generate/<int:roadmap_id>")
@login_required
def roadmap_generate(roadmap_id):
    """Show loading screen and generate roadmap."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        flash("Roadmap not found.", "error")
        return redirect(url_for("career.results"))

    career = db.session.get(CareerPath, roadmap.career_path_id)
    return render_template(
        "career/roadmap.html",
        roadmap=roadmap,
        career=career,
        generating=True,
    )


@career_bp.route("/roadmap/do_generate/<int:roadmap_id>", methods=["POST"])
@login_required
def do_generate(roadmap_id):
    """API endpoint that actually calls Gemini to generate the roadmap."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Roadmap not found"}), 404

    profile = current_user.profile
    career = db.session.get(CareerPath, roadmap.career_path_id)

    # Get score details
    cs = CareerScore.query.filter_by(
        user_id=current_user.id, career_path_id=roadmap.career_path_id
    ).first()

    score_details = {
        "score": cs.score if cs else 0,
        "matched_skills": json.loads(cs.matched_skills) if cs and cs.matched_skills else [],
        "gap_skills": json.loads(cs.gap_skills) if cs and cs.gap_skills else [],
        "covered_by_curriculum": json.loads(cs.curriculum_covered) if cs and cs.curriculum_covered else {},
    }

    # We must preserve the app context for the threads since llm_engine uses current_app
    from flask import current_app
    app = current_app._get_current_object()

    def run_roadmap():
        with app.app_context():
            return generate_roadmap(profile, career, score_details, profile.courses)

    def run_guide():
        with app.app_context():
            return generate_visual_guide(career)

    # Generate roadmap AND visual guide in parallel (two Groq calls simultaneously)
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_roadmap = executor.submit(run_roadmap)
        future_guide   = executor.submit(run_guide)
        roadmap_data, error      = future_roadmap.result()
        guide_data,   guide_error = future_guide.result()

    if error:
        roadmap.status = "error"
        roadmap.content = json.dumps({"error": error})
        db.session.commit()
        return jsonify({"error": error}), 500

    # Save both results
    roadmap.content = json.dumps(roadmap_data)
    roadmap.status  = "approved"
    if guide_data:
        roadmap.guide_content = json.dumps(guide_data)

    projects_data, project_error = generate_career_projects(profile, career, roadmap_data)

    Milestone.query.filter_by(roadmap_id=roadmap.id).delete()
    CareerProject.query.filter_by(roadmap_id=roadmap.id).delete()

    # Create milestone records — new phase-based structure
    phases = roadmap_data.get("phases", [])
    global_order = 1

    if phases:
        # New phase-based format from updated AI prompt
        for phase in phases:
            p_num = phase.get("phase_number", 1)
            p_title = phase.get("phase_title", "Phase")
            p_desc = phase.get("phase_description", "")
            p_title, p_desc = _clean_phase_copy(p_num, p_title, p_desc)
            for m in phase.get("milestones", []):
                milestone = Milestone(
                    roadmap_id=roadmap.id,
                    title=m.get("title", "Untitled"),
                    description=m.get("description", ""),
                    resource_url=m.get("resource_url", ""),
                    resource_type=m.get("resource_type", "article"),
                    estimated_hours=m.get("estimated_hours", 1),
                    order=global_order,
                    phase_number=p_num,
                    phase_title=p_title,
                    phase_description=p_desc,
                    card_type=m.get("card_type", "core"),
                    learning_goal=m.get("learning_goal", ""),
                    success_criteria=m.get("success_criteria", ""),
                    practice_tasks=json.dumps(m.get("practice_tasks", [])),
                    resource_title=m.get("resource_title", ""),
                    requires=m.get("requires", ""),
                    unlocks=m.get("unlocks", ""),
                )
                db.session.add(milestone)
                global_order += 1
    else:
        # Fallback: old flat milestones format (backward-compat)
        for m in roadmap_data.get("milestones", []):
            milestone = Milestone(
                roadmap_id=roadmap.id,
                title=m.get("title", "Untitled"),
                description=m.get("description", ""),
                resource_url=m.get("resource_url", ""),
                resource_type=m.get("resource_type", "article"),
                estimated_hours=m.get("estimated_hours", 1),
                order=m.get("order", global_order),
                phase_number=1,
                phase_title="Roadmap",
                card_type=m.get("card_type", "core"),
                learning_goal=m.get("learning_goal", ""),
                success_criteria=m.get("success_criteria", ""),
                practice_tasks=json.dumps(m.get("practice_tasks", [])),
                resource_title=m.get("resource_title", ""),
                requires=m.get("requires", ""),
                unlocks=m.get("unlocks", ""),
            )
            db.session.add(milestone)
            global_order += 1

    if projects_data and not project_error:
        for idx, p in enumerate(projects_data.get("projects", []), start=1):
            db.session.add(CareerProject(
                user_id=current_user.id,
                roadmap_id=roadmap.id,
                career_path_id=career.id,
                title=p.get("title", "Career Project"),
                difficulty=p.get("difficulty", "beginner"),
                summary=p.get("summary", ""),
                features=json.dumps(p.get("features", [])),
                skills_used=json.dumps(p.get("skills_used", [])),
                deliverables=json.dumps(p.get("deliverables", [])),
                resource_url=p.get("resource_url", ""),
                estimated_hours=p.get("estimated_hours", 8),
                portfolio_value=p.get("portfolio_value", ""),
                order=p.get("order", idx),
            ))

    db.session.commit()
    log_activity(current_user.id, f"Generated {career.title} Roadmap")

    return jsonify({
        "success": True,
        "redirect": (
            url_for("career.roadmap_view", roadmap_id=roadmap.id)
            if request.args.get("return") == "start"
            else url_for("career.guide_view", roadmap_id=roadmap.id)
        ),
    })


@career_bp.route("/roadmap/<int:roadmap_id>")
@login_required
def roadmap_view(roadmap_id):
    """View a completed roadmap."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        flash("Roadmap not found.", "error")
        return redirect(url_for("career.results"))

    career = db.session.get(CareerPath, roadmap.career_path_id)
    roadmap_data = json.loads(roadmap.content) if roadmap.content else {}

    # Calculate progress
    total = len(roadmap.milestones)
    completed = sum(1 for m in roadmap.milestones if m.completed)
    progress = int((completed / total) * 100) if total > 0 else 0

    # Group milestones by phase
    from collections import OrderedDict
    phases = OrderedDict()
    phase_meta = {
        (p.get("phase_number") or idx): p
        for idx, p in enumerate(roadmap_data.get("phases", []), start=1)
        if isinstance(p, dict)
    }
    for m in roadmap.milestones:
        key = m.phase_number or 1
        meta = phase_meta.get(key, {})
        phase_title, phase_description = _clean_phase_copy(
            key,
            m.phase_title or meta.get("phase_title", f"Phase {key}"),
            m.phase_description or meta.get("phase_description", ""),
        )
        if key not in phases:
            phases[key] = {
                "phase_number": key,
                "phase_title": phase_title,
                "phase_description": phase_description,
                "learning_goals": meta.get("learning_goals", []),
                "key_skills": meta.get("key_skills", []),
                "phase_resources": meta.get("phase_resources", []),
                "milestones": [],
            }
        phases[key]["milestones"].append(m)

    # ── New vars for redesigned page ──────────────────────────────────
    # Find the first incomplete milestone (drives the "You are here" sticky)
    next_milestone = None
    current_phase_data = None
    for m in roadmap.milestones:
        if not m.completed:
            next_milestone = m
            break

    # Find which phase dict that milestone belongs to
    if next_milestone and next_milestone.phase_number in phases:
        current_phase_data = phases[next_milestone.phase_number]

    # Outcome fields — new LLM fields, fall back gracefully for old roadmaps
    outcome_roles     = roadmap_data.get("outcome_roles", [])
    readiness_start   = roadmap_data.get("readiness_start", None)
    readiness_end     = roadmap_data.get("readiness_end", None)
    hero_subtitle     = roadmap_data.get("hero_subtitle", roadmap_data.get("summary", ""))
    projects_preview  = CareerProject.query.filter_by(
        user_id=current_user.id,
        roadmap_id=roadmap.id,
    ).order_by(CareerProject.order.asc()).limit(9).all()

    return render_template(
        "career/roadmap.html",
        roadmap=roadmap,
        career=career,
        roadmap_data=roadmap_data,
        generating=False,
        progress=progress,
        completed_count=completed,
        total_count=total,
        phases=phases,
        # New context vars
        next_milestone=next_milestone,
        current_phase_data=current_phase_data,
        outcome_roles=outcome_roles,
        readiness_start=readiness_start,
        readiness_end=readiness_end,
        hero_subtitle=hero_subtitle,
        projects_preview=projects_preview,
    )


@career_bp.route("/projects")
@login_required
def projects_latest():
    """Show projects for the user's most recent selected career roadmap."""
    roadmap = (
        Roadmap.query.filter_by(user_id=current_user.id, status="approved")
        .filter(Roadmap.career_path_id.isnot(None))
        .order_by(Roadmap.created_at.desc())
        .first()
    )
    if not roadmap:
        flash("Generate or select a career roadmap first.", "warning")
        return redirect(url_for("career.results"))
    return redirect(url_for("career.projects_view", roadmap_id=roadmap.id))


@career_bp.route("/projects/<int:roadmap_id>")
@login_required
def projects_view(roadmap_id):
    """Career-specific portfolio project board."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        flash("Roadmap not found.", "error")
        return redirect(url_for("career.results"))

    career = db.session.get(CareerPath, roadmap.career_path_id)
    projects = CareerProject.query.filter_by(
        user_id=current_user.id,
        roadmap_id=roadmap.id,
    ).order_by(CareerProject.order.asc()).all()

    grouped_projects = {"beginner": [], "intermediate": [], "advanced": []}
    for project in projects:
        key = (project.difficulty or "beginner").lower()
        if key not in grouped_projects:
            key = "beginner"
        grouped_projects[key].append(project)

    return render_template(
        "career/projects.html",
        roadmap=roadmap,
        career=career,
        projects=projects,
        grouped_projects=grouped_projects,
    )


@career_bp.route("/projects/<int:roadmap_id>/generate", methods=["POST"])
@login_required
def projects_generate(roadmap_id):
    """Generate or refresh project ideas for an existing roadmap."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Roadmap not found"}), 404

    profile = current_user.profile
    career = db.session.get(CareerPath, roadmap.career_path_id)
    roadmap_data = json.loads(roadmap.content) if roadmap.content else {}
    projects_data, error = generate_career_projects(profile, career, roadmap_data)
    if error:
        return jsonify({"error": error}), 500

    CareerProject.query.filter_by(roadmap_id=roadmap.id).delete()
    for idx, p in enumerate(projects_data.get("projects", []), start=1):
        db.session.add(CareerProject(
            user_id=current_user.id,
            roadmap_id=roadmap.id,
            career_path_id=career.id,
            title=p.get("title", "Career Project"),
            difficulty=p.get("difficulty", "beginner"),
            summary=p.get("summary", ""),
            features=json.dumps(p.get("features", [])),
            skills_used=json.dumps(p.get("skills_used", [])),
            deliverables=json.dumps(p.get("deliverables", [])),
            resource_url=p.get("resource_url", ""),
            estimated_hours=p.get("estimated_hours", 8),
            portfolio_value=p.get("portfolio_value", ""),
            order=p.get("order", idx),
        ))
    db.session.commit()
    return jsonify({"success": True, "redirect": url_for("career.projects_view", roadmap_id=roadmap.id)})


@career_bp.route("/projects/<int:project_id>/complete", methods=["POST"])
@login_required
def project_complete(project_id):
    project = db.session.get(CareerProject, project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({"error": "Project not found"}), 404
    project.completed = not project.completed
    db.session.commit()
    return jsonify({"success": True, "completed": project.completed})


@career_bp.route("/compare")
@login_required
def compare():
    """Career comparison: side-by-side decision engine."""
    profile = current_user.profile
    if not profile:
        return redirect(url_for("profile.setup"))

    # Load all scores for this user
    scores = (
        CareerScore.query.filter_by(user_id=current_user.id)
        .order_by(CareerScore.score.desc())
        .all()
    )

    if not scores:
        flash("Please run a career analysis first.", "warning")
        return redirect(url_for("career.analyze"))

    # Build a quick lookup: career_path_id -> score_details
    score_map = {}
    for cs in scores:
        score_map[cs.career_path_id] = {
            "score": cs.score,
            "matched_skills": json.loads(cs.matched_skills) if cs.matched_skills else [],
            "gap_skills": json.loads(cs.gap_skills) if cs.gap_skills else [],
            "covered_by_curriculum": json.loads(cs.curriculum_covered) if cs.curriculum_covered else {},
        }

    # All career paths the user has scores for (for the selector dropdowns)
    scored_careers = [cs.career_path for cs in scores]

    comparison = None
    slug_a = request.args.get("a")
    slug_b = request.args.get("b")

    if slug_a and slug_b and slug_a != slug_b:
        career_a = CareerPath.query.filter_by(slug=slug_a).first()
        career_b = CareerPath.query.filter_by(slug=slug_b).first()

        if career_a and career_b:
            score_a = score_map.get(career_a.id, {"score": 0, "matched_skills": [], "gap_skills": [], "covered_by_curriculum": {}})
            score_b = score_map.get(career_b.id, {"score": 0, "matched_skills": [], "gap_skills": [], "covered_by_curriculum": {}})
            comparison = compare_careers(profile, career_a, career_b, score_a, score_b)

    return render_template(
        "career/compare.html",
        scored_careers=scored_careers,
        comparison=comparison,
        selected_a=slug_a,
        selected_b=slug_b,
        profile=profile,
    )
