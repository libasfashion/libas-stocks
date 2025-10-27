from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Load environment (.env) and optional Cloudinary credentials
# -----------------------------------------------------------------------------
load_dotenv()

import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

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


def db_path() -> str:
    """Absolute path to cache.db next to app.py"""
    return os.path.join(app.root_path, "cache.db")


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
    Now includes ImageURL column if present.
    """
    q = request.args.get("q", "").strip()

    path = db_path()
    if not os.path.exists(path):
        return jsonify({"items": []})

    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql("SELECT * FROM items", conn)
    except Exception as e:
        conn.close()
        return jsonify({"error": "failed to read cache.db", "detail": str(e)}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if q:
        q_lower = q.lower()
        name = df.get("ItemName")
        alias = df.get("ItemAlias")
        mask = False
        if name is not None:
            mask = name.fillna("").str.lower().str.contains(q_lower)
        if alias is not None:
            mask = mask | alias.fillna("").str.lower().str.contains(q_lower)
        df = df[mask] if isinstance(mask, pd.Series) else df

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


# -------------------- NEW: Image upload + save URL to SQLite ----------------
@app.route("/api/upload_image", methods=["POST"])
def upload_image():
    """
    Uploads an image file to Cloudinary and stores its secure URL
    into items.ImageURL for the given ItemCode.

    Expects form fields:
      - code: ItemCode (string)
      - file: image file (multipart/form-data)
    """
    code = request.form.get("code", "").strip()
    file = request.files.get("file")

    if not code or not file:
        return jsonify({"ok": False, "error": "code and file are required"}), 400

    # Upload to Cloudinary (folder 'libas', one image per code -> overwrite=True)
    try:
        result = cloudinary.uploader.upload(
            file,
            folder="libas",
            public_id=code,
            overwrite=True,
            resource_type="image",
        )
        url = result.get("secure_url")
        if not url:
            raise RuntimeError("Cloudinary did not return secure_url")
    except Exception as e:
        return jsonify({"ok": False, "error": f"upload failed: {e}"}), 500

    # Save URL into SQLite
    path = db_path()
    con = sqlite3.connect(path)
    cur = con.cursor()
    try:
        cur.execute("UPDATE items SET ImageURL=? WHERE ItemCode=?", (url, code))
        if cur.rowcount == 0:
            # If item missing, try insert minimal row
            cur.execute(
                "INSERT INTO items (ItemCode, ImageURL) VALUES (?, ?)",
                (code, url),
            )
        con.commit()
    except Exception as e:
        con.rollback()
        return jsonify({"ok": False, "error": f"db write failed: {e}"}), 500
    finally:
        con.close()

    return jsonify({"ok": True, "code": code, "url": url})


# -------------------- start server ------------------------------------------
if __name__ == "__main__":
    # Use PORT env var on cloud (Render etc). Default to 5000 locally.
    port = int(os.environ.get("PORT", 5000))
    # debug False for production
    app.run(debug=False, host="0.0.0.0", port=port)
