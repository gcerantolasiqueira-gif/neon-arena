import asyncio

from rooms import rooms_store
from wallet import debit_entry, pay_prize, refund_entry


class WebSocketManager:
    def __init__(self):
        self.running = False
        self.loop_task = None

    async def start(self):
        if self.running:
            return

        self.running = True
        self.loop_task = asyncio.create_task(self.game_loop())

    async def stop(self):
        self.running = False

        if self.loop_task:
            self.loop_task.cancel()

    async def connect(self, codigo, jogador, websocket):
        await websocket.accept()

        sala = rooms_store.get_room(codigo)
        if not sala:
            await websocket.close()
            return

        sala.connections[jogador].add(websocket)
        rooms_store.touch(codigo)

        await self.try_start_room(codigo)

        await websocket.send_json({
            "type": "connected",
            "jogador": jogador,
            "codigo": codigo
        })

    def disconnect(self, codigo, jogador, websocket):
        sala = rooms_store.get_room(codigo)
        if not sala:
            return

        sala.connections[jogador].discard(websocket)
        rooms_store.touch(codigo)

        if len(sala.connections[1]) == 0 or len(sala.connections[2]) == 0:
            if sala.game.status != "finished":
                self.refund_room_entries(sala)
            sala.status = "aguardando"
            sala.game.pause_online()

    async def try_start_room(self, codigo):
        sala = rooms_store.get_room(codigo)
        if not sala:
            return

        both_connected = len(sala.connections[1]) > 0 and len(sala.connections[2]) > 0
        if not both_connected or sala.status == "jogando":
            return

        if sala.stake > 0:
            if not sala.player_ids[1] or not sala.player_ids[2]:
                sala.status = "aguardando_login"
                return

            for jogador in [1, 2]:
                if not sala.entry_charged[jogador]:
                    ok, balance, error = debit_entry(sala.player_ids[jogador], sala.stake, sala.codigo)

                    if not ok:
                        self.refund_room_entries(sala)
                        sala.status = "saldo_insuficiente"
                        return

                    sala.entry_charged[jogador] = True

        sala.status = "jogando"
        sala.game.start_match()

    def refund_room_entries(self, sala):
        for jogador in [1, 2]:
            if sala.entry_charged[jogador] and sala.player_ids[jogador]:
                refund_entry(sala.player_ids[jogador], sala.stake, sala.codigo)
                sala.entry_charged[jogador] = False

    def pay_room_prize_if_needed(self, sala):
        if sala.paid_out or sala.stake <= 0 or sala.game.status != "finished":
            return

        winner_side = sala.game.winner
        if winner_side not in ["p1", "p2"]:
            return

        winner_slot = 1 if winner_side == "p1" else 2
        winner_id = sala.player_ids[winner_slot]

        if not winner_id:
            return

        pay_prize(winner_id, sala.stake, sala.codigo)
        sala.paid_out = True

    async def game_loop(self):
        last_time = asyncio.get_event_loop().time()

        while self.running:
            now = asyncio.get_event_loop().time()
            dt = min(now - last_time, 0.05)
            last_time = now

            for codigo, sala in list(rooms_store.rooms.items()):
                if sala.status == "jogando":
                    rooms_store.touch(codigo)
                    sala.game.update(dt)
                    self.pay_room_prize_if_needed(sala)

                await self.broadcast_state(codigo)

            rooms_store.cleanup_expired()
            await asyncio.sleep(1 / 60)

    async def broadcast_state(self, codigo):
        sala = rooms_store.get_room(codigo)
        if not sala:
            return

        payload = {
            "type": "state",
            "room": {
                "codigo": codigo,
                "status": sala.status,
                "conectados": {
                    "p1": len(sala.connections[1]),
                    "p2": len(sala.connections[2])
                },
                "players": {
                    "p1": sala.player_names[1],
                    "p2": sala.player_names[2]
                },
                "aposta": sala.stake
            },
            "game": sala.game.to_dict()
        }

        websockets = list(sala.connections[1]) + list(sala.connections[2])

        for websocket in websockets:
            try:
                await websocket.send_json(payload)
            except Exception:
                pass


websocket_manager = WebSocketManager()
