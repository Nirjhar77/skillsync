from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()


def _loads_json_list(value):
    try:
        data = json.loads(value) if value else []
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="student")  # student / counselor
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    profile = db.relationship("Profile", backref="user", uselist=False, cascade="all, delete-orphan")
    nontech_profile = db.relationship("NonTechProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    career_scores = db.relationship("CareerScore", backref="user", cascade="all, delete-orphan")
    roadmaps = db.relationship("Roadmap", backref="user", cascade="all, delete-orphan")
    visual_items = db.relationship("VisualLearnerItem", backref="user", cascade="all, delete-orphan",
                                   order_by="VisualLearnerItem.created_at.desc()")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    major = db.Column(db.String(100))
    semester = db.Column(db.Integer)
    total_semesters = db.Column(db.Integer, default=8)
    location = db.Column(db.String(100))
    hours_per_week = db.Column(db.Integer, default=10)
    interests = db.Column(db.Text)  # JSON array
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skills = db.relationship("UserSkill", backref="profile", cascade="all, delete-orphan")
    courses = db.relationship("UserCourse", backref="profile", cascade="all, delete-orphan")

    def get_interests(self):
        try:
            return json.loads(self.interests) if self.interests else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_interests(self, interests_list):
        self.interests = json.dumps(interests_list)


class UserSkill(db.Model):
    __tablename__ = "user_skills"

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profiles.id"), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.String(20), default="beginner")  # beginner / intermediate / advanced


class UserCourse(db.Model):
    __tablename__ = "user_courses"

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profiles.id"), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    course_name = db.Column(db.String(150))
    status = db.Column(db.String(20), default="completed")  # completed / in_progress / upcoming


class CareerPath(db.Model):
    __tablename__ = "career_paths"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    required_skills = db.Column(db.Text)  # JSON
    recommended_tools = db.Column(db.Text)  # JSON
    avg_salary_range = db.Column(db.String(50))
    growth_outlook = db.Column(db.String(20))

    def get_required_skills(self):
        try:
            return json.loads(self.required_skills) if self.required_skills else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_recommended_tools(self):
        try:
            return json.loads(self.recommended_tools) if self.recommended_tools else []
        except (json.JSONDecodeError, TypeError):
            return []


class CareerScore(db.Model):
    __tablename__ = "career_scores"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    career_path_id = db.Column(db.Integer, db.ForeignKey("career_paths.id"), nullable=False)
    score = db.Column(db.Float, default=0.0)
    matched_skills = db.Column(db.Text)  # JSON
    gap_skills = db.Column(db.Text)  # JSON
    curriculum_covered = db.Column(db.Text)  # JSON — skills covered by courses
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    career_path = db.relationship("CareerPath")


class Roadmap(db.Model):
    __tablename__ = "roadmaps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    career_path_id = db.Column(db.Integer, db.ForeignKey("career_paths.id"), nullable=True)  # Nullable for non-tech roadmaps
    roadmap_type = db.Column(db.String(20), default="tech")  # "tech" or "nontech"
    content = db.Column(db.Text)  # Full JSON roadmap from LLM
    guide_content = db.Column(db.Text, nullable=True)  # JSON visual knowledge graph
    status = db.Column(db.String(20), default="approved")  # Phase 1: auto-approved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    career_path = db.relationship("CareerPath")
    milestones = db.relationship("Milestone", backref="roadmap", cascade="all, delete-orphan",
                                 order_by="Milestone.order")
    projects = db.relationship("CareerProject", backref="roadmap", cascade="all, delete-orphan",
                               order_by="CareerProject.order")
    chat_messages = db.relationship("ChatMessage", backref="roadmap", cascade="all, delete-orphan",
                                    order_by="ChatMessage.created_at")


class NonTechProfile(db.Model):
    """Stores intake data for non-tech background users."""
    __tablename__ = "nontech_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    background_field = db.Column(db.String(150))   # e.g. "Leather Engineering"
    target_career = db.Column(db.String(150))       # e.g. "Digital Marketer"
    interests = db.Column(db.Text)                  # JSON list
    existing_skills = db.Column(db.Text)            # JSON list
    hobbies = db.Column(db.Text)                    # free text
    english_level = db.Column(db.String(20), default="intermediate")  # beginner/intermediate/advanced
    hours_per_week = db.Column(db.Integer, default=10)
    learning_goal = db.Column(db.Text)              # short text goal
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_interests(self):
        try:
            return json.loads(self.interests) if self.interests else []
        except (json.JSONDecodeError, TypeError):
            return []

    def get_existing_skills(self):
        try:
            return json.loads(self.existing_skills) if self.existing_skills else []
        except (json.JSONDecodeError, TypeError):
            return []


class Milestone(db.Model):
    __tablename__ = "milestones"

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("roadmaps.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_url = db.Column(db.String(500))
    resource_type = db.Column(db.String(20))  # udemy / youtube / project / article
    estimated_hours = db.Column(db.Float, default=1.0)
    order = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    clicked = db.Column(db.Boolean, default=False)  # Track if user clicked the link
    # Phase-based journey map fields
    phase_number = db.Column(db.Integer, default=1)
    phase_title = db.Column(db.String(100), default="Foundation")
    phase_description = db.Column(db.Text, default="")
    card_type = db.Column(db.String(20), default="core")  # core / project / resource / checkpoint
    learning_goal = db.Column(db.Text, default="")
    success_criteria = db.Column(db.Text, default="")
    practice_tasks = db.Column(db.Text, default="[]")  # JSON list
    resource_title = db.Column(db.String(180), default="")
    requires = db.Column(db.String(140), default="")
    unlocks = db.Column(db.String(140), default="")

    def get_practice_tasks(self):
        try:
            return json.loads(self.practice_tasks) if self.practice_tasks else []
        except (json.JSONDecodeError, TypeError):
            return []


class CareerProject(db.Model):
    __tablename__ = "career_projects"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("roadmaps.id"), nullable=False)
    career_path_id = db.Column(db.Integer, db.ForeignKey("career_paths.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    difficulty = db.Column(db.String(20), default="beginner")  # beginner / intermediate / advanced
    summary = db.Column(db.Text, default="")
    features = db.Column(db.Text, default="[]")  # JSON list
    skills_used = db.Column(db.Text, default="[]")  # JSON list
    deliverables = db.Column(db.Text, default="[]")  # JSON list
    resource_url = db.Column(db.String(500), default="")
    estimated_hours = db.Column(db.Float, default=8)
    portfolio_value = db.Column(db.Text, default="")
    order = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    career_path = db.relationship("CareerPath")

    def get_features(self):
        return _loads_json_list(self.features)

    def get_skills_used(self):
        return _loads_json_list(self.skills_used)

    def get_deliverables(self):
        return _loads_json_list(self.deliverables)


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("roadmaps.id"), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("roadmaps.id"), nullable=False)
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TutorMessage(db.Model):
    """Stores global AI Tutor chat history for a user."""
    __tablename__ = "tutor_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class VisualLearnerItem(db.Model):
    """Stores generated Visual Learner outputs for a user."""
    __tablename__ = "visual_learner_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    input_text = db.Column(db.Text, nullable=False)
    visual_url = db.Column(db.String(500), nullable=False)
    request_id = db.Column(db.String(120))
    word_count = db.Column(db.Integer, default=0)
    source = db.Column(db.String(30), default="visual_learner")  # visual_learner / tutor
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudySession(db.Model):
    """Stores individual study sessions logged by a user against a milestone."""
    __tablename__ = "study_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("roadmaps.id"), nullable=False)
    milestone_id = db.Column(db.Integer, db.ForeignKey("milestones.id"), nullable=True)
    hours_logged = db.Column(db.Float, default=1.0)
    notes = db.Column(db.Text, default="")
    session_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    milestone = db.relationship("Milestone", foreign_keys=[milestone_id])
    roadmap = db.relationship("Roadmap", foreign_keys=[roadmap_id])


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), default="success")  # success / active / pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def log_activity(user_id, action, status="success"):
    """Helper to log a user action."""
    try:
        log = ActivityLog(user_id=user_id, action=action, status=status)
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Failed to log activity: {e}")
