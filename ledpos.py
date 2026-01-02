import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Parameters (match SCAD)
diameter = 200
thickness = 2.5
hole_count = 400

R = diameter / 2
r_inner = R - thickness
golden = (1 + math.sqrt(5)) / 2

# Generate Fibonacci points
points = []
indices = []

for i in range(hole_count):
    z = 1 - 2 * (i + 0.5) / hole_count
    theta = math.acos(z)
    phi = 2 * math.pi * i / golden

    x = r_inner * math.sin(theta) * math.cos(phi)
    y = r_inner * math.sin(theta) * math.sin(phi)
    zc = r_inner * math.cos(theta)

    points.append((x, y, zc))
    indices.append(i)

xs, ys, zs = zip(*points)

# Plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

scatter = ax.scatter(
    xs, ys, zs,
    c=indices,
    cmap='coolwarm'
)

# Label some points (avoid clutter)
step = 1;
for i in range(0, hole_count, step):
    ax.text(xs[i], ys[i], zs[i], str(i), fontsize=8)

ax.set_title("Fibonacci Sphere LED Order (Blue → Red)")
ax.set_xlabel("X (mm)")
ax.set_ylabel("Y (mm)")
ax.set_zlabel("Z (mm)")

fig.colorbar(scatter, ax=ax, label="LED index")
plt.show()

