"""
sync.py
Safe local sync logic for Busy -> cache.db

Usage:
  - From Flask when ALLOW_SYNC=1: app will import this file and call run_sync()
  - From command line locally: python sync.py
Notes:
  - This code imports pyodbc **inside** run_sync() so cloud deploys that import this file won't attempt to load ODBC.
  - Configure connection via environment variables:
      SQLSERVER, SQLDATABASE, SQLUSER, SQLPASSWORD, SQLDRIVER
"""

import os
import sqlite3
import pandas as pd

# The exact SQL you insisted on (unchanged)
BUSY_SQL = """
SELECT
  I.Name                                   AS ItemName,
  I.Alias                                  AS ItemAlias,
  G.Name                                   AS GroupName,
  ISNULL(I.D2, 0)                          AS Item_MRP,
  ISNULL(I.D3, 0)                          AS Item_Sale_Price,
  COALESCE(NULLIF(I.D9, 0), OV.OpenValPerUnit, 0) AS Item_SelfVal_Price,
  ISNULL(SQ.Stock, 0)                      AS Stock
FROM Master1 I
LEFT JOIN Master1 G
  ON I.ParentGrp = G.Code AND G.MasterType = 5
LEFT JOIN (
  SELECT T4.MasterCode1 AS ItemCode,
         SUM(T4.D1) AS OpenQty,
         SUM(T4.D2) AS OpenValue,
         CASE WHEN SUM(T4.D1) <> 0 THEN SUM(T4.D2) / SUM(T4.D1) ELSE 0 END AS OpenValPerUnit
  FROM Tran4 T4
  GROUP BY T4.MasterCode1
) OV
  ON OV.ItemCode = I.Code
LEFT JOIN (
  SELECT T2.MasterCode1 AS ItemCode,
         SUM(CASE WHEN T2.TranType IN (0,1) THEN T2.Value1 ELSE -T2.Value1 END) AS Stock
  FROM Tran2 T2
  GROUP BY T2.MasterCode1
) SQ
  ON SQ.ItemCode = I.Code
WHERE I.MasterType = 6
ORDER BY I.Name
"""

def run_sync():
    """
    Connects to Busy SQL Server via pyodbc, runs BUSY_SQL, writes results to cache.db (table 'items').
    Returns a dict with summary: {"rows": N, "saved_to": "cache.db"}
    Raises RuntimeError on failures (pyodbc missing or connection error).
    """
    # read connection configuration from environment (safe defaults)
    server = os.environ.get("SQLSERVER", "").strip()
    database = os.environ.get("SQLDATABASE", "").strip()
    user = os.environ.get("SQLUSER", "").strip()
    password = os.environ.get("SQLPASSWORD", "").strip()
    driver = os.environ.get("SQLDRIVER", "ODBC Driver 17 for SQL Server").strip()

    if not server or not database:
        raise RuntimeError("SQLSERVER and SQLDATABASE environment variables must be set for sync.")

    # import pyodbc only when running sync (so cloud imports don't fail)
    try:
        import pyodbc
    except Exception as e:
        raise RuntimeError("pyodbc import failed: " + str(e))

    # build connection string
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};DATABASE={database};"
    )
    if user:
        conn_str += f"UID={user};PWD={password};"
    else:
        # try trusted connection (Windows auth) if user not provided
        conn_str += "Trusted_Connection=yes;"

    # trust server certificate to avoid encryption issues on some setups
    conn_str += "TrustServerCertificate=yes;"

    # connect and fetch
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
    except Exception as e:
        raise RuntimeError("pyodbc connection failed: " + str(e))

    try:
        # Use pandas.read_sql to execute the query
        df = pd.read_sql(BUSY_SQL, conn)
    except Exception as e:
        conn.close()
        raise RuntimeError("Failed to execute query: " + str(e))
    finally:
        try:
            conn.close()
        except:
            pass

    # Save to SQLite cache.db in the same folder as this file (project root)
    root = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(root, "cache.db")

    try:
        # Use SQLAlchemy engine to ensure pandas to_sql works reliably
        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{cache_path}", future=True)
        # Save (replace) the items table
        with engine.begin() as cx:
            df.to_sql("items", cx, if_exists="replace", index=False)
    except Exception as e:
        raise RuntimeError("Failed to write cache.db: " + str(e))

    return {"rows": int(len(df)), "saved_to": cache_path}


# Allow running this script directly on your local machine:
if __name__ == "__main__":
    try:
        result = run_sync()
        print("Sync completed:", result)
    except Exception as e:
        print("Sync failed:", str(e))
        raise
