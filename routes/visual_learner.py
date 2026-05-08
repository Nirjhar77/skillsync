"""Visual Learner routes - text-to-visual generation through Napkin."""

import json
import os
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from database.models import VisualLearnerItem, db


visual_learner_bp = Blueprint("visual_learner", __name__, url_prefix="/visual-learner")

MAX_VISUAL_WORDS = 100
NAPKIN_BASE_URL = "https://api.napkin.ai"
NAPKIN_USER_AGENT = "SkillSync/1.0 (+https://localhost)"


@visual_learner_bp.route("/", methods=["GET"])
@login_required
def index():
    """Standalone Visual Learner workspace."""
    history = (
        VisualLearnerItem.query.filter_by(user_id=current_user.id)
        .order_by(VisualLearnerItem.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template("visual_learner/index.html", max_words=MAX_VISUAL_WORDS, history=history)


@visual_learner_bp.route("/api/visualize", methods=["POST"])
@login_required
def visualize():
    """Generate a visual from user-provided text and return a local asset URL."""
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    source = (data.get("source") or "visual_learner").strip()[:30] or "visual_learner"

    if not text:
        return jsonify({"error": "Text is required."}), 400

    word_count = _count_words(text)
    if word_count > MAX_VISUAL_WORDS:
        return jsonify({
            "error": f"Please keep the text within {MAX_VISUAL_WORDS} words.",
            "word_count": word_count,
            "max_words": MAX_VISUAL_WORDS,
        }), 400

    token = current_app.config.get("NAPKIN_API_KEY") or os.environ.get("NAPKIN_API_KEY", "")
    if not token:
        return jsonify({"error": "NAPKIN_API_KEY is missing in the server configuration."}), 500

    try:
        visual_url, request_id = _generate_napkin_visual(text, token)
        item = VisualLearnerItem(
            user_id=current_user.id,
            input_text=text,
            visual_url=visual_url,
            request_id=request_id,
            word_count=word_count,
            source=source,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({
            "success": True,
            "id": item.id,
            "visual_url": visual_url,
            "request_id": request_id,
            "word_count": word_count,
            "input_text": text,
            "source": source,
            "created_at": item.created_at.strftime("%b %d, %Y %I:%M %p"),
        })
    except Exception as exc:
        current_app.logger.exception("Visual generation failed")
        return jsonify({"error": str(exc)}), 500


def _generate_napkin_visual(text, token):
    create_payload = {
        "format": "svg",
        "content": text,
    }
    created = _napkin_json("/v1/visual", token, method="POST", payload=create_payload, expected=(200, 201))
    request_id = _first_value(created, "request_id", "id", "visual_id")
    if not request_id:
        raise RuntimeError("Napkin did not return a visual request ID.")

    status = _poll_napkin_status(request_id, token)
    files = status.get("generated_files") or status.get("files") or []
    if not files:
        raise RuntimeError("Napkin completed the request but returned no files.")

    file_meta = _choose_svg_file(files)
    download_url = _first_value(file_meta, "url", "download_url", "file_url", "href")
    if not download_url:
        raise RuntimeError("Napkin did not return a downloadable file URL.")

    content, content_type = _napkin_download(download_url, token)
    ext = ".svg" if "svg" in content_type.lower() or download_url.lower().endswith(".svg") else ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "visuals")
    os.makedirs(upload_dir, exist_ok=True)
    output_path = os.path.join(upload_dir, filename)
    with open(output_path, "wb") as f:
        f.write(content)

    return url_for("static", filename=f"uploads/visuals/{filename}"), request_id


def _poll_napkin_status(request_id, token):
    delay = 1.2
    deadline = time.time() + 45
    last_status = None

    while time.time() < deadline:
        payload = _napkin_json(f"/v1/visual/{request_id}/status", token, method="GET")
        last_status = (payload.get("status") or payload.get("state") or "").lower()
        if last_status in {"completed", "complete", "succeeded", "success", "done"}:
            return payload
        if last_status in {"failed", "error", "errored"}:
            message = payload.get("error") or payload.get("message") or "Napkin visual generation failed."
            raise RuntimeError(message)
        time.sleep(delay)
        delay = min(delay * 1.35, 4)

    raise RuntimeError(f"Timed out waiting for Napkin visual generation. Last status: {last_status or 'unknown'}.")


def _napkin_json(path, token, method="GET", payload=None, expected=(200,)):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        f"{NAPKIN_BASE_URL}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": NAPKIN_USER_AGENT,
        },
    )
    try:
        with urlopen(req, timeout=30) as res:
            if res.status not in expected:
                raise RuntimeError(f"Napkin returned HTTP {res.status}.")
            return json.loads(res.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Napkin returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Napkin API: {exc.reason}") from exc


def _napkin_download(download_url, token):
    parsed = urlparse(download_url)
    if not parsed.scheme:
        download_url = f"{NAPKIN_BASE_URL}{download_url}"

    req = Request(download_url, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": NAPKIN_USER_AGENT,
    })
    try:
        with urlopen(req, timeout=30) as res:
            return res.read(), res.headers.get("Content-Type", "")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Napkin file download failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not download Napkin visual: {exc.reason}") from exc


def _choose_svg_file(files):
    for file_meta in files:
        if isinstance(file_meta, str):
            file_meta = {"url": file_meta}
        fmt = str(file_meta.get("format") or file_meta.get("type") or file_meta.get("mime_type") or "").lower()
        url = str(_first_value(file_meta, "url", "download_url", "file_url", "href") or "").lower()
        if "svg" in fmt or url.endswith(".svg"):
            return file_meta
    first = files[0]
    return {"url": first} if isinstance(first, str) else first


def _first_value(source, *keys):
    for key in keys:
        value = source.get(key)
        if value:
            return value
    return None


def _count_words(text):
    return len([part for part in text.split() if part.strip()])
