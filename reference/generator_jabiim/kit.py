"""Outils de construction : sol en dalles, bâtiments creux à étages, props posés et vérifiés, nœuds PNJ.

Tout le contenu vient du jeu de base (HL2 + Garry's Mod) : aucun pack Workshop requis.
"""
import json
import math
import os
import random

from srctools import Vec

from geom import Poly, norm, overlap, box_sub

HERE = os.path.dirname(os.path.abspath(__file__))
BOUNDS = json.load(open(os.path.join(HERE, "prop_bounds.json"), encoding="utf-8"))
import vexis_style as VS                       # style Vexis : textures et props de rp_cw_arsenal_vexis
for _m, _b in VS.VEXIS_BOUNDS.items():
    BOUNDS.setdefault(_m, _b)
RNG = random.Random(1977)

DOOR_W, DOOR_H = 192, 176
WIN_W, WIN_LO, WIN_HI = 128, 48, 144     # fenêtres : appui à 48 (on tire debout), haut à 144


def rot_box(model, x, y, z, yaw):
    """Boîte englobante monde d'un modèle tourné de `yaw` degrés (origine à x, y, z)."""
    b = BOUNDS[model]
    (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    xs, ys = [], []
    for px in (x0, x1):
        for py in (y0, y1):
            xs.append(px * c - py * s)
            ys.append(px * s + py * c)
    return (x + min(xs), y + min(ys), z + z0, x + max(xs), y + max(ys), z + z1)


# modèles refusés en prop_static par vbsp -> équivalent statique, ou caisse en brush ("BOX", l, p, h), ou rien (None)
SUBST = {
    "models/props_junk/wood_crate001a.mdl": ("BOX", 48, 48, 48),
    "models/props_junk/wood_crate002a.mdl": ("BOX", 48, 80, 48),
    "models/props_c17/oildrum001.mdl": ("BOX", 32, 32, 48),
    "models/props_junk/wood_pallet001a.mdl": None,
    "models/props_junk/pushcart01a.mdl": "models/props_vehicles/wagon001a.mdl",
    "models/props_junk/trafficcone001a.mdl": None,
    "models/props_wasteland/barricade002a.mdl": "models/props_c17/concrete_barrier001a.mdl",
    "models/props_wasteland/barricade001a.mdl": "models/props_c17/concrete_barrier001a.mdl",
    "models/props_c17/bench01a.mdl": "models/props_trainstation/benchoutdoor01a.mdl",
    "models/props_junk/trashbin01a.mdl": "models/props_trainstation/trashcan_indoor001a.mdl",
    "models/props_junk/trashdumpster01a.mdl": "models/props_junk/trashdumpster02.mdl",
    "models/props_c17/furnituretable001a.mdl": "models/props_lab/lockers.mdl",
    "models/props_c17/furniturecouch001a.mdl": "models/props_wasteland/laundry_dryer001.mdl",
    "models/props_c17/shelfunit01a.mdl": "models/props_lab/lockers.mdl",
    "models/props_vehicles/apc001.mdl": "models/props_vehicles/truck003a.mdl",
    "models/props_wasteland/laundry_cart001.mdl": None,
    "models/props_wasteland/kitchen_counter001a.mdl": None,
    "models/props_wasteland/prison_bedframe001a.mdl": None,
}
CRATE_MATS = ("wood/woodwall009a", "wood/woodshelf001a")


class Ctx:
    """Contexte commun : World + sol (hauteurs), obstacles, zones à garder libres, props, lumières."""

    def __init__(self, w):
        self.w = w
        self.ground = []        # (x0, y0, x1, y1, z) : surfaces où l'on peut poser un prop
        self.obst = {}          # index 512 -> boîtes pleines
        self.clear = []         # rectangles 2D à laisser libres (routes, cols, portes)
        self.props = []         # (modèle, (x, y, z), yaw, solid)
        self.rej = {}
        self.nodes_extra = []   # nœuds PNJ aux étages
        self.info = {}          # repères pour le plan (noms des lieux)
        self.footprints = []    # emprises des bâtiments (pas de décor extérieur posé sur les toits)
        self.labels = []        # (x0, y0, x1, y1, type) pour le plan

    # ---------- obstacles ----------
    def _cells(self, b):
        for ix in range(int(b[0] // 512), int(b[3] // 512) + 1):
            for iy in range(int(b[1] // 512), int(b[4] // 512) + 1):
                yield (ix, iy)

    def add_obst(self, b):
        b = norm(b)
        for k in self._cells(b):
            self.obst.setdefault(k, []).append(b)

    def hits(self, b):
        for k in self._cells(b):
            for o in self.obst.get(k, ()):
                if overlap(b, o):
                    return True
        return False

    # ---------- brushes ----------
    def blk(self, box, mat, kind="detail", top=None, ground=False, obst=True):
        b = self.w.block(norm(box), mat, kind, top)
        if obst:
            self.add_obst(b.box)
        if ground:
            x0, y0, z0, x1, y1, z1 = b.box
            self.ground.append((x0, y0, x1, y1, z1))
        return b

    def poly(self, p, ground_top=None):
        self.w.add(p)
        self.add_obst(p.bbox)
        if ground_top:
            self.ground.append(ground_top)
        return p

    def gz(self, x, y, zmax=1e9):
        z = 0
        for (x0, y0, x1, y1, zz) in self.ground:
            if x0 <= x <= x1 and y0 <= y <= y1 and z < zz <= zmax:
                z = zz
        return z

    def gz_all(self, x, y, zmax=1e9):
        zs = {0}
        for (x0, y0, x1, y1, zz) in self.ground:
            if x0 <= x <= x1 and y0 <= y <= y1 and zz <= zmax:
                zs.add(zz)
        return sorted(zs)

    def in_clear(self, b):
        return any(b[0] < c[2] and c[0] < b[3] and b[1] < c[3] and c[1] < b[4] for c in self.clear)

    def in_air(self, b):
        """La boîte (sans sa base) est entièrement dans un volume d'air (pas dans un mur)."""
        for s in self.w.spaces:
            sb = s.box
            if sb[0] <= b[0] and b[3] <= sb[3] and sb[1] <= b[1] and b[4] <= sb[4] and sb[2] <= b[2] + 2 and b[5] <= sb[5]:
                return True
        return False

    # ---------- props ----------
    def prop(self, model, x, y, yaw=0, z=None, solid=6, road_ok=False, why="divers", check=True, zmax=1e9):
        if model in SUBST:
            sub = SUBST[model]
            if sub is None:
                return False
            if isinstance(sub, tuple):
                return self.crate(x, y, sub[1], sub[2], sub[3], z=z, road_ok=road_ok, zmax=zmax)
            model = sub
        model = VS.swap(model)
        b = BOUNDS[model]
        if z is None and zmax >= 1e8 and check:
            if any(f[0] - 8 <= x <= f[2] + 8 and f[1] - 8 <= y <= f[3] + 8 for f in self.footprints):
                self.rej["batiment"] = self.rej.get("batiment", 0) + 1
                return False
        zf = self.gz(x, y, zmax) if z is None else z
        oz = zf - b["min"][2] + 1
        box = rot_box(model, x, y, oz, yaw)
        test = (box[0], box[1], box[2] + 2, box[3], box[4], box[5])
        if check:
            reason = None
            if not self.in_air(test):
                reason = "hors_air"
            elif self.hits(test):
                reason = "obstacle"
            elif not road_ok and self.in_clear(test):
                reason = "route"
            if reason:
                self.rej[reason] = self.rej.get(reason, 0) + 1
                return False
        self.props.append((model, (round(x, 1), round(y, 1), round(oz, 1)), yaw, solid))
        if solid:
            self.add_obst(test)
        return True

    def crate(self, x, y, lx, ly, h, z=None, road_ok=False, zmax=1e9):
        """Caisse en brush (les caisses HL2 ne peuvent pas être statiques)."""
        if RNG.random() < 0.5:
            lx, ly = ly, lx
        x0, y0 = int(x // 16 * 16), int(y // 16 * 16)
        if z is None and zmax >= 1e8 and any(f[0] - 8 <= x <= f[2] + 8 and f[1] - 8 <= y <= f[3] + 8 for f in self.footprints):
            return False
        zf = self.gz(x, y, zmax) if z is None else z
        box = (x0, y0, zf, x0 + lx, y0 + ly, zf + h)
        test = (box[0], box[1], box[2] + 2, box[3], box[4], box[5])
        if not self.in_air(test) or self.hits(test) or (not road_ok and self.in_clear(test)):
            self.rej["caisse"] = self.rej.get("caisse", 0) + 1
            return False
        self.blk(box, RNG.choice(CRATE_MATS))
        if RNG.random() < 0.3:                       # parfois une 2e caisse posée dessus
            b2 = (x0 + 8, y0 + 8, zf + h, x0 + 8 + 32, y0 + 8 + 32, zf + h + 32)
            if not self.hits((b2[0], b2[1], b2[2] + 1, b2[3], b2[4], b2[5])):
                self.blk(b2, RNG.choice(CRATE_MATS))
        return True

    def scatter(self, models, rect, n, tries=8, yaw=None, **kw):
        x0, y0, x1, y1 = rect
        ok = 0
        for _ in range(n * tries):
            if ok >= n:
                break
            m = RNG.choice(models)
            x, y = RNG.uniform(x0, x1), RNG.uniform(y0, y1)
            if self.prop(m, x, y, RNG.choice([0, 90, 180, 270]) if yaw is None else yaw + RNG.uniform(-15, 15), **kw):
                ok += 1
        return ok

    # ---------- lumière ----------
    def light(self, x, y, z, color="255 226 184 160", dist=0):
        kv = {"_light": color}
        if dist:
            kv["_fifty_percent_distance"] = dist
        self.w.ent("light", (x, y, z), **kv)


# ---------------------------------------------------------------- sol en dalles
def fill_ground(c, rect, holes, matf, z0=0, z1=16, cell=64, kind="detail"):
    """Couvre rect de dalles (z0..z1) sauf les trous. matf(x, y) -> matériau (ou None = trou).
    Fusion gloutonne en rectangles par matériau (peu de brushes)."""
    x0, y0, x1, y1 = rect
    nx, ny = (x1 - x0) // cell, (y1 - y0) // cell
    grid = [[None] * nx for _ in range(ny)]
    for j in range(ny):
        cy0 = y0 + j * cell
        for i in range(nx):
            cx0 = x0 + i * cell
            if any(cx0 < h[2] and h[0] < cx0 + cell and cy0 < h[3] and h[1] < cy0 + cell for h in holes):
                continue
            grid[j][i] = matf(cx0 + cell / 2, cy0 + cell / 2)
    used = [[False] * nx for _ in range(ny)]
    n = 0
    for j in range(ny):
        for i in range(nx):
            m = grid[j][i]
            if m is None or used[j][i]:
                continue
            i2 = i
            while i2 + 1 < nx and grid[j][i2 + 1] == m and not used[j][i2 + 1] and (i2 + 1 - i) * cell < 2048:
                i2 += 1
            j2 = j
            while j2 + 1 < ny and (j2 + 1 - j) * cell < 2048 and all(grid[j2 + 1][k] == m and not used[j2 + 1][k] for k in range(i, i2 + 1)):
                j2 += 1
            for jj in range(j, j2 + 1):
                for ii in range(i, i2 + 1):
                    used[jj][ii] = True
            c.blk((x0 + i * cell, y0 + j * cell, z0, x0 + (i2 + 1) * cell, y0 + (j2 + 1) * cell, z1), m, kind,
                  ground=True, obst=False)
            n += 1
    return n


# ---------------------------------------------------------------- formes
def wedge(x0, y0, x1, y1, z0, z1, high, mat, kind="detail"):
    """Talus/falaise en prisme triangulaire : face inclinée qui monte vers le côté `high` (x0|x1|y0|y1)."""
    x0, y0, x1, y1 = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
    h = z1 - z0
    if high == "y1":
        d = y1 - y0; slope = (Vec(x0, y0, z0), Vec(0, -h, d).norm())
    elif high == "y0":
        d = y1 - y0; slope = (Vec(x0, y1, z0), Vec(0, h, d).norm())
    elif high == "x1":
        d = x1 - x0; slope = (Vec(x0, y0, z0), Vec(-h, 0, d).norm())
    else:
        d = x1 - x0; slope = (Vec(x1, y0, z0), Vec(h, 0, d).norm())
    planes = [slope, (Vec(x0, y0, z0), Vec(0, 0, -1))]
    low = {"y1": "y0", "y0": "y1", "x1": "x0", "x0": "x1"}[high]
    for side, n, p in (("x0", Vec(-1, 0, 0), Vec(x0, y0, z0)), ("x1", Vec(1, 0, 0), Vec(x1, y1, z0)),
                       ("y0", Vec(0, -1, 0), Vec(x0, y0, z0)), ("y1", Vec(0, 1, 0), Vec(x1, y1, z0))):
        if side != low:          # côté bas : arête, pas de face (sinon face dégénérée)
            planes.append((p, n))
    return Poly(planes, mat, kind, (x0, y0, z0, x1, y1, z1))


# ---------------------------------------------------------------- bâtiments
def _wall_pieces(box, holes):
    pieces = [box]
    for h in holes:
        nxt = []
        for p in pieces:
            nxt.extend(box_sub(p, h))
        pieces = nxt
    return [p for p in pieces if p[0] < p[3] and p[1] < p[4] and p[2] < p[5]]


def stairs_axis(x0, y0, x1, y1, fh=256, T=32):
    """Axe possible pour l'escalier de building() (None = trop petit pour un étage praticable)."""
    run = int(math.ceil(fh * 1.25 / 16) * 16)
    if (x1 - x0) >= 2 * run + 2 * T + 192 and (y1 - y0) >= 160 + 2 * T + 256:
        return "x"
    if (y1 - y0) >= 2 * run + 2 * T + 192 and (x1 - x0) >= 160 + 2 * T + 256:
        return "y"
    return None


def building(c, x0, y0, x1, y1, z0, floors, fh, ext, inner, floor_mat, roof_mat,
             doors=("y0",), windows=True, kind="detail", parapet=True, roof_access=True,
             big_door=None, light="255 226 184 160", T=32, name=None):
    """Bâtiment creux praticable : murs avec portes (192x176) et fenêtres, planchers, escaliers en
    rampe alternés (ouest/est le long du mur nord), toit-terrasse avec parapet.
    big_door = (côté, largeur, hauteur) : grande ouverture (hangar, grange).
    Les murs sont en `ext` (les deux faces : façade dehors et dedans)."""
    run = int(math.ceil(fh * 1.25 / 16) * 16)
    sw = 160                                       # largeur de l'escalier
    L = [z0 + 16 + f * fh for f in range(floors + 1)]   # hauteur du dessus de chaque plancher ; L[-1] = toit
    top = L[-1]
    # dalle du rez-de-chaussée
    c.blk((x0, y0, z0, x1, y1, z0 + 16), floor_mat, kind, ground=True, obst=False)
    # escaliers le long du mur nord (axe x) ; sinon, si le bâtiment est plus profond que large, le long du mur est (axe y)
    ax = None
    if (x1 - x0) >= 2 * run + 2 * T + 192 and (y1 - y0) >= sw + 2 * T + 256:
        ax = "x"
    elif (y1 - y0) >= 2 * run + 2 * T + 192 and (x1 - x0) >= sw + 2 * T + 256:
        ax = "y"
    stairs_possible = ax is not None

    # trémies : étage f (1..floors) -> côté alterné
    def hole(f):
        if ax == "x":
            hx0 = x0 + T + 32 if f % 2 == 1 else x1 - T - 32 - run
            return (hx0, y1 - T - sw, hx0 + run, y1 - T)
        hy0 = y0 + T + 32 if f % 2 == 1 else y1 - T - 32 - run
        return (x1 - T - sw, hy0, x1 - T, hy0 + run)
    # murs
    sides = {
        "y0": (x0, y0, x1, y0 + T), "y1": (x0, y1 - T, x1, y1),
        "x0": (x0, y0 + T, x0 + T, y1 - T), "x1": (x1 - T, y0 + T, x1, y1 - T),
    }
    for side, (a0, b0, a1, b1) in sides.items():
        wall = (a0, b0, z0 + 16, a1, b1, top)
        holes = []
        along_x = side in ("y0", "y1")
        lo, hi = (a0, a1) if along_x else (b0, b1)
        mid = (lo + hi) / 2
        mid = int(mid // 16 * 16)
        if big_door and big_door[0] == side:
            bw, bh = big_door[1], big_door[2]
            u0, u1 = mid - bw // 2, mid + bw // 2
            holes.append((u0, b0 - 1, z0 + 16, u1, b1 + 1, z0 + 16 + bh) if along_x else (a0 - 1, u0, z0 + 16, a1 + 1, u1, z0 + 16 + bh))
        elif side in doors:
            u0, u1 = mid - DOOR_W // 2, mid + DOOR_W // 2
            holes.append((u0, b0 - 1, z0 + 16, u1, b1 + 1, z0 + 16 + DOOR_H) if along_x else (a0 - 1, u0, z0 + 16, a1 + 1, u1, z0 + 16 + DOOR_H))
        if windows:
            span = hi - lo
            n = max(1, min(4, int((span - 128) // 448)))
            for f in range(floors):
                if f == 0 and (side in doors or (big_door and big_door[0] == side)):
                    continue
                if stairs_possible and side == ("y1" if ax == "x" else "x1"):   # mur des escaliers : pas de fenêtres
                    continue
                for k in range(n):
                    u = lo + span * (k + 0.5) / n
                    u = int(u // 16 * 16)
                    z_lo, z_hi = L[f] + WIN_LO, L[f] + WIN_HI
                    if z_hi > L[f + 1] - 32:
                        continue
                    holes.append((u - WIN_W // 2, b0 - 1, z_lo, u + WIN_W // 2, b1 + 1, z_hi) if along_x
                                 else (a0 - 1, u - WIN_W // 2, z_lo, a1 + 1, u + WIN_W // 2, z_hi))
        for p in _wall_pieces(wall, holes):
            c.blk(p, ext, kind)
    # planchers d'étage et toit (avec trémie)
    for f in range(1, floors + 1):
        slab = (x0 + T, y0 + T, L[f] - 16, x1 - T, y1 - T, L[f])
        hs = []
        if stairs_possible and (f < floors or roof_access):
            hx0, hy0, hx1, hy1 = hole(f)
            hs.append((hx0, hy0, L[f] - 17, hx1, hy1, L[f] + 1))
        mat = roof_mat if f == floors else floor_mat
        for p in _wall_pieces(slab, hs):
            c.blk(p, mat, kind, ground=True, obst=False)
        # rampe sous la trémie, du plancher f-1 au plancher f
        if hs:
            hx0, hy0, hx1, hy1 = hole(f)
            rise = ("+x" if f % 2 == 1 else "-x") if ax == "x" else ("+y" if f % 2 == 1 else "-y")
            from geom import ramp
            r = ramp(hx0, hy0, hx1, hy1, L[f - 1], L[f], rise, base=L[f - 1], mat=floor_mat, kind=kind)
            c.poly(r)
    # parapet du toit
    if parapet:
        for (a0, b0, a1, b1) in ((x0, y0, x1, y0 + 16), (x0, y1 - 16, x1, y1), (x0, y0 + 16, x0 + 16, y1 - 16), (x1 - 16, y0 + 16, x1, y1 - 16)):
            c.blk((a0, b0, top, a1, b1, top + 48), ext, kind)
    # lumières intérieures
    if light:
        nlx = max(1, int((x1 - x0) // 768))
        for f in range(floors):
            zc = L[f + 1] - 16 - 24 if f + 1 <= floors else top - 40
            for k in range(nlx):
                c.light(x0 + (x1 - x0) * (k + 0.5) / nlx, (y0 + y1) / 2, zc, light)
    # nœuds PNJ aux étages
    for f in range(1, floors):
        c.nodes_extra.append(((x0 + x1) / 2, y0 + T + 64, L[f] + 16))
    # empreinte pleine pour les props extérieurs (on ne pose rien dans les murs)
    for (a0, b0, a1, b1) in sides.values():
        c.add_obst((a0, b0, z0 + 16, a1, b1, top + 48))
    c.footprints.append((x0, y0, x1, y1))
    c.labels.append((x0, y0, x1, y1, "bat"))
    if name:
        c.info[name] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return {"L": L, "top": top, "box": (x0, y0, z0, x1, y1, top)}


def tower(c, x0, y0, x1, y1, z0, h, ext, roof, kind="world", name=None, roof_props=True):
    """Immeuble plein (occulteur pour la visibilité) avec toit plat et équipements de toit."""
    c.blk((x0, y0, z0, x1, y1, z0 + h), ext, kind, top=roof, ground=True)
    c.footprints.append((x0, y0, x1, y1))
    c.labels.append((x0, y0, x1, y1, "tour"))
    if roof_props:
        zt = z0 + h
        for _ in range(RNG.randint(1, 3)):
            m = RNG.choice(["models/props_rooftop/roof_vent001.mdl", "models/props_rooftop/chimneypipe_cluster02a.mdl",
                            "models/props_rooftop/antennaclusters01a.mdl", "models/props_rooftop/satellitedish02.mdl"])
            c.prop(m, RNG.uniform(x0 + 96, x1 - 96), RNG.uniform(y0 + 96, y1 - 96), RNG.choice([0, 90, 180]), z=zt, solid=0)
    if name:
        c.info[name] = ((x0 + x1) / 2, (y0 + y1) / 2)
