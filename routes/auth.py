"""Authentication routes — Login, Register, Logout."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
import uuid
from database.models import db, User, Profile

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.profile:
            return redirect(url_for("dashboard.index"))
        if current_user.nontech_profile:
            return redirect(url_for("nontech.intake"))
        return redirect(url_for("profile.background"))
    return render_template("index.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Lookup user by username or email case-insensitively
        user = User.query.filter(
            (db.func.lower(User.username) == db.func.lower(username)) |
            (db.func.lower(User.email) == db.func.lower(username))
        ).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back! 🎯", "success")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            if user.profile:
                return redirect(url_for("dashboard.index"))
            if user.nontech_profile:
                return redirect(url_for("nontech.intake"))
            return redirect(url_for("profile.background"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/guest", methods=["POST", "GET"])
def guest_login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.index"))

    # Generate a random username and password for the guest session
    guest_id = uuid.uuid4().hex[:6]
    username = f"guest_{guest_id}"
    email = f"guest_{guest_id}@skillsync.local"
    password = uuid.uuid4().hex

    user = User(username=username, email=email, role="guest")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    flash("Browsing as a temporary Guest. Your data will be lost upon logout.", "warning")
    return redirect(url_for("profile.background"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("Please enter a valid email.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(username=username).first():
            errors.append("Username already taken.")
        if User.query.filter_by(email=email).first():
            errors.append("Email already registered.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html")

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Account created! Let's get started. 🚀", "success")
        return redirect(url_for("profile.background"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("auth.login"))
