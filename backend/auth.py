import hashlib
import hmac
import os
import secrets

from database import get_connection


def hash_password(password):
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return salt.hex() + ":" + password_hash.hex()


def verify_password(password, stored_hash):
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
    except ValueError:
        return False

    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return hmac.compare_digest(password_hash, expected_hash)


def create_session(player_id):
    token = secrets.token_urlsafe(32)

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO sessions (token, player_id) VALUES (?, ?)",
            (token, player_id)
        )
        connection.commit()

    return token


def get_player_by_token(token):
    if not token:
        return None

    with get_connection() as connection:
        row = connection.execute("""
            SELECT players.id, players.username, players.display_name
            FROM sessions
            JOIN players ON players.id = sessions.player_id
            WHERE sessions.token = ?
        """, (token,)).fetchone()

    if not row:
        return None

    return dict(row)


def remove_session(token):
    if not token:
        return

    with get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
        connection.commit()
