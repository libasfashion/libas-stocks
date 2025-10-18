from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import pandas as pd
import os
import sys
import subprocess

app = Flask(__name__)

# ---------- pages ----------
@app.route("/")
def home():
    # renders templates/libas.html
    return render_template("libas.html")

# ---------- api ----------
@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    g = request.args.get("group", "").strip()

    conn = sqlite3.connect("cache.db")
    df = pd.read_sql("SELECT * FROM items", conn)
    conn.close()

    if q:
        q_lower = q.lower()
        df = df[
            df["ItemName"].str.lower().str.contains(q_lower, na=False) |
            df["ItemAlias"].str.lower().str.contains(q_lower, na=False)
        ]
    if g:
        df = df[df["GroupName"] == g]

    return jsonify({"items": df.to_dict(orient="records")})

# ---------- on-demand sync ----------
@app.route("/sync", methods=["POST"])
def sync_now():
    """
    Runs sync.py (in this same folder) to refresh cache.db from Busy.
    Returns JSON { ok: bool, msg: tail-of-logs }.
    """
    try:
        project_root = app.root_path
        sync_path = os.path.join(project_root, "sync.py")
        if not os.path.exists(sync_path):
            return jsonify({"ok": False, "msg": "sync.py not found"}), 404

        completed = subprocess.run(
            [sys.executable, sync_path],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        ok = (completed.returncode == 0)
        tail = (completed.stdout or "")[-800:] + ("\n" + (completed.stderr or "")[-800:] if completed.stderr else "")
        return jsonify({"ok": ok, "msg": tail})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

# ---------- service worker at root ----------
@app.route("/service-worker.js")
def service_worker():
    # serve SW from project root (same folder as app.py) with root scope
    return send_from_directory(app.root_path, "service-worker.js", mimetype="application/javascript")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
