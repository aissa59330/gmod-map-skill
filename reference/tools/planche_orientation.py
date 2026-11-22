"""PLANCHE DE CONTRÔLE DES ORIENTATIONS (Blender + Plumber, en arrière-plan) :
  blender -b -P tools/planche_orientation.py -- liste_modeles.json sortie_dossier
Chaque modèle est importé à sa vraie taille, en rangées ; la caméra regarde depuis +X (l'avant attendu par le générateur).
Un modèle dont on voit le dos ou le flanc sur la vue « avant » a besoin d'une exception dans interieurs.ORIENT.
Vue « dessus » : flèche rouge = +X. Les préférences de Blender ne sont pas modifiées (rien n'est sauvegardé)."""
import json
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
models = json.load(open(argv[0], encoding="utf8"))
out = argv[1]
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
paths = [("DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "content", "maison"))]
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
S = 0.01
COLS, DY, DZ = 10, 3.4, 2.6
missing = []
for i, m in enumerate(models):
    r, c = divmod(i, COLS)
    before = set(bpy.data.objects)
    try:
        bpy.ops.import_scene.plumber_mdl(filepath=m, from_game_fs=True, game=gi, scale=S, import_animations=False)
    except Exception as e:
        missing.append((m, str(e)[:80]))
        continue
    new = [o for o in bpy.data.objects if o not in before]
    if not new:
        missing.append((m, "rien importé"))
        continue
    roots = [o for o in new if o.parent is None]
    for o in roots:
        o.location = (0, c * DY, -r * DZ)
    # étiquette lisible depuis +X, sous le modèle
    bpy.ops.object.text_add(location=(1.6, c * DY, -r * DZ - 0.45), rotation=(math.pi / 2, 0, math.pi / 2))
    t = bpy.context.object
    t.data.body = "%d %s" % (i, m.split("/")[-1][:-4][:22])
    t.data.size = 0.22
    t.data.align_x = "CENTER"
    # flèche +X (vue de dessus)
    bpy.ops.mesh.primitive_cone_add(radius1=0.12, depth=0.5, location=(0.9, c * DY, -r * DZ + 0.02),
                                    rotation=(0, math.pi / 2, 0))
    a = bpy.context.object
    mat = bpy.data.materials.get("fleche") or bpy.data.materials.new("fleche")
    mat.diffuse_color = (1, 0, 0, 1)
    a.data.materials.append(mat)

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.view_settings.exposure = 1.2
sc.render.resolution_x, sc.render.resolution_y = 420, 340
sc.render.film_transparent = False
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
cam.data.type = "ORTHO"
sc.camera = cam
groups = {}
for o in bpy.data.objects:
    if o.type == "MESH" and o.name != "cam":
        groups.setdefault((round(o.matrix_world.translation.y / DY), round(-o.matrix_world.translation.z / DZ)), []).append(o)
from mathutils import Vector
for i, m in enumerate(models):
    r, c = divmod(i, COLS)
    obs = groups.get((c, r), [])
    for o in bpy.data.objects:
        o.hide_render = o not in obs and o.type != "CAMERA"
    pts = [o.matrix_world @ Vector(v) for o in obs if o.type == "MESH" and o.data.name.find("Cone") < 0 for v in o.bound_box]
    if not pts:
        continue
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr, size = (lo + hi) / 2, max((hi - lo).length, 0.3)
    d = Vector((1.0, 0.45, 0.6)).normalized()                     # trois quarts face : depuis +X, un peu à droite, en hauteur
    cam.location = ctr + d * size * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = size * 1.25
    sc.render.filepath = os.path.join(out, "_o_%02d.png" % i)
    bpy.ops.render.render(write_still=True)
open(os.path.join(out, "orientation_index.txt"), "w", encoding="utf8").write(
    "\n".join("%d %s" % (i, m) for i, m in enumerate(models)) + "\n\nNON IMPORTÉS :\n" +
    "\n".join("%s : %s" % x for x in missing))
print("planche faite ;", len(missing), "non importés")
