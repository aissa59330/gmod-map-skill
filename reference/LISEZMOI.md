# Index du code de référence

Code de référence complet et fonctionnel : `reference/` (générateur `reference/generator/`, outils `reference/tools/`,
addons de test `reference/addons/`, ancien CLAUDE.md du projet `reference/CLAUDE_givre_noir.md`),
moteur d'intérieurs `reference/generator_jabiim/`. Fiches : `reference/interieurs.md`, `mesures.md`, `style_vexis.md`, `publication.md`.

⚠ Ce sont des **sources d'outils**, pas des modèles de qualité visuelle : ne pas reproduire l'aspect de ces maps
(voir « Niveau visé » dans `SKILL.md`).

| Dossier / fichier | Rôle | État |
|---|---|---|
| `generator/` | Givre Noir : salles en boîtes, logique de 11 phases, effets, mini-jeux (map intérieure) | autonome ; `prop_bounds_packs.json` absent (le régénérer avec `tools/model_bounds.py`), `dressing.py` démarre sans |
| `generator_tf/` | Triple Front / Vexis : restyle, immeubles accessibles, ville en bataille, monde vivant | autonome (kit/geom de Triple Front + données Vexis dans `vexis_data/`) ; imports testés |
| `generator_jabiim/` | terrain ouvert à déplacements + **moteur d'intérieurs** (`interieurs.py`) + export avec props inclinés | autonome, version v27 (puits, ville, remplissage) ; imports testés, moteur d'intérieurs testé |
| `tools/` | compilation, contenu embarqué, LOD, bench FPS / serveur, contrôle des trous, photos en jeu, planches Blender | certains outils citent `givre_noir` : passer le nom de map en paramètre |
| `addons/` | addons de TEST seulement (tournée, bench, `jb_check`, `jb_photos`, `jb_fps`) — jamais à publier | — |
| `*.md` | fiches détaillées lues au besoin (voir la table de routage de `SKILL.md`) | — |
