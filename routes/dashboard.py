from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from database.models import db, Roadmap, Milestone, UserCourse, CareerPath, CareerScore, ActivityLog, log_activity
from datetime import datetime, timedelta, date
import json

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    if not current_user.profile and not current_user.nontech_profile:
        return redirect(url_for('profile.background'))

    is_nontech = bool(current_user.nontech_profile and not current_user.profile)

    # Log today's dashboard visit (drives streak calculation)
    log_activity(current_user.id, "Dashboard visit", "active")

    # ── Roadmap data ──────────────────────────────────────────────────────────
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

    # ── Active roadmap + next milestone ──────────────────────────────────────
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

    # ── Mission impact per milestone ──────────────────────────────────────────
    remaining          = total_milestones - completed_milestones
    mission_impact_pct = round(1 / total_milestones * 100, 1) if total_milestones > 0 else 0

    if is_nontech:
        study_hours     = current_user.nontech_profile.hours_per_week or 10
        skills_verified = len(current_user.nontech_profile.get_existing_skills())
        courses_enrolled = resources_opened
    elif current_user.profile:
        study_hours     = current_user.profile.hours_per_week or 10
        skills_verified = len(current_user.profile.skills)

    # ── Career match scores + skill gap ──────────────────────────────────────
    top_scores = (
        CareerScore.query
        .filter_by(user_id=current_user.id)
        .order_by(CareerScore.score.desc())
        .limit(5).all()
    )
    career_chart = [
        {"title": cs.career_path.title, "score": round(cs.score)}
        for cs in top_scores if cs.career_path
    ]

    active_score      = None
    strong_skills     = []
    gap_focus         = []
    skill_gap_pct     = 0

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
            try:
                gap_focus = (json.loads(active_score.gap_skills) or [])[:4]
            except (json.JSONDecodeError, TypeError):
                gap_focus = []

    # ── Day streak (computed from ActivityLog, no migration needed) ───────────
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

    # ── Recent Activity ───────────────────────────────────────────────────────
    recent_activity = (
        ActivityLog.query
        .filter_by(user_id=current_user.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(5).all()
    )

    # ── UI strings ────────────────────────────────────────────────────────────
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
        action_message = "No roadmap yet — run a career analysis to get your personalised learning plan."
    elif milestones_this_week == 0:
        action_message = f"{remaining} milestone{'s' if remaining != 1 else ''} left. You haven't completed any this week — let's change that!"
    elif milestones_this_week >= 3:
        action_message = f"🔥 Great week! {milestones_this_week} milestones done. {remaining} remaining — keep going!"
    else:
        action_message = f"{milestones_this_week} milestone{'s' if milestones_this_week != 1 else ''} done this week. {remaining} to go — you're making progress!"

    # Target role from latest roadmap
    if roadmaps:
        latest = roadmaps[-1]
        if latest.roadmap_type == "nontech" and current_user.nontech_profile:
            target_role   = current_user.nontech_profile.target_career or "Tech Professional"
            salary_target = "Varies by Role"
        elif latest.career_path:
            target_role   = latest.career_path.title
            salary_target = latest.career_path.avg_salary_range

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
    )


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

    # No incomplete milestones — prompt to generate a new roadmap
    return redirect(url_for('career.results'))
