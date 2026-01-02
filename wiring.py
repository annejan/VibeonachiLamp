import math
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# Parameters
# =====================================================
diameter = 180
thickness = 8
hole_count = 400

wiring_mode = "fibonacci"   # "fibonacci" or "nearest"
hemisphere = "north"        # "north" or "south"

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
# Select hemisphere
# =====================================================
if hemisphere == "north":
    hemi_indices = [i for i, p in enumerate(points) if p[2] >= 0]
else:
    hemi_indices = [i for i, p in enumerate(points) if p[2] <= 0]

hemi_points = {i: points[i] for i in hemi_indices}

# =====================================================
# Distance helper
# =====================================================
def dist(p, q):
    return np.linalg.norm(p - q)

# =====================================================
# Build wiring path (within hemisphere)
# =====================================================
if wiring_mode == "fibonacci":
    path = [i for i in range(hole_count) if i in hemi_indices]

elif wiring_mode == "nearest":
    unused = set(hemi_indices)
    start = hemi_indices[0]
    path = [start]
    unused.remove(start)

    while unused:
        last = path[-1]
        next_idx = min(unused, key=lambda i: dist(points[last], points[i]))
        path.append(next_idx)
        unused.remove(next_idx)

else:
    raise ValueError("Unknown wiring_mode")

# =====================================================
# Segment lengths
# =====================================================
segments = np.array([
    dist(points[path[i]], points[path[i+1]])
    for i in range(len(path) - 1)
])

# =====================================================
# Visualization
# =====================================================
fig = plt.figure(figsize=(9, 9))
ax = fig.add_subplot(111, projection="3d")

# Color mapping
norm = (segments - segments.min()) / (segments.max() - segments.min() + 1e-9)
cmap = plt.cm.coolwarm if wiring_mode == "fibonacci" else plt.cm.viridis

# Draw wiring
for i in range(len(path) - 1):
    p = points[path[i]]
    q = points[path[i + 1]]
    ax.plot(
        [p[0], q[0]],
        [p[1], q[1]],
        [p[2], q[2]],
        color=cmap(norm[i]),
        linewidth=2
    )

# Hemisphere LEDs
hp = np.array(list(hemi_points.values()))
ax.scatter(hp[:, 0], hp[:, 1], hp[:, 2],
           color="black", s=8, alpha=0.4)

# Other hemisphere (context only)
other = np.array([
    p for i, p in enumerate(points)
    if i not in hemi_indices
])
ax.scatter(other[:, 0], other[:, 1], other[:, 2],
           color="gray", s=4, alpha=0.05)

# =====================================================
# Transparent reference sphere
# =====================================================
u = np.linspace(0, 2 * np.pi, 80)
v = np.linspace(0, np.pi, 40)

xs = r_inner * np.outer(np.cos(u), np.sin(v))
ys = r_inner * np.outer(np.sin(u), np.sin(v))
zs = r_inner * np.outer(np.ones_like(u), np.cos(v))

ax.plot_surface(xs, ys, zs,
                color="lightgray",
                alpha=0.06,
                linewidth=0)

# =====================================================
# Axes & layout
# =====================================================
lim = r_inner * 1.1
ax.set_xlim(-lim, lim)
ax.set_ylim(-lim, lim)
ax.set_zlim(-lim, lim)
ax.set_box_aspect([1, 1, 1])

ax.set_title(
    f"{hemisphere.capitalize()} hemisphere – {wiring_mode} data wiring\n"
    f"Blue = short, Red = long segments"
)
ax.set_xlabel("X (mm)")
ax.set_ylabel("Y (mm)")
ax.set_zlabel("Z (mm)")

# Colorbar
sm = plt.cm.ScalarMappable(cmap=cmap)
sm.set_array(segments)
fig.colorbar(sm, ax=ax, label="Segment length (mm)")

plt.tight_layout()
plt.show()

# =====================================================
# Stats
# =====================================================
print("=== Wiring statistics ===")
print("Mode:", wiring_mode)
print("Hemisphere:", hemisphere)
print("LED count:", len(path))
print("Min segment:", segments.min(), "mm")
print("Max segment:", segments.max(), "mm")
print("Avg segment:", segments.mean(), "mm")
print("Total wire length:", segments.sum(), "mm")
