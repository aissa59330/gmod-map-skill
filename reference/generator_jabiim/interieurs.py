"""MOTEUR D'INTÉRIEURS : pièces typées, compositions par rôle, placement validé, tirage stable.

Repère LOCAL du bâtiment (x vers la droite de la façade, y vers le fond, la façade est en y négatif) ; W(lx, ly) donne
le point monde et byaw la rotation du bâtiment. Chaque pièce est un rectangle intérieur (faces internes des murs).

Règles appliquées à chaque meuble AVANT de le poser :
  - entièrement dans la pièce (2 u de jeu contre les murs) ;
  - hors zones réservées : passages de portes (dégagement de 56 u des deux côtés), escaliers et trémies, fenêtres pour
    tout meuble plus haut que l'allège ;
  - sans recouper un autre meuble du même niveau (les objets « posés sur » ne touchent que leur support) ;
  - posé au sol (origine relevée de -min.z du modèle) ou sur le dessus réel de son support (max.z du support) ;
  - la pièce reste traversable : toutes ses portes restent reliées entre elles et au moins 35 % du sol reste accessible
    (inondation sur une grille de 16 u, obstacles gonflés du rayon d'un joueur). Sinon le meuble est refusé.
Contrôle final : une pièce dont une porte est inaccessible fait échouer la génération (RuntimeError).
Tirage stable : un générateur aléatoire par bâtiment et par pièce (empreinte de la position), indépendant du reste.
"""
import math
import random
import zlib

from vx import BOUNDS

MD = "models/"
NIK = MD + "niksacokica/"
# Avant de chaque modèle : par convention Source l'avant est +X. Exceptions relevées sur la planche de contrôle
# (tools/planche_orientation.py) : rotation à ajouter pour que l'avant du modèle regarde vers +X local.
ORIENT = {MD + "props_c17/shelfunit01a.mdl": -90,          # rayonnages côté +Y (planche du 22/11/2026 ; modèle physique, plus utilisé)
          NIK + "tech/tech_city_workbench.mdl": -90}       # plan de travail et écrans côté +Y
DOOR_CLEAR = 56
CELL = 16
STATS = {"meubles": 0, "refus": {}, "pieces": 0}
DUMP = []           # relevé des pièces (vues en plan de contrôle)


def srng(*key):
    """Générateur stable (même résultat à chaque compilation) pour une clé donnée (bâtiment, pièce)."""
    k = ",".join(str(round(x)) if isinstance(x, float) else str(x) for x in key)
    return random.Random(zlib.crc32(k.encode()))


def foot(model, a):
    """Empreinte locale (x0, y0, x1, y1) du modèle tourné de a degrés autour de son origine."""
    b = BOUNDS[model]
    (x0, y0, _), (x1, y1, _) = b["min"], b["max"]
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    xs, ys = [], []
    for px in (x0, x1):
        for py in (y0, y1):
            xs.append(px * c - py * s)
            ys.append(px * s + py * c)
    return (min(xs), min(ys), max(xs), max(ys))


def overlap(a, b, m=0):
    return a[0] < b[2] - m and b[0] < a[2] - m and a[1] < b[3] - m and b[1] < a[3] - m


class Room:
    def __init__(self, role, rect, z, doors, keep=(), tall_keep=(), key=(), loot=False, ceil=224, solid=()):
        self.role, self.rect, self.z, self.ceil = role, rect, z, ceil
        self.doors = list(doors)          # rectangles de passage (dans la pièce)
        self.keep = list(keep)            # zones sans meuble mais où l'on marche (paliers, départs d'escalier)
        self.solid = list(solid)          # zones où l'on ne marche pas (volée d'escalier, trémie)
        self.tall_keep = list(tall_keep)  # zones interdites aux meubles hauts (devant les fenêtres)
        self.placed = []                  # (modèle, lx, ly, la, rect, z_dessus)
        self.rng = srng(*key)
        self.rng_key = key
        self.loot = loot


