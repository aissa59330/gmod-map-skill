"""Génère maps_src/rp_cw_battle_of_jabiim.vmf (+ .json pour le plan) — export repris de rp_cw_arsenal_vexis,
pour 3 secteurs empilés (chacun décalé de LEVELS[secteur] en z).

python generator/build_map.py
"""
import json
import os
import random
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from srctools import Vec
from srctools.vmf import VMF, Output

from geom import Block, to_solid, make_box_solid, LIMIT
import terrain as T
import vx as VX
import jabiim as J

MAP = "rp_cw_battle_of_jabiim"
SKY = "sky_day03_04"                # ciel d orage lourd (brief : ciel lourd, humide)
# Nœuds PNJ (info_node) désactivés comme sur Vexis ; positions praticables exportées pour le bench serveur.
WITH_NODES = False
LOD = set(re.findall(r"^OK (models/\S+\.mdl) :", open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generator_tf", "vexis_data",
                                                                    "lod_report.txt"), encoding="utf-8").read(), re.M))


def fade_for(model):
    """Distances de disparition (recette Vexis)."""
    b = VX.BOUNDS[model]
    size = max(b["max"][i] - b["min"][i] for i in range(3))
    if "foliage" in model or "rockcliff" in model or "plants" in model:
        return (3400, 4500) if size > 300 else (1300, 1800)
    if size < 48:
        return 500, 750
    if size < 128:
        return 1000, 1400
    if size < 300:
        return 1800, 2400
    if size < 800:
        return 3000, 3800
    return 0, 0


def shift_world(w, dz):
    for s in w.spaces:
        b = s.box
        s.box = (b[0], b[1], b[2] + dz, b[3], b[4], b[5] + dz)
    w.carve = [(b[0], b[1], b[2] + dz, b[3], b[4], b[5] + dz) for b in w.carve]   # sinon le fond des puits reste bouché

    def sh(b):
        if isinstance(b, Block):
            x0, y0, z0, x1, y1, z1 = b.box
            b.box = (x0, y0, z0 + dz, x1, y1, z1 + dz)
        else:
            b.planes = [(p + Vec(0, 0, dz), n) for (p, n) in b.planes]
            x0, y0, z0, x1, y1, z1 = b.bbox
            b.bbox = (x0, y0, z0 + dz, x1, y1, z1 + dz)
    for b in w.blocks:
        sh(b)
    for e in w.ents:
        if "origin" in e["kv"]:
            x, y, z = (float(c) for c in str(e["kv"]["origin"]).split())
            e["kv"]["origin"] = "%g %g %g" % (x, y, z + dz)
        for b in e["solids"]:
            sh(b)


def node_positions(v, dz):
    """Positions praticables (sol libre, plein air ou cavernes) pour le bench serveur."""
    pts = []
    for x in range(-J.PX + 400, 15600, 640):
        for y in range(-J.PY + 400, J.PY - 400, 640):
            in_cave = any(r[0] < x < r[2] and r[1] < y < r[3] for (r, _) in v.cave_t)
            if (not v.has_t and not in_cave) or (v.has_t and max(abs(x), abs(y)) > J.PX - 300):
                continue
            z = v.gz(x, y)
            if not v.hits((x - 20, y - 20, z + 4, x + 20, y + 20, z + 72)):
                pts.append((x, y, z + 16 + dz))
    return pts


def fx(vmf, v, dz, name):
    """Ambiance (recette Vexis) : fumées, feux + artillerie lointaine qui frappe le paysage au-delà du mur invisible."""
    for kind, (x, y, z), kv in v.fx:
        z += dz
        if kind == "smoke":
            # panache continu et translucide (beaucoup de petites bouffées) au lieu de grosses boules noires opaques
            vmf.create_ent("env_smokestack", origin=f"{x:.0f} {y:.0f} {z:.0f}", InitialState=1, BaseSpread=kv["size"] // 6,
                           SpreadSpeed=30, Speed=90, StartSize=kv["size"] // 6, EndSize=kv["size"] // 2, Rate=kv["rate"] * 3,
                           JetLength=kv["size"] * 3, WindAngle=35, WindSpeed=50, SmokeMaterial="particle/SmokeStack.vmt",
                           rendercolor=kv["color"], renderamt=90, roll=12)
        elif kind == "fire":
            vmf.create_ent("env_fire", origin=f"{x:.0f} {y:.0f} {z:.0f}", health=0, firesize=kv["size"], fireattack=1,
                           firetype=0, spawnflags=1 + 2 + 4 + 16 + 128, damagescale=0, ignitionpoint=0)
    if not v.has_t:
        return 0
    rnd = random.Random(sum(map(ord, name)))
    spots = []
    for k in range(12):
        side = k % 3
        d = rnd.uniform(700, 1700)
        if side == 0:
            x, y = -J.PX - d, rnd.uniform(-J.PY, J.PY)
        else:
            x, y = rnd.uniform(-J.PX, J.PX), ((-J.PY - d) if side == 1 else (J.PY + d))
        spots.append((x, y, v.t.h(x, y) + 48 + dz))
    case = vmf.create_ent("logic_case", origin=f"0 0 {dz + 3000}", targetname=f"artillerie_{name}_case")
    for i, (x, y, z) in enumerate(spots):
        nm = f"artillerie_{name}_{i}"
        vmf.create_ent("env_explosion", origin=f"{x:.0f} {y:.0f} {z:.0f}", targetname=nm, iMagnitude=0, iRadiusOverride=1,
                       spawnflags=1 + 4 + 64 + 2048, fireballsprite="sprites/zerogxplode.spr", rendermode=5)
        vmf.create_ent("env_shake", origin=f"{x:.0f} {y:.0f} {z:.0f}", targetname=nm, amplitude=3, radius=5200, duration=1.4,
                       frequency=60, spawnflags=4 + 8)
        vmf.create_ent("ambient_generic", origin=f"{x:.0f} {y:.0f} {z + 64:.0f}", targetname=nm + "_snd",
                       message="ambient/explosions/explode_" + str(1 + i % 9) + ".wav", health=10, radius=12000,
                       spawnflags=16 + 32, pitch=85, pitchstart=85)
        case.add_out(Output(f"OnCase{i + 1:02d}", nm, "Explode"))
        case.add_out(Output(f"OnCase{i + 1:02d}", nm, "StartShake"))
        case.add_out(Output(f"OnCase{i + 1:02d}", nm + "_snd", "PlaySound"))
    vmf.create_ent("logic_timer", origin=f"0 64 {dz + 3000}", targetname=f"artillerie_{name}_timer", UseRandomTime=1,
                   LowerRandomBound=7, UpperRandomBound=18).add_out(Output("OnTimer", f"artillerie_{name}_case", "PickRandomShuffle"))
    return len(spots)


