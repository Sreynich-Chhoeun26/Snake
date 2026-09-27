import pygame
import math
import random
import sys

SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 700
WORLD_RADIUS = 1600
FPS = 60
BOT_COUNT = 15

BG_COLOR = (22, 28, 48)
GRID_LINE_COLOR = (32, 40, 68)
BORDER_COLOR = (230, 50, 50)

FOOD_PALETTE = [
    (248, 113, 113),
    (251, 146, 60),
    (250, 204, 21),
    (74, 222, 128),
    (96, 165, 250),
    (244, 114, 182),
]


class Food:
    def __init__(self, x=None, y=None, value=1, radius=6):
        if x is None or y is None:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, WORLD_RADIUS - 50)
            self.x = dist * math.cos(angle)
            self.y = dist * math.sin(angle)
        else:
            self.x = x
            self.y = y
        self.value = value
        self.radius = radius
        self.color = random.choice(FOOD_PALETTE)

    def draw(self, surface, cam_x, cam_y):
        sx = int(self.x - cam_x + SCREEN_WIDTH // 2)
        sy = int(self.y - cam_y + SCREEN_HEIGHT // 2)
        if -20 <= sx <= SCREEN_WIDTH + 20 and -20 <= sy <= SCREEN_HEIGHT + 20:
            pygame.draw.circle(surface, self.color, (sx, sy), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (sx - self.radius // 3, sy - self.radius // 3), max(1, self.radius // 3))


class Worm:
    def __init__(self, x, y, is_bot=False, name=None):
        self.x = x
        self.y = y
        self.angle = 0
        self.base_speed = 3.6
        self.boost_speed = 6.8
        self.turn_speed = 0.08
        self.radius = 16
        self.segment_spacing = 7
        self.initial_segments = 25
        self.target_length = self.initial_segments
        self.history = [(x, y)] * (self.initial_segments * self.segment_spacing + 1)
        self.score = 0
        self.is_boosting = False
        self.is_bot = is_bot
        self.name = name or ("Player" if not is_bot else "Bot")
        self.alive = True
        self.head_color = (147, 51, 234) if not is_bot else (250, 120, 86)
        self.body_color = (168, 85, 247) if not is_bot else (251, 146, 60)
        self.alt_body_color = (216, 180, 254) if not is_bot else (253, 186, 116)
        self.eye_white = (255, 255, 255)
        self.pupil_color = (20, 20, 20)

    def update(self, target_angle, boosting, food_list):
        diff = (target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.angle += max(-self.turn_speed, min(self.turn_speed, diff))
        self.is_boosting = boosting and self.target_length > 12
        speed = self.boost_speed if self.is_boosting else self.base_speed

        if self.is_boosting and random.random() < 0.25:
            self.target_length -= 0.15
            self.score = max(0, self.score - 1)
            tail_x, tail_y = self.history[-1]
            food_list.append(Food(tail_x + random.uniform(-5, 5), tail_y + random.uniform(-5, 5), value=1, radius=4))

        self.x += math.cos(self.angle) * speed
        self.y += math.sin(self.angle) * speed

        self.history.insert(0, (self.x, self.y))
        max_history = int(self.target_length * self.segment_spacing) + 1
        if len(self.history) > max_history:
            self.history.pop()

    def get_body_positions(self):
        positions = []
        for i in range(int(self.target_length)):
            idx = i * self.segment_spacing
            if idx < len(self.history):
                positions.append(self.history[idx])
        return positions

    def update_ai(self, food_list, snakes):
        if not food_list:
            target_x, target_y = 0, 0
        else:
            food = min(food_list, key=lambda f: (self.x - f.x) ** 2 + (self.y - f.y) ** 2)
            target_x, target_y = food.x, food.y

        nearest_enemy = None
        nearest_enemy_dist = float('inf')
        for snake in snakes:
            if snake is self or not snake.alive:
                continue
            dist = (self.x - snake.x) ** 2 + (self.y - snake.y) ** 2
            if dist < nearest_enemy_dist:
                nearest_enemy = snake
                nearest_enemy_dist = dist

        if nearest_enemy is not None:
            enemy_dx = nearest_enemy.x - self.x
            enemy_dy = nearest_enemy.y - self.y
            enemy_dist = math.hypot(enemy_dx, enemy_dy)
            if nearest_enemy.target_length > self.target_length and enemy_dist < 260:
                target_x = self.x - enemy_dx * 0.8
                target_y = self.y - enemy_dy * 0.8
            elif nearest_enemy.target_length < self.target_length and enemy_dist < 220:
                intercept_angle = math.atan2(enemy_dy, enemy_dx)
                side = 1 if random.random() < 0.5 else -1
                target_x = nearest_enemy.x + math.cos(intercept_angle + side * 1.0) * 75
                target_y = nearest_enemy.y + math.sin(intercept_angle + side * 1.0) * 75

        dist_from_origin = math.hypot(self.x, self.y)
        if dist_from_origin > WORLD_RADIUS * 0.75:
            target_x = -self.x * 0.8
            target_y = -self.y * 0.8

        target_angle = math.atan2(target_y - self.y, target_x - self.x)
        diff = (target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        self.angle += max(-self.turn_speed * 1.6, min(self.turn_speed * 1.6, diff))

        self.is_boosting = self.target_length > 18 and random.random() < 0.14
        speed = self.boost_speed if self.is_boosting else self.base_speed * 1.08
        self.x += math.cos(self.angle) * speed
        self.y += math.sin(self.angle) * speed

        self.history.insert(0, (self.x, self.y))
        max_history = int(self.target_length * self.segment_spacing) + 1
        if len(self.history) > max_history:
            self.history.pop()

    def draw(self, surface, cam_x, cam_y):
        positions = self.get_body_positions()
        screen_cx = SCREEN_WIDTH // 2
        screen_cy = SCREEN_HEIGHT // 2

        for i in reversed(range(len(positions))):
            bx, by = positions[i]
            sx = int(bx - cam_x + screen_cx)
            sy = int(by - cam_y + screen_cy)
            color = self.body_color if (i // 2) % 2 == 0 else self.alt_body_color
            pygame.draw.circle(surface, color, (sx, sy), self.radius)
            pygame.draw.circle(surface, (126, 34, 206) if not self.is_bot else (185, 92, 33), (sx, sy), self.radius, 2)

        head_sx = int(self.x - cam_x + screen_cx)
        head_sy = int(self.y - cam_y + screen_cy)
        pygame.draw.circle(surface, self.head_color, (head_sx, head_sy), self.radius + 1)

        eye_offset_angle = 0.55
        eye_dist = self.radius * 0.65
        for side in (-1, 1):
            ea = self.angle + side * eye_offset_angle
            ex = head_sx + math.cos(ea) * eye_dist
            ey = head_sy + math.sin(ea) * eye_dist
            pygame.draw.circle(surface, self.eye_white, (int(ex), int(ey)), 5)
            px = ex + math.cos(self.angle) * 2
            py = ey + math.sin(self.angle) * 2
            pygame.draw.circle(surface, self.pupil_color, (int(px), int(py)), 2.5)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Snake_Friend")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 46, bold=True)
        self.reset()

    def spawn_bot_snakes(self):
        bots = []
        for i in range(BOT_COUNT):
            angle = (2 * math.pi * i) / BOT_COUNT
            radius = 320 + (i % 5) * 55
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            bot = Worm(x, y, is_bot=True, name=f"Bot {i + 1}")
            bot.angle = angle + math.pi
            bots.append(bot)
        return bots

    def reset(self):
        self.player = Worm(0, 0, is_bot=False, name="Player")
        self.snakes = [self.player] + self.spawn_bot_snakes()
        self.foods = [Food() for _ in range(400)]
        self.game_over = False

    def drop_food_for_death(self, snake):
        if not snake.alive:
            return
        segments = self.get_snake_segments(snake)
        death_count = max(12, min(30, int(snake.target_length * 2)))
        for index, (bx, by) in enumerate(segments[: max(8, min(len(segments), death_count))]):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(12, 65)
            x = bx + math.cos(angle) * dist
            y = by + math.sin(angle) * dist
            value = 6 + min(18, index // 2)
            self.foods.append(Food(x, y, value=value, radius=8))

    def get_snake_segments(self, snake):
        positions = snake.get_body_positions()
        if not positions:
            return [(snake.x, snake.y)]
        return positions

    def head_hits_other_body(self, attacker, target):
        if not attacker.alive or not target.alive or attacker is target:
            return False

        for index, (bx, by) in enumerate(self.get_snake_segments(target)):
            if index == 0:
                continue
            if (attacker.x - bx) ** 2 + (attacker.y - by) ** 2 <= (attacker.radius + target.radius * 0.9) ** 2:
                return True
        return False

    def head_to_head_collision(self, snake_a, snake_b):
        if not snake_a.alive or not snake_b.alive:
            return False
        distance = (snake_a.x - snake_b.x) ** 2 + (snake_a.y - snake_b.y) ** 2
        threshold = (snake_a.radius + snake_b.radius + 6) ** 2
        return distance <= threshold

    def kill_snake(self, snake):
        if not snake.alive:
            return
        snake.alive = False
        self.drop_food_for_death(snake)
        if snake is self.player:
            self.game_over = True
        elif not any(s.alive for s in self.snakes if s is not self.player):
            self.game_over = True

    def draw_minimap(self):
        size = 120
        padding = 20
        map_rect = pygame.Rect(SCREEN_WIDTH - size - padding, padding, size, size)
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(s, (15, 23, 42, 180), (size // 2, size // 2), size // 2)
        pygame.draw.circle(s, (100, 116, 139, 200), (size // 2, size // 2), size // 2, 2)

        scale = (size // 2) / WORLD_RADIUS
        for snake in self.snakes:
            if not snake.alive:
                continue
            px = int(size // 2 + snake.x * scale)
            py = int(size // 2 + snake.y * scale)
            color = (234, 179, 8) if snake is self.player else (239, 68, 68)
            pygame.draw.circle(s, color, (px, py), 3 if snake is self.player else 2)

        self.screen.blit(s, map_rect.topleft)

    def draw_leaderboard(self):
        panel_x, panel_y = 20, 20
        panel_w, panel_h = 260, 155
        board = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        board.fill((15, 23, 42, 180))
        pygame.draw.rect(board, (148, 163, 184, 120), board.get_rect(), 1)
        self.screen.blit(board, (panel_x, panel_y))

        ordered = sorted(self.snakes, key=lambda s: s.score, reverse=True)[:5]
        title = self.font.render("LEADERBOARD", True, (255, 255, 255))
        self.screen.blit(title, (panel_x + 16, panel_y + 12))

        for index, snake in enumerate(ordered, start=1):
            name = snake.name
            label = f"{index}. {name}: {int(snake.score)}"
            text = self.font.render(label, True, (255, 255, 255) if snake is self.player else (253, 186, 116))
            self.screen.blit(text, (panel_x + 16, panel_y + 35 + index * 22))

    def draw_world_grid(self, cam_x, cam_y):
        grid_size = 60
        start_x = int(-cam_x % grid_size)
        start_y = int(-cam_y % grid_size)
        for x in range(start_x, SCREEN_WIDTH, grid_size):
            pygame.draw.line(self.screen, GRID_LINE_COLOR, (x, 0), (x, SCREEN_HEIGHT), 1)
        for y in range(start_y, SCREEN_HEIGHT, grid_size):
            pygame.draw.line(self.screen, GRID_LINE_COLOR, (0, y), (SCREEN_WIDTH, y), 1)
        arena_sx = int(-cam_x + SCREEN_WIDTH // 2)
        arena_sy = int(-cam_y + SCREEN_HEIGHT // 2)
        pygame.draw.circle(self.screen, BORDER_COLOR, (arena_sx, arena_sy), WORLD_RADIUS, 5)

    def run(self):
        while True:
            self.clock.tick(FPS)
            mouse_x, mouse_y = pygame.mouse.get_pos()
            mouse_buttons = pygame.mouse.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and self.game_over:
                    self.reset()

            if not self.game_over and self.player.alive:
                dx = mouse_x - (SCREEN_WIDTH // 2)
                dy = mouse_y - (SCREEN_HEIGHT // 2)
                target_angle = math.atan2(dy, dx)
                boosting = mouse_buttons[0] or pygame.key.get_pressed()[pygame.K_SPACE]
                self.player.update(target_angle, boosting, self.foods)

            for snake in self.snakes:
                if snake is self.player or not snake.alive:
                    continue
                snake.update_ai(self.foods, self.snakes)

            remaining_food = []
            for food in self.foods:
                eaten = False
                for snake in self.snakes:
                    if not snake.alive:
                        continue
                    if (snake.x - food.x) ** 2 + (snake.y - food.y) ** 2 < (snake.radius + food.radius + 2) ** 2:
                        snake.target_length += 0.4
                        snake.score += food.value * 10
                        eaten = True
                        break
                if not eaten:
                    remaining_food.append(food)
            self.foods = remaining_food

            while len(self.foods) < 400:
                self.foods.append(Food())

            for snake_a in self.snakes:
                if not snake_a.alive:
                    continue
                for snake_b in self.snakes:
                    if snake_a is snake_b or not snake_b.alive:
                        continue

                    if self.head_to_head_collision(snake_a, snake_b):
                        if abs(snake_a.target_length - snake_b.target_length) < 1.0:
                            self.kill_snake(snake_a)
                            self.kill_snake(snake_b)
                        elif snake_a.target_length >= snake_b.target_length:
                            self.kill_snake(snake_b)
                            snake_a.target_length += 0.5
                            snake_a.score += 50
                        else:
                            self.kill_snake(snake_a)
                            snake_b.target_length += 0.5
                            snake_b.score += 50
                        continue

                    if self.head_hits_other_body(snake_a, snake_b):
                        self.kill_snake(snake_a)
                        snake_b.target_length += 0.4
                        snake_b.score += 60
                        continue

                    if self.head_hits_other_body(snake_b, snake_a):
                        self.kill_snake(snake_b)
                        snake_a.target_length += 0.4
                        snake_a.score += 60

            for snake in self.snakes:
                if not snake.alive:
                    continue
                dist_from_origin = math.hypot(snake.x, snake.y)
                if dist_from_origin + snake.radius >= WORLD_RADIUS:
                    self.kill_snake(snake)

            self.screen.fill(BG_COLOR)
            cam_x, cam_y = self.player.x, self.player.y
            self.draw_world_grid(cam_x, cam_y)

            for food in self.foods:
                food.draw(self.screen, cam_x, cam_y)

            for snake in self.snakes:
                if snake.alive:
                    snake.draw(self.screen, cam_x, cam_y)

            self.draw_leaderboard()

            score_surf = self.font.render(f"Score: {int(self.player.score)}", True, (255, 255, 255))
            length_surf = self.font.render(f"Length: {int(self.player.target_length)}", True, (203, 213, 225))
            self.screen.blit(score_surf, (SCREEN_WIDTH - 170, 20))
            self.screen.blit(length_surf, (SCREEN_WIDTH - 170, 48))

            self.draw_minimap()

            if self.game_over:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                self.screen.blit(overlay, (0, 0))
                go_text = self.big_font.render("YOU DIED!", True, (239, 68, 68))
                restart_text = self.font.render("Press SPACE to Play Again", True, (255, 255, 255))
                self.screen.blit(go_text, (SCREEN_WIDTH // 2 - go_text.get_width() // 2, SCREEN_HEIGHT // 2 - 40))
                self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 25))

            pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()