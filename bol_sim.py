import pygame
import numpy as np
from PIL import Image
import math
import sys

# ===================== CONFIG =====================
NUM_LEDS = 400
SCREEN = 1000
POINT_SIZE = 16

DAY_TEX_SIZE   = (256, 128)
NIGHT_TEX_SIZE = (128, 64)

AXIAL_TILT = math.radians(23.44)
TIME_SCALE = 24000.0
VIEW_ROT_SPEED = 2.0  # For keyboard view rotation
MOUSE_SENSITIVITY = 0.002  # For mouse world rotation
# =================================================

# ---------- Fibonacci sphere ----------
def fibonacci_sphere(n):
    pts = np.zeros((n, 3), dtype=np.float32)
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - 2 * i / (n - 1)
        r = math.sqrt(max(0, 1 - y * y))
        t = golden * i
        pts[i] = (math.cos(t) * r, y, math.sin(t) * r)
    return pts

# ---------- Quaternion ----------
def quat_mul(a, b):
    return np.array([
        a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
        a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
        a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
        a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]
    ], dtype=np.float32)

def quat_axis(axis, angle):
    s = math.sin(angle / 2)
    return np.array([
        math.cos(angle / 2),
        axis[0] * s,
        axis[1] * s,
        axis[2] * s
    ], dtype=np.float32)

def quat_rotate(q, v):
    # Vectorized: rotate a batch of vectors (n,3) with quaternion q
    n = v.shape[0]
    qv = np.hstack((np.zeros((n, 1)), v)).astype(np.float32)
    q_expanded = np.tile(q, (n, 1))
    qi_expanded = np.tile(np.array([q[0], -q[1], -q[2], -q[3]]), (n, 1))
    
    out = np.empty((n, 4), dtype=np.float32)
    for i in range(n):
        qvi = quat_mul(q_expanded[0], qv[i])
        out[i] = quat_mul(qvi, qi_expanded[0])
    return out[:, 1:]

# ---------- XYZ → UV ----------
def xyz_to_uv(p):
    lon = np.arctan2(p[:, 2], p[:, 0])
    lat = np.arcsin(p[:, 1])
    u = 1.0 - ((lon + math.pi) / (2 * math.pi))
    v = (math.pi / 2 - lat) / math.pi
    return np.clip(u, 0, 0.9999), np.clip(v, 0, 0.9999)

# ---------- Texture loading ----------
def load_tex(path, size):
    try:
        img = Image.open(path).convert("RGB")
        img = img.resize(size, Image.LANCZOS)
        arr = np.array(img, dtype=np.float32) / 255.0
        print(f"{path}: {size[0]}×{size[1]} ({arr.size / 1024:.1f} KB)")
        return arr
    except FileNotFoundError:
        print(f"Warning: {path} not found. Using gray fallback.")
        return np.full((*size, 3), 0.5, dtype=np.float32)

# ---------- Area sampling ----------
def sample_area(tex, u, v, r=1):
    H, W, _ = tex.shape
    x = (u * (W - 1)).astype(int)
    y = (v * (H - 1)).astype(int)

    acc = np.zeros((len(u), 3), dtype=np.float32)
    cnt = np.zeros(len(u), dtype=np.float32)

    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            sx = np.clip(x + dx, 0, W - 1)
            sy = np.clip(y + dy, 0, H - 1)
            acc += tex[sy, sx]
            cnt += 1

    return acc / cnt[:, None]

# ===================== MAIN =====================
pygame.init()
screen = pygame.display.set_mode((SCREEN, SCREEN))
pygame.display.set_caption(f"LED Globe Simulator – {NUM_LEDS} LEDs (Swapped Controls)")
clock = pygame.time.Clock()

tex_day = load_tex("world_day.png", DAY_TEX_SIZE)
tex_night = load_tex("world_night.png", NIGHT_TEX_SIZE)

points = fibonacci_sphere(NUM_LEDS)

# Keyboard = view quaternion (q_cam) - NOW SWAPPED
pygame.event.set_grab(True)
pygame.mouse.set_visible(False)
q_cam = np.array([1, 0, 0, 0], dtype=np.float32)

# Mouse = world rotation quaternion (q_world) - NOW SWAPPED  
q_world = np.array([1, 0, 0, 0], dtype=np.float32)

seconds_today = 12 * 3600
day_of_year = 172

running = True
while running:
    dt = clock.tick(60) / 1000.0

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            running = False

    # ---------- SWAPPED: Mouse → World Rotation (globe spins) ----------
    dx, dy = pygame.mouse.get_rel()
    if dx != 0:
        delta_yaw = quat_axis([0, 1, 0], -dx * MOUSE_SENSITIVITY)
        q_world = quat_mul(delta_yaw, q_world)
    if dy != 0:
        delta_pitch = quat_axis([1, 0, 0], -dy * MOUSE_SENSITIVITY)
        q_world = quat_mul(delta_pitch, q_world)
    q_world /= np.linalg.norm(q_world)

    # ---------- SWAPPED: Keyboard → View Rotation (camera orbits) ----------
    keys = pygame.key.get_pressed()
    angle = VIEW_ROT_SPEED * dt
    
    # Horizontal view rotation (orbit left/right)
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        delta = quat_axis([0, 1, 0], angle)
        q_cam = quat_mul(delta, q_cam)
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        delta = quat_axis([0, 1, 0], -angle)
        q_cam = quat_mul(delta, q_cam)
    
    # Vertical view rotation (orbit up/down)
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        delta = quat_axis([1, 0, 0], angle)
        q_cam = quat_mul(delta, q_cam)
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        delta = quat_axis([1, 0, 0], -angle)
        q_cam = quat_mul(delta, q_cam)
        
    q_cam /= np.linalg.norm(q_cam)

    # ---------- Time Advancement ----------
    seconds_today += dt * TIME_SCALE
    if seconds_today >= 86400:
        seconds_today -= 86400
        day_of_year = (day_of_year + 1) % 365

    # Sun position (world space)
    sun_lon = 2 * math.pi * (seconds_today / 86400.0)
    sun_lat = math.sin(2 * math.pi * day_of_year / 365.2422) * AXIAL_TILT
    sun = np.array([
        math.cos(sun_lat) * math.cos(sun_lon),
        math.sin(sun_lat),
        math.cos(sun_lat) * math.sin(sun_lon)
    ], dtype=np.float32)

    # ---------- Rotation Pipeline ----------
    # Step 1: World positions (points rotated by q_world)
    world_pos = quat_rotate(q_world, points)

    # Step 2: Lighting and UV from world_pos (fixed to globe)
    light = np.clip(np.dot(world_pos, sun), 0, 1)
    u, v = xyz_to_uv(world_pos)
    col_day = sample_area(tex_day, u, v)
    col_night = sample_area(tex_night, u, v)
    colors = (col_day * light[:, None] + col_night * (1 - light[:, None])) * 255
    colors = np.clip(colors, 0, 255).astype(np.uint8)

    # Step 3: View positions (world_pos rotated by q_cam) for projection
    view_pos = quat_rotate(q_cam, world_pos)

    # ---------- Draw ----------
    screen.fill((0, 0, 0))
    scale = SCREEN * 0.38

    for i, (x, y, z) in enumerate(view_pos):
        if z <= 0:
            continue
        px = int(x * scale + SCREEN // 2)
        py = int(-y * scale + SCREEN // 2)
        if 0 <= px < SCREEN and 0 <= py < SCREEN:
            pygame.draw.circle(
                screen,
                colors[i].tolist(),
                (px, py),
                POINT_SIZE
            )

    pygame.display.flip()

pygame.quit()
sys.exit()
