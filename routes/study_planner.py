"""Study Planner routes — Log study sessions and get AI weekly check-ins."""

from datetime import date, datetime, timedelta
from collections import defaultdict

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from database.models import Milestone, Roadmap, StudySession, db
from engines.llm_engine import generate_weekly_checkin

study_planner_bp = Blueprint("study_planner", __name__, url_prefix="/study-planner")


@study_planner_bp.route("/")
@login_required
def index():
    """Main Study Planner page."""
    roadmap = (
        Roadmap.query.filter_by(user_id=current_user.id, status="approved")
        .order_by(Roadmap.created_at.desc())
        .first()
    )

    milestones = []
    career = None
    if roadmap:
        career = roadmap.career_path
        milestones = roadmap.milestones  # ordered by Milestone.order

    # Fetch all sessions for this user, newest first
    sessions_all = (
        StudySession.query.filter_by(user_id=current_user.id)
        .order_by(StudySession.session_date.desc(), StudySession.created_at.desc())
        .all()
    )

    # Group sessions by date string for the timeline
    sessions_by_date = defaultdict(list)
    for s in sessions_all:
        key = s.session_date.strftime("%B %d, %Y")
        sessions_by_date[key].append(s)

    # Stats
    total_hours = sum(s.hours_logged for s in sessions_all)
    total_sessions = len(sessions_all)

    week_start = date.today() - timedelta(days=date.today().weekday())
    sessions_this_week_list = [s for s in sessions_all if s.session_date >= week_start]
    hours_this_week = sum(s.hours_logged for s in sessions_this_week_list)

    avg_hours = round(total_hours / total_sessions, 1) if total_sessions > 0 else 0

    return render_template(
        "study_planner/index.html",
        roadmap=roadmap,
        career=career,
        milestones=milestones,
        sessions_by_date=dict(sessions_by_date),
        total_hours=round(total_hours, 1),
        total_sessions=total_sessions,
        hours_this_week=round(hours_this_week, 1),
        avg_hours=avg_hours,
        today=date.today().isoformat(),
    )


@study_planner_bp.route("/log", methods=["POST"])
@login_required
def log_session():
    """Log a new study session."""
    data = request.get_json() or {}

    roadmap_id = data.get("roadmap_id")
    milestone_id = data.get("milestone_id") or None
    hours = float(data.get("hours", 1.0))
    notes = (data.get("notes") or "").strip()
    session_date_str = data.get("session_date", date.today().isoformat())

    if not roadmap_id:
        return jsonify({"error": "No active roadmap found."}), 400

    if hours <= 0 or hours > 24:
        return jsonify({"error": "Hours must be between 0.5 and 24."}), 400

    try:
        session_date_obj = date.fromisoformat(session_date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format."}), 400

    # Verify roadmap ownership
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Roadmap not found."}), 404

    session = StudySession(
        user_id=current_user.id,
        roadmap_id=roadmap_id,
        milestone_id=milestone_id,
        hours_logged=hours,
        notes=notes,
        session_date=session_date_obj,
    )
    db.session.add(session)
    db.session.commit()

    milestone_title = session.milestone.title if session.milestone else "General Study"

    return jsonify({
        "success": True,
        "session": {
            "id": session.id,
            "milestone_title": milestone_title,
            "hours_logged": session.hours_logged,
            "notes": session.notes,
            "session_date": session.session_date.strftime("%B %d, %Y"),
            "created_at": session.created_at.strftime("%H:%M"),
        }
    })


@study_planner_bp.route("/session/<int:session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    """Delete a study session."""
    session = db.session.get(StudySession, session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"error": "Session not found."}), 404

    db.session.delete(session)
    db.session.commit()
    return jsonify({"success": True})


@study_planner_bp.route("/weekly-checkin", methods=["POST"])
@login_required
def weekly_checkin():
    """Generate an AI weekly check-in report."""
    profile = current_user.profile
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    roadmap = (
        Roadmap.query.filter_by(user_id=current_user.id, status="approved")
        .order_by(Roadmap.created_at.desc())
        .first()
    )
    career = roadmap.career_path if roadmap else None

    # Sessions from the last 7 days
    week_ago = date.today() - timedelta(days=7)
    sessions_this_week = (
        StudySession.query
        .filter_by(user_id=current_user.id)
        .filter(StudySession.session_date >= week_ago)
        .order_by(StudySession.session_date.desc())
        .all()
    )

    # Milestones completed in the last 7 days
    week_ago_dt = datetime.utcnow() - timedelta(days=7)
    completed_this_week = []
    if roadmap:
        completed_this_week = [
            m for m in roadmap.milestones
            if m.completed and m.completed_at and m.completed_at >= week_ago_dt
        ]

    # Total hours ever logged
    all_sessions = StudySession.query.filter_by(user_id=current_user.id).all()
    total_hours = sum(s.hours_logged for s in all_sessions)

    checkin_data, error = generate_weekly_checkin(
        profile, career, sessions_this_week, completed_this_week, total_hours
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify({"success": True, "report": checkin_data})
