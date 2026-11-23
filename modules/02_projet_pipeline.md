# Architecture d'un projet et pipeline

## 1. Architecture du projet
```
projet/
  generator/   build_map.py (VMF via srctools), zones.py (salles = "spaces" en boîtes), entities.py (logique),
               props.py / dressing.py / kit.py (habillage), fx.py (effets), minigames.py, optim.py, nodes.py, areaportals.py
  tools/       compile.ps1, make_sounds.py, make_signs.py, embed_content.py, extract_workshop.py, diag.py, bench.ps1, package_map.ps1
  addons/      addon de test (tournée, bench) — JAMAIS publié ; addon de la map (bsp + addon.json, zéro Lua)
  compile_game/ profil de compilation (gameinfo + cfg/mount.cfg qui monte les packs extraits)
  maps_src/ logs/ docs/ shots/
```
Principe : **on ne touche jamais le .vmf à la main**, tout vient du générateur (régénérable, versionnable).
Si l'utilisateur veut passer sur Hammer, lui expliquer que la régénération écraserait ses retouches.
