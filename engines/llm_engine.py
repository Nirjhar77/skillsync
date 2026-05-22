"""
LLM Engine — Builds enriched prompts including the student's upcoming university courses,
then generates personalized roadmaps and handles contextual chat via Groq API.
"""

import os
import json
import traceback
from flask import current_app
from groq import Groq
from openai import OpenAI
from engines.curriculum_engine import get_upcoming_courses, identify_skill_gaps, get_covered_skills


def _get_client(key_type="journey"):
    """
    Create a Groq client using the appropriate dedicated API key.
    key_type options:
      - 'journey'  → GROQ_API_KEY_JOURNEY  (Start Journey: roadmaps, career suggestions)
      - 'visual'   → GROQ_API_KEY_VISUAL   (Visual Guide ONLY)
      - 'projects' → GROQ_API_KEY_PROJECTS (Projects & Chat/Tutor)
    Falls back to the generic GROQ_API_KEY if the dedicated key is missing.
    """
    key_map = {
        "journey":  "GROQ_API_KEY_JOURNEY",
        "visual":   "GROQ_API_KEY_VISUAL",
        "projects": "GROQ_API_KEY_PROJECTS",
    }
    config_key = key_map.get(key_type, "GROQ_API_KEY_JOURNEY")
    api_key = (
        current_app.config.get(config_key)
        or os.environ.get(config_key)
    )
    if not api_key:
        raise ValueError(
            f"{config_key} is not set. Please add it to your .env file. "
            f"Do NOT use the generic GROQ_API_KEY — that key is reserved exclusively for the Aptitude section."
        )
    return Groq(api_key=api_key)


