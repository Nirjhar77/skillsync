"""One-time DB migration — run from project root: python migrate_run.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from database.models import db

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text("ALTER TABLE roadmaps ADD COLUMN roadmap_type VARCHAR(20) DEFAULT 'tech'"))
            conn.commit()
            print("[OK] Added roadmap_type column")
        except Exception as e:
            print(f"[SKIP] roadmap_type already exists: {e}")

        try:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS nontech_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    background_field VARCHAR(150),
                    target_career VARCHAR(150),
                    interests TEXT,
                    existing_skills TEXT,
                    hobbies TEXT,
                    english_level VARCHAR(20) DEFAULT 'intermediate',
                    hours_per_week INTEGER DEFAULT 10,
                    learning_goal TEXT,
                    updated_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """))
            conn.commit()
            print("[OK] nontech_profiles table ready")
        except Exception as e:
            print(f"[SKIP] nontech_profiles: {e}")

    print("\n[DONE] Migration complete!")
