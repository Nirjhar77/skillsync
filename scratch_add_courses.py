import json
import os

catalog_path = "data/course_catalog.json"
with open(catalog_path, "r", encoding="utf-8") as f:
    data = json.load(f)

courses = data["courses"]

new_courses = {
    # Cybersecurity
    "CYBER101": {"name": "Programming Fundamentals", "semester": 1, "department": "Cybersecurity", "skills_covered": {"python": "beginner", "algorithms": "beginner"}},
    "CYBER102": {"name": "Logic Design", "semester": 1, "department": "Cybersecurity", "skills_covered": {"hardware_design": "beginner"}},
    "CYBER201": {"name": "Data Structures", "semester": 2, "department": "Cybersecurity", "skills_covered": {"data_structures": "intermediate", "algorithms": "intermediate"}},
    "CYBER202": {"name": "Introduction to Networking", "semester": 2, "department": "Cybersecurity", "skills_covered": {"networking": "beginner"}},
    "CYBER301": {"name": "Operating Systems", "semester": 3, "department": "Cybersecurity", "skills_covered": {"linux": "beginner", "system_design": "beginner"}},
    "CYBER302": {"name": "Network Fundamentals", "semester": 3, "department": "Cybersecurity", "skills_covered": {"networking": "intermediate"}},
    "CYBER303": {"name": "Secure Programming Basics", "semester": 3, "department": "Cybersecurity", "skills_covered": {"security_fundamentals": "beginner", "python": "intermediate"}},
    "CYBER401": {"name": "Computer Security", "semester": 4, "department": "Cybersecurity", "skills_covered": {"security_fundamentals": "intermediate"}},
    "CYBER402": {"name": "Cryptography Basics", "semester": 4, "department": "Cybersecurity", "skills_covered": {"cryptography": "beginner", "algorithms": "intermediate"}},
    "CYBER403": {"name": "Database Security", "semester": 4, "department": "Cybersecurity", "skills_covered": {"databases": "intermediate", "security_fundamentals": "intermediate"}},
    "CYBER404": {"name": "Linux Administration", "semester": 4, "department": "Cybersecurity", "skills_covered": {"linux": "intermediate"}},
    "CYBER501": {"name": "Ethical Hacking", "semester": 5, "department": "Cybersecurity", "skills_covered": {"security_fundamentals": "advanced", "networking": "advanced"}},
    "CYBER502": {"name": "Web Security", "semester": 5, "department": "Cybersecurity", "skills_covered": {"security_fundamentals": "advanced", "html_css": "intermediate"}},
    "CYBER503": {"name": "Digital Forensics", "semester": 5, "department": "Cybersecurity", "skills_covered": {"incident_response": "beginner", "linux": "advanced"}},
    "CYBER504": {"name": "Secure Coding", "semester": 5, "department": "Cybersecurity", "skills_covered": {"python": "advanced", "security_fundamentals": "advanced"}},
    "CYBER601": {"name": "Malware Analysis", "semester": 6, "department": "Cybersecurity", "skills_covered": {"security_fundamentals": "advanced", "cryptography": "intermediate"}},
    "CYBER602": {"name": "Incident Response", "semester": 6, "department": "Cybersecurity", "skills_covered": {"incident_response": "intermediate"}},
    "CYBER603": {"name": "Network Security", "semester": 6, "department": "Cybersecurity", "skills_covered": {"networking": "advanced", "security_fundamentals": "advanced"}},
    "CYBER604": {"name": "Cloud Security", "semester": 6, "department": "Cybersecurity", "skills_covered": {"cloud_computing": "intermediate", "security_fundamentals": "advanced"}},
    "CYBER701": {"name": "Penetration Testing", "semester": 7, "department": "Cybersecurity", "skills_covered": {"security_fundamentals": "advanced", "linux": "advanced"}},
    "CYBER702": {"name": "Threat Intelligence", "semester": 7, "department": "Cybersecurity", "skills_covered": {"incident_response": "advanced", "data_analysis": "intermediate"}},
    "CYBER703": {"name": "Reverse Engineering", "semester": 7, "department": "Cybersecurity", "skills_covered": {"algorithms": "advanced", "security_fundamentals": "advanced"}},
    "CYBER704": {"name": "Application Security", "semester": 7, "department": "Cybersecurity", "skills_covered": {"security_fundamentals": "advanced", "api_design": "intermediate"}},

    # Data Science
    "DS101": {"name": "Programming Fundamentals", "semester": 1, "department": "Data Science", "skills_covered": {"python": "beginner", "algorithms": "beginner"}},
    "DS102": {"name": "Calculus", "semester": 1, "department": "Data Science", "skills_covered": {"critical_thinking": "intermediate"}},
    "DS201": {"name": "Data Structures", "semester": 2, "department": "Data Science", "skills_covered": {"data_structures": "intermediate", "python": "intermediate"}},
    "DS202": {"name": "Probability", "semester": 2, "department": "Data Science", "skills_covered": {"statistics": "beginner"}},
    "DS203": {"name": "Statistics I", "semester": 2, "department": "Data Science", "skills_covered": {"statistics": "intermediate", "excel": "intermediate"}},
    "DS204": {"name": "Linear Algebra", "semester": 2, "department": "Data Science", "skills_covered": {"linear_algebra": "intermediate"}},
    "DS301": {"name": "Database Systems", "semester": 3, "department": "Data Science", "skills_covered": {"sql": "intermediate", "databases": "intermediate"}},
    "DS302": {"name": "Data Wrangling", "semester": 3, "department": "Data Science", "skills_covered": {"python": "intermediate", "excel": "advanced"}},
    "DS303": {"name": "Python for Data Science", "semester": 3, "department": "Data Science", "skills_covered": {"python": "advanced", "data_visualization": "beginner"}},
    "DS401": {"name": "Data Visualization", "semester": 4, "department": "Data Science", "skills_covered": {"data_visualization": "intermediate", "python": "advanced"}},
    "DS402": {"name": "Machine Learning Basics", "semester": 4, "department": "Data Science", "skills_covered": {"machine_learning": "beginner", "statistics": "advanced"}},
    "DS403": {"name": "Exploratory Data Analysis", "semester": 4, "department": "Data Science", "skills_covered": {"statistics": "advanced", "data_visualization": "advanced"}},
    "DS501": {"name": "Applied Machine Learning", "semester": 5, "department": "Data Science", "skills_covered": {"machine_learning": "intermediate", "python": "advanced"}},
    "DS502": {"name": "Big Data Analytics", "semester": 5, "department": "Data Science", "skills_covered": {"sql": "advanced", "cloud_computing": "beginner"}},
    "DS503": {"name": "Data Mining", "semester": 5, "department": "Data Science", "skills_covered": {"machine_learning": "intermediate", "databases": "advanced"}},
    "DS504": {"name": "SQL for Analytics", "semester": 5, "department": "Data Science", "skills_covered": {"sql": "advanced", "business_analysis": "beginner"}},
    "DS601": {"name": "Deep Learning", "semester": 6, "department": "Data Science", "skills_covered": {"deep_learning": "intermediate", "machine_learning": "advanced"}},
    "DS602": {"name": "Natural Language Processing", "semester": 6, "department": "Data Science", "skills_covered": {"machine_learning": "advanced", "python": "advanced"}},
    "DS603": {"name": "Cloud Data Platforms", "semester": 6, "department": "Data Science", "skills_covered": {"cloud_computing": "intermediate", "databases": "advanced"}},
    "DS701": {"name": "Advanced Machine Learning", "semester": 7, "department": "Data Science", "skills_covered": {"machine_learning": "advanced", "algorithms": "advanced"}},
    "DS702": {"name": "MLOps Basics", "semester": 7, "department": "Data Science", "skills_covered": {"mlops": "beginner", "cloud_computing": "intermediate"}},
    "DS703": {"name": "Business Analytics", "semester": 7, "department": "Data Science", "skills_covered": {"business_analysis": "intermediate", "data_visualization": "advanced"}}
}

# Add only if not already present
for code, details in new_courses.items():
    if code not in courses:
        courses[code] = details

with open(catalog_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Added {len(new_courses)} courses.")
