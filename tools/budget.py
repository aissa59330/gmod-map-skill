"""BUDGET PAR ZONE avant compilation (lecture du .vmf, quelques secondes) : plans uniques, part de brushes obliques et
nombre de brushes par zone, + estimation des plans du BSP. C'est un INDICATEUR (estimation), pas une mesure du BSP :
la mesure vient de tools/audit_bsp.py après vbsp.
Étalonnage mesuré (Jabiim, 2026-11) : plans du BSP ≈ 5,1 à 5,5 × paires de plans uniques du VMF (biseaux + découpes).

Usage : python tools/budget.py <map.vmf> [--zones zones.json] [--cell 4096]
  zones.json = {"nom": [x0, y0, x1, y1], ...} (sinon grille de --cell unités)"""
import argparse
import json
import math
import re
from collections import defaultdict

RATIO = (5.1, 5.5)
MAX_PLANES = 65536
PLANE = re.compile(r'"plane" "\(([^)]*)\) \(([^)]*)\) \(([^)]*)\)"')


def planes(vmf_text):
    """-> liste de (clé du plan, oblique ?, centre x, centre y) par face de brush."""
    out = []
    for m in PLANE.finditer(vmf_text):
        a, b, c = [list(map(float, g.split())) for g in m.groups()]
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        ln = math.sqrt(sum(x * x for x in n)) or 1.0
        n = [x / ln for x in n]
        d = sum(n[i] * a[i] for i in range(3))
        k1 = tuple(round(x, 3) for x in n) + (round(d, 1),)
        k2 = tuple(round(-x, 3) for x in n) + (round(-d, 1),)
        obl = sum(1 for x in n if abs(abs(x) - 1) < 1e-3) != 1
        out.append((min(k1, k2), obl, (a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3))
    return out


def budget(text, zones=None, cell=4096):
    def zone_of(x, y):
        if zones:
            for name, (x0, y0, x1, y1) in zones.items():
                if x0 <= x <= x1 and y0 <= y <= y1:
                    return name
            return "hors zones"
        return f"{int(x // cell)},{int(y // cell)}"
    seen = set()
    per = defaultdict(lambda: {"plans": 0, "obliques": 0})
    for key, obl, x, y in planes(text):
        if key in seen:
            continue
        seen.add(key)
        z = per[zone_of(x, y)]
        z["plans"] += 1
        z["obliques"] += obl
    tot = len(seen)
    est = (round(tot * RATIO[0]), round(tot * RATIO[1]))
    return {"paires_uniques": tot, "plans_bsp_estimes": est,
            "pct_estime": (round(100 * est[0] / MAX_PLANES, 1), round(100 * est[1] / MAX_PLANES, 1)),
            "zones": dict(sorted(per.items(), key=lambda kv: -kv[1]["plans"]))}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("vmf")
    ap.add_argument("--zones")
    ap.add_argument("--cell", type=int, default=4096)
    a = ap.parse_args()
    r = budget(open(a.vmf, encoding="utf-8", errors="ignore").read(),
               json.load(open(a.zones, encoding="utf-8")) if a.zones else None, a.cell)
    print(f"BUDGET (ESTIMATION avant compilation) : {r['paires_uniques']} plans uniques dans le VMF"
          f" -> {r['plans_bsp_estimes'][0]}-{r['plans_bsp_estimes'][1]} plans dans le BSP"
          f" ({r['pct_estime'][0]}-{r['pct_estime'][1]} % de 65 536 ; viser < 85 %)")
    print("  zone                 plans  obliques")
    for z, v in list(r["zones"].items())[:12]:
        print(f"  {z:20} {v['plans']:6}  {100 * v['obliques'] // max(1, v['plans']):3} %")