def _get_openrouter_client():
    """Create an OpenRouter client using the OpenAI SDK."""
    import os
    api_key = current_app.config.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set. Please add it to your .env file.")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def build_roadmap_prompt(profile, career_path, score_details, user_courses):
    """
    Build an enriched prompt that includes the student's curriculum context.
    """
    # Gather student info
    interests = profile.get_interests()
    user_skills = [(s.skill_name, s.proficiency) for s in profile.skills]

    # Get upcoming courses with skills
    upcoming = get_upcoming_courses(user_courses, profile.semester)
    upcoming_text = ""
    if upcoming:
        for c in upcoming:
            skills_str = ", ".join(f"{s} ({l})" for s, l in c["skills"].items())
            upcoming_text += f"  - {c['code']}: {c['name']} (Semester {c['semester']}) → Skills: {skills_str}\n"
    else:
        upcoming_text = "  No upcoming courses selected.\n"

    # Get gap vs covered skills
    gap_skills = score_details.get("gap_skills", [])
    covered = score_details.get("covered_by_curriculum", {})

    covered_text = ""
    if covered:
        for skill, info in covered.items():
            covered_text += f"  - {skill}: covered by {info['source']} ({info['type']})\n"
    else:
        covered_text = "  None identified.\n"

    gap_text = ", ".join(gap_skills) if gap_skills else "None — strong match!"

    # Build tools text
    tools = career_path.get_recommended_tools()
    tools_text = ", ".join(tools) if tools else "N/A"

    prompt = f"""You are a career advisor specializing in creating personalized learning roadmaps for undergraduate students.

=== STUDENT PROFILE ===
- Major: {profile.major}
- Current Semester: {profile.semester} of {profile.total_semesters}
- Location: {profile.location or 'Not specified'}
- Available Study Hours/Week: {profile.hours_per_week}
- Existing Skills: {', '.join(f'{s} ({p})' for s, p in user_skills) if user_skills else 'None listed'}
- Interests: {', '.join(interests) if interests else 'Not specified'}

=== UPCOMING UNIVERSITY COURSES ===
{upcoming_text}

=== TARGET CAREER: {career_path.title} ===
- Category: {career_path.category}
- Description: {career_path.description}
- Recommended Tools: {tools_text}
- Salary Range: {career_path.avg_salary_range}
- Growth Outlook: {career_path.growth_outlook}

=== SKILL ANALYSIS ===
Match Score: {score_details['score']}/100

Skills ALREADY COVERED by curriculum (DO NOT recommend courses for these — suggest projects instead):
{covered_text}

Skill GAPS to fill (student needs to learn these outside of class):
{gap_text}

=== INSTRUCTIONS ===
Generate a comprehensive, phase-based learning roadmap with 24-35 milestones total, grouped into exactly 4-5 phases.

Each phase MUST have the following milestone counts (scale up within these ranges based on career complexity):
- Phase 1: Foundation       → 5-7 milestones  (prerequisites, language basics, core math/theory)
- Phase 2: Core Skills      → 10-14 milestones (domain-specific skills — this is the densest phase)
- Phase 3: Build & Practice → 5-7 milestones  (projects, integration exercises)
- Phase 4: Portfolio        → 4-5 milestones  (2-3 recruiter-ready showcase projects + a README/deployment step)
- Phase 5: Job Prep         → 3-4 milestones  (resume, GitHub, interview prep, networking)

Phase titles should be adapted to the career path but follow this intent:
- Phase 1: Foundation
- Phase 2: Core Skills
- Phase 3: Build & Practice
- Phase 4: Portfolio
- Phase 5: Job Prep

For each milestone, choose the most appropriate card_type:
- "core" → Essential, must-do skill or concept
- "project" → Hands-on build task (at least 6 across the roadmap, mostly in phases 3-4)
- "resource" → Optional but strongly recommended reading/watching
- "checkpoint" → A self-assessment or milestone review point (at least 1 per phase)

IMPORTANT RULES:
- For skills COVERED by upcoming courses, suggest PROJECTS instead of separate courses
- Prioritize FREE resources (YouTube, freeCodeCamp, Khan Academy)
- Order milestones from foundational → advanced within each phase
- Include at least 3 project-type milestones total
- Tailor the timeline to {profile.hours_per_week} hours/week
- For each milestone, fill "requires" with the short name of the prerequisite skill/step (or empty string if first)
- For each milestone, fill "unlocks" with the short name of what completing it enables next (or empty string if last)

Return ONLY valid JSON format exactly matching this schema. Do NOT include markdown codeblocks or any conversational text:
{{
  "roadmap_title": "Your Path to Becoming a {career_path.title}",
  "hero_subtitle": "One personalized sentence about why this roadmap suits this student based on their background and interests.",
  "summary": "Brief 2-sentence personalized summary",
  "estimated_total_weeks": <number>,
  "readiness_start": <integer between 10 and 50 representing estimated readiness percent before starting>,
  "readiness_end": <integer between 65 and 95 representing estimated readiness percent after completing>,
  "outcome_roles": ["Entry-level job title 1", "Entry-level job title 2"],
  "phases": [
    {{
      "phase_number": 1,
      "phase_title": "Foundation",
      "phase_description": "One sentence describing what this phase achieves",
      "milestones": [
        {{
          "title": "Milestone title",
          "description": "What to learn and why",
          "estimated_hours": <number>,
          "resource_type": "youtube|udemy|project|article",
          "resource_url": "https://...",
          "card_type": "core|project|resource|checkpoint",
          "requires": "Short name of skill/milestone this builds on, or empty string",
          "unlocks": "Short name of skill/topic this milestone unlocks, or empty string",
          "order": 1
        }}
      ]
    }}
  ]
}}"""

    return prompt


def generate_roadmap(profile, career_path, score_details, user_courses):
    """
    Generate a personalized roadmap using Groq API.

    Returns:
        dict: Parsed roadmap JSON, or None on error
        str: Error message if any
    """
    try:
        client = _get_client(key_type="journey")  # Key 1: Start Journey
        prompt = build_roadmap_prompt(profile, career_path, score_details, user_courses)

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Using Groq's blazing fast, free Llama 3.3 model
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content.strip()
        roadmap_data = json.loads(text)
        return roadmap_data, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse AI response as JSON: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        return None, f"AI generation failed: {str(e)}"


def chat_with_context(roadmap, profile, career_path, user_message, chat_history=None):
    """
    Send a contextual chat message about the roadmap.
    """
    try:
        client = _get_client(key_type="projects")  # Key 3: Chat/Projects

        # Build context
        history_text = ""
        if chat_history:
            for msg in chat_history[-10:]:  # Last 10 messages for context window
                role = "Student" if msg.role == "user" else "Advisor"
                history_text += f"{role}: {msg.content}\n"

        # Get milestone progress
        milestones = roadmap.milestones
        completed = sum(1 for m in milestones if m.completed)
        total = len(milestones)

        prompt = f"""You are a helpful career advisor assistant. You are helping a student who is working towards becoming a {career_path.title}.

CONTEXT:
- Student: {profile.major} major, Semester {profile.semester}
- Career Target: {career_path.title}
- Roadmap Progress: {completed}/{total} milestones completed
- Student's Skills: {', '.join(s.skill_name for s in profile.skills) if profile.skills else 'Not listed'}

CONVERSATION HISTORY:
{history_text if history_text else 'No previous messages.'}

Student's Question: {user_message}

Provide a helpful, concise, and encouraging response. If they ask about specific resources, suggest real links. If they seem stuck, offer practical next steps. Keep your response under 200 words unless they ask for something detailed."""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
        )

        return completion.choices[0].message.content.strip(), None

    except Exception as e:
        traceback.print_exc()
        return None, f"Chat failed: {str(e)}"


