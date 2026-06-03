"""Generate the Skill Issue favicon from the product's score-ring motif.

Final mark (candidate C): score-ring gauge (#27272a track + #60a5fa arc with a
rounded cap, 78% sweep from top) wrapping a bold Inter "S" on the app's #09090b
tile. Rendered supersampled (4x) then downscaled with LANCZOS per icon size for
crisp edges down to 16px.

Outputs:
  src/app/favicon.ico      multi-size 16/32/48/64/256
  src/app/apple-icon.png   180x180 square tile for iOS
  .next/shots/fav-final-*  preview PNGs (legibility check)
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "src", "app")
SHOTS = os.path.join(ROOT, ".next", "shots")
FONT_BOLD = os.path.join(ROOT, "public", "fonts", "Inter-Bold.ttf")
os.makedirs(SHOTS, exist_ok=True)

S = 1024  # supersample canvas
BG = (9, 9, 11, 255)          # #09090b  app background
TRACK = (39, 39, 42, 255)     # #27272a  app border / faint ring
ACCENT = (96, 165, 250, 255)  # #60a5fa  app accent
LIGHT = (250, 250, 250, 255)  # #fafafa  foreground


def draw_arc(d, cx, cy, radius, width, color, start_deg, sweep_deg, rounded=True):
    """0deg = top (12 o'clock); positive sweep = clockwise."""
    pil_start = start_deg - 90
    pil_end = pil_start + sweep_deg
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    d.arc(bbox, pil_start, pil_end, fill=color, width=width)
    if rounded:
        cap = width / 2
        for ang in (pil_start, pil_end):
            a = math.radians(ang)
            ex = cx + radius * math.cos(a)
            ey = cy + radius * math.sin(a)
            d.ellipse([ex - cap, ey - cap, ex + cap, ey + cap], fill=color)


def render(radius_frac=0.22, s_scale=1.0, stroke_scale=1.0):
    """Render the mark at the supersample size. radius_frac=0 -> square tile."""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(S * radius_frac)
    if r > 0:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=BG)
    else:
        d.rectangle([0, 0, S - 1, S - 1], fill=BG)

    cx = cy = S / 2
    radius = S * 0.345
    width = int(S * 0.105 * stroke_scale)
    draw_arc(d, cx, cy, radius, width, TRACK, 0, 360, rounded=False)
    draw_arc(d, cx, cy, radius, width, ACCENT, 0, 281, rounded=True)

    font = ImageFont.truetype(FONT_BOLD, int(S * 0.40 * s_scale))
    bb = d.textbbox((0, 0), "S", font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1]), "S", font=font, fill=LIGHT)
    return img


# Tab-favicon master (rounded tile). At very small sizes nudge the S a touch
# larger and the stroke a touch thicker so both survive the downscale.
master = render(radius_frac=0.22)
master_small = render(radius_frac=0.22, s_scale=1.06, stroke_scale=1.06)

ico_sizes = [16, 32, 48, 64, 256]
frames = []
for sz in ico_sizes:
    src = master_small if sz <= 32 else master
    frames.append(src.resize((sz, sz), Image.LANCZOS))

ico_path = os.path.join(APP, "favicon.ico")
frames[-1].save(ico_path, format="ICO", sizes=[(s, s) for s in ico_sizes],
                append_images=frames[:-1])
print("wrote", ico_path)

# Apple touch icon: square (iOS applies its own mask), opaque, 180px.
apple = render(radius_frac=0.0).resize((180, 180), Image.LANCZOS)
apple_path = os.path.join(APP, "apple-icon.png")
apple.convert("RGB").save(apple_path)
print("wrote", apple_path)

# Legibility previews.
for sz in (16, 32, 48):
    (master_small if sz <= 32 else master).resize((sz, sz), Image.LANCZOS).save(
        os.path.join(SHOTS, f"fav-final-{sz}.png"))
# Side-by-side strip at native sizes on a neutral chip.
strip = Image.new("RGBA", (16 + 32 + 48 + 64 + 80, 80), (24, 24, 27, 255))
x = 16
for sz in (16, 32, 48):
    im = Image.open(os.path.join(SHOTS, f"fav-final-{sz}.png"))
    strip.alpha_composite(im, (x, (80 - sz) // 2))
    x += sz + 16
strip.alpha_composite(master.resize((64, 64), Image.LANCZOS), (x, 8))
strip.save(os.path.join(SHOTS, "fav-final-strip.png"))
print("preview:", os.path.join(SHOTS, "fav-final-strip.png"))
