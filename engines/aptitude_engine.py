"""Aptitude & IQ test AI engine — uses the spare GROQ_API_KEY_APTITUDE."""

import json
import re
import traceback
from flask import current_app
from groq import Groq


def _aptitude_client():
    key = current_app.config.get("GROQ_API_KEY_APTITUDE") or current_app.config.get("GROQ_API_KEY")
    return Groq(api_key=key)


MODEL = "llama-3.3-70b-versatile"


def _clamp_int(value, low=0, high=100, fallback=0):
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        value = fallback
    return max(low, min(high, value))


def _normalize_interview_feedback(data):
    """Keep the UI contract stable even if the model omits a field."""
    metrics = data.get("metric_scores") or {}
    data["score"] = _clamp_int(data.get("score"), 0, 100, 0)
    data["metric_scores"] = {
        "clarity": _clamp_int(metrics.get("clarity"), 0, 10, 0),
        "technical_depth": _clamp_int(metrics.get("technical_depth"), 0, 10, 0),
        "accuracy": _clamp_int(metrics.get("accuracy"), 0, 10, 0),
        "structure": _clamp_int(metrics.get("structure"), 0, 10, 0),
        "communication": _clamp_int(metrics.get("communication"), 0, 10, 0),
    }
    data.setdefault("grade", "B")
    data.setdefault("strengths", [])
    data.setdefault("improvements", [])
    data.setdefault("ideal_answer_points", [])
    data.setdefault("overall_feedback", "")
    data.setdefault("confidence_signal", "Medium")
    data.setdefault("interviewer_follow_up", "")
    return data


def _extract_json_from_raw(raw: str):
    """Attempt to reliably extract a JSON object from a potentially noisy model response.

    Tries several strategies and logs helpful debug info on failure.
    """
    # Step 0: strip markdown code fences (model sometimes wraps in ```json ... ```)
    stripped = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r'\s*```$', '', stripped.strip())

    # Try direct parse of the stripped text first
    try:
        return json.loads(stripped)
    except Exception:
        pass

    # Try direct parse of the original (in case stripping broke something)
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Find first { and last } and try that slice
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = raw[start:end + 1]
            try:
                return json.loads(snippet)
            except Exception:
                # Attempt simple repair: remove trailing commas before } or ]
                repaired = re.sub(r",(\s*[}\]])", r"\1", snippet)
                try:
                    return json.loads(repaired)
                except Exception:
                    # Log for debugging and re-raise a clear error
                    try:
                        current_app.logger.debug("[APTITUDE] Raw response:\n%s", raw)
                        current_app.logger.debug("[APTITUDE] Extracted snippet:\n%s", snippet)
                        current_app.logger.debug("[APTITUDE] Repaired snippet:\n%s", repaired)
                    except Exception:
                        print("[APTITUDE] Failed to log raw response due to app context")
                    raise
    except Exception:
        pass

    # If all else fails, raise a JSON error to be handled by caller
    raise ValueError("Unable to locate valid JSON in model response")


# ─── Quick Fire ───────────────────────────────────────────────────────────────
def generate_quick_fire(career_title: str, category: str, difficulty: str):
    """Generate 10 MCQ questions tuned to career & category."""
    prompt = f"""You are a technical aptitude test generator for a career platform.
Generate exactly 10 multiple-choice questions for a student pursuing a career in: {career_title}.
Category: {category} | Difficulty: {difficulty}

Category guide:
- "logical": sequences, patterns, deduction puzzles
- "numerical": arithmetic, ratios, percentages, data interpretation
- "verbal": analogies, sentence completion, critical reading
- "technical": career-specific technical knowledge for {career_title}

Rules:
- Each question must have exactly 4 options (A, B, C, D)
- Exactly one correct answer per question
- Include a brief 1-sentence explanation for the correct answer
- Make questions realistic and interview-relevant

Return ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "id": 1,
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "A",
      "explanation": "..."
    }}
  ]
}}"""

    try:
        client = _aptitude_client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2500,
        )
        raw = resp.choices[0].message.content.strip()
        try:
            data = _extract_json_from_raw(raw)
            return data, None
        except Exception as e:
            return None, f"Failed to parse questions: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            print("[APTITUDE] ⚠️  Rate limit hit on GROQ_API_KEY_APTITUDE — wait ~60s or get a new key.")
        return None, err


# ─── Deep Think (Logic Puzzle) ────────────────────────────────────────────────
def generate_logic_puzzle(career_title: str):
    """Generate a single multi-step logic puzzle."""
    prompt = f"""Generate one challenging logic puzzle appropriate for a tech student pursuing {career_title}.

The puzzle should:
- Require multi-step reasoning
- Be solvable (no trick questions)
- Have a clear, satisfying answer
- Include 2-3 progressive hints that don't immediately give away the answer
- Include a detailed step-by-step solution

Return ONLY valid JSON:
{{
  "title": "short puzzle name",
  "puzzle": "full puzzle text",
  "hints": ["hint 1", "hint 2", "hint 3"],
  "answer": "the final answer",
  "solution": "detailed step-by-step explanation"
}}"""

    try:
        client = _aptitude_client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=1000,
        )
        raw = resp.choices[0].message.content.strip()
        try:
            data = _extract_json_from_raw(raw)
            return data, None
        except Exception as e:
            return None, f"Failed to parse puzzle: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            print("[APTITUDE] ⚠️  Rate limit hit on GROQ_API_KEY_APTITUDE — wait ~60s or get a new key.")
        return None, err


