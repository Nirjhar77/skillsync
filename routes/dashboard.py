from flask import Blueprint, render_template, redirect, url_for, jsonify, request as freq
from flask_login import login_required, current_user
from database.models import db, AptitudeProfile, Roadmap, Milestone, UserCourse, CareerPath, CareerScore, ActivityLog, log_activity
from engines.transferability_engine import compute_transferability
from engines.job_market_engine import get_job_pulse
from datetime import datetime, timedelta, date
import json
import requests as http_requests

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _json_list(value):
    try:
        data = json.loads(value) if value else []
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _skill_label(skill_key):
    words = str(skill_key or "").replace("-", "_").split("_")
    short_names = {
        "sql": "SQL",
        "ui": "UI",
        "ux": "UX",
        "api": "API",
        "aws": "AWS",
    }
    return " ".join(short_names.get(word.lower(), word.capitalize()) for word in words if word)


def _skill_matches(skill_key, skill_names):
    normalized_key = str(skill_key or "").lower().replace("_", " ").replace("-", " ")
    for name in skill_names:
        normalized_name = str(name or "").lower().replace("_", " ").replace("-", " ")
        if normalized_key == normalized_name or normalized_key in normalized_name or normalized_name in normalized_key:
            return True
    return False


def _required_value(meta):
    level = (meta or {}).get("level", "intermediate") if isinstance(meta, dict) else "intermediate"
    weight = float((meta or {}).get("weight", 0.7)) if isinstance(meta, dict) else 0.7
    level_floor = {"beginner": 58, "intermediate": 72, "advanced": 86}.get(str(level).lower(), 72)
    return max(48, min(96, round(level_floor + (weight * 10))))


def _build_career_trajectory(score):
    career = score.career_path if score else None
    required = career.get_required_skills() if career else {}
    required_items = sorted(
        required.items(),
        key=lambda item: float(item[1].get("weight", 0.5)) if isinstance(item[1], dict) else 0.5,
        reverse=True,
    )[:5]

    matched_skills = _json_list(score.matched_skills if score else None)
    gap_skills = _json_list(score.gap_skills if score else None)
    base_score = round(score.score) if score else 0

    if not required_items:
        fallback = ["Core Skills", "Portfolio", "Tools", "Communication", "Execution"]
        required_items = [(key, {"weight": 0.7, "level": "intermediate"}) for key in fallback]

    axes = []
    for skill_key, meta in required_items:
        required_pct = _required_value(meta)
        if _skill_matches(skill_key, matched_skills):
            user_pct = min(96, round(base_score + 12))
        elif _skill_matches(skill_key, gap_skills):
            user_pct = max(18, round(base_score - 28))
        else:
            weight = float(meta.get("weight", 0.6)) if isinstance(meta, dict) else 0.6
            user_pct = max(20, min(92, round(base_score * (0.58 + weight * 0.28))))
        axes.append({
            "key": skill_key,
            "label": _skill_label(skill_key),
            "user": user_pct,
            "required": required_pct,
        })

    focus = [_skill_label(skill) for skill in gap_skills[:3]]
    return {
        "title": career.title if career else "Finding your fit",
        "score": base_score,
        "skill_gap": max(0, 100 - base_score),
        "estimated_weeks": None,
        "is_active": False,
        "focus": focus,
        "axes": axes,
    }


