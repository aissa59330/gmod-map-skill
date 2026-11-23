# Aperçus Blender

## 4 bis. Prévisualisation Blender (AVANT de compiler, à chaque grosse modification du tracé)
- Outils : **Blender** (4.x/5.x) + addon **Plumber** (import VMF/MDL ; demander à l'utilisateur avant d'installer).
- Commande : `blender -b -P tools/preview_blender.py -- maps_src/<map>.vmf shots/iter_N/blender/`
  (référence : `reference/tools/preview_blender.py`). Opérateur d'import : `bpy.ops.import_scene.plumber_vmf`
  (le lister dans `dir(bpy.ops.import_scene)` ; activer l'extension `bl_ext.user_default.plumber` si besoin).
  Plumber refuse le bloc `editor` au niveau du world : en importer une copie nettoyée. Échelle Plumber : 0,01.
- Rendus : 1 vue de dessus orthographique de toute la map + 1 vue par zone. **Regarder les images** :
  proportions, connexions, salles qui se chevauchent, 3 voies par zone, ≥ 3 entrées par objectif.
- Complément rapide sans Blender : plan SVG de dessus (`reference/tools/plan_svg.py`, lit le .json exporté par le générateur).
- Blender sert aussi aux **LOD des props** : import MDL (Plumber) → Decimate → export SMD → studiomdl
  (`reference/tools/make_lod_props.py`, puis `fix_lod_qc.py` pour les $cdmaterials).
- Ensuite seulement : compilation, puis tournée en jeu (les rendus Blender ne remplacent pas la vérification en jeu).
