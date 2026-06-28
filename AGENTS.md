# AGENTS.md — Top-Down Shooter

## Quick start

```bash
pip install -r requirements.txt
python main.py           # desktop
# or double-click start.bat
```

## Entry points

- `main.py` — everything. Player, Bullet, Enemy, Particle classes + game loop.
- `__main__.py` — thin wrapper for `python -m topdown_shooter` (not used directly).

## Critical quirks

- **Keyboard uses Win32 API, not pygame.** `pygame.key.get_pressed()` and KEYDOWN events do not work on this machine (SDL windows driver quirk). The game reads keys via `ctypes.windll.user32.GetAsyncKeyState()` in `_WinKeys`. Do not switch back to `pygame.key.get_pressed()` without verifying on this machine.
- **Sounds are synthesized** at startup via `_synth()` / `_synth_sweep()` — no audio asset files. If `pygame.mixer.init()` fails, `_has_audio = False` and all `play_sound()` calls are silent no-ops (not a bug).
- **Sync game loop** — pure `while` + `clock.tick(FPS)`. No asyncio.
- **Pygbag** (`requirements.txt`) is present for Web builds (`pygbag main.py` → `build/web/`), but the game is desktop-first. The pygbag build may need `asyncio` conversion if re-enabled.

## Game architecture

- **Single file** (~540 lines), all state in module-level game loop variables.
- **Level config** computed live by `level_config(level)` — no external data files.
- **No tests, no CI, no lint/typecheck config.**
- **Constants** (screen size, colors, speeds) at module top in ALL_CAPS.
- Invincibility frames: `player.invincible_time` countdown after `take_damage()`.

## Controls

| Action | Input |
|--------|-------|
| Move | WASD / Arrows |
| Shoot | Hold LMB (triple spread, piercing) |
| Restart | R |
| Quit | ESC |
