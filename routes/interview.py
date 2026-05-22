"""Mock Interview — session page and API."""

import json

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from database.models import Roadmap, MockInterviewSession, db, log_activity
from engines import interview_engine as eng

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")


def _career_title():
    roadmap = (
        Roadmap.query.filter_by(user_id=current_user.id, status="approved")
        .order_by(Roadmap.created_at.desc())
        .first()
    )
    if roadmap and roadmap.career_path:
        return roadmap.career_path.title
    return "Software Engineering"


def _session_for_user(session_id: int):
    return MockInterviewSession.query.filter_by(
        id=session_id, user_id=current_user.id
    ).first()


@interview_bp.route("/")
@login_required
def session():
    career = _career_title()
    active = eng.get_resumable_session(current_user.id)
    return render_template(
        "interview/session.html",
        career_title=career,
        round_label="Technical Round 2",
        difficulty="Intermediate",
        active_session=active.to_dict() if active else None,
    )


@interview_bp.route("/api/session", methods=["GET"])
@login_required
def api_get_session():
    session_id = request.args.get("id", type=int)
    if session_id:
        s = _session_for_user(session_id)
    else:
        s = eng.get_resumable_session(current_user.id)
    if not s:
        return jsonify({"success": True, "session": None})
    return jsonify({"success": True, "session": s.to_dict()})


@interview_bp.route("/api/session/prepare", methods=["POST"])
@login_required
def api_prepare_session():
    """Create a pending session (lobby) — timer does not run yet."""
    data = request.get_json() or {}
    career = data.get("career_title") or _career_title()
    s = eng.create_pending_session(
        current_user.id,
        career,
        data.get("round_label", "Technical Round 2"),
        data.get("difficulty", "Intermediate"),
    )
    return jsonify({"success": True, "session": s.to_dict()})


@interview_bp.route("/api/session/<int:session_id>/start", methods=["POST"])
@login_required
def api_start_session(session_id):
    """User clicked Start Interview — begin timer and load Q1."""
    s = _session_for_user(session_id)
    if not s:
        return jsonify({"error": "Session not found."}), 404
    if s.status == "completed":
        return jsonify({"error": "Session already finished."}), 400

    updated, err = eng.start_session(s)
    if err:
        return jsonify({"error": err}), 400
    log_activity(current_user.id, "Started mock interview", "active")
    return jsonify({"success": True, "session": updated.to_dict()})


@interview_bp.route("/api/session/<int:session_id>/submit", methods=["POST"])
@login_required
def api_submit_answer(session_id):
    s = _session_for_user(session_id)
    if not s:
        return jsonify({"error": "Session not found."}), 404
    data = request.get_json() or {}
    answer = (data.get("answer") or "").strip()
    if len(answer) < 10:
        return jsonify({"error": "Please write at least 10 characters."}), 400

    result, err = eng.submit_answer(s, answer)
    if err:
        return jsonify({"error": err}), 400
    feedback = result.get("feedback") if isinstance(result, dict) else result
    return jsonify({
        "success": True,
        "feedback": feedback,
        "session": s.to_dict(),
        "aptitude": result.get("aptitude") if isinstance(result, dict) else None,
    })


@interview_bp.route("/api/session/<int:session_id>/next", methods=["POST"])
@login_required
def api_next_question(session_id):
    s = _session_for_user(session_id)
    if not s:
        return jsonify({"error": "Session not found."}), 404
    if s.status != "active":
        return jsonify({"error": "Interview is not active."}), 400

    updated, err = eng.load_question(s, advance=True)
    if err:
        done = s.status == "completed"
        return jsonify({
            "success": not done,
            "error": err,
            "session": s.to_dict(),
            "completed": done,
        }), (200 if done else 400)

    return jsonify({"success": True, "session": updated.to_dict()})


@interview_bp.route("/api/session/<int:session_id>/hint", methods=["POST"])
@login_required
def api_hint(session_id):
    s = _session_for_user(session_id)
    if not s:
        return jsonify({"error": "Session not found."}), 404
    payload, err = eng.use_hint(s)
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"success": True, **payload, "session": s.to_dict()})


@interview_bp.route("/api/session/<int:session_id>/end", methods=["POST"])
@login_required
def api_end_session(session_id):
    s = _session_for_user(session_id)
    if not s:
        return jsonify({"error": "Session not found."}), 404
    data = request.get_json() or {}
    completed = bool(data.get("completed"))
    eng.end_session(s, completed=completed)
    log_activity(
        current_user.id,
        "Completed mock interview" if completed else "Ended mock interview",
        "success" if completed else "pending",
    )
    return jsonify({"success": True, "session": s.to_dict()})
