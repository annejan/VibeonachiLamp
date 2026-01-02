import math
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# Parameters
# =====================================================
N = 400
r_inner = 81.0
golden = (1 + math.sqrt(5)) / 2

# north hemisphere
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
# Generate LED points
# =====================================================
points = []

for i in range(N):
    z = 1 - 2 * (i + 0.5) / N
    theta = math.acos(z)
    phi = 2 * math.pi * i / golden

    x = r_inner * math.sin(theta) * math.cos(phi)
    y = r_inner * math.sin(theta) * math.sin(phi)
    zc = r_inner * math.cos(theta)

    points.append(np.array([x, y, zc]))

points = np.array(points)
north_pts = {i: unit(points[i]) * r_inner for i in range(0, 200)}

# =====================================================
# Phase 1: choose injectiepunt per zone (medoid)
# =====================================================
inject_points = {}

for zone in zones:
    best_i = None
    best_sum = 1e18

    for i in zone:
        s = sum(surface_dist(north_pts[i], north_pts[j], r_inner)
                for j in zone)
        if s < best_sum:
            best_sum = s
            best_i = i

    inject_points[best_i] = list(zone)

# =====================================================
# Phase 2: local nearest-neighbour tree per zone
# =====================================================
trees = {}
lengths = {}

for inj, leds in inject_points.items():
    unused = set(leds)
    connected = {inj}
    unused.remove(inj)

    edges = []
    total = 0.0

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
        edges.append((a, b, best_d))
        total += best_d
        connected.add(b)
        unused.remove(b)

    trees[inj] = edges
    lengths[inj] = total

# =====================================================
# Plot
# =====================================================
fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111, projection="3d")

pts = np.array([north_pts[i] for i in range(0, 200)])
ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2],
           color="black", s=6, alpha=0.4)

colors = ["red", "green", "blue", "purple", "orange"]

for (inj, edges), color in zip(trees.items(), colors):
    for a, b, _ in edges:
        arc = arc_points(north_pts[a], north_pts[b], r_inner)
        ax.plot(arc[:, 0], arc[:, 1], arc[:, 2],
                color=color, linewidth=1.6)

    p = north_pts[inj]
    ax.scatter(*p, c=color, s=90)
    ax.text(*(p * 1.05), f"INJ {inj}", color=color, weight="bold")

# equator
xx, yy = np.meshgrid(np.linspace(-90, 90, 20), np.linspace(-90, 90, 20))
ax.plot_surface(xx, yy, np.zeros_like(xx), alpha=0.05, color="gray")

ax.set_title(
    "North hemisphere – power-routering\n"
    "injectiepunten automatisch gekozen per 40-LED zone"
)
ax.set_box_aspect([1, 1, 1])
ax.view_init(elev=20, azim=35)

# --- zuidelijke hemisfeer als context ---
south_pts = [unit(points[i]) * r_inner for i in range(200, 400)]
south_pts = np.array(south_pts)

ax.scatter(
    south_pts[:, 0],
    south_pts[:, 1],
    south_pts[:, 2],
    color="gray",
    s=4,
    alpha=0.15
)

plt.tight_layout()
plt.show()

# =====================================================
# Console report
# =====================================================
print("\n=== Power-routering per zone (north hemisphere) ===")
grand = 0.0

for inj, leds in inject_points.items():
    n = len(leds)
    l = lengths[inj]
    grand += l
    print(f"Injectie LED {inj:3d}: {n:2d} LEDs, {l:6.1f} mm")

print(f"\nTotale draadlengte (noord): {grand:6.1f} mm")
print(f"Aanbevolen kniplengte (+20%): {grand * 1.2:6.1f} mm")
