"""Progress routes — Track milestone completion with external link redirection."""

from collections import OrderedDict
from datetime import datetime
from flask import Blueprint, redirect, url_for, flash, jsonify, request, render_template
from flask_login import login_required, current_user
from database.models import db, Milestone, Roadmap, log_activity

progress_bp = Blueprint("progress", __name__, url_prefix="/progress")


@progress_bp.route("/")
@login_required
def tracker():
    """Main progress tracker dashboard."""
    # Get user's most recent approved roadmap
    roadmap = (
        Roadmap.query.filter_by(user_id=current_user.id, status="approved")
        .order_by(Roadmap.created_at.desc())
        .first()
    )

    if not roadmap:
        if current_user.nontech_profile and not current_user.profile:
            return redirect(url_for("nontech.dashboard"))
        flash("No roadmap found. Please select a career path first.", "info")
        return redirect(url_for("career.results"))

    # If it's a non-tech roadmap, redirect to the custom non-tech view
    if roadmap.roadmap_type == "nontech":
        return redirect(url_for("nontech.roadmap_view", roadmap_id=roadmap.id))

    career = roadmap.career_path
    milestones = roadmap.milestones
    total = len(milestones)
    completed = sum(1 for m in milestones if m.completed)
    progress = int((completed / total) * 100) if total > 0 else 0
    total_hours = sum(m.estimated_hours for m in milestones)
    completed_hours = sum(m.estimated_hours for m in milestones if m.completed)

    # Group milestones by phase
    phases = OrderedDict()
    for m in milestones:
        key = m.phase_number or 1
        if key not in phases:
            phases[key] = {
                "phase_number": key,
                "phase_title": m.phase_title or f"Phase {key}",
                "phase_description": m.phase_description or "",
                "milestones": [],
                "total": 0,
                "completed": 0,
            }
        phases[key]["milestones"].append(m)
        phases[key]["total"] += 1
        if m.completed:
            phases[key]["completed"] += 1

    return render_template(
        "progress/tracker.html",
        roadmap=roadmap,
        career=career,
        milestones=milestones,
        phases=phases,
        progress=progress,
        completed_count=completed,
        total_count=total,
        total_hours=round(total_hours, 1),
        completed_hours=round(completed_hours, 1),
    )


@progress_bp.route("/redirect/<int:milestone_id>")
@login_required
def redirect_to_resource(milestone_id):
    """
    Redirect to external resource (Udemy/YouTube) and mark milestone as clicked.
    The actual completion is done via a separate endpoint when user marks it done.
    """
    milestone = db.session.get(Milestone, milestone_id)
    if not milestone:
        flash("Milestone not found.", "error")
        return redirect(url_for("progress.tracker"))

    # Verify ownership
    roadmap = db.session.get(Roadmap, milestone.roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("progress.tracker"))

    # Mark as clicked
    milestone.clicked = True
    db.session.commit()

    # Redirect to external resource
    if milestone.resource_url and milestone.resource_url.startswith("http"):
        return redirect(milestone.resource_url)
    else:
        flash("No external resource link available for this milestone.", "info")
        return redirect(url_for("progress.tracker"))


@progress_bp.route("/milestone/<int:milestone_id>/complete", methods=["POST"])
@login_required
def complete_milestone(milestone_id):
    """Mark a milestone as complete."""
    milestone = db.session.get(Milestone, milestone_id)
    if not milestone:
        return jsonify({"error": "Milestone not found"}), 404

    # Verify ownership
    roadmap = db.session.get(Roadmap, milestone.roadmap_id)
    if not roadmap or roadmap.user_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    milestone.completed = not milestone.completed  # Toggle
    milestone.completed_at = datetime.utcnow() if milestone.completed else None
    db.session.commit()
    
    if milestone.completed:
        log_activity(current_user.id, "Completed a Milestone")

    # Calculate new progress
    milestones = roadmap.milestones
    total = len(milestones)
    completed = sum(1 for m in milestones if m.completed)
    progress = int((completed / total) * 100) if total > 0 else 0

    return jsonify({
        "success": True,
        "completed": milestone.completed,
        "progress": progress,
        "completed_count": completed,
        "total_count": total,
    })


@progress_bp.route("/stats")
@login_required
def stats():
    """Get progress statistics as JSON."""
    roadmap = (
        Roadmap.query.filter_by(user_id=current_user.id, status="approved")
        .order_by(Roadmap.created_at.desc())
        .first()
    )

    if not roadmap:
        return jsonify({"error": "No roadmap found"}), 404

    milestones = roadmap.milestones
    total = len(milestones)
    completed = sum(1 for m in milestones if m.completed)
    clicked = sum(1 for m in milestones if m.clicked)

    return jsonify({
        "total": total,
        "completed": completed,
        "clicked": clicked,
        "progress": int((completed / total) * 100) if total > 0 else 0,
    })
