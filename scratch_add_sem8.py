import json
import os

catalog_path = "data/course_catalog.json"
with open(catalog_path, "r", encoding="utf-8") as f:
    data = json.load(f)

courses = data["courses"]

new_courses = {
    # ECE Semester 8
    "ECE801": {"name": "Advanced Mobile Communication", "semester": 8, "department": "Electronics Engineering", "skills_covered": {"networking": "advanced"}},
    "ECE802": {"name": "Nanoelectronics", "semester": 8, "department": "Electronics Engineering", "skills_covered": {"hardware_design": "advanced"}},
    "ECE803": {"name": "Image Processing", "semester": 8, "department": "Electronics Engineering", "skills_covered": {"algorithms": "advanced", "python": "intermediate"}},
    "ECE804": {"name": "ECE Capstone: Embedded System Design", "semester": 8, "department": "Electronics Engineering", "skills_covered": {"c_plus_plus": "advanced", "iot": "advanced", "project_management": "advanced"}},

    # EEE Semester 8
    "EEE801": {"name": "Advanced Power Electronics", "semester": 8, "department": "Electrical Engineering", "skills_covered": {"hardware_design": "advanced"}},
    "EEE802": {"name": "EEE Capstone: Energy Management Project", "semester": 8, "department": "Electrical Engineering", "skills_covered": {"data_analysis": "intermediate", "project_management": "advanced"}},

    # MECH Semester 8
    "MECH801": {"name": "Advanced Machine Design", "semester": 8, "department": "Mechanical Engineering", "skills_covered": {"autocad": "advanced", "algorithms": "intermediate"}},
    "MECH802": {"name": "Smart Manufacturing", "semester": 8, "department": "Mechanical Engineering", "skills_covered": {"iot": "intermediate", "data_analysis": "beginner"}},
    "MECH803": {"name": "Mechanical Capstone: Renewable Energy Systems", "semester": 8, "department": "Mechanical Engineering", "skills_covered": {"project_management": "advanced", "system_design": "intermediate"}},

    # Cybersecurity Semester 8
    "CYBER801": {"name": "Advanced Cryptography", "semester": 8, "department": "Cybersecurity", "skills_covered": {"cryptography": "advanced", "algorithms": "advanced"}},
    "CYBER802": {"name": "Security Governance", "semester": 8, "department": "Cybersecurity", "skills_covered": {"security_fundamentals": "advanced", "business_analysis": "intermediate"}},
    "CYBER803": {"name": "Cybersecurity Capstone: Threat Simulation Lab", "semester": 8, "department": "Cybersecurity", "skills_covered": {"project_management": "advanced", "incident_response": "advanced", "linux": "advanced"}},

    # Data Science Semester 8
    "DS801": {"name": "Data Engineering Basics", "semester": 8, "department": "Data Science", "skills_covered": {"cloud_computing": "intermediate", "sql": "advanced", "databases": "advanced"}},
    "DS802": {"name": "Data Science Capstone: AI Predictive Modeling", "semester": 8, "department": "Data Science", "skills_covered": {"machine_learning": "advanced", "python": "advanced", "project_management": "advanced"}}
}

# Add only if not already present
for code, details in new_courses.items():
    if code not in courses:
        courses[code] = details

with open(catalog_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Added {len(new_courses)} Sem 8 courses.")
