from app import create_app
app = create_app()
with app.app_context():
    from database.models import db
    from sqlalchemy import text
    with db.engine.connect() as conn:
        conn.execute(text("UPDATE roadmaps SET guide_content = NULL"))
        conn.commit()
        print("Cleared all guide_content — will regenerate fresh on next visit")
