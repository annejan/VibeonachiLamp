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
VIEW_ROT_SPEED = 1.5    # toetsen
# =================================================


# ---------- Fibonacci sphere ----------
def fibonacci_sphere(n):
    pts = np.zeros((n,3), dtype=np.float32)
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - 2 * i / (n - 1)
        r = math.sqrt(max(0, 1 - y*y))
        t = golden * i
        pts[i] = (
            math.cos(t) * r,
            y,
            math.sin(t) * r
        )
    return pts


# ---------- Quaternion ----------
def quat_mul(a, b):
    return np.array([
        a[0]*b[0] - a[1]*b[1] - a[2]*b[2] - a[3]*b[3],
        a[0]*b[1] + a[1]*b[0] + a[2]*b[3] - a[3]*b[2],
        a[0]*b[2] - a[1]*b[3] + a[2]*b[0] + a[3]*b[1],
        a[0]*b[3] + a[1]*b[2] - a[2]*b[1] + a[3]*b[0]
    ], dtype=np.float32)

def quat_axis(axis, angle):
    s = math.sin(angle/2)
    return np.array([
        math.cos(angle/2),
        axis[0]*s,
        axis[1]*s,
        axis[2]*s
    ], dtype=np.float32)

def quat_rotate(q, v):
    qv = np.array([0, v[0], v[1], v[2]], dtype=np.float32)
    qi = np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float32)
    r = quat_mul(quat_mul(q, qv), qi)
    return r[1:]


# ---------- XYZ → UV ----------
def xyz_to_uv(p):
    lon = np.arctan2(p[:,2], p[:,0])
    lat = np.arcsin(p[:,1])
    u = 1.0 - ((lon + math.pi) / (2 * math.pi))
    v = (math.pi/2 - lat) / math.pi
    return np.clip(u,0,0.9999), np.clip(v,0,0.9999)


# ---------- Texture loading ----------
def load_tex(path, size):
    img = Image.open(path).convert("RGB")
    img = img.resize(size, Image.LANCZOS)
    arr = np.array(img, dtype=np.float32)
    print(f"{path}: {size[0]}×{size[1]} ({arr.size/1024:.1f} KB)")
    return arr


# ---------- Area sampling ----------
def sample_area(tex, u, v, r=1):
    H, W, _ = tex.shape
    x = (u * (W - 1)).astype(int)
    y = (v * (H - 1)).astype(int)

    acc = np.zeros((len(u), 3), dtype=np.float32)
    cnt = np.zeros(len(u), dtype=np.float32)

    for dy in range(-r, r+1):
        for dx in range(-r, r+1):
            if dx*dx + dy*dy > r*r:
                continue
            sx = np.clip(x+dx, 0, W-1)
            sy = np.clip(y+dy, 0, H-1)
            acc += tex[sy, sx]
            cnt += 1

    return acc / cnt[:,None]


# ===================== MAIN =====================
pygame.init()
screen = pygame.display.set_mode((SCREEN, SCREEN))
pygame.display.set_caption(f"LED Globe Simulator – {NUM_LEDS} LEDs")
clock = pygame.time.Clock()

tex_day   = load_tex("world_day.png", DAY_TEX_SIZE)
tex_night = load_tex("world_night.png", NIGHT_TEX_SIZE)

points = fibonacci_sphere(NUM_LEDS)

# mouse = IMU quaternion
pygame.event.set_grab(True)
pygame.mouse.set_visible(False)
q_cam = np.array([1,0,0,0], dtype=np.float32)

# keyboard = absolute world offset (THIS is the key)
q_world = np.array([1,0,0,0], dtype=np.float32)

seconds_today = 12 * 3600
day_of_year   = 172

running = True
while running:
    dt = clock.tick(60) / 1000.0

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            running = False

    # ---------- mouse → IMU ----------
    dx, dy = pygame.mouse.get_rel()
    q_cam = quat_mul(quat_axis([0,1,0], -dx*0.002), q_cam)
    q_cam = quat_mul(quat_axis([1,0,0], -dy*0.002), q_cam)

    # ---------- keyboard → WORLD OFFSET (FIXED ORDER) ----------
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        q_world = quat_mul(
            q_world,
            quat_axis([0,1,0],  VIEW_ROT_SPEED * dt)
        )
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        q_world = quat_mul(
            q_world,
            quat_axis([0,1,0], -VIEW_ROT_SPEED * dt)
        )

    # normalize (important)
    q_world /= np.linalg.norm(q_world)

    # ---------- time ----------
    seconds_today += dt * TIME_SCALE
    if seconds_today >= 86400:
        seconds_today -= 86400
        day_of_year = (day_of_year + 1) % 365

    sun_lon = 2*math.pi * (seconds_today / 86400.0)
    sun_lat = math.sin(2*math.pi * day_of_year / 365.2422) * AXIAL_TILT

    sun = np.array([
        math.cos(sun_lat)*math.cos(sun_lon),
        math.sin(sun_lat),
        math.cos(sun_lat)*math.sin(sun_lon)
    ], dtype=np.float32)

    # ---------- WORLD ROTATION PIPELINE ----------
    world = []
    for x,y,z in points:
        p = quat_rotate(q_cam, (x,y,z))           # IMU / mouse movement
        world.append(p)

    world = np.array(world, dtype=np.float32)

    # ---------- lighting ----------
    light = np.clip(world @ sun, 0, 1)

    # ---------- textures ----------
    u, v = xyz_to_uv(world)
    col_day   = sample_area(tex_day, u, v)
    col_night = sample_area(tex_night, u, v)
    colors = col_day * light[:,None] + col_night * (1-light[:,None])
    colors = colors.astype(np.uint8)

    # ---------- draw ----------
    screen.fill((0,0,0))
    scale = SCREEN * 0.38

    for i,(x,y,z) in enumerate(world):
        if z <= 0:
            continue
        px = int(x*scale + SCREEN//2)
        py = int(-y*scale + SCREEN//2)
        pygame.draw.circle(
            screen,
            colors[i].tolist(),
            (px,py),
            POINT_SIZE
        )

    pygame.display.flip()

pygame.quit()
sys.exit()
