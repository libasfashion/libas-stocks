from flask import Flask, jsonify
import sqlite3
import pandas as pd

app = Flask(__name__)

@app.route('/api/search')
def api_search():
    conn = sqlite3.connect('cache.db')
    df = pd.read_sql('SELECT * FROM items', conn)
    conn.close()
    return jsonify({'items': df.to_dict(orient='records')})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
