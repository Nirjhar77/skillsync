import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "skillsync-dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'skillsync.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    NAPKIN_API_KEY = os.environ.get("NAPKIN_API_KEY", "")
    LLM_MODEL = "llama-3.3-70b-versatile"
    DATA_DIR = os.path.join(BASE_DIR, "data")
    GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY", "")