@dashboard_bp.route("/")
@login_required
def index():
    if not current_user.profile and not current_user.nontech_profile:
        return redirect(url_for('profile.background'))

    is_nontech = bool(current_user.nontech_profile and not current_user.profile)

    # Log today's dashboard visit (drives streak calculation)
    log_activity(current_user.id, "Dashboard visit", "active")

    # â”€â”€ Roadmap data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    roadmaps = (
        Roadmap.query
        .filter_by(user_id=current_user.id)
        .order_by(Roadmap.created_at.asc())
        .all()
    )
    roadmaps_generated   = len(roadmaps)
    completed_milestones = sum(1 for r in roadmaps for m in r.milestones if m.completed)
    total_milestones     = sum(len(r.milestones) for r in roadmaps)
    resources_opened     = sum(1 for r in roadmaps for m in r.milestones if m.clicked)
    courses_enrolled     = UserCourse.query.filter_by(profile_id=current_user.profile.id).count() if current_user.profile else 0
    study_hours          = 10
    skills_verified      = 0

    # Milestones completed in the last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    milestones_this_week = sum(
        1 for r in roadmaps for m in r.milestones
        if m.completed and m.completed_at and m.completed_at >= week_ago
    )

    # â”€â”€ Active roadmap + next milestone â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    active_roadmap  = roadmaps[-1] if roadmaps else None
    next_milestone  = None
    next_milestones = []
    estimated_weeks = None
    active_career   = None

    if active_roadmap:
        if active_roadmap.career_path_id:
            active_career = db.session.get(CareerPath, active_roadmap.career_path_id)
        incomplete = [m for m in active_roadmap.milestones if not m.completed]
        if incomplete:
            next_milestone  = incomplete[0]
            next_milestones = incomplete[:5]
        try:
            if active_roadmap.content:
                content = json.loads(active_roadmap.content)
                estimated_weeks = content.get('estimated_total_weeks')
        except (json.JSONDecodeError, TypeError):
            estimated_weeks = None

    # â”€â”€ Mission impact per milestone â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    remaining          = total_milestones - completed_milestones
    mission_impact_pct = round(1 / total_milestones * 100, 1) if total_milestones > 0 else 0

    if is_nontech:
        study_hours     = current_user.nontech_profile.hours_per_week or 10
        skills_verified = len(current_user.nontech_profile.get_existing_skills())
        courses_enrolled = resources_opened
    elif current_user.profile:
        study_hours     = current_user.profile.hours_per_week or 10
        skills_verified = len(current_user.profile.skills)

    # â”€â”€ Career trajectories: ACTIVE career first, then suggestions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Step 1: Build the active career trajectory (user's selected roadmap path)
    career_trajectories = []
    strong_skills = []
    gap_focus = []
    skill_gap_pct = 0

    if active_roadmap and active_roadmap.career_path_id:
        active_score = CareerScore.query.filter_by(
            user_id=current_user.id,
            career_path_id=active_roadmap.career_path_id
        ).first()
        if active_score:
            skill_gap_pct = round(100 - active_score.score)
            try:
                strong_skills = (json.loads(active_score.matched_skills) or [])[:4]
            except (json.JSONDecodeError, TypeError):
                strong_skills = []

            # â”€â”€ Dynamic Next Focus: derived from the next incomplete milestones â”€â”€
            # This updates automatically as the user completes milestones,
            # rather than showing the stale static gap_skills from the AI analysis.
            if next_milestones:
                gap_focus = [m.title for m in next_milestones[:4]]
            else:
                # Roadmap fully complete â€” fall back to static AI gap_skills
                try:
                    gap_focus = (json.loads(active_score.gap_skills) or [])[:4]
                except (json.JSONDecodeError, TypeError):
                    gap_focus = []

            active_trajectory = _build_career_trajectory(active_score)
            active_trajectory["is_active"] = True
            active_trajectory["estimated_weeks"] = estimated_weeks
            # Inject the dynamic focus into the trajectory so the radar card also updates
            active_trajectory["focus"] = gap_focus
            career_trajectories.append(active_trajectory)
        else:
            # Roadmap exists but no CareerScore (AI-selected path) â€” build minimal entry
            active_trajectory = {
                "title": active_career.title if active_career else target_role,
                "score": 0,
                "skill_gap": 0,
                "estimated_weeks": estimated_weeks,
                "is_active": True,
                "focus": gap_focus,
                "axes": [],
            }
            career_trajectories.append(active_trajectory)

    # Step 2: Fill remaining slots from top career match scores (excluding active)
    active_career_path_id = active_roadmap.career_path_id if active_roadmap else None
    top_scores = (
        CareerScore.query
        .filter_by(user_id=current_user.id)
        .order_by(CareerScore.score.desc())
        .limit(6).all()
    )
    career_chart = []
    for cs in top_scores:
        if not cs.career_path:
            continue
        career_chart.append({"title": cs.career_path.title, "score": round(cs.score)})
        # Skip if already added as active career
        if cs.career_path_id == active_career_path_id:
            continue
        if len(career_trajectories) < 5:
            trajectory = _build_career_trajectory(cs)
            trajectory["is_active"] = False
            trajectory["estimated_weeks"] = None
            career_trajectories.append(trajectory)

    # Step 3: If no active roadmap, fall back to top scores list
    if not career_trajectories:
        for cs in top_scores:
            if not cs.career_path:
                continue
            trajectory = _build_career_trajectory(cs)
            trajectory["is_active"] = False
            career_trajectories.append(trajectory)
        career_chart = [{"title": cs.career_path.title, "score": round(cs.score)}
                        for cs in top_scores if cs.career_path]


    day_streak = 0
    check_date = date.today()
    while day_streak < 365:
        has = ActivityLog.query.filter(
            ActivityLog.user_id == current_user.id,
            db.func.date(ActivityLog.created_at) == str(check_date)
        ).first()
        if has:
            day_streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    last_log = (
        ActivityLog.query
        .filter_by(user_id=current_user.id)
        .order_by(ActivityLog.created_at.desc())
        .first()
    )
    last_active_days = (datetime.utcnow() - last_log.created_at).days if last_log else 0

    if day_streak >= 5:
        learning_status, learning_status_class = "On Track",    "status-on-track"
    elif day_streak >= 2:
        learning_status, learning_status_class = "Building",    "status-building"
    elif last_active_days <= 2:
        learning_status, learning_status_class = "Just Started", "status-building"
    elif last_active_days <= 5:
        learning_status, learning_status_class = "At Risk",     "status-at-risk"
    else:
        learning_status, learning_status_class = "Inactive",    "status-inactive"

    # â”€â”€ Weekly activity bars (real data, Mon=0 â€¦ Sun=6) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    week_start = date.today() - timedelta(days=date.today().weekday())  # Monday
    weekly_logs = ActivityLog.query.filter(
        ActivityLog.user_id == current_user.id,
        ActivityLog.created_at >= datetime.combine(week_start, datetime.min.time())
    ).all()
    raw_counts = [0] * 7
    for log in weekly_logs:
        day_idx = log.created_at.weekday()  # 0=Mon â€¦ 6=Sun
        raw_counts[day_idx] += 1
    max_count = max(raw_counts) or 1
    weekly_bars = [round((c / max_count) * 100) for c in raw_counts]  # 0â€“100 scale

    # â”€â”€ Career Transferability (proven-skill pivot scores) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Collects all completed milestones across all roadmaps, then runs the
    # transferability engine to show which OTHER careers the user could pivot
    # to based on skills they have actually proven â€” not day-1 self-assessments.
    all_completed_milestones = [
        m for r in roadmaps for m in r.milestones if m.completed
    ]
    all_career_paths = CareerPath.query.all()
    transferability_data = compute_transferability(
        completed_milestones=all_completed_milestones,
        all_career_paths=all_career_paths,
        active_career_path_id=active_career_path_id,
    )

    # â”€â”€ Job Market Pulse (TheirStack â†’ Remotive â†’ DB cache â†’ estimate) â”€â”€â”€â”€â”€
    job_pulse_data = None
    if active_career:
        try:
            job_pulse_data = get_job_pulse(active_career.title)
        except Exception:
            pass

    # â”€â”€ Recent Activity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    recent_activity = (
        ActivityLog.query
        .filter_by(user_id=current_user.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(5).all()
    )
    aptitude_profile = AptitudeProfile.query.filter_by(user_id=current_user.id).first()
    aptitude_state = aptitude_profile.to_dict() if aptitude_profile else {}

    # â”€â”€ UI strings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    target_role      = "Finding your fit" if is_nontech else "General Tech"
    salary_target    = "Depends on Role"
    profile_edit_url = url_for("nontech.intake") if is_nontech else url_for("profile.setup")
    navigator_url    = url_for("nontech.dashboard") if is_nontech else url_for("career.results")
    navigator_cta    = "Find My Path" if is_nontech else "Start Analysis"
    funnel_title     = "Learning Funnel" if is_nontech else "Skill Funnel"
    courses_label    = "Resources Opened" if is_nontech else "Courses Logged"
    skills_label     = "Skills Noted" if is_nontech else "Skills Verified"
    chart_title      = "Suggested Path Fit" if is_nontech else "Career Match Scores"
    chart_empty      = (
        "Choose a non-tech path to see your personalized learning direction here."
        if is_nontech
        else "Run a career analysis to see your match scores here."
    )

    # Smart action message
    if total_milestones == 0:
        action_message = "No roadmap yet â€” run a career analysis to get your personalised learning plan."
    elif milestones_this_week == 0:
        action_message = f"{remaining} milestone{'s' if remaining != 1 else ''} left. You haven't completed any this week â€” let's change that!"
    elif milestones_this_week >= 3:
        action_message = f"ðŸ”¥ Great week! {milestones_this_week} milestones done. {remaining} remaining â€” keep going!"
    else:
        action_message = f"{milestones_this_week} milestone{'s' if milestones_this_week != 1 else ''} done this week. {remaining} to go â€” you're making progress!"

    # Target role from latest roadmap
    if roadmaps:
        latest = roadmaps[-1]
        if latest.roadmap_type == "nontech" and current_user.nontech_profile:
            target_role   = current_user.nontech_profile.target_career or "Tech Professional"
            salary_target = "Varies by Role"
        elif latest.career_path:
            target_role   = latest.career_path.title
            salary_target = latest.career_path.avg_salary_range

    # Display name for the user's single active roadmap (metric card + panel context)
    active_roadmap_name = None
    if active_career:
        active_roadmap_name = active_career.title
    elif active_roadmap and active_roadmap.career_path_id:
        cp = active_roadmap.career_path or db.session.get(CareerPath, active_roadmap.career_path_id)
        if cp:
            active_roadmap_name = cp.title
    elif active_roadmap and is_nontech and current_user.nontech_profile:
        active_roadmap_name = current_user.nontech_profile.target_career
    elif target_role not in ("Finding your fit", "General Tech"):
        active_roadmap_name = target_role
    if not active_roadmap_name:
        active_roadmap_name = "Not started"

    # Career Flexibility card: proven pivots, or career-match preview when none yet
    ctf_display = list(transferability_data) if transferability_data else []
    ctf_is_preview = False
    if not ctf_display and career_chart:
        ctf_is_preview = True
        active_title = active_career.title if active_career else None
        for item in career_chart:
            if active_title and item.get("title") == active_title:
                continue
            ctf_display.append({
                "title": item["title"],
                "transferability": item["score"],
                "shared": 0,
                "required": 0,
            })
            if len(ctf_display) >= 4:
                break

    return render_template("dashboard/index.html",
        roadmaps_generated=roadmaps_generated,
        completed_milestones=completed_milestones,
        total_milestones=total_milestones,
        courses_enrolled=courses_enrolled,
        skills_verified=skills_verified,
        next_milestone=next_milestone,
        next_milestones=next_milestones,
        active_roadmap=active_roadmap,
        active_career=active_career,
        mission_impact_pct=mission_impact_pct,
        estimated_weeks=estimated_weeks,
        target_role=target_role,
        salary_target=salary_target,
        skill_gap_pct=skill_gap_pct,
        strong_skills=strong_skills,
        gap_focus=gap_focus,
        day_streak=day_streak,
        last_active_days=last_active_days,
        learning_status=learning_status,
        learning_status_class=learning_status_class,
        career_chart=career_chart,
        career_trajectories=career_trajectories,
        recent_activity=recent_activity,
        action_message=action_message,
        milestones_this_week=milestones_this_week,
        study_hours=study_hours,
        is_nontech=is_nontech,
        profile_edit_url=profile_edit_url,
        navigator_url=navigator_url,
        navigator_cta=navigator_cta,
        funnel_title=funnel_title,
        courses_label=courses_label,
        skills_label=skills_label,
        chart_title=chart_title,
        chart_empty=chart_empty,
        aptitude_state=aptitude_state,
        weekly_bars=weekly_bars,
        transferability_data=transferability_data,
        ctf_display=ctf_display,
        ctf_is_preview=ctf_is_preview,
        job_pulse_data=job_pulse_data,
        active_roadmap_name=active_roadmap_name,
        now=date.today(),
    )



