from dataclasses import dataclass, field
import random
import time
from typing import Dict, Set

from fastapi import WebSocket

from game_state import AirHockeyGame


@dataclass
class Room:
    codigo: str
    status: str = "aguardando"
    reserved_players: int = 1
    tipo: str = "privada"
    stake: int = 0
    paid_out: bool = False
    entry_charged: Dict[int, bool] = field(default_factory=lambda: {1: False, 2: False})
    player_ids: Dict[int, int | None] = field(default_factory=lambda: {1: None, 2: None})
    player_names: Dict[int, str] = field(default_factory=lambda: {1: "Jogador 1", 2: "Jogador 2"})
    connections: Dict[int, Set[WebSocket]] = field(default_factory=lambda: {1: set(), 2: set()})
    game: AirHockeyGame = field(default_factory=AirHockeyGame)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class RoomsStore:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def create_room(self, stake=0) -> Room:
        codigo = self._generate_code()
        room = Room(codigo=codigo, stake=max(int(stake or 0), 0))
        self.rooms[codigo] = room
        return room

    def remove_room(self, codigo: str):
        if codigo in self.rooms:
            del self.rooms[codigo]

    def get_room(self, codigo: str):
        return self.rooms.get(codigo)

    def touch(self, codigo: str):
        room = self.get_room(codigo)
        if room:
            room.updated_at = time.time()

    def cleanup_expired(self, max_wait_seconds=1800, max_finished_seconds=300):
        now = time.time()

        for codigo, room in list(self.rooms.items()):
            connected = len(room.connections[1]) + len(room.connections[2])
            age = now - room.updated_at

            if connected > 0:
                continue

            if room.status == "finished" and age > max_finished_seconds:
                self.remove_room(codigo)
                continue

            if room.status in ["aguardando", "procurando", "pronta", "saldo_insuficiente"] and age > max_wait_seconds:
                self.remove_room(codigo)

    def public_rooms(self):
        return {
            codigo: {
                "status": room.status,
                "tipo": room.tipo,
                "aposta": room.stake,
                "jogadores": room.reserved_players,
                "conectados": len(room.connections[1]) + len(room.connections[2])
            }
            for codigo, room in self.rooms.items()
        }

    def _generate_code(self) -> str:
        codigo = str(random.randint(1000, 9999))

        while codigo in self.rooms:
            codigo = str(random.randint(1000, 9999))

        return codigo


rooms_store = RoomsStore()
