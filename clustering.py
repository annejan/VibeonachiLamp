import math

# Parameters
diameter = 200
thickness = 2.5
hole_count = 300
cluster_size = 40   # LEDs per power injectie

R = diameter / 2
r_inner = R - thickness
golden = (1 + math.sqrt(5)) / 2

# Generate Fibonacci points
points = []
for i in range(hole_count):
    z = 1 - 2 * (i + 0.5) / hole_count
    theta = math.acos(z)
    phi = 2 * math.pi * i / golden
    x = r_inner * math.sin(theta) * math.cos(phi)
    y = r_inner * math.sin(theta) * math.sin(phi)
    zc = r_inner * math.cos(theta)
    points.append((x, y, zc))

# Split hemispheres
top_leds = [(i, p) for i, p in enumerate(points) if p[2] >= 0]
bottom_leds = [(i, p) for i, p in enumerate(points) if p[2] < 0]

def power_clusters(leds, cluster_size):
    clusters = []
    for i in range(0, len(leds), cluster_size):
        cluster = leds[i:i+cluster_size]
        clusters.append(cluster)
    return clusters

top_clusters = power_clusters(top_leds, cluster_size)
bottom_clusters = power_clusters(bottom_leds, cluster_size)

print("TOP hemisphere power injects:")
for idx, c in enumerate(top_clusters):
    indices = [i for i,_ in c]
    print(f"  Cluster {idx}: LEDs {indices[0]} – {indices[-1]}")

print("\nBOTTOM hemisphere power injects:")
for idx, c in enumerate(bottom_clusters):
    indices = [i for i,_ in c]
    print(f"  Cluster {idx}: LEDs {indices[0]} – {indices[-1]}")

