# export_to_json.py
import sqlite3, json, os, sys
from upload_items_github import upload  # uses env token

ROOT = os.path.dirname(__file__)
db_path = os.path.join(ROOT, "cache.db")
json_path = os.path.join(ROOT, "items.json")

def export_items():
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM items;")
        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)

        print(f"✅ Exported {len(rows)} items to {json_path}")
        return True
    except Exception as e:
        print("❌ Error exporting:", e)
        return False

if __name__ == "__main__":
    ok = export_items()
    if not ok:
        sys.exit(1)
    # now upload to GitHub
    uploaded = upload()
    if not uploaded:
        print("⚠️ Upload failed. items.json still created locally.")
