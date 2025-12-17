import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sessions.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    state TEXT
)
""")
conn.commit()
conn.close()

print("✅ sessions table created at", DB_PATH)
