"""AUDIT TECHNIQUE d'un .bsp Source (lecture seule) : compteurs face aux limites du moteur, entités, props statiques,
lumières, cubemaps, overlays, visibilité, puis les 3 corrections au meilleur rapport gain / qualité.
Les chiffres sont des MESURES du fichier ; ce ne sont pas des FPS (seuls les benchmarks en jeu mesurent les FPS).

Usage : python tools/audit_bsp.py <map.bsp> [--json rapport.json] [--compare ancien.bsp]
Sortie : ~25 lignes lisibles (+ JSON complet si --json)."""
import argparse
import json
import os
import re
import struct
import sys
from collections import Counter

# limites du moteur (Source 2013 / Garry's Mod) : (lump, taille d'un élément, limite)
LIMITS = {
    "plans": (1, 20, 65536), "sommets": (3, 12, 65536), "faces": (7, 56, 65536), "brushes": (18, 12, 8192),
    "côtés de brushes": (19, 8, 65536), "texinfo": (6, 72, 12288), "texdata (matériaux)": (2, 32, 2048),
    "modèles de brushes": (14, 48, 1024), "feuilles (leafs)": (10, 32, 65536), "overlays": (45, 352, 512),
}
ALERT = 0.85                                     # au-delà : alerte (marge à garder pour les ajouts)


def lumps(path):
    with open(path, "rb") as f:
        head = f.read(8 + 16 * 64)
    ident, ver = struct.unpack_from("<4si", head, 0)
    if ident != b"VBSP":
        sys.exit(f"pas un BSP Source : {path}")
    out = {}
    for i in range(64):
        ofs, ln, lver, _ = struct.unpack_from("<iiii", head, 8 + 16 * i)
        out[i] = (ofs, ln, lver)
    return ver, out


def read(path, ofs, ln):
    with open(path, "rb") as f:
        f.seek(ofs)
        return f.read(ln)


def audit(path):
    ver, L = lumps(path)
    r = {"fichier": os.path.basename(path), "taille_mo": round(os.path.getsize(path) / 1e6, 1), "version_bsp": ver,
         "limites": {}}
    for name, (idx, size, lim) in LIMITS.items():
        n = L[idx][1] // size
        r["limites"][name] = {"n": n, "max": lim, "pct": round(100 * n / lim, 1)}
    vis = L[4]
    r["clusters_visibilite"] = struct.unpack("<i", read(path, vis[0], 4))[0] if vis[1] >= 4 else 0
    r["cubemaps"] = L[42][1] // 16
    r["lumieres_monde"] = L[15][1] // 88
    r["lightmaps_mo"] = round(max(L[8][1], L[53][1]) / 1e6, 1)
    # entités (texte)
    txt = read(path, L[0][0], L[0][1]).decode("latin-1", "replace")
    classes = Counter(re.findall(r'"classname"\s+"([^"]+)"', txt))
    r["entites"] = {"total": sum(classes.values()), "top": classes.most_common(12)}
    named_lights = len(re.findall(r'"classname"\s+"light(?:_spot)?"[^}]*"targetname"', txt)) + \
        len(re.findall(r'"targetname"[^}]*"classname"\s+"light(?:_spot)?"', txt))
    r["lumieres_nommees"] = named_lights
    r["props_dynamiques"] = classes.get("prop_dynamic", 0) + classes.get("prop_dynamic_override", 0)
    r["props_physiques"] = classes.get("prop_physics", 0) + classes.get("prop_physics_multiplayer", 0)
    r["decals_infodecal"] = classes.get("infodecal", 0)
    # props statiques (srctools)
    try:
        from srctools.bsp import BSP
        b = BSP(path)
        props = list(b.props)
        fade_ok = sum(1 for p in props if getattr(p, "max_fade", 0) and p.max_fade > 0)
        models = Counter(p.model.lower() for p in props)
        r["props_statiques"] = {"total": len(props), "avec_fondu": fade_ok, "sans_fondu": len(props) - fade_ok,
                                "modeles_distincts": len(models), "plus_frequents": models.most_common(5)}
    except Exception as e:                       # srctools absent ou format inattendu : on le dit
        r["props_statiques"] = {"erreur": f"{type(e).__name__}: {e}"[:160]}
    r["corrections"] = corrections(r)
    return r


