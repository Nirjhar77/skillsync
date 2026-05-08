"""Chat routes — Contextual Q&A about the student's roadmap."""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database.models import db, Roadmap, ChatMessage
from engines.llm_engine import chat_with_context

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


@chat_bp.route("/send", methods=["POST"])
@login_required
def send_message():
    """Send a chat message and get AI response."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    roadmap_id = data.get("roadmap_id")
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Roadmap not found"}), 404

    profile = current_user.profile
    career = roadmap.career_path

    # Save user message
    user_msg = ChatMessage(
        roadmap_id=roadmap.id,
        role="user",
        content=user_message,
    )
    db.session.add(user_msg)
    db.session.commit()

    # Get chat history
    history = ChatMessage.query.filter_by(roadmap_id=roadmap.id).order_by(
        ChatMessage.created_at
    ).all()

    # Get AI response
    response_text, error = chat_with_context(
        roadmap, profile, career, user_message, history
    )

    if error:
        return jsonify({"error": error}), 500

    # Save AI response
    ai_msg = ChatMessage(
        roadmap_id=roadmap.id,
        role="assistant",
        content=response_text,
    )
    db.session.add(ai_msg)
    db.session.commit()

    return jsonify({
        "success": True,
        "response": response_text,
    })


@chat_bp.route("/history/<int:roadmap_id>")
@login_required
def get_history(roadmap_id):
    """Get chat history for a roadmap."""
    roadmap = db.session.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Roadmap not found"}), 404

    messages = ChatMessage.query.filter_by(roadmap_id=roadmap.id).order_by(
        ChatMessage.created_at
    ).all()

    return jsonify({
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at.isoformat(),
            }
            for m in messages
        ]
    })
