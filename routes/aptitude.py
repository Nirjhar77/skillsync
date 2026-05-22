"""Aptitude & IQ Test routes."""

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
import json

from database.models import AptitudeProfile, Roadmap, db
from engines.aptitude_engine import (
    generate_quick_fire,
    generate_logic_puzzle,
    generate_interview_question,
    score_interview_answer,
    score_puzzle_answer,
)
from engines.evaluation_engine import record_performance_event, record_interview_answer

aptitude_bp = Blueprint("aptitude", __name__, url_prefix="/aptitude")


DEFAULT_APTITUDE_STATE = {
    "xp": 0,
    "streak": 0,
    "attempted": 0,
    "correct": 0,
    "longestStreak": 0,
    "skills": {
        "logical": {"label": "Logical Reasoning", "level": 1, "pct": 0},
        "communication": {"label": "Communication", "level": 1, "pct": 0},
        "system": {"label": "System Design", "level": 1, "pct": 0},
        "analytical": {"label": "Analytical Thinking", "level": 1, "pct": 0},
        "problem": {"label": "Problem Solving", "level": 1, "pct": 0},
    },
    "activity": [],
    "evaluation": {
        "technical": 0,
        "clarity": 0,
        "reasoning": 0,
        "confidence": 0
    }
}


def _get_career_title():
    """Get the user's active career title, or a generic fallback."""
    roadmap = (
        Roadmap.query.filter_by(user_id=current_user.id, status="approved")
        .order_by(Roadmap.created_at.desc())
        .first()
    )
    if roadmap and roadmap.career_path:
        return roadmap.career_path.title
    return "Software Engineering"


def _merged_aptitude_state(profile):
    state = {
        **DEFAULT_APTITUDE_STATE,
        "skills": DEFAULT_APTITUDE_STATE["skills"].copy(),
        "activity": list(DEFAULT_APTITUDE_STATE["activity"]),
        "evaluation": DEFAULT_APTITUDE_STATE["evaluation"].copy(),
    }
    if profile:
        saved = profile.to_dict()
        state.update({k: v for k, v in saved.items() if k not in ("skills", "activity", "evaluation")})
        state["skills"].update(saved.get("skills") or {})
        state["activity"] = saved.get("activity") or state["activity"]
        state["evaluation"].update(saved.get("evaluation") or {})
    return state


def _get_aptitude_profile():
    profile = AptitudeProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = AptitudeProfile(user_id=current_user.id)
        profile.skills_json = json.dumps(DEFAULT_APTITUDE_STATE["skills"])
        profile.activity_json = json.dumps(DEFAULT_APTITUDE_STATE["activity"])
        profile.evaluation_json = json.dumps(DEFAULT_APTITUDE_STATE["evaluation"])
        profile.evidence_json = json.dumps([])
        db.session.add(profile)
        db.session.commit()
    return profile


@aptitude_bp.route("/")
@login_required
def index():
    career_title = _get_career_title()
    aptitude_state = _merged_aptitude_state(_get_aptitude_profile())
    return render_template("aptitude/index.html", career_title=career_title, aptitude_state=aptitude_state)


@aptitude_bp.route("/state", methods=["POST"])
@login_required
def save_state():
    data = request.get_json() or {}
    profile = _get_aptitude_profile()
    profile.xp = int(data.get("xp") or profile.xp or 0)
    profile.streak = int(data.get("streak") or profile.streak or 0)
    profile.attempted = int(data.get("attempted") or profile.attempted or 0)
    profile.correct = int(data.get("correct") or profile.correct or 0)
    profile.longest_streak = int(data.get("longestStreak") or profile.longest_streak or 0)

    if isinstance(data.get("activity"), list):
        profile.activity_json = json.dumps(data["activity"][:12])
    # skills + evaluation are updated only by AI via /evaluation/record
    db.session.commit()
    return jsonify({"success": True, "aptitude": profile.to_dict()})


@aptitude_bp.route("/evaluation/record", methods=["POST"])
@login_required
def evaluation_record():
    """Record a training event and re-run AI cognitive evaluation."""
    data = request.get_json() or {}
    event_type = (data.get("type") or "").strip()
    payload = data.get("payload") or {}
    if not event_type:
        return jsonify({"error": "Missing event type."}), 400

    profile = _get_aptitude_profile()
    career_title = _get_career_title()
    aptitude, err = record_performance_event(profile, career_title, event_type, payload)
    if err:
        return jsonify({"error": err}), 500
    db.session.commit()
    return jsonify({
        "success": True,
        "aptitude": aptitude,
        "evaluation": aptitude.get("evaluation"),
        "skills": aptitude.get("skills"),
        "summary": aptitude.get("evaluation", {}).get("summary"),
    })


# ─── Quick Fire API ───────────────────────────────────────────────────────────
@aptitude_bp.route("/quick-fire/generate", methods=["POST"])
@login_required
def quick_fire_generate():
    data = request.get_json() or {}
    career_title = _get_career_title()
    category = data.get("category", "logical")
    difficulty = data.get("difficulty", "medium")

    questions, error = generate_quick_fire(career_title, category, difficulty)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"success": True, "questions": questions.get("questions", []), "career": career_title})


# ─── Logic Puzzle API ─────────────────────────────────────────────────────────
@aptitude_bp.route("/puzzle/generate", methods=["POST"])
@login_required
def puzzle_generate():
    career_title = _get_career_title()
    puzzle, error = generate_logic_puzzle(career_title)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"success": True, "puzzle": puzzle})


@aptitude_bp.route("/puzzle/score", methods=["POST"])
@login_required
def puzzle_score():
    data = request.get_json() or {}
    career_title = _get_career_title()
    puzzle_text = data.get("puzzle", "")
    solution = data.get("solution", "")
    answer = data.get("answer", "")

    if not answer.strip():
        return jsonify({"error": "Please provide an answer before submitting."}), 400

    feedback, error = score_puzzle_answer(career_title, puzzle_text, solution, answer)
    if error:
        return jsonify({"error": error}), 500

    return jsonify({"success": True, "feedback": feedback})


# ─── Mock Interview API ───────────────────────────────────────────────────────
@aptitude_bp.route("/interview/question", methods=["POST"])
@login_required
def interview_question():
    data = request.get_json() or {}
    career_title = _get_career_title()
    q_type = data.get("type", "behavioral")

    question, error = generate_interview_question(career_title, q_type)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"success": True, "question": question, "career": career_title})


@aptitude_bp.route("/interview/score", methods=["POST"])
@login_required
def interview_score():
    data = request.get_json() or {}
    career_title = _get_career_title()
    question = data.get("question", "")
    answer = data.get("answer", "")

    if not answer.strip():
        return jsonify({"error": "Please write an answer before submitting."}), 400

    feedback, error = score_interview_answer(career_title, question, answer)
    if error:
        return jsonify({"error": error}), 500

    profile = _get_aptitude_profile()
    aptitude, eval_err = record_interview_answer(profile, career_title, question, answer, feedback)
    if eval_err:
        db.session.commit()
        return jsonify({
            "success": True,
            "feedback": feedback,
            "evaluation_warning": eval_err,
        })
    db.session.commit()
    return jsonify({"success": True, "feedback": feedback, "aptitude": aptitude})
