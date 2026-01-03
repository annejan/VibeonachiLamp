import math
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# Parameters
# =====================================================
diameter = 350
thickness = 8
hole_count = 1337

hemisphere = "north"
zones_count = 15

DATA_OFFSET = 0.6   # mm – lift data lines above surface

# =====================================================
# Derived values
# =====================================================
R = diameter / 2
r_inner = R - thickness
golden = (1 + math.sqrt(5)) / 2

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

# =====================================================
# Select hemisphere (correct)
# =====================================================
if hemisphere == "north":
    hemi_indices = [i for i, p in enumerate(points) if p[2] >= 0]
else:
    hemi_indices = [i for i, p in enumerate(points) if p[2] <= 0]

# Fibonacci data path within hemisphere
path = [i for i in range(hole_count) if i in hemi_indices]

# =====================================================
# Helpers
# =====================================================
def unit(v):
    return v / np.linalg.norm(v)

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
# Split data path into 15 zones
# =====================================================
def split_zones(seq, n):
    k, m = divmod(len(seq), n)
    return [
        seq[i*k + min(i,m):(i+1)*k + min(i+1,m)]
        for i in range(n)
    ]

zones = split_zones(path, zones_count)

# =====================================================
# Injectiepunten (medoids)
# =====================================================
inject_points = {}  # inj -> zone

for zone in zones:
    best = None
    best_sum = 1e18
    for i in zone:
        s = sum(surface_dist(points[i], points[j], r_inner) for j in zone)
        if s < best_sum:
            best_sum = s
            best = i
    inject_points[best] = zone

# =====================================================
# Power routing (MST per zone)
# =====================================================
power_edges = []

for inj, zone in inject_points.items():
    unused = set(zone)
    connected = {inj}
    unused.remove(inj)

    while unused:
        best_edge = None
        best_d = 1e18
        for a in connected:
            for b in unused:
                d = surface_dist(points[a], points[b], r_inner)
                if d < best_d:
                    best_d = d
                    best_edge = (a, b)
        a, b = best_edge
        power_edges.append((inj, a, b))
        connected.add(b)
        unused.remove(b)

# =====================================================
# Colors
# =====================================================
palette = [
    "red", "green", "blue", "purple", "orange",
    "cyan", "magenta", "yellow", "lime", "pink",
    "teal", "gold", "brown", "navy", "olive"
]

inj_colors = dict(zip(inject_points.keys(), palette))

# =====================================================
# Visualization
# =====================================================
fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111, projection="3d")


# --- Reference sphere ---
u = np.linspace(0, 2 * np.pi, 60)
v = np.linspace(0, np.pi, 30)
xs = r_inner * np.outer(np.cos(u), np.sin(v))
ys = r_inner * np.outer(np.sin(u), np.sin(v))
zs = r_inner * np.outer(np.ones_like(u), np.cos(v))
ax.plot_surface(xs, ys, zs,
                color="lightgray",
                alpha=0.04,
                linewidth=0)

# --- POWER wiring ---
for inj, a, b in power_edges:
    arc = arc_points(points[a], points[b], r_inner)
    ax.plot(
        arc[:,0], arc[:,1], arc[:,2],
        color=inj_colors[inj],
        linewidth=3.2,
        alpha=0.85
    )

# --- DATA wiring (offset & visible) ---
for i in range(len(path) - 1):
    a = unit(points[path[i]]) * (r_inner + DATA_OFFSET)
    b = unit(points[path[i+1]]) * (r_inner + DATA_OFFSET)
    ax.plot(
        [a[0], b[0]],
        [a[1], b[1]],
        [a[2], b[2]],
        color="steelblue",
        linewidth=0.8,
        alpha=0.7
    )

# --- LEDs ---
hp = np.array([points[i] for i in hemi_indices])
ax.scatter(hp[:,0], hp[:,1], hp[:,2],
           color="black", s=6, alpha=0.4)

# --- Injectiepunten ---
for inj, color in inj_colors.items():
    p = points[inj]
    ax.scatter(*p, c=color, s=120)
    ax.text(*(p * 1.05), f"INJ {inj}", color=color, weight="bold")


# --- Axes ---
lim = r_inner * 1.1
ax.set_xlim(-lim, lim)
ax.set_ylim(-lim, lim)
ax.set_zlim(-lim, lim)
ax.set_box_aspect([1,1,1])
ax.view_init(elev=20, azim=35)

ax.set_title("North hemisphere – Fibonacci data (visible) + power zones")

plt.tight_layout()
plt.show()
