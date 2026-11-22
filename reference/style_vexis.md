# Niveau « Vexis » : style, level design vivant, pièges de géométrie

Modules de référence : `reference/generator_tf/` (vexis_style.py, city_style.py, rp_style.py, life.py) et
`reference/tools/` (embed_content_tf.py, shrink_vtf.py, compile_embed.ps1, make_presentation.py, make_banner_event.py).
Projets complets (non inclus) : `gmod_arsenal_vexis` (terrain ouvert à déplacements, contenu embarqué) et
`gmod_triple_front` (3 secteurs empilés, style Vexis, ville vivante) — tous deux en git.
- **Restyler une map existante sans tout réécrire** : un module `MAT_REMAP` (texture d'origine → texture du style,
  appliqué à l'export sur toutes les faces) + `PROP_SWAP` (modèle d'origine → modèle du style, appliqué AU PLACEMENT
  pour que les contrôles de collision utilisent la taille du nouveau modèle) + bounds du projet modèle fusionnées +
  versions LOD réutilisées (`models/vxl/...`). Interrupteur `ENABLED` pour revenir en arrière.
- **Immeubles accessibles** (demande récurrente : « trop de bâtiments inaccessibles ») : socle creux praticable de 1–2
  niveaux EN BRUSHES WORLD (garde l'occultation de l'ancien bloc plein) + tour pleine en retrait (terrasse devant,
  trémie d'escalier laissée libre) + couronnement varié (champignon, gradins, pyramide, toit technique) + auvents.
  Ça a fait passer Triple Front de 2 450 à 4 000 zones de visibilité (culling plus fin) mais +37 % de faces.
- **Limite de 65 536 sommets (vbsp « Too many unique verts »)** : vite atteinte avec des bâtiments creux à fenêtres.
  Couper d'abord ce qui rapporte peu (corniches/bandeaux, fenêtres des petits bâtiments, prismes décoratifs) ;
  vérifier la marge après compilation (`len(BSP(...).vertexes)`, viser < 85 %).
- **La ville doit raconter quelque chose** (pas des props au hasard) : ligne alliée (barrages en chicane avec passage
  ≥ 256, murets, munitions derrière), no man's land (épaves le long des voies, pas au milieu), ancienne ligne ennemie
  (barricades, bannières, capsules), éboulis en pente douce qui coupent la moitié d'une rue. Tout placé aux carrefours.
- **Lieux RP nommés** (camp avancé, poste médical, relais radio, convoi détruit, avant-poste ennemi) + hameaux et silos
  pour casser les grands vides. Les silos/pylônes pleins en world servent aussi d'occulteurs. ⚠ Les poser AVANT la
  végétation et les couverts aléatoires (sinon presque aucun emplacement libre : 3/17 posés au lieu de 21).
  Contrôle d'emprise : ni route, ni obstacle, sol plat sous les 9 points de l'emprise.
- **Monde vivant** avec plafonds par secteur (5 fumées, 6 feux, 3 étincelles, 6 néons clignotants, 8 points
  d'artillerie) : les modules marquent les endroits qui ont une raison d'être animés (épave → feu, éboulis → fumée,
  relais → étincelles), un module unique crée les entités. Bruits de combat et avions via logic_case + logic_timer
  aléatoire ; ambiance de fond en boucles à rayon limité (on n'entend pas les autres secteurs empilés).
- **Matériaux de MODÈLE sur des brushes** (`VertexLitGeneric`, `$model 1`, ex. `phoenix_storms/road`) : pas de lightmap,
  éclairage faux, reflets `$envmap` bizarres sans env_cubemap → créer un .vmt maison `LightmappedGeneric` qui reprend
  le même `$basetexture` (embarqué : < 1 Ko), dossier de contenu maison ajouté à content_paths.txt.
  Vérifier le shader de toute texture prise dans un pack de props avant de la mettre sur un mur ou un sol.
- **Photos de présentation automatiques** : addon temporaire (SetPos/SetEyeAngles côté serveur, `render.Capture`
  jpeg côté client dans `data/`, HUD caché), Gmod lancé fenêtré `-windowed -w 1920 -h 1080 -noborder -novid
  +maxplayers 1 +map <map>` ; noter le PID, ne fermer QUE ce PID (vérifier sa ligne de commande ; « Stop-Process gmod »
  est refusé à juste titre). Choisir les points de vue depuis le .json (infos, positions des props), regarder la
  planche contact, écarter les vues ratées (caméra dans une falaise), puis miniature 512 + bannière 1920×1080.
  Retirer l'addon et `data/<dossier>` à la fin.
