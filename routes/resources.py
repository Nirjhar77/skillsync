"""Resources routes — curated course library."""

import json
import os
from flask import Blueprint, render_template, abort, current_app
from flask_login import login_required

resources_bp = Blueprint("resources", __name__, url_prefix="/resources")


def load_resources():
    """Load resources from JSON file."""
    path = os.path.join(current_app.config["DATA_DIR"], "resources.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@resources_bp.route("/")
@login_required
def index():
    """Render the resources hub page with all categories."""
    data = load_resources()
    # Count total courses across all categories
    total = sum(len(cat["courses"]) for cat in data["categories"])
    return render_template(
        "resources/index.html",
        categories=data["categories"],
        total_courses=total,
    )


@resources_bp.route("/<course_id>")
@login_required
def course_detail(course_id):
    """Render a single course's detail / sources page."""
    data = load_resources()
    found_course = None
    found_category = None

    for category in data["categories"]:
        for course in category["courses"]:
            if course["id"] == course_id:
                found_course = course
                found_category = category
                break
        if found_course:
            break

    if not found_course:
        abort(404)

    return render_template(
        "resources/course_detail.html",
        course=found_course,
        category=found_category,
    )