def main():
    t0 = time.time()
    sectors = J.build_all()
    vmf = VMF()
    vmf.spawn["skyname"] = SKY
    vmf.map_ver = int(time.time()) // 60 % 1000000      # version unique : un ancien graphe PNJ (.ain) est ignoré
    vmf.spawn["mapversion"] = vmf.map_ver
    vmf.spawn["detailvbsp"] = "detail_vexis.vbsp"
    vmf.spawn["detailmaterial"] = "detail/detailsprites"
    vmf.spawn["maxpropscreenwidth"] = -1
    side = {"levels": J.LEVELS, "sectors": {}}
    detail = vmf.create_ent("func_detail")
    vc = vmf.create_ent("func_viscluster")
    tot = {"world": 0, "detail": 0, "props": 0, "lod": 0, "disp": 0, "lights": 0}
    for (name, v, dz) in sectors:
        w = v.w
        cells = J.viscells(v, dz) if v.has_t else []
        nodes = node_positions(v, dz)
        hm = None
        if v.has_t:
            hm = {"x0": J.XA, "y0": J.YA, "step": 512,
                  "rows": [[round(v.t.h(J.XA + i * 512, J.YA + j * 512)) for i in range(63)] for j in range(63)]}
        shift_world(w, dz)
        for box, mat, sky, zone, role, sname in w.shell_slabs():
            for c in box:
                assert abs(c) <= LIMIT, box
            sol = make_box_solid(vmf, box, mat)
            for sd in sol.sides:
                sd.lightmap = 128 if v.has_t else 32
            vmf.add_brush(sol)
        if v.has_t:
            nd, nb = T.add_displacements(vmf, v.t, lightmap=32, lightmap_far=64, dz=dz)
            tot["disp"] += nd
        for (r, ct) in getattr(v, "cave_t", ()):                      # sols naturels des cavernes
            nd, nb = T.add_displacements(vmf, ct, lightmap=32, lightmap_far=32, dz=dz)
            tot["disp"] += nd
        for b in w.blocks:
            s = to_solid(vmf, b)
            bb = b.box if isinstance(b, Block) else b.bbox
            big = max(bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2])
            for sd in s.sides:
                sd.lightmap = 32 if big >= 1500 else 16
            axis = isinstance(b, Block) or all(max(abs(n.x), abs(n.y), abs(n.z)) > 0.999 for _, n in b.planes)
            if (b.kind == "world" and axis) or b.kind == "world!":
                vmf.add_brush(s); tot["world"] += 1
            else:
                detail.solids.append(s); tot["detail"] += 1
        for (x0, y0, z0, x1, y1, z1) in getattr(v, "water", []):        # eau (marais, lac) : brush world, dessus = eau
            sol = make_box_solid(vmf, (x0, y0, z0 + dz, x1, y1, z1 + dz), "tools/toolsnodraw", top=J.WATER)
            vmf.add_brush(sol)
        for box in cells:
            vc.solids.append(make_box_solid(vmf, box, "tools/toolstrigger"))
        for (x, y, z) in v.spawns:
            vmf.create_ent("info_player_start", origin=f"{x} {y} {z + dz}", angles="0 0 0")
        for k, (x, y, z) in enumerate(v.droid_spawns):
            vmf.create_ent("info_target", origin=f"{x:.0f} {y:.0f} {z + dz:.0f}", angles="0 180 0", targetname=f"spawn_droides_{k + 1}")
        for (model, (x, y, z), yaw, solid) in v.props:
            mn, mx = fade_for(model)
            out = model
            if model in LOD:
                out = "models/vxl/" + os.path.basename(model)
                tot["lod"] += 1
                solid = 0 if ("plants" in model or "foliage" in model) else 2
            elif "foliage" in model and "tree" not in model:
                solid = 0
            tp, tr = getattr(v, "tilt", {}).get((model, round(x), round(y)), (0, 0))
            vmf.create_ent("prop_static", origin=f"{x} {y} {z + dz}", angles=f"{tp:.1f} {yaw:.1f} {tr:.1f}", model=out, solid=solid, skin=0,
                           fademindist=mn, fademaxdist=mx, disableshadows=1 if (0 < mx < 2500) else 0)
            tot["props"] += 1
        for (m, x, y, z, yaw) in getattr(v, "sky_props", []):           # vaisseaux du ciel 3D (versions légères Vexis)
            vmf.create_ent("prop_static", origin=f"{x} {y} {z + dz}", angles=f"0 {yaw} 0", model=m, solid=0, disableshadows=1,
                           fademindist=-1, fademaxdist=0, skin=0)
        for e in w.ents:
            kv = {k: (str(val) if not isinstance(val, str) else val) for k, val in e["kv"].items()}
            ent = vmf.create_ent(e["classname"], **kv)
            for b in e["solids"]:
                ent.solids.append(to_solid(vmf, b))
            for (o, tgt, inp, param, delay, times) in e["outputs"]:
                ent.add_out(Output(o, tgt, inp, param, delay=delay, times=times))
            tot["lights"] += e["classname"] == "light"
        n_art = fx(vmf, v, dz, name)
        sd = {"dz": dz, "spaces": [{"box": s.box, "sky": s.sky} for s in w.spaces],
              "blocks": [list(b.box if isinstance(b, Block) else b.bbox) + [b.mat] for b in w.blocks],
              "rects": v.rects + [l for l in v.labels if len(l) == 5], "info": v.info, "routes": v.routes,
              "props": [[m, [p[0], p[1], p[2] + dz]] for (m, p, y, s) in v.props],
              "spawns": [(x, y, z + dz) for (x, y, z) in v.spawns], "droid_spawns": [(x, y, z + dz) for (x, y, z) in v.droid_spawns],
              "tp": [[*e["solids"][0].box, e["kv"].get("target", "")] for e in w.ents if e["classname"] == "trigger_teleport"],
              "tp_dest": [[float(c) for c in e["kv"]["origin"].split()] for e in w.ents if e["classname"] == "info_teleport_destination"],
              "node_pos": [[round(c) for c in p] for p in nodes], "hm": hm}
        side["sectors"][name] = sd
        print(f"  {name}: props={len(v.props)} refus={dict(sorted(v.rej.items(), key=lambda kv: -kv[1])[:10])} artillerie={n_art} "
              f"positions={len(nodes)}")
    # environnement (entités DANS l'air du secteur 1) : orage, lumière froide, brouillard gris-vert
    ez = sectors[0][2] + 3000
    # brief étape 6 : soleil voilé plus bas et plus faible (ombres longues = relief lisible), ambiance froide plus présente,
    # ombres des props dans le même sens que le soleil
    vmf.create_ent("light_environment", origin=f"-15000 0 {ez}", angles="-48 35 0", pitch=-48,
                   _light="186 190 192 175", _ambient="98 108 118 150", _lightHDR="-1 -1 -1 1", _ambientHDR="-1 -1 -1 1",
                   SunSpreadAngle=25)
    vmf.create_ent("shadow_control", origin=f"-15000 64 {ez}", angles="48 35 0", color="44 48 52", distance=96, disableallshadows=0)
    vmf.create_ent("env_fog_controller", origin=f"-15000 128 {ez}", fogenable=1, fogblend=0, fogcolor="112 120 118",
                   fogcolor2="112 120 118", fogstart=900, fogend=7000, fogmaxdensity=0.82, farz=8000, fogdir="1 0 0",
                   targetname="fog_main", use_angles=0)
    vmf.create_ent("env_tonemap_controller", origin=f"-15000 192 {ez}", targetname="tonemap")
    for ent in vmf.entities:
        if ent["classname"] in ("func_detail", "func_illusionary", "trigger_teleport", "func_door"):
            ent["gmod_allowphysgun"] = "0"
            ent["gmod_allowtools"] = "aucun"
    os.makedirs(os.path.join(ROOT, "maps_src"), exist_ok=True)
    path = os.path.join(ROOT, "maps_src", MAP + ".vmf")
    with open(path, "w", encoding="utf-8") as f:
        vmf.export(f)
    with open(os.path.join(ROOT, "maps_src", MAP + ".json"), "w", encoding="utf-8") as f:
        json.dump(side, f)
    print(f"VMF : {path}  ({time.time() - t0:.0f} s)")
    print(f"  {tot}  viscluster={len(vc.solids)}  stats={J.STATS}")


if __name__ == "__main__":
    main()
