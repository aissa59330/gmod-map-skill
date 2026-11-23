"""ÉTAT DU PROJET : mémoire de production compacte (reprendre une map sans relire l'historique).
Deux fichiers à la racine du projet : etat_projet.json (machine) et journal.md (une ligne par itération).

  python tools/etat.py init <dossier> --map rp_x --theme "..."      crée les deux fichiers (sans écraser)
  python tools/etat.py show <dossier>                               résumé de 10-15 lignes à lire en début de session
  python tools/etat.py version <dossier> v3 "ce qui a changé" [--audit rapport.json] [--score score.json]
  python tools/etat.py decision <dossier> "décision prise avec l'utilisateur"
  python tools/etat.py todo <dossier> "reste à faire" | done <dossier> <n°>"""
import argparse
import datetime
import json
import os
import sys

MODELE = {"map": "", "theme": "", "cree_le": "", "version": "v0", "etape_pipeline": "1 cadrage",
          "brief": {}, "decisions": [], "reste_a_faire": [], "versions": [], "points_de_vue": [],
          "benchmark": {"points": [], "protocole": "3 passages, médiane, mêmes réglages, PC au repos"}}


def path(d, f):
    return os.path.join(d, f)


def load(d):
    p = path(d, "etat_projet.json")
    if not os.path.exists(p):
        sys.exit(f"pas d'état dans {d} : lancer « etat.py init » d'abord")
    return json.load(open(p, encoding="utf-8"))


def save(d, e):
    json.dump(e, open(path(d, "etat_projet.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def log(d, line):
    with open(path(d, "journal.md"), "a", encoding="utf-8") as f:
        f.write(f"- {datetime.date.today().isoformat()} · {line}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["init", "show", "version", "decision", "todo", "done"])
    ap.add_argument("dir")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--map", default="")
    ap.add_argument("--theme", default="")
    ap.add_argument("--audit")
    ap.add_argument("--score")
    a = ap.parse_args()
    d = a.dir
    if a.cmd == "init":
        if os.path.exists(path(d, "etat_projet.json")):
            sys.exit("état déjà présent : rien écrasé")
        e = dict(MODELE, map=a.map, theme=a.theme, cree_le=datetime.date.today().isoformat())
        save(d, e)
        with open(path(d, "journal.md"), "w", encoding="utf-8") as f:
            f.write(f"# Journal — {a.map}\n\n")
        log(d, f"projet créé ({a.theme})")
        print("état créé")
        return
    e = load(d)
    if a.cmd == "show":
        print(f"PROJET {e['map']} — {e['theme']} · version {e['version']} · étape {e['etape_pipeline']}")
        for v in e["versions"][-3:]:
            s = v.get("score", {}).get("global", "?")
            pl = v.get("audit", {}).get("plans_pct", "?")
            print(f"  {v['version']} ({v['date']}) : {v['note']} · score {s} · plans {pl} %")
        print("  décisions :", "; ".join(e["decisions"][-5:]) or "—")
        print("  reste à faire :")
        for i, t in enumerate(e["reste_a_faire"], 1):
            print(f"   {i}. {t}")
        print(f"  points de vue photo : {len(e['points_de_vue'])} · points de benchmark : {len(e['benchmark']['points'])}")
    elif a.cmd == "version":
        ver, note = a.args[0], " ".join(a.args[1:])
        v = {"version": ver, "date": datetime.date.today().isoformat(), "note": note}
        if a.audit:
            r = json.load(open(a.audit, encoding="utf-8"))
            v["audit"] = {"plans_pct": r["limites"]["plans"]["pct"], "sommets_pct": r["limites"]["sommets"]["pct"],
                          "props": r["props_statiques"].get("total"), "corrections": r["corrections"]}
        if a.score:
            v["score"] = json.load(open(a.score, encoding="utf-8"))
        e["versions"].append(v)
        e["version"] = ver
        log(d, f"{ver} : {note}")
    elif a.cmd == "decision":
        e["decisions"].append(" ".join(a.args))
        log(d, "décision : " + " ".join(a.args))
    elif a.cmd == "todo":
        e["reste_a_faire"].append(" ".join(a.args))
    elif a.cmd == "done":
        t = e["reste_a_faire"].pop(int(a.args[0]) - 1)
        log(d, "fait : " + t)
    save(d, e)


if __name__ == "__main__":
    main()