def generate_tech_career_suggestions(profile, user_courses):
    """
    Generate 3-5 hyper-personalized tech career suggestions for a tech student based on their courses.
    """
    try:
        client = _get_client(key_type="journey")  # Key 1: Start Journey

        courses_list = [c.course_name for c in user_courses]
        courses_text = ", ".join(courses_list) if courses_list else "Basic core CS subjects"
        interests_text = ", ".join(json.loads(profile.interests)) if profile.interests else "General Software"

        prompt = f"""You are a top-tier tech career counselor.

=== STUDENT PROFILE ===
- Major/Department: {profile.major or 'Computer Science'}
- Current Semester: {profile.semester or 'Unknown'}
- Interests: {interests_text}
- Completed/Current Courses: {courses_text}
- Preferred Study Hours/Week: {profile.hours_per_week or 10}

=== YOUR TASK ===
Based ONLY on their specific courses, major, and interests, suggest exactly 4 realistic, highly-specific tech careers they should consider. Do not suggest generic roles like "Software Engineer" if they have highly specialized courses (e.g., if they took Cryptography, suggest Security Engineer).

For each career:
1. Provide the exact title.
2. Write a 2-sentence description of the job.
3. Write a personalized 2-sentence explanation of EXACTLY WHY this fits them based on the specific courses and interests they selected.

Return ONLY valid JSON matching this schema:
{{
  "suggestions": [
    {{
      "title": "Job Title",
      "description": "What they do.",
      "why_it_fits": "Why it matches their profile."
    }}
  ]
}}"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content.strip()
        suggestions_data = json.loads(text)
        return suggestions_data, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"AI generation failed: {str(e)}"


def generate_career_suggestions(nt_profile):
    """
    Generate 5-6 tech career suggestions tailored to a non-tech user's background.

    Args:
        nt_profile: NonTechProfile model instance

    Returns:
        dict: Parsed JSON with career suggestions, or None on error
        str: Error message if any
    """
    try:
        client = _get_client(key_type="journey")  # Key 1: Start Journey

        interests = nt_profile.get_interests()
        existing_skills = nt_profile.get_existing_skills()

        interests_text = ", ".join(interests) if interests else "Not specified"
        skills_text = ", ".join(existing_skills) if existing_skills else "None listed"

        prompt = f"""You are a career counselor specializing in helping people transition from non-tech backgrounds into the tech industry.

=== PERSON'S PROFILE ===
- Current Background / Field of Study: {nt_profile.background_field or 'Not specified'}
- Personal Interests & Passions: {interests_text}
- Existing Skills: {skills_text}
- Hobbies: {nt_profile.hobbies or 'Not mentioned'}
- English Language Level: {nt_profile.english_level or 'Intermediate'}
- Their Overall Goal: {nt_profile.learning_goal or 'Enter the tech industry'}

=== YOUR TASK ===
Based ONLY on their specific background, interests, and existing skills, suggest exactly 5 or 6 realistic, high-demand tech careers they should consider transitioning into.

For each career:
1. Provide the exact title (e.g., "UX/UI Designer", "Data Analyst", "Digital Marketer").
2. Write a 2-sentence description of what the job actually entails.
3. Write a highly personalized 2-3 sentence explanation of EXACTLY WHY this fits them based on the hobbies, skills, and background provided.

Return ONLY valid JSON matching this exact schema. Do not include markdown, code blocks, or conversational text:
{{
  "suggestions": [
    {{
      "title": "Job Title",
      "description": "What they do.",
      "why_it_fits": "Why it matches their background/hobbies."
    }}
  ]
}}"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Using Groq's fast, free endpoint
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content.strip()
        suggestions_data = json.loads(text)
        return suggestions_data, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse AI response as JSON: {str(e)}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"AI generation failed: {str(e)}"


