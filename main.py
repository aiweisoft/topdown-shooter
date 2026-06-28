# -*- coding: utf-8 -*-
"""
Top-Down Shooter — 俯视角射击小游戏
"""

import pygame
import sys
import math
import random
import array
import ctypes
from ctypes import wintypes

# ── Windows API keyboard reader (bypasses pygame event system) ──
user32 = ctypes.WinDLL('user32', use_last_error=True)
# Map pygame key constants → Windows virtual-key codes
_VK = {
    pygame.K_w: 0x57, pygame.K_UP: 0x26,
    pygame.K_s: 0x53, pygame.K_DOWN: 0x28,
    pygame.K_a: 0x41, pygame.K_LEFT: 0x25,
    pygame.K_d: 0x44, pygame.K_RIGHT: 0x27,
    pygame.K_r: 0x52, pygame.K_ESCAPE: 0x1B,
}
class _WinKeys:
    """Duck-typed replacement for pygame.key.get_pressed() — uses Win32 API."""
    def __getitem__(self, k):
        vk = _VK.get(k)
        if vk is None:
            return False
        # GetAsyncKeyState: msb = 1 means key is currently down
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)
_win_keys = _WinKeys()

# ── Constants ──
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 60, 60)
GREEN = (60, 255, 60)
BLUE = (60, 120, 255)
YELLOW = (255, 240, 60)
GRAY = (100, 100, 100)
DARK_GRAY = (30, 30, 30)
GRID_COLOR = (25, 25, 30)


# ── Sound System (synthesized — no external files) ──
_sounds = {}
_has_audio = False

def _synth(freq, duration, volume=0.3, wave='sine'):
    """Generate a mono 16-bit PCM sound at 22050 Hz."""
    sr = 22050
    n = int(sr * duration)
    samples = array.array('h', [0]) * n
    for i in range(n):
        t = i / sr
        env = max(0.0, 1.0 - t / duration)  # linear fade-out
        if wave == 'noise':
            val = random.uniform(-1, 1)
        elif wave == 'square':
            val = 1.0 if (freq * t) % 1.0 < 0.5 else -1.0
        else:  # sine
            val = math.sin(2 * math.pi * freq * t)
        sample = int(volume * 32767 * val * env)
        samples[i] = max(-32768, min(32767, sample))
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _synth_sweep(f0, f1, duration, volume=0.3):
    """Frequency sweep from f0→f1."""
    sr = 22050
    n = int(sr * duration)
    samples = array.array('h', [0]) * n
    for i in range(n):
        t = i / sr
        f = f0 + (f1 - f0) * (t / duration)
        env = max(0.0, 1.0 - t / duration)
        val = math.sin(2 * math.pi * f * t)
        sample = int(volume * 32767 * val * env)
        samples[i] = max(-32768, min(32767, sample))
    return pygame.mixer.Sound(buffer=samples.tobytes())

def init_sounds():
    global _has_audio
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        _sounds['shoot']   = _synth(880, 0.06, 0.25)
        _sounds['explode'] = _synth(100, 0.15, 0.30, 'noise')
        _sounds['hit']     = _synth(150, 0.12, 0.40, 'square')
        _sounds['levelup'] = _synth_sweep(400, 800, 0.35, 0.30)
        _has_audio = True
    except Exception:
        _has_audio = False

def play_sound(name):
    if _has_audio:
        s = _sounds.get(name)
        if s:
            s.play()


# ── Level Configuration ──
def level_config(level):
    """Return (target_kills, min_speed, max_speed, spawn_interval) for the given level."""
    target = 3 + level * 2           # enemies to kill to clear wave
    spd_min = 100 + (level - 1) * 8
    spd_max = 150 + (level - 1) * 8
    interval = max(0.3, 1.8 - (level - 1) * 0.08)
    return target, spd_min, spd_max, interval


