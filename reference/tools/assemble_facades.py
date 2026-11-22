"""Assemble les rendus de façades (_f_XXX_K.png) : une ligne par bâtiment (façade, droite, arrière, gauche), 8 par planche."""
import json, os, sys
from PIL import Image, ImageDraw
d = sys.argv[1]
idx = json.load(open(os.path.join(d, "facades_index.json"), encoding="utf8"))
W, H, PER = 560, 400, 8
for p in range(0, len(idx), PER):
    rows = idx[p:p + PER]
    sheet = Image.new("RGB", (4 * W, len(rows) * (H + 18)), (30, 30, 30))
    dr = ImageDraw.Draw(sheet)
    for j, (nm, x, y) in enumerate(rows):
        for k in range(4):
            f = os.path.join(d, "_f_%03d_%d.png" % (p + j, k))
            if os.path.exists(f):
                sheet.paste(Image.open(f).convert("RGB"), (k * W, j * (H + 18) + 18))
        dr.text((6, j * (H + 18) + 3), "%d %s (%d, %d)   facade | droite | arriere | gauche" % (p + j, nm, x, y), fill=(255, 255, 0))
    sheet.save(os.path.join(d, "facades_%02d.jpg" % (p // PER)), quality=85)
for f in os.listdir(d):
    if f.startswith("_f_"):
        os.remove(os.path.join(d, f))
print("planches :", (len(idx) + PER - 1) // PER)
