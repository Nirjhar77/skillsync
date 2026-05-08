"""Chatbot routes — Powers the AI Tutor page."""

import os
from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import login_required, current_user
import groq
from database.models import db, TutorMessage

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/chatbot")

@chatbot_bp.route("/tutor", methods=["GET"])
@login_required
def tutor_view():
    """Render the AI Tutor full-page UI."""
    return render_template("tutor.html")

@chatbot_bp.route("/history", methods=["GET"])
@login_required
def get_history():
    """Fetch previous AI Tutor chat history for the current user."""
    messages = TutorMessage.query.filter_by(user_id=current_user.id).order_by(TutorMessage.created_at).all()
    history = [{"role": msg.role, "content": msg.content} for msg in messages]
    return jsonify({"history": history})

@chatbot_bp.route("/clear", methods=["POST"])
@login_required
def clear_history():
    """Clear AI Tutor chat history for the current user."""
    TutorMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True})

@chatbot_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY is missing in the server configuration."}), 500

    # Save user message to DB
    user_msg_db = TutorMessage(user_id=current_user.id, role="user", content=user_message)
    db.session.add(user_msg_db)
    db.session.commit()

    try:
        client = groq.Client(api_key=api_key)

        # Build context from user profile
        context_str = "Tech Student"
        if current_user.profile:
            context_str = f"Major: {current_user.profile.major}, Semester: {current_user.profile.semester}"
            if current_user.profile.courses:
                courses = [c.course_name for c in current_user.profile.courses]
                context_str += f", Courses: {', '.join(courses)}"

        system_prompt = {
            "role": "system",
            "content": f"You are an expert AI Tech Tutor on the SkillSync platform. The student's profile: {context_str}. Answer their questions about tech concepts, programming, career roadmaps, or curriculum. Provide clear, step-by-step explanations, code snippets where appropriate, and keep a supportive, encouraging tone. Format responses nicely using Markdown."
        }

        # Fetch recent history (limit to last 20 messages for context window)
        history_msgs = TutorMessage.query.filter_by(user_id=current_user.id).order_by(TutorMessage.created_at.desc()).limit(20).all()
        history_msgs.reverse() # chronologically
        
        # Don't duplicate the message we just added
        messages = [system_prompt]
        for msg in history_msgs:
            messages.append({"role": msg.role, "content": msg.content})

        completion = client.chat.completions.create(
            model=current_app.config.get("LLM_MODEL", "llama-3.3-70b-versatile"),
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        reply = completion.choices[0].message.content

        # Save AI response to DB
        ai_msg_db = TutorMessage(user_id=current_user.id, role="assistant", content=reply)
        db.session.add(ai_msg_db)
        db.session.commit()

        return jsonify({"reply": reply})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
