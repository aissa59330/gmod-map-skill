"""Découpe l'ancien SKILL.md (monolithique) en modules chargés à la demande, SANS PERTE : chaque section est
recopiée telle quelle dans le module qui la reçoit (les modules s'enrichissent ensuite).
Usage unique : python tools/split_skill.py <ancien SKILL.md> <dossier modules/>
Le contrôle de non-perte est fait par tools/check_skill_coverage.py."""
import os
import re
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
lines = open(SRC, encoding="utf-8").read().split("\n")

# en-tête de section -> module (fichier, titre du module)
ROUTE = [
    ("## 0.", "01_cadrage.md"),
    ("## 1. Architecture", "02_projet_pipeline.md"),
    ("## 1 bis.", "03_level_design.md"),
    ("## 2. Construction", "08_source_technique.md"),
    ("## 3. Logique", "09_logique_event.md"),
    ("## 4. Effets", "10_ambiance_effets.md"),
    ("## 4 bis.", "12_apercus_blender.md"),
    ("## 5. Compilation", "13_compilation.md"),
    ("## 6. Optimisation", "14_performance.md"),
    ("## 6 bis.", "14_performance.md"),
    ("## 6 ter.", "05_architecture_villes.md"),
    ("## 6 quater.", "06_interieurs.md"),
    ("## 7. Vérification", "11_controle_qualite.md"),
    ("## 8. Packs", "15_publication.md"),
    ("## 9. Façon", "00_regles_utilisateur.md"),
]
# la section 10 (leçons) est ventilée par thème
SPLIT10 = {"**Budget de plans": "14_performance.md", "**Terrain": "04_terrain_biomes.md",
           "**Génération": "08_source_technique.md"}

TITLES = {
    "00_regles_utilisateur.md": "Règles de travail avec l'utilisateur (rappel détaillé)",
    "01_cadrage.md": "Cadrage : questions de départ et contraintes",
    "02_projet_pipeline.md": "Architecture d'un projet et pipeline",
    "03_level_design.md": "Level design : structure, circulation, lignes de vue",
    "04_terrain_biomes.md": "Terrain ouvert et biomes",
    "05_architecture_villes.md": "Architecture, style et villes",
    "06_interieurs.md": "Bâtiments explorables et intérieurs",
    "08_source_technique.md": "Construction Source (générateur, géométrie, props)",
    "09_logique_event.md": "Logique d'event 100 % map (sans Lua)",
    "10_ambiance_effets.md": "Ambiance et effets",
    "11_controle_qualite.md": "Contrôle qualité",
    "12_apercus_blender.md": "Aperçus Blender",
    "13_compilation.md": "Compilation",
    "14_performance.md": "Performance (100 joueurs, PNJ) et budgets",
    "15_publication.md": "Packs requis et publication",
}

out = {}
cur = None
sub = None
for ln in lines[14:]:                       # après l'en-tête du skill (frontmatter + intro)
    if ln.startswith("## "):
        sub = None
        cur = next((m for (p, m) in ROUTE if ln.startswith(p)), None)
        if ln.startswith("## 10."):
            cur = "__10__"
        if cur and cur != "__10__":
            out.setdefault(cur, []).append(re.sub(r"^## ", "## ", ln))
        continue
    if cur == "__10__":
        for k, m in SPLIT10.items():
            if ln.startswith(k):
                sub = m
                out.setdefault(sub, []).append("\n## Leçons vécues (Jabiim v23 → v28)")
        if sub:
            out[sub].append(ln)
        continue
    if cur:
        out[cur].append(ln)

os.makedirs(OUT, exist_ok=True)
for m, body in out.items():
    with open(os.path.join(OUT, m), "w", encoding="utf-8") as f:
        f.write(f"# {TITLES[m]}\n\n" + "\n".join(body).strip() + "\n")
print("\n".join(f"{m}: {len(b)} lignes" for m, b in sorted(out.items())))
