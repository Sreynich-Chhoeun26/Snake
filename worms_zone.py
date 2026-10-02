"""
WORMS ZONE — Full Feature Build
==========================================
Controls:
  - Move mouse       : steer snake
  - Left Mouse/Space : boost (costs score + size)
  - R                : respawn when dead
  - Enter (menu)     : select / buy skin
  - Arrow keys (menu): change skin
  - ESC              : quit

Requirements: pip install pygame
Run: python worms_zone.py
"""

import pygame
import math
import random
import sys
import json
import os
import datetime

# ============================================================
# INITIALIZATION
# ============================================================
pygame.init()
pygame.font.init()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Worms Zone")
clock = pygame.time.Clock()

WORLD_WIDTH = 4000
WORLD_HEIGHT = 4000

# Colors
COLOR_BG = (22, 96, 160)
COLOR_GRID = (18, 82, 140)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GOLD = (255, 215, 0)
COLOR_RED = (231, 76, 60)
COLOR_GREEN = (46, 204, 113)
COLOR_BLUE = (52, 152, 219)

# Fonts
FONT_UI = pygame.font.SysFont("arial", 16, bold=True)
FONT_BIG = pygame.font.SysFont("arial", 36, bold=True)
FONT_HUGE = pygame.font.SysFont("arial", 52, bold=True)
FONT_FLOAT = pygame.font.SysFont("arial", 14, bold=True)
FONT_SMALL = pygame.font.SysFont("arial", 12, bold=True)


# ============================================================
# PRE-RENDERED SURFACES
# ============================================================
FOOD_TYPES = [
    {"color": (46, 204, 113), "radius": 10, "points": 10},
    {"color": (231, 76, 60),  "radius": 8,  "points": 8},
    {"color": (241, 196, 15), "radius": 9,  "points": 12},
    {"color": (155, 89, 182), "radius": 7,  "points": 6},
    {"color": (230, 126, 34), "radius": 11, "points": 15},
]