def generate_nontech_roadmap(nt_profile):
    """
    Generate a beginner-friendly roadmap for a non-tech background user.
    No mention of university courses or semesters — purely interest/goal driven.

    Args:
        nt_profile: NonTechProfile model instance

    Returns:
        dict: Parsed roadmap JSON, or None on error
        str: Error message if any
    """
    try:
        client = _get_client(key_type="journey")  # Key 1: Start Journey

        interests = nt_profile.get_interests()
        existing_skills = nt_profile.get_existing_skills()

        interests_text = ", ".join(interests) if interests else "Not specified"
        skills_text = ", ".join(existing_skills) if existing_skills else "None listed"

        prompt = f"""You are a career transition advisor helping someone with NO tech background break into the tech industry.

=== PERSON'S PROFILE ===
- Current Background / Field of Study: {nt_profile.background_field or 'Not specified'}
- Tech Career They Want to Enter: {nt_profile.target_career or 'Not specified'}
- Personal Interests & Passions: {interests_text}
- Existing Skills: {skills_text}
- Hobbies: {nt_profile.hobbies or 'Not mentioned'}
- English Language Level: {nt_profile.english_level or 'Intermediate'}
- Available Study Hours Per Week: {nt_profile.hours_per_week}
- Their Learning Goal: {nt_profile.learning_goal or 'Enter the tech industry'}

=== YOUR TASK ===
Create a complete, beginner-friendly, step-by-step learning roadmap for this person.

CRITICAL RULES:
- This person has NO computer science or programming background. Start from absolute basics if needed.
- DO NOT mention university courses, semesters, or academic curricula.
- Tailor every step to their specific background and interests. Use examples they can relate to.
- Suggest FREE resources wherever possible (YouTube, freeCodeCamp, Google Digital Garage, Coursera free audit, etc.)
- Include at least 2 hands-on practice tasks or mini-projects.
- Be encouraging — this person is making a career change, acknowledge it.
- Realistically schedule steps based on {nt_profile.hours_per_week} hours/week.
- If their English level is below Intermediate, suggest easier resources or Bengali/local resources where possible.

Generate 7-12 milestones that take this person from their current position to being job-ready or freelance-ready in their chosen field.

Return ONLY valid JSON matching this exact schema. No markdown, no extra text:
{{
  "roadmap_title": "Your Path to Becoming a {nt_profile.target_career or 'Tech Professional'}",
  "summary": "2-sentence personalized summary of what this roadmap covers and why it suits them",
  "estimated_total_weeks": <number>,
  "milestones": [
    {{
      "title": "Step title",
      "description": "What to learn, why it matters for their goal, and how it connects to their background",
      "estimated_hours": <number>,
      "resource_type": "youtube|udemy|article|project",
      "resource_url": "https://...",
      "order": 1
    }}
  ]
}}"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Using Groq's fast, free endpoint
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content.strip()
        roadmap_data = json.loads(text)
        return roadmap_data, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse AI response as JSON: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        return None, f"AI generation failed: {str(e)}"


def analyze_career_overview(career_path):
    """
    Generate a detailed overview and insights for a specific career path.
    """
    try:
        client = _get_client(key_type="journey")  # Key 1: Start Journey

        tools = career_path.get_recommended_tools()
        tools_text = ", ".join(tools) if tools else "Various industry tools"

        prompt = f"""You are a senior career advisor and industry expert.
Your task is to provide a comprehensive, realistic overview of the following tech career:

=== TARGET CAREER ===
- Title: {career_path.title}
- Category: {career_path.category}
- Base Description: {career_path.description}
- Recommended Tools: {tools_text}
- Salary Range: {career_path.avg_salary_range}
- Growth Outlook: {career_path.growth_outlook}

Generate a highly detailed intelligence report for a student considering this path.
Do not hallucinate; use standard industry realities.

Return ONLY valid JSON matching this exact schema:
{{
  "overview": "A compelling 3-4 sentence paragraph explaining what this role actually does day-to-day and its impact on a business.",
  "core_responsibilities": [
    "Specific task 1",
    "Specific task 2",
    "Specific task 3",
    "Specific task 4"
  ],
  "tech_stack": [
    "Language/Tool 1",
    "Language/Tool 2",
    "Language/Tool 3"
  ],
  "market_reality": {{
    "salary_context": "Explanation of the salary trajectory (e.g., entry level vs senior).",
    "demand_context": "Why is this role in demand right now?",
    "entry_barrier": "What makes it hard or easy to break into this field?"
  }},
  "similar_careers": [
    {{
      "title": "Alternative Job Title 1",
      "reason": "Why someone who likes the target career might also like this."
    }},
    {{
      "title": "Alternative Job Title 2",
      "reason": "Why someone who likes the target career might also like this."
    }}
  ]
}}"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content.strip()
        overview_data = json.loads(text)
        return overview_data, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse AI response as JSON: {str(e)}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"AI generation failed: {str(e)}"