# ── Player ──
class Player:
    def __init__(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.radius = 15
        self.speed = 280
        self.hp = 3
        self.max_hp = 3
        self.shoot_cooldown = 0.25  # triple shot, so effective rate is higher
        self.last_shot = 0
        self.invincible_time = 0
        self.invincible_duration = 0.8

    def update(self, dt, keys):
        dx, dy = 0.0, 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))
        if self.invincible_time > 0:
            self.invincible_time -= dt

    def draw(self, screen):
        if self.invincible_time > 0 and int(self.invincible_time * 10) % 2 == 0:
            return
        pygame.draw.circle(screen, BLUE, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)
        mx, my = pygame.mouse.get_pos()
        angle = math.atan2(my - self.y, mx - self.x)
        tip_x = self.x + math.cos(angle) * self.radius * 1.1
        tip_y = self.y + math.sin(angle) * self.radius * 1.1
        pygame.draw.circle(screen, WHITE, (int(tip_x), int(tip_y)), 4)

    def get_pos(self):
        return self.x, self.y

    def take_damage(self):
        if self.invincible_time <= 0:
            self.hp -= 1
            self.invincible_time = self.invincible_duration
            return True
        return False


# ── Bullet ──
class Bullet:
    def __init__(self, x, y, target_x, target_y, angle_offset=0):
        self.x = x
        self.y = y
        self.radius = 6          # was 4
        self.speed = 700         # was 520
        # Apply spread offset to the firing angle
        angle = math.atan2(target_y - y, target_x - x) + angle_offset
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        return not (self.x < -50 or self.x > SCREEN_WIDTH + 50
                    or self.y < -50 or self.y > SCREEN_HEIGHT + 50)

    def draw(self, screen):
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.radius)

    def get_pos(self):
        return self.x, self.y


# ── Enemy ──
class Enemy:
    def __init__(self, player_x, player_y, min_speed=100, max_speed=170):
        side = random.randint(0, 3)
        margin = 40
        if side == 0:
            self.x = random.uniform(0, SCREEN_WIDTH)
            self.y = -margin
        elif side == 1:
            self.x = SCREEN_WIDTH + margin
            self.y = random.uniform(0, SCREEN_HEIGHT)
        elif side == 2:
            self.x = random.uniform(0, SCREEN_WIDTH)
            self.y = SCREEN_HEIGHT + margin
        else:
            self.x = -margin
            self.y = random.uniform(0, SCREEN_HEIGHT)
        self.radius = 12
        self.speed = random.uniform(min_speed, max_speed)

    def update(self, dt, player_x, player_y):
        angle = math.atan2(player_y - self.y, player_x - self.x)
        self.x += math.cos(angle) * self.speed * dt
        self.y += math.sin(angle) * self.speed * dt

    def draw(self, screen, player_x, player_y):
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)
        # Eyes look toward player
        angle = math.atan2(player_y - self.y, player_x - self.x)
        for offset in [-0.3, 0.3]:
            ex = self.x + math.cos(angle + offset) * self.radius * 0.4
            ey = self.y + math.sin(angle + offset) * self.radius * 0.4
            pygame.draw.circle(screen, WHITE, (int(ex), int(ey)), 2)

    def get_pos(self):
        return self.x, self.y


# ── Particle ──
class Particle:
    def __init__(self, x, y, color, vel, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.vx = vel[0]
        self.vy = vel[1]
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.radius = random.uniform(2, 5)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        return self.lifetime > 0

    def draw(self, screen):
        t = self.lifetime / self.max_lifetime
        r = int(self.radius * t + 1)
        if r < 1:
            return
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), r)


def spawn_explosion(particles, x, y, color, count=15):
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(80, 200)
        lifetime = random.uniform(0.3, 0.7)
        particles.append(Particle(x, y, color,
                        (math.cos(angle) * speed, math.sin(angle) * speed), lifetime))


def circle_collision(r1, pos1, r2, pos2):
    return math.hypot(pos1[0] - pos2[0], pos1[1] - pos2[1]) < r1 + r2


