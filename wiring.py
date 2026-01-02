import math
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# =====================================================
# Parameters (match je SCAD)
# =====================================================
diameter = 180
thickness = 2.5
hole_count = 400

wiring_mode = "fibonacci"  
# "fibonacci" = i -> i+1
# "nearest"   = nearest-neighbor wiring

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

# =====================================================
# Distance helper
# =====================================================
def dist(p, q):
    return np.linalg.norm(p - q)

# =====================================================
# Build wiring path
# =====================================================
if wiring_mode == "fibonacci":
    path = list(range(len(points)))

elif wiring_mode == "nearest":
    unused = set(range(len(points)))
    path = [0]
    unused.remove(0)

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
fig = plt.figure(figsize=(9, 8))
ax = fig.add_subplot(111, projection="3d")

# Normalize for color mapping
norm = (segments - segments.min()) / (segments.max() - segments.min() + 1e-9)

cmap = plt.cm.coolwarm if wiring_mode == "fibonacci" else plt.cm.viridis

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

# LED points
xs, ys, zs = zip(*points)
ax.scatter(xs, ys, zs, color="black", s=6, alpha=0.3)

ax.set_title(
    f"{wiring_mode.capitalize()} wiring\n"
    f"Blue = short segments, Red/Yellow = long segments"
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
print("LED count:", hole_count)
print("Min segment:", segments.min(), "mm")
print("Max segment:", segments.max(), "mm")
print("Avg segment:", segments.mean(), "mm")
print("Total wire length:", segments.sum(), "mm")
