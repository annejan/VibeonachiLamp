import math
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# Parameters
# =====================================================
diameter = 180
thickness = 8
hole_count = 400

r_inner = diameter / 2 - thickness
golden = (1 + math.sqrt(5)) / 2

# north hemisphere
north_ids = list(range(0, 200))
zones = [
    range(0, 40),
    range(40, 80),
    range(80, 120),
    range(120, 160),
    range(160, 200),
]

# =====================================================
# Helpers
# =====================================================
def unit(v):
    return v / np.linalg.norm(v)

def dist(p, q):
    return np.linalg.norm(p - q)

def surface_dist(a, b, r):
    return r * math.acos(np.clip(np.dot(unit(a), unit(b)), -1.0, 1.0))

def arc_points(a, b, r, steps=20):
    ua = unit(a)
    ub = unit(b)
    angle = math.acos(np.clip(np.dot(ua, ub), -1.0, 1.0))
    if angle < 1e-6:
        return np.array([r * ua])
    return np.array([
        r * (
            math.sin((1 - t) * angle) * ua +
            math.sin(t * angle) * ub
        ) / math.sin(angle)
        for t in np.linspace(0, 1, steps)
    ])

# =====================================================
# Generate Fibonacci points
# =====================================================
points = []
for i in range(hole_count):
    z = 1 - 2 * (i + 0.5) / hole_count
    theta = math.acos(z)
    phi = 2 * math.pi * i / golden

    x = r_inner * math.sin(theta) * math.cos(phi)
    y = r_inner * math.sin(theta) * math.sin(phi)
    zc = r_inner * math.cos(theta)

    points.append(np.array([x, y, zc]))

points = np.array(points)
north_pts = {i: unit(points[i]) * r_inner for i in north_ids}

# =====================================================
# DATA wiring (Fibonacci, hemisphere)
# =====================================================
data_path = north_ids
data_segments = [
    dist(points[data_path[i]], points[data_path[i+1]])
    for i in range(len(data_path) - 1)
]

data_norm = (data_segments - min(data_segments)) / (
    max(data_segments) - min(data_segments) + 1e-9
)

# =====================================================
# POWER routing (zone medoid)
# =====================================================
inject_points = {}

# choose medoid per zone
for zone in zones:
    best = None
    best_sum = 1e18
    for i in zone:
        s = sum(surface_dist(north_pts[i], north_pts[j], r_inner)
                for j in zone)
        if s < best_sum:
            best_sum = s
            best = i
    inject_points[best] = list(zone)

# build trees
power_edges = []  # (inj, a, b)

for inj, leds in inject_points.items():
    unused = set(leds)
    connected = {inj}
    unused.remove(inj)

    while unused:
        best_edge = None
        best_d = 1e9

        for a in connected:
            for b in unused:
                d = surface_dist(north_pts[a], north_pts[b], r_inner)
                if d < best_d:
                    best_d = d
                    best_edge = (a, b)

        a, b = best_edge
        power_edges.append((inj, a, b))
        connected.add(b)
        unused.remove(b)

# =====================================================
# Plot (overlay)
# =====================================================
fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111, projection="3d")

# --- reference sphere ---
u = np.linspace(0, 2 * np.pi, 80)
v = np.linspace(0, np.pi, 40)
xs = r_inner * np.outer(np.cos(u), np.sin(v))
ys = r_inner * np.outer(np.sin(u), np.sin(v))
zs = r_inner * np.outer(np.ones_like(u), np.cos(v))
ax.plot_surface(xs, ys, zs, color="lightgray", alpha=0.05, linewidth=0)

# --- other hemisphere (context only) ---
south = np.array([points[i] for i in range(200, 400)])
ax.scatter(south[:, 0], south[:, 1], south[:, 2],
           color="gray", s=4, alpha=0.04)

# --- POWER wiring (thicker, colored, semi-transparent) ---
palette = ["red", "green", "blue", "purple", "orange"]
inj_colors = {}

for (inj, _), color in zip(inject_points.items(), palette):
    inj_colors[inj] = color

for inj, a, b in power_edges:
    arc = arc_points(north_pts[a], north_pts[b], r_inner)
    ax.plot(
        arc[:, 0], arc[:, 1], arc[:, 2],
        color=inj_colors[inj],
        linewidth=3.0,
        alpha=0.55
    )

# --- LEDs ---
hp = np.array([north_pts[i] for i in north_ids])
ax.scatter(hp[:, 0], hp[:, 1], hp[:, 2],
           color="black", s=6, alpha=0.25)

# --- DATA wiring (thin & transparent) ---
for i in range(len(data_path) - 1):
    p = points[data_path[i]]
    q = points[data_path[i+1]]
    ax.plot(
        [p[0], q[0]],
        [p[1], q[1]],
        [p[2], q[2]],
        color=plt.cm.coolwarm(data_norm[i]),
        linewidth=1.2,
        alpha=0.6
    )

# --- injectiepunten ---
for inj, color in inj_colors.items():
    p = north_pts[inj]
    ax.scatter(*p, c=color, s=100)
    ax.text(*(p * 1.05), f"INJ {inj}", color=color, weight="bold")

# --- axes ---
lim = r_inner * 1.1
ax.set_xlim(-lim, lim)
ax.set_ylim(-lim, lim)
ax.set_zlim(-lim, lim)
ax.set_box_aspect([1, 1, 1])
ax.view_init(elev=20, azim=35)

ax.set_title(
    "Globe wiring overview (north hemisphere)\n"
    "Data = thin & transparent, Power = thick & colored"
)

plt.tight_layout()
plt.show()
