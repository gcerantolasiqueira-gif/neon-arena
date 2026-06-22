import sqlite3
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("NEON_DB_PATH", BASE_DIR / "neon_arena.db")).expanduser()


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def init_database():
    with get_connection() as connection:
        connection.execute("PRAGMA journal_mode = WAL")

        connection.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            connection.execute("ALTER TABLE players ADD COLUMN email TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_players_username_lower
                ON players(lower(username))
            """)
        except sqlite3.IntegrityError:
            pass

        try:
            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_players_display_name_lower
                ON players(lower(display_name))
            """)
        except sqlite3.IntegrityError:
            pass

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_players_email
            ON players(email)
            WHERE email IS NOT NULL AND email != ''
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                player_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(player_id) REFERENCES players(id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                opponent_name TEXT NOT NULL,
                winner_name TEXT NOT NULL,
                score_player INTEGER NOT NULL,
                score_opponent INTEGER NOT NULL,
                mode TEXT NOT NULL,
                room_code TEXT NOT NULL,
                match_uid TEXT,
                played_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(player_id) REFERENCES players(id)
            )
        """)

        try:
            connection.execute("ALTER TABLE matches ADD COLUMN match_uid TEXT")
        except sqlite3.OperationalError:
            pass

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_player_match_uid
            ON matches(player_id, match_uid)
            WHERE match_uid IS NOT NULL AND match_uid != ''
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                player_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 1000,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(player_id) REFERENCES players(id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                balance_before INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                type TEXT NOT NULL,
                room_code TEXT,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(player_id) REFERENCES players(id)
            )
        """)

        connection.commit()
