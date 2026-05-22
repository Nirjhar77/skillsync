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
    # Dedicated keys per section — distributes rate limits across 3 accounts
    GROQ_API_KEY_JOURNEY = os.environ.get("GROQ_API_KEY_JOURNEY", "")
    GROQ_API_KEY_VISUAL = os.environ.get("GROQ_API_KEY_VISUAL", "")
    GROQ_API_KEY_PROJECTS = os.environ.get("GROQ_API_KEY_PROJECTS", "")
    GROQ_API_KEY_APTITUDE = os.environ.get("GROQ_API_KEY_APTITUDE", "")
    THEIRSTACK_API_KEY   = os.environ.get("THEIRSTACK_API_KEY", "")
    ADZUNA_APP_ID        = os.environ.get("ADZUNA_APP_ID", "")
    ADZUNA_API_KEY       = os.environ.get("ADZUNA_API_KEY", "")
    NEWSAPI_KEY          = os.environ.get("NEWSAPI_KEY", "")

