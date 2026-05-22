import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from routes.news import fetch_github_trending, fetch_show_hn

app = Flask(__name__)
class MockLogger:
    def warning(self, msg):
        print("WARNING:", msg)
app.logger = MockLogger()

# Establish app context
with app.app_context():
    print("--- TESTING GITHUB TRENDING FETCH ---")
    repos = fetch_github_trending(limit=3)
    if repos:
        for r in repos:
            print(f"- {r['name']} by {r['owner']} ({r['stars']} stars) [{r['language']}]: {r['description']}")
    else:
        print("No GitHub repos fetched or rate-limited.")

    print("\n--- TESTING SHOW HN FETCH ---")
    builds = fetch_show_hn(limit=3)
    if builds:
        for b in builds:
            print(f"- {b['title']} ({b['score']} pts, {b['comments']} comments): {b['url']}")
    else:
        print("No Show HN builds fetched.")
