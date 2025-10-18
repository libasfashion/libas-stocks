from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import pandas as pd
import os

app = Flask(__name__)

# -----------------------------------------------------------------------------
# Control whether sync (pyodbc) is allowed. Default: disabled (safe for cloud).
# Set environment variable ALLOW_SYNC=1 only on your local machine where ODBC driver is installed.
# -----------------------------------------------------------------------------
ALLOW_SYNC = os.environ.get("ALLOW_SYNC", "0") == "1"

# Try to import sync module only when allowed.
sync = None
if ALLOW_SYNC:
    try:
        # This import is safe because sync.py does not import pyodbc at top-level.
        import sync as sync_module
        sync = sync_module
    except Exception as e:
        # Keep server alive even if sync import fails locally
        print("Warning: failed to import sync module (local only).", e)
        sync = None


# -------------------- Pages / routes ----------------------------------------
@app.route("/")
def home():
    # Renders templates/libas.html
    return render_template("libas.html")


@app.route("/api/search")
def api_search():
    """
    Returns JSON: {"items": [ ... rows ... ]}
    Supports optional query param q for client-side filtering.
    """
    q = request.args.get("q", "").strip()

    # Read the cached SQLite file 'cache.db' which must contain table 'items'
    db_path = os.path.join(app.root_path, "cache.db")
    if not os.path.exists(db_path):
        return jsonify({"items": []})

    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql("SELECT * FROM items", conn)
    except Exception as e:
        conn.close()
        return jsonify({"error": "failed to read cache.db", "detail": str(e)}), 500
    conn.close()

    if q:
        q_lower = q.lower()
        # filter by ItemName or ItemAlias (case-insensitive)
        mask = df["ItemName"].fillna("").str.lower().str.contains(q_lower) | df["ItemAlias"].fillna("").str.lower().str.contains(q_lower)
        df = df[mask]

    items = df.to_dict(orient="records")
    return jsonify({"items": items})


@app.route("/service-worker.js")
def service_worker():
    """
    Serve the service worker JS from project root so it controls full scope.
    Make sure service-worker.js exists at project root (same folder as app.py).
    """
    return send_from_directory(app.root_path, "service-worker.js", mimetype="application/javascript")


@app.route("/sync", methods=["GET", "POST"])
def run_sync_route():
    """
    Run sync only when ALLOW_SYNC is True (local machine).
    On cloud this will return 403 to avoid importing pyodbc.
    """
    if not ALLOW_SYNC or sync is None:
        return jsonify({"error": "sync disabled on this server (ALLOW_SYNC not set)"}), 403

    try:
        result = sync.run_sync()
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"error": "sync failed", "detail": str(e)}), 500


# -------------------- static files: Flask will serve /static/ by default ----------
# No extra route needed for static files; put manifest, icons, CSS, JS in /static


# -------------------- start server ------------------------------------------
if __name__ == "__main__":
    # Use PORT env var on cloud (Render sets it). Default to 5000 locally.
    port = int(os.environ.get("PORT", 5000))
    # debug False for production
    app.run(debug=False, host="0.0.0.0", port=port)
