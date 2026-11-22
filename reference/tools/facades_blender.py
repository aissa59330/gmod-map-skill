"""CONTRÔLE DES FAÇADES (Blender + Plumber, arrière-plan) :
  blender -b --factory-startup -P tools/facades_blender.py -- carte.vmf recense.json sortie_dossier
Importe le VMF (brushes + props, contenu des packs), puis rend chaque bâtiment de surface sur ses 4 côtés
(façade, arrière, gauche, droite), caméra orthographique légèrement plongeante. Les préférences ne sont pas sauvegardées."""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
vmf, rec, out = argv[0], json.load(open(argv[1], encoding="utf8")), argv[2]
os.makedirs(out, exist_ok=True)
GN = os.environ.get("GMOD_PACKS", r"C:/gn_content")   # packs Workshop extraits (chemin court)
SE = r"C:/Program Files (x86)/Steam/steamapps/common/GarrysMod"
EXT = "bl_ext.user_default.plumber"
if EXT not in bpy.context.preferences.addons:
    bpy.ops.preferences.addon_enable(module=EXT)
bpy.context.preferences.use_preferences_save = False
prefs = bpy.context.preferences.addons[EXT].preferences
game = prefs.games.add()
game.name = "jabiim_controle"
paths = [("DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "content", "maison")),
         ("DIR", os.environ.get("GMOD_CONTENU_EXTRA", os.path.join(GN, "_extra")))]
paths += [("DIR", os.path.join(GN, d)) for d in sorted(os.listdir(GN)) if os.path.isdir(os.path.join(GN, d))]
paths += [("VPK", SE + "/garrysmod/garrysmod_dir.vpk"), ("VPK", SE + "/sourceengine/hl2_misc_dir.vpk"),
          ("VPK", SE + "/sourceengine/hl2_textures_dir.vpk")]
for (k, p) in paths:
    sp = game.search_paths.add()
    sp.kind = k
    sp["path"] = p
gi = str(len(prefs.games) - 1)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.plumber_vmf(filepath=vmf, game=gi, import_props=True, import_overlays=False, scale=0.01)
print("VMF importé :", len(bpy.data.objects), "objets")

S = 0.01
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.display.shading.show_shadows = True
sc.view_settings.exposure = 1.0
sc.render.resolution_x, sc.render.resolution_y = 560, 400
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.clip_start, cam.data.clip_end = 0.1, 200

blds = []
for r in rec:
    if r["type"] == "house":
        blds.append(("maison_%s_%s" % (r["kind"], r["state"]), r["x"], r["y"], r.get("z", 0), r["w"], r["d"], 224 * r["floors"] + 300,
                     r["yaw"]))
    elif r["type"] == "vault_hall":
        blds.append(("halle", r["x"], r["y"], r["z"], r["w"], r["d"], r["h"] + 350, r["yaw"]))
    elif r["type"] == "round_hall" and r["caller"] != "caves":
        blds.append(("dome", r["x"], r["y"], r["z"], 2 * r["r"], 2 * r["r"], r["h"] + r["r"] * 0.6, 0))
names = ("facade", "droite", "arriere", "gauche")
for i, (nm, x, y, z, w, d, h, yaw) in enumerate(blds):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    ctr = Vector((x * S, y * S, (z + h * 0.4) * S))
    for k, (lx, ly) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):     # façade = -y local
        dv = Vector((lx * c - ly * s, lx * s + ly * c, 0.45)).normalized()
        span = (w if ly else d) * 1.35
        cam.location = ctr + dv * (max(w, d) * S * 2.2)
        cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = max(span, h * 1.6) * S
        sc.render.filepath = os.path.join(out, "_f_%03d_%d.png" % (i, k))
        bpy.ops.render.render(write_still=True)
json.dump([(b[0], round(b[1]), round(b[2])) for b in blds], open(os.path.join(out, "facades_index.json"), "w", encoding="utf8"))
print("façades rendues :", len(blds), "bâtiments")
