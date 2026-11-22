"""Bannière RP « Opération Vexis » (1920x1080) à partir d'une capture en jeu.
Usage : python tools/make_banner_event.py <image_source> <sortie.png>"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
W, H = 1920, 1080
ORANGE = (255, 154, 46)
WHITE = (246, 240, 230)
GREY = (205, 196, 184)

def font(size, bold=True):
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf", size)
        f.set_variation_by_name("Bold" if bold else "SemiLight")
        return f
    except Exception:
        return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", size)

src = Image.open(SRC).convert("RGB")
sw, sh = src.size
# partie de la capture SANS l'ancien texte (tour centrale + tour de droite), agrandie pour remplir la hauteur
k = sw / 1920
clean = src.crop((int(560 * k), int(200 * k), sw, int(870 * k)))
sc = H / clean.size[1]
clean = clean.resize((int(clean.size[0] * sc), H), Image.LANCZOS)
img = Image.new("RGB", (W, H), (16, 11, 9))
X0 = 560                                   # la tour tombe vers x = 1150
img.paste(clean, (X0, 0))
# panneau gauche : opaque puis dégradé vers l'image ; bande basse
from PIL import ImageChops
m1 = Image.new("L", (W, H), 0); d1 = ImageDraw.Draw(m1)
for x in range(W):
    d1.line([(x, 0), (x, H)], fill=255 if x < X0 + 40 else max(0, int(255 - (x - X0 - 40) * 255 / 360)))
m2 = Image.new("L", (W, H), 0); d2 = ImageDraw.Draw(m2)
for y in range(H):
    d2.line([(0, y), (W, y)], fill=0 if y < 840 else min(235, int(235 * (y - 840) / 60)))
mask = ImageChops.lighter(m1, m2)
img = Image.composite(Image.new("RGB", (W, H), (16, 11, 9)), img, mask)
draw = ImageDraw.Draw(img)

def text(xy, s, f, fill, spacing=0, shadow=True):
    x, y = xy
    for ch in s:
        if shadow:
            draw.text((x + 3, y + 3), ch, font=f, fill=(0, 0, 0))
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + spacing
    return x

# en-tête
draw.rectangle((90, 88, 96, 196), fill=ORANGE)
text((122, 92), "FLOTTE COSMOS", font(34), ORANGE, spacing=7)
text((122, 146), "ORDRE DE MISSION  •  ÉVÉNEMENT", font(30, False), GREY, spacing=5)

# titre
text((84, 250), "OPÉRATION", font(78), ORANGE, spacing=10)
text((78, 320), "VEXIS", font(190), WHITE, spacing=6)

# date
draw.rectangle((90, 548, 640, 616), fill=ORANGE)
text((112, 558), "SAMEDI 21/11  •  18H00", font(44), (20, 12, 6), spacing=3, shadow=False)

# objectifs
text((92, 660), "OBJECTIFS", font(32), ORANGE, spacing=6)
objs = ["Détruire la production de la CSI", "Détruire les dépôts d'armes", "Prendre la citadelle"]
for i, o in enumerate(objs):
    y = 712 + i * 46
    draw.rectangle((96, y + 14, 108, y + 26), fill=ORANGE)
    text((126, y), o, font(34, False), WHITE, spacing=1)

# bande basse
text((92, 960), "PLANÈTE-ARSENAL DE LA CSI  •  COMBAT DE MASSE", font(30), GREY, spacing=4)
bx0, by0, bx1, by1 = 1470, 940, 1830, 1010
draw.rectangle((bx0, by0, bx1, by1), fill=ORANGE)
f = font(40)
s = "À VOS POSTES"
tw = draw.textlength(s, font=f) + 3 * (len(s) - 1)
text((bx0 + (bx1 - bx0 - tw) / 2, by0 + 12), s, f, (20, 12, 6), spacing=3, shadow=False)

img.save(OUT)
print("ok", OUT)
