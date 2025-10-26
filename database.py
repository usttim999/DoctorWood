import sqlite3
from contextlib import contextmanager
from datetime import datetime

DATABASE_URL = None
USE_POSTGRES = False

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT,
            photo_file_id TEXT,
            watering_every_days INTEGER,
            last_watered_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS care_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            note TEXT,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
        )
        """)

        conn.commit()

@contextmanager
def get_conn():
    conn = sqlite3.connect("plants.db")
    try:
        yield conn
    finally:
        conn.close()

def upsert_user(chat_id: int, username: str, first_name: str, last_name: str):
    with get_conn() as conn:
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()

        cur.execute("SELECT id FROM users WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE users SET username=?, first_name=?, last_name=? WHERE chat_id=?
            """, (username, first_name, last_name, chat_id))
            user_id = row[0]
        else:
            cur.execute("""
                INSERT INTO users (chat_id, username, first_name, last_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, username, first_name, last_name, now))
            user_id = cur.lastrowid

        conn.commit()
        return user_id

def add_plant(user_id: int, name: str, type_: str = None, photo_file_id: str = None, watering_every_days: int = None):
    with get_conn() as conn:
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute("""
            INSERT INTO plants (user_id, name, type, photo_file_id, watering_every_days, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name, type_, photo_file_id, watering_every_days, now))
        conn.commit()
        return cur.lastrowid

def list_plants(user_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, type, photo_file_id, watering_every_days, last_watered_at, created_at
            FROM plants
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        return cur.fetchall()

def get_plant(plant_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, name, type, photo_file_id, watering_every_days, last_watered_at, created_at
            FROM plants
            WHERE id = ?
        """, (plant_id,))
        return cur.fetchone()

def delete_plant(plant_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM care_history WHERE plant_id = ?", (plant_id,))
        cur.execute("DELETE FROM plants WHERE id = ?", (plant_id,))
        conn.commit()

def set_watering_schedule(plant_id: int, watering_interval_days: int):
    """Установить график полива для растения"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE plants 
            SET watering_every_days = ?, last_watered_at = ?
            WHERE id = ?
        """, (watering_interval_days, datetime.utcnow().isoformat(), plant_id))
        conn.commit()

def get_plants_needing_watering():
    """Получить список растений, которые нужно полить"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.name, p.watering_every_days, p.last_watered_at, u.chat_id
            FROM plants p
            JOIN users u ON p.user_id = u.id
            WHERE p.watering_every_days IS NOT NULL
            AND p.last_watered_at IS NOT NULL
            AND julianday('now') - julianday(p.last_watered_at) > p.watering_every_days
        """)
        return cur.fetchall()

def mark_watered(plant_id: int):
    """Отметить растение как политое"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE plants 
            SET last_watered_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), plant_id))
        conn.commit()