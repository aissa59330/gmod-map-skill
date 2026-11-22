"""Vues en plan de contrôle des intérieurs, par type de pièce (lit le relevé pieces.json écrit par la génération).
Vert = passages de portes, jaune = zones sans meuble, gris = volée d'escalier / trémie, bleu = fenêtres,
rouge = emprise réelle des meubles (trait = avant du modèle, +X), violet = objet posé sur un meuble. Façade en bas."""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
rooms = json.load(open(src, encoding="utf8"))
by = {}
for r in rooms:
    by.setdefault(r["role"], []).append(r)
K, PAD = 1.3, 40
for role, rs in sorted(by.items()):
    pick = [r for r in rs if not r["loot"]][:2] + [r for r in rs if r["loot"]][:1]
    tiles = []
    for r in pick:
        x0, y0, x1, y1 = r["rect"]
        Wd, Hd = int((x1 - x0) * K) + 2 * PAD, int((y1 - y0) * K) + 2 * PAD + 20
        im = Image.new("RGB", (Wd, Hd), "white")
        d = ImageDraw.Draw(im, "RGBA")
        P = lambda x, y: (PAD + (x - x0) * K, Hd - PAD - (y - y0) * K)   # y vers le haut, façade en bas
        box = lambda a: [min(P(a[0], a[1])[0], P(a[2], a[3])[0]), min(P(a[0], a[1])[1], P(a[2], a[3])[1]),
                         max(P(a[0], a[1])[0], P(a[2], a[3])[0]), max(P(a[0], a[1])[1], P(a[2], a[3])[1])]
        for (lst, col) in ((r["win"], (0, 170, 255, 60)), (r["doors"], (0, 160, 0, 90)), (r["keep"], (230, 190, 0, 90)),
                           (r["solid"], (110, 110, 110, 150))):
            for a in lst:
                d.rectangle(box(a), fill=col)
        d.rectangle(box(r["rect"]), outline="black", width=3)
        for (name, a, ang, solid) in r["meubles"]:
            col = (180, 30, 30) if solid else (130, 40, 170)
            d.rectangle(box(a), outline=col, width=2 if solid else 1)
            cx, cy = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
            L = min(a[2] - a[0], a[3] - a[1]) * 0.5
            d.line([P(cx, cy), P(cx + L * math.cos(math.radians(ang)), cy + L * math.sin(math.radians(ang)))], fill=col, width=3)
            d.text(P(a[0], a[3]), name.replace("rep_", "").replace("con_", "")[:18], fill=(0, 0, 0))
        d.text((6, 4), "%s%s  bat %s" % (role, " PILLEE" if r["loot"] else "", r["key"][:2]), fill=(0, 0, 0))
        tiles.append(im)
    W_ = sum(t.width for t in tiles) + 10 * (len(tiles) - 1)
    sheet = Image.new("RGB", (W_, max(t.height for t in tiles)), (220, 220, 220))
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width + 10
    sheet.save(os.path.join(out, "plan_%s.png" % role))
print("plans :", ", ".join("%s (%d)" % (k, len(v)) for k, v in sorted(by.items())), "->", out)
