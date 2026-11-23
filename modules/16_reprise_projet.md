# Reprendre un projet (sans relire l'historique)

1. `python <skill>/tools/etat.py show <projet>` : version, 3 dernières versions (score, plans), décisions, reste à faire.
   C'est la SEULE lecture obligatoire pour reprendre. Ne pas relire les logs bruts ni tout le générateur.
2. Si l'état n'existe pas (ancien projet) : `etat.py init <projet> --map <nom> --theme "..."`, puis le remplir en
   recensant : `git log --oneline | head`, dernier BSP (`tools/audit_bsp.py`), budget (`tools/budget.py`), et demander à
   l'utilisateur (QCM) ce qui reste à faire.
3. Pendant le travail : `etat.py decision` à chaque choix de l'utilisateur, `etat.py version <vN> "note" --audit r.json`
   après chaque compilation, `etat.py todo` / `done`. Commit git à chaque version.
4. Le journal (`journal.md`) est la mémoire courte : une ligne par itération, lisible par l'utilisateur.
Ce qui est dans l'état ne se ré-analyse pas : on ne refait pas une analyse dont le résultat est déjà noté.
