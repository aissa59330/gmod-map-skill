"""Miniature Workshop (512x512 JPG) et bannière (1920x1080) à partir des captures en jeu (shots/iter5).
python tools/make_presentation.py"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "shots", "iter5")
OUT = os.path.join(ROOT, "publish")
ORANGE, WHITE, GREY, DARK = (255, 154, 46), (246, 240, 230), (210, 202, 190), (14, 12, 11)


def font(size, bold=True):
    f = ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf", size)
    f.set_variation_by_name("Bold" if bold else "SemiLight")
    return f


def text(d, xy, s, f, fill, spacing=0, shadow=True):
    x, y = xy
    for ch in s:
        if shadow:
            d.text((x + 3, y + 3), ch, font=f, fill=(0, 0, 0))
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + spacing
    return x


def width(d, s, f, spacing):
    return sum(d.textlength(ch, font=f) + spacing for ch in s) - spacing


def grade(im):
    im = ImageEnhance.Contrast(im).enhance(1.15)
    return ImageEnhance.Color(im).enhance(1.15)


def shade_bottom(im, start, alpha=235):
    w, h = im.size
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for y in range(start, h):
        d.line([(0, y), (w, y)], fill=int(alpha * (y - start) / (h - start)))
    return Image.composite(Image.new("RGB", (w, h), DARK), im, m)


# ---------- miniature 512x512 : la ville vue des toits ----------
src = grade(Image.open(os.path.join(SH, "ville_ciel.jpg")).convert("RGB"))
w, h = src.size
crop = src.crop((w // 2 - h // 2 + 120, 0, w // 2 + h // 2 + 120, h)).resize((512, 512), Image.LANCZOS)
crop = shade_bottom(crop, 250)
d = ImageDraw.Draw(crop)
d.rectangle((0, 0, 512, 6), fill=ORANGE)
f = font(64)
s = "TRIPLE FRONT"
text(d, ((512 - width(d, s, f, 3)) / 2, 378), s, f, WHITE, spacing=3)
f2 = font(19, False)
s2 = "VILLE  •  CAMPAGNE  •  BASE SÉPARATISTE"
text(d, ((512 - width(d, s2, f2, 2)) / 2, 456), s2, f2, ORANGE, spacing=2)
crop.save(os.path.join(OUT, "miniature_512.jpg"), quality=92)

# ---------- bannière 1920x1080 : 3 secteurs ----------
W, H = 1920, 1080
ban = Image.new("RGB", (W, H), DARK)
panels = [("ville_ciel.jpg", "VILLE", 0.5), ("convoi.jpg", "CAMPAGNE", 0.45), ("sep_front.jpg", "BASE SÉPARATISTE", 0.4)]
pw = W // 3
for i, (fn, label, cx) in enumerate(panels):
    im = grade(Image.open(os.path.join(SH, fn)).convert("RGB"))
    iw, ih = im.size
    sc = H / ih
    im = im.resize((int(iw * sc), H), Image.LANCZOS)
    x0 = int(im.size[0] * cx - pw / 2)
    ban.paste(im.crop((x0, 0, x0 + pw, H)), (i * pw, 0))
ban = shade_bottom(ban, 560, 245)
d = ImageDraw.Draw(ban)
for i in (1, 2):
    d.rectangle((i * pw - 3, 0, i * pw + 3, 700), fill=DARK)
for i, (_, label, _) in enumerate(panels):
    f = font(30)
    text(d, (i * pw + (pw - width(d, label, f, 6)) / 2, 60), label, f, WHITE, spacing=6)
    d.rectangle((i * pw + pw / 2 - 40, 104, i * pw + pw / 2 + 40, 108), fill=ORANGE)
text(d, (92, 712), "NOUVELLE MAP  •  GARRY'S MOD  •  CLONE WARS RP", font(30), ORANGE, spacing=6)
text(d, (84, 760), "TRIPLE FRONT", font(170), WHITE, spacing=6)
text(d, (92, 960), "3 CHAMPS DE BATAILLE  •  AUCUN PACK REQUIS  •  OPEN SOURCE", font(30), GREY, spacing=4)
bx0, by0, bx1, by1 = 1470, 940, 1830, 1010
d.rectangle((bx0, by0, bx1, by1), fill=ORANGE)
f = font(40)
s = "REJOINS-NOUS"
text(d, (bx0 + (bx1 - bx0 - width(d, s, f, 3)) / 2, by0 + 12), s, f, (20, 12, 6), spacing=3, shadow=False)
ban.save(os.path.join(OUT, "banniere_triple_front.png"))
print("ok")
