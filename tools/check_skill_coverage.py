"""Contrôle de NON-PERTE de la refonte : chaque ligne utile de l'ancien SKILL.md (étiquette git avant-refonte-v2)
doit se retrouver mot pour mot dans le nouveau SKILL.md, un module ou une fiche de référence.
Usage : python tools/check_skill_coverage.py <ancien SKILL.md> <racine du skill>   -> code 0 si rien n'est perdu."""
import glob
import os
import sys

old, root = sys.argv[1], sys.argv[2]
corpus = ""
for p in [os.path.join(root, "SKILL.md")] + glob.glob(os.path.join(root, "modules", "*.md")) + \
        glob.glob(os.path.join(root, "reference", "*.md")):
    corpus += open(p, encoding="utf-8").read() + "\n"
norm = lambda s: " ".join(s.split())
corpus_n = norm(corpus)
missing = []
for ln in open(old, encoding="utf-8").read().split("\n"):
    t = norm(ln)
    if not t or t.startswith("#") or t.startswith("---") or t in ("```",) or len(t) < 12 \
            or t.startswith("description:"):        # la description du frontmatter est réécrite volontairement
        continue                                  # titres, séparateurs, lignes trop courtes : non significatifs
    if t not in corpus_n:
        missing.append(ln)
print(f"lignes perdues : {len(missing)}")
for m in missing[:40]:
    print("  -", m[:150])
sys.exit(1 if missing else 0)
