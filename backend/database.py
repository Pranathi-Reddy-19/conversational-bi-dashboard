import sqlite3
import pandas as pd
import json

DB_FILE = "easy_bi.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            username TEXT,
            role TEXT,
            content TEXT,
            follow_ups TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

def save_message(session_id: str, username: str, role: str, content: str, follow_ups: list = None):
    conn = get_db_connection()
    follow_ups_json = json.dumps(follow_ups) if follow_ups else None
    conn.execute(
        "INSERT INTO chat_history (session_id, username, role, content, follow_ups) VALUES (?, ?, ?, ?, ?)",
        (session_id, username, role, content, follow_ups_json)
    )
    conn.commit()
    conn.close()

def get_history(session_id: str, username: str):
    conn = get_db_connection()
    df = pd.read_sql(
        "SELECT role, content, follow_ups FROM chat_history WHERE session_id = ? AND username = ? ORDER BY id ASC", 
        conn, params=(session_id, username)
    )
    conn.close()
    
    messages = []
    for _, row in df.iterrows():
        msg = {"role": row["role"], "content": row["content"]}
        if row["follow_ups"]:
            try:
                msg["follow_ups"] = json.loads(row["follow_ups"])
            except:
                pass
        messages.append(msg)
    return messages