@dashboard_bp.route("/api/skill-progress")
@login_required
def skill_progress_api():
    """Live skill progress: blends roadmap completion % with CareerScore weights.
    Called by the dashboard JS every 30 s for real-time bar updates."""
    from flask import jsonify

    roadmaps = (
        Roadmap.query
        .filter_by(user_id=current_user.id)
        .order_by(Roadmap.created_at.asc())
        .all()
    )
    active_roadmap = roadmaps[-1] if roadmaps else None

    completed = sum(1 for r in roadmaps for m in r.milestones if m.completed)
    total     = sum(len(r.milestones) for r in roadmaps)
    completion_pct = (completed / total * 100) if total > 0 else 0

    skills = []
    if active_roadmap and active_roadmap.career_path_id:
        active_score = CareerScore.query.filter_by(
            user_id=current_user.id,
            career_path_id=active_roadmap.career_path_id
        ).first()

        if active_score:
            career = active_score.career_path
            required_raw = career.get_required_skills() if career else {}
            required_items = sorted(
                required_raw.items(),
                key=lambda item: float(item[1].get("weight", 0.5)) if isinstance(item[1], dict) else 0.5,
                reverse=True
            )[:5]

            base_score    = round(active_score.score)
            matched_skills = _json_list(active_score.matched_skills)
            gap_skills     = _json_list(active_score.gap_skills)

            for skill_key, meta in required_items:
                weight       = float(meta.get("weight", 0.6)) if isinstance(meta, dict) else 0.6
                required_pct = _required_value(meta)

                # Base depends on whether this was a matched, gap, or neutral skill
                if _skill_matches(skill_key, matched_skills):
                    base = min(96, round(base_score + 12))
                elif _skill_matches(skill_key, gap_skills):
                    base = max(10, round(base_score - 28))
                else:
                    base = max(15, min(90, round(base_score * (0.58 + weight * 0.28))))

                # As roadmap milestones complete, skill grows from base â†’ required
                growth = (required_pct - base) * (completion_pct / 100) * (0.65 + weight * 0.35)
                current_pct = min(required_pct, round(base + growth))

                skills.append({
                    "label":    _skill_label(skill_key),
                    "current":  current_pct,
                    "required": required_pct,
                    "gap":      max(0, required_pct - current_pct),
                    "is_gap":   _skill_matches(skill_key, gap_skills),
                })

    return jsonify({
        "skills":               skills,
        "completion_pct":       round(completion_pct, 1),
        "completed_milestones": completed,
        "total_milestones":     total,
    })