# ─── Mock Interview ───────────────────────────────────────────────────────────
def generate_interview_question(career_title: str, q_type: str):
    """Generate one interview question (behavioral or technical)."""
    type_guide = {
        "behavioral": "STAR-method behavioral question about teamwork, problem-solving, or leadership",
        "technical": f"core technical concept question for {career_title}",
        "situational": f"situational/case-study question relevant to {career_title} role",
    }
    prompt = f"""Generate one {type_guide.get(q_type, 'interview')} question for a {career_title} candidate.

Return ONLY valid JSON:
{{
  "question": "...",
  "what_interviewers_look_for": ["point 1", "point 2", "point 3"],
  "example_strong_answer_outline": "..."
}}"""

    try:
        client = _aptitude_client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )
        raw = resp.choices[0].message.content.strip()
        try:
            data = _extract_json_from_raw(raw)
            return data, None
        except Exception as e:
            return None, f"Failed to parse question: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            print("[APTITUDE] ⚠️  Rate limit hit on GROQ_API_KEY_APTITUDE — wait ~60s or get a new key.")
        return None, err


def score_interview_answer(career_title: str, question: str, answer: str):
    """Score a user's interview answer and give structured feedback."""
    if not answer or len(answer.strip()) < 20:
        return None, "Answer too short to evaluate."

    prompt = f"""You are an expert interviewer evaluating a candidate for {career_title}.

Question: {question}

Candidate's answer: {answer}

Evaluate the answer and return ONLY valid JSON:
{{
  "score": <integer 0-100>,
  "grade": "<A/B/C/D/F>",
  "metric_scores": {{
    "clarity": <integer 0-10>,
    "technical_depth": <integer 0-10>,
    "accuracy": <integer 0-10>,
    "structure": <integer 0-10>,
    "communication": <integer 0-10>
  }},
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1", "improvement 2"],
  "ideal_answer_points": ["key point 1", "key point 2", "key point 3"],
  "confidence_signal": "<Low/Medium/High>",
  "interviewer_follow_up": "one realistic follow-up question the interviewer would ask next",
  "overall_feedback": "2-3 sentence overall feedback"
}}

Scoring rubric:
- clarity: whether the answer is easy to follow and concise
- technical_depth: correctness and depth for the target role
- accuracy: factual correctness and lack of invented claims
- structure: clear framework such as STAR, tradeoffs, steps, examples
- communication: interview presence, confidence, and practical wording
- score: weighted overall score, not a simple average; penalize vague answers heavily
Be strict like a real interviewer, but constructive.
Technical questions should weight technical_depth and accuracy more heavily.
Behavioral questions should weight structure, clarity, and communication more heavily.
Situational questions should weight tradeoffs, judgment, and structure more heavily."""

    try:
        client = _aptitude_client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=700,
        )
        raw = resp.choices[0].message.content.strip()
        try:
            data = _extract_json_from_raw(raw)
            return _normalize_interview_feedback(data), None
        except Exception as e:
            return None, f"Failed to parse feedback: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            print("[APTITUDE] ⚠️  Rate limit hit on GROQ_API_KEY_APTITUDE — wait ~60s or get a new key.")
        return None, err


def score_puzzle_answer(career_title: str, puzzle_text: str, official_solution: str, user_answer: str):
    """Score a user's free-text answer to a logic puzzle."""
    if not user_answer or len(user_answer.strip()) < 5:
        return None, "Answer too short to evaluate."

    prompt = f"""You are a strict but encouraging logic tutor evaluating a candidate for {career_title}.

Puzzle: {puzzle_text}
Official Solution: {official_solution}

Candidate's Answer: {user_answer}

Evaluate the candidate's logic and correctness.
Return ONLY valid JSON:
{{
  "score": <integer 0-100>,
  "feedback": "<2-3 sentence feedback explaining what they got right or missed compared to the solution>",
  "is_correct": <boolean true if they fundamentally got the right answer, false otherwise>
}}
"""
    try:
        client = _aptitude_client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content.strip()
        data = _extract_json_from_raw(raw)
        
        score = _clamp_int(data.get("score"), 0, 100, 0)
        feedback = data.get("feedback") or "Good attempt, check the official solution for more details."
        is_correct = bool(data.get("is_correct"))
        
        return {"score": score, "feedback": feedback, "is_correct": is_correct}, None
    except Exception as e:
        traceback.print_exc()
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            print("[APTITUDE] ⚠️  Rate limit hit on GROQ_API_KEY_APTITUDE — wait ~60s or get a new key.")
        return None, f"Failed to parse puzzle scoring: {str(e)}"
