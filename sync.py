import os, sys
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

try:
    import pyodbc
except Exception as e:
    print("ERROR: pyodbc import failed:", e)
    sys.exit(1)

load_dotenv()

SQLSERVER   = os.getenv("SQLSERVER", "").strip()
SQLDATABASE = os.getenv("SQLDATABASE", "").strip()
SQLUSER     = os.getenv("SQLUSER", "").strip()
SQLPASSWORD = os.getenv("SQLPASSWORD", "").strip()
SQLDRIVER   = os.getenv("SQLDRIVER", "").strip() or "ODBC Driver 17 for SQL Server"

if not SQLSERVER or not SQLDATABASE:
    print("Please set SQLSERVER and SQLDATABASE in .env")
    sys.exit(1)

def connect():
    if SQLUSER and SQLPASSWORD:
        conn_str = (
            f"DRIVER={{{SQLDRIVER}}};"
            f"SERVER={SQLSERVER};"
            f"DATABASE={SQLDATABASE};"
            f"UID={SQLUSER};PWD={SQLPASSWORD};"
            "Encrypt=yes;TrustServerCertificate=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{{SQLDRIVER}}};"
            f"SERVER={SQLSERVER};"
            f"DATABASE={SQLDATABASE};"
            "Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
        )
    return pyodbc.connect(conn_str, timeout=10)

print(f"Connecting to {SQLSERVER} / DB={SQLDATABASE} …")
conn = connect()
print("Connected.")

# --- run your exact SQL file ---
with open("query.sql", "r", encoding="utf-8") as f:
    sql = f.read()

print("Running query …")
df = pd.read_sql(sql, conn)
conn.close()
print(f"Fetched {len(df):,} rows.")

df.columns = [c.strip() for c in df.columns]

sqlite_path = "cache.db"
engine = create_engine(f"sqlite:///{sqlite_path}", future=True)
with engine.begin() as cxn:
    df.to_sql("items", cxn, if_exists="replace", index=False)

print(f"Saved to {sqlite_path} (table 'items').")
print(df.head(5).to_string(index=False))
