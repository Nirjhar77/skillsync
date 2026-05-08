"""Add enriched roadmap/project storage columns."""

import os
import sqlite3

from app import create_app
from database.models import db


def _add_column_if_missing(conn, table, column, ddl):
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def migrate():
    app = create_app()
    with app.app_context():
        db.create_all()
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        db_path = db_uri.replace("sqlite:///", "", 1)
        db_path = os.path.abspath(db_path)

        with sqlite3.connect(db_path) as conn:
            _add_column_if_missing(conn, "milestones", "learning_goal", "learning_goal TEXT DEFAULT ''")
            _add_column_if_missing(conn, "milestones", "success_criteria", "success_criteria TEXT DEFAULT ''")
            _add_column_if_missing(conn, "milestones", "practice_tasks", "practice_tasks TEXT DEFAULT '[]'")
            _add_column_if_missing(conn, "milestones", "resource_title", "resource_title VARCHAR(180) DEFAULT ''")
            _add_column_if_missing(conn, "milestones", "requires", "requires VARCHAR(140) DEFAULT ''")
            _add_column_if_missing(conn, "milestones", "unlocks", "unlocks VARCHAR(140) DEFAULT ''")
            conn.commit()

    print("Project board and enriched milestone storage ready.")


if __name__ == "__main__":
    migrate()