def _free(room, extra):
    """Vrai si toutes les portes restent reliées et qu'au moins 35 % du sol reste accessible."""
    x0, y0, x1, y1 = room.rect
    nx, ny = max(1, int((x1 - x0) // CELL)), max(1, int((y1 - y0) // CELL))
    obst = [p[4] for p in room.placed if p[6]] + extra
    blocked, kept = set(), 0
    for i in range(nx):
        for j in range(ny):
            cx, cy = x0 + (i + 0.5) * CELL, y0 + (j + 0.5) * CELL
            pr = (cx - 14, cy - 14, cx + 14, cy + 14)       # demi-largeur d'un joueur (16) moins la tolérance
            if any(overlap(pr, o) for o in room.solid):
                blocked.add((i, j))
                kept += 1
            elif any(overlap(pr, o) for o in obst):
                blocked.add((i, j))
    starts = []
    for d in room.doors:
        cx, cy = (max(d[0], x0) + min(d[2], x1)) / 2, (max(d[1], y0) + min(d[3], y1)) / 2
        starts.append((min(nx - 1, max(0, int((cx - x0) // CELL))), min(ny - 1, max(0, int((cy - y0) // CELL)))))
    if not starts:
        return True
    seen, st = {starts[0]}, [starts[0]]
    while st:
        i, j = st.pop()
        for (a, b) in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if 0 <= a < nx and 0 <= b < ny and (a, b) not in seen and (a, b) not in blocked:
                seen.add((a, b))
                st.append((a, b))
    return all(s in seen for s in starts) and len(seen) >= 0.35 * (nx * ny - kept)


def place(room, models, spot, la=0.0, on=None, tall=None, why=None, solid=True):
    """Essaie de poser un des modèles. spot = (lx, ly) centre voulu. Retourne l'index du meuble posé ou None."""
    if isinstance(models, str):
        models = [models]
    models = [m for m in models if m in BOUNDS and BOUNDS[m].get("static", True)]
    if not models:
        STATS["refus"]["absent"] = STATS["refus"].get("absent", 0) + 1
        return None
    m = room.rng.choice(models)
    a = (la + ORIENT.get(m, 0)) % 360
    f = foot(m, a)
    lx, ly = spot
    r = (lx + f[0], ly + f[1], lx + f[2], ly + f[3])
    b = BOUNDS[m]
    h = b["max"][2] - b["min"][2]
    x0, y0, x1, y1 = room.rect
    reason = None
    if on is not None:                                           # posé sur un meuble : dans l'emprise du dessus
        host = room.placed[on]
        hr = host[4]
        if not (r[0] >= hr[0] + 1 and r[2] <= hr[2] - 1 and r[1] >= hr[1] + 1 and r[3] <= hr[3] - 1):
            reason = "deborde_support"
        z = host[5] - b["min"][2]
    else:
        z = room.z - b["min"][2]
        if r[0] < x0 + 2 or r[2] > x1 - 2 or r[1] < y0 + 2 or r[3] > y1 - 2:
            reason = "hors_piece"
        elif any(overlap(r, k) for k in room.keep + room.solid + room.doors):
            reason = "passage"
        elif (tall if tall is not None else h > 80) and any(overlap(r, k) for k in room.tall_keep):
            reason = "fenetre"
        elif any(overlap(r, p[4], 1) for p in room.placed if p[6]):
            reason = "meuble"
        elif h > room.ceil - 8:
            reason = "plafond"
        elif not _free(room, [r]):
            reason = "acces"
    if reason:
        STATS["refus"][reason] = STATS["refus"].get(reason, 0) + 1
        return None
    room.placed.append((m, lx, ly, a, r, z + b["max"][2], on is None and solid, why))
    room.zs = getattr(room, "zs", [])
    room.zs.append(z)
    return len(room.placed) - 1


def along(room, side, t, depth_of=None):
    """Point contre un mur : side 'N' (fond), 'S' (façade), 'E' (+x), 'O' (-x) ; t de 0 à 1 le long du mur.
    Retourne (lx, ly, la) : la = rotation locale pour que l'avant (+X modèle) regarde vers l'intérieur."""
    x0, y0, x1, y1 = room.rect
    if side == "N":
        return x0 + t * (x1 - x0), y1, 270
    if side == "S":
        return x0 + t * (x1 - x0), y0, 90
    if side == "E":
        return x1, y0 + t * (y1 - y0), 180
    return x0, y0 + t * (y1 - y0), 0


def against(room, models, side, t, gap=2, **kw):
    """Meuble dos au mur : recule le centre de sa demi-profondeur (empreinte réelle), essaie plusieurs positions."""
    if isinstance(models, str):
        models = [models]
    ts = [t] + [min(0.95, max(0.05, t + d)) for d in (0.12, -0.12, 0.25, -0.25, 0.4, -0.4)]
    for tt in ts:
        lx, ly, la = along(room, side, tt)
        good = [m for m in models if m in BOUNDS]
        if not good:
            return None
        m0 = room.rng.choice(good)
        f = foot(m0, (la + ORIENT.get(m0, 0)) % 360)
        if side == "N":
            ly = ly - gap - f[3]
        elif side == "S":
            ly = ly + gap - f[1]
        elif side == "E":
            lx = lx - gap - f[2]
        else:
            lx = lx + gap - f[0]
        i = place(room, [m0], (lx, ly), la, **kw)
        if i is not None:
            return i
    return None


def beside(room, host, models, **kw):
    """Meuble posé juste à côté d'un autre (table de chevet contre le lit), même alignement."""
    if host is None:
        return None
    m, lx, ly, a, r, *_ = room.placed[host]
    for k in room.rng.sample([0, 1], 2):
        for mm in room.rng.sample(models, len(models)):
            if mm not in BOUNDS:
                continue
            f = foot(mm, (a + ORIENT.get(mm, 0)) % 360)
            horiz = abs(math.cos(math.radians(a))) < 0.5            # meuble dos à un mur N/S : on glisse en x
            if horiz:
                x = r[2] + 4 - f[0] if k else r[0] - 4 - f[2]
                y = (r[1] - f[1]) if math.sin(math.radians(a)) > 0 else (r[3] - f[3])
            else:
                y = r[3] + 4 - f[1] if k else r[1] - 4 - f[3]
                x = (r[0] - f[0]) if math.cos(math.radians(a)) > 0 else (r[2] - f[2])
            i = place(room, [mm], (x, y), a, **kw)
            if i is not None:
                return i
    return None


def slots(room, side, spacing):
    """Positions régulières (0..1) le long d'un mur, une tous les « spacing » unités."""
    x0, y0, x1, y1 = room.rect
    L = (x1 - x0) if side in "NS" else (y1 - y0)
    n = max(1, int(L // spacing))
    return [(k + 0.5) / n for k in range(n)]


def corner(room, models, **kw):
    for side, t in room.rng.sample([("N", 0.08), ("N", 0.92), ("S", 0.08), ("S", 0.92)], 4):
        i = against(room, models, side, t, **kw)
        if i is not None:
            return i
    return None


def on_top(room, host, models, n=1):
    """Petits objets posés sur le dessus réel du support."""
    if host is None:
        return
    hr = room.placed[host][4]
    for _ in range(n):
        for _ in range(6):
            lx = room.rng.uniform(hr[0] + 10, hr[2] - 10)
            ly = room.rng.uniform(hr[1] + 10, hr[3] - 10)
            if place(room, models, (lx, ly), room.rng.uniform(0, 360), on=host) is not None:
                break


def around(room, table, chair, n):
    """Chaises autour d'une table, tournées vers elle."""
    if table is None:
        return
    t = room.placed[table][4]
    cx, cy = (t[0] + t[2]) / 2, (t[1] + t[3]) / 2
    spots = [(t[0] - 22, cy, 0), (t[2] + 22, cy, 180), (cx, t[1] - 22, 90), (cx, t[3] + 22, 270)]
    room.rng.shuffle(spots)
    k = 0
    for (x, y, a) in spots:
        if k >= n:
            break
        if place(room, chair, (x, y), a + room.rng.uniform(-12, 12)) is not None:
            k += 1


def center(room, models, la=0, **kw):
    x0, y0, x1, y1 = room.rect
    for (fx, fy) in ((0.5, 0.5), (0.5, 0.6), (0.5, 0.4), (0.4, 0.5), (0.6, 0.5)):
        i = place(room, models, (x0 + fx * (x1 - x0), y0 + fy * (y1 - y0)), la, **kw)
        if i is not None:
            return i
    return None


# ------------------------------------------------------------------ catalogue (modèles disponibles aux joueurs)
TABLE, CHAIR = NIK + "republic/rep_peasant_table.mdl", NIK + "republic/rep_peasant_chair.mdl"
LAMP = NIK + "republic/rep_peasant_lamp.mdl"
LOCKERS = [MD + "props_lab/lockers.mdl", NIK + "tech/tech_armory_locker.mdl", NIK + "republic/rep_wardrobe.mdl"]
SHELF = NIK + "republic/rep_library_wall_4m_sideways.mdl"   # shelfunit01a : physique seulement (vbsp le supprime)
COUCH = [MD + "props/starwars/chairs/couch01.mdl"]
BEDS = [NIK + "republic/rep_bunk_beds.mdl", MD + "lt_c/sci_fi/bed_bunk.mdl"]
RUG = [NIK + "city/city_plush_rug.mdl", NIK + "city/city_plush_red_rug.mdl"]
STOVE, FRIDGE = MD + "props_c17/furniturestove001a.mdl", MD + "props_wasteland/kitchen_fridge001a.mdl"
COUNTER = [MD + "lt_c/sci_fi/counter_sinks.mdl"]
SINKS = MD + "lt_c/sci_fi/counter_sinks.mdl"
SMALL = [MD + "lt_c/sci_fi/holo_tablet.mdl", NIK + "tech/tech_datapad_01.mdl", NIK + "containers/con_crate_05_closed.mdl"]
DESKTOP = [NIK + "tech/tech_holo_terminal_rep.mdl", MD + "lt_c/sci_fi/holo_tablet.mdl", NIK + "tech/tech_datapad_01.mdl"]
CRATES = [NIK + "containers/con_box_crate_02.mdl", NIK + "containers/con_box_crate_03.mdl", NIK + "republic/rep_crate.mdl",
          NIK + "containers/con_square_crate02.mdl", NIK + "containers/con_box_crate_06.mdl"]
SMALL_CRATES = [NIK + "containers/con_box_crate_01.mdl", NIK + "containers/con_box_crate_05.mdl", NIK + "containers/con_crate_05_closed.mdl"]
BARRELS = [NIK + "tech/tech_mine_barrel.mdl", NIK + "republic/rep_crate.mdl"]
BROKEN = [NIK + "containers/con_crate_04_broken.mdl", NIK + "containers/con_square_crate_broken.mdl",
          NIK + "republic/rep_crate_02_broken.mdl", NIK + "containers/con_rectangle_crate_broken.mdl"]
RUBBLE = [NIK + "ruins/ruins_rubble_01_c.mdl", NIK + "caves/caves_rubble_small_ald_02.mdl"]
BIN = MD + "lt_c/sci_fi/ground_locker_small.mdl"
PALLET = NIK + "republic/rep_pallet_02.mdl"
HOLO, CTABLE = NIK + "tech/tech_holotable_01.mdl", NIK + "republic/rep_computer_table.mdl"
BENCHES = [NIK + "imperial/imp_citadel_bench.mdl", NIK + "city/city_furn_bench_metal.mdl"]
TERM, ARCH = NIK + "tech/tech_imp_comp_terminal.mdl", NIK + "tech/tech_archive_terminal.mdl"
CONSOLE_L, CONSOLE_S = NIK + "tech/tech_console_large_controls.mdl", NIK + "tech/tech_console_wo_solar_panels.mdl"
GREE = NIK + "tech/tech_gree_computer.mdl"
SERVERS = [MD + "props_lab/servers.mdl"]
GEN_LARGE, GEN_CONSOLE = NIK + "republic/rep_generator_plate_large.mdl", MD + "props_lab/generatorconsole.mdl"
TOXIC = NIK + "containers/con_toxicwaste_barrel.mdl"
CRATE_W1, CRATE_W2 = NIK + "containers/crate_weapon_01.mdl", NIK + "containers/crate_weapon_02.mdl"
STOOL = NIK + "city/city_bar_stool.mdl"


# ------------------------------------------------------------------ compositions par type de pièce
def compose(room):
    """Meubles principaux, puis secondaires, puis décoration et objets posés. Pillage crédible si room.loot."""
    g = room.rng
    role = room.role
    keep = lambda p: not (room.loot and g.random() < p)      # pièce pillée : une partie des meubles a disparu
    if role == "salle":
        center(room, RUG, la=90, tall=False, solid=False) if keep(0.5) else None     # le tapis ne gêne ni passage ni meuble
        tb = center(room, TABLE, la=g.choice((0, 90)))
        around(room, tb, CHAIR, g.choice((2, 3, 4)) if not room.loot else 1)
        against(room, COUCH, g.choice("NE"), g.uniform(0.3, 0.7)) if keep(0.4) else None
        sh = against(room, SHELF, g.choice("NO"), g.uniform(0.2, 0.8)) if keep(0.4) else None
        against(room, LOCKERS, "O" if g.random() < 0.5 else "N", 0.15) if keep(0.5) else None
        on_top(room, tb, [LAMP] + SMALL, n=g.randint(1, 2) if keep(0.6) else 0)
        on_top(room, sh, SMALL, n=1)
        corner(room, [BIN] + BARRELS[:1])
        corner(room, SMALL_CRATES + CRATES[:2]) if keep(0.5) else None
    elif role == "cuisine":
        st = against(room, STOVE, "N", 0.2)
        ct = against(room, COUNTER, "N", 0.45)
        against(room, SINKS, "N", 0.7) if keep(0.3) else None
        against(room, FRIDGE, "E", 0.85) if keep(0.5) else None
        tb = center(room, TABLE, la=90)
        around(room, tb, [CHAIR, STOOL], 2 if not room.loot else 1)
        on_top(room, ct, SMALL + [LAMP], n=g.randint(1, 2))
        on_top(room, tb, SMALL, n=1 if keep(0.5) else 0)
        corner(room, BARRELS + SMALL_CRATES)
    elif role == "chambre":
        bed = against(room, BEDS, g.choice("NE"), g.uniform(0.25, 0.75))
        against(room, LOCKERS, g.choice("NO"), g.uniform(0.1, 0.9)) if keep(0.4) else None
        ns = beside(room, bed, SMALL_CRATES) or corner(room, SMALL_CRATES)   # table de chevet contre le lit
        on_top(room, ns, [LAMP], n=1 if keep(0.5) else 0)
        center(room, RUG, tall=False, solid=False) if keep(0.6) and bed is not None else None
        corner(room, CRATES[:3]) if keep(0.3) else None
    elif role == "bureau":
        tb = against(room, TABLE, g.choice("NE"), g.uniform(0.3, 0.7))
        around(room, tb, CHAIR, 1)
        on_top(room, tb, DESKTOP, n=2 if keep(0.5) else 1)
        sh = against(room, SHELF, g.choice("NO"), g.uniform(0.2, 0.8))
        on_top(room, sh, SMALL, n=1)
        against(room, LOCKERS, "N", 0.9) if keep(0.4) else None
        corner(room, SMALL_CRATES)
    elif role == "entree":
        against(room, MD + "props_c17/bench01a.mdl", g.choice("NE"), 0.5) if keep(0.5) else None
        against(room, LOCKERS, "E", 0.2) if keep(0.5) else None
        corner(room, CRATES + BARRELS[:1])
    elif role == "cellier":
        sh = against(room, SHELF, "N", 0.3)
        on_top(room, sh, SMALL_CRATES, n=2)
        c1 = against(room, CRATES[:3], "N", 0.75)
        on_top(room, c1, SMALL_CRATES, n=1)
        corner(room, BARRELS)
        corner(room, BARRELS)
        against(room, NIK + "republic/rep_pallet_02.mdl", "E", 0.4) if keep(0.3) else None
    elif role == "epicerie":
        c1 = center(room, SINKS, la=90)                         # comptoir face à la porte
        on_top(room, c1, DESKTOP[:1] + SMALL, n=2)
        for t in (0.15, 0.4, 0.65, 0.9):
            sh = against(room, [SHELF, NIK + "slum/slum_food_storage_unit.mdl"], "N", t) if keep(0.35) else None
            on_top(room, sh, SMALL_CRATES, n=1)
        against(room, CRATES, "O", 0.6)
        corner(room, BARRELS + CRATES)
        corner(room, SMALL_CRATES)
    elif role == "atelier":
        wb = against(room, NIK + "tech/tech_city_workbench.mdl", "N", 0.5)
        on_top(room, wb, [NIK + "tech/tech_city_workbench_device.mdl"] + SMALL, n=2)
        center(room, MD + "props_vehicles/car002b.mdl", la=0) if keep(0.5) else None
        against(room, MD + "lt_c/sci_fi/generator_portable.mdl", "E", 0.7)
        against(room, LOCKERS, "E", 0.2)
        against(room, SHELF, "O", 0.5)
        corner(room, BARRELS)
        corner(room, CRATES)
    elif role == "stockage":                                     # travée de grange / entrepôt : contre le mur du fond
        def lot(t):
            k = g.random()
            if k < 0.3:
                sh = against(room, SHELF, "N", t)
                on_top(room, sh, SMALL_CRATES, n=2)
            elif k < 0.6:
                c1 = against(room, CRATES[:3] + [NIK + "imperial/imp_crate_02_x04.mdl"], "N", t)
                on_top(room, c1, SMALL_CRATES + CRATES[3:], n=1)
            elif k < 0.8:
                p1 = against(room, PALLET, "N", t)
                on_top(room, p1, CRATES[:3], n=1)
            else:
                against(room, BARRELS, "N", t)
                against(room, BARRELS, "N", t + 0.03)
        for t in slots(room, "N", 190):
            lot(t)
        if room.rect[3] - room.rect[1] > 260:                    # travée profonde : îlot de palettes au milieu, avec passages
            x0, y0, x1, y1 = room.rect
            for k in range(1, int((x1 - x0) // 420)):
                p1 = place(room, [PALLET, NIK + "imperial/imp_crate_02_x04.mdl"], (x0 + k * 420, (y0 + y1) / 2), g.choice((0, 90)))
                on_top(room, p1, CRATES[:3], n=1)
    elif role == "industrie":                                    # atelier de raffinerie : machines contre le mur
        for t in slots(room, "N", 260):
            against(room, [GEN_LARGE, GEN_CONSOLE, MD + "lt_c/sci_fi/generator_portable.mdl", TOXIC], "N", t)
        corner(room, [TOXIC] + BARRELS)
        corner(room, CRATES)
    elif role in ("reunion", "briefing"):                        # table centrale, bancs de part et d'autre, consoles au mur
        tb = center(room, [HOLO] if role == "briefing" else [CTABLE, HOLO], la=0)
        if tb is not None:
            r = room.placed[tb][4]
            cy = (r[1] + r[3]) / 2
            for (x, a) in ((r[0] - 70, 0), (r[2] + 70, 180), (r[0] - 160, 0), (r[2] + 160, 180)):
                place(room, BENCHES, (x, cy), a)
        for side in "NS":
            for t in slots(room, side, 300):
                against(room, [TERM, CONSOLE_S, ARCH] if role == "briefing" else [SHELF, ARCH, LOCKERS[2]], side, t)
        against(room, LOCKERS, "E", 0.5) if keep(0.4) else None
        corner(room, [CRATE_W2] + CRATES[:2])
    elif role in ("archives", "bureau_cmd", "observation"):
        tb = against(room, [TABLE, ARCH], g.choice("NE"), g.uniform(0.3, 0.7))
        around(room, tb, CHAIR, 1)
        on_top(room, tb, DESKTOP, n=2)
        for t in slots(room, "O", 160):
            against(room, (SERVERS + [SHELF]) if role != "bureau_cmd" else LOCKERS + [SHELF], "O", t)
        corner(room, [CRATE_W2, CRATE_W1] if role == "bureau_cmd" else SMALL_CRATES)
        corner(room, SMALL_CRATES)
    elif role in ("controle", "commandement"):                   # pupitres le long des murs, table holo au centre
        for t in slots(room, "N", 260):
            against(room, [CONSOLE_L, CONSOLE_S], "N", t)
        for side in "EO":
            for t in slots(room, side, 320):
                against(room, [TERM, GREE, NIK + "republic/rep_console02.mdl"], side, t)
        if role == "commandement":
            ht = center(room, HOLO, la=0)
            around(room, ht, CHAIR, 2)
        place(room, CHAIR, ((room.rect[0] + room.rect[2]) / 2, room.rect[3] - 120), 90)
        corner(room, CRATES[:2])
    elif role in ("machines", "serveurs"):
        x0, y0, x1, y1 = room.rect
        for side in ("NS" if (x1 - x0) >= (y1 - y0) else "EO"):    # les deux murs les plus longs
            for t in slots(room, side, 150 if role == "serveurs" else 240):
                against(room, SERVERS if role == "serveurs" else [GEN_LARGE, GEN_CONSOLE, TOXIC], side, t)
        corner(room, BARRELS)
    elif role == "interrogatoire":
        center(room, NIK + "tech/tech_bomb_chair.mdl", la=0)
        against(room, [TERM, NIK + "republic/rep_console02.mdl"], "N", 0.5)
        against(room, LOCKERS, "E", 0.3)
        corner(room, SMALL_CRATES)
    elif role == "bunker":                                       # objets bas uniquement : meurtrières dégagées
        for _ in range(4):
            x0, y0, x1, y1 = room.rect
            place(room, [CRATE_W1, CRATE_W2, NIK + "containers/crate_weapon_01_open.mdl", NIK + "containers/con_box_crate_01.mdl",
                         NIK + "republic/rep_crate.mdl"], (g.uniform(x0 + 30, x1 - 30), g.uniform(y0 + 30, y1 - 30)), g.uniform(0, 360))
    elif role == "cellule":
        against(room, [NIK + "republic/rep_bunk_beds.mdl", MD + "lt_c/sci_fi/bed_bunk.mdl"], "N", g.uniform(0.25, 0.75))
        corner(room, [BIN])
    if room.loot:                                                # pillage : caisses éventrées, débris, objets de travers
        for _ in range(g.randint(1, 3)):
            x0, y0, x1, y1 = room.rect
            place(room, BROKEN + RUBBLE, (g.uniform(x0 + 40, x1 - 40), g.uniform(y0 + 40, y1 - 40)), g.uniform(0, 360))
    # contrôle final de la pièce : chaque porte doit rester accessible
    if not _free(room, []):
        raise RuntimeError("pièce inaccessible : %s %s" % (room.role, room.rect))
    STATS["pieces"] += 1
    DUMP.append(dict(role=room.role, rect=room.rect, doors=room.doors, keep=room.keep, solid=room.solid,
                     win=room.tall_keep, loot=room.loot, key=[k if isinstance(k, str) else round(k) for k in room.rng_key],
                     meubles=[(m.split("/")[-1][:-4], r, a, s_) for (m, lx, ly, a, r, zt, s_, w) in room.placed]))


def emit(v, room, W, byaw, light_z=None, light="255 214 170 90", check=True):
    """Pose les meubles validés (contrôle final contre toute la map dans vx.resolve) + plafonnier et lumière de la pièce."""
    for (m, lx, ly, a, r, ztop, solid, why), z in zip(room.placed, room.zs):
        v.prop(m, *W(lx, ly), byaw + a, z=z, why="int_" + room.role, check=check)
        STATS["meubles"] += 1
    x0, y0, x1, y1 = room.rect
    cx, cy = W((x0 + x1) / 2, (y0 + y1) / 2)
    zl = room.z + room.ceil - 2 if light_z is None else light_z
    if light is None:                                            # pièce déjà éclairée (cellule, bunker)
        return
    v.prop(NIK + "city/city_hanging_light.mdl", cx, cy, 0, z=zl, why="int_lumiere", check=False)
    v.light(cx, cy, zl - 40, light)
