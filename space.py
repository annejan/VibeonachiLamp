import math
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# Parameters
# =====================================================
diameter = 180          # mm
thickness = 8           # mm
hole_count = 400

use_hemisphere = True   # True = LEDs 0–199
hemisphere = "north"    # "north" or "south"

# =====================================================
# Derived
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
# Select data path
# =====================================================
if use_hemisphere:
    if hemisphere == "north":
        data_path = list(range(0, hole_count // 2))
    else:
        data_path = list(range(hole_count // 2, hole_count))
else:
    data_path = list(range(hole_count))

# =====================================================
# Geometry helper
# =====================================================
def segment_distance_to_origin(a, b):
    """
    Shortest distance from line segment a-b to origin (0,0,0)
    """
    ab = b - a
    denom = np.dot(ab, ab)
    if denom < 1e-12:
        return np.linalg.norm(a)

    t = -np.dot(a, ab) / denom
    t = np.clip(t, 0.0, 1.0)
    closest = a + t * ab
    return np.linalg.norm(closest)

# =====================================================
# Compute hole radius
# =====================================================
min_dist = float("inf")
worst_segment = None

for i in range(len(data_path) - 1):
    a = points[data_path[i]]
    b = points[data_path[i + 1]]
    d = segment_distance_to_origin(a, b)

    if d < min_dist:
        min_dist = d
        worst_segment = (data_path[i], data_path[i + 1])

# =====================================================
# Results
# =====================================================
print("\n=== Data wiring hole analysis ===")
print(f"Inner sphere radius: {r_inner:.1f} mm")
print(f"Data LEDs considered: {len(data_path)}")
print(f"Worst segment: LED {worst_segment[0]} → {worst_segment[1]}")
print(f"Free hole radius:   {min_dist:.1f} mm")
print(f"Free hole diameter: {2 * min_dist:.1f} mm")

# Conservative safety margin
margin = 5.0
safe_radius = max(0.0, min_dist - margin)

print(f"\nWith {margin:.1f} mm safety margin:")
print(f"Safe usable radius:   {safe_radius:.1f} mm")
print(f"Safe usable diameter: {2 * safe_radius:.1f} mm")

# =====================================================
# Optional visualization
# =====================================================
fig = plt.figure(figsize=(9, 9))
ax = fig.add_subplot(111, projection="3d")

# Reference sphere
u = np.linspace(0, 2 * math.pi, 60)
v = np.linspace(0, math.pi, 30)
xs = r_inner * np.outer(np.cos(u), np.sin(v))
ys = r_inner * np.outer(np.sin(u), np.sin(v))
zs = r_inner * np.outer(np.ones_like(u), np.cos(v))
ax.plot_surface(xs, ys, zs, color="lightgray", alpha=0.05, linewidth=0)

# Data wiring
for i in range(len(data_path) - 1):
    p = points[data_path[i]]
    q = points[data_path[i + 1]]
    ax.plot(
        [p[0], q[0]],
        [p[1], q[1]],
        [p[2], q[2]],
        color="steelblue",
        alpha=0.6,
        linewidth=1.2
    )

# LEDs
hp = np.array([points[i] for i in data_path])
ax.scatter(hp[:, 0], hp[:, 1], hp[:, 2],
           color="black", s=6, alpha=0.3)

# Hole sphere
u = np.linspace(0, 2 * math.pi, 40)
v = np.linspace(0, math.pi, 20)
xh = min_dist * np.outer(np.cos(u), np.sin(v))
yh = min_dist * np.outer(np.sin(u), np.sin(v))
zh = min_dist * np.outer(np.ones_like(u), np.cos(v))
ax.plot_surface(xh, yh, zh, color="green", alpha=0.15, linewidth=0)

# Axes
lim = r_inner * 1.1
ax.set_xlim(-lim, lim)
ax.set_ylim(-lim, lim)
ax.set_zlim(-lim, lim)
ax.set_box_aspect([1, 1, 1])
ax.view_init(elev=20, azim=35)

ax.set_title(
    "Data wiring hole analysis\n"
    f"Free diameter ≈ {2 * min_dist:.1f} mm"
)

plt.tight_layout()
plt.show()