# ── Game Loop (pure sync) ──
def game_loop(screen, clock):
    font = pygame.font.Font(None, 36)
    large_font = pygame.font.Font(None, 72)

    player = Player()
    bullets = []
    enemies = []
    particles = []
    score = 0
    spawn_timer = 0.0
    game_over = False
    grabfail = 0

    # ── Level system ──
    level = 1
    level_kills = 0          # enemies killed this level
    wave_transition = 0.0    # countdown > 0 means showing "Wave Complete!"
    lvl_target, lvl_spd_min, lvl_spd_max, lvl_interval = level_config(level)

    running = True
    debug_font = pygame.font.Font(None, 24)
    while running:
        dt = clock.tick(FPS) / 1000.0

        # ── Pump & Events ──
        pygame.event.pump()
        # Use Win32 API for keyboard (works without window focus)
        keys = _win_keys
        # Fallback: also try pygame's get_pressed (in case it works on some systems)
        try:
            _py_keys = pygame.key.get_pressed()
            # Merge: if pygame detects a key, trust it
            if any(_py_keys[k] for k in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d)):
                keys = _py_keys
        except Exception:
            pass
        mouse_held = pygame.mouse.get_pressed()
        mouse_pos = pygame.mouse.get_pos()

        restart_pressed = False
        quit_pressed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    restart_pressed = True
                if event.key == pygame.K_ESCAPE:
                    quit_pressed = True

        # ══ grab input focus ══
        if grabfail < 120:
            grabfail += 1
            try:
                pygame.event.set_grab(True)
                pygame.mouse.set_visible(False)
            except Exception:
                pass

        # ── Game Over ──
        if game_over:
            if restart_pressed:
                player = Player()
                bullets.clear()
                enemies.clear()
                particles.clear()
                score = 0
                spawn_timer = 0.0
                game_over = False
                level = 1
                level_kills = 0
                wave_transition = 0.0
                lvl_target, lvl_spd_min, lvl_spd_max, lvl_interval = level_config(level)
                continue
            if keys[pygame.K_r]:         # fallback via physical state
                player = Player()
                bullets.clear()
                enemies.clear()
                particles.clear()
                score = 0
                spawn_timer = 0.0
                game_over = False
                level = 1
                level_kills = 0
                wave_transition = 0.0
                lvl_target, lvl_spd_min, lvl_spd_max, lvl_interval = level_config(level)
                continue
            if quit_pressed or keys[pygame.K_ESCAPE]:
                running = False

        # ── Update ──
        if not game_over:
            if quit_pressed or keys[pygame.K_ESCAPE]:
                running = False
                continue

            player.update(dt, keys)

            if mouse_held[0]:
                now = pygame.time.get_ticks() / 1000.0
                if now - player.last_shot > player.shoot_cooldown:
                    px, py = player.get_pos()
                    # Triple spread shot (±20°)
                    for spread in (-0.35, 0, 0.35):
                        bullets.append(Bullet(px, py, mouse_pos[0], mouse_pos[1], spread))
                    player.last_shot = now
                    play_sound('shoot')

            # ── Wave transition or normal spawn ──
            if wave_transition > 0:
                wave_transition -= dt
                if wave_transition <= 0:
                    level += 1
                    lvl_target, lvl_spd_min, lvl_spd_max, lvl_interval = level_config(level)
                    level_kills = 0
                    play_sound('levelup')
            else:
                spawn_timer += dt
                if spawn_timer >= lvl_interval and level_kills < lvl_target:
                    enemies.append(Enemy(player.x, player.y, lvl_spd_min, lvl_spd_max))
                    spawn_timer = 0.0

            bullets = [b for b in bullets if b.update(dt)]

            for e in enemies:
                e.update(dt, player.x, player.y)

            # Bullet vs Enemy (piercing: bullets pass through enemies)
            ei_set = set()
            for ei, e in enumerate(enemies):
                for b in bullets:
                    if circle_collision(b.radius, b.get_pos(), e.radius, e.get_pos()):
                        ei_set.add(ei)
                        spawn_explosion(particles, e.x, e.y, RED)
                        play_sound('explode')
                        break  # one hit per enemy per frame
            for i in sorted(ei_set, reverse=True):
                del enemies[i]
            kills_this_frame = len(ei_set)
            score += 10 * kills_this_frame
            level_kills += kills_this_frame

            # Wave clear check
            if wave_transition <= 0 and level_kills >= lvl_target and not enemies:
                wave_transition = 2.0   # show "Wave Complete!" for 2 seconds

            # Enemy vs Player
            for e in enemies[:]:
                if circle_collision(player.radius, player.get_pos(), e.radius, e.get_pos()):
                    enemies.remove(e)
                    spawn_explosion(particles, e.x, e.y, RED, 8)
                    if player.take_damage():
                        play_sound('hit')
                    if player.hp <= 0:
                        game_over = True

            particles = [p for p in particles if p.update(dt)]

        # ── Draw ──
        screen.fill(BLACK)

        for i in range(0, SCREEN_WIDTH, 50):
            pygame.draw.line(screen, GRID_COLOR, (i, 0), (i, SCREEN_HEIGHT))
        for i in range(0, SCREEN_HEIGHT, 50):
            pygame.draw.line(screen, GRID_COLOR, (0, i), (SCREEN_WIDTH, i))

        for p in particles:
            p.draw(screen)
        for b in bullets:
            b.draw(screen)
        for e in enemies:
            e.draw(screen, player.x, player.y)
        player.draw(screen)

        mx, my = mouse_pos
        cs = 12
        pygame.draw.line(screen, WHITE, (mx - cs, my), (mx + cs, my), 1)
        pygame.draw.line(screen, WHITE, (mx, my - cs), (mx, my + cs), 1)
        pygame.draw.circle(screen, WHITE, (mx, my), cs + 3, 1)

        if not game_over:
            # Score + Level
            surf = font.render(f"Score: {score}", True, WHITE)
            screen.blit(surf, (12, 12))
            lvl_surf = font.render(f"Level: {level}", True, YELLOW)
            screen.blit(lvl_surf, (SCREEN_WIDTH - lvl_surf.get_width() - 12, 12))
            # Wave progress bar
            if lvl_target > 0:
                prog = min(level_kills / lvl_target, 1.0)
                bx, by, bw, bh = SCREEN_WIDTH - 220, 48, 200, 10
                pygame.draw.rect(screen, DARK_GRAY, (bx, by, bw, bh))
                pygame.draw.rect(screen, YELLOW, (bx, by, int(bw * prog), bh))
                pygame.draw.rect(screen, WHITE, (bx, by, bw, bh), 1)
                pct = font.render(f"{level_kills}/{lvl_target}", True, WHITE)
                screen.blit(pct, (bx - pct.get_width() - 8, by - 4))
            # HP bar
            bx, by, bw, bh = 12, 50, 200, 20
            pygame.draw.rect(screen, DARK_GRAY, (bx, by, bw, bh))
            ratio = player.hp / player.max_hp
            fw = int(bw * ratio)
            hc = GREEN if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
            pygame.draw.rect(screen, hc, (bx, by, fw, bh))
            pygame.draw.rect(screen, WHITE, (bx, by, bw, bh), 2)
            hp_surf = font.render(f"HP {player.hp}/{player.max_hp}", True, WHITE)
            screen.blit(hp_surf, (bx + bw + 12, by - 2))
            # Enemy count
            e_surf = font.render(f"Enemies: {len(enemies)}", True, GRAY)
            screen.blit(e_surf, (12, 80))
            # ── Wave transition overlay ──
            if wave_transition > 0:
                t = large_font.render(f"Wave {level} Complete!", True, GREEN)
                screen.blit(t, t.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))
                sub = font.render(f"Score: {score}", True, WHITE)
                screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)))
            # ── Debug: key states ──
            dbg_y = 115
            for name, kc in [("W/UP", pygame.K_w), ("S/DOWN", pygame.K_s),
                             ("A/LEFT", pygame.K_a), ("D/RIGHT", pygame.K_d)]:
                state = "DOWN" if keys[kc] else "UP  "
                d = debug_font.render(f"{name}:{state}  pos:({int(player.x)},{int(player.y)})", True, YELLOW)
                screen.blit(d, (12, dbg_y))
                dbg_y += 22
            # dt and fps
            fps = clock.get_fps()
            d2 = debug_font.render(f"dt:{dt:.4f}  fps:{fps:.0f}  focus:{pygame.key.get_focused()}", True, YELLOW)
            screen.blit(d2, (12, dbg_y + 5))
        else:
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            screen.blit(ov, (0, 0))
            t1 = large_font.render("GAME OVER", True, RED)
            screen.blit(t1, t1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 70)))
            t2 = font.render(f"Score: {score}  |  Level: {level}", True, WHITE)
            screen.blit(t2, t2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            t3 = font.render("Press [R] to Restart  |  [ESC] to Quit", True, GRAY)
            screen.blit(t3, t3.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60)))

        pygame.display.flip()

    return score


def main():
    pygame.init()
    init_sounds()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Top-Down Shooter")
    clock = pygame.time.Clock()
    try:
        game_loop(screen, clock)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
        except Exception:
            pass
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    main()
