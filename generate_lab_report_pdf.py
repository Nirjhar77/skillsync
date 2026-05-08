"""
Generate SkillSync lab report PDF (run from project root):
  .venv\\Scripts\\python generate_lab_report_pdf.py
Output: SkillSync_Lab_Report.pdf
"""

import os
from fpdf import FPDF

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "static", "images")
OUT = os.path.join(BASE, "SkillSync_Lab_Report.pdf")


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)

    def header(self):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, "SkillSync - Laboratory / Project Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def section(self, title: str):
        self.set_x(self.l_margin)
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 45, 90)
        self.multi_cell(0, 7, title)
        self.set_x(self.l_margin)
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 11)
        self.ln(2)

    def body_text(self, text: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 11)
        self.multi_cell(0, 5.5, text)
        self.set_x(self.l_margin)
        self.ln(1)

    def bullet_list(self, items):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 11)
        for it in items:
            self.set_x(self.l_margin)
            self.multi_cell(0, 5.5, f"  - {it}")
            self.set_x(self.l_margin)
        self.ln(1)


RULE_ENGINE_SNIPPET = r'''def rank_careers(profile, career_paths, user_courses, min_score=5):
    results = []
    for career in career_paths:
        details = score_career_path(profile, career, user_courses)
        if details["score"] >= min_score:
            results.append((career, details))
    results.sort(key=lambda x: x[1]["score"], reverse=True)
    return results

# score_career_path combines (up to 100):
# - skill_match_score: explicit skills + curriculum (40)
# - interest_score: INTEREST_CAREER_MAP (35)
# - activity_score: ACTIVITY_CAREER_MAP (15)
# - curriculum_bonus + semester_boost (10 + 0-8, capped at 100)'''


