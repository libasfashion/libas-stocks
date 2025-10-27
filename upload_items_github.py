# upload_items_github.py
import base64, os, json, requests, datetime, sys

ROOT = os.path.dirname(__file__)
JSON_PATH = os.path.join(ROOT, "items.json")

# Replace these with your GitHub account & repo exactly
OWNER = "unique205"     # <-- change to your GitHub username if different
REPO = "libas-site"     # <-- change to your repo name if different
PATH_IN_REPO = "items.json"
BRANCH = "main"

TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    print("❌ GITHUB_TOKEN env var not set. Please set it (setx) and restart PowerShell.")
    sys.exit(1)

def upload():
    if not os.path.exists(JSON_PATH):
        print("❌ items.json not found at", JSON_PATH)
        return False

    with open(JSON_PATH, "rb") as f:
        content = f.read()
    b64 = base64.b64encode(content).decode("utf-8")

    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{PATH_IN_REPO}"

    # Try to get existing file to obtain sha (for update)
    r = requests.get(url + f"?ref={BRANCH}", headers={"Authorization": f"token {TOKEN}"})
    data = {
        "message": f"Auto update items.json {datetime.datetime.utcnow().isoformat()}Z",
        "content": b64,
        "branch": BRANCH
    }
    if r.status_code == 200:
        sha = r.json().get("sha")
        if sha:
            data["sha"] = sha

    resp = requests.put(url, headers={"Authorization": f"token {TOKEN}"}, json=data)
    if resp.status_code in (200,201):
        print("✅ items.json uploaded to GitHub")
        return True
    else:
        print("❌ GitHub API error", resp.status_code)
        print(resp.text)
        return False

if __name__ == "__main__":
    upload()
