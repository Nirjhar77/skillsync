# SkillSync

SkillSync is an AI-assisted career navigation web application designed to bridge the gap between undergraduate curricula and entry-level tech industry requirements. It allows users to input their major, semester, skills, and interests, and uses an LLM (Large Language Model) via the Groq API to generate highly personalized learning roadmaps alongside rule-based career matching.

## Prerequisites

To run this application locally, you will need:
- **Python 3.8+** installed on your computer.
- A **Groq API Key** (this handles the AI roadmap generation).

## How to Run the App (Locally)

1. **Open a Terminal / Command Prompt** in the root directory of this project (where this `README.md` file is located).

2. **Create a Virtual Environment** (Recommended):
   ```bash
   python -m venv venv
   ```
   *Activate it (Windows):*
   ```bash
   venv\Scripts\activate
   ```
   *Activate it (Mac/Linux):*
   ```bash
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Your Environment Variables**:
   Create a file named `.env` in the root directory and add your API key like this:
   ```env
   GROQ_API_KEY=gsk_YourGroqApiKeyHere
   SECRET_KEY=a_random_secure_string_for_sessions
   ```

5. **Run the Server**:
   ```bash
   python app.py
   ```

6. **Open the App in Your Browser**:
   Once the server is running, the terminal will show a message saying it's running on `http://127.0.0.1:5000`. 
   Copy that exact link and paste it into your web browser (Chrome, Edge, Safari, etc.).

## Troubleshooting

- **"The site can't be reached" / Link doesn't work**: The `http://127.0.0.1:5000` link ONLY works when your terminal is open and the `python app.py` command is actively running. If you close the terminal or stop the command, the website goes down.
- **AI Roadmap isn't generating**: Ensure your `.env` file exists and has a valid `GROQ_API_KEY`.


//## Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\activate
python app.py
