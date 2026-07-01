import sqlite3
import os
import datetime
from typing import List, Dict, Any, Optional
from app.config import settings

def get_db_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Conversations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

def create_conversation(conversation_id: str, title: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
        (conversation_id, title, now)
    )
    conn.commit()
    conn.close()
    return {"id": conversation_id, "title": title, "created_at": now}

def get_conversations() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at FROM conversations ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "title": row["title"], "created_at": row["created_at"]} for row in rows]

def rename_conversation(conversation_id: str, new_title: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, conversation_id))
    conn.commit()
    conn.close()

def delete_conversation(conversation_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    conn.commit()
    conn.close()

def add_message(conversation_id: str, role: str, content: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, now)
    )
    conn.commit()
    conn.close()
    return {"conversation_id": conversation_id, "role": role, "content": content, "created_at": now}

def get_messages(conversation_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"], "created_at": row["created_at"]} for row in rows]