FOOD_SURFACES = []
for _info in FOOD_TYPES:
    _r = _info["radius"]
    _s = pygame.Surface((_r * 2 + 2, _r * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(_s, _info["color"], (_r + 1, _r + 1), _r)
    pygame.draw.circle(_s, COLOR_WHITE, (_r - _r // 3 + 1, _r - _r // 3 + 1), max(2, _r // 3))
    FOOD_SURFACES.append(_s)

_BODY_CACHE = {}


def get_body_surface(color, radius):
    key = (color, radius)
    if key not in _BODY_CACHE:
        size = radius * 2 + 4
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (size // 2, size // 2), radius)
        pygame.draw.circle(surf, COLOR_WHITE, (size // 2, size // 2), radius, 1)
        _BODY_CACHE[key] = (surf, size // 2)
    return _BODY_CACHE[key]


_HEAD_CACHE = {}


def get_head_surface(color, radius):
    key = (color, radius)
    if key not in _HEAD_CACHE:
        size = radius * 2 + 6
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (size // 2, size // 2), radius + 1)
        pygame.draw.circle(surf, COLOR_WHITE, (size // 2, size // 2), radius + 1, 2)
        _HEAD_CACHE[key] = (surf, size // 2)
    return _HEAD_CACHE[key]


# ============================================================
# SKINS
# ============================================================
WORM_SKINS = [
    {"name": "Classic", "color": (255, 255, 255), "price": 0},
    {"name": "Ember",   "color": (231, 76, 60),   "price": 50},
    {"name": "Solar",   "color": (241, 196, 15),  "price": 100},
    {"name": "Violet",  "color": (155, 89, 182),  "price": 150},
    {"name": "Ocean",   "color": (52, 152, 219),  "price": 200},
    {"name": "Toxic",   "color": (46, 204, 113),  "price": 300},
    {"name": "Sunset",  "color": (230, 126, 34),  "price": 400},
    {"name": "Mint",    "color": (26, 188, 156),  "price": 500},
    {"name": "Blood",   "color": (192, 57, 43),   "price": 700},
    {"name": "Royal",   "color": (142, 68, 173),  "price": 1000},
]


# ============================================================
# SAVE FILE
# ============================================================
SAVE_FILE = "worms_save.json"


def load_save():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                data.setdefault("coins", 0)
                data.setdefault("best_score", 0)
                data.setdefault("skins_owned", [0])
                data.setdefault("daily_best", {})
                data.setdefault("weekly_best", {})
                return data
        except Exception:
            pass
    return {"coins": 0, "best_score": 0, "skins_owned": [0],
            "daily_best": {}, "weekly_best": {}}


def write_save(data):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


# ============================================================
# CAMERA
# ============================================================
class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def snap(self, tx, ty):
        self.x = tx - SCREEN_WIDTH // 2
        self.y = ty - SCREEN_HEIGHT // 2

    def follow(self, tx, ty, ease=0.15):
        target_x = tx - SCREEN_WIDTH // 2
        target_y = ty - SCREEN_HEIGHT // 2
        self.x += (target_x - self.x) * ease
        self.y += (target_y - self.y) * ease

    def world_to_screen(self, wx, wy):
        return int(wx - self.x), int(wy - self.y)


camera = Camera()

# Recent deaths, for radar
RECENT_DEATHS = []


# ============================================================
# FLOATING TEXT
# ============================================================
class FloatingText:
    def __init__(self, x, y, text, color=COLOR_WHITE):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.alpha = 255
        self.life = 45

    def update(self):
        self.y -= 1.2
        self.alpha -= 6
        self.life -= 1

    def draw(self, surface):
        if self.alpha > 0:
            txt = FONT_FLOAT.render(self.text, True, self.color)
            txt.set_alpha(max(0, self.alpha))
            sx, sy = camera.world_to_screen(self.x, self.y)
            surface.blit(txt, (sx, sy))


# ============================================================
# FOOD
# ============================================================
class Food:
    def __init__(self, x=None, y=None):
        self.x = x if x is not None else random.randint(50, WORLD_WIDTH - 50)
        self.y = y if y is not None else random.randint(50, WORLD_HEIGHT - 50)
        info = random.choice(FOOD_TYPES)
        self.type_index = FOOD_TYPES.index(info)
        self.color = info["color"]
        self.radius = info["radius"]
        self.points = info["points"]

    def draw(self, surface):
        sx, sy = camera.world_to_screen(self.x, self.y)
        if -20 < sx < SCREEN_WIDTH + 20 and -20 < sy < SCREEN_HEIGHT + 20:
            surf = FOOD_SURFACES[self.type_index]
            surface.blit(surf, (sx - self.radius - 1, sy - self.radius - 1))


# ============================================================
# SNAKE BASE
# ============================================================
class Snake:
    def __init__(self, name, color, x, y, radius=14, initial_length=30):
        self.name = name
        self.color = color
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.angle = random.uniform(0, math.pi * 2)
        self.alive = True
        self.score = 0

        self.base_speed = 3.2
        self.boost_speed = 6.5
        self.speed = self.base_speed
        self.boosting = False
        self.boost_mass_debt = 0.0

        self.segment_spacing = self.radius * 0.55
        self.length = initial_length
        self.max_body_length = 180
        self.body = [[self.x, self.y] for _ in range(self.length)]
        self.path_history = [[self.x, self.y] for _ in range(60)]

    def grow(self, amount):
        if len(self.body) >= self.max_body_length:
            self.score += amount // 2
            return
        self.score += amount
        segs = max(1, amount // 4)
        tail = self.body[-1]
        for _ in range(segs):
            if len(self.body) >= self.max_body_length:
                break
            self.body.append([tail[0], tail[1]])

    def _update_body(self):
        self.path_history.insert(0, [self.x, self.y])

        pixels_needed = len(self.body) * self.segment_spacing + 40
        step = max(self.speed, 0.5)
        needed_points = int(pixels_needed / step) + 30
        max_len = max(60, min(needed_points, 900))
        if len(self.path_history) > max_len:
            del self.path_history[max_len:]

        if len(self.body) == 0:
            return

        self.body[0][0] = self.x
        self.body[0][1] = self.y

        history = self.path_history
        seg_idx = 1
        target_dist = self.segment_spacing
        accumulated = 0.0

        for j in range(len(history) - 1):
            p1 = history[j]
            p2 = history[j + 1]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 0.001:
                continue

            while accumulated + seg_len >= target_dist and seg_idx < len(self.body):
                t = (target_dist - accumulated) / seg_len
                self.body[seg_idx][0] = p1[0] + (p2[0] - p1[0]) * t
                self.body[seg_idx][1] = p1[1] + (p2[1] - p1[1]) * t
                seg_idx += 1
                target_dist += self.segment_spacing

            accumulated += seg_len
            if seg_idx >= len(self.body):
                break

    def die(self):
        self.alive = False
        dropped = []
        step = max(3, len(self.body) // 60)
        for i in range(0, len(self.body), step):
            seg = self.body[i]
            food = Food(seg[0], seg[1])
            food.points = max(3, int(self.score * 0.15))
            food.radius = min(16, 5 + food.points // 6)
            dropped.append(food)
        # Register death for radar
        RECENT_DEATHS.append([self.x, self.y, 600])
        return dropped

    def draw(self, surface):
        if not self.alive:
            return

        r = int(self.radius)
        body_surf, body_half = get_body_surface(self.color, r)
        for i in range(len(self.body) - 1, 0, -1):
            seg = self.body[i]
            sx, sy = camera.world_to_screen(seg[0], seg[1])
            if -40 < sx < SCREEN_WIDTH + 40 and -40 < sy < SCREEN_HEIGHT + 40:
                surface.blit(body_surf, (sx - body_half, sy - body_half))

        hx, hy = camera.world_to_screen(self.x, self.y)
        head_surf, head_half = get_head_surface(self.color, r)
        surface.blit(head_surf, (hx - head_half, hy - head_half))

        eye_dist = self.radius * 0.45
        eye_offset = 0.55
        for sign in (1, -1):
            ex = hx + math.cos(self.angle + eye_offset * sign) * eye_dist
            ey = hy + math.sin(self.angle + eye_offset * sign) * eye_dist
            pygame.draw.circle(surface, COLOR_WHITE, (int(ex), int(ey)), 4)
            pygame.draw.circle(surface, COLOR_BLACK, (int(ex), int(ey)), 2)

        if self.name:
            tag = FONT_SMALL.render(self.name[:14], True, COLOR_WHITE)
            tag.set_alpha(180)
            surface.blit(tag, (hx - tag.get_width() // 2, hy - int(self.radius) - 18))


# ============================================================
# PLAYER SNAKE
# ============================================================
class PlayerSnake(Snake):
    def __init__(self, color=COLOR_WHITE):
        super().__init__(
            name="You",
            color=color,
            x=WORLD_WIDTH // 2,
            y=WORLD_HEIGHT // 2,
            radius=14,
            initial_length=25,
        )
        self.powerups = {}
        self.zoom = 1.0

    def update(self, target_x, target_y, boosting, foods):
        if not self.alive:
            return

        for k in list(self.powerups.keys()):
            self.powerups[k] -= 1
            if self.powerups[k] <= 0:
                del self.powerups[k]

        speed_mult = 1.7 if "speed" in self.powerups else 1.0
        self.boosting = boosting and self.score > 15
        if self.boosting:
            self.speed = self.boost_speed * speed_mult
            cost = 0.4 + self.score / 1500.0
            self.score = max(0, self.score - cost)
            self.boost_mass_debt += 0.03
            while self.boost_mass_debt >= 1.0 and len(self.body) > 12:
                self.body.pop()
                self.boost_mass_debt -= 1.0
        else:
            self.speed = self.base_speed * speed_mult

        dx = target_x - self.x
        dy = target_y - self.y
        if math.hypot(dx, dy) > 5:
            target_angle = math.atan2(dy, dx)
            diff = target_angle - self.angle
            while diff > math.pi:
                diff -= math.pi * 2
            while diff < -math.pi:
                diff += math.pi * 2
            turn_rate = 0.24 if "turn" in self.powerups else 0.15
            self.angle += diff * turn_rate

        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

        if "magnet" in self.powerups:
            pull_radius = 220
            for f in foods:
                d = math.hypot(f.x - self.x, f.y - self.y)
                if 1 < d < pull_radius:
                    strength = 2.5 * (1 - d / pull_radius)
                    f.x += (self.x - f.x) / d * strength
                    f.y += (self.y - f.y) / d * strength

        self.x = max(self.radius, min(WORLD_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(WORLD_HEIGHT - self.radius, self.y))

        self._update_body()
        self.radius = min(24, 14 + self.score / 800)
        self.segment_spacing = self.radius * 0.55

        # Zoom calculation
        base_zoom = max(0.75, 1.0 - self.score / 15000)
        if "zoom" in self.powerups:
            base_zoom *= 0.7
        self.zoom = base_zoom


# ============================================================
# AI SNAKE
# ============================================================
BOT_NAMES = [
    "LouderBoi103", "WatergateTendency81", "Spud", "PoeticFighter81207",
    "SkyMammoth", "Anton Teterin", "CoilCrusher", "VenomStrike",
    "TwistTerror", "FangFury", "PythonPredator", "CobraCommander",
    "SlitherKing", "WormLord", "HissHunter", "BoaBruiser",
]

SNAKE_COLORS = [
    (231, 76, 60), (241, 196, 15), (155, 89, 182), (52, 152, 219),
    (230, 126, 34), (26, 188, 156), (192, 57, 43), (142, 68, 173),
    (41, 128, 185), (39, 174, 96),
]


class AISnake(Snake):
    _career = {}

    def __init__(self, name, color, x, y):
        super().__init__(name, color, x, y,
                         radius=random.randint(11, 16),
                         initial_length=random.randint(20, 40))
        self.score = random.randint(50, 400)
        self.wander_angle = random.uniform(0, math.pi * 2)
        self.wander_timer = 0
        self.boost_timer = 0
        self.state = "feed"
        self.state_timer = random.randint(60, 180)
        self.eat_cooldown = 0

        # Persistent career high (fake global ranking)
        if name not in AISnake._career:
            AISnake._career[name] = random.randint(2000, 200000)
        self.career_high = AISnake._career[name]

    def _nearest_food(self, foods, max_d=700):
        best, best_d = None, max_d
        for f in foods:
            d = math.hypot(f.x - self.x, f.y - self.y)
            if d < best_d:
                best, best_d = f, d
        return best

    def _avoid_walls(self):
        margin = 200
        ax = ay = 0
        if self.x < margin:
            ax += (margin - self.x) / margin
        if self.x > WORLD_WIDTH - margin:
            ax -= (self.x - (WORLD_WIDTH - margin)) / margin
        if self.y < margin:
            ay += (margin - self.y) / margin
        if self.y > WORLD_HEIGHT - margin:
            ay -= (self.y - (WORLD_HEIGHT - margin)) / margin
        return ax, ay

    def _choose_state(self, player):
        if not player.alive:
            self.state = "feed"
            return
        d = math.hypot(player.x - self.x, player.y - self.y)
        if d < 320 and self.score > player.score * 1.3:
            self.state = "hunt"
        elif d < 220 and self.score < player.score * 0.7:
            self.state = "flee"
        elif random.random() < 0.7:
            self.state = "feed"
        else:
            self.state = "wander"

    def update(self, foods, all_snakes, player):
        if not self.alive:
            return

        if self.boost_timer > 0:
            self.boost_timer -= 1
        if self.eat_cooldown > 0:
            self.eat_cooldown -= 1

        self.state_timer -= 1
        if self.state_timer <= 0:
            self._choose_state(player)
            self.state_timer = random.randint(60, 180)

        target_angle = None

        if self.state == "hunt" and player.alive:
            predict_time = 40
            fut_x = player.x + math.cos(player.angle) * player.speed * predict_time
            fut_y = player.y + math.sin(player.angle) * player.speed * predict_time
            cut_x = fut_x + math.cos(player.angle) * 100
            cut_y = fut_y + math.sin(player.angle) * 100
            target_angle = math.atan2(cut_y - self.y, cut_x - self.x)
            if self.score > 100 and random.random() < 0.05:
                self.boost_timer = 20
        elif self.state == "flee" and player.alive:
            dx = self.x - player.x
            dy = self.y - player.y
            target_angle = math.atan2(dy, dx)
            if self.score > 60 and random.random() < 0.08:
                self.boost_timer = 15
        elif self.state == "feed":
            food = self._nearest_food(foods)
            if food:
                target_angle = math.atan2(food.y - self.y, food.x - self.x)
            else:
                self.state = "wander"
                target_angle = self.wander_angle

        if target_angle is None:
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                self.wander_angle += random.uniform(-0.5, 0.5)
                self.wander_timer = random.randint(30, 90)
            target_angle = self.wander_angle

        ax, ay = self._avoid_walls()
        if ax != 0 or ay != 0:
            avoid_a = math.atan2(ay, ax)
            target_angle = target_angle * 0.6 + avoid_a * 0.4

        diff = target_angle - self.angle
        while diff > math.pi:
            diff -= math.pi * 2
        while diff < -math.pi:
            diff += math.pi * 2
        self.angle += diff * 0.08

        if self.boost_timer > 0 and self.score > 30:
            self.speed = self.boost_speed
            self.score = max(0, self.score - 0.3)
        else:
            self.speed = self.base_speed

        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.x = max(self.radius, min(WORLD_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(WORLD_HEIGHT - self.radius, self.y))

        self._update_body()
        self.radius = min(24, 11 + self.score / 800)
        self.segment_spacing = self.radius * 0.55


# ============================================================
# POWER-UPS (6 TYPES)
# ============================================================
class PowerUp:
    TYPES = {
        "speed":  {"color": (46, 204, 113),  "duration": 300, "label": "SPEED"},
        "food5":  {"color": (52, 152, 219),  "duration": 480, "label": "5x FOOD"},
        "magnet": {"color": (231, 76, 60),   "duration": 360, "label": "MAGNET"},
        "radar":  {"color": (155, 89, 182),  "duration": 600, "label": "RADAR"},
        "turn":   {"color": (26, 188, 156),  "duration": 400, "label": "TURN"},
        "zoom":   {"color": (241, 196, 15),  "duration": 500, "label": "ZOOM"},
    }

    def __init__(self, x=None, y=None):
        self.x = x if x is not None else random.randint(100, WORLD_WIDTH - 100)
        self.y = y if y is not None else random.randint(100, WORLD_HEIGHT - 100)
        self.type = random.choice(list(self.TYPES.keys()))
        self.color = self.TYPES[self.type]["color"]
        self.radius = 11

    def draw(self, surface):
        sx, sy = camera.world_to_screen(self.x, self.y)
        if -30 < sx < SCREEN_WIDTH + 30 and -30 < sy < SCREEN_HEIGHT + 30:
            pygame.draw.circle(surface, self.color, (sx, sy), self.radius)
            pygame.draw.circle(surface, COLOR_WHITE, (sx, sy), self.radius, 2)
            pygame.draw.circle(surface, COLOR_WHITE, (sx, sy), 4)


# ============================================================
# COLLISIONS
# ============================================================
def check_collisions(player, ai_snakes, foods, floating_texts):
    if player.alive:
        for ai in ai_snakes:
            if not ai.alive:
                continue
            if math.hypot(player.x - ai.x, player.y - ai.y) < player.radius + ai.radius:
                foods.extend(player.die())
                foods.extend(ai.die())
                floating_texts.append(FloatingText(player.x, player.y, "CRASH!", COLOR_RED))
                return
            for seg in ai.body:
                if math.hypot(player.x - seg[0], player.y - seg[1]) < player.radius + ai.radius * 0.9:
                    foods.extend(player.die())
                    floating_texts.append(FloatingText(player.x, player.y, "You died!", COLOR_RED))
                    return

    for ai in ai_snakes:
        if not ai.alive:
            continue
        hit = False
        for seg in player.body[1:]:
            if math.hypot(ai.x - seg[0], ai.y - seg[1]) < ai.radius + player.radius * 0.9:
                foods.extend(ai.die())
                floating_texts.append(FloatingText(ai.x, ai.y, f"{ai.name} died!", COLOR_GOLD))
                hit = True
                break
        if hit:
            continue

    for i, a1 in enumerate(ai_snakes):
        if not a1.alive:
            continue
        for a2 in ai_snakes[i + 1:]:
            if not a2.alive:
                continue
            if math.hypot(a1.x - a2.x, a1.y - a2.y) < a1.radius + a2.radius:
                foods.extend(a1.die())
                foods.extend(a2.die())
                continue
            a1_hit = False
            for seg in a2.body[1:]:
                if math.hypot(a1.x - seg[0], a1.y - seg[1]) < a1.radius + a2.radius * 0.9:
                    foods.extend(a1.die())
                    a1_hit = True
                    break
            if not a1_hit and a2.alive:
                for seg in a1.body[1:]:
                    if math.hypot(a2.x - seg[0], a2.y - seg[1]) < a2.radius + a1.radius * 0.9:
                        foods.extend(a2.die())
                        break


# ============================================================
# HUD
# ============================================================
def draw_hud(surface, player, ai_snakes, save):
    lb = pygame.Surface((250, 340), pygame.SRCALPHA)
    lb.fill((10, 25, 50, 170))
    surface.blit(lb, (15, 15))

    title = FONT_UI.render("Leaderboard", True, COLOR_WHITE)
    surface.blit(title, (25, 22))

    all_p = [{"name": s.name, "score": int(s.career_high), "me": False}
             for s in ai_snakes if s.alive]
    if player.alive:
        all_p.append({"name": player.name, "score": int(save["best_score"]), "me": True})
    all_p.sort(key=lambda k: k["score"], reverse=True)

    y = 48
    for i, p in enumerate(all_p[:10]):
        col = COLOR_GOLD if p["me"] else COLOR_WHITE
        n = FONT_UI.render(f"{i + 1}. {p['name'][:14]}", True, col)
        s = FONT_UI.render(f"{p['score']:,}", True, col)
        surface.blit(n, (25, y))
        surface.blit(s, (180, y))
        y += 20

    # Player coins, best
    coin_txt = FONT_UI.render(f"Coins: {save['coins']:,}", True, COLOR_GOLD)
    surface.blit(coin_txt, (25, y + 5))
    best_txt = FONT_UI.render(f"Best: {save['best_score']:,}", True, COLOR_WHITE)
    surface.blit(best_txt, (25, y + 25))

    # Live score
    sc = FONT_BIG.render(f"Score: {int(player.score):,}", True, COLOR_WHITE)
    surface.blit(sc, (20, SCREEN_HEIGHT - 55))

    hint = FONT_UI.render("Hold LMB / SPACE to boost", True, COLOR_WHITE)
    surface.blit(hint, (SCREEN_WIDTH - hint.get_width() - 20, SCREEN_HEIGHT - 30))

    px = 20
    py = SCREEN_HEIGHT - 90
    for k, v in player.powerups.items():
        info = PowerUp.TYPES[k]
        box = FONT_UI.render(f"{info['label']} {v // 60 + 1}s", True, info['color'])
        surface.blit(box, (px, py))
        px += box.get_width() + 15


def draw_minimap(surface, player, ai_snakes):
    size = 160
    x = SCREEN_WIDTH - size - 20
    y = 20
    mm = pygame.Surface((size, size), pygame.SRCALPHA)
    mm.fill((10, 25, 50, 180))
    pygame.draw.rect(mm, (255, 255, 255, 100), (0, 0, size, size), 2)

    for ai in ai_snakes:
        if not ai.alive:
            continue
        mx = int(ai.x / WORLD_WIDTH * size)
        my = int(ai.y / WORLD_HEIGHT * size)
        pygame.draw.circle(mm, ai.color, (mx, my), 2)

    if player.alive and "radar" in player.powerups:
        for entry in RECENT_DEATHS:
            mx = int(entry[0] / WORLD_WIDTH * size)
            my = int(entry[1] / WORLD_HEIGHT * size)
            pulse = 2 + int(1.5 * (1 + math.sin(pygame.time.get_ticks() * 0.01)))
            pygame.draw.circle(mm, COLOR_RED, (mx, my), pulse)
            pygame.draw.circle(mm, COLOR_WHITE, (mx, my), pulse, 1)

    if player.alive:
        px = int(player.x / WORLD_WIDTH * size)
        py = int(player.y / WORLD_HEIGHT * size)
        pygame.draw.circle(mm, COLOR_GREEN, (px, py), 4)
        pygame.draw.circle(mm, COLOR_WHITE, (px, py), 4, 1)

    surface.blit(mm, (x, y))


def draw_death_screen(surface, player, coins_earned, save):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    t1 = FONT_BIG.render("YOU DIED!", True, COLOR_RED)
    surface.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, SCREEN_HEIGHT // 2 - 130))

    t2 = FONT_BIG.render(f"Score: {int(player.score):,}", True, COLOR_WHITE)
    surface.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, SCREEN_HEIGHT // 2 - 60))

    t_coins = FONT_UI.render(f"+{coins_earned} coins earned", True, COLOR_GOLD)
    surface.blit(t_coins, (SCREEN_WIDTH // 2 - t_coins.get_width() // 2, SCREEN_HEIGHT // 2 - 10))

    t_best = FONT_UI.render(f"Best: {save['best_score']:,}", True, COLOR_WHITE)
    surface.blit(t_best, (SCREEN_WIDTH // 2 - t_best.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    t3 = FONT_BIG.render("Press R to Respawn", True, COLOR_GOLD)
    surface.blit(t3, (SCREEN_WIDTH // 2 - t3.get_width() // 2, SCREEN_HEIGHT // 2 + 70))


# ============================================================
# SKIN MENU
# ============================================================
def skin_menu(save):
    selected = 0
    t = 0
    message = ""
    message_timer = 0

    while True:
        clock.tick(60)
        t += 1
        if message_timer > 0:
            message_timer -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_RETURN:
                    skin = WORM_SKINS[selected]
                    if selected in save["skins_owned"]:
                        return selected
                    elif save["coins"] >= skin["price"]:
                        save["coins"] -= skin["price"]
                        save["skins_owned"].append(selected)
                        write_save(save)
                        message = f"Unlocked {skin['name']}!"
                        message_timer = 120
                    else:
                        message = f"Need {skin['price'] - save['coins']} more coins"
                        message_timer = 120
                if event.key == pygame.K_LEFT:
                    selected = (selected - 1) % len(WORM_SKINS)
                if event.key == pygame.K_RIGHT:
                    selected = (selected + 1) % len(WORM_SKINS)

        # Mouse click select / buy
        mx, my = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            for i in range(len(WORM_SKINS)):
                cx = 80 + (i % 5) * 230
                cy = 250 + (i // 5) * 180
                if math.hypot(mx - cx, my - cy) < 60:
                    selected = i

        screen.fill(COLOR_BG)

        # Header
        coin_txt = FONT_UI.render(f"Coins: {save['coins']:,}", True, COLOR_GOLD)
        screen.blit(coin_txt, (SCREEN_WIDTH - coin_txt.get_width() - 25, 25))

        today = datetime.date.today().isoformat()
        yw = datetime.date.today().isocalendar()
        week = f"{yw[0]}-W{yw[1]}"
        daily = save["daily_best"].get(today, 0)
        weekly = save["weekly_best"].get(week, 0)

        dtxt = FONT_UI.render(f"Today's best: {daily:,}", True, COLOR_WHITE)
        screen.blit(dtxt, (25, 25))
        wtxt = FONT_UI.render(f"This week: {weekly:,}", True, COLOR_WHITE)
        screen.blit(wtxt, (25, 50))
        btxt = FONT_UI.render(f"All-time best: {save['best_score']:,}", True, COLOR_WHITE)
        screen.blit(btxt, (25, 75))

        title = FONT_HUGE.render("Worms Zone", True, COLOR_WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 120))

        subtitle = FONT_UI.render("Choose Your Worm", True, COLOR_WHITE)
        screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 185))

        for i, skin in enumerate(WORM_SKINS):
            cx = 80 + (i % 5) * 230
            cy = 320 + (i // 5) * 180
            owned = i in save["skins_owned"]

            for k in range(3):
                pygame.draw.circle(screen, skin["color"], (cx - 30 + k * 30, cy), 16)
                pygame.draw.circle(screen, COLOR_WHITE, (cx - 30 + k * 30, cy), 16, 2)

            if i == selected:
                pulse = 65 + int(5 * math.sin(t * 0.1))
                pygame.draw.circle(screen, COLOR_GOLD, (cx, cy), pulse, 3)

            name = FONT_UI.render(skin["name"], True, COLOR_WHITE)
            screen.blit(name, (cx - name.get_width() // 2, cy + 50))

            if not owned:
                price_txt = FONT_SMALL.render(f"{skin['price']} coins", True, COLOR_GOLD)
                screen.blit(price_txt, (cx - price_txt.get_width() // 2, cy + 68))
                pygame.draw.circle(screen, (0, 0, 0, 100), (cx, cy), 55)
                pygame.draw.circle(screen, COLOR_GOLD, (cx, cy), 55, 2)

        if message_timer > 0:
            msg = FONT_UI.render(message, True, COLOR_GOLD)
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT - 100))

        hint = FONT_UI.render("Arrow keys to select — Enter to buy / start", True, COLOR_WHITE)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 60))

        pygame.display.flip()


# ============================================================
# MAIN
# ============================================================
def main():
    global camera

    save = load_save()

    skin_index = skin_menu(save)
    if skin_index is None:
        pygame.quit()
        sys.exit()

    player_color = WORM_SKINS[skin_index]["color"]

    player = PlayerSnake(color=player_color)
    camera.snap(player.x, player.y)

    ai_snakes = []
    random.shuffle(BOT_NAMES)
    for i in range(12):
        ai_snakes.append(AISnake(
            BOT_NAMES[i % len(BOT_NAMES)],
            SNAKE_COLORS[i % len(SNAKE_COLORS)],
            random.randint(200, WORLD_WIDTH - 200),
            random.randint(200, WORLD_HEIGHT - 200),
        ))

    foods = [Food() for _ in range(250)]
    powerups = [PowerUp() for _ in range(20)]
    floating_texts = []

    coins_earned = 0
    was_alive = True
    death_fade = 0

    running = True
    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r and not player.alive:
                    player = PlayerSnake(color=player_color)
                    camera.snap(player.x, player.y)
                    coins_earned = 0
                    death_fade = 0
                    was_alive = True

        mx, my = pygame.mouse.get_pos()
        mouse_world_x = mx + camera.x
        mouse_world_y = my + camera.y
        keys = pygame.key.get_pressed()
        mouse_btns = pygame.mouse.get_pressed()
        boosting = keys[pygame.K_SPACE] or mouse_btns[0]

        # --- Update player ---
        if player.alive:
            player.update(mouse_world_x, mouse_world_y, boosting, foods)
            camera.follow(player.x, player.y)

        # --- Update AI ---
        for ai in ai_snakes:
            if ai.alive:
                ai.update(foods, ai_snakes, player)

        # --- Food eating ---
        for snake in [player] + ai_snakes:
            if not snake.alive:
                continue
            if snake is not player and snake.eat_cooldown > 0:
                continue
            for idx in range(len(foods) - 1, -1, -1):
                food = foods[idx]
                if math.hypot(snake.x - food.x, snake.y - food.y) < snake.radius + food.radius:
                    mult = 1
                    if snake is player and "food5" in player.powerups:
                        mult = 5
                    snake.grow(food.points * mult)
                    foods[idx] = Food()
                    if snake is not player:
                        snake.eat_cooldown = 2

        # --- Power-up pickup ---
        if player.alive:
            for idx in range(len(powerups) - 1, -1, -1):
                pu = powerups[idx]
                if math.hypot(player.x - pu.x, player.y - pu.y) < player.radius + pu.radius:
                    player.powerups[pu.type] = PowerUp.TYPES[pu.type]["duration"]
                    label = PowerUp.TYPES[pu.type]["label"]
                    floating_texts.append(FloatingText(player.x, player.y, label, pu.color))
                    powerups[idx] = PowerUp()

        # --- Collisions ---
        check_collisions(player, ai_snakes, foods, floating_texts)

        # --- Detect death transition ---
        if was_alive and not player.alive:
            coins_earned = max(1, int(player.score * 0.1))
            save["coins"] += coins_earned
            if int(player.score) > save["best_score"]:
                save["best_score"] = int(player.score)
            today = datetime.date.today().isoformat()
            yw = datetime.date.today().isocalendar()
            week = f"{yw[0]}-W{yw[1]}"
            save["daily_best"][today] = max(save["daily_best"].get(today, 0), int(player.score))
            save["weekly_best"][week] = max(save["weekly_best"].get(week, 0), int(player.score))
            write_save(save)
            death_fade = 30
        was_alive = player.alive

        # --- Respawn dead AI ---
        for i, ai in enumerate(ai_snakes):
            if not ai.alive and random.random() < 0.01:
                ai_snakes[i] = AISnake(
                    random.choice(BOT_NAMES),
                    random.choice(SNAKE_COLORS),
                    random.randint(200, WORLD_WIDTH - 200),
                    random.randint(200, WORLD_HEIGHT - 200),
                )

        # --- Floating texts ---
        for ft in floating_texts[:]:
            ft.update()
            if ft.life <= 0:
                floating_texts.remove(ft)

        # --- Recent deaths for radar ---
        for entry in RECENT_DEATHS[:]:
            entry[2] -= 1
            if entry[2] <= 0:
                RECENT_DEATHS.remove(entry)

        # ====================================================
        # RENDER
        # ====================================================
        screen.fill(COLOR_BG)

        # Grid
        grid = 80
        start_x = int(-camera.x % grid)
        start_y = int(-camera.y % grid)
        for x in range(start_x, SCREEN_WIDTH, grid):
            pygame.draw.line(screen, COLOR_GRID, (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(start_y, SCREEN_HEIGHT, grid):
            pygame.draw.line(screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y), 1)

        for food in foods:
            food.draw(screen)
        for pu in powerups:
            pu.draw(screen)
        for ai in ai_snakes:
            ai.draw(screen)
        if player.alive:
            player.draw(screen)
        for ft in floating_texts:
            ft.draw(screen)

        # HUD
        draw_hud(screen, player, ai_snakes, save)
        draw_minimap(screen, player, ai_snakes)

        # Death screen
        if not player.alive:
            draw_death_screen(screen, player, coins_earned, save)

        # Zoom (only when needed, avoids costly smoothscale at start)
        zoom = player.zoom if player.alive else 1.0
        if zoom < 0.99:
            scaled = pygame.transform.smoothscale(
                screen,
                (int(SCREEN_WIDTH * zoom), int(SCREEN_HEIGHT * zoom))
            )
            screen.fill(COLOR_BG)
            screen.blit(scaled, (
                (SCREEN_WIDTH - scaled.get_width()) // 2,
                (SCREEN_HEIGHT - scaled.get_height()) // 2
            ))

        # Death fade overlay (after zoom, so it always covers)
        if death_fade > 0:
            death_fade -= 1
            alpha = int(120 * (1 - death_fade / 30))
            fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            fade.fill((0, 0, 0, alpha))
            screen.blit(fade, (0, 0))

        pygame.display.flip()

    write_save(save)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()