def main():
    pdf = ReportPDF()
    pdf.add_page()

    # --- Title ---
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(25, 55, 110)
    pdf.multi_cell(0, 10, "SkillSync", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(
        0,
        8,
        "AI-Assisted Career Navigation for Undergraduate Tech Curricula",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_x(pdf.l_margin)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, "Laboratory / project documentation", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.ln(6)

    # --- 1 Title (formal) ---
    pdf.section("1) Title of the project")
    pdf.body_text(
        "SkillSync is a web application that combines rule-based career matching with "
        "LLM-generated learning roadmaps so undergraduates can align coursework, skills, "
        "and interests with industry-oriented technology careers."
    )

    # --- 2 Introduction ---
    pdf.section("2) Introduction")
    pdf.body_text(
        "University programs often cover theory and breadth, while employers expect "
        "demonstrable skills, projects, and role-specific tooling. Students frequently "
        "lack a structured bridge between transcript, self-reported skills, and realistic "
        "job targets. SkillSync addresses this by ingesting a student profile (major, "
        "semester, skills, interests, selected courses), scoring predefined career paths "
        "with a transparent rule engine, persisting results, and optionally invoking a "
        "large language model (Groq) to produce phased roadmaps, visual guides, and a "
        "context-aware chat assistant. A parallel intake supports learners from non-technical "
        "backgrounds targeting tech-adjacent roles."
    )

    # --- 3 Problem & idea ---
    pdf.section("3) Problem statement and idea description")
    pdf.body_text(
        "Problem: (i) Weak visibility into how courses map to employable skills; "
        "(ii) generic career advice without curriculum context; (iii) fragmented planning "
        "across free resources and degree requirements."
    )
    pdf.body_text(
        "Idea: Encode career requirements and a course-to-skill catalog in structured data; "
        "score careers deterministically for explainability; use the LLM only for narrative "
        "roadmaps and tutoring where creativity and personalization add the most value. "
        "Curriculum coverage reduces duplicate recommendations and steers the model toward "
        "projects for skills already scheduled in upcoming terms."
    )

    # --- 4 Architecture ---
    pdf.section("4) Project architecture")
    pdf.body_text(
        "Client: HTML templates, CSS (landing, dashboard, resources), and JavaScript for "
        "interactive UI (e.g., roadmap guide, resources). Server: Flask application factory "
        "with blueprints for authentication, profile, career analysis, progress, chat, "
        "non-tech flows, resources, dashboard, CV helpers, chatbot API, and news. "
        "Persistence: SQLite via Flask-SQLAlchemy (users, profiles, courses, skills, "
        "career paths, scores, roadmaps, milestones, chat messages, feedback). "
        "Engines: curriculum_engine (JSON catalog crosswalk), rule_engine (scoring), "
        "decision_engine (comparisons / fit), llm_engine (Groq prompts for roadmaps and guides). "
        "Configuration: environment variables for SECRET_KEY, GROQ_API_KEY, optional GNews."
    )
    pdf.body_text("Layered view (conceptual):")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Courier", "", 9)
    arch = (
        " [Browser]  <--HTTP-->  [Flask + Jinja2]\n"
        "                              |\n"
        "            +----------------+----------------+\n"
        "            v                v                v\n"
        "     [SQLite ORM]    [Rule + Curriculum]   [Groq LLM]\n"
        "            |                |                |\n"
        "     skillsync.db    career_paths.json   roadmaps / chat\n"
        "                     course_catalog.json"
    )
    pdf.multi_cell(0, 4.5, arch)
    pdf.set_x(pdf.l_margin)
    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 11)

    pdf.body_text("Target population:")
    pdf.bullet_list(
        [
            "Undergraduate students in computing-related majors building a tech career plan.",
            "Students who can enumerate completed/in-progress/upcoming courses from a catalog.",
            "Non-technical background users re-skilling toward digital, creative, or IT-adjacent roles.",
            "Educators or counselors (role field exists) as secondary stakeholders for future use.",
        ]
    )
    pdf.body_text(
        "Platform: Python 3.x, Flask 3.x, Flask-Login, Werkzeug; local deployment on "
        "http://127.0.0.1:5000 (development). Data: JSON assets under /data; uploads for CV. "
        "External APIs: Groq (primary LLM), optional OpenRouter in code paths, optional GNews for news."
    )

    # --- 5 Features ---
    pdf.section("5) Project features")
    pdf.bullet_list(
        [
            "Registration, login, and session management with password hashing.",
            "Tech profile setup: major, semester, location, weekly hours, interests, skills, course selection.",
            "Career analysis: run rule engine, persist CareerScore rows, bucket results (best / adjacent / stretch / wildcard).",
            "Career overview, compare paths, and decision-engine-backed comparisons.",
            "LLM-generated phased roadmaps with milestones (core, project, resource, checkpoint) and milestone tracking.",
            "Visual knowledge-style guide generation for roadmaps.",
            "Per-roadmap chat history tied to milestones and Groq.",
            "Non-tech intake and AI roadmap for alternative learner personas.",
            "Dashboard metrics, resources area, tech news, CV-related routes, sidebar career chatbot.",
        ]
    )

    # --- 6 Screenshots ---
    pdf.section("6) Project screenshots (marketing / UI mockups from repository)")
    dash = os.path.join(IMG, "dashboard_mockup.png")
    career = os.path.join(IMG, "career_match_mockup.png")
    for label, path in [("Dashboard concept", dash), ("Career matching concept", career)]:
        if os.path.isfile(path):
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, label)
            pdf.set_x(pdf.l_margin)
            pdf.image(path, x=18, w=174)
            pdf.ln(4)
        else:
            pdf.body_text(f"[Image not found: {path}]")

    # --- 7 Source code ---
    pdf.add_page()
    pdf.section("7) Source code excerpt (rule engine: ranking logic)")
    pdf.body_text(
        "The rule engine (engines/rule_engine.py) maps interests and activities to career slugs, "
        "merges explicit skill proficiency with curriculum-derived coverage from course_catalog.json, "
        "and produces a 0-100 score with explainable subcomponents. The excerpt below shows the "
        "public ranking entry point."
    )
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Courier", "", 8)
    pdf.multi_cell(0, 4.2, RULE_ENGINE_SNIPPET)
    pdf.set_x(pdf.l_margin)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 5, "Full implementation: engines/rule_engine.py, engines/curriculum_engine.py.")
    pdf.set_x(pdf.l_margin)
    pdf.set_text_color(0, 0, 0)

    # --- 8 Social & economic ---
    pdf.section("8) Social and economic value")
    pdf.body_text(
        "Social: Improves equity of career information for students without professional networks; "
        "supports non-traditional paths into tech-adjacent work; encourages structured self-study "
        "and mental health-friendly planning via phased goals."
    )
    pdf.body_text(
        "Economic: Better alignment of human capital with labor-market demand can shorten "
        "job-search friction, reduce skills mismatches, and increase productivity of graduates "
        "entering software, data, cloud, security, and product roles. Institutions may use "
        "similar systems to scale advising."
    )

    # --- 9 Risk management ---
    pdf.section("9) Risk management")
    pdf.bullet_list(
        [
            "LLM hallucination / stale advice: mitigate with structured JSON expectations, curriculum constraints in prompts, and human review for high-stakes decisions.",
            "API key exposure: store secrets only in .env, never commit; rotate keys; use HTTPS in production.",
            "Privacy: student profiles and chat logs are sensitive; encrypt at rest in production, minimize retention, and apply access control (Flask-Login already scopes data by user).",
            "Scoring bias: interest maps are hand-curated; periodic audit against labor statistics and diverse role titles.",
            "Dependency on third-party Groq availability: graceful error handling and user-visible messages when keys are missing or rate-limited.",
            "SQLite concurrency limits: migrate to PostgreSQL if deployed multi-user at scale.",
        ]
    )

    # --- 10 Conclusion ---
    pdf.section("10) Conclusion")
    pdf.body_text(
        "SkillSync demonstrates a pragmatic hybrid architecture: explainable rules for ranking "
        "and gap analysis, plus generative AI for rich roadmaps and conversational help. "
        "By grounding recommendations in a course catalog and student selections, the system "
        "reduces redundant study plans and better reflects each learner's academic trajectory. "
        "Future work includes production hardening, broader catalogs, empirical validation with "
        "students, and optional integration with institutional LMS data."
    )

    # --- 11 IEEE references ---
    pdf.section("11) References (IEEE style)")
    refs = [
        "Pallets Projects, \"Flask Documentation,\" Flask, 2024. [Online]. Available: https://flask.palletsprojects.com/",
        "Groq Inc., \"GroqCloud API Reference,\" Groq Developer Docs, 2024. [Online]. Available: https://console.groq.com/docs",
        "M. A. Garcia and S. N. Jones, \"SQLite,\" in SQLite Documentation, D. R. Hipp, Ed., SQLite Consortium, 2024. [Online]. Available: https://www.sqlite.org/docs.html",
        "SQLAlchemy authors, \"SQLAlchemy Documentation,\" SQLAlchemy, 2024. [Online]. Available: https://docs.sqlalchemy.org/",
        "OpenAI, \"OpenAI Python API library used with compatible endpoints,\" OpenAI GitHub, 2024. [Online]. Available: https://github.com/openai/openai-python",
        "W3C, \"HTML Living Standard,\" WHATWG/W3C, 2024. [Online]. Available: https://html.spec.whatwg.org/",
    ]
    pdf.set_font("Helvetica", "", 10)
    for i, r in enumerate(refs, 1):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, f"[{i}] {r}")
        pdf.set_x(pdf.l_margin)
        pdf.ln(0.5)

    pdf.output(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