def generate_visual_guide(career_path):
    """Generate a structured visual knowledge graph for a career path."""
    try:
        client = _get_client(key_type="visual")  # Key 2: Visual Guide ONLY
        tools = career_path.get_recommended_tools()
        tools_text = ", ".join(tools) if tools else "Various industry tools"

        prompt = f"""You are building a comprehensive visual knowledge roadmap for: {career_path.title}
Career Description: {career_path.description}
Key Tools: {tools_text}

Generate a DETAILED roadmap.sh-style knowledge graph with 8-10 major sections covering EVERYTHING a professional in this field needs to know.
Each section must have EXACTLY 10 topics:
- 5 topics with "side": "left"
- 5 topics with "side": "right"

Do not make thin sections. If a domain area seems to have fewer than 10 obvious topics,
split it into concrete subskills, tools, workflows, examples, mistakes, or practice tasks
that a learner genuinely needs for this career. Avoid filler and avoid generic labels.

Sections should cover the full learning arc, for example:
- Foundations & Prerequisites
- Core Language/Tools  
- Domain-Specific Concepts
- Frameworks & Libraries
- System Design / Architecture
- Advanced Topics
- Projects & Portfolio
- Soft Skills & Best Practices
- Career Preparation

Assign phase numbers 1-5 in learning order (multiple sections can share a phase number).

Return ONLY valid JSON (no markdown, no explanation):
{{
  "title": "{career_path.title}",
  "description": "1 concise sentence summarizing the roadmap",
  "sections": [
    {{
      "id": "unique_snake_case_id",
      "label": "Section Name",
      "phase": 1,
      "order": 1,
      "topics": [
        {{
          "id": "unique_snake_case_id",
          "label": "Topic Name",
          "side": "left|right",
          "type": "required|optional|tool|project",
          "importance": "critical|important|good_to_know"
        }}
      ]
    }}
  ]
}}"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=7000,
            response_format={"type": "json_object"},
        )
        guide_data = json.loads(completion.choices[0].message.content.strip())
        return guide_data, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse guide JSON: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        return None, f"Guide generation failed: {str(e)}"


def explain_topic(career_title, topic_label, section_label=""):
    """Live AI explanation for a clicked topic node in the Visual Guide."""
    try:
        client = _get_client(key_type="visual")  # Key 2: Visual Guide ONLY
        context = f" in the context of {section_label}" if section_label else ""

        prompt = f"""You are a top-tier tech educator explaining a topic on a career roadmap.
Career Path: {career_title}
Topic: {topic_label}{context}

Provide a comprehensive explanation for a student who just clicked this topic.
Be specific, practical, and encouraging. Only suggest freely available resources.

Return ONLY valid JSON:
{{
  "overview": "2-3 sentences explaining what this topic is",
  "why_it_matters": "2-3 sentences on why this matters for {career_title}",
  "how_to_learn": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
  "resources": [
    {{"title": "Resource name", "url": "https://...", "type": "youtube|article|course|docs"}},
    {{"title": "Resource name 2", "url": "https://...", "type": "youtube|article|course|docs"}}
  ],
  "common_mistakes": ["Mistake 1 to avoid", "Mistake 2 to avoid"],
  "estimated_time": "e.g. 1-2 weeks at 10 hrs/week"
}}"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        explanation = json.loads(completion.choices[0].message.content.strip())
        return explanation, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse explanation JSON: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        return None, f"Explanation failed: {str(e)}"