@dashboard_bp.route("/start-now")
@login_required
def start_now():
    """Deep link: find the next incomplete milestone and go directly to its resource."""
    roadmaps = (
        Roadmap.query
        .filter_by(user_id=current_user.id)
        .order_by(Roadmap.created_at.desc())
        .all()
    )
    for roadmap in roadmaps:
        incomplete = [m for m in roadmap.milestones if not m.completed]
        if incomplete:
            milestone = incomplete[0]
            milestone.clicked = True
            db.session.commit()
            log_activity(current_user.id, f"Started: {milestone.title}", "active")
            if milestone.resource_url:
                return redirect(milestone.resource_url)
            return redirect(url_for('progress.tracker'))

    # No incomplete milestones â€” prompt to generate a new roadmap
    return redirect(url_for('career.results'))


@dashboard_bp.route("/api/transferability")
@login_required
def transferability_api():
    """
    Live Career Transferability scores.

    Returns the top matching alternate career paths (above 30% threshold)
    derived from the user's PROVEN skills (completed milestones), not the
    static day-1 CareerScore assessment.

    Called by the dashboard JS every 60s so the card updates immediately
    after a milestone is marked complete.

    Response shape:
    {
        "careers": [
            {
                "title":           "ML Engineer",
                "slug":            "ml_engineer",
                "transferability": 72,
                "shared":          5,
                "required":        7,
                "shared_skills":   ["python", "machine_learning", ...]
            },
            ...
        ],
        "proven_count": 8,    # total unique proven skill keys
        "active_path":  "ai_engineer"
    }
    """
    roadmaps = (
        Roadmap.query
        .filter_by(user_id=current_user.id)
        .order_by(Roadmap.created_at.asc())
        .all()
    )
    active_roadmap = roadmaps[-1] if roadmaps else None
    active_career_path_id = active_roadmap.career_path_id if active_roadmap else None

    all_completed = [m for r in roadmaps for m in r.milestones if m.completed]
    all_paths     = CareerPath.query.all()

    results = compute_transferability(
        completed_milestones=all_completed,
        all_career_paths=all_paths,
        active_career_path_id=active_career_path_id,
    )

    # Count unique proven skills for the UI badge
    from engines.transferability_engine import extract_skills_from_milestone
    proven = set()
    for m in all_completed:
        proven.update(extract_skills_from_milestone(m.title))

    active_slug = None
    if active_roadmap and active_roadmap.career_path_id:
        cp = db.session.get(CareerPath, active_roadmap.career_path_id)
        active_slug = cp.slug if cp else None

    return jsonify({
        "careers":       results,
        "proven_count":  len(proven),
        "active_path":   active_slug,
    })


