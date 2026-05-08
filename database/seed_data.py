"""Seed career paths from JSON into the database."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from database.models import db, CareerPath


def seed():
    app = create_app()
    with app.app_context():
        data_path = os.path.join(app.config["DATA_DIR"], "career_paths.json")
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for cp in data["career_paths"]:
            existing = CareerPath.query.filter_by(slug=cp["slug"]).first()
            if existing:
                print(f"  ~ Updating {cp['title']}")
                existing.title = cp["title"]
                existing.category = cp["category"]
                existing.description = cp["description"]
                existing.required_skills = json.dumps(cp["required_skills"])
                existing.recommended_tools = json.dumps(cp["recommended_tools"])
                existing.avg_salary_range = cp["avg_salary_range"]
                existing.growth_outlook = cp["growth_outlook"]
            else:
                print(f"  + Adding {cp['title']}")
                career = CareerPath(
                    slug=cp["slug"],
                    title=cp["title"],
                    category=cp["category"],
                    description=cp["description"],
                    required_skills=json.dumps(cp["required_skills"]),
                    recommended_tools=json.dumps(cp["recommended_tools"]),
                    avg_salary_range=cp["avg_salary_range"],
                    growth_outlook=cp["growth_outlook"],
                )
                db.session.add(career)

        db.session.commit()
        count = CareerPath.query.count()
        print(f"\n[OK] Seeded {count} career paths.")


if __name__ == "__main__":
    seed()
