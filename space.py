import math
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# Parameters
# =====================================================
diameter = 350
thickness = 8
led_count = 1337

hemisphere = "north"       # LEDs 0–199
SEG_SAMPLES = 40           # sampling along wires
Z_BINS = 120               # resolution of profile
Z_SLICE_THICKNESS = 1.0    # mm
SAFETY_MARGIN = 2.5        # mm

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
for i in range(led_count):
    z = 1 - 2 * (i + 0.5) / led_count
    theta = math.acos(z)
    phi = 2 * math.pi * i / golden

    x = r_inner * math.sin(theta) * math.cos(phi)
    y = r_inner * math.sin(theta) * math.sin(phi)
    zc = r_inner * math.cos(theta)

    points.append(np.array([x, y, zc]))

points = np.array(points)

# =====================================================
# Data path
# =====================================================
if hemisphere == "north":
    data_path = list(range(0, led_count // 2))
else:
    data_path = list(range(led_count // 2, led_count))

# =====================================================
# Sample all data wires
# =====================================================
samples = []

for i in range(len(data_path) - 1):
    a = points[data_path[i]]
    b = points[data_path[i + 1]]
    for t in np.linspace(0, 1, SEG_SAMPLES):
        samples.append(a * (1 - t) + b * t)

samples = np.array(samples)

# =====================================================
# Radial profile ρ(z)
# =====================================================
z_min = samples[:, 2].min()
z_max = samples[:, 2].max()

z_centers = np.linspace(z_min, z_max, Z_BINS)
rho_free = []

for zc in z_centers:
    slab = samples[np.abs(samples[:, 2] - zc) <= Z_SLICE_THICKNESS]
    if len(slab) == 0:
        rho_free.append(np.nan)
    else:
        rho_free.append(np.min(np.hypot(slab[:, 0], slab[:, 1])))

rho_free = np.array(rho_free)

# apply safety margin
rho_safe = rho_free - SAFETY_MARGIN

# =====================================================
# Report key values
# =====================================================
min_idx = np.nanargmin(rho_free)

print("\n=== Radial free-space profile ===")
print(f"Minimum free diameter: {2 * rho_free[min_idx]:.1f} mm")
print(f"At z = {z_centers[min_idx]:.1f} mm")
print(f"Safe minimum diameter: {2 * rho_safe[min_idx]:.1f} mm")

# =====================================================
# Visualization
# =====================================================
fig = plt.figure(figsize=(14, 6))

# --- left: 3D context ---
ax3d = fig.add_subplot(121, projection="3d")

# inner shell
u = np.linspace(0, 2 * math.pi, 60)
v = np.linspace(0, math.pi, 30)
xs = r_inner * np.outer(np.cos(u), np.sin(v))
ys = r_inner * np.outer(np.sin(u), np.sin(v))
zs = r_inner * np.outer(np.ones_like(u), np.cos(v))
ax3d.plot_surface(xs, ys, zs, color="lightgray", alpha=0.04, linewidth=0)

# data wiring
for i in range(len(data_path) - 1):
    p = points[data_path[i]]
    q = points[data_path[i + 1]]
    ax3d.plot(
        [p[0], q[0]],
        [p[1], q[1]],
        [p[2], q[2]],
        color="steelblue",
        alpha=0.6,
        linewidth=1.1
    )

ax3d.set_box_aspect([1, 1, 1])
ax3d.set_xlim(-r_inner, r_inner)
ax3d.set_ylim(-r_inner, r_inner)
ax3d.set_zlim(-r_inner, r_inner)
ax3d.view_init(elev=20, azim=35)
ax3d.set_title("Data wiring context")

# --- right: radial profile ---
ax = fig.add_subplot(122)

ax.plot(z_centers, 2 * rho_free, label="Free diameter", linewidth=2)
ax.plot(z_centers, 2 * rho_safe, "--", label="Safe diameter", linewidth=2)

ax.axvline(z_centers[min_idx], color="red", linestyle=":")
ax.axhline(2 * rho_free[min_idx], color="red", linestyle=":")

ax.set_xlabel("Z position (mm)")
ax.set_ylabel("Diameter (mm)")
ax.set_title("Free diameter vs Z (pole → equator)")
ax.grid(True)
ax.legend()

plt.tight_layout()
plt.show()
