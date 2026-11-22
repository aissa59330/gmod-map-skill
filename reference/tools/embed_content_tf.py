"""Embarque dans le .bsp tout ce que la map prend aux packs Workshop NON requis (4 packs requis maximum).

Lit maps_src/rp_cw_triple_front.vmf (style Vexis) (textures des brushes, props, décalques) et les modèles maison (models/gnl = LOD des
props d'origine, models/givre_noir), cherche chaque fichier dans les packs extraits (tools/content_paths.txt) :
  - présent dans un pack requis (REQUIRED) -> rien à faire ;
  - présent seulement dans un autre pack -> copié dans compile_game/embed/<chemin> (compile.ps1 l'ajoute au .bsp).
python tools/embed_content.py
"""
import os
import re
import shutil

from srctools import Keyvalues
from srctools.filesys import RawFileSystem
from srctools.mdl import Model
from srctools.vmf import VMF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ()   # aucun pack requis : tout ce qui est utilisé est embarqué dans le .bsp
PACKS = [l.strip() for l in open(os.path.join(ROOT, "tools", "content_paths.txt"), encoding="utf-8")
         if l.strip() and not l.startswith("#")]
OUT = "C:/gn_content/_tf"     # chemin court : bspzip ignore les fichiers au-delà de 260 caractères
# cartes de relief non embarquées (5,6 Mo chacune) : on les retire des .vmt embarqués, rendu quasi identique
NO_BUMP = ()
TEX_KEYS = ("$bumpmap", "$bumpmap2", "$normalmap", "$basetexture", "$basetexture2", "$envmapmask", "$detail",
            "$selfillummask", "$phongexponenttexture", "$lightwarptexture", "$blendmodulatetexture", "$iris", "$ambientoccltexture")


from srctools.filesys import VPKFileSystem
_SE = r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
BASE = set()
for _v in (r"\sourceengine\hl2_misc_dir.vpk", r"\sourceengine\hl2_textures_dir.vpk", r"\sourceengine\hl2_sound_misc_dir.vpk",
           r"\garrysmod\garrysmod_dir.vpk"):
    try:
        for _f in VPKFileSystem(_SE + _v).walk_folder(""):
            BASE.add(_f.path.replace("\\", "/").lower())
    except Exception as _e:
        print("vpk", _v, _e)


def find(rel):
    """-> (pack requis ?, chemin) ou None. Un fichier du jeu de base n'est jamais pris dans un pack."""
    if rel.lower() in BASE:
        return None
    hits = [p for p in PACKS if os.path.isfile(os.path.join(p, rel))]
    if not hits:
        return None
    req = [p for p in hits if p.rsplit("_", 1)[1] in REQUIRED]
    return (True, req[0]) if req else (False, hits[0])


copied = {}


def take(rel):
    rel = rel.replace("\\", "/").lower()
    if rel in copied:
        return copied[rel]
    f = find(rel)
    copied[rel] = f
    if f and not f[0]:
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(f[1], rel), dst)
    return f


def material(name):
    name = name.replace("\\", "/").lower().strip("/")
    rel = f"materials/{name}.vmt"
    f = take(rel)
    if not f or f[0]:
        return f
    dst = os.path.join(OUT, rel)
    lines = open(dst, encoding="utf-8", errors="replace").read().splitlines()
    keep = [l for l in lines if not any(re.match(r'\s*"?' + re.escape(k) + r'"?\s', l, re.I) for k in NO_BUMP)]
    open(dst, "w", encoding="utf-8").write("\n".join(keep) + "\n")
    try:
        kv = Keyvalues.parse(open(dst, encoding="utf-8", errors="replace"))
    except Exception:
        return f
    for blk in kv:
        for k in blk.iter_tree(blocks=False):
            if k.name in TEX_KEYS and k.value:
                take(f"materials/{k.value.replace(chr(92), '/').lower().removesuffix('.vtf')}.vtf")
            if k.name == "include":
                take(k.value)
    return f


def model(rel, skins_from=None):
    rel = rel.replace("\\", "/").lower()
    f = find(rel)
    if f is None and not skins_from:
        return
    if f and not f[0]:
        base = rel[:-4]
        for ext in (".mdl", ".vvd", ".dx90.vtx", ".dx80.vtx", ".sw.vtx", ".phy"):
            take(base + ext)
    src = skins_from or (f and f[1])
    if not src or (f and f[0] and not skins_from):
        return
    fs = RawFileSystem(src)
    try:
        m = Model(fs, fs[rel])
    except Exception as e:
        print("illisible", rel, e)
        return
    for skin in m.skins:
        for tex in skin:
            for cd in m.cdmaterials:
                if material(cd.replace("\\", "/").strip("/") + "/" + tex):
                    break


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    vmf = VMF.parse(Keyvalues.parse(open(os.path.join(ROOT, "maps_src", "rp_cw_triple_front.vmf"), encoding="utf-8")))
    for sol in vmf.iter_wbrushes(world=True, detail=True):
        for face in sol:
            material(face.mat)
    for sfx in ("bk", "dn", "ft", "lf", "rt", "up"):
        material("skybox/" + vmf.spawn["skyname"] + sfx)
    lod = {}
    rep = os.path.join(os.path.dirname(ROOT), "gmod_arsenal_vexis", "assets", "lod_props", "lod_report.txt")   # LOD faits pour Vexis
    if os.path.exists(rep):
        for m in re.findall(r"^OK (models/\S+\.mdl)", open(rep, encoding="utf-8").read(), re.M):
            lod[os.path.splitext(os.path.basename(m))[0].lower()] = m
    for e in vmf.entities:
        for sol in e.solids:
            for face in sol:
                material(face.mat)
        for key in ("material", "texture"):
            if e[key]:
                material(e[key].removesuffix(".vmt"))
        mdl = (e["model"] or "").lower()
        if not mdl.endswith(".mdl"):
            continue
        name = os.path.splitext(os.path.basename(mdl))[0]
        if mdl.startswith("models/vxl/"):
            model(mdl, skins_from=os.path.join(ROOT, "compile_game"))  # modèle maison : ses matériaux
        else:
            model(mdl)
    files = [r for r, f in copied.items() if f and not f[0]]
    size = sum(os.path.getsize(os.path.join(OUT, r)) for r in files)
    used = sorted({os.path.basename(f[1]) for f in copied.values() if f})
    print(f"embarqués : {len(files)} fichiers, {size / 1e6:.1f} Mo")
    print("packs encore utilisés directement :", [u for u in used if u.rsplit('_', 1)[1] in REQUIRED])


if __name__ == "__main__":
    main()
