"""AI-driven aptitude evaluation — updates cognitive profile from real performance evidence."""

import json
from datetime import datetime

from flask import current_app
from groq import Groq

from database.models import AptitudeProfile, db
from engines.aptitude_engine import MODEL, _clamp_int, _extract_json_from_raw

SKILL_KEYS = ("logical", "communication", "analytical", "problem", "system")
SKILL_LABELS = {
    "logical": "Logical Reasoning",
    "communication": "Communication",
    "analytical": "Analytical Thinking",
    "problem": "Problem Solving",
    "system": "System Design",
}

DEFAULT_SKILLS = {
    key: {"label": SKILL_LABELS[key], "level": 1, "pct": 0}
    for key in SKILL_KEYS
}


def _client():
    key = current_app.config.get("GROQ_API_KEY_APTITUDE") or current_app.config.get("GROQ_API_KEY")
    return Groq(api_key=key)


def _get_evidence(profile: AptitudeProfile) -> list:
    try:
        raw = getattr(profile, "evidence_json", None) or "[]"
        data = json.loads(raw) if raw else []
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _set_evidence(profile: AptitudeProfile, items: list):
    profile.evidence_json = json.dumps(items[-24:])


def append_evidence(profile: AptitudeProfile, event_type: str, payload: dict) -> list:
    items = _get_evidence(profile)
    items.append({
        "type": event_type,
        "payload": payload or {},
        "at": datetime.utcnow().isoformat() + "Z",
    })
    _set_evidence(profile, items)
    return items


def _normalize_skills(raw: dict, previous: dict) -> dict:
    prev = previous or DEFAULT_SKILLS
    out = {}
    for key in SKILL_KEYS:
        block = (raw or {}).get(key) or {}
        prev_block = prev.get(key) or DEFAULT_SKILLS[key]
        pct = _clamp_int(block.get("pct", prev_block.get("pct")), 0, 100, 0)
        level = _clamp_int(block.get("level", max(1, pct // 20 + 1)), 1, 10, 1)
        out[key] = {
            "label": SKILL_LABELS[key],
            "level": level,
            "pct": pct,
        }
    return out


def _normalize_evaluation(raw: dict, previous: dict) -> dict:
    prev = previous or {}
    metrics = {
        "technical": _clamp_int((raw or {}).get("technical", prev.get("technical")), 0, 100, 0),
        "clarity": _clamp_int((raw or {}).get("clarity", prev.get("clarity")), 0, 100, 0),
        "reasoning": _clamp_int((raw or {}).get("reasoning", prev.get("reasoning")), 0, 100, 0),
        "confidence": _clamp_int((raw or {}).get("confidence", prev.get("confidence")), 0, 100, 0),
    }
    avg = sum(metrics.values()) / 4
    grade = (raw or {}).get("grade") or _grade_from_avg(avg)
    return {
        **metrics,
        "grade": grade,
        "summary": str((raw or {}).get("summary") or prev.get("summary") or "").strip()[:600],
        "focus_skill": str((raw or {}).get("focus_skill") or prev.get("focus_skill") or "").strip()[:80],
        "focus_boost_pct": _clamp_int((raw or {}).get("focus_boost_pct", prev.get("focus_boost_pct")), 4, 12, 6),
        "ai_updated_at": datetime.utcnow().isoformat() + "Z",
    }


def _grade_from_avg(avg: float) -> str:
    if avg >= 90:
        return "A"
    if avg >= 82:
        return "B+"
    if avg >= 74:
        return "B"
    if avg >= 66:
        return "C+"
    if avg >= 58:
        return "C"
    return "D"


def synthesize_profile(career_title: str, profile: AptitudeProfile):
    """Call LLM to produce evaluation + skills from accumulated evidence."""
    evidence = _get_evidence(profile)
    if not evidence:
        return None, "No performance evidence yet. Complete a training activity first."

    current_skills = profile.get_skills() or DEFAULT_SKILLS
    current_eval = profile.get_evaluation() or {}

    prompt = f"""You are an expert career coach and cognitive assessor for a {career_title} student using SkillSync training.

Review the performance evidence below and produce an honest, evidence-based aptitude profile.
CRITICAL INSTRUCTION: Weight the MOST RECENT performance evidence heavily. If the candidate just scored a 'B' or 'A', their overall rank should closely reflect this recent improvement rather than being anchored to old 'C' scores. Let the overall grade move up quickly when recent evidence supports it.
Penalize guessing, vague interview answers, hint-heavy puzzles, and low accuracy.
Reward consistent accuracy, depth in interview feedback, and improvement across sessions.
Do not inflate scores without evidence.

CURRENT STORED SKILLS (for reference):
{json.dumps(current_skills, indent=2)}

CURRENT STORED EVALUATION METRICS:
{json.dumps({k: current_eval.get(k) for k in ("technical", "clarity", "reasoning", "confidence")}, indent=2)}

PERFORMANCE EVIDENCE (chronological):
{json.dumps(evidence[-16:], indent=2)}

Return ONLY valid JSON:
{{
  "evaluation": {{
    "technical": <0-100>,
    "clarity": <0-100>,
    "reasoning": <0-100>,
    "confidence": <0-100>,
    "grade": "<letter grade A/B+/B/C+/C/D>",
    "summary": "<2-3 sentences explaining the assessment based on evidence>",
    "focus_skill": "<exactly one of: Logical Reasoning, Communication, Analytical Thinking, Problem Solving, System Design>",
    "focus_boost_pct": <integer 4-12 — realistic % improvement if they focus on weakest area>
  }},
  "skills": {{
    "logical": {{ "pct": <0-100>, "level": <1-10> }},
    "communication": {{ "pct": <0-100>, "level": <1-10> }},
    "analytical": {{ "pct": <0-100>, "level": <1-10> }},
    "problem": {{ "pct": <0-100>, "level": <1-10> }},
    "system": {{ "pct": <0-100>, "level": <1-10> }}
  }}
}}"""

    try:
        client = _client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
            max_tokens=900,
        )
        raw = resp.choices[0].message.content.strip()
        data = _extract_json_from_raw(raw)
    except Exception as exc:
        return None, str(exc)

    eval_block = data.get("evaluation") or {}
    skills_block = data.get("skills") or {}

    normalized_eval = _normalize_evaluation(eval_block, current_eval)
    normalized_skills = _normalize_skills(skills_block, current_skills)

    profile.evaluation_json = json.dumps(normalized_eval)
    profile.skills_json = json.dumps(normalized_skills)
    profile.updated_at = datetime.utcnow()

    return {
        "evaluation": normalized_eval,
        "skills": normalized_skills,
        "summary": normalized_eval.get("summary"),
    }, None


def record_performance_event(profile: AptitudeProfile, career_title: str, event_type: str, payload: dict):
    """Append evidence and run AI synthesis. Returns aptitude slice for the client."""
    append_evidence(profile, event_type, payload)
    result, err = synthesize_profile(career_title, profile)
    if err:
        return None, err
    return profile.to_dict(), None


def record_interview_answer(profile: AptitudeProfile, career_title: str, question: str, answer: str, feedback: dict):
    metrics = feedback.get("metric_scores") or {}
    payload = {
        "question": (question or "")[:500],
        "answer_excerpt": (answer or "")[:800],
        "score": feedback.get("score"),
        "grade": feedback.get("grade"),
        "metrics": metrics,
        "strengths": (feedback.get("strengths") or [])[:4],
        "improvements": (feedback.get("improvements") or [])[:4],
        "overall_feedback": (feedback.get("overall_feedback") or "")[:400],
    }
    return record_performance_event(profile, career_title, "interview_answer", payload)
