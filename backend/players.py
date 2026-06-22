from database import get_connection
from auth import create_session, get_player_by_token, hash_password, remove_session, verify_password
from wallet import ensure_wallet, get_balance, get_transactions


def clean_username(username):
    return "".join(char for char in username.strip().lower() if char.isalnum() or char in "._-")[:24]


def clean_display_name(display_name):
    clean_name = " ".join(display_name.strip().split())[:18]
    return clean_name or "NeonPlayer"


def clean_email(email):
    return (email or "").strip().lower()[:120]


def public_player(player):
    return {
        "id": player["id"],
        "usuario": player["username"],
        "apelido": player["display_name"]
    }

def register_player(username, display_name, password, email=""):
    username = clean_username(username)
    display_name = clean_display_name(display_name)
    email = clean_email(email)

    if len(username) < 3:
        return None, "Nome de usuário precisa ter pelo menos 3 caracteres"

    if len(display_name) < 3:
        return None, "Apelido precisa ter pelo menos 3 caracteres"

    if email and ("@" not in email or "." not in email):
        return None, "E-mail inválido"

    if len(password) < 4:
        return None, "Senha precisa ter pelo menos 4 caracteres"

    with get_connection() as connection:
        existing_username = connection.execute(
            "SELECT id FROM players WHERE lower(username) = lower(?)",
            (username,)
        ).fetchone()

        if existing_username:
            return None, "Nome de usuário já existe"

        existing_display_name = connection.execute(
            "SELECT id FROM players WHERE lower(display_name) = lower(?)",
            (display_name,)
        ).fetchone()

        if existing_display_name:
            return None, "Apelido já existe"

        try:
            cursor = connection.execute(
                "INSERT INTO players (username, email, display_name, password_hash) VALUES (?, ?, ?, ?)",
                (username, email, display_name, hash_password(password))
            )
            connection.commit()
            player_id = cursor.lastrowid
        except Exception:
            return None, "Não foi possível criar a conta"

    token = create_session(player_id)
    ensure_wallet(player_id)

    return {
        "token": token,
        "player": {
            "id": player_id,
            "username": username,
            "display_name": display_name
        }
    }, None

def login_player(username, password):
    username = clean_username(username)

    with get_connection() as connection:
        player = connection.execute(
            """
            SELECT id, username, email, display_name, password_hash
            FROM players
            WHERE username = ? OR email = ?
            """,
            (username, username)
        ).fetchone()

    if not player or not verify_password(password, player["password_hash"]):
        return None, "Usuário ou senha inválidos"

    token = create_session(player["id"])

    return {
        "token": token,
        "player": dict(player)
    }, None


def get_profile(token):
    player = get_player_by_token(token)

    if not player:
        return None

    stats = get_player_stats(player["id"], player["display_name"])
    saldo = get_balance(player["id"])
    transacoes = get_transactions(player["id"])

    return {
        "player": player,
        "stats": stats,
        "wallet": {
            "saldo": saldo,
            "transacoes": transacoes
        }
    }


def logout_player(token):
    remove_session(token)


def save_match(player, data):
    player_name = data.get("player_name") or player["display_name"]
    opponent_name = data.get("opponent_name") or "Adversário"
    winner_name = data.get("winner_name") or player_name
    score_player = int(data.get("score_player") or 0)
    score_opponent = int(data.get("score_opponent") or 0)
    mode = str(data.get("mode") or "local")[:24]
    room_code = str(data.get("room_code") or "LOCAL")[:24]
    match_uid = str(data.get("match_uid") or "")[:120]

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO matches (
                player_id,
                player_name,
                opponent_name,
                winner_name,
                score_player,
                score_opponent,
                mode,
                room_code,
                match_uid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id, match_uid) DO NOTHING
        """, (
            player["id"],
            player_name,
            opponent_name,
            winner_name,
            score_player,
            score_opponent,
            mode,
            room_code,
            match_uid
        ))
        connection.commit()


def get_player_stats(player_id, display_name):
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT winner_name FROM matches WHERE player_id = ?",
            (player_id,)
        ).fetchall()

    total = len(rows)
    wins = sum(1 for row in rows if row["winner_name"] == display_name)
    losses = max(total - wins, 0)
    win_rate = round((wins / total) * 100) if total else 0

    return {
        "partidas": total,
        "vitorias": wins,
        "derrotas": losses,
        "aproveitamento": win_rate
    }


def get_recent_matches(player_id):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT player_name, opponent_name, winner_name, score_player, score_opponent, mode, room_code, played_at
            FROM matches
            WHERE player_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (player_id,)).fetchall()

    return [dict(row) for row in rows]


def get_global_ranking():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                players.display_name AS nome,
                COUNT(matches.id) AS partidas,
                SUM(CASE WHEN matches.winner_name = players.display_name THEN 1 ELSE 0 END) AS vitorias
            FROM players
            LEFT JOIN matches ON matches.player_id = players.id
            GROUP BY players.id
            ORDER BY vitorias DESC, partidas DESC, players.display_name ASC
            LIMIT 10
        """).fetchall()

    ranking = []

    for row in rows:
        partidas = row["partidas"] or 0
        vitorias = row["vitorias"] or 0
        derrotas = max(partidas - vitorias, 0)
        aproveitamento = round((vitorias / partidas) * 100) if partidas else 0

        ranking.append({
            "nome": row["nome"],
            "partidas": partidas,
            "vitorias": vitorias,
            "derrotas": derrotas,
            "aproveitamento": aproveitamento
        })

    return ranking