@dashboard_bp.route("/api/job-pulse")
@login_required
def job_pulse_api():
    """
    Live job market intelligence for a career path.

    Query params:
        career  (str, optional) â€” career path title to look up.
                                  Defaults to the user's active path.

    Response:
    {
        "total_jobs":     31851,
        "remote_pct":     52,
        "top_skills":     [{"slug": "python", "label": "Python", "count": 18}, ...],
        "seniority":      "Mid Level",
        "companies":      [{"name": "Acme", "logo": "...", "domain": "acme.io"}, ...],
        "avg_salary_usd": 194450,
        "demand_label":   "High",
        "demand_color":   "#34d399",
        "career_title":   "AI Engineer",
        "cached_at_ts":   1715800000
    }
    """
    from flask import request as freq

    career_title = freq.args.get("career", "").strip()

    # Fall back to active career from latest roadmap
    if not career_title:
        roadmaps = (
            Roadmap.query
            .filter_by(user_id=current_user.id)
            .order_by(Roadmap.created_at.desc())
            .limit(1).all()
        )
        if roadmaps and roadmaps[0].career_path_id:
            cp = db.session.get(CareerPath, roadmaps[0].career_path_id)
            career_title = cp.title if cp else ""

    if not career_title:
        return jsonify({"error": "no active career path"}), 404

    force = freq.args.get("refresh", "").lower() in ("1", "true", "yes")

    try:
        data = get_job_pulse(career_title, force_refresh=force)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(data)


