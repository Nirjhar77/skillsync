import urllib.request
import json

def test_github():
    url = "https://api.github.com/search/repositories?q=stars:>1000+pushed:>2026-05-01&sort=stars&order=desc"
    req = urllib.request.Request(url, headers={"User-Agent": "SkillSync/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print("GitHub top repositories:")
            for item in data.get("items", [])[:5]:
                print(f"- {item['name']} by {item['owner']['login']} ({item['stargazers_count']} stars): {item['description']}")
    except Exception as e:
        print("GitHub test failed:", e)

def test_show_hn():
    # Show HN items: we can query Hacker News
    # First get show HN stories list
    url = "https://hacker-news.firebaseio.com/v0/showstories.json"
    req = urllib.request.Request(url, headers={"User-Agent": "SkillSync/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            ids = json.loads(resp.read().decode())
            print("\nShow HN items:")
            count = 0
            for story_id in ids[:10]:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                item_req = urllib.request.Request(item_url, headers={"User-Agent": "SkillSync/1.0"})
                with urllib.request.urlopen(item_req, timeout=5) as item_resp:
                    story = json.loads(item_resp.read().decode())
                    if story and story.get("url"):
                        print(f"- {story.get('title')} ({story.get('score')} pts): {story.get('url')}")
                        count += 1
                        if count >= 5:
                            break
    except Exception as e:
        print("Show HN test failed:", e)

if __name__ == "__main__":
    test_github()
    test_show_hn()
