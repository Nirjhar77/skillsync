# Lab Report



## 1. Title of the Project
**SkillSync: AI-Powered Career Navigator and Interactive Tech Roadmap Platform**

---

## 2. Introduction
SkillSync is an intelligent career navigation and educational platform designed to bridge the gap between academic curricula and industry requirements. By leveraging Large Language Models (LLMs) and advanced rule-based matching algorithms, SkillSync provides users with personalized learning roadmaps, skills gap analysis, and real-time tech intelligence. The platform acts as an automated career advisor, guiding users step-by-step from their current academic background to their desired tech profession.

---

## 3. Problem Statements and Idea Description

**Problem Statement:**  
University students and junior developers often feel overwhelmed by the vast, rapidly changing landscape of technology. They frequently lack clear, personalized guidance on how to transition from their specific university courses to highly specialized industry roles (e.g., Machine Learning Engineer, Cloud Architect). Existing solutions are either too generic or require expensive human career advising.

**Idea Description:**  
The core idea of SkillSync is to automatically extract a student's academic background (via PDF transcript/curriculum parsing) and match their existing knowledge against the requirements of modern tech careers. The system identifies specific "gap skills" and uses an AI engine to generate a highly personalized, interactive learning roadmap. This roadmap breaks down the journey into manageable phases, complete with a visual knowledge graph and an integrated AI tutor to explain complex topics on demand.

---

## 4. Project Architecture

### → Target Population
*   **Primary:** University students (especially in Computer Science, IT, and Engineering) seeking structured pathways to industry roles.
*   **Secondary:** Recent graduates and junior developers looking to upskill or pivot into specialized tech careers.

### → Platform
*   **Architecture Type:** Client-Server Web Application.
*   **Backend:** Python with the Flask web framework.
*   **Database:** SQLite using SQLAlchemy ORM for relational data management (Users, Profiles, Roadmaps, Milestones).
*   **Frontend:** HTML5, CSS3, and vanilla JavaScript with a modern, glass-morphism aesthetic.
*   **AI Integration:** Groq API utilizing the Llama-3.3-70b model for high-speed, structured JSON generation and natural language processing.
*   **Data Processing:** PyMuPDF (`fitz`) for document extraction and analysis.

---

## 5. Project Features
1.  **Automated Curriculum Parsing:** Users can upload their academic PDFs, which the system parses to extract learned concepts and automatically populate their skill profile.
2.  **Career Matching Engine:** An intelligent algorithm that compares the user's current skills against a database of career paths, calculating a "Readiness Score" and identifying specific gap skills.
3.  **Phased Milestone Roadmap:** A personalized, step-by-step tracker that organizes learning materials into sequential phases with `Required` and `Unlocks` dependencies.
4.  **Visual Knowledge Graph:** An interactive, `roadmap.sh`-style node graph. Topics branch off a central spine, visually demonstrating how different technologies connect.
5.  **Live AI Topic Explainer:** Users can click any node in the visual guide to open a side panel where an AI tutor instantly provides an overview, learning steps, common mistakes, and free resources.

---

## 6. Project Screenshots
*(Note: Please insert the relevant screenshots below)*

### 6.1 Dashboard & Career Navigator
[ Insert Screenshot Here ]

### 6.2 Phased Milestone Roadmap (Start Journey)
[ Insert Screenshot Here ]

### 6.3 Interactive Visual Guide (Node Graph)
[ Insert Screenshot Here ]

### 6.4 Live AI Topic Explanation Panel
[ Insert Screenshot Here ]

---

## 7. Source Code (Key Architectures)

### 7.1 Career Matching Logic (`rule_engine.py`)
This snippet demonstrates how the system calculates the readiness score by comparing user skills with required career skills.
```python
def rank_careers(profile, all_careers):
    user_skills = set(profile.skills) if profile.skills else set()
    scored_careers = []
    
    for career in all_careers:
        required_skills = set(career.required_skills)
        if not required_skills:
            continue
            
        matched = user_skills.intersection(required_skills)
        gap = required_skills.difference(user_skills)
        
        score = (len(matched) / len(required_skills)) * 100
        
        scored_careers.append({
            "career": career,
            "score": round(score, 1),
            "matched_skills": list(matched),
            "gap_skills": list(gap)
        })
        
    scored_careers.sort(key=lambda x: x["score"], reverse=True)
    return scored_careers
```

### 7.2 AI Roadmap Generation (`llm_engine.py`)
This snippet shows how the application securely interfaces with the Groq API to generate structured visual guide data.
```python
def generate_visual_guide(career_path):
    try:
        client = _get_client()
        prompt = f"""You are building a comprehensive visual knowledge roadmap for: {career_path.title}
        Generate a DETAILED knowledge graph with 8-10 major sections covering EVERYTHING a professional needs.
        Return ONLY valid JSON format."""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=5000,
            response_format={"type": "json_object"},
        )
        return json.loads(completion.choices[0].message.content.strip()), None
    except Exception as e:
        return None, f"Guide generation failed: {str(e)}"
```

---

## 8. Social and Economical Value
*   **Social Value:** Democratizes access to high-quality career advising. It levels the playing field for students who may not have access to expensive industry mentors or elite career centers, providing everyone with a clear path to success.
*   **Economical Value:** Saves immense amounts of time by preventing students from learning irrelevant or outdated skills. By accelerating the time it takes to become "job-ready," the platform helps users enter the workforce faster and helps companies find properly trained talent more efficiently.

---

## 9. Risk Management
1.  **Third-Party API Dependency (Groq/LLM):** 
    *   *Risk:* The AI API could go down or rate-limit the application.
    *   *Mitigation:* Implementing robust error handling, loading states, and fallback caching for previously generated roadmaps so the core application remains accessible.
2.  **AI Hallucinations:**
    *   *Risk:* The AI might suggest non-existent tools or incorrect learning paths.
    *   *Mitigation:* Strict JSON schema enforcement and heavily engineered prompts that restrict the AI to suggesting only widely recognized, free industry resources.
3.  **Data Privacy:**
    *   *Risk:* Handling user curriculum data securely.
    *   *Mitigation:* All sensitive PDF parsing happens locally. Personal data is stored locally in SQLite using hashed authentication.

---

## 10. Conclusion
SkillSync successfully demonstrates the powerful intersection of traditional educational data and modern Generative AI. By transforming static course curriculums into dynamic, interactive, and personalized career roadmaps, the platform solves a critical pain point for emerging professionals. The addition of interactive visual node graphs and live AI tutoring proves that automated systems can provide deeply contextual, human-like guidance at scale.

---

## 11. References
[1] Flask Documentation, "Flask: A Python Microframework," Pallets Projects. [Online]. Available: https://flask.palletsprojects.com/.  
[2] Groq API Documentation, "Groq Cloud API," Groq. [Online]. Available: https://console.groq.com/docs.  
[3] Meta AI, "Llama 3: Open Foundation and Chat Models," Meta. [Online]. Available: https://llama.meta.com/.  
[4] SQLAlchemy Documentation, "The Python SQL Toolkit and Object Relational Mapper," SQLAlchemy. [Online]. Available: https://www.sqlalchemy.org/.  
