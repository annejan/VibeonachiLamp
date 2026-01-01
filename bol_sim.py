import pygame
import numpy as np
from PIL import Image
import math
import sys

# ===================== CONFIG =====================
NUM_LEDS = 1024*8
SCREEN_SIZE = 900

ROT_SPEED = 1.5
EARTH_ROT_SPEED = 0.01
SUN_ROT_SPEED   = 0.18

AXIAL_TILT = math.radians(23.44)

DAY_TEXTURE   = "world_day.png"
NIGHT_TEXTURE = "world_night.png"

# LED appearance
POINT_SIZE_MIN = 7
POINT_SIZE_MAX = 15
ALPHA_MIN = 40
ALPHA_MAX = 255

# glow
GLOW_RADIUS_MULT = 2.8
GLOW_ALPHA_MULT  = 0.3

# area sampling radius in texture pixels (1 = 5 samples)
AREA_RADIUS = 1
# ==================================================

# ---------- Fibonacci sphere ----------
def fibonacci_sphere(n):
    pts = np.zeros((n,3), dtype=np.float32)
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - 2 * i / (n - 1)
        r = math.sqrt(max(0, 1 - y*y))
        theta = golden * i
        pts[i] = (
            math.cos(theta) * r,
            y,
            math.sin(theta) * r
        )
    return pts

# ---------- Rotations ----------
def rot_x(a):
    c,s = math.cos(a), math.sin(a)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]], dtype=np.float32)

def rot_y(a):
    c,s = math.cos(a), math.sin(a)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]], dtype=np.float32)

def rot_z(a):
    c,s = math.cos(a), math.sin(a)
    return np.array([[c,-s,0],[s,c,0],[0,0,1]], dtype=np.float32)

# ---------- XYZ → UV ----------
def xyz_to_uv(p):
    lon = np.arctan2(p[:,2], p[:,0])
    lat = np.arcsin(p[:,1])

    u = 1.0 - ((lon + math.pi) / (2 * math.pi))
    v = (math.pi/2 - lat) / math.pi

    return np.clip(u,0,0.9999), np.clip(v,0,0.9999)


# ---------- Projection ----------
def project(p):
    scale = SCREEN_SIZE * 0.35
    x = p[:,0] * scale + SCREEN_SIZE/2
    y = -p[:,1] * scale + SCREEN_SIZE/2
    return np.stack((x,y), axis=1)

# ---------- Load textures ----------
def load_tex(path):
    return np.array(Image.open(path).convert("RGB")).astype(np.float32)

tex_day   = load_tex(DAY_TEXTURE)
tex_night = load_tex(NIGHT_TEXTURE)
H, W, _ = tex_day.shape

# ---------- Area sampling ----------
def sample_area(tex, u, v, r):
    H, W, _ = tex.shape

    px = (u * (W - 1)).astype(int)
    py = (v * (H - 1)).astype(int)

    acc = np.zeros((len(px), 3), dtype=np.float32)
    count = 0

    for dy in range(-r, r+1):
        for dx in range(-r, r+1):
            if dx*dx + dy*dy > r*r:
                continue

            sx = np.clip(px + dx, 0, W - 1)
            sy = np.clip(py + dy, 0, H - 1)

            acc += tex[sy, sx]
            count += 1

    return acc / count


# ===================== MAIN =====================
pygame.init()
screen = pygame.display.set_mode((SCREEN_SIZE,SCREEN_SIZE))
pygame.display.set_caption("LED Sphere – Area Sampling")
clock = pygame.time.Clock()

points = fibonacci_sphere(NUM_LEDS)

camX = 0.0
camY = 0.0
earth_rot = 0.0
sun_rot   = 0.0

running = True
while running:
    dt = clock.tick(60)/1000.0

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            running = False

    # ---------- CAMERA INPUT ----------
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:  camY -= ROT_SPEED * dt
    if keys[pygame.K_RIGHT]: camY += ROT_SPEED * dt
    if keys[pygame.K_UP]:    camX -= ROT_SPEED * dt
    if keys[pygame.K_DOWN]:  camX += ROT_SPEED * dt

    camX = max(-math.pi/2 + 0.05, min(math.pi/2 - 0.05, camX))

    # ---------- AUTOMATIC MOTION ----------
    earth_rot += EARTH_ROT_SPEED * dt
    sun_rot   += SUN_ROT_SPEED * dt

    # ---------- ROTATION PIPELINE ----------
    R_tilt  = rot_x(AXIAL_TILT)
    R_earth = rot_y(earth_rot) @ R_tilt
    R_cam   = rot_y(camY) @ rot_x(camX)

    world = points @ R_earth.T
    camera_space = world @ R_cam.T

    # ---------- SUN LIGHT ----------
    sun_dir = np.array([
        math.cos(sun_rot),
        math.sin(sun_rot) * math.sin(AXIAL_TILT),
        math.sin(sun_rot)
    ], dtype=np.float32)
    sun_dir /= np.linalg.norm(sun_dir)

    light = np.einsum('ij,j->i', world, sun_dir)
    day = np.clip((light - 0.1) / 0.9, 0, 1)

    # ---------- TEXTURE SAMPLING (AREA) ----------
    u,v = xyz_to_uv(world)
    col_day   = sample_area(tex_day,   u, v, AREA_RADIUS)
    col_night = sample_area(tex_night, u, v, AREA_RADIUS)
    colors = col_day * day[:,None] + col_night * (1 - day[:,None])
    colors = colors.astype(np.uint8)

    # ---------- VISIBILITY ----------
    visible = camera_space[:,2] > 0
    proj = project(camera_space)

    # ---------- DRAW ----------
    screen.fill((0,0,0))
    for i in range(NUM_LEDS):
        if not visible[i]:
            continue

        x,y = proj[i]
        if not (0 <= x < SCREEN_SIZE and 0 <= y < SCREEN_SIZE):
            continue

        facing = max(0.0, min(1.0, camera_space[i, 2]))
        f = facing ** 1.5

        size  = POINT_SIZE_MIN + f * (POINT_SIZE_MAX - POINT_SIZE_MIN)
        alpha = ALPHA_MIN + f * (ALPHA_MAX - ALPHA_MIN)

        c = colors[i]

        # glow
        glow_r = int(size * GLOW_RADIUS_MULT)
        glow_a = int(alpha * GLOW_ALPHA_MULT)
        if glow_a > 0:
            surf = pygame.Surface((2*glow_r,2*glow_r), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*c, glow_a), (glow_r,glow_r), glow_r)
            screen.blit(surf, (int(x-glow_r), int(y-glow_r)))

        # core LED
        r = int(size)
        surf = pygame.Surface((2*r,2*r), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*c, int(alpha)), (r,r), r)
        screen.blit(surf, (int(x-r), int(y-r)))

    pygame.display.flip()

pygame.quit()
sys.exit()
