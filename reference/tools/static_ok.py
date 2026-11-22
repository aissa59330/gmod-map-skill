"""Indique si un modèle peut être prop_static (pas de prop_data « dynamique seulement »).
python tools/static_ok.py m1.mdl ..."""
import re, sys
from srctools.mdl import Model
from srctools.filesys import VPKFileSystem, FileSystemChain
SE = r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
fs = FileSystemChain(*[VPKFileSystem(SE + p) for p in (r"\sourceengine\hl2_misc_dir.vpk", r"\garrysmod\garrysmod_dir.vpk")])
for m in sys.argv[1:]:
    try:
        kv = Model(fs, fs[m]).keyvalues or ""
    except Exception as e:
        print("ERR", m, e); continue
    pd = re.search(r'"prop_data"\s*\{([^}]*)\}', kv, re.I)
    allow = pd and re.search(r'"allowstatic"\s*"1"', pd.group(1), re.I)
    print(("OK " if (not pd or allow) else "DYN"), m, (pd.group(1).strip().replace("\n", " ")[:70] if pd else ""))
