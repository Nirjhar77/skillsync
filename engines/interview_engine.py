"""Mock interview session logic."""

import json
from datetime import datetime

from database.models import MockInterviewSession, AptitudeProfile, db
from engines.aptitude_engine import generate_interview_question, score_interview_answer

TOTAL_QUESTIONS = 8
DEFAULT_TIMER_SEC = 15 * 60

PHASE_BY_INDEX = {
    1: "introduction",
    2: "introduction",
    3: "technical",
    4: "technical",
    5: "technical",
    6: "scenario",
    7: "system_design",
    8: "closing",
}

TYPE_BY_INDEX = {
    1: "behavioral",
    2: "behavioral",
    3: "technical",
    4: "technical",
    5: "technical",
    6: "situational",
    7: "technical",
    8: "behavioral",
}


def question_type_for_index(index: int) -> str:
    return TYPE_BY_INDEX.get(max(1, min(index, TOTAL_QUESTIONS)), "technical")


def phase_for_index(index: int) -> str:
    return PHASE_BY_INDEX.get(max(1, min(index, TOTAL_QUESTIONS)), "technical")


def abandon_active_sessions(user_id: int):
    (
        MockInterviewSession.query.filter_by(user_id=user_id, status="active")
        .update({"status": "abandoned", "ended_at": datetime.utcnow()})
    )
    (
        MockInterviewSession.query.filter_by(user_id=user_id, status="pending")
        .update({"status": "abandoned", "ended_at": datetime.utcnow()})
    )


def create_pending_session(user_id: int, career_title: str, round_label: str, difficulty: str):
    abandon_active_sessions(user_id)
    session = MockInterviewSession(
        user_id=user_id,
        career_title=career_title,
        round_label=round_label,
        difficulty=difficulty,
        status="pending",
        total_questions=TOTAL_QUESTIONS,
        current_index=0,
        timer_total_sec=DEFAULT_TIMER_SEC,
        timer_remaining_sec=DEFAULT_TIMER_SEC,
        current_phase="introduction",
        hints_remaining=2,
    )
    db.session.add(session)
    db.session.commit()
    return session


def get_resumable_session(user_id: int):
    return (
        MockInterviewSession.query.filter_by(user_id=user_id, status="active")
        .order_by(MockInterviewSession.updated_at.desc())
        .first()
    )


def start_session(session: MockInterviewSession):
    """Begin interview: start timer and load question 1."""
    if session.status not in ("pending", "active"):
        return None, "Session is not startable."

    session.status = "active"
    session.started_at = datetime.utcnow()
    session.timer_remaining_sec = session.timer_total_sec
    db.session.commit()

    return load_question(session, advance=False)


def load_question(session: MockInterviewSession, advance: bool = True):
    """Generate and attach the next question."""
    session.sync_timer()
    if session.timer_remaining_sec <= 0 and session.status == "active":
        session.status = "completed"
        session.ended_at = datetime.utcnow()
        db.session.commit()
        return None, "Time is up — interview ended."

    if advance:
        if session.current_index >= session.total_questions:
            session.status = "completed"
            session.ended_at = datetime.utcnow()
            db.session.commit()
            return None, "Interview complete."
        session.current_index += 1
    elif session.current_index == 0:
        session.current_index = 1

    idx = session.current_index
    q_type = question_type_for_index(idx)
    session.current_phase = phase_for_index(idx)

    question, err = generate_interview_question(session.career_title, q_type)
    if err:
        return None, err

    session.current_question_text = question.get("question", "")
    session.set_question_meta({
        "type": q_type,
        "what_interviewers_look_for": question.get("what_interviewers_look_for", []),
        "example_strong_answer_outline": question.get("example_strong_answer_outline", ""),
    })
    db.session.commit()
    return session, None


def submit_answer(session: MockInterviewSession, answer: str):
    session.sync_timer()
    if session.status != "active":
        return None, "Interview is not active."
    if not session.current_question_text:
        return None, "No active question."

    feedback, err = score_interview_answer(
        session.career_title,
        session.current_question_text,
        answer,
    )
    if err:
        return None, err

    session.append_history({
        "index": session.current_index,
        "question": session.current_question_text,
        "answer": answer[:8000],
        "feedback": feedback,
    })
    _bump_aptitude_xp(session.user_id, feedback)

    aptitude_payload = None
    try:
        from database.models import AptitudeProfile
        from engines.evaluation_engine import record_interview_answer

        profile = AptitudeProfile.query.filter_by(user_id=session.user_id).first()
        if not profile:
            profile = AptitudeProfile(user_id=session.user_id)
            profile.skills_json = "{}"
            profile.evaluation_json = "{}"
            profile.evidence_json = "[]"
            db.session.add(profile)
        aptitude_dict, eval_err = record_interview_answer(
            profile,
            session.career_title,
            session.current_question_text,
            answer,
            feedback,
        )
        if aptitude_dict and not eval_err:
            aptitude_payload = aptitude_dict
    except Exception:
        pass

    db.session.commit()
    return {"feedback": feedback, "aptitude": aptitude_payload}, None


def use_hint(session: MockInterviewSession):
    if session.hints_remaining <= 0:
        return None, "No hints remaining."
    session.hints_remaining -= 1
    db.session.commit()
    meta = session.get_question_meta()
    tips = meta.get("what_interviewers_look_for") or []
    outline = meta.get("example_strong_answer_outline") or ""
    if tips:
        hint = tips[min(2 - session.hints_remaining, len(tips) - 1)]
    elif outline:
        hint = outline
    else:
        hint = "Lead with context, explain your approach, tradeoffs, and a concrete result."
    return {"hint": hint, "hints_remaining": session.hints_remaining}, None


def end_session(session: MockInterviewSession, completed: bool = False):
    session.sync_timer()
    session.status = "completed" if completed else "abandoned"
    session.ended_at = datetime.utcnow()
    db.session.commit()
    return session


def _bump_aptitude_xp(user_id: int, feedback: dict):
    profile = AptitudeProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return
    score = int(feedback.get("score") or 0)
    profile.xp = (profile.xp or 0) + max(40, 90 + score // 2)
    activity = profile.get_activity()
    activity.insert(0, {
        "icon": "mic",
        "title": "Mock Interview",
        "detail": f"Grade {feedback.get('grade', 'B')}",
    })
    profile.activity_json = json.dumps(activity[:12])
