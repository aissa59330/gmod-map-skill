"""Assemble les vues trois-quarts-face de la planche d'orientation (shots/interieurs/_o_XX.png) en une planche."""
import os, sys
from PIL import Image, ImageDraw
d = sys.argv[1]
idx = dict(l.split(" ", 1) for l in open(os.path.join(d, "orientation_index.txt"), encoding="utf8").read().split("\n\n")[0].splitlines())
fs = sorted(f for f in os.listdir(d) if f.startswith("_o_"))
C = 6
W, H = 420, 360
sheet = Image.new("RGB", (C * W, ((len(fs) + C - 1) // C) * H), (40, 40, 40))
for k, f in enumerate(fs):
    i = f[3:5].lstrip("0") or "0"
    im = Image.open(os.path.join(d, f)).convert("RGB")
    x, y = (k % C) * W, (k // C) * H
    sheet.paste(im, (x, y))
    ImageDraw.Draw(sheet).text((x + 6, y + 342), "%s %s" % (i, idx[i].split("/")[-1][:-4]), fill=(255, 255, 0))
sheet.save(os.path.join(d, "planche_orientation.png"))
for f in fs:
    os.remove(os.path.join(d, f))
print("ok", len(fs))