def corrections(r):
    c = []
    lim = r["limites"]
    if lim["plans"]["pct"] > 85:
        c.append((3, f"plans à {lim['plans']['pct']} % : remplacer les brushes obliques (bâtiments tournés, routes inclinées,"
                     " cylindres) par des modèles ou des brushes axiaux"))
    if lim["sommets"]["pct"] > 85:
        c.append((3, f"sommets à {lim['sommets']['pct']} % : retirer corniches/fenêtres des petits bâtiments, passer le détail en modèles"))
    if lim["côtés de brushes"]["pct"] > 85 or lim["brushes"]["pct"] > 85:
        c.append((3, "brushes / côtés proches de la limite : fusionner les blocs, détail en modèles"))
    ps = r.get("props_statiques", {})
    if isinstance(ps.get("total"), int) and ps["total"] and ps["sans_fondu"] / ps["total"] > 0.3:
        c.append((2, f"{ps['sans_fondu']} props statiques sans distance de fondu : appliquer le barème de fondu (module 14)"))
    if r["props_physiques"] > 50:
        c.append((2, f"{r['props_physiques']} props physiques : passer en prop_static ce qui ne doit pas bouger"))
    if r["cubemaps"] == 0:
        c.append((2, "aucun env_cubemap : reflets faux sur toutes les surfaces brillantes ; en placer un par espace"))
    if r["limites"]["overlays"]["n"] + r["decals_infodecal"] == 0:
        c.append((1, "aucune décalcomanie ni overlay : sols et murs « propres » (réalisme, module 07/10)"))
    if r["lumieres_nommees"] > 40:
        c.append((1, f"{r['lumieres_nommees']} lumières nommées : risque de styles de lumière > 4 par face"))
    c.sort(key=lambda t: -t[0])
    return [t[1] for t in c[:3]] or ["aucune correction prioritaire détectée par l'audit statique"]


def show(r, old=None):
    print(f"AUDIT {r['fichier']}  ({r['taille_mo']} Mo, BSP v{r['version_bsp']})  — mesures du fichier, pas des FPS")
    for k, v in r["limites"].items():
        flag = "  ⚠" if v["pct"] / 100 > ALERT else ""
        d = ""
        if old:
            dv = v["n"] - old["limites"][k]["n"]
            d = f"  ({'+' if dv >= 0 else ''}{dv})"
        print(f"  {k:22} {v['n']:>7} / {v['max']:<6} {v['pct']:>5} %{d}{flag}")
    ps = r["props_statiques"]
    print(f"  props statiques      : {ps.get('total', '?')} (sans fondu {ps.get('sans_fondu', '?')}, modèles distincts "
          f"{ps.get('modeles_distincts', '?')})")
    print(f"  entités {r['entites']['total']} · props dynamiques {r['props_dynamiques']} · physiques {r['props_physiques']}"
          f" · cubemaps {r['cubemaps']} · lumières {r['lumieres_monde']} (nommées {r['lumieres_nommees']})"
          f" · overlays {r['limites']['overlays']['n']} · clusters de visibilité {r['clusters_visibilite']}"
          f" · lightmaps {r['lightmaps_mo']} Mo")
    print("  CORRECTIONS PRIORITAIRES :")
    for c in r["corrections"]:
        print("   -", c)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("bsp")
    ap.add_argument("--json")
    ap.add_argument("--compare")
    a = ap.parse_args()
    rep = audit(a.bsp)
    old = audit(a.compare) if a.compare else None
    show(rep, old)
    if a.json:
        json.dump(rep, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
