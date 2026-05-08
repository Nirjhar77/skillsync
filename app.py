import os
from flask import Flask
from flask_login import LoginManager
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance folder exists
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    # --- Database ---
    from database.models import db

    db.init_app(app)

    # --- Login Manager ---
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    from database.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- Blueprints ---
    from routes.auth import auth_bp
    from routes.profile import profile_bp
    from routes.career import career_bp
    from routes.progress import progress_bp
    from routes.chat import chat_bp
    from routes.nontech import nontech_bp
    from routes.resources import resources_bp
    from routes.dashboard import dashboard_bp
    from routes.cv import cv_bp
    from routes.chatbot import chatbot_bp
    from routes.news import news_bp
    from routes.visual_learner import visual_learner_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(career_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(nontech_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(cv_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(visual_learner_bp)

    # --- Create tables ---
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
