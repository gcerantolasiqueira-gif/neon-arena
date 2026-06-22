from fastapi import FastAPI, Header, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
import os
import time

from auth import get_player_by_token
from database import init_database
from players import (
    get_global_ranking,
    get_profile,
    get_recent_matches,
    login_player,
    logout_player,
    register_player,
    save_match
)
from rooms import rooms_store
from wallet import add_bonus, get_balance, get_transactions
from websocket_manager import websocket_manager
from matchmaking import matchmaking_queue
from rate_limiter import rate_limiter

app = FastAPI(title="Neon Arena", version="1.0.0-beta")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
ONLINE_TIMEOUT_SECONDS = 20
online_presence = {}
chat_messages = []
CHAT_LIMIT = 80
ALLOWED_STAKES = {0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000}

allowed_hosts = [
    host.strip()
    for host in os.getenv("NEON_ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]

if allowed_hosts and allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


class RegisterRequest(BaseModel):
    usuario: str
    email: str = ""
    apelido: str
    senha: str


class LoginRequest(BaseModel):
    usuario: str
    senha: str


class MatchRequest(BaseModel):
    player_name: str
    opponent_name: str
    winner_name: str
    score_player: int
    score_opponent: int
    mode: str
    room_code: str
    match_uid: str = ""


class PresenceRequest(BaseModel):
    visitor_id: str
    nome: str = ""


class ChatRequest(BaseModel):
    mensagem: str


def client_key(request: Request):
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def check_limit(request: Request, action: str, limit: int, window_seconds: int):
    ok, retry_after = rate_limiter.allow(
        f"{action}:{client_key(request)}",
        limit,
        window_seconds
    )

    if ok:
        return None

    return {
        "sucesso": False,
        "mensagem": f"Muitas tentativas. Tente novamente em {retry_after} segundos."
    }


def token_from_header(authorization):
    if not authorization:
        return ""

    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return authorization.strip()


def normalize_stake(aposta):
    try:
        stake = int(aposta or 0)
    except (TypeError, ValueError):
        return None

    if stake not in ALLOWED_STAKES:
        return None

    return stake


def active_online_players():
    now = time.time()

    expired = [
        visitor_id
        for visitor_id, data in online_presence.items()
        if now - data["last_seen"] > ONLINE_TIMEOUT_SECONDS
    ]

    for visitor_id in expired:
        online_presence.pop(visitor_id, None)

    return len(online_presence)


@app.post("/api/online/heartbeat")
def online_heartbeat(payload: PresenceRequest, authorization: str | None = Header(default=None)):
    visitor_id = payload.visitor_id.strip()[:80]

    if not visitor_id:
        return {
            "sucesso": False,
            "online": active_online_players()
        }

    token = token_from_header(authorization)
    player = get_player_by_token(token)
    nome = payload.nome.strip()[:18] or "Visitante"

    if player:
        nome = player["display_name"]

    online_presence[visitor_id] = {
        "nome": nome,
        "last_seen": time.time()
    }

    return {
        "sucesso": True,
        "online": active_online_players()
    }


@app.get("/api/online")
def online_count():
    return {
        "sucesso": True,
        "online": active_online_players()
    }


@app.get("/api/chat")
def listar_chat():
    return {
        "sucesso": True,
        "mensagens": chat_messages[-CHAT_LIMIT:]
    }


@app.post("/api/chat")
def enviar_chat(payload: ChatRequest, request: Request, authorization: str | None = Header(default=None)):
    limited = check_limit(request, "chat", 12, 60)
    if limited:
        return limited

    token = token_from_header(authorization)
    player = get_player_by_token(token)

    if not player:
        return {
            "sucesso": False,
            "mensagem": "Faça login para conversar no chat"
        }

    mensagem = " ".join(payload.mensagem.strip().split())[:240]
    if not mensagem:
        return {
            "sucesso": False,
            "mensagem": "Digite uma mensagem"
        }

    chat_messages.append({
        "id": int(time.time() * 1000),
        "nome": player["display_name"],
        "mensagem": mensagem,
        "horario": time.strftime("%H:%M")
    })

    del chat_messages[:-CHAT_LIMIT]

    return {
        "sucesso": True,
        "mensagens": chat_messages[-CHAT_LIMIT:]
    }


@app.post("/api/auth/cadastrar")
def cadastrar_player(payload: RegisterRequest, request: Request):
    limited = check_limit(request, "cadastro", 8, 300)
    if limited:
        return limited

    result, error = register_player(payload.usuario, payload.apelido, payload.senha, payload.email)

    if error:
        return {
            "sucesso": False,
            "mensagem": error
        }

    return {
        "sucesso": True,
        "token": result["token"],
        "player": {
            "id": result["player"]["id"],
            "usuario": result["player"]["username"],
            "apelido": result["player"]["display_name"]
        }
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request):
    limited = check_limit(request, "login", 15, 300)
    if limited:
        return limited

    result, error = login_player(payload.usuario, payload.senha)

    if error:
        return {
            "sucesso": False,
            "mensagem": error
        }

    return {
        "sucesso": True,
        "token": result["token"],
        "player": {
            "id": result["player"]["id"],
            "usuario": result["player"]["username"],
            "apelido": result["player"]["display_name"]
        }
    }


@app.get("/api/auth/me")
def perfil(authorization: str | None = Header(default=None)):
    token = token_from_header(authorization)
    profile = get_profile(token)

    if not profile:
        return {
            "sucesso": False,
            "mensagem": "Sessão inválida"
        }

    return {
        "sucesso": True,
        "player": {
            "id": profile["player"]["id"],
            "usuario": profile["player"]["username"],
            "apelido": profile["player"]["display_name"]
        },
        "stats": profile["stats"],
        "wallet": profile["wallet"],
        "partidas": get_recent_matches(profile["player"]["id"])
    }


@app.get("/api/health")
def health():
    return {
        "sucesso": True,
        "status": "online",
        "versao": "1.0.0-beta",
        "ambiente": os.getenv("NEON_ENV", "local"),
        "banco": "sqlite",
        "persistencia": "configuravel_por_NEON_DB_PATH",
        "salas": len(rooms_store.rooms)
    }


@app.get("/api/carteira")
def carteira(authorization: str | None = Header(default=None)):
    token = token_from_header(authorization)
    player = get_player_by_token(token)

    if not player:
        return {
            "sucesso": False,
            "mensagem": "Faça login para acessar a carteira"
        }

    return {
        "sucesso": True,
        "saldo": get_balance(player["id"]),
        "transacoes": get_transactions(player["id"])
    }


@app.post("/api/carteira/bonus")
def carteira_bonus(request: Request, authorization: str | None = Header(default=None)):
    limited = check_limit(request, "bonus", 10, 300)
    if limited:
        return limited

    token = token_from_header(authorization)
    player = get_player_by_token(token)

    if not player:
        return {
            "sucesso": False,
            "mensagem": "Faça login para receber Moedas Neon"
        }

    saldo = add_bonus(player["id"])

    return {
        "sucesso": True,
        "saldo": saldo,
        "mensagem": "Bônus adicionado"
    }


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    token = token_from_header(authorization)
    logout_player(token)

    return {
        "sucesso": True
    }


@app.post("/api/partidas")
def salvar_partida(payload: MatchRequest, authorization: str | None = Header(default=None)):
    token = token_from_header(authorization)
    player = get_player_by_token(token)

    if not player:
        return {
            "sucesso": False,
            "mensagem": "Faça login para salvar partidas no servidor"
        }

    save_match(player, payload.dict())

    return {
        "sucesso": True
    }


@app.get("/api/minhas-partidas")
def minhas_partidas(authorization: str | None = Header(default=None)):
    token = token_from_header(authorization)
    player = get_player_by_token(token)

    if not player:
        return {
            "sucesso": False,
            "mensagem": "Sessão inválida"
        }

    return {
        "sucesso": True,
        "partidas": get_recent_matches(player["id"])
    }


@app.get("/api/ranking-global")
def ranking_global():
    return {
        "sucesso": True,
        "ranking": get_global_ranking()
    }


@app.get("/api/criar-sala")
def criar_sala(
    request: Request,
    aposta: int = Query(default=0),
    authorization: str | None = Header(default=None)
):
    limited = check_limit(request, "criar_sala", 20, 60)
    if limited:
        return limited

    stake = normalize_stake(aposta)
    if stake is None:
        return {
            "sucesso": False,
            "mensagem": "Mesa inválida"
        }

    if stake > 0 and not get_player_by_token(token_from_header(authorization)):
        return {
            "sucesso": False,
            "mensagem": "Faça login para criar mesa valendo Moedas Neon"
        }

    sala = rooms_store.create_room(stake=stake)

    return {
        "sucesso": True,
        "codigo": sala.codigo,
        "jogador": 1,
        "aposta": sala.stake,
        "status": sala.status
    }


@app.get("/api/procurar-partida")
def procurar_partida(
    request: Request,
    aposta: int = Query(default=0),
    authorization: str | None = Header(default=None)
):
    limited = check_limit(request, "matchmaking", 30, 60)
    if limited:
        return limited

    stake = normalize_stake(aposta)
    if stake is None:
        return {
            "sucesso": False,
            "mensagem": "Mesa inválida"
        }

    if stake > 0 and not get_player_by_token(token_from_header(authorization)):
        return {
            "sucesso": False,
            "mensagem": "Faça login para jogar valendo Moedas Neon"
        }

    return matchmaking_queue.find_or_create_match(stake=stake)


@app.get("/api/cancelar-sala/{codigo}")
def cancelar_sala(codigo: str):
    sala = rooms_store.get_room(codigo)

    if not sala:
        return {
            "sucesso": False,
            "mensagem": "Sala não encontrada"
        }

    if sala.status in ["jogando", "pronta"]:
        return {
            "sucesso": False,
            "mensagem": "Não é possível cancelar uma sala que já começou"
        }

    matchmaking_queue.cancel(codigo)
    rooms_store.remove_room(codigo)

    return {
        "sucesso": True
    }


@app.get("/api/entrar-sala/{codigo}")
def entrar_sala(codigo: str):
    sala = rooms_store.get_room(codigo)

    if not sala:
        return {
            "sucesso": False,
            "mensagem": "Sala não encontrada"
        }

    if sala.reserved_players >= 2:
        return {
            "sucesso": False,
            "mensagem": "Sala cheia"
        }

    sala.reserved_players = 2
    sala.status = "pronta"

    return {
        "sucesso": True,
        "codigo": codigo,
        "jogador": 2,
        "status": sala.status
    }


@app.get("/api/status-sala/{codigo}")
def status_sala(codigo: str):
    sala = rooms_store.get_room(codigo)

    if not sala:
        return {
            "sucesso": False,
            "mensagem": "Sala não encontrada"
        }

    return {
        "sucesso": True,
        "codigo": codigo,
        "jogadores": sala.reserved_players,
        "conectados": len(sala.connections[1]) + len(sala.connections[2]),
        "tipo": sala.tipo,
        "aposta": sala.stake,
        "status": sala.status
    }


@app.get("/api/salas")
def listar_salas():
    return rooms_store.public_rooms()


@app.websocket("/ws/air-hockey/{codigo}/{jogador}")
async def air_hockey_websocket(websocket: WebSocket, codigo: str, jogador: int):
    sala = rooms_store.get_room(codigo)

    if not sala or jogador not in [1, 2]:
        await websocket.close(code=1008)
        return

    await websocket_manager.connect(codigo, jogador, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "player_info":
                nome = str(data.get("nome", "")).strip()[:18]
                sala.player_names[jogador] = nome or f"Jogador {jogador}"
                token = str(data.get("token", "")).strip()
                player = get_player_by_token(token)
                if player:
                    sala.player_ids[jogador] = player["id"]
                    sala.player_names[jogador] = player["display_name"]
                await websocket_manager.try_start_room(codigo)
                continue

            sala.game.set_player_input(jogador, data)

    except WebSocketDisconnect:
        websocket_manager.disconnect(codigo, jogador, websocket)


@app.on_event("startup")
async def startup_event():
    init_database()
    await websocket_manager.start()


@app.on_event("shutdown")
async def shutdown_event():
    await websocket_manager.stop()


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
