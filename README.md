# Compétence « gmod-map » — installation

Cette compétence apprend à Claude à créer de A à Z une map Garry's Mod d'event (générée en Python, compilée,
vérifiée en jeu, optimisée pour ~100 joueurs, logique sans Lua, effets, publication Workshop).
Elle contient la méthode (`SKILL.md`) et un projet complet qui fonctionne comme exemple (`reference/`).

---

## 1. Ce qu'il faut sur le PC

| Logiciel | Pourquoi | Où le trouver |
|---|---|---|
| **Windows 10/11** | les outils de compilation de Gmod sont pour Windows | — |
| **Claude Code** (application Claude de bureau, onglet Code, ou `claude` en terminal) | c'est lui qui génère, compile et teste la map | claude.com/claude-code |
| **Garry's Mod** (Steam) | le jeu + ses outils de compilation (`vbsp`, `vvis`, `vrad`, `bspzip` dans `GarrysMod\bin\`) | Steam |
| **Python 3.10 ou plus** + **srctools** + **Pillow** | le générateur de map et les textures | python.org, puis `pip install srctools pillow` |
| **Blender** (4.x ou 5.x) + extension **Plumber** | aperçus de la map avant compilation, allègement des props | blender.org ; Plumber : Édition > Préférences > Get Extensions > « Plumber » |
| **Git** (conseillé) | sauvegarde avant chaque grosse modification | git-scm.com |
| **gmpublisher** (pour publier) | publier / mettre à jour la map sur le Workshop | github.com/WilliamVenner/gmpublisher |

Facultatif : **SteamCMD** (serveur dédié de test pour le bench à 100 joueurs). Claude demandera avant d'installer quoi que ce soit.

Pendant l'installation de Python, cocher **« Add python.exe to PATH »**. Vérifier ensuite dans un terminal :
```
python --version
python -c "import srctools, PIL; print('ok')"
```

---

## 2. Installer la compétence

### Avec Claude Code (recommandé : seul moyen de compiler et tester la map)
1. Le plus simple, dans un terminal :
   ```
   git clone https://github.com/aissa59330/gmod-map-skill "%USERPROFILE%\.claude\skills\gmod-map"
   ```
   (ou bouton **Code > Download ZIP**, dézipper et renommer le dossier en `gmod-map`).
2. Sinon, copier le dossier `gmod-map` dans :
   ```
   C:\Users\<ton nom>\.claude\skills\
   ```
   Résultat attendu : `C:\Users\<ton nom>\.claude\skills\gmod-map\SKILL.md`
3. Redémarrer Claude Code.
4. Vérifier : taper `/gmod-map` dans une conversation, ou simplement « je veux faire une map Gmod ».

### Avec claude.ai (navigateur) — méthode seulement
Paramètres > Fonctionnalités > Compétences > importer le zip.
Claude aura la méthode mais ne pourra **ni compiler ni lancer Gmod** sur ton PC.

---

## 3. Démarrer un projet

1. Créer un **dossier de projet durable** à chemin court, par exemple `C:\Maps\ma_map` (pas dans Téléchargements ni
   dans un dossier temporaire : Windows peut le vider, et Source ne lit pas les chemins de plus de 260 caractères).
2. Ouvrir Claude Code **dans ce dossier**.
3. Décrire la map : thème, nombre de joueurs, durée, phases / objectifs, règles du serveur (Lua autorisé ou non,
   nombre maximum de packs Workshop, taille maximum), packs de textures/props souhaités.
4. Claude prépare le projet à partir de `reference/` en l'adaptant, puis enchaîne :
   générer → aperçu Blender → compiler → tester en jeu → corriger.

**Conseil :** commencer par une **petite map** (2-3 zones, 1 objectif) pour valider l'installation.

---

## 4. Chemins à adapter

Le code de `reference/` vient d'un vrai projet. Les chemins personnels ont été remplacés par `<UTILISATEUR>` :
- `reference/tools/content_paths.txt` : dossiers des packs Workshop extraits (`tools/extract_workshop.py` les crée) ;
- `reference/tools/compile.ps1` : dossier du contenu embarqué ;
- `reference/tools/bench_server.ps1` et `check_server.ps1` : serveur dédié de test (`C:\gn_srcds` par défaut) ;
- outils Blender (`planche_orientation.py`, `facades_blender.py`) : dossier des packs extraits, variable d'environnement
  `GMOD_PACKS` (par défaut `C:\gn_content`).
Le dossier de Garry's Mod par défaut est `C:\Program Files (x86)\Steam\steamapps\common\GarrysMod` ; s'il est ailleurs,
le dire à Claude. Claude adapte tout ça lui-même au début du projet.

---

## 5. Ce que contient `reference/`

| Dossier / fichier | Rôle |
|---|---|
| `generator/` | générateur complet de « Opération Givre Noir » (salles en boîtes, logique de phases, effets, mini-jeux) |
| `generator_tf/` | modules de style « Vexis » / ville vivante (Triple Front) |
| `generator_jabiim/` | terrain ouvert + **moteur d'intérieurs** (`interieurs.py`) : pièces typées, compositions, validation, accès |
| `tools/` | compilation, contenu embarqué, LOD, bench FPS / serveur, **contrôle des trous** (`check_server.ps1`), **photos en jeu** (`photos_jeu.ps1`), plans de pièces, planche d'orientation et façades Blender, `static_ok.py` |
| `addons/` | addons de TEST seulement (tournée, bench, `jb_check`, `jb_photos`, `jb_fps`) — jamais à publier |
| `interieurs.md`, `mesures.md`, `style_vexis.md`, `publication.md`, `METHODE_BENCH_SERVEUR.md`, `PROMPTS.md` | fiches détaillées lues par Claude au besoin |

---

## 6. Ton rôle pendant le projet

- **Tester en jeu** et envoyer des captures (F12) + la position (`getpos` dans la console) de ce qui ne va pas.
- **Fermer Garry's Mod** quand Claude veut lancer ses propres tests (il ne fermera jamais ton jeu à ta place).
- Valider les étapes importantes (installation d'un logiciel, publication).
- Surveiller le quota : une grosse map demande beaucoup d'allers-retours ; tu peux fixer une limite à Claude.

---

## 7. Publier

1. Claude prépare le dossier de l'addon (`.bsp` + `addon.json`, sans Lua) et une miniature JPG 512×512.
2. gmpublisher : **Publish** la première fois, puis **Update** sur le même addon pour les mises à jour
   (sinon un nouvel ID est créé).
3. Sur la page Steam : cocher les packs en « éléments requis », ajouter les crédits des auteurs des packs.
4. Ne jamais publier les addons de test (`*_devtour`, `*_bench`) : ils contiennent du Lua de test.

---

Méthode issue des maps « Opération Givre Noir », Vexis, Triple Front et Battle of Jabiim (Just_Vortex).
Licence : CC BY 4.0 (voir `LICENSE`) — réutilisation libre avec mention de l'auteur. Aucun modèle, aucune texture ni aucun
son d'autres créateurs n'est inclus ; le contenu des packs Workshop reste la propriété de leurs auteurs.
