import os
import sqlite3
import psycopg2
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import urlparse


DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS plants (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    else:
        conn = sqlite3.connect("plants.db")
    try:
        yield conn
    finally:
        conn.close()


def upsert_user(chat_id: int, username: str, first_name: str, last_name: str):
    with get_conn() as conn:
        cur = conn.cursor()
        now = datetime.utcnow()

        if USE_POSTGRES:
            cur.execute("SELECT id FROM users WHERE chat_id = %s", (chat_id,))
        else:
            cur.execute("SELECT id FROM users WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()

        if row:
            if USE_POSTGRES:
                cur.execute("""
                    UPDATE users SET username=%s, first_name=%s, last_name=%s WHERE chat_id=%s
                """, (username, first_name, last_name, chat_id))
            else:
                cur.execute("""
                    UPDATE users SET username=?, first_name=?, last_name=? WHERE chat_id=?
                """, (username, first_name, last_name, chat_id))
            user_id = row[0]
        else:
            if USE_POSTGRES:
                cur.execute("""
                    INSERT INTO users (chat_id, username, first_name, last_name, created_at)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id
                """, (chat_id, username, first_name, last_name, now))
                user_id = cur.fetchone()[0]
            else:
                cur.execute("""
                    INSERT INTO users (chat_id, username, first_name, last_name, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (chat_id, username, first_name, last_name, now.isoformat()))
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
        # сначала удалим историю ухода
        cur.execute("DELETE FROM care_history WHERE plant_id = ?", (plant_id,))
        # затем само растение
        cur.execute("DELETE FROM plants WHERE id = ?", (plant_id,))
        conn.commit()
