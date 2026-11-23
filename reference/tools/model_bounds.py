"""Bornes (hull) des modèles de base -> generator/prop_bounds.json.  python tools/model_bounds.py m1.mdl m2.mdl ..."""
import json, os, sys
from srctools.mdl import Model
from srctools.filesys import VPKFileSystem, FileSystemChain
SE = r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
fs = FileSystemChain(*[VPKFileSystem(SE + p) for p in (r"\sourceengine\hl2_misc_dir.vpk", r"\sourceengine\hl2_textures_dir.vpk", r"\garrysmod\garrysmod_dir.vpk")])
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generator", "prop_bounds.json")
data = json.load(open(out)) if os.path.exists(out) else {}
for m in sys.argv[1:]:
    try:
        mdl = Model(fs, fs[m])
        lo, hi = mdl.hull_min, mdl.hull_max
        if (hi - lo).mag() < 1:
            lo, hi = mdl.view_min, mdl.view_max
        data[m] = {"min": [round(v, 1) for v in lo], "max": [round(v, 1) for v in hi], "static": bool(mdl.flags.value & 0x10) if hasattr(mdl, "flags") else None}
        print(m, data[m]["min"], data[m]["max"])
    except Exception as e:
        print("ERR", m, e)
json.dump(data, open(out, "w"), indent=1)
