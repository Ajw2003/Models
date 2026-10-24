"""Builds docs/art/reviews/goose-v2-review.png: the concept, the four goose_v2 views, and each join
close-up from version 1 (goose-joins/) above the same shot of version 2 (goose-v2-joins/).

  python3.11 docs/art/reviews/goose-v2-joins/review_sheet.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEWS = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(REVIEWS)))
WIDTH, PAD, TILE = 2400, 24, 455
JOINS = ["neck_base_front", "neck_base_side", "side_neck_join", "wing_root", "leg_hip"]
VIEWS = ["view_front", "view_side", "view_three_quarter", "view_back"]


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def fit(path, width):
    img = Image.open(path).convert("RGB")
    return img.resize((width, round(img.height * width / img.width)))


concept = fit(os.path.join(ROOT, "art", "goose", "concept.png"), WIDTH - 2 * PAD)
view_w = (WIDTH - 5 * PAD) // 4
views = [fit(os.path.join(HERE, v + ".png"), view_w) for v in VIEWS]
rows = [("Version 1", "goose-joins"), ("Version 2", "goose-v2-joins")]
joins = [[fit(os.path.join(REVIEWS, folder, j + ".png"), TILE) for j in JOINS] for _, folder in rows]

title_h, label_h = 70, 44
height = (title_h + concept.height + label_h + views[0].height + PAD
          + 2 * (label_h + TILE) + 2 * PAD)
sheet = Image.new("RGB", (WIDTH, height), "#EDE6D6")
draw = ImageDraw.Draw(sheet)
draw.text((PAD, 18), "The goose, version 2: one fused skin and a neck root that forks into three (#18)",
          fill="#1A1714", font=font(34))
y = title_h
sheet.paste(concept, (PAD, y))
y += concept.height
draw.text((PAD, y + 8), "goose_v2: front, side, three-quarter, back", fill="#1A1714", font=font(26))
y += label_h
for k, img in enumerate(views):
    sheet.paste(img, (PAD + k * (view_w + PAD), y))
y += views[0].height + PAD
for (label, _), tiles in zip(rows, joins):
    draw.text((PAD, y + 8), f"{label} joins: neck base front, neck base side, side neck, wing root, hip",
              fill="#1A1714", font=font(26))
    y += label_h
    for k, img in enumerate(tiles):
        sheet.paste(img, (PAD + k * (TILE + PAD // 2 + 4), y))
    y += TILE + PAD
out = os.path.join(REVIEWS, "goose-v2-review.png")
sheet.save(out)
print(f"review_sheet: wrote {out} ({sheet.width} x {sheet.height})")