@dashboard_bp.route("/api/job-pulse/refresh", methods=["POST"])
@login_required
def job_pulse_refresh():
    """Force-refresh market data for the user's active career (or ?career=)."""
    from flask import request as freq

    career_title = (freq.get_json(silent=True) or {}).get("career", "")
    career_title = career_title or freq.args.get("career", "").strip()

    if not career_title:
        roadmaps = (
            Roadmap.query
            .filter_by(user_id=current_user.id)
            .order_by(Roadmap.created_at.desc())
            .limit(1).all()
        )
        if roadmaps and roadmaps[0].career_path_id:
            cp = db.session.get(CareerPath, roadmaps[0].career_path_id)
            career_title = cp.title if cp else ""

    if not career_title:
        return jsonify({"error": "no active career path"}), 404

    try:
        data = get_job_pulse(career_title, force_refresh=True)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(data)


# â”€â”€ Skill-Matched Job Notifications (Remotive API) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@dashboard_bp.route("/api/notifications")
@login_required
def notifications_api():
    """Return a contextual dashboard notification feed."""
    roadmaps = (
        Roadmap.query
        .filter_by(user_id=current_user.id)
        .order_by(Roadmap.created_at.desc())
        .limit(1).all()
    )
    active_roadmap = roadmaps[0] if roadmaps else None
    career_title = ""
    skill_keywords = []

    if active_roadmap and active_roadmap.career_path_id:
        cp = db.session.get(CareerPath, active_roadmap.career_path_id)
        if cp:
            career_title = cp.title
            try:
                skill_keywords = list((cp.get_required_skills() or {}).keys())[:5]
            except Exception:
                skill_keywords = []

    if current_user.profile:
        user_skill_names = [s.skill_name for s in current_user.profile.skills]
        skill_keywords = list(dict.fromkeys(skill_keywords + user_skill_names))[:8]

    def _posted_label(value):
        if not value:
            return "recent"
        try:
            posted = datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            days = max((datetime.utcnow() - posted).days, 0)
            if days == 0:
                return "today"
            if days == 1:
                return "1 day ago"
            return f"{days} days ago"
        except Exception:
            return "recent"

    search_query = career_title if career_title else (skill_keywords[0] if skill_keywords else "software engineer")
    search_query = search_query.replace(" Engineer", "").replace(" Developer", "").strip() or "software"
    job_error = ""
    try:
        resp = http_requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": search_query, "limit": 20},
            timeout=8,
        )
        resp.raise_for_status()
        jobs_raw = resp.json().get("jobs", [])
    except Exception as exc:
        jobs_raw = []
        job_error = str(exc)

    def _job_text(job):
        tags = job.get("tags", [])
        tag_text = " ".join(tags if isinstance(tags, list) else [str(tags)])
        return (job.get("title", "") + " " + tag_text + " " + job.get("description", "")[:600]).lower()

    def _relevance_score(job):
        text = _job_text(job)
        score = sum(2 for kw in skill_keywords if kw and kw.lower() in text)
        if career_title and any(part.lower() in text for part in career_title.split() if len(part) > 2):
            score += 1
        return score

    def _matched_terms(job):
        text = _job_text(job)
        matches = [_skill_label(kw) for kw in skill_keywords if kw and kw.lower() in text]
        return list(dict.fromkeys(matches))[:3]

    job_notifications = []
    for job in sorted(jobs_raw, key=_relevance_score, reverse=True)[:5]:
        tags = job.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        matched = _matched_terms(job)
        score = min(96, 62 + (_relevance_score(job) * 6))
        reason = (
            f"Matches {', '.join(matched)} from your roadmap/profile."
            if matched else
            f"Fresh remote role related to {career_title or search_query}."
        )
        job_notifications.append({
            "id": job.get("id"),
            "type": "job",
            "icon": "briefcase-business",
            "title": job.get("title", "Open Position"),
            "company": job.get("company_name", "Unknown Company"),
            "company_logo": job.get("company_logo", ""),
            "url": job.get("url", "#"),
            "tags": tags[:4],
            "posted_at": job.get("publication_date", ""),
            "posted_label": _posted_label(job.get("publication_date", "")),
            "source": "Remotive",
            "salary": job.get("salary", ""),
            "location": job.get("candidate_required_location", "Remote"),
            "job_type": job.get("job_type", "Remote"),
            "match_score": score,
            "reason": reason,
            "context": f"{score}% fit signal - {job.get('candidate_required_location', 'Remote')}",
            "action_label": "Open role",
            "priority": "Job match",
        })

    notifications = job_notifications[:8]
    return jsonify({
        "notifications": notifications,
        "career_title": career_title or search_query,
        "total_found": len(jobs_raw),
        "job_error": job_error,
        "skill_keywords": [_skill_label(skill) for skill in skill_keywords[:6]],
    })

