from rooms import rooms_store


class MatchmakingQueue:
    def __init__(self):
        self.waiting_rooms = {}

    def find_or_create_match(self, stake=0):
        stake = max(int(stake or 0), 0)
        waiting_room = self._get_waiting_room(stake)

        if waiting_room:
            waiting_room.reserved_players = 2
            waiting_room.status = "pronta"
            self.waiting_rooms.pop(stake, None)

            return {
                "sucesso": True,
                "encontrou": True,
                "codigo": waiting_room.codigo,
                "jogador": 2,
                "status": waiting_room.status
            }

        room = rooms_store.create_room(stake=stake)
        room.tipo = "matchmaking"
        room.status = "procurando"
        room.reserved_players = 1
        self.waiting_rooms[stake] = room.codigo

        return {
            "sucesso": True,
            "encontrou": False,
            "codigo": room.codigo,
            "jogador": 1,
            "status": room.status
        }

    def cancel(self, codigo):
        for stake, room_code in list(self.waiting_rooms.items()):
            if room_code == codigo:
                self.waiting_rooms.pop(stake, None)

    def _get_waiting_room(self, stake):
        waiting_room_code = self.waiting_rooms.get(stake)

        if not waiting_room_code:
            return None

        room = rooms_store.get_room(waiting_room_code)

        if not room or room.status != "procurando" or room.reserved_players != 1:
            self.waiting_rooms.pop(stake, None)
            return None

        return room


matchmaking_queue = MatchmakingQueue()
