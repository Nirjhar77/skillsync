"""CV Builder routes — Form input → JSON → Render Resume Template."""

import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

cv_bp = Blueprint("cv", __name__, url_prefix="/cv")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
UPLOAD_FOLDER = os.path.join("static", "uploads", "cv")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@cv_bp.route("/")
@login_required
def builder():
    """Render the multi-step CV builder form."""
    return render_template("cv/builder.html")


@cv_bp.route("/preview", methods=["POST"])
@login_required
def preview():
    """
    Receive form data, convert to structured JSON context,
    and render the Azurill resume template.
    """
    form = request.form

    # ── Photo Upload ─────────────────────────────────────
    photo_url = None
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename and allowed_file(photo_file.filename):
        ext = photo_file.filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        save_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(save_dir, exist_ok=True)
        photo_file.save(os.path.join(save_dir, unique_name))
        photo_url = url_for("static", filename=f"uploads/cv/{unique_name}")

    # ── Basics & Socials ─────────────────────────────────
    data = {
        "name":         form.get("name", "").strip(),
        "title":        form.get("title", "").strip(),
        "email":        form.get("email", "").strip(),
        "phone":        form.get("phone", "").strip(),
        "location":     form.get("location", "").strip(),
        "website":      form.get("website", "").strip(),
        "github_url":   form.get("github_url", "").strip(),
        "linkedin_url": form.get("linkedin_url", "").strip(),
        "twitter_url":  form.get("twitter_url", "").strip(),
        "summary":      form.get("summary", "").strip(),
        "accent_color": form.get("accent_color", "#2563eb"),
        "photo_url":    photo_url,
    }

    # ── KPI Stats ────────────────────────────────────────
    data["stats"] = []
    for idx in range(1, 5):
        val = form.get(f"stat_val{idx}", "").strip()
        lbl = form.get(f"stat_lbl{idx}", "").strip()
        if val:
            # Match Lucide icons for each box
            icons = ["briefcase", "folder", "award", "graduation-cap"]
            data["stats"].append({
                "value": val,
                "label": lbl,
                "icon": icons[idx-1]
            })

    # ── Experience ───────────────────────────────────────
    exp_roles       = form.getlist("exp_role[]")
    exp_companies   = form.getlist("exp_company[]")
    exp_starts      = form.getlist("exp_start[]")
    exp_ends        = form.getlist("exp_end[]")
    exp_locations   = form.getlist("exp_location[]")
    exp_descs       = form.getlist("exp_description[]")

    data["experience"] = [
        {
            "role":        exp_roles[i],
            "company":     exp_companies[i],
            "start":       exp_starts[i],
            "end":         exp_ends[i] or "Present",
            "location":    exp_locations[i],
            "description": exp_descs[i],
        }
        for i in range(len(exp_roles))
        if exp_roles[i].strip()
    ]

    # ── Extracurricular Activities ───────────────────────
    extra_roles = form.getlist("extra_role[]")
    extra_orgs  = form.getlist("extra_org[]")
    extra_dates = form.getlist("extra_date[]")
    extra_descs = form.getlist("extra_description[]")

    data["extracurriculars"] = [
        {
            "role":        extra_roles[i],
            "organization":extra_orgs[i],
            "date":        extra_dates[i],
            "description": extra_descs[i],
        }
        for i in range(len(extra_roles))
        if extra_roles[i].strip()
    ]

    # ── Education ────────────────────────────────────────
    edu_degrees   = form.getlist("edu_degree[]")
    edu_insts     = form.getlist("edu_institution[]")
    edu_starts    = form.getlist("edu_start[]")
    edu_ends      = form.getlist("edu_end[]")
    edu_descs     = form.getlist("edu_description[]")

    data["education"] = [
        {
            "degree":      edu_degrees[i],
            "institution": edu_insts[i],
            "start":       edu_starts[i],
            "end":         edu_ends[i] or "Present",
            "description": edu_descs[i],
        }
        for i in range(len(edu_degrees))
        if edu_degrees[i].strip()
    ]

    # ── Certifications ───────────────────────────────────
    cert_names   = form.getlist("cert_name[]")
    cert_issuers = form.getlist("cert_issuer[]")
    cert_dates   = form.getlist("cert_date[]")

    data["certifications"] = [
        {
            "name":   cert_names[i],
            "issuer": cert_issuers[i],
            "date":   cert_dates[i],
        }
        for i in range(len(cert_names))
        if cert_names[i].strip()
    ]

    # ── Skills ───────────────────────────────────────────
    skill_names  = form.getlist("skill_name[]")
    skill_levels = form.getlist("skill_level[]")

    data["skills"] = [
        {
            "name":  skill_names[i],
            "level": int(skill_levels[i]) if skill_levels[i].isdigit() else 70,
        }
        for i in range(len(skill_names))
        if skill_names[i].strip()
    ]

    # ── Languages ────────────────────────────────────────
    lang_names  = form.getlist("lang_name[]")
    lang_levels = form.getlist("lang_level[]")

    data["languages"] = [
        {"name": lang_names[i], "level": lang_levels[i]}
        for i in range(len(lang_names))
        if lang_names[i].strip()
    ]

    # ── Interests ────────────────────────────────────────
    interest_names = form.getlist("interest_name[]")
    data["interests"] = [
        interest_names[i].strip()
        for i in range(len(interest_names))
        if interest_names[i].strip()
    ]

    # ── Projects ─────────────────────────────────────────
    proj_names  = form.getlist("proj_name[]")
    proj_urls   = form.getlist("proj_url[]")
    proj_techs  = form.getlist("proj_tech[]")
    proj_descs  = form.getlist("proj_description[]")

    data["projects"] = [
        {
            "name":        proj_names[i],
            "url":         proj_urls[i],
            "tech":        proj_techs[i],
            "description": proj_descs[i],
        }
        for i in range(len(proj_names))
        if proj_names[i].strip()
    ]

    # ── Achievements ─────────────────────────────────────
    ach_descs = form.getlist("ach_desc[]")
    data["achievements"] = [
        ach_descs[i].strip()
        for i in range(len(ach_descs))
        if ach_descs[i].strip()
    ]

    return render_template("cv/azurill.html", **data)
