import math
import random
import time


WIDTH = 1100
HEIGHT = 560
PLAYER_RADIUS = 34
PUCK_RADIUS = 19
PLAYER_SPEED = 610
FRICTION = 0.996
HIT_POWER = 14
MAX_PUCK_SPEED = 24
GOAL_HEIGHT = 190
WIN_SCORE = 7


class AirHockeyGame:
    def __init__(self):
        self.p1 = self._player(170, HEIGHT / 2, "#ff416d")
        self.p2 = self._player(WIDTH - 170, HEIGHT / 2, "#00eaff")
        self.puck = {"x": WIDTH / 2, "y": HEIGHT / 2, "vx": 0, "vy": 0}
        self.score = {"p1": 0, "p2": 0}
        self.stats = {
            "p1": {"touches": 0, "shots": 0},
            "p2": {"touches": 0, "shots": 0}
        }
        self.inputs = {
            1: self._empty_input(),
            2: self._empty_input()
        }
        self.status = "waiting"
        self.countdown_end = 0
        self.goal_pause_end = 0
        self.last_event_id = 0
        self.last_event = None
        self.winner = None

    def _player(self, x, y, color):
        return {
            "x": x,
            "y": y,
            "lastX": x,
            "lastY": y,
            "color": color
        }

    def _empty_input(self):
        return {
            "up": False,
            "down": False,
            "left": False,
            "right": False
        }

    def start_match(self):
        if self.status in ["playing", "countdown", "goal"]:
            return

        self.status = "countdown"
        self.countdown_end = time.time() + 3
        self.winner = None

    def pause_online(self):
        if self.status != "finished":
            self.status = "waiting"
            self.puck["vx"] = 0
            self.puck["vy"] = 0

    def set_player_input(self, jogador, data):
        if jogador not in [1, 2]:
            return

        if data.get("type") == "reset":
            if self.status != "finished":
                return
            self.reset_match()
            return

        if data.get("type") != "input":
            return

        current = self.inputs[jogador]
        keys = data.get("keys", {})

        current["up"] = bool(keys.get("up"))
        current["down"] = bool(keys.get("down"))
        current["left"] = bool(keys.get("left"))
        current["right"] = bool(keys.get("right"))

    def reset_match(self):
        self.score = {"p1": 0, "p2": 0}
        self.stats = {
            "p1": {"touches": 0, "shots": 0},
            "p2": {"touches": 0, "shots": 0}
        }
        self.reset_positions(False)
        self.status = "countdown"
        self.countdown_end = time.time() + 3
        self.winner = None

    def reset_positions(self, serve=True, direction=1):
        self.p1.update({"x": 170, "y": HEIGHT / 2, "lastX": 170, "lastY": HEIGHT / 2})
        self.p2.update({"x": WIDTH - 170, "y": HEIGHT / 2, "lastX": WIDTH - 170, "lastY": HEIGHT / 2})
        self.puck.update({"x": WIDTH / 2, "y": HEIGHT / 2, "vx": 0, "vy": 0})

        if serve:
            self.goal_pause_end = time.time() + 0.9
            self.serve_direction = direction

    def update(self, dt):
        now = time.time()

        if self.status == "waiting" or self.status == "finished":
            return

        if self.status == "countdown":
            if now >= self.countdown_end:
                self.status = "playing"
                self.start_puck()
            return

        if self.status == "goal":
            if now >= self.goal_pause_end:
                self.status = "playing"
                direction = getattr(self, "serve_direction", 1)
                self.puck["vx"] = 8 * direction
                self.puck["vy"] = 4 if random.random() > 0.5 else -4
            return

        self.move_players(dt)
        self.update_puck()

    def start_puck(self):
        self.puck["vx"] = 8 if random.random() > 0.5 else -8
        self.puck["vy"] = 4 if random.random() > 0.5 else -4

    def move_players(self, dt):
        self._move_player(self.p1, self.inputs[1], "left", dt)
        self._move_player(self.p2, self.inputs[2], "right", dt)

    def _move_player(self, player, input_state, side, dt):
        player["lastX"] = player["x"]
        player["lastY"] = player["y"]

        move_x = 0
        move_y = 0

        if input_state["up"]:
            move_y -= 1
        if input_state["down"]:
            move_y += 1
        if input_state["left"]:
            move_x -= 1
        if input_state["right"]:
            move_x += 1

        length = math.hypot(move_x, move_y)
        if length > 0:
            player["x"] += move_x / length * PLAYER_SPEED * dt
            player["y"] += move_y / length * PLAYER_SPEED * dt

        self.limit_player(player, side)

    def limit_player(self, player, side):
        player["y"] = max(PLAYER_RADIUS, min(HEIGHT - PLAYER_RADIUS, player["y"]))

        if side == "left":
            player["x"] = max(PLAYER_RADIUS, min(WIDTH / 2 - PLAYER_RADIUS, player["x"]))
        else:
            player["x"] = max(WIDTH / 2 + PLAYER_RADIUS, min(WIDTH - PLAYER_RADIUS, player["x"]))

    def update_puck(self):
        self.puck["x"] += self.puck["vx"]
        self.puck["y"] += self.puck["vy"]
        self.puck["vx"] *= FRICTION
        self.puck["vy"] *= FRICTION

        if abs(self.puck["vx"]) < 0.03:
            self.puck["vx"] = 0
        if abs(self.puck["vy"]) < 0.03:
            self.puck["vy"] = 0

        goal_top = HEIGHT / 2 - GOAL_HEIGHT / 2
        goal_bottom = HEIGHT / 2 + GOAL_HEIGHT / 2
        inside_goal = goal_top < self.puck["y"] < goal_bottom

        if self.puck["x"] - PUCK_RADIUS <= 0:
            if inside_goal:
                self.goal("p2")
                return

            self.puck["x"] = PUCK_RADIUS
            self.puck["vx"] *= -1
            self.emit_event("hit", self.puck["x"], self.puck["y"], "#ffffff")

        if self.puck["x"] + PUCK_RADIUS >= WIDTH:
            if inside_goal:
                self.goal("p1")
                return

            self.puck["x"] = WIDTH - PUCK_RADIUS
            self.puck["vx"] *= -1
            self.emit_event("hit", self.puck["x"], self.puck["y"], "#ffffff")

        if self.puck["y"] - PUCK_RADIUS <= 0:
            self.puck["y"] = PUCK_RADIUS
            self.puck["vy"] *= -1
            self.emit_event("hit", self.puck["x"], self.puck["y"], "#ffffff")

        if self.puck["y"] + PUCK_RADIUS >= HEIGHT:
            self.puck["y"] = HEIGHT - PUCK_RADIUS
            self.puck["vy"] *= -1
            self.emit_event("hit", self.puck["x"], self.puck["y"], "#ffffff")

        self.player_collision(self.p1, "p1")
        self.player_collision(self.p2, "p2")

    def player_collision(self, player, name):
        dx = self.puck["x"] - player["x"]
        dy = self.puck["y"] - player["y"]
        distance = math.hypot(dx, dy)
        min_distance = PLAYER_RADIUS + PUCK_RADIUS

        if distance >= min_distance or distance <= 0:
            return

        nx = dx / distance
        ny = dy / distance

        self.puck["x"] = player["x"] + nx * min_distance
        self.puck["y"] = player["y"] + ny * min_distance

        player_vx = player["x"] - player["lastX"]
        player_vy = player["y"] - player["lastY"]
        player_speed = math.hypot(player_vx, player_vy)
        current_speed = math.hypot(self.puck["vx"], self.puck["vy"])
        new_speed = max(HIT_POWER + player_speed * 0.8, current_speed + 2.5)

        self.puck["vx"] = nx * new_speed + player_vx * 0.45
        self.puck["vy"] = ny * new_speed + player_vy * 0.45

        self.stats[name]["touches"] += 1

        if name == "p1" and self.puck["vx"] > 0:
            self.stats[name]["shots"] += 1
        if name == "p2" and self.puck["vx"] < 0:
            self.stats[name]["shots"] += 1

        self.limit_puck_speed()
        color = "#ff416d" if name == "p1" else "#00eaff"
        self.emit_event("hit", self.puck["x"], self.puck["y"], color)

    def limit_puck_speed(self):
        speed = math.hypot(self.puck["vx"], self.puck["vy"])

        if speed > MAX_PUCK_SPEED:
            factor = MAX_PUCK_SPEED / speed
            self.puck["vx"] *= factor
            self.puck["vy"] *= factor

    def goal(self, player):
        self.score[player] += 1
        self.status = "goal"

        if player == "p1":
            self.emit_event("goal", WIDTH - 28, HEIGHT / 2, "#00eaff", "GOOOOL DO JOGADOR 1!")
            self.reset_positions(True, 1)
        else:
            self.emit_event("goal", 28, HEIGHT / 2, "#ff416d", "GOOOOL DO JOGADOR 2!")
            self.reset_positions(True, -1)

        if self.score["p1"] >= WIN_SCORE or self.score["p2"] >= WIN_SCORE:
            self.status = "finished"
            self.winner = "p1" if self.score["p1"] > self.score["p2"] else "p2"
            self.emit_event("victory", WIDTH / 2, HEIGHT / 2, "#ffffff", "")

    def emit_event(self, event_type, x, y, color, message=""):
        self.last_event_id += 1
        self.last_event = {
            "id": self.last_event_id,
            "type": event_type,
            "x": x,
            "y": y,
            "color": color,
            "message": message
        }

    def to_dict(self):
        countdown = 0

        if self.status == "countdown":
            countdown = max(0, math.ceil(self.countdown_end - time.time()))

        return {
            "status": self.status,
            "countdown": countdown,
            "p1": self.p1,
            "p2": self.p2,
            "puck": self.puck,
            "score": self.score,
            "stats": self.stats,
            "winner": self.winner,
            "event": self.last_event
        }
