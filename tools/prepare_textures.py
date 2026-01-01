from PIL import Image, ImageFilter
import numpy as np
import os

# ========== CONFIG ==========
INPUT_DAY   = "world_day.png"
INPUT_NIGHT = "world_night.png"

DAY_SIZE   = (128, 64)
NIGHT_SIZE = (64, 32)

OUT_DIR = "generated"
# ============================

os.makedirs(OUT_DIR, exist_ok=True)

def prepare(name, path, size):
    img = Image.open(path).convert("RGB")

    # high quality downscale
    img = img.resize(size, Image.LANCZOS)

    # optional: very light blur to kill sparkle
    img = img.filter(ImageFilter.GaussianBlur(radius=0.3))

    arr = np.array(img, dtype=np.uint8)

    print(
        f"{name}: {size[0]}×{size[1]} "
        f"({arr.size/1024:.1f} KB)"
    )

    return arr

day   = prepare("DAY",   INPUT_DAY,   DAY_SIZE)
night = prepare("NIGHT", INPUT_NIGHT, NIGHT_SIZE)

# ---------- write C headers ----------
def write_header(name, arr):
    h, w, _ = arr.shape
    fname = f"{OUT_DIR}/{name.lower()}_tex.h"

    with open(fname, "w") as f:
        f.write(f"#pragma once\n")
        f.write(f"#define {name}_W {w}\n")
        f.write(f"#define {name}_H {h}\n")
        f.write(f"static const uint8_t {name.lower()}_tex[] = {{\n")

        flat = arr.flatten()
        for i, v in enumerate(flat):
            f.write(f"{v},")
            if i % 24 == 23:
                f.write("\n")

        f.write("};\n")

    print(f"→ wrote {fname}")

write_header("DAY", day)
write_header("NIGHT", night)