def generate_weekly_checkin(profile, career_path, sessions_this_week, completed_this_week, total_hours_logged):
    """
    Generate an AI weekly check-in report based on the student's study sessions and milestone progress.
    Uses Key 1 (Journey) since it's a roadmap-context function.
    """
    try:
        client = _get_client(key_type="journey")  # Key 1: Start Journey

        sessions_text = ""
        if sessions_this_week:
            for s in sessions_this_week:
                ms_name = s.milestone.title if s.milestone else "General Study"
                sessions_text += f"  - {s.session_date}: {s.hours_logged}h on '{ms_name}'"
                if s.notes:
                    sessions_text += f" — Notes: {s.notes}"
                sessions_text += "\n"
        else:
            sessions_text = "  No sessions logged this week.\n"

        completed_text = ""
        if completed_this_week:
            for m in completed_this_week:
                completed_text += f"  - {m.title} (Phase {m.phase_number}: {m.phase_title})\n"
        else:
            completed_text = "  No milestones completed this week.\n"

        prompt = f"""You are an encouraging and insightful career advisor reviewing a student's weekly study progress.

=== STUDENT PROFILE ===
- Major: {profile.major}
- Semester: {profile.semester}
- Target Career: {career_path.title if career_path else 'Not selected'}
- Total Hours Logged All-Time: {total_hours_logged:.1f}h

=== THIS WEEK'S STUDY SESSIONS ===
{sessions_text}

=== MILESTONES COMPLETED THIS WEEK ===
{completed_text}

=== YOUR TASK ===
Write a personalized, warm, and data-driven weekly check-in report for this student.

Return ONLY valid JSON matching this exact schema. No markdown, no extra text:
{{
  "summary": "2-3 sentence personalized summary of how their week went, referencing specific sessions/milestones",
  "accomplishments": ["Specific thing they accomplished 1", "Specific thing 2", "Specific thing 3"],
  "next_focus": ["Top priority milestone/skill to focus on next week 1", "Priority 2", "Priority 3"],
  "velocity_note": "1-2 sentences on their pace — are they on track, ahead, or behind? Be specific.",
  "motivational_message": "A short, punchy, personalized motivational message (1 sentence). Reference their career goal."
}}"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content.strip()
        checkin_data = json.loads(text)
        return checkin_data, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse check-in JSON: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        return None, f"Weekly check-in failed: {str(e)}"


def generate_career_projects(profile, career_path, roadmap_data):
    """
    Generate beginner/intermediate/advanced portfolio projects for a career path.
    Uses Key 3 (Projects & Chat) to keep it isolated from journey rate limits.
    """
    try:
        client = _get_client(key_type="projects")  # Key 3: Projects & Chat

        user_skills = [(s.skill_name, s.proficiency) for s in profile.skills]
        career_title = career_path.title
        tools = career_path.get_recommended_tools()
        tools_text = ", ".join(tools) if tools else "Various industry tools"

        # Extract milestone titles from the roadmap for context
        milestone_titles = []
        for phase in roadmap_data.get("phases", []):
            for m in phase.get("milestones", []):
                if m.get("card_type") in ("project", "core"):
                    milestone_titles.append(m.get("title", ""))
        milestones_text = ", ".join(milestone_titles[:15]) if milestone_titles else "Core skills for " + career_title

        prompt = f"""You are a senior software engineer and career coach designing a portfolio project board.

=== STUDENT PROFILE ===
- Major: {profile.major}
- Current Semester: {profile.semester}
- Existing Skills: {', '.join(f'{s} ({p})' for s, p in user_skills) if user_skills else 'None listed'}

=== TARGET CAREER: {career_title} ===
- Key Tools: {tools_text}
- Relevant Roadmap Skills: {milestones_text}

=== YOUR TASK ===
Generate exactly 9 portfolio projects (3 beginner, 3 intermediate, 3 advanced) that a student targeting this career should build.

For each project:
1. Make it specific, real, and buildable — not generic (e.g. NOT "To-Do App").
2. Tailor it to the exact career path and tools.
3. Include concrete features the student should implement.
4. Specify what skills it demonstrates and why recruiters will care.

Return ONLY valid JSON matching this exact schema. No markdown, no extra text:
{{
  "projects": [
    {{
      "title": "Specific project name",
      "difficulty": "beginner|intermediate|advanced",
      "summary": "2-sentence description of what this project is and what it does",
      "features": ["Feature 1", "Feature 2", "Feature 3"],
      "skills_used": ["Skill 1", "Skill 2"],
      "deliverables": ["Deliverable 1", "Deliverable 2"],
      "resource_url": "https://...",
      "estimated_hours": <number>,
      "portfolio_value": "1-2 sentences on why this impresses recruiters",
      "order": <1-9>
    }}
  ]
}}"""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        text = completion.choices[0].message.content.strip()
        projects_data = json.loads(text)
        return projects_data, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse projects JSON: {str(e)}"
    except Exception as e:
        traceback.print_exc()
        return None, f"Projects generation failed: {str(e)}"
