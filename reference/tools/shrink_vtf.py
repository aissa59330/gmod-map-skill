"""Réduit les grosses textures embarquées (dossier _tf) : vaisseaux lointains 512 px, le reste 1024 px max, en DXT.
python tools/shrink_vtf.py"""
import os
from srctools.vtf import VTF, ImageFormats

OUT = r"C:/gn_content/_tf"
before = after = n = 0
for dp, _, fl in os.walk(OUT):
    for f in fl:
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, OUT).replace(os.sep, "/").lower()
        if not rel.startswith("materials/"):
            continue
        size = os.path.getsize(p)
        try:
            with open(p, "rb") as fh:
                v = VTF.read(fh); v.load()
        except Exception:
            continue
        cap = 512 if "/salty/" in rel else 1024
        if v.width <= cap and v.height <= cap and size < 1_500_000:
            continue
        k = max(v.width, v.height) / cap
        w, h = max(4, int(v.width / max(k, 1))), max(4, int(v.height / max(k, 1)))
        im = v.get().to_PIL().convert("RGBA").resize((w, h))
        alpha = im.getextrema()[3][0] < 250
        fmt = ImageFormats.DXT5 if alpha else ImageFormats.DXT1
        nv = VTF(w, h, fmt=fmt, version=(7, 2), flags=v.flags)
        nv.get().copy_from(im.tobytes(), ImageFormats.RGBA8888)
        nv.compute_mipmaps()
        with open(p, "wb") as fh:
            nv.save(fh)
        before += size; after += os.path.getsize(p); n += 1
print(f"textures réduites : {n}, {before / 1e6:.1f} Mo -> {after / 1e6:.1f} Mo")
