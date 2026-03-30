"""Generate the default background image for Flowcast.

Run once during build or setup:
    python scripts/generate_default_bg.py
"""
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Run: pip install Pillow")
    raise

W, H = 1920, 1080
OUT = Path(__file__).parent.parent / "app" / "static" / "img" / "default_bg.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

img = Image.new("RGB", (W, H), color=(15, 15, 30))
draw = ImageDraw.Draw(img)

# Gradient-like effect with horizontal bars
for y in range(H):
    t = y / H
    r = int(15 + t * 10)
    g = int(15 + t * 5)
    b = int(30 + t * 40)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Subtle grid lines
for x in range(0, W, 120):
    draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 10), width=1)
for y in range(0, H, 120):
    draw.line([(0, y), (W, y)], fill=(255, 255, 255, 10), width=1)

# "FLOWCAST" watermark text
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 180)
except Exception:
    font = ImageFont.load_default()

draw.text((W // 2, H // 2 - 60), "FLOWCAST", font=font, fill=(40, 40, 70), anchor="mm")

img.save(OUT, "PNG")
print(f"Default background saved to {OUT}")
