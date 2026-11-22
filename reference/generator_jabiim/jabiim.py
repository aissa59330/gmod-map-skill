"""Tracé de rp_cw_battle_of_jabiim — v9 : REFONTE selon le brief (docs/brief_refonte.pdf) et son « nouveau plan général ».

Une région de Jabiim crédible, boueuse, accidentée, marquée par une bataille déjà engagée, en 3 secteurs aux limites
naturelles (pas de rectangles), reliés par une route goudronnée sinueuse :
  NORD   — Secteur 1, plaines de Jobreth : village rural irrégulier (maisons variées, intactes / endommagées / en ruine),
           fermes, granges, silos, clôtures brisées, champs boueux, collines, arbres morts.
  CENTRE — Secteur 2, bassin minier : mine à ciel ouvert en gradins (rampes, parois rocheuses) avec, au fond, le puits
           vers les cavernes ; convoyeur vers la raffinerie ; sous-zones industrielles dispersées (raffinerie, gare de
           chargement, centrale, camp ouvrier, carrière, poste séparatiste).
  SUD    — Secteur 3, front de Jabiim : FOB républicaine en terrasses (spawn), réseaux de tranchées CREUSÉES ramifiées
           (républicain et séparatiste), no man's land de cratères, bunkers, artillerie, postes d'observation, épaves.
Relief d'abord (brief §4) : collines, talus, cratères, fossés, falaises, mares. Mur invisible + paysage au-delà.
Les cavernes (prison, centre de commandement droïde) restent sous la map ; le puits principal est au fond de la mine.
"""
import math
import os

from geom import Block, frustum, ramp, box_sub
from kit import building, stairs_axis
from terrain import Terrain, fbm, smoothstep, poly_dist, seg_dist
import shapes as S
import vx as VX
import vignettes as VG
import interieurs as IN
from vx import M, MDL, NIK, round_hall, cooling_tower, chimney, silo, vault_hall, pillbox, wall_line, landing_pad, mushroom_tower

R = VX.R
XA, XB, YA, YB = -15872, 15872, -15872, 15872
PX, PY = 13824, 13824                     # mur invisible sur les 4 côtés
FLOOR, CEIL = -1600, 4096                 # la mine descend à ~ -1200
CAVE_DZ = -3840                           # cavernes sous la map
LEVELS = {"jabiim": 0, "hyber": CAVE_DZ}

# matériaux du terrain par secteur (palette du brief : terre sombre, boue, roche, herbe morte)
GRASS = "jabiim/sol_plaine"               # plaines : terre sombre / herbe morte (tools/make_textures.py)
FIELD = "jabiim/sol_champ"                # champs : boue / terre labourée
MUDT, MUDT2 = "jabiim/sol_front", "nature/blendmudmud001a"   # front : boue / terre grise retournée
ROCKT, CLIFFT = "nature/blendrockdirt006a", "nature/blendcliffdirt001a"
EARTH = "nature/dirtfloor011a"
ROAD = "jabiim/road"
WATER = "jabiim/eau_marais"
PLANK = "wood/woodwall009a"
SACS = "jabiim/sacs"
STATS = {}

ATTE = MDL + "props/starwars/vehicles/atte_crash.mdl"
BARR = NIK + "republic/rep_barricade_metal.mdl"
MORTAR = NIK + "turrets/neu_autoturret01_mortar.mdl"
TURRET = NIK + "turrets/turret_neu_tracking.mdl"
CRATES = [NIK + "containers/con_box_crate_06.mdl", NIK + "containers/con_box_crate_02.mdl", MDL + "props_wasteland/cargo_container01.mdl"]
BANNER = NIK + "items/banner_separatist.mdl"
FLAG = MDL + "props/starwars/furniture/flag.mdl"
TREES = [MDL + "props_foliage/tree_cliff_01a.mdl", MDL + "props_foliage/tree_cliff_02a.mdl", MDL + "props_foliage/oak_tree01.mdl"]
DEAD = [MDL + "props_foliage/tree_dry01_big.mdl", MDL + "props_foliage/tree_cliff_02a.mdl"]
SHRUBS = [MDL + "fallout_4/landscape/plants/shrubgrouplarge04.mdl", MDL + "fallout_4/landscape/plants/shrubgroupmedium02.mdl",
          MDL + "fallout_4/landscape/plants/shrubgroupsmall01.mdl"]
ROCKS = [MDL + "props_wasteland/rockcliff05a.mdl", MDL + "props_wasteland/rockcliff_cluster03a.mdl", NIK + "caves/caves_large_boulder_ald.mdl"]
REEDS = [f"models/kingpommes/starwars/misc/lothal/tallgrass_group{i}.mdl" for i in (1, 2, 3)]

# ---------------------------------------------------------------- composition (coordonnées monde)
def front_top(x):          # limite nord du secteur 3 (front), ondulée
    return -2900 + 650 * math.sin(x / 3100 + 0.7)


def plain_bottom(x):       # limite sud du secteur 1 (plaines), ondulée
    return 4800 + 700 * math.sin(x / 2700 + 2.1)


def sector(x, y):
    if y < front_top(x):
        return 3
    if y > plain_bottom(x):
        return 1
    return 2


PIT = (-1024, 1024)                       # mine à ciel ouvert
PIT_R = 3400
BENCH_R = [3400, 2700, 2000, 1350]        # rayon extérieur de chaque paroi (de haut en bas)
BENCH_Z = [40, -260, -560, -860, -1180]   # niveau du rebord puis de chaque gradin (dernier = fond)
FOB = (-3584, -13440, 3584, -9472)        # FOB en terrasse au sud (z = 72)
FOB_Z = 72
SHAFTS = {                                # puits vers les cavernes (dalle de terrain de 1024 retirée) : (x, y)
    "mine": (-1536, 512),                 # au FOND de la mine (le seul qui mène directement à la galerie principale)
    "nord": (9728, 8704),                 # vieille tête de mine des plaines (au-dessus de la caverne « mine »)
    "sud": (7680, -11776),                # puits d'aération bombardé, côté front (au-dessus du lac souterrain)
}
ROAD_MAIN = [(0, -9300), (500, -7700), (-700, -5900), (700, -4000), (2500, -2500), (3700, -300), (3400, 2300), (1900, 4300),
             (-300, 6100), (-1100, 8000), (-1600, 9700), (-900, 11300), (1700, 12300), (5000, 11700), (8200, 10500), (9900, 9300)]
ROAD_WEST = [(-1600, 9700), (-4400, 10300), (-7600, 9800), (-10300, 8500), (-11600, 6800)]
ROAD_EAST = [(3700, -300), (6300, 1100), (8600, 500), (10300, -500), (12200, -200)]


# ================================================================== terrain et contexte
def outside(x, y):
    return math.hypot(max(abs(x) - PX, 0), max(abs(y) - PY, 0))


class SegIndex:
    """Index spatial de segments (polylignes) : distance au plus proche segment, rapide."""

    def __init__(self, lines, cell=1024):
        self.cell, self.grid = cell, {}
        for pts in lines:
            for (a, b) in zip(pts, pts[1:]):
                x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
                for i in range(int(x0 // cell) - 1, int(x1 // cell) + 2):
                    for j in range(int(y0 // cell) - 1, int(y1 // cell) + 2):
                        self.grid.setdefault((i, j), []).append((a, b))

    def dist(self, x, y):
        best = 1e9
        for (a, b) in self.grid.get((int(x // self.cell), int(y // self.cell)), ()):
            d = seg_dist(x, y, a[0], a[1], b[0], b[1])[0]
            if d < best:
                best = d
        return best


class JTerrain(Terrain):
    def base(self, x, y):
        s = sector(x, y)
        h = 60 + 120 * fbm(x / 5200, y / 5200, 4, 3) + 40 * fbm(x / 1300, y / 1300, 3, 11)
        if s == 2:                                    # bassin minier : plus accidenté, rocheux
            h += 140 * fbm(x / 2200, y / 2200, 3, 21) + 70 * abs(fbm(x / 700, y / 700, 3, 37))
        elif s == 3:                                  # front : sol labouré
            h += 35 * fbm(x / 500, y / 500, 2, 43)
        d = outside(x, y)
        if d > 0:                                     # au-delà du mur : collines boisées puis montagnes
            k = smoothstep(450, 2300, d)
            h += k * (1800 + 650 * fbm(x / 2600, y / 2600, 4, 23)) + k * 320 * abs(fbm(x / 700, y / 700, 3, 31))
        for f in self.features:
            h = f(x, y, h)
        return h


class CaveFloor(Terrain):
    def base(self, x, y):
        h = 24 + 46 * fbm(x / 1400, y / 1400, 3, 83) + 18 * fbm(x / 400, y / 400, 2, 89)
        for f in self.features:
            h = f(x, y, h)
        return h


class JV(VX.V):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.t = JTerrain(XA, YA, XB, YB, FLOOR)
        self.has_t = True
        self.cave_t = []
        self.info, self.footprints, self.routes, self.rects, self.water = {}, [], [], [], []

    def gz(self, x, y, zmax=1e9):
        z = None
        for (r, ct) in self.cave_t:
            if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
                z = ct.h(x, y)
        if z is None:
            z = self.t.h(x, y) if self.has_t else 0
        for s in self.slabs:
            zt = s[-1]
            if zt > zmax:
                continue
            if s[0] == "disc":
                if (x - s[1]) ** 2 + (y - s[2]) ** 2 <= s[3] ** 2:
                    z = max(z, zt)
            elif s[1] <= x <= s[3] and s[2] <= y <= s[4]:
                z = max(z, zt)
        return z

    def blk(self, box, mat, kind="detail", top=None, obst=True, ground=False):
        b = super().blk(box, mat, kind, top, obst)
        if ground:
            self.slabs.append(("rect", b.box[0], b.box[1], b.box[3], b.box[4], b.box[5]))
        return b

    def poly(self, p, ground_top=None):
        self.add(p)
        if ground_top:
            x0, y0, x1, y1, z = ground_top
            self.slabs.append(("rect", x0, y0, x1, y1, z))
        return p


def pack_bounds(models):
    missing = [m for m in models if m not in VX.BOUNDS]
    if not missing:
        return
    from srctools.mdl import Model
    from srctools.filesys import RawFileSystem, VPKFileSystem, FileSystemChain
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    packs = [l.strip() for l in open(os.path.join(root, "tools", "content_paths.txt"), encoding="utf-8")
             if l.strip() and not l.startswith("#")]
    se = "C:/Program Files (x86)/Steam/steamapps/common/GarrysMod"
    fs = FileSystemChain(*[RawFileSystem(p) for p in packs if os.path.isdir(p)],
                         *[VPKFileSystem(se + p) for p in ("/sourceengine/hl2_misc_dir.vpk", "/garrysmod/garrysmod_dir.vpk")])
    for m in missing:
        mdl = Model(fs, fs[m])
        VX.BOUNDS[m] = {"min": list(mdl.hull_min), "max": list(mdl.hull_max), "static": True}


def route(v, kind, *pts):
    v.routes.append((kind, [tuple(p) for p in pts]))


def areaportal(v, box):
    v.w.ent("func_areaportal", solids=[Block(box, "tools/toolsareaportal", "detail")], StartOpen=1, PortalVersion=1)
    STATS["areaportals"] = STATS.get("areaportals", 0) + 1


def in_zone(v, x, y, pad=0):
    return any(a - pad <= x <= c + pad and b - pad <= y <= d + pad for (a, b, c, d, _) in v.zones)


def zone(v, x0, y0, x1, y1, name):
    v.zones.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), name))


def smooth(pts, step=420):
    """Polyligne lissée (Catmull-Rom) échantillonnée tous les ~step : virages doux pour la route et les chemins."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        n = max(1, int(L // step))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2 +
                                    (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in (0, 1)))
    out.append(pts[-1])
    return out


# ================================================================== RELIEF (priorité du brief)
CRATERS = []
POOLS = []
HILLS = [  # (x, y, rayon, hauteur) : buttes et collines (points d'observation, silhouettes)
    (-9000, 11200, 1500, 420), (-12000, 4200, 1300, 380), (6500, 7300, 1400, 360), (11800, 12400, 1300, 460),
    (-6000, 6400, 1100, 260), (3600, 13000, 1000, 300), (-12600, 11800, 1200, 520), (12600, 6000, 1100, 340),
    (-10500, -1200, 1300, 620), (12000, 3200, 1200, 560), (-7200, 2600, 900, 380), (8600, -2300, 1000, 420),
    (-12400, -11200, 1300, 300), (12400, -12600, 1300, 340), (-6400, -11800, 900, 180), (5600, -12900, 900, 200),
    # buttes plus petites (points de vue, couverts) dans les plaines et autour de la mine
    (-3600, 12600, 700, 160), (2600, 7400, 650, 140), (-8200, 4800, 800, 200), (8000, 2600, 700, 180), (-4800, 4200, 600, 150),
    (5400, 5600, 650, 170), (-9200, -7600, 700, 130), (10400, -9000, 700, 140),
]


# traces de chenilles (brief §5) : deux ornières de boue sombre peintes dans le sol (alpha), sans aucun brush
TRACKS = [[(300, -9300), (1400, -8200), (3000, -7300), (5200, -6200)],
          [(-400, -9300), (-1800, -8400), (-3900, -7300), (-6100, -6500)],
          [(-8400, 7200), (-7000, 8300), (-5200, 9500), (-3200, 10000)],
          [(6500, -2200), (7800, -1300), (9100, -900), (10600, -1400)]]
_RUTS = []
for _pts in TRACKS:
    for (_a, _b) in zip(_pts, _pts[1:]):
        _L = math.hypot(_b[0] - _a[0], _b[1] - _a[1])
        _nx, _ny = -(_b[1] - _a[1]) / _L, (_b[0] - _a[0]) / _L
        for _o in (0,):                     # sommets du sol tous les 128 : une bande de boue retournée (2 ornières fines seraient invisibles)
            _RUTS.append((_a[0] + _nx * _o, _a[1] + _ny * _o, _b[0] + _nx * _o, _b[1] + _ny * _o))


def on_rut(x, y):
    for (x0, y0, x1, y1) in _RUTS:
        if min(x0, x1) - 240 < x < max(x0, x1) + 240 and min(y0, y1) - 240 < y < max(y0, y1) + 240                 and seg_dist(x, y, x0, y0, x1, y1)[0] < 170 + 60 * fbm(x / 400, y / 400, 2, 83):
            return True
    return False


def relief(v, trench_lines):
    t = v.t
    rnd = __import__("random").Random(11)
    # cratères : très nombreux sur le front (no man's land), quelques-uns ailleurs
    for _ in range(600):
        if len(CRATERS) >= 95:
            break
        x, y = rnd.uniform(-PX + 600, PX - 600), rnd.uniform(-PY + 600, PY - 600)
        s = sector(x, y)
        if s == 1 and rnd.random() > 0.08 or s == 2 and rnd.random() > 0.2:
            continue
        if s == 3 and not (-7900 < y < -5000) and rnd.random() > 0.35:
            continue
        r = rnd.uniform(220, 520) if s == 3 else rnd.uniform(260, 420)
        if math.hypot(x - PIT[0], y - PIT[1]) < PIT_R + 900 or (FOB[0] - 600 < x < FOB[2] + 600 and FOB[1] - 600 < y < FOB[3] + 600):
            continue
        CRATERS.append((x, y, r))
    for (dx, dy, r) in ((0, 0, 360), (-520, 380, 240), (430, -350, 280)):     # obus tombés sur le quartier bombardé
        CRATERS.append((VILLAGE[0] + 2000 + dx, VILLAGE[1] - 1300 + dy, r))
    # mares (boue + quelques mares, brief) : petites cuvettes inondées
    for (x, y, r) in ((-8400, -10800, 700), (7400, -8600, 650), (-11200, -4300, 600), (4600, -5200, 520), (-4800, 8200, 620),
                      (7900, 12600, 560), (-10600, 12900, 540), (10800, 6400, 500),
                      # flaques dans les ornières et au bord des chemins (petites, peu profondes)
                      (-7000, 8300, 230), (1400, -8200, 220), (-3900, -7300, 240), (7800, -1300, 210), (-5200, 9500, 200)):
        POOLS.append((x, y, r))
    tri = SegIndex(trench_lines)
    pit_x, pit_y = PIT

    def pit(x, y, h):
        """Mine à ciel ouvert : rebord surélevé, 4 parois rocheuses et gradins, rampes en hélice."""
        r = math.hypot(x - pit_x, y - pit_y)
        if r > PIT_R + 900:
            return h
        if r > PIT_R:                                # bourrelet du rebord (déblais)
            w = 1 - smoothstep(PIT_R, PIT_R + 900, r)
            # raccord continu avec le 1er gradin (plus de ressaut infranchissable) ; bourrelet de déblais un peu plus loin
            return h + (BENCH_Z[0] - h) * w + 110 * math.exp(-(((r - PIT_R - 450) / 240) ** 2)) * smoothstep(PIT_R, PIT_R + 250, r)
        ang = math.degrees(math.atan2(y - pit_y, x - pit_x)) % 360
        z = BENCH_Z[-1]
        for k in range(len(BENCH_R)):
            outer = BENCH_R[k]
            inner = BENCH_R[k + 1] if k + 1 < len(BENCH_R) else 0
            if inner < r <= outer:
                wall = min(1.0, (outer - r) / 380.0)     # paroi sur 380 (~48°) : les displacements plus raides laissaient passer les joueurs
                z = BENCH_Z[k] + (BENCH_Z[k + 1] - BENCH_Z[k]) * smoothstep(0, 1, wall)
                # rampe : dans une fenêtre angulaire, la paroi devient une pente douce (route de roulage)
                a0 = (40 + 105 * k) % 360
                da = (ang - a0 + 540) % 360 - 180
                span = math.degrees(1300 / max(outer, 400))
                if abs(da) < span:
                    tt = (da + span) / (2 * span)
                    zr = BENCH_Z[k] + (BENCH_Z[k + 1] - BENCH_Z[k]) * tt
                    if r > outer - 520:
                        z = zr
                z += 18 * fbm(x / 300, y / 300, 2, 61) * (1 - wall)
                break
        return z

    def hills(x, y, h):
        for (cx, cy, r, hh) in HILLS:
            dx, dy = x - cx, y - cy
            if abs(dx) < r * 1.7 and abs(dy) < r * 1.7:
                d = math.hypot(dx, dy)
                h += hh * math.exp(-((d / r) ** 2) * 1.5) * (0.85 + 0.15 * fbm(x / 500, y / 500, 2, 17))
        return h

    def craters(x, y, h):
        for (cx, cy, r) in CRATERS:
            dx, dy = x - cx, y - cy
            if abs(dx) < r * 1.5 and abs(dy) < r * 1.5:
                d = math.hypot(dx, dy)
                h -= 130 * (1 - smoothstep(0, r, d)) - 55 * math.exp(-(((d - r) / 140) ** 2))
        return h

    def trenches(x, y, h):
        """Tranchées CREUSÉES : fossé de ~150 de profondeur, flancs en pente (cachés par les coffrages)."""
        if y > -2000:
            return h
        d = tri.dist(x, y)
        if d < 330:                                   # profondeur variable (130 à 190) : pas de tranchée « au gabarit »
            return h - (160 + 30 * fbm(x / 900, y / 900, 2, 91)) * (1 - smoothstep(110, 330, d))
        return h

    roads_idx = SegIndex([smooth(ROAD_MAIN), smooth(ROAD_WEST), smooth(ROAD_EAST)])

    def ditches(x, y, h):
        """Fossés de bord de route (eau de pluie) : petite dépression juste au-delà de l'accotement."""
        d = roads_idx.dist(x, y)
        if 260 < d < 520:
            return h - 46 * math.exp(-(((d - 380) / 70) ** 2))
        return h

    def boundary_talus(x, y, h):
        """Talus naturels entre secteurs (avec des passages) : sépare sans rectangle."""
        for yb, amp in ((front_top(x) + 250, 140), (plain_bottom(x) - 200, 110)):
            d = abs(y - yb)
            if d < 700:
                gate = abs(math.sin(x / 1900 + (0.3 if amp > 120 else 1.7)))
                h += amp * math.exp(-((d / 320) ** 2)) * smoothstep(0.25, 0.6, gate)
        return h
    t.features += [hills, boundary_talus, ditches, craters, trenches, pit]
    for (x, y, r) in POOLS:                          # mares : rebord aplani puis cuvette, eau à niveau propre
        zl = int(t.h(x, y) // 16) * 16
        t.flat_disc(x, y, r * 1.25, zl + 12, 520)
        t.flat_disc(x, y, r * 0.65, zl - 64, r * 0.45)
        v.water.append((int(x - r), int(y - r), FLOOR, int(x + r), int(y + r), zl - 8))
        zone(v, x - r, y - r, x + r, y + r, "mare")
        n = 0
        for _ in range(60):
            if n >= 14:
                break
            a, rr = R.uniform(0, 2 * math.pi), R.uniform(r * 0.8, r * 1.15)
            v.prop(R.choice(REEDS), x + rr * math.cos(a), y + rr * math.sin(a), R.uniform(0, 360), sink=6, why="roseaux", solid=0)
            n += 1

    def region(fn, mat):
        return (fn, mat)
    t.regions = [
        region(lambda x, y: outside(x, y) > 250, CLIFFT),
        region(lambda x, y: math.hypot(x - pit_x, y - pit_y) < PIT_R + 150, CLIFFT),
        region(lambda x, y: sector(x, y) == 2 and fbm(x / 1700, y / 1700, 2, 43) > -0.2, ROCKT),
        region(lambda x, y: sector(x, y) == 3 and fbm(x / 1500, y / 1500, 2, 47) > 0.1, MUDT2),
        region(lambda x, y: sector(x, y) == 3, MUDT),
        region(lambda x, y: sector(x, y) == 1 and any(abs(x - fx) < fw and abs(y - fy) < fh for (fx, fy, fw, fh) in FIELDS), FIELD),
        region(lambda x, y: sector(x, y) == 1, GRASS),
    ]
    t.default_mat = MUDT
    # « vertex painting » des plaines : plaques de terre sombre et d'herbe morte mélangées (pas de grande surface uniforme),
    # terre nue sur les chemins et dans les pentes
    def paint(t_, x, y):
        sc = sector(x, y)
        if sc != 2 and on_rut(x, y):
            return 0
        if sc == 3:                                   # front : boue noire et terre grise retournée par les obus
            n = fbm(x / 900, y / 900, 3, 79)
            return 255 * smoothstep(-0.3, 0.45, n) * (1 - smoothstep(0.3, 0.6, t_.slope(x, y)))
        if sc != 1:
            return None
        if t_.on_track(x, y):
            return 0
        n = fbm(x / 1300, y / 1300, 3, 77) + 0.35 * fbm(x / 380, y / 380, 2, 78)
        return 255 * smoothstep(-0.4, 0.35, n) * (1 - smoothstep(0.3, 0.6, t_.slope(x, y)))
    t.alpha_fn = paint
    STATS["crateres"], STATS["mares"] = len(CRATERS), len(POOLS)


FIELDS = [(-9800, 9800, 1300, 900), (-6200, 12400, 1100, 800), (4800, 9200, 1200, 800), (9400, 12000, 1000, 900),
          (-11400, 6400, 900, 700), (7200, 6000, 900, 700)]


# ================================================================== ROUTE GOUDRONNÉE + chemins (transitions)
def roads(v):
    t = v.t
    lines = [smooth(ROAD_MAIN), smooth(ROAD_WEST), smooth(ROAD_EAST)]
    n_seg = 0
    for li, pts in enumerate(lines):
        t.track(pts, 300)
        rp = pts[::2] + ([pts[-1]] if (len(pts) - 1) % 2 else [])
        for (a, b) in zip(rp, rp[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 32:
                continue
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if sector(mx, my) == 3 and R.random() < 0.12:           # route dégradée sur le front : tronçons arrachés
                continue
            za, zb = t.h(*a), t.h(*b)
            yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            pitch = -math.degrees(math.atan2(zb - za, L))
            v.add(S.obox(mx, my, (za + zb) / 2 + 2, L + 48, 416, 14, yaw, ROAD, "detail", pitch=pitch), obst=False)
            n_seg += 1
        route(v, "principal", *pts[::4], pts[-1])
    # chemins de terre (pistes non goudronnées) entre fermes, village, mine et front
    paths = [
        [(-1600, 9700), (-3800, 12600), (-6200, 12400)],
        [(-4400, 10300), (-6800, 7400), (-9800, 6200), (-12000, 4300)],
        [(5000, 11700), (5200, 9300), (7200, 6100), (9800, 4300)],
        [(3400, 2300), (2600, 4300), (3200, 4400)],
        [(-300, 6100), (-4200, 4800), (-8000, 3200), (-9500, 1200)],
        [(700, -4000), (-4200, -3400), (-8500, -3600), (-11000, -4200)],
        [(500, -7700), (5600, -7000), (9800, -6200), (11600, -6400)],
        [(2500, -2500), (6500, -1800), (8600, 500)],
        [(-700, -5900), (-6000, -6600), (-10800, -6600)],
    ]
    for pts in paths:
        p = smooth(pts, 500)
        t.track(p, 180)
        route(v, "secondaire", *p[::4], p[-1])
    STATS["route_segments"] = n_seg
    return lines + [smooth(p, 500) for p in paths]


# ================================================================== SECTEUR 3 : LE FRONT
def zigzag(y0, x0, x1, amp=260, step=700, seed=0, tilt=0.0):
    """Ligne en baïonnette qui dérive (tilt) et ondule à grande échelle : deux lignes ne restent jamais parallèles."""
    rnd = __import__("random").Random(seed)
    base = lambda x: y0 + tilt * (x - x0) + 520 * math.sin(x / 2900 + seed * 1.7) + 260 * math.sin(x / 1300 + seed)
    pts, x, k = [], x0, 0
    while x < x1:
        pts.append((x, base(x) + (amp if k % 2 else -amp) + rnd.uniform(-140, 140)))
        x += step + rnd.uniform(-160, 220)
        k += 1
    pts.append((x1, base(x1)))
    return pts


def trench_network():
    """Deux réseaux ramifiés et irréguliers (pas de lignes parallèles) : ligne principale en baïonnette, boyaux de
    liaison vers l'arrière, sapes vers l'avant qui finissent en postes isolés."""
    lines, saps, comms = [], [], []
    # le no man's land change de largeur (~1500 au centre, ~4500 aux ailes) : lignes inclinées en sens opposés
    rep = zigzag(-8700, -12800, -1200, seed=1, tilt=0.12), zigzag(-7500, 1500, 12600, seed=2, tilt=-0.11)
    sep = zigzag(-4100, -12400, -2600, seed=3, tilt=-0.14), zigzag(-5500, -400, 12400, seed=4, tilt=0.09)
    for main in rep + sep:
        lines.append(main)
    rnd = __import__("random").Random(5)
    for main, fwd in [(m, +1) for m in rep] + [(m, -1) for m in sep]:
        for i in range(2, len(main) - 2, 4):
            x, y = main[i]
            # sape vers l'avant (vers l'ennemi), finit en poste isolé
            L = rnd.uniform(800, 1300)
            pts = [(x, y), (x + rnd.uniform(-300, 300), y + fwd * L * 0.5), (x + rnd.uniform(-450, 450), y + fwd * L)]
            lines.append(pts)
            saps.append(pts[-1])
            # boyau de liaison vers l'arrière (une fois sur deux)
            if (i // 4) % 2 == 0:
                L2 = rnd.uniform(1100, 1700)
                pts2 = [(x, y), (x + rnd.uniform(-500, 500), y - fwd * L2 * 0.5), (x + rnd.uniform(-600, 600), y - fwd * L2)]
                lines.append(pts2)
                comms.append(pts2[-1])
    return lines, saps, comms


def revetment(v, lines):
    """Coffrages des tranchées : planches (brush) des deux côtés, avec des sorties tous les ~900 ; abris couverts."""
    t = v.t
    n = 0
    for pts in lines:
        dist = 0
        for (a, b) in zip(pts, pts[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx, ny = -uy, ux
            # planches regroupées en longs pans (un brush par pan au lieu d'un tous les 320) : les brushes en biais
            # coûtent cher en planes ; des pans manquent par endroits (coffrage arraché), remplacés par des sacs/caisses
            runs = {-1: [], 1: []}
            s = 0
            while s < L - 64:
                ln = min(320, L - s)
                dist += ln
                exit_gap = (int(dist) // 900) % 3 == 0 and (dist % 900) < 330
                for side in (-1, 1):
                    gap = exit_gap and side == 1
                    if not gap and runs[side] and runs[side][-1][1] == s:
                        runs[side][-1][1] = s + ln
                    elif not gap:
                        runs[side].append([s, s + ln])
                if R.random() < 0.05:                    # abri renforcé : toit + sacs, banc, lampe, caisses
                    cx, cy = a[0] + ux * (s + ln / 2), a[1] + uy * (s + ln / 2)
                    zt = t.h(cx, cy) + 150
                    v.add(S.obox(cx, cy, zt, ln, 300, 16, yaw, PLANK, "detail"), obst=False)
                    v.add(S.obox(cx, cy, zt + 16, ln - 40, 260, 36, yaw, SACS, "detail"), obst=False)
                    v.prop(R.choice(CRATES[:2]), cx, cy, yaw, why="abri")
                    v.prop(NIK + "republic/rep_peasant_lamp.mdl", cx + ux * 60, cy + uy * 60, 0, why="abri")
                    v.light(cx, cy, zt - 30, "255 200 140 90")
                elif R.random() < 0.06 and cy < -6300:   # caillebotis (côté républicain) : plancher de planches au fond
                    cx, cy = a[0] + ux * (s + ln / 2), a[1] + uy * (s + ln / 2)
                    v.add(S.obox(cx, cy, t.h(cx, cy) - 2, ln, 120, 8, yaw, PLANK, "detail"), obst=False)
                s += ln
            for side in (-1, 1):
                for (s0, s1) in runs[side]:
                    if s1 - s0 > 500 and R.random() < 0.3:          # pan arraché : on coupe le brush en deux
                        cut = R.uniform(s0 + 160, s1 - 320)
                        pieces = [(s0, cut), (cut + 200, s1)]
                        mx, my = a[0] + ux * (cut + 100) + nx * side * 110, a[1] + uy * (cut + 100) + ny * side * 110
                        v.prop(R.choice([VG.md("und_barricade"), CRATES[0]]), mx, my, yaw + 90 * (1 - side), why="coffrage")
                    else:
                        pieces = [(s0, s1)]
                    for (p0, p1) in pieces:
                        if p1 - p0 < 96:
                            continue
                        smp = [t.h(a[0] + ux * q, a[1] + uy * q) for q in (p0, (p0 + p1) / 2, p1)]
                        zb = min(smp) - 8
                        hh = max(smp) - zb + 190            # du fond de la tranchée jusqu au-dessus du parapet
                        cx, cy = a[0] + ux * (p0 + p1) / 2, a[1] + uy * (p0 + p1) / 2
                        sep_side = cy > -6300                                   # au nord : séparatistes (tôles sombres)
                        v.add(S.obox(cx + nx * side * 120, cy + ny * side * 120, zb, p1 - p0 + 8, 20, hh, yaw,
                                     "metal/metalhull010b" if sep_side else PLANK, "detail"), obst=True)
                        n += 1
    STATS["coffrages"] = n


def front(v, lines, saps, comms):
    # FOB : terrasse aménagée (terrassement), périmètre en sacs, préfabriqués, aires LAAT, dépôt de véhicules
    t = v.t
    x0, y0, x1, y1 = FOB
    v.info["FOB RÉPUBLICAINE (spawn)"] = ((x0 + x1) / 2, y1 + 500)
    t.flat_rect(x0, y0, x1, y1, FOB_Z - 6, 1100)                 # talus de terrassement tout autour
    # pas de grande dalle grise : terre battue, dalles seulement sous les bâtiments + allée de circulation depuis la porte
    v.slab_rect(-2944, -13056, -1664, -11776, FOB_Z, M["conc"], thick=48, flat=False)      # QG
    v.slab_rect(-832, -13120, 832, -11968, FOB_Z, M["conc"], thick=48, flat=False)         # caserne
    v.slab_rect(-256, -11968, 256, y1 - 120, FOB_Z, M["conc"], thick=32, flat=False)        # allée porte -> caserne
    v.slab_rect(256, -11200, 1472, -10816, FOB_Z, M["conc"], thick=32, flat=False)          # bretelle vers les aires LAAT
    zone(v, x0 - 300, y0 - 300, x1 + 300, y1 + 300, "fob")
    sb = lambda x, y, L, yaw: v.add(S.obox(x, y, FOB_Z - 8, L, 72, 96, yaw, SACS, "detail"), obst=True)
    # périmètre lisible mais pas rectangulaire : octogone irrégulier de sacs de sable, porte nord, poterne est
    C = 700
    poly = [(x0 + 200, y0 + 200 + C), (x0 + 200 + C, y0 + 200), (x1 - 200 - 900, y0 + 200), (x1 - 200, y0 + 200 + 900),
            (x1 - 200, y1 - 200 - 500), (x1 - 200 - 500, y1 - 200), (x0 + 200 + C + 300, y1 - 200), (x0 + 200, y1 - 200 - C - 300)]
    for i, (a, b) in enumerate(zip(poly, poly[1:] + poly[:1])):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        if i == 5:                                                      # côté nord : porte au centre (sur la route)
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            m = (0 - a[0]) / ux if abs(ux) > 0.1 else L / 2
            for (s0, s1) in ((0, m - 320), (m + 320, L)):
                sb(a[0] + ux * (s0 + s1) / 2, a[1] + uy * (s0 + s1) / 2, s1 - s0, yaw)
        elif i == 3:                                                    # côté est : poterne
            sb(a[0] + (b[0] - a[0]) * 0.25, a[1] + (b[1] - a[1]) * 0.25, L * 0.5 - 160, yaw)
            sb(a[0] + (b[0] - a[0]) * 0.8, a[1] + (b[1] - a[1]) * 0.8, L * 0.4 - 80, yaw)
        else:
            sb((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, L + 40, yaw)
    v.rects.append((x0 + 200, y0 + 200, x1 - 200, y1 - 200, "fob"))
    for (lx, ly) in ((0, y1 - 420), (-2300, -11300), (1500, -12700), (2048, -11500), (-600, -10400)):   # projecteurs de la FOB
        v.light(lx, ly, FOB_Z + 260, "236 240 255 380")
    round_hall(v, -2304, -12416, 640, FOB_Z, 448, doors=(90, 0), roof="dome", wall=M["pk"], light="255 230 200 260", closed=True)
    dome_interior(v, -2304, -12416, 640, FOB_Z, 448, (90, 0), "briefing", "bureau_cmd", M["pk"])
    v.info["QG"] = (-2304, -11600)
    for k, rm in enumerate(("roombarracks", "roomempty01", "roomoffice01", "roombarracks")):
        v.prop(VG.PF + rm + ".mdl", -512 + (k % 2) * 560, -12800 + (k // 2) * 600, 0, z=FOB_Z, why="fob")
        prefab_interior(v, rm, -512 + (k % 2) * 560, -12800 + (k // 2) * 600, FOB_Z, "bureau_cmd")
    v.info["Caserne préfabriquée"] = (0, -11500)
    for (px, py) in ((2048, -12288), (2048, -10752)):
        landing_pad(v, px, py, FOB_Z, 560, h=96, ramp_yaw=180)
        v.rects.append((px - 560, py - 560, px + 560, py + 560, "laat"))
    v.info["Aires LAAT"] = (2400, -10000)
    for i in range(8):
        for j in range(8):
            v.spawns.append((-1664 + i * 64, -10880 + j * 64, FOB_Z + 24))
    v.clear += [(-1440, -10650, 420), (0, -9800, 650)]
    for (bx, by) in ((-700, -9700), (700, -9700)):
        v.prop(FLAG, bx, by, 0, z=FOB_Z, why="fob")
    v.scatter(CRATES, -2600, -10400, 450, 9, why="fob")
    for (cx, cy) in ((x0 + 820, y1 - 820), (x1 - 640, y1 - 640)):          # sur les pans coupés du périmètre
        pillbox(v, cx, cy, FOB_Z, 90, r=230)
    # réseaux de tranchées (relief déjà creusé) : coffrages, abris, postes isolés au bout des sapes
    revetment(v, lines)
    for (x, y) in saps:
        z = t.h(x, y)
        for a in (0, 120, 240):
            v.add(S.obox(x + 260 * math.cos(math.radians(a)), y + 260 * math.sin(math.radians(a)), z - 4, 360, 64, 84, a + 90,
                         SACS, "detail"), obst=True)
        v.prop(TURRET if y > -6500 else NIK + "turrets/neu_autoturret01.mdl", x, y, 90 if y < -6500 else 270, why="poste")
        if y > -6300:                                   # poste séparatiste : bannière + barricade droïde
            v.prop(BANNER, x + 200, y + 120, 180, why="poste")
            v.prop(VG.md("und_barricade"), x - 200, y - 220, 270, why="poste")
        else:                                           # poste républicain : barrière métal + caisses d'armes
            v.prop(BARR, x + 160, y + 240, 0, why="poste")
            v.prop(NIK + "containers/crate_weapon_01.mdl", x - 180, y - 140, 30, why="poste")
    for (x, y) in comms:
        v.prop(R.choice(CRATES), x + 150, y, R.uniform(0, 360), why="depot")
    v.info["Tranchées républicaines"] = (-9000, -9300)
    v.info["Tranchées séparatistes"] = (9000, -3900)
    v.info["No man's land (cratères)"] = (-4200, -6500)
    # bunkers, artillerie, postes d'observation (dispersés, sans symétrie)
    for (bx, by, face) in ((-9300, -4000, 270), (-3600, -3700, 270), (5200, -4200, 270), (10400, -3900, 270), (-6500, -9200, 90),
                           (6800, -8900, 90)):
        pillbox(v, bx, by, t.h(bx, by) + 8, face, r=280)
        back = 1 if face == 270 else -1                     # arrière du bunker (côté de son camp)
        for d_ in (700, 900, 1100):
            for dx_ in (0, 300, -300):
                ex, ey = bx + dx_, by + back * d_
                if not (in_zone(v, ex, ey, 380) or t.on_track(ex, ey, 420)):
                    buried_entrance(v, ex, ey, 90 if back < 0 else 270, (bx, by))
                    break
            else:
                continue
            break
    v.info["Bunkers"] = (-3600, -3000)
    for (gx, gy) in ((-7800, -3300), (2600, -3600), (8800, -3400)):
        z = t.h(gx, gy)
        t.flat_disc(gx, gy, 380, z, 300)
        v.add(S.ring_wall(gx, gy, 340, 56, z, z + 80, EARTH, "detail", 12, gaps={9, 10}))
        v.prop(MORTAR, gx, gy, 270, z=z, why="artillerie")
        v.rects.append((gx - 340, gy - 340, gx + 340, gy + 340, "canon"))
    v.info["Artillerie séparatiste"] = (2600, -3000)
    for (ox, oy) in ((-11800, -6800), (11900, -7400)):
        v.prop(VG.md("tsftower") if "tsftower" in VG.IDX else TURRET, ox, oy, 0, why="observation")
        v.info["Poste d'observation"] = (ox, oy + 700)
    # épaves (AT-TE, speeders), barbelés, dépôts
    for (ax, ay, yaw) in ((-5600, -6700, 25), (3600, -6200, 200), (9300, -6900, 120)):
        v.prop(ATTE, ax, ay, yaw, sink=70, why="epave", check=False)        # épave couchée : peut chevaucher une tranchée
    v.info["AT-TE abattus"] = (-5600, -7400)
    for k in range(14):
        x, y = R.uniform(-12000, 12000), R.uniform(-7300, -5600)
        v.prop(VG.md("exterior_fence_notbarbed002f"), x, y, R.uniform(-20, 20), why="barbele")
    for k in range(8):
        x, y = R.uniform(-12000, 12000), R.uniform(-7600, -5300)
        v.prop(VG.md("veh_neu_speeder_02_wreckage"), x, y, R.uniform(0, 360), why="epave")
    v.info["Dépôt républicain"] = (6200, -10900)
    # poste de commandement avancé (république) et dépôt de munitions, position antichar (séparatistes)
    for (x, y, m, why) in ((-1500, -8300, NIK + "republic/rep_computer_table.mdl", "pc_avance"),
                           (-1300, -8300, NIK + "republic/rep_console02.mdl", "pc_avance"),
                           (-1700, -8150, FLAG, "pc_avance")):
        v.prop(m, x, y, 0, why=why)
    v.info["Poste de commandement avancé"] = (-1500, -7900)
    for k in range(6):
        v.prop(NIK + "containers/crate_weapon_01.mdl", 4300 + (k % 3) * 70, -9200 + (k // 3) * 70, R.uniform(-10, 10), why="munitions")
    v.info["Dépôt de munitions"] = (4300, -8900)
    for (x, y) in ((-2000, -4400), (2600, -4600), (7400, -4100)):
        v.prop(VG.md("und_barricade"), x, y, 270, why="antichar")
        v.prop(TURRET, x, y + 200, 270, why="antichar")
    v.info["Position antichar séparatiste"] = (2600, -4100)
    v.scatter(CRATES + [VG.md("rep_pallet_02")], 6200, -10600, 700, 14, why="depot")
    v.info["Dépôt séparatiste"] = (-7200, -2600)
    v.scatter(CRATES + [VG.md("tech_mine_barrel")], -7200, -2900, 600, 12, why="depot")


# ================================================================== SECTEUR 2 : LE BASSIN MINIER
def mine(v):
    t = v.t
    px, py = PIT
    v.info["MINE À CIEL OUVERT"] = (px, py + PIT_R + 700)
    zone(v, px - PIT_R - 300, py - PIT_R - 300, px + PIT_R + 300, py + PIT_R + 300, "mine")
    # rochers sur les gradins, engins abandonnés, tas de minerai
    for k in range(70):
        a = R.uniform(0, 2 * math.pi)
        r = R.uniform(1500, PIT_R - 150)
        x, y = px + r * math.cos(a), py + r * math.sin(a)
        if t.slope(x, y) > 0.5:
            v.prop(R.choice(ROCKS), x, y, R.uniform(0, 360), sink=30, why="mine")
    for (a, r) in ((30, 2350), (150, 1700), (250, 3000), (320, 1700)):
        x, y = px + r * math.cos(math.radians(a)), py + r * math.sin(math.radians(a))
        v.prop(VG.md("construction_mining_drill_01") if "construction_mining_drill_01" in VG.IDX else VG.md("tech_huge_generator"),
               x, y, a + 90, why="mine")
    for (a, r) in ((80, 2300), (200, 1650), (290, 2350)):
        x, y = px + r * math.cos(math.radians(a)), py + r * math.sin(math.radians(a))
        z = t.h(x, y)
        v.add(S.cone(x, y, 260, 40, z - 30, z + 200, EARTH, "detail", 9))
    for (a, r, mdl, pitch, roll, sink) in ((60, 1750, NIK + "tech/tech_forklift.mdl", 0, 90, 6),
                                           (115, 2550, MDL + "props_vehicles/truck003a.mdl", 22, 6, 60),
                                           (200, 2200, NIK + "tech/tech_mining_drill.mdl", 8, 72, 10),
                                           (275, 1500, MDL + "props_vehicles/truck001a.mdl", 0, 180, 8),
                                           (335, 2900, NIK + "tech/tech_forklift.mdl", -15, 0, 40)):
        x, y = px + r * math.cos(math.radians(a)), py + r * math.sin(math.radians(a))
        wreck(v, mdl, x, y, a + 70, pitch, roll, sink, why="mine_epave")
    # convoyeur : du fond de la mine jusqu'à la raffinerie, sur pylônes
    conv = [(px + 900, py + 300), (px + 2600, py + 700), (px + 4300, py + 1100), (5600, 2200)]
    for (a, b) in zip(conv, conv[1:]):
        za, zb = t.h(*a) + 520, t.h(*b) + 520
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        v.add(S.obox((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (za + zb) / 2, L, 128, 48, yaw, M["dirty"], "detail",
                     pitch=-math.degrees(math.atan2(zb - za, L))), obst=False)
        for k in range(1, int(L // 700) + 1):
            f = k / (int(L // 700) + 1)
            x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            z = t.h(x, y)
            v.add(S.cylinder(x, y, 40, z - 420, za + (zb - za) * f, M["trim"], "detail", 6))   # fondation enterrée (terrain retouché après)
    v.info["Convoyeur"] = (px + 2700, py + 1400)
    # sous-zones industrielles dispersées (brief : pas toutes au même endroit)
    rx, ry = 6400, 2600
    t.flat_rect(rx - 1500, ry - 1200, rx + 1700, ry + 1500, t.h(rx, ry), 900)
    zone(v, rx - 1600, ry - 1300, rx + 1800, ry + 1600, "raffinerie")
    zr = t.h(rx, ry)
    Wr = vault_hall(v, rx, ry, zr, 1792, 1024, 384, 288, 15, mat=M["wall3"])
    hall_interior(v, Wr, 15, ("raffinerie",), zr, 1792, 1024, 384, True, 1024 * 0.55, bays=("industrie", "stockage"),
                  office="controle", mat=M["wall3"])
    cooling_tower(v, rx + 1200, ry + 900, 520, zr, 1500)
    chimney(v, rx - 1100, ry + 1000, 110, zr, 1400)
    for (sx, sy) in ((rx + 1250, ry - 700), (rx + 500, ry - 650)):          # 2e silo hors de la plateforme
        silo(v, sx, sy, 240, zr, 900)
    v.prop(VG.md("tech_kolto_tank_lg"), rx - 1000, ry - 700, 30, why="raffinerie")
    v.prop(BANNER, rx - 300, ry - 700, 0, why="raffinerie")
    v.info["Raffinerie (occupée)"] = (rx, ry + 1700)
    platform(v, rx + 300, ry - 1050, zr, 1024, 256, 288, stairs=2)                     # passerelle de service
    v.blk((rx + 812, ry - 1114, zr + 272, rx + 1314, ry - 986, zr + 288), M["grate"], obst=False)    # passerelle -> 1er silo
    v.blk((rx + 1186, ry - 986, zr + 272, rx + 1314, ry - 920, zr + 288), M["grate"], obst=False)
    v.blk((rx + 812, ry - 1122, zr + 288, rx + 1322, ry - 1114, zr + 332), M["trim"], obst=False)    # garde-corps
    v.blk((rx + 1314, ry - 1114, zr + 288, rx + 1322, ry - 920, zr + 332), M["trim"], obst=False)
    for px_ in (rx + 1000, rx + 1250):
        v.blk((px_ - 12, ry - 1062, zr - 64, px_ + 12, ry - 1038, zr + 272), M["trim"])
    for (px_, py_, m) in ((rx - 600, ry - 1250, "con_small_container_pipes_stack"), (rx + 900, ry - 1250, "con_small_container_pipes"),
                          (rx + 100, ry - 1300, "generator_portable")):
        v.prop(VG.md(m) if m in VG.IDX else MDL + "lt_c/sci_fi/generator_portable.mdl", px_, py_, R.uniform(0, 360), why="raffinerie")
    gx, gy = 10200, -500                                          # gare de chargement
    t.flat_rect(gx - 1400, gy - 700, gx + 1400, gy + 700, t.h(gx, gy), 700)
    zone(v, gx - 1500, gy - 800, gx + 1500, gy + 800, "gare")
    zg = t.h(gx, gy)
    for dy in (-192, 192):
        v.add(S.obox(gx, gy + dy, zg - 4, 2800, 24, 14, 0, M["trim"], "detail"), obst=False)
    for k in range(4):
        v.prop(MDL + "props_wasteland/cargo_container01.mdl", gx - 1000 + k * 600, gy + 450, 0, why="gare")
    v.add(S.cone(gx + 800, gy - 450, 300, 50, zg - 30, zg + 220, EARTH, "detail", 9))
    v.prop(VG.md("construction_crane") if "construction_crane" in VG.IDX else VG.md("generator01"), gx - 900, gy - 500, 90, why="gare")
    v.info["Gare de chargement"] = (gx, gy + 1100)
    gantry(v, gx + 500, gy + 120, zg, 1500, 600, axis="y")
    v.prop(NIK + "tech/tech_forklift.mdl", gx - 300, gy + 900, 180, why="gare")
    platform(v, gx + 200, gy - 420, zg, 768, 224, 256, stairs=1)                       # quai de chargement surélevé
    for (dx, dy) in ((-1200, -560), (-700, -600), (1250, 520)):
        v.prop(NIK + "containers/con_crate_shipping02.mdl", gx + dx, gy + dy, R.choice((0, 90)), why="gare")
    cx_, cy_ = 10900, 4200                                         # centrale électrique
    t.flat_disc(cx_, cy_, 900, t.h(cx_, cy_), 600)
    zone(v, cx_ - 1000, cy_ - 1000, cx_ + 1000, cy_ + 1000, "centrale")
    zc = t.h(cx_, cy_)
    round_hall(v, cx_, cy_, 520, zc, 448, doors=(180, 270), roof="dome", wall=M["wall2"], closed=True, light="200 220 255 240")
    dome_interior(v, cx_, cy_, 520, zc, 448, (180, 270), "controle", "machines", M["wall2"])
    v.prop(VG.md("tech_huge_generator"), cx_ + 700, cy_ + 300, 0, why="centrale")
    v.prop(VG.md("generator01"), cx_ - 750, cy_ - 300, 90, why="centrale")
    v.info["Centrale"] = (cx_, cy_ + 1100)
    platform(v, cx_ - 50, cy_ - 760, zc, 640, 224, 224, stairs=1)
    for k in range(4):                                                                   # lampadaires du site
        a = k * math.pi / 2 + 0.4
        v.prop(NIK + "republic/rep_lamppost.mdl", cx_ + 820 * math.cos(a), cy_ + 820 * math.sin(a), 0, why="centrale")
        v.light(cx_ + 820 * math.cos(a), cy_ + 820 * math.sin(a), zc + 150, "255 236 200 160")
    wx, wy = 3200, 4300                                           # camp ouvrier
    t.flat_rect(wx - 900, wy - 600, wx + 900, wy + 600, t.h(wx, wy), 600)
    zone(v, wx - 1000, wy - 700, wx + 1000, wy + 700, "camp")
    for k, rm in enumerate(("roombarracks", "roomempty05", "roombarracks")):
        v.prop(VG.PF + rm + ".mdl", wx - 600 + k * 600, wy, 0, z=t.h(wx, wy), why="camp")
        prefab_interior(v, rm, wx - 600 + k * 600, wy, t.h(wx, wy), "salle")
    v.info["Camp ouvrier"] = (wx, wy + 900)
    qx, qy = -9600, 1500                                          # carrière à l'ouest + poste séparatiste sur la butte
    v.info["Carrière"] = (qx, qy + 1200)
    for k in range(10):
        a, r = R.uniform(0, 2 * math.pi), R.uniform(200, 900)
        v.prop(R.choice(ROCKS), qx + r * math.cos(a), qy + r * math.sin(a), R.uniform(0, 360), sink=20, why="carriere")
    sx_, sy_ = -10500, -1200
    zs = t.h(sx_, sy_)
    t.flat_disc(sx_, sy_, 700, zs, 600)
    zone(v, sx_ - 800, sy_ - 800, sx_ + 800, sy_ + 800, "poste")
    pillbox(v, sx_, sy_, zs, 270, r=300)
    v.prop(BANNER, sx_ + 400, sy_, 0, why="poste")
    v.info["Poste séparatiste (butte)"] = (sx_, sy_ + 900)


# ================================================================== BÂTIMENTS ORIENTÉS (variété : formes, tailles, états)
def house(v, cx, cy, w, d, yaw, state="intact", wall=None, roof=None, floors=1, kind="maison", roof_kind="gable",
          door=(160, 176), annex=None):
    """Maison orientée librement : 4 murs (porte en façade, fenêtres), toit à 2 pans ou plat ;
    état intact / endommagé (toit percé, pan de mur tombé) / ruine (murs bas déchiquetés)."""
    t = v.t
    wall = wall or R.choice([M["conc2"], M["dirty"], "plaster/plasterwall030a", "stone/stonewall032a", M["wall2"]])   # pas de brique à fenêtres (faux étages)
    roof = roof or R.choice([M["hull"], "metal/metalhull010b", M["hull3"]])
    z = max(t.h(cx, cy) for (cx, cy) in ((cx, cy),)) - 8
    t.flat_disc(cx, cy, max(w, d) * 0.75, z + 6, 420)
    fr = floors                     # étages vus par le tirage global R (aléas inchangés : extérieurs identiques)
    LR = IN.srng("maison", cx, cy)  # tirage propre au bâtiment (stable d'une compilation à l'autre)
    if floors == 1 and state == "intact" and kind == "maison" and roof_kind == "gable" and w >= 512 and d >= 448 \
            and LR.random() < 0.55:
        floors = 2                  # plus de maisons à étage (escalier + trémie)
    H = 224 * floors + 32
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    W = lambda lx, ly: (cx + lx * c - ly * s, cy + lx * s + ly * c)
    T = 24
    wins = []                       # fenêtres (zones interdites aux meubles hauts) : (rect local, niveau)
    v.add(S.obox(cx, cy, z - 16, w, d, 24, yaw, M["floor2"], "detail"), obst=False)
    v.slabs.append(("disc", cx, cy, min(w, d) / 2 - 20, z + 8))
    hh = (lambda: R.choice([64, 96, 140, 180])) if state == "ruine" else (lambda: H)

    def wall_run(lx, ly, L, lyaw, h, holes, ext=0, zb0=0):
        """Un mur percé : holes = [(u, largeur, z_bas, z_haut)] le long du mur (u = 0 au centre) ; pans pleins entre
        les ouvertures, allège sous chaque fenêtre, linteau au-dessus (rien au-dessus si le mur est plus bas)."""
        ax, ay = (1, 0) if lyaw == 0 else (0, 1)
        for (u, hw, zb, zt) in holes:
            if zb > 0:
                wx, wy = lx + ax * u, ly + ay * u
                r = (wx - hw / 2, wy - 64, wx + hw / 2, wy + 64) if lyaw == 0 else (wx - 64, wy - hw / 2, wx + 64, wy + hw / 2)
                wins.append((r, 1 if zb0 + zb >= 224 else 0))
        cuts = sorted((u - hw / 2, u + hw / 2, zb, zt) for (u, hw, zb, zt) in holes if zb < h - 24)
        u0 = -L / 2 - ext / 2
        segs = []
        for (ua, ub, zb, zt) in cuts:
            segs.append((u0, ua, 0, h))
            if zb > 0:
                segs.append((ua, ub, 0, zb))
            if zt < h - 8:
                segs.append((ua, ub, zt, h))
            u0 = ub
        segs.append((u0, L / 2 + ext / 2, 0, h))
        for (ua, ub, za, zb_) in segs:
            if ub - ua < 8 or zb_ - za < 8:
                continue
            um = (ua + ub) / 2
            x, y = W(lx + ax * um, ly + ay * um)
            v.add(S.obox(x, y, z + zb0 + za, ub - ua, T, zb_ - za, yaw + lyaw, wall, "detail"), obst=True)

    win = lambda u, zf=0: (u, R.choice([80, 96, 112]), zf + 88, zf + 176)
    up = [224] if floors > 1 and state != "ruine" else []
    RR = R if fr > 1 else LR                                  # fenêtres d'étage d'une maison surélevée : tirage local
    upw = lambda u, zf: (u, RR.choice([80, 96, 112]), zf + 88, zf + 176)
    # façade (y = -d/2) : porte au milieu, une fenêtre de part et d'autre si la place le permet
    fac = [(0, door[0], 0, door[1])]
    if w >= 512:
        fac += [win(-w / 4 - 30), win(w / 4 + 30)]
    fac += [upw(RR.choice([-1, 1]) * w / 4, zf) for zf in up]
    wall_run(0, -d / 2, w, 0, hh(), fac, ext=T)
    # arrière : une fenêtre décentrée (deux à l'étage s'il y en a un)
    wall_run(0, d / 2, w, 0, hh(), [win(R.uniform(-w / 4, w / 4))] + [upw(u, zf) for zf in up for u in (-w / 4, w / 4)], ext=T)
    for sx in (-1, 1):
        if state == "endommage" and sx == 1 and R.random() < 0.6:
            wall_run(sx * w / 2, -d / 4, d / 2, 90, hh(), [])                        # pan de mur tombé
        else:
            holes = [win(R.uniform(-d / 6, d / 6))] if (d >= 448 and sx == 1) else []
            wall_run(sx * w / 2, 0, d, 90, hh(), holes)
    # cloison intérieure percée d'une porte : deux pièces (salle / chambre ou atelier / réserve)
    part, du, du2 = None, 0, 0
    if state != "ruine" and w >= 512 and kind == "maison":
        sgn = 1 if fr > 1 else R.choice((-1, 1))
        part = sgn * max(w / 8, door[0] / 2 + T / 2 + 16)     # jamais dans l'embrasure de la porte d'entrée
        if floors > 1:
            part = abs(part)                                   # escalier à gauche, cuisine à droite
        du = R.uniform(-d / 6, d / 6)
        wall_run(part, 0, d - T, 90, 224 if floors > 1 else H - 8, [(du, 112, 0, 176)])
        if floors > 1:                                         # cloison de l'étage (deux pièces) percée d'une porte
            du2 = LR.uniform(-d / 6, d / 6)
            wall_run(part, 0, d - T, 90, H - 8 - 240, [(du2, 112, 0, 176)], zb0=240)
    stair = None
    if floors > 1 and state != "ruine":                        # vrai étage : plancher, escalier droit, trémie + garde-corps
        xi0, xi1, yi0, yi1 = -w / 2 + T / 2, w / 2 - T / 2, -d / 2 + T / 2, d / 2 - T / 2
        xa, xb = xi0, xi0 + 96
        ys = yi0 + 48
        ye = ys + 15 * 18                                      # 15 marches de 15,5 de haut, 18 de giron
        for (a0, b0, a1, b1) in ((xb, yi0, xi1, yi1), (xa, ye, xb, yi1), (xa, yi0, xb, ys)):
            v.add(S.obox(*W((a0 + a1) / 2, (b0 + b1) / 2), z + 224, a1 - a0, b1 - b0, 16, yaw, M["floor2"], "detail"),
                  obst=False)
        for k in range(1, 16):
            v.add(S.obox(*W((xa + xb) / 2, ys + (k - 0.5) * 18), z + 8, 96, 18, round(232 * k / 15), yaw, wall,
                         "detail"), obst=False)
        v.add(S.obox(*W(xb + 4, (ys + ye) / 2 + 20), z + 240, 8, ye - ys - 40, 40, yaw, M["trim"], "detail"), obst=False)
        v.add(S.obox(*W((xa + xb) / 2, ys - 4), z + 240, 96, 8, 40, yaw, M["trim"], "detail"), obst=False)
        stair = (xa, xb, ys, ye)
    if roof_kind == "flat" and state != "ruine":             # toit plat (commerce, atelier) + acrotère côté rue
        v.add(S.obox(cx, cy, z + H - 8, w + 32, d + 32, 16, yaw, M["floor2"], "detail"), obst=False)
        v.add(S.obox(*W(0, -d / 2 - 8), z + H + 8, w + 32, 16, 40, yaw, wall, "detail"), obst=False)
    elif state == "intact" or (state == "endommage" and R.random() < 0.5):
        rise = min(w, d) * 0.32
        half = d / 2 + 32                                     # débord de 32 au-delà des murs
        ze = z + H - 8                                        # égout du toit
        P = lambda lx, ly, zz: (round(W(lx, ly)[0]), round(W(lx, ly)[1]), round(zz))
        roof_z = lambda ly: ze + rise * (1 - abs(ly) / half)  # dessus de charpente (faîtage au centre)
        for sy in (-1, 1):                                    # deux pans construits par leurs sommets (plus de roulis)
            pts = []
            for lx in (-w / 2 - 32, w / 2 + 32):
                for ly in (0, sy * half):
                    pts += [P(lx, ly, roof_z(ly)), P(lx, ly, roof_z(ly) + 16)]
            v.add(S.hull_piece(pts, roof, "detail"), obst=False)
        apex = rise
        for sx in (-1, 1):                                    # pignons : triangle sous les pans, jamais au-dessus
            pts = []
            for lx in (sx * w / 2 - T / 2, sx * w / 2 + T / 2):
                pts += [P(lx, -d / 2, z + H - 4), P(lx, d / 2, z + H - 4), P(lx, -d / 2, roof_z(d / 2)),
                        P(lx, d / 2, roof_z(d / 2)), P(lx, 0, roof_z(0))]
            v.add(S.hull_piece(pts, wall, "detail"), obst=False)
        if R.random() < 0.45:                                 # cheminée
            v.add(S.obox(*W(R.choice([-1, 1]) * w / 4, d / 5), z + H - 40, 56, 56, apex + 110, yaw, "stone/stonewall032a", "detail"),
                  obst=False)
    else:                                                     # toit effondré : gravats de taille moyenne (les gros tas touchaient les murs)
        for k in range(3):
            v.prop(VG.md(R.choice(["ruins_rubble_01_a", "ruins_rubble_01_c", "ruins_rubble_02_c", "caves_rubble_small_ald_02",
                                   "ruins_rubble_02_f"])),
                   *W(R.uniform(-w / 4, w / 4), R.uniform(-d / 4, d / 4)), R.uniform(0, 360), sink=4, why="ruine")
    if state != "intact":                                     # traces de brûlé sur la façade (décalque : ni planes ni props)
        for lx in (R.uniform(-w / 3, -w / 8), R.uniform(w / 8, w / 3)):
            v.w.ent("infodecal", (*W(lx, -d / 2 - T / 2 - 1), z + R.uniform(60, 150)), texture=R.choice(["decals/scorch1", "decals/scorch2"]))
    if kind == "epicerie" and state != "ruine":               # auvent au-dessus de la vitrine
        pts = [(round(W(lx, ly)[0]), round(W(lx, ly)[1]), round(zz)) for lx in (-w / 3, w / 3)
               for (ly, zz) in ((-d / 2 - T / 2, z + 216), (-d / 2 - 200, z + 176), (-d / 2 - T / 2, z + 228), (-d / 2 - 200, z + 188))]
        v.add(S.hull_piece(pts, M["hull3"], "detail"), obst=False)
    _furnish_consume(v, W, yaw, w, d, z, fr, kind, state, part, H)     # mêmes aléas R qu'avant (rien ne bouge dehors)
    if state != "ruine":
        interior(v, W, yaw, cx, cy, w, d, z, floors, kind, state, part, du, du2, H, door, wins, stair, roof_kind)
    if state != "intact":                                     # impacts de tirs sur la façade
        for _ in range(R.randint(3, 6)):
            v.w.ent("infodecal", (*W(R.uniform(-w / 2.4, w / 2.4), -d / 2 - T / 2 - 1), z + R.uniform(40, 200)),
                    texture=R.choice(["decals/concrete/shot5", "decals/concrete/shot3_subrect", "decals/concrete/shot1_subrect"]))
    v.footprints.append((cx - max(w, d) / 2, cy - max(w, d) / 2, cx + max(w, d) / 2, cy + max(w, d) / 2))
    v.rects.append((cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2, "bat"))
    STATS["maisons"] = STATS.get("maisons", 0) + 1
    return z


# ================================================================== MOTEUR : intérieurs, landmarks, plateformes
NIKR, NIKT, NIKC = NIK + "republic/", NIK + "tech/", NIK + "city/"
# ---- mobilier : chaque pièce a un rôle (salle à vivre, cuisine, chambre, cellier) ; positions en fraction de la pièce
#      (u de 0 = mur gauche à 1 = mur droit de la pièce, v de -1 = façade à +1 = mur du fond), rotation, alternatives
TABLE, CHAIR, LAMP = NIKR + "rep_peasant_table.mdl", NIKR + "rep_peasant_chair.mdl", NIKR + "rep_peasant_lamp.mdl"
LOCKER, ARMOIRE, STOVE = MDL + "props_lab/lockers.mdl", NIKT + "tech_armory_locker.mdl", MDL + "props_c17/furniturestove001a.mdl"
BUNK, BENCH = NIKR + "rep_bunk_beds.mdl", NIKC + "city_furn_bench_metal.mdl"
CLUTTER = [NIK + "containers/con_box_crate_02.mdl", NIK + "containers/con_square_crate02_open.mdl", NIK + "tech/tech_mine_barrel.mdl",
           NIKR + "rep_crate.mdl", NIKR + "rep_pallet_02.mdl"]
ROOMS = {
    "salle": [(TABLE, 0.5, 0.05, 0), (CHAIR, 0.5, -0.45, 0), (CHAIR, 0.5, 0.55, 180), (CHAIR, 0.2, 0.05, 270),
              ([ARMOIRE, LOCKER], 0.08, 0.82, 180), (LAMP, 0.92, 0.85, 0), (BENCH, 0.92, -0.3, 90)],
    "cuisine": [(STOVE, 0.15, 0.85, 180), ([ARMOIRE, LOCKER], 0.45, 0.85, 180), (TABLE, 0.55, -0.1, 90), (CHAIR, 0.55, -0.6, 0),
                ([NIK + "tech/tech_mine_barrel.mdl", NIKR + "rep_crate.mdl"], 0.9, 0.8, 0), (LAMP, 0.9, -0.75, 0)],
    "chambre": [(BUNK, 0.75, 0.6, 90), ([LOCKER, ARMOIRE], 0.1, 0.82, 180), (NIKR + "rep_crate.mdl", 0.85, -0.7, 15), (LAMP, 0.15, -0.8, 0)],
    "cellier": [(NIKR + "rep_pallet_02.mdl", 0.3, 0.7, 0), (NIK + "containers/con_box_crate_02.mdl", 0.3, 0.72, 10),
                (NIK + "tech/tech_mine_barrel.mdl", 0.8, 0.75, 0), (NIK + "tech/tech_mine_barrel.mdl", 0.88, 0.5, 0),
                ([ARMOIRE, LOCKER], 0.85, -0.6, 270)],
    "epicerie": [(MDL + "lt_c/sci_fi/counter_sinks.mdl", 0.35, -0.3, 0), (MDL + "lt_c/sci_fi/counter_sinks.mdl", 0.55, -0.3, 0),
                 (ARMOIRE, 0.1, 0.85, 180), (ARMOIRE, 0.35, 0.85, 180), (ARMOIRE, 0.6, 0.85, 180),
                 (NIK + "containers/con_box_crate_02.mdl", 0.9, 0.7, 20), (NIK + "containers/con_square_crate02_open.mdl", 0.88, 0.1, 0),
                 (NIK + "tech/tech_mine_barrel.mdl", 0.1, 0.2, 0), (LAMP, 0.9, -0.8, 0)],
    "atelier": [(NIKT + "tech_city_workbench.mdl", 0.5, 0.82, 180), (MDL + "props_vehicles/car002b.mdl", 0.4, -0.05, 90),
                (MDL + "lt_c/sci_fi/generator_portable.mdl", 0.88, 0.6, 0), (NIKR + "rep_pallet_02.mdl", 0.88, -0.45, 30),
                (NIK + "containers/con_box_crate_06.mdl", 0.1, 0.7, 10), (ARMOIRE, 0.95, 0.15, 270),
                (NIK + "tech/tech_mine_barrel.mdl", 0.08, -0.5, 0)],
}


def _furnish_consume(v, *a):
    """Ancien aménagement exécuté à blanc : consomme exactement les mêmes tirages R qu'avant, pour que tout ce qui est
    généré ensuite (maisons suivantes, végétation...) reste au même endroit. Ne pose rien."""
    v.prop = lambda *x, **k: True
    try:
        furnish(v, *a)
    finally:
        del v.prop


def interior(v, W, yaw, cx, cy, w, d, z, floors, kind, state, part, du, du2, H, door, wins, stair, roof_kind):
    """Découpe le bâtiment en pièces typées et les aménage (moteur interieurs.py)."""
    T = 24
    xi0, xi1, yi0, yi1 = -w / 2 + T / 2, w / 2 - T / 2, -d / 2 + T / 2, d / 2 - T / 2
    C = IN.DOOR_CLEAR
    front = (-door[0] / 2, yi0, door[0] / 2, yi0 + C)
    loot = state == "endommage"
    g0 = z + 8
    ceil0 = 216 if floors > 1 else (H - 16 if roof_kind == "flat" else H - 8)
    tk = lambda lvl: [r for (r, l) in wins if l == lvl]
    rooms = []
    pd = lambda dd, side: ((part - T / 2 - C, dd - 56, part - T / 2, dd + 56) if side < 0 else
                           (part + T / 2, dd - 56, part + T / 2 + C, dd + 56))
    if part is None:
        role = kind if kind in ("epicerie", "atelier") else "salle"
        rooms.append(IN.Room(role, (xi0, yi0, xi1, yi1), g0, [front], tall_keep=tk(0), key=(cx, cy, 0), loot=loot, ceil=ceil0))
    elif floors > 1:
        xa, xb, ys, ye = stair
        rooms.append(IN.Room("salle", (xi0, yi0, part - T / 2, yi1), g0, [front, pd(du, -1)], keep=[(xa, ys - 56, xb, ys)],
                             solid=[(xa, ys, xb, ye)],
                             tall_keep=tk(0), key=(cx, cy, 0), loot=loot, ceil=ceil0))
        rooms.append(IN.Room("cuisine", (part + T / 2, yi0, xi1, yi1), g0, [pd(du, 1)], tall_keep=tk(0), key=(cx, cy, 1),
                             loot=loot, ceil=ceil0))
        up = z + 240
        cu = H - 8 - 240
        rooms.append(IN.Room("bureau", (xi0, yi0, part - T / 2, yi1), up, [(xa, ye, xb, ye + 40), pd(du2, -1)],
                             keep=[(xa, ye, xb + 40, ye + C)], solid=[(xa, ys - 4, xb + 8, ye)], tall_keep=tk(1), key=(cx, cy, 2),
                             loot=loot, ceil=cu))
        rooms.append(IN.Room("chambre", (part + T / 2, yi0, xi1, yi1), up, [pd(du2, 1)], tall_keep=tk(1), key=(cx, cy, 3),
                             loot=loot, ceil=cu))
    else:
        L, Rr = (xi0, yi0, part - T / 2, yi1), (part + T / 2, yi0, xi1, yi1)
        big, small, sb = (L, Rr, -1) if part > 0 else (Rr, L, 1)
        rooms.append(IN.Room("salle", big, g0, [front, pd(du, sb)], tall_keep=tk(0), key=(cx, cy, 0), loot=loot, ceil=ceil0))
        role2 = IN.srng("role", cx, cy).choice(["chambre", "chambre", "cellier", "bureau"])
        rooms.append(IN.Room(role2, small, g0, [pd(du, -sb)], tall_keep=tk(0), key=(cx, cy, 1), loot=loot, ceil=ceil0))
    for rm in rooms:
        IN.compose(rm)
        IN.emit(v, rm, W, yaw)


def furnish(v, W, yaw, w, d, z, floors, kind, state, part=None, H=256):
    """Aménage chaque pièce selon son rôle (props statiques, zéro plane). Maison à étage : entrée + cuisine sous la mezzanine,
    chambre à l'étage ; plain-pied : salle d'un côté de la cloison, chambre ou cellier de l'autre. Pillé si endommagé."""
    if state == "ruine":
        return
    half, hd = w / 2 - 72, d / 2 - 72
    rooms = []                                                 # (rôle, x gauche, x droit, niveau)
    if kind in ("epicerie", "atelier"):
        rooms = [(kind, -half, half, 0)]
    elif floors > 1:                                           # rampe côté -x : la pièce de gauche reste dégagée au centre
        rooms = [("cuisine", (part or 0) + 40, half, 0), ("chambre", 40, half, 1)]
        for (m, lx, ly, ry) in ((ARMOIRE, -half + 30, hd * 0.85, 180), (BENCH, -half + 40, -hd * 0.7, 90), (LAMP, -w / 8, hd * 0.85, 0)):
            v.prop(m, *W(lx, ly), yaw + ry, why="interieur", check=False)
    elif part is not None:
        left, right = (-half, part - 40), (part + 40, half)
        big, small = (left, right) if (left[1] - left[0]) >= (right[1] - right[0]) else (right, left)
        rooms = [("salle", big[0], big[1], 0), (R.choice(["chambre", "cellier"]), small[0], small[1], 0)]
    else:
        rooms = [("salle", -half, half, 0)]
    for (role, x0, x1, lvl) in rooms:
        for (m, u, vv, ry) in ROOMS[role]:
            if state == "endommage" and R.random() < 0.3:        # pillé : il manque des meubles
                continue
            m = R.choice(m) if isinstance(m, list) else m
            lx, ly = x0 + u * (x1 - x0), vv * hd
            zz = z + 8 + 232 if lvl else None
            v.prop(m, *W(lx + R.uniform(-10, 10), ly + R.uniform(-10, 10)), yaw + ry + R.uniform(-10, 10), z=zz,
                   why="interieur", check=False)
        if role != "atelier":                                  # un peu de désordre (différent d'une maison à l'autre)
            for _ in range(R.randint(0, 2)):
                v.prop(R.choice(CLUTTER), *W(x0 + R.uniform(0.2, 0.8) * (x1 - x0), R.choice((-1, 1)) * hd * 0.8),
                       R.uniform(0, 360), z=(z + 8 + 232) if lvl else None, why="interieur", check=False)
        # plafonnier de la pièce
        cx_, cy_ = W((x0 + x1) / 2, 0)
        v.prop(NIK + "city/city_hanging_light.mdl", cx_, cy_, 0, z=z + (224 if (floors > 1 and not lvl) else H) - 24,
               why="interieur", check=False)
    if state == "endommage":                                   # débris tombés du plafond
        v.prop(NIK + "ruins/ruins_rubble_01_c.mdl", *W(R.uniform(-half, half) * 0.6, R.uniform(-hd, hd) * 0.6), R.uniform(0, 360),
               why="interieur", check=False)


# ================================================================== PETITS AVANT-POSTES (dispersés, chacun avec un rôle)
def outpost(v, x, y, kind):
    """Petites positions autonomes : donnent une raison d'aller dans les zones vides, sans les surcharger."""
    t = v.t
    z = t.h(x, y)
    t.flat_disc(x, y, 520, z, 380)
    yaw = R.uniform(0, 360)
    c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    Wl = lambda lx, ly: (x + lx * c - ly * s_, y + lx * s_ + ly * c)
    P = lambda m, lx, ly, ry=0, why="avant_poste": v.prop(m, *Wl(lx, ly), yaw + ry, why=why)
    if kind == "observation_rep":                       # nid d'observation républicain : arc de sacs, jumelles (console), drapeau
        for a in (-50, 0, 50):
            v.add(S.obox(*Wl(260 * math.cos(math.radians(a + 90)), 260 * math.sin(math.radians(a + 90))), z - 4, 300, 64, 76,
                         yaw + a, SACS, "detail"), obst=True)
        P(NIKR + "rep_console02.mdl", 0, 120); P(FLAG, -160, -80); P(NIK + "containers/crate_weapon_01.mdl", 120, -60, 30)
        P(NIKR + "rep_crate.mdl", 170, -40, 10); P(LAMP, -60, -120)
        label = "Poste d'observation républicain"
    elif kind == "relais_sep":                          # relais de communication séparatiste : antenne, parabole, générateur
        P(MDL + "props_rooftop/antennaclusters01a.mdl", 0, 0); P(MDL + "props_rooftop/satellitedish02.mdl", 220, 80, 200)
        P(MDL + "props_canal/generator01.mdl", -220, 60, 90); P(BANNER, 0, -260, 180); P(VG.md("und_barricade"), 260, -200, 300)
        P(NIK + "tech/tech_mine_barrel.mdl", -140, -160)
        label = "Relais séparatiste"
    elif kind == "checkpoint":                          # point de contrôle abandonné : guérite, barrière, panneau
        v.add(S.obox(*Wl(-200, 0), z - 8, 160, 160, 232, yaw, M["dirty"], "detail"), obst=True)
        v.add(S.obox(*Wl(-200, 0), z + 224, 200, 200, 16, yaw, M["hull3"], "detail"), obst=False)
        P(BARR, 120, 0, 90); P(BARR, 300, 40, 80); P(NIKC + "city_sign_small.mdl", -60, -160, 0)
        P(NIK + "containers/con_crate_04_broken.mdl", 200, -180, 40)
        label = "Point de contrôle abandonné"
    elif kind == "cache":                               # cache de ravitaillement sous bâche : caisses, palettes, fûts
        for (lx, ly) in ((0, 0), (90, 30), (-90, -20), (40, 120)):
            P(R.choice([NIKR + "rep_crate.mdl", NIK + "containers/con_box_crate_02.mdl", NIKR + "rep_pallet_02.mdl"]), lx, ly,
              R.uniform(-20, 20))
        P(NIK + "tech/tech_mine_barrel.mdl", -160, 110); P(NIK + "tech/tech_mine_barrel.mdl", -200, 60)
        v.add(S.obox(*Wl(0, 40), z + 130, 360, 260, 8, yaw, M["hull"], "detail", roll=8), obst=False)   # bâche/tôle posée
        for (lx, ly) in ((-170, -80), (170, -80), (-170, 160), (170, 160)):
            v.add(S.cylinder(*Wl(lx, ly), 6, t.h(*Wl(lx, ly)) - 24, z + 130, M["trim"], "detail", 4), obst=False)
        label = "Cache de ravitaillement"
    elif kind == "medical":                             # poste de secours républicain à l'arrière du front
        P(NIK + "imperial/imp_medical_bed.mdl", -120, 60, 90); P(NIK + "imperial/imp_medical_bed.mdl", 120, 60, 90)
        P(MDL + "props/starwars/medical/bacta_tank.mdl", 0, 220); P(MDL + "props/starwars/medical/health_droid.mdl", 0, -60)
        P(NIKR + "rep_crate.mdl", 240, -120, 20); P(FLAG, -260, -160)
        v.add(S.obox(*Wl(0, 80), z + 200, 520, 380, 8, yaw, M["hull"], "detail"), obst=False)          # toile tendue
        for (lx, ly) in ((-250, -100), (250, -100), (-250, 260), (250, 260)):
            v.add(S.cylinder(*Wl(lx, ly), 6, t.h(*Wl(lx, ly)) - 24, z + 200, M["trim"], "detail", 4), obst=False)
        v.light(x, y, z + 170, "235 245 255 160")
        label = "Poste de secours"
    elif kind == "sniper_sep":                          # nid de tireur séparatiste dans des rochers
        for (lx, ly) in ((-180, 60), (160, 120), (0, -200)):
            P(R.choice(ROCKS), lx, ly, R.uniform(0, 360))
        P(VG.md("und_barricade"), 0, 140, 0); P(NIK + "tech/tech_mine_barrel.mdl", -80, -60)
        label = "Nid de tireur séparatiste"
    v.info[label] = (x, y + 500)
    zone(v, x - 450, y - 450, x + 450, y + 450, "avant_poste")
    STATS["avant_postes"] = STATS.get("avant_postes", 0) + 1


def outposts(v):
    """Place les avant-postes dans les zones vides (disque de Poisson, pente faible, hors routes et bâtiments)."""
    by_sector = {1: ["checkpoint", "cache", "observation_rep"], 2: ["relais_sep", "cache", "sniper_sep"],
                 3: ["medical", "observation_rep", "sniper_sep"]}
    used = {1: 0, 2: 0, 3: 0}
    rnd = __import__("random").Random(41)
    pts = poisson(-PX + 1500, -PY + 1500, PX - 1500, PY - 1500, 2600, rnd)
    rnd.shuffle(pts)
    for (x, y) in pts:
        sc = sector(x, y)
        if used[sc] >= 3 or in_zone(v, x, y, 900) or v.t.on_track(x, y, 700) or v.t.slope(x, y) > 0.25:
            continue
        if sc == 3 and y > -8000 and by_sector[3][used[3]] == "medical":    # le poste de secours reste à l'arrière
            continue
        outpost(v, x, y, by_sector[sc][used[sc]])
        used[sc] += 1


def landmark(v, kind, x, y, yaw):
    """Bâtiments qui structurent le village (uniques, travaillés, accessibles)."""
    t = v.t
    if kind == "maire":
        house(v, x, y, 768, 512, yaw, state="intact", floors=2, kind="maison", wall="stone/stonewall032a", roof=M["hull3"])
        v.info["Maison du maire"] = (x, y + 600)
    elif kind == "epicerie":
        house(v, x, y, 640, 448, yaw, state="endommage", kind="epicerie", roof_kind="flat", wall="plaster/plasterwall030a",
              door=(224, 192))
        v.info["Épicerie"] = (x, y + 520)
    elif kind == "atelier":
        house(v, x, y, 832, 576, yaw, state="intact", kind="atelier", roof_kind="flat", wall=M["dirty"], door=(352, 256))
        v.info["Atelier-garage"] = (x, y + 620)
    elif kind == "coop":                                      # grange coopérative + mezzanine de stockage
        z = t.h(x, y)
        t.flat_disc(x, y, 900, z, 500)
        Wc = vault_hall(v, x, y, z, 1280, 768, 320, 256, yaw, mat=M["wall2"])
        hall_interior(v, Wc, yaw, ("coop",), z, 1280, 768, 320, True, 768 * 0.55, mat=M["wall2"], bays_only_neg=True)
        c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        Wl = lambda lx, ly: (x + lx * c - ly * s_, y + lx * s_ + ly * c)
        v.add(S.obox(*Wl(0, 230), z + 200, 1100, 260, 16, yaw, M["floor2"], "detail"), obst=False)            # mezzanine
        for k in range(1, 14):                                                                          # escalier
            v.add(S.obox(*Wl(-420, 100 - 13 * 20 + (k - 0.5) * 20), z, 96, 20, round(216 * k / 14), yaw, M["floor2"], "detail"),
                  obst=True)
        for k in range(5):
            v.prop(R.choice([NIKR + "rep_pallet_02.mdl", NIK + "containers/con_box_crate_02.mdl",
                             NIK + "containers/con_box_crate_02.mdl"]), *Wl(-450 + k * 220, -150), yaw + R.uniform(-20, 20), why="coop")
        v.prop(VG.md("generatortrailer01"), *Wl(250, -120), yaw + 90, why="coop")
        v.footprints.append((x - 700, y - 700, x + 700, y + 700))
        v.info["Coopérative agricole"] = (x, y + 800)
    elif kind == "chateau_eau":                               # château d'eau : silhouette repère du village
        z = t.h(x, y)
        for (dx, dy) in ((-160, -160), (160, -160), (-160, 160), (160, 160)):
            v.add(S.cylinder(x + dx, y + dy, 24, z - 40, z + 700, M["dirty"], "detail", 6))
        v.add(S.cylinder(x, y, 260, z + 700, z + 980, M["hull3"], "detail", 12), obst=False)
        v.add(S.cone(x, y, 270, 40, z + 980, z + 1080, M["hull3"], "detail", 12), obst=False)
        v.info["Château d'eau"] = (x, y + 450)
    zone(v, x - 500, y - 500, x + 500, y + 500, "landmark")


def wall_seg(v, W, yaw, a, b, z, h, mat, door=None, T=24):
    """Cloison droite en repère local de a=(x, y) à b (axe x ou y), percée d'une porte door=(u centre, largeur, hauteur)."""
    (ax, ay), (bx, by) = a, b
    along_x = abs(by - ay) < 1e-6
    L = abs(bx - ax) if along_x else abs(by - ay)
    u0 = (ax + bx) / 2 if along_x else (ay + by) / 2
    segs = [(-L / 2, L / 2, 0, h)]
    if door:
        du, dw, dh = door
        segs = [(-L / 2, du - dw / 2, 0, h), (du + dw / 2, L / 2, 0, h), (du - dw / 2, du + dw / 2, dh, h)]
    for (ua, ub, za, zb) in segs:
        if ub - ua < 4 or zb - za < 4:
            continue
        um = u0 + (ua + ub) / 2
        lx, ly = (um, ay) if along_x else (ax, um)
        v.add(S.obox(*W(lx, ly), z + za, (ub - ua) if along_x else T, T if along_x else (ub - ua), zb - za, yaw, mat, "detail"),
              obst=True)


def door_box(px, py, rect, C=56, w=60):
    """Passage d'une porte située en (px, py) hors ou au bord de la pièce : rectangle collé au bord le plus proche."""
    x0, y0, x1, y1 = rect
    qx, qy = min(max(px, x0), x1), min(max(py, y0), y1)
    if qx in (x0, x1) and not (y0 < py < y1 and qy == py and x0 < px < x1):
        return (x0, qy - w, x0 + C, qy + w) if qx == x0 else (x1 - C, qy - w, x1, qy + w)
    return (qx - w, y0, qx + w, y0 + C) if qy == y0 else (qx - w, y1 - C, qx + w, y1)


def hall_interior(v, W, yaw, key, z, L, span, wall_h, side_doors, gate_w, bays=("stockage", "stockage"), office="bureau",
                  mat=None, bays_only_neg=False):
    """Halle voûtée : allée centrale dégagée entre les portails, travées de rangement contre les longs murs,
    bureau cloisonné (porte, plafond, lumière) au milieu du côté +y."""
    th, T, C = 32, 24, IN.DOOR_CLEAR
    hw = span / 2
    xi0, xi1, yi0, yi1 = -L / 2 + th, L / 2 - th, -hw + th, hw - th
    aisle = min(gate_w / 2, 150)
    sdoors = [-L / 4, L / 4] if side_doors else []
    rooms = []
    oh = min(wall_h - 48, 224)
    ow = 448 if L >= 1500 else 320
    if not bays_only_neg:
        ox0, ox1 = -ow / 2, ow / 2
        wall_seg(v, W, yaw, (ox0 - T / 2, aisle + T / 2), (ox1 + T / 2, aisle + T / 2), z, oh, mat, door=(0, 112, 176))
        for xx in (ox0 - T / 2, ox1 + T / 2):
            wall_seg(v, W, yaw, (xx, aisle + T), (xx, yi1), z, oh, mat)
        v.add(S.obox(*W(0, (aisle + yi1) / 2), z + oh, ow + 2 * T, yi1 - aisle + T, 16, yaw, M["floor2"], "detail"), obst=False)
        orect = (ox0, aisle + T, ox1, yi1)
        rooms.append(IN.Room(office, orect, z, [(-60, orect[1], 60, orect[1] + C)], key=key + (9,), ceil=oh))
        for (a0, a1) in ((xi0, ox0 - T), (ox1 + T, xi1)):
            rr = (a0, aisle, a1, yi1)
            ds = [(a0, aisle, a1, aisle + 24)] + [(dx - 140, yi1 - C, dx + 140, yi1) for dx in sdoors if a0 < dx < a1]
            rooms.append(IN.Room(bays[0], rr, z, ds, key=key + (len(rooms),), ceil=wall_h - 16))
    rr = (xi0, yi0, xi1, -aisle)
    ds = [(xi0, -aisle - 24, xi1, -aisle)] + [(dx - 140, yi0, dx + 140, yi0 + C) for dx in sdoors]
    rm = IN.Room(bays[1], rr, z, ds, key=key + (7,), ceil=wall_h - 16)
    rm.flip = True
    rooms.append(rm)
    for rm in rooms:
        if getattr(rm, "flip", False):                       # travée côté -y : on la compose dans un repère retourné
            x0, y0, x1, y1 = rm.rect
            rm.rect = (-x1, -y1, -x0, -y0)
            rm.doors = [(-d[2], -d[3], -d[0], -d[1]) for d in rm.doors]
            IN.compose(rm)
            IN.emit(v, rm, lambda lx, ly: W(-lx, -ly), yaw + 180)
        else:
            IN.compose(rm)
            IN.emit(v, rm, W, yaw)


def dome_interior(v, cx, cy, r, z, h, doors, front, back, mat):
    """Dôme : cloison droite (porte) qui isole une pièce au fond, à l'opposé de l'entrée principale."""
    T, C = 24, IN.DOOR_CLEAR
    R_ = r - 32
    u0 = (doors[0] + 180) % 360
    cu, su = math.cos(math.radians(u0)), math.sin(math.radians(u0))
    W = lambda lx, ly: (cx + lx * cu - ly * su, cy + lx * su + ly * cu)
    p = R_ * 0.38
    ch = math.sqrt((R_ + 16) ** 2 - p ** 2)
    wall_seg(v, W, u0, (p, -ch), (p, ch), z, h, mat, door=(0, 112, 176))
    hwf = 0.7 * R_
    fr = (-math.sqrt(R_ ** 2 - hwf ** 2), -hwf, p - T / 2, hwf)
    b = 0.86 * R_
    hb = min(math.sqrt(R_ ** 2 - b ** 2), math.sqrt(R_ ** 2 - (p + T) ** 2))
    br = (p + T / 2, -hb, b, hb)
    fd = [(p - T / 2 - C, -60, p - T / 2, 60)]
    for a in doors:
        la = math.radians(a - u0)
        fd.append(door_box(R_ * math.cos(la), R_ * math.sin(la), fr))
    key = ("dome", round(cx), round(cy))
    for (role, rect, ds, k) in ((front, fr, fd, 0), (back, br, [(p + T / 2, -60, p + T / 2 + C, 60)], 1)):
        rm = IN.Room(role, rect, z, ds, key=key + (k,), ceil=h - 8)
        IN.compose(rm)
        IN.emit(v, rm, W, u0, light_z=z + h - 2)


def pillbox(v, cx, cy, z, face, r=260):
    """Bunker droïde (vx.pillbox) + caisses de munitions basses : les meurtrières (56 à 112) restent dégagées."""
    VX.pillbox(v, cx, cy, z, face, r)
    q = (r - 48) * 0.68
    g = (face + 180) % 360
    rect = (-q, -q, q, q)
    W = lambda lx, ly: (cx + lx, cy + ly)
    rm = IN.Room("bunker", rect, z, [door_box((r - 48) * math.cos(math.radians(g)), (r - 48) * math.sin(math.radians(g)), rect)],
                 key=("bunker", round(cx), round(cy)), ceil=56)
    IN.compose(rm)
    IN.emit(v, rm, W, 0, light=None)


# salles préfabriquées vides du pack (relevé sur la vue de dessus Blender, shots/interieurs/prefabs) :
# sol utile, passages de portes (repère du modèle, porte principale côté -y)
PREFAB_ROOMS = {"roomempty01": ((-180, -118, 180, 180), [(-60, -118, 60, -62)]),
                "roomempty05": ((-180, -118, 180, 152), [(-60, -118, 60, -62), (-60, 96, 60, 152)])}


def prefab_interior(v, rm, x, y, z, role):
    """Meuble une salle préfabriquée vide (le modèle est un obstacle plein : seule la validation de pièce s'applique)."""
    if rm not in PREFAB_ROOMS:
        return
    rect, doors = PREFAB_ROOMS[rm]
    room = IN.Room(role, rect, z + 4, doors, key=("prefab", round(x), round(y)), ceil=150)
    IN.compose(room)
    IN.emit(v, room, lambda lx, ly: (x + lx, y + ly), 0, light_z=z + 158, check=False)


def wreck(v, model, x, y, yaw, pitch, roll, sink, why="epave"):
    """Engin renversé / enfoncé : hauteur calculée sur la boîte réellement inclinée (le point le plus bas touche le sol,
    puis enfoncé de « sink »). Le sol pris est le plus bas sous l'emprise."""
    b = VX.BOUNDS.get(model)
    if not b:
        return
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    zmin = min(-px * sp + cp * (py * sr + pz * cr) for px in (b["min"][0], b["max"][0]) for py in (b["min"][1], b["max"][1])
               for pz in (b["min"][2], b["max"][2]))
    rr = max(b["max"][0] - b["min"][0], b["max"][1] - b["min"][1]) * 0.4
    g = min(v.t.h(x + dx, y + dy) for (dx, dy) in ((0, 0), (rr, 0), (-rr, 0), (0, rr), (0, -rr)))
    v.prop(model, x, y, yaw, z=g - zmin - sink, tilt=(pitch, roll), why=why)


def gantry(v, x, y, z, span, h, axis="y"):
    """Portique de manutention : deux pylônes + poutre (brushes droits, presque sans coût en plans), crochet et câble."""
    a0, a1 = -span / 2, span / 2
    for a in (a0, a1):
        px, py = (x, y + a) if axis == "y" else (x + a, y)
        v.blk((px - 40, py - 40, z - 64, px + 40, py + 40, z + h), M["trim"])
    bx = (x - 56, y + a0 - 40, z + h, x + 56, y + a1 + 40, z + h + 72) if axis == "y" else \
        (x + a0 - 40, y - 56, z + h, x + a1 + 40, y + 56, z + h + 72)
    v.blk(bx, M["dirty"], obst=False)
    cx, cy = (x, y + span * 0.22) if axis == "y" else (x + span * 0.22, y)
    cab, clp = NIK + "construction/construction_crane_cable.mdl", NIK + "construction/construction_crane_clamp.mdl"
    if cab in VX.BOUNDS and clp in VX.BOUNDS:
        zc = z + h - VX.BOUNDS[cab]["max"][2]
        v.prop(cab, cx, cy, 0, z=zc, check=False, why="portique")
        v.prop(clp, cx, cy, 0, z=zc + VX.BOUNDS[cab]["min"][2] - VX.BOUNDS[clp]["max"][2], check=False, why="portique")


def buried_entrance(v, x, y, face, key):
    """Entrée de bunker enterrée (décor, porte fermée : rien ne change au gameplay) : cadre en béton encastré dans
    un monticule de terre, porte blindée au fond, lampe et caisses."""
    t = v.t
    c, s_ = math.cos(math.radians(face)), math.sin(math.radians(face))
    Wl = lambda lx, ly: (x + lx * c - ly * s_, y + lx * s_ + ly * c)      # +x local = vers la sortie (face)
    mx, my = Wl(-260, 0)
    t.features.append(lambda px, py, h, mx=mx, my=my: h + 130 * (1 - smoothstep(120, 520, math.hypot(px - mx, py - my))))
    z = t.h(x, y) - 24
    for sy in (-1, 1):                                                      # joues
        v.add(S.obox(*Wl(-96, sy * 104), z - 32, 256, 32, 200, face, M["conc2"], "detail"), obst=True)
    v.add(S.obox(*Wl(-112, 0), z + 168, 288, 240, 32, face, M["conc2"], "detail"), obst=False)    # dalle
    v.add(S.obox(*Wl(-232, 0), z - 32, 32, 176, 200, face, M["conc2"], "detail"), obst=True)       # fond
    v.prop(NIK + "tech/tech_reinforced_door.mdl", *Wl(-206, 0), face, z=z, check=False, why="bunker_enterre")
    v.prop(LAMP, *Wl(40, -150), 0, why="bunker_enterre")
    v.prop(NIK + "containers/crate_weapon_02.mdl", *Wl(60, 160), face + 20, why="bunker_enterre")
    zone(v, x - 400, y - 400, x + 400, y + 400, "bunker_enterre")
    v.info["Entrée de bunker"] = (x, y)
    STATS["bunkers_enterres"] = STATS.get("bunkers_enterres", 0) + 1


def platform(v, x, y, z, L, D, h, axis="x", stairs=1):
    """Plateforme technique sur pilotis (axiale = peu coûteuse) : plancher grillagé, garde-corps, escalier(s) en rampe."""
    x0, y0, x1, y1 = x - L / 2, y - D / 2, x + L / 2, y + D / 2
    v.blk((x0, y0, z + h - 16, x1, y1, z + h), M["grate"], obst=False)
    for (px, py) in ((x0 + 24, y0 + 24), (x1 - 24, y0 + 24), (x0 + 24, y1 - 24), (x1 - 24, y1 - 24)):
        v.blk((px - 16, py - 16, z - 64, px + 16, py + 16, z + h - 16), M["trim"])
    v.blk((x0, y1 - 8, z + h, x1, y1, z + h + 44), M["trim"], obst=False)                    # garde-corps arrière
    for k in range(stairs):
        sx = x0 - 448 if k == 0 else x1
        v.add(S.obox(sx + 224, y0 + 72, z - 8, 470, 128, 16, 0 if k == 0 else 180, M["grate"], "detail",
                     pitch=-math.degrees(math.atan2(h, 448))), obst=False)
    v.footprints.append((x0, y0, x1, y1))

# ================================================================== SECTEUR 1 : PLAINES DE JOBRETH
VILLAGE = (-1400, 9900)


def village(v, road_pts):
    """Village rural irrégulier : maisons le long de la route qui serpente, une petite place, des cours, des ruelles,
    un quartier touché (ruines). Tailles, orientations et états variés (aucun clone aligné)."""
    t = v.t
    vx_, vy_ = VILLAGE
    v.info["VILLAGE DE JOBRETH"] = (vx_, vy_ + 2700)
    # place du village + maison du Congrès nationaliste (petit dôme fermé)
    zp = t.h(vx_, vy_)
    t.flat_disc(vx_, vy_, 900, zp, 700)
    v.slab_disc(vx_, vy_, 640, zp + 8, M["conc"], flat=False)
    zone(v, vx_ - 900, vy_ - 900, vx_ + 900, vy_ + 900, "place")
    zcg = t.h(vx_ + 260, vy_ + 1250) + 8
    round_hall(v, vx_ + 260, vy_ + 1250, 520, zcg, 384, doors=(270, 180), roof="dome",
               wall="stone/stonewall032a", roof_mat=M["hull3"], closed=True, light="255 214 170 220")
    dome_interior(v, vx_ + 260, vy_ + 1250, 520, zcg, 384, (270, 180), "reunion", "archives", "stone/stonewall032a")
    zone(v, vx_ - 400, vy_ + 600, vx_ + 900, vy_ + 1900, "congres")
    v.info["Maison du Congrès"] = (vx_ + 260, vy_ + 2000)
    v.prop(BANNER, vx_ - 300, vy_ + 700, 270, why="village")
    v.prop(VG.md("city_statue_jedi") if "city_statue_jedi" in VG.IDX else FLAG, vx_, vy_, 180, why="village")
    # bâtiments qui structurent le village, autour de la place (essais d'angles jusqu'à trouver un terrain libre)
    for (kind, rr) in (("maire", 1500), ("epicerie", 1450), ("atelier", 1700), ("coop", 2500), ("chateau_eau", 1900)):
        for k in range(120):
            a = R.uniform(0, 2 * math.pi)
            r_ = rr + R.uniform(-200, 900)
            x, y = vx_ + r_ * math.cos(a), vy_ + r_ * math.sin(a)
            if sector(x, y) != 1 or in_zone(v, x, y, 620) or v.t.on_track(x, y, 600):
                continue
            landmark(v, kind, x, y, math.degrees(a) - 90)        # façade (-y local) tournée vers la place
            break
    # îlots en U autour d'une cour fermée (impasse) : trois maisons de tailles différentes tournées vers la cour
    placed = 0
    v._houses = []
    RUIN = (vx_ + 2000, vy_ - 1300)                       # quartier bombardé : l'obus est tombé ici, les maisons autour sont détruites
    v.info["Quartier bombardé"] = RUIN
    def st(x, y):
        dr = math.hypot(x - RUIN[0], y - RUIN[1])
        if dr < 1500:
            return R.choices(["endommage", "ruine"], [0.35, 0.65])[0]
        return R.choices(["intact", "endommage", "ruine"], [0.6, 0.3, 0.1])[0]
    for k in range(160):
        if placed >= 9:
            break
        a, r = R.uniform(0, 2 * math.pi), R.uniform(1700, 4300)
        ox, oy = vx_ + r * math.cos(a), vy_ + r * 0.85 * math.sin(a)
        by = math.degrees(a) + 180 + R.uniform(-35, 35)       # la cour s'ouvre vers le village
        c_, s_ = math.cos(math.radians(by)), math.sin(math.radians(by))
        WL = lambda lx, ly: (ox + lx * c_ - ly * s_, oy + lx * s_ + ly * c_)
        spec = [((0, 660), 0, R.choice([(640, 448), (768, 448), (704, 512)])),
                ((-720, 40), 90, R.choice([(512, 384), (448, 384), (576, 448)])),
                ((720, -60), -90, R.choice([(448, 320), (512, 448), (384, 320)]))]
        if R.random() < 0.35:
            spec.pop(2)                                    # îlot en L
        pos = [(WL(*lp), yo, wd) for (lp, yo, wd) in spec]
        if sector(ox, oy) != 1 or in_zone(v, ox, oy, 800) or v.t.on_track(ox, oy, 850)                 or any(math.hypot(ox - hx, oy - hy) < 1700 for (hx, hy) in v._houses):
            continue
        for ((hx, hy), yo, (w, d)) in pos:
            s = st(hx, hy)
            house(v, hx, hy, w, d, by + yo, state=s, floors=2 if (s == "intact" and w >= 576 and R.random() < 0.5) else 1)
            v._houses.append((hx, hy))
            zone(v, hx - w / 2 - 80, hy - d / 2 - 80, hx + w / 2 + 80, hy + d / 2 + 80, "maison")
            placed += 1
        zone(v, ox - 500, oy - 500, ox + 500, oy + 500, "cour")
        v._houses.append((ox, oy))
        for (lx, ly, mdl) in ((R.uniform(-200, 200), R.uniform(0, 250), R.choice(CRATES[:2])),
                              (R.uniform(-250, 250), R.uniform(-150, 150), VG.md("city_firebarrel")),
                              (R.uniform(-300, 300), -420, VG.md("fence03a"))):
            v.prop(mdl, *WL(lx, ly), by + R.uniform(-20, 20), why="cour")
    STATS["ilots"] = placed
    # maisons isolées le long de la route (orientées vers elle) et dans les champs proches
    near = [p for p in road_pts if math.hypot(p[0] - vx_, p[1] - vy_) < 3600]
    tries = 0
    while placed < 15 and tries < 900:            # qualité > quantité (brief) : moins de maisons génériques
        tries += 1
        if near and R.random() < 0.65:
            p = R.choice(near)
            i = road_pts.index(p)
            q = road_pts[min(i + 1, len(road_pts) - 1)]
            ang = math.atan2(q[1] - p[1], q[0] - p[0])
            side = R.choice((-1, 1))
            off = R.uniform(560, 900)
            x, y = p[0] - math.sin(ang) * off * side, p[1] + math.cos(ang) * off * side
            yaw = math.degrees(ang) + (0 if side > 0 else 180)
        else:
            a, r = R.uniform(0, 2 * math.pi), R.uniform(1200, 3600)
            x, y = vx_ + r * math.cos(a), vy_ + r * 0.8 * math.sin(a)
            yaw = math.degrees(a) + 90 + R.uniform(-25, 25)
        w, d = R.choice([(448, 384), (512, 448), (640, 448), (704, 512), (576, 576), (768, 448), (384, 320)])
        if in_zone(v, x, y, max(w, d) * 0.6) or v.t.on_track(x, y, max(w, d) * 0.7) or sector(x, y) != 1 \
                or any(math.hypot(x - fx, y - fy) < 820 for (fx, fy) in v._houses):
            continue
        state = st(x, y)
        house(v, x, y, w, d, yaw, state=state, floors=2 if (state == "intact" and w >= 576 and R.random() < 0.6) else 1,
              roof_kind="flat" if R.random() < 0.2 else "gable")
        v._houses.append((x, y))
        zone(v, x - w / 2 - 80, y - d / 2 - 80, x + w / 2 + 80, y + d / 2 + 80, "maison")
        placed += 1
        # petite cour : muret, caisses, brasero
        if R.random() < 0.4:
            c_, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            fx, fy = x - (d / 2 + 260) * -s_, y - (d / 2 + 260) * c_
            v.prop(VG.md("fence03a"), fx, fy, yaw, why="cour")
            v.prop(R.choice(CRATES[:2] + [VG.md("city_firebarrel")]), fx + 120, fy, R.uniform(0, 360), why="cour")
    STATS["village"] = placed


def farm(v, x, y, yaw, name):
    """Ferme : maison, grange voûtée, silo, clôture brisée autour d'un champ, matériel abandonné."""
    t = v.t
    z = t.h(x, y)
    t.flat_disc(x, y, 1300, z, 800)
    zone(v, x - 1400, y - 1400, x + 1400, y + 1400, "ferme")
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    W = lambda lx, ly: (x + lx * c - ly * s, y + lx * s + ly * c)
    house(v, *W(-600, 300), 640, 448, yaw, state=R.choice(["intact", "endommage"]), floors=2)
    Wg = vault_hall(v, *W(500, 300), z, 1024, 640, 256, 224, yaw, mat=M["wall2"], side_doors=False)
    hall_interior(v, Wg, yaw, ("grange", round(x), round(y)), z, 1024, 640, 256, False, 640 * 0.55, mat=M["wall2"])
    silo(v, *W(450, -500), 220, z, 760)
    for k in range(10):
        if R.random() < 0.25:
            continue                                      # clôture brisée
        v.prop(VG.md("fence03a"), *W(-900 + k * 180, -1000), yaw, why="cloture")
    v.prop(VG.md("generatortrailer01"), *W(0, -400), yaw + 30, why="ferme")
    v.info[name] = (x, y + 1500)
    STATS["fermes"] = STATS.get("fermes", 0) + 1


def plains(v, road_pts):
    village(v, road_pts)
    for (x, y, yaw, nm) in ((-9800, 8600, 15, "Ferme Lars"), (-6200, 11300, -20, "Ferme Kessel"), (4800, 8000, 40, "Ferme du gué"),
                            (9400, 10900, -10, "Ferme de la colline"), (-11400, 5600, 80, "Ferme de l'ouest")):
        farm(v, x, y, yaw, nm)
    v.info["SECTEUR 1 — PLAINES DE JOBRETH"] = (0, 13300)


def battle_details(v, road_pts):
    """Étape 5 du brief : traces d'une bataille déjà engagée, en petites scènes qui racontent quelque chose
    (pas de props semés au hasard) : barricades improvisées, quartier bombardé, épaves qui brûlent, matériel abandonné."""
    t = v.t
    rnd = __import__("random").Random(29)
    md = VG.md
    n0 = len(v.props) if hasattr(v, "props") else 0
    smoke = lambda x, y, z, size=420, col="52 50 48": v.fx.append(("smoke", (x, y, z), {"rate": 6, "size": size, "color": col}))
    def fire(x, y, z, size=120):                          # le feu éclaire le sol et l'épave (lumière statique orangée)
        v.fx.append(("fire", (x, y, z), {"size": size}))
        v.light(x, y, z + 80, "255 132 54 %d" % (size + 90))
    # --- S1 : barricades improvisées en travers de la route du village (voitures, caisses, barrières), passage laissé
    vx_, vy_ = VILLAGE
    cands = [i for i, p in enumerate(road_pts) if 1500 < math.hypot(p[0] - vx_, p[1] - vy_) < 3600]
    picked = []
    for i in cands:
        if all(abs(i - j) > 6 for j in picked) and len(picked) < 4:
            picked.append(i)
    for i in picked:
        p, q = road_pts[i], road_pts[min(i + 1, len(road_pts) - 1)]
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        nx, ny = -math.sin(ang), math.cos(ang)
        gap = rnd.choice((-1, 1)) * rnd.uniform(60, 140)           # chicane : un passage d'homme, pas de véhicule
        items = [md("car002b"), BARR, md("con_crate_04_broken"), BARR, md("und_barricade"), md("car003a")]
        rnd.shuffle(items)
        k = 0
        for off in (-300, -180, -60, 60, 180, 300):
            if abs(off - gap) < 110:
                continue
            x, y = p[0] + nx * off, p[1] + ny * off
            v.prop(items[k % len(items)], x, y, math.degrees(ang) + 90 + rnd.uniform(-25, 25), why="barricade")
            k += 1
    v.info["Barricades du village"] = road_pts[picked[0]] if picked else (vx_, vy_)
    # --- S1 : quartier bombardé (gravats, pans de murs, fumées) — les cratères sont creusés dans le relief
    rx, ry = vx_ + 2000, vy_ - 1300
    for k in range(9):
        a, d = rnd.uniform(0, 2 * math.pi), rnd.uniform(300, 1300)
        v.prop(rnd.choice([md("ruins_rubble_01_a"), md("ruins_rubble_02_c"), md("concrete_debris256pile001a"),
                           md("walldestroyed03a"), md("ruins_rubble_02_f")]), rx + d * math.cos(a), ry + d * math.sin(a),
               rnd.uniform(0, 360), sink=6, why="bombarde")
    for (dx, dy) in ((-300, 200), (500, -500)):
        smoke(rx + dx, ry + dy, t.h(rx + dx, ry + dy) + 40, 520)
    # --- S1 : speeder abattu dans un champ, encore en feu ; voiture abandonnée sur la route de l'ouest
    for (x, y, yaw) in ((-7600, 7000, 30), (6400, 9600, 200)):
        z = t.h(x, y)
        v.prop(md("veh_neu_speeder_02_wreckage"), x, y, yaw, why="epave")
        v.prop(md("veh_neu_speeder_02_debris"), x + 260, y - 120, yaw + 40, why="epave")
        fire(x, y, z + 24, 90)
        smoke(x, y, z + 80, 460)
    for (x, y, yaw, m) in ((-8900, 9300, 160, "truck001a"), (-4600, 10500, 80, "car004a"), (2800, 12300, 15, "car005a")):
        v.prop(md(m), x, y, yaw, why="epave")
    # --- S1 : traces de l'attaque droïde à l'entrée du village (pièces détachées de droïdes)
    for k in range(5):
        x, y = vx_ - 1700 + rnd.uniform(-500, 500), vy_ - 2300 + rnd.uniform(-400, 400)
        v.prop(rnd.choice([md("debris_droid_parts_hk51_torso"), md("debris_droid_parts_hk51_arm"), md("debris_droid_parts_hk51_head"),
                           md("debris_droid_parts_hk51_group01")]), x, y, rnd.uniform(0, 360), why="droides")
    # --- S2 : séparatistes retranchés dans les installations (barricades aux accès, tourelle détruite, conteneurs crevés)
    for (x, y, yaw) in ((5200, 2400, 90), (5400, 1700, 90), (7600, 3900, 0), (9300, -700, 180)):
        v.prop(rnd.choice([BARR, md("und_barricade")]), x, y, yaw, why="sep_mine")
    v.prop(BANNER, 6000, 3400, 180, why="sep_mine")
    v.prop(md("neu_autoturret01_destroyed"), 8700, 900, 210, why="sep_mine")
    v.prop(md("droideka_dispenser"), 7300, 1500, 130, why="sep_mine")
    for (x, y) in ((-2400, -900), (-3200, 2600), (600, 2800)):          # matériel minier abandonné sur les gradins
        v.prop(rnd.choice([md("con_tank_toxic_damaged_01"), md("tech_canister_destroyed"), md("debris_generic_engine_01_env")]),
               x, y, rnd.uniform(0, 360), why="mine_abandon")
    # --- S3 : les AT-TE abattus brûlent encore ; débris de droïdes et caisses éventrées dans le no man's land
    for (ax, ay) in ((-5600, -6700), (3600, -6200), (9300, -6900)):
        z = t.h(ax, ay)
        fire(ax, ay, z + 40, 150)                                    # le feu sur l'épave, la fumée part du feu
        smoke(ax, ay, z + 70, 460, "44 42 40")
    for (x, y) in poisson(-12500, -7800, 12500, -4800, 1500, rnd)[:22]:
        if in_zone(v, x, y, 200):
            continue
        v.prop(rnd.choice([md("destroyed_astromech_rep_a01"), md("debris_droid_parts_hk51_whole"), md("con_square_crate_broken"),
                           md("rep_crate_02_broken"), md("ruins_rubble_01_c"), md("tech_canister_destroyed")]),
               x, y, rnd.uniform(0, 360), why="nomansland")
    for (x, y, r) in CRATERS[::2] + CRATERS[-3:]:            # fond des cratères noirci par l'explosion
        v.w.ent("infodecal", (x, y, t.h(x, y) + 2), texture=rnd.choice(["decals/scorch1", "decals/scorch2"]))
    # village : lampadaires le long de la route (certains abattus), panneaux aux entrées, zone de stockage
    for i in range(0, len(road_pts), 3):
        x, y = road_pts[i]
        if 900 < math.hypot(x - vx_, y - vy_) < 3800 and i + 1 < len(road_pts):
            q = road_pts[i + 1]
            ang = math.atan2(q[1] - y, q[0] - x)
            lx, ly = x - math.sin(ang) * 300, y + math.cos(ang) * 300
            if rnd.random() < 0.3:
                v.prop(NIK + "city/city_street_lamp_dmg.mdl", lx, ly, math.degrees(ang), why="lampadaire")
            else:
                v.prop(NIK + "republic/rep_lamppost.mdl", lx, ly, 0, why="lampadaire")
                v.light(lx, ly, t.h(lx, ly) + 140, "255 220 170 120")
    for (x, y) in ((vx_ - 3300, vy_ - 900), (vx_ + 3200, vy_ + 900)):
        v.prop(NIK + "city/city_sign_small.mdl", x, y, rnd.uniform(0, 360), why="panneau")
    STATS["details_bataille"] = "barricades %d, scènes S1/S2/S3" % len(picked)


def poisson(x0, y0, x1, y1, r, rng, k=30, accept=None):
    """Échantillonnage en disque de Poisson (Bridson) : points espacés d'au moins r, sans amas ni alignement
    (skill procedural-gen, gamedev-skills/awesome-gamedev-agent-skills, Apache-2.0). accept(x, y) filtre les points."""
    cs = r / math.sqrt(2)
    gw, gh = int((x1 - x0) / cs) + 1, int((y1 - y0) / cs) + 1
    grid = {}
    first = (rng.uniform(x0, x1), rng.uniform(y0, y1))
    pts, active = [first], [first]
    grid[(int((first[0] - x0) / cs), int((first[1] - y0) / cs))] = first
    while active:
        i = rng.randrange(len(active))
        bx, by = active[i]
        for _ in range(k):
            a, d = rng.uniform(0, 2 * math.pi), rng.uniform(r, 2 * r)
            x, y = bx + d * math.cos(a), by + d * math.sin(a)
            if not (x0 <= x < x1 and y0 <= y < y1):
                continue
            gx, gy = int((x - x0) / cs), int((y - y0) / cs)
            if any(math.hypot(x - q[0], y - q[1]) < r for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)
                   for q in [grid.get((gx + dx, gy + dy))] if q):
                continue
            grid[(gx, gy)] = (x, y)
            pts.append((x, y))
            active.append((x, y))
            break
        else:
            active.pop(i)
    return [p for p in pts if accept is None or accept(*p)]


def check_reach(v, step=128, max_slope=0.9):
    """Validation (skill level-design : « critical path solvable », pas de cul-de-sac) : remplissage depuis le spawn
    sur une grille de marche (pente < ~42°, dans le mur invisible, hors emprises de bâtiments) ; liste les lieux nommés
    injoignables à pied."""
    t = v.t
    nx, ny = int(2 * PX / step), int(2 * PY / step)
    blocked = set()
    for (a, b, c, d) in v.footprints:
        for i in range(int((a + PX) // step) + 1, int((c + PX) // step)):
            for j in range(int((b + PY) // step) + 1, int((d + PY) // step)):
                blocked.add((i, j))
    ok = lambda i, j: 0 <= i < nx and 0 <= j < ny and (i, j) not in blocked and         t.slope(-PX + (i + 0.5) * step, -PY + (j + 0.5) * step) < max_slope
    sx, sy = v.spawns[0][:2]
    start = (int((sx + PX) // step), int((sy + PY) // step))
    seen, todo = {start}, [start]
    while todo:
        i, j = todo.pop()
        for (di, dj) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (i + di, j + dj)
            if q not in seen and ok(*q):
                seen.add(q)
                todo.append(q)
    bad = []
    for name, (x, y) in v.info.items():
        if not (-PX < x < PX and -PY < y < PY) or "caverne" in name.lower() or "sous la mine" in name:
            continue
        ci, cj = int((x + PX) // step), int((y + PY) // step)
        if not any((ci + di, cj + dj) in seen for di in range(-6, 7) for dj in range(-6, 7)):
            bad.append(name)
    STATS["joignable"] = f"{len(seen)}/{nx * ny} cases ; lieux injoignables : {bad or 'aucun'}"
    try:                                                   # carte de marche (vert = joignable, rouge = trop raide, noir = bâti)
        from PIL import Image
        im = Image.new("RGB", (nx, ny))
        for i in range(nx):
            for j in range(ny):
                im.putpixel((i, ny - 1 - j), (60, 170, 70) if (i, j) in seen else (0, 0, 0) if (i, j) in blocked
                            else (200, 50, 40) if not ok(i, j) else (90, 90, 90))
        out = os.path.join(os.path.dirname(__file__), "..", "shots", "squelette", "marche.png")
        im.resize((nx * 4, ny * 4), Image.NEAREST).save(out)
    except Exception as e:
        print("  carte de marche :", e)
    return bad


def vegetation(v):
    """Végétation par secteur : bosquets et haies dans les plaines, arbres morts épars sur le front, rochers dans le bassin."""
    rnd = R
    centres = poisson(-PX + 700, -PY + 700, PX - 700, PY - 700, 2300, rnd)
    rnd.shuffle(centres)
    for (cx, cy) in centres[:52]:                          # bosquets espacés (disque de Poisson) : jamais en grille
        s = sector(cx, cy)
        if in_zone(v, cx, cy, 300) or v.t.on_track(cx, cy, 300):
            continue
        pool = TREES if s == 1 else (DEAD if s == 3 else TREES[:2] + DEAD)
        n = rnd.randint(6, 14) if s == 1 else rnd.randint(3, 7)
        rr = rnd.uniform(350, 700)
        for _ in range(n):
            a, d = rnd.uniform(0, 2 * math.pi), rr * math.sqrt(rnd.random())
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if not in_zone(v, x, y) and not v.t.on_track(x, y, 120):
                v.prop(rnd.choice(pool) if rnd.random() < 0.7 else rnd.choice(SHRUBS), x, y, rnd.uniform(0, 360), why="bosquet", sink=8)
    for (x, y) in poisson(-PX + 500, -PY + 500, PX - 500, PY - 500, 950, rnd):   # rochers sur les pentes, arbres morts
        x, y = x + rnd.uniform(-80, 80), y + rnd.uniform(-80, 80)
        if in_zone(v, x, y) or v.t.on_track(x, y, 200):
            continue
        if v.t.slope(x, y) > 0.3:
            v.prop(rnd.choice(ROCKS), x, y, rnd.uniform(0, 360), sink=24, why="nature")
        elif sector(x, y) == 3 and rnd.random() < 0.3:
            v.prop(rnd.choice(DEAD), x, y, rnd.uniform(0, 360), why="nature")
    for _ in range(190):                                   # au-delà du mur : forêts et montagnes (référence)
        side = rnd.randrange(4)
        d = rnd.uniform(250, 1900)
        if side < 2:
            x, y = (-PX - d if side == 0 else PX + d), rnd.uniform(-PY, PY)
        else:
            x, y = rnd.uniform(-PX, PX), (-PY - d if side == 2 else PY + d)
        v.prop(rnd.choice(TREES + ROCKS), x, y, rnd.uniform(0, 360), sink=40, why="horizon", check=False)


# ================================================================== assemblage
def build_all():
    pack_bounds(REEDS + VG.PF_ALL)
    lines, saps, comms = trench_network()
    v = JV("jabiim")
    v.w.space("jabiim", "jabiim", (XA, YA, FLOOR, XB, YB, CEIL), sky=True, floor="tools/toolsnodraw", wall="tools/toolsskybox",
              light=None)
    T = 32
    for b in ((-PX - T, -PY - T, FLOOR, -PX, PY + T, CEIL), (PX, -PY - T, FLOOR, PX + T, PY + T, CEIL),
              (-PX, -PY - T, FLOOR, PX, -PY, CEIL), (-PX, PY, FLOOR, PX, PY + T, CEIL)):
        v.w.block(b, "tools/toolsclip", "world")
    relief(v, lines)
    road_lines = roads(v)
    front(v, lines, saps, comms)
    mine(v)
    plains(v, road_lines[0])
    v.info["SECTEUR 2 — BASSIN MINIER"] = (6000, 5200)
    v.info["SECTEUR 3 — FRONT DE JABIIM"] = (-9000, -12800)
    skybox(v)
    vc = JV("hyber")
    vc.has_t = False
    caves(vc)
    shafts(v, vc)
    outposts(v)
    vegetation(v)
    battle_details(v, road_lines[0])
    v.resolve()
    vc.resolve()
    bad = check_reach(v)
    det = {k: n for k, n in v.rej.items() if k in ("barricade", "bombarde", "epave", "droides", "sep_mine", "mine_abandon", "nomansland")}
    print("  détails de bataille refusés (collision) :", det or "aucun")
    print("  connectivité :", STATS["joignable"])
    return [("jabiim", v, 0), ("hyber", vc, CAVE_DZ)]


def viscells(v, dz):
    cells = [(XA, YA, 2560 + dz, XB, YB, CEIL + dz)]
    for x0 in range(XA, XB, 4096):
        for y0 in range(YA, YB, 4096):
            x1, y1 = min(x0 + 4096, XB), min(y0 + 4096, YB)
            hmax = max(v.gz(x, y) for x in range(x0, x1 + 1, 512) for y in range(y0, y1 + 1, 512))
            bot = max(900, int((hmax + 600) // 16 + 1) * 16)
            if bot < 2560:
                cells.append((x0, y0, bot + dz, x1, y1, 2560 + dz))
    return cells


def shafts(v, vc):
    """Puits de 1024 x 1024 entre la surface (v) et les cavernes (vc) : dalle de terrain retirée, parois, margelle,
    chevalement, rampe en spirale ; le puits de la mine ouvre en plus la grande galerie de roulage vers la prison."""
    t = v.t
    for name, (hx, hy) in SHAFTS.items():
        cx, cy = hx + 512, hy + 512
        zs = int(t.h(cx, cy) // 16) * 16
        t.holes.add((hx, hy))
        t.flat_rect(hx - 256, hy - 256, hx + 1280, hy + 1280, zs - 8, 700)
        zone(v, hx - 700, hy - 700, hx + 1724, hy + 1724, "puits")
        v.clear.append((cx, cy, 1200))
        v.w.carve.append((hx, hy, FLOOR - 64, hx + 1024, hy + 1024, FLOOR + 64))
        for b in ((hx - 64, hy - 64, hx + 1088, hy), (hx - 64, hy + 1024, hx + 1088, hy + 1088),
                  (hx - 64, hy, hx, hy + 1024), (hx + 1024, hy, hx + 1088, hy + 1024)):
            v.blk((b[0], b[1], FLOOR, b[2], b[3], zs + 16), M["conc2"], kind="world", top=M["hazard"])
        for (a0, b0, a1, b1) in ((hx - 448, hy - 448, hx + 1472, hy - 64), (hx - 448, hy + 1088, hx + 1472, hy + 1472),
                                 (hx - 448, hy - 64, hx - 64, hy + 1088), (hx + 1088, hy - 64, hx + 1472, hy + 1088)):
            v.blk((a0, b0, zs - 48, a1, b1, zs + 16), M["conc"], ground=True, obst=False)
        # chevalement en pyramide : 4 jambes inclinées vers une cabine de treuil, molette, feu rouge (plus de « table »)
        top = zs + 1150
        for (px, py) in ((hx - 192, hy - 192), (hx + 1216, hy - 192), (hx - 192, hy + 1216), (hx + 1216, hy + 1216)):
            tx, ty = cx + (160 if px > cx else -160), cy + (160 if py > cy else -160)
            hl = math.hypot(tx - px, ty - py)
            L3 = math.hypot(hl, top - zs)
            v.add(S.obox((px + tx) / 2, (py + ty) / 2, (zs + top) / 2 - 28, L3, 56, 56, math.degrees(math.atan2(ty - py, tx - px)),
                         M["dirty"], "detail", pitch=-math.degrees(math.atan2(top - zs, hl))), obst=True)
            v.add(S.cylinder(px, py, 72, zs - 32, zs + 48, M["conc"], "detail", 8), obst=True)          # semelle béton
        for k in (0.35, 0.65):                                                                         # entretoises
            r = 704 - 544 * k
            zk = zs + (top - zs) * k
            v.blk((cx - r, cy - r, zk, cx + r, cy - r + 32, zk + 32), M["trim"], obst=False)
            v.blk((cx - r, cy + r - 32, zk, cx + r, cy + r, zk + 32), M["trim"], obst=False)
        v.blk((cx - 224, cy - 224, top - 16, cx + 224, cy + 224, top + 224), M["hull3"])                 # cabine de treuil
        v.add(S.obox(cx, cy, top + 224, 400, 40, 300, 0, M["dirty"], "detail"), obst=False)          # molette (flasque)
        v.add(S.cylinder(cx, cy, 40, top + 224, top + 300, M["redlight"], "detail", 8), obst=False)
        v.light(cx, cy, zs + 840, "255 186 120 320")
        v.info[{"mine": "Puits principal (fond de la mine)", "nord": "Vieille tête de mine", "sud": "Puits bombardé"}[name]] = (cx, hy + 1500)
        top_local = zs + 16 - CAVE_DZ
        vc.w.space(f"puits_{name}", "mine", (hx, hy, 0, hx + 1024, hy + 1024, FLOOR - CAVE_DZ), floor=EARTH, wall=M["rock"],
                   ceil=M["rock"], light="255 186 120 260", light_step=512)
        vc.w.carve.append((hx, hy, FLOOR - CAVE_DZ - 64, hx + 1024, hy + 1024, top_local + 900))
        vc.add(S.cylinder(cx, cy, 200, 0, top_local, M["rock"], "world", 8))
        spiral(vc, cx, cy, top_local, 16)
        for (r, ct) in vc.cave_t:
            if r[0] <= cx <= r[2] and r[1] <= cy <= r[3]:
                ct.flat_rect(hx - 128, hy - 128, hx + 1152, hy + 1152, 8, 500)
        vc.blk((hx, hy, -48, hx + 1024, hy + 1024, 16), M["floor"], ground=True, obst=False)
        if name == "mine":                       # grande galerie de roulage : du fond de la mine jusqu'au camp de prisonniers
            gy0, gy1 = hy + 192, hy + 832
            x0g = hx + 1024
            vc.w.space("galerie", "mine", (x0g, gy0, 0, 7168, gy1, 512), floor=EARTH, wall=M["rock"], ceil=M["rock"],
                       light="255 186 120 280", light_step=896)
            areaportal(vc, (x0g, gy0, 0, x0g + 16, gy1, 512))
            areaportal(vc, (7168 - 16, gy0, 0, 7168, gy1, 512))
            for dy in (-96, 96):
                vc.blk((x0g, (gy0 + gy1) // 2 + dy - 12, 0, 7168, (gy0 + gy1) // 2 + dy + 12, 10), M["trim"])
            vc.blk((x0g, gy0, -48, 7168, gy1, 0), EARTH, ground=True, obst=False)
            for k in range(6):
                vc.prop(NIK + "tech/tech_mine_barrel.mdl", x0g + 900 + k * 1100, (gy0 + gy1) / 2, 0, why="galerie")
            for gx_ in range(x0g + 320, 7168 - 200, 448):                               # cadres de soutènement (axiaux : peu chers)
                for (a0, a1) in ((gy0, gy0 + 40), (gy1 - 40, gy1)):
                    vc.blk((gx_, a0, 0, gx_ + 40, a1, 440), "wood/woodwall009a")
                vc.blk((gx_, gy0, 440, gx_ + 40, gy1, 480), "wood/woodwall009a", obst=False)
                if (gx_ // 448) % 3 == 0:
                    vc.prop(NIK + "city/city_hanging_light.mdl", gx_ + 20, (gy0 + gy1) / 2, 0, z=420, why="galerie")
                    vc.light(gx_ + 20, (gy0 + gy1) / 2, 400, "255 190 120 140")
            for k in range(5):
                vc.prop(R.choice([NIK + "containers/con_box_crate_06.mdl", NIK + "imperial/imp_crate_02_x04.mdl",
                                  NIKR + "rep_pallet_02.mdl"]), x0g + 500 + k * 1250, gy0 + 90, R.uniform(-15, 15), why="galerie")
            v.info["Galerie de roulage (sous la mine) -> cavernes"] = (3000, 1900)
    STATS["puits"] = len(SHAFTS)


def spiral(v, cx, cy, ztop, zbot):
    """Rampe hélicoïdale dans un puits de 1024 : couloir de 320 entre le pilier (rayon ~200) et la paroi,
    paliers plats aux 4 coins, rampes de 384 qui descendent de 192 (pente 0,5)."""
    from geom import slope_slab
    a, b = 192, 512
    corners = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
    z, i = ztop, 0

    def landing(c, zz):
        x0, x1 = sorted((cx + c[0] * a, cx + c[0] * b))
        y0, y1 = sorted((cy + c[1] * a, cy + c[1] * b))
        v.blk((x0, y0, zz - 24, x1, y1, zz), M["grate"], ground=True, obst=False)
    landing(corners[0], z)
    while z - 192 >= zbot:
        c, n = corners[i % 4], corners[(i + 1) % 4]
        if c[0] == n[0]:                        # côté est ou ouest : la rampe court le long de y
            x0, x1 = sorted((cx + c[0] * a, cx + c[0] * b))
            y0, y1 = sorted((cy + c[1] * a, cy + n[1] * a))
            rise = "+y" if c[1] > n[1] else "-y"
        else:                                   # côté nord ou sud : le long de x
            y0, y1 = sorted((cy + c[1] * a, cy + c[1] * b))
            x0, x1 = sorted((cx + c[0] * a, cx + n[0] * a))
            rise = "+x" if c[0] > n[0] else "-x"
        v.add(slope_slab(x0, y0, x1, y1, z - 192, z, rise, thick=24, mat=M["grate"]), obst=False)
        z -= 192
        landing(n, z)
        if i % 4 == 3:
            v.light(cx + 352, cy + 352, z + 140, "255 186 120 160")
        i += 1


def skybox(v):
    """Ciel 3D (recette Vexis, échelle 1/16) : montagnes à l'horizon, flotte républicaine en orbite basse sous l'orage."""
    room = (-4096, -4096, 6144, 4096, 4096, 8192)
    cz = 6144 + 32 + (0 - FLOOR) // 16
    v.w.space("ciel3d", "ciel", room, sky=True, floor="tools/toolsnodraw", wall="tools/toolsskybox", light=None)
    v.w.block((room[0], room[1], room[2], room[3], room[4], cz - 24), "nature/dirtfloor011a", "detail")
    v.w.ent("sky_camera", (0, 0, cz), scale=16, fogenable=1, fogcolor="112 120 118", fogcolor2="112 120 118", fogdir="1 0 0",
            fogstart=200, fogend=3200, fogmaxdensity=0.7, use_angles=0)
    v.sky_props = [("models/vxl/sky_venator_class_cruiser_22.mdl", -1800, 2200, 900, 210),
                   ("models/vxl/sky_venator_class_cruiser_20.mdl", -2600, 1200, 1050, 200),
                   ("models/vxl/sky_venator_class_cruiser_22.mdl", 900, 2600, 1150, 230),
                   ("models/vxl/sky_munificent_class_18.mdl", 2500, -1800, 980, 30),
                   ("models/vxl/sky_munificent_class_20.mdl", 3000, -400, 1100, 15)]
    v.sky_props = [(m, x, y, cz + z, yaw) for (m, x, y, z, yaw) in v.sky_props]


# ================================================================== EST (sous la montagne) : RÉSEAU DE CAVERNES
CAVES = {   # nom : (x0, y0, x1, y1, plafond)   (multiples de 1024 : dalles de déplacement)
    "mine": (7168, 5120, 12288, 12288, 1792),
    "prison": (7168, -3072, 12288, 3072, 1792),
    "lac": (7168, -12288, 12288, -5120, 2048),
    "commandement": (12800, -7168, 15872, 7168, 2048),
}
CZ0 = -512
TH = 512


def cave_rocks(v, box, n_per=1.0, avoid=(), big=False):
    """Parois de caverne naturelle : blocs de roche irréguliers + stalactites (func_detail)."""
    x0, y0, z0, x1, y1, z1 = box
    h = z1 - z0
    out = 0
    for side in ("x0", "x1", "y0", "y1"):
        along_x = side in ("y0", "y1")
        u = (x0 if along_x else y0) + 64
        end = (x1 if along_x else y1) - 64
        while u < end:
            w = R.randrange(448, 960 if big else 704, 16)
            d = R.randrange(48, 112, 16) if min(x1 - x0, y1 - y0) < 900 else R.randrange(96, 384 if big else 224, 16)
            hh = R.randrange(int(h * 0.4), int(h * 0.98) + 1, 16)
            if along_x:
                yb = y0 if side == "y0" else y1 - d
                pts = [(u, yb, z0 - 8), (u + w, yb, z0 - 8), (u, yb + d, z0 - 8), (u + w, yb + d, z0 - 8),
                       (u + R.randrange(16, 96), yb + (0 if side == "y0" else d), z0 + hh),
                       (u + w - R.randrange(16, 96), yb + (0 if side == "y0" else d), z0 + hh - R.randrange(0, 160)),
                       (u + w // 2, yb + (d * 0.25 if side == "y0" else d * 0.75), z0 + hh * 0.55)]
            else:
                xb = x0 if side == "x0" else x1 - d
                pts = [(xb, u, z0 - 8), (xb, u + w, z0 - 8), (xb + d, u, z0 - 8), (xb + d, u + w, z0 - 8),
                       (xb + (0 if side == "x0" else d), u + R.randrange(16, 96), z0 + hh),
                       (xb + (0 if side == "x0" else d), u + w - R.randrange(16, 96), z0 + hh - R.randrange(0, 160)),
                       (xb + (d * 0.25 if side == "x0" else d * 0.75), u + w // 2, z0 + hh * 0.55)]
            rb = (min(p[0] for p in pts) - 96, min(p[1] for p in pts) - 96, z0 - 64, max(p[0] for p in pts) + 96,
                  max(p[1] for p in pts) + 96, z0 + hh)
            free = not any(rb[0] < a[3] and a[0] < rb[3] and rb[1] < a[4] and a[1] < rb[4] and rb[2] < a[5] and a[2] < rb[5]
                           for a in avoid)
            if free and R.random() < 0.85 * n_per:
                piece = S.hull_piece(pts, M["rock"], "detail")
                bb = piece.bbox                   # enveloppe dégénérée (ouverte) : on jette la roche
                if (len(piece.planes) >= 5 and bb[0] >= x0 - 8 and bb[3] <= x1 + 8 and bb[1] >= y0 - 8 and bb[4] <= y1 + 8
                        and bb[2] >= z0 - 16 and bb[5] <= z1 + 8):
                    v.w.add(piece)
                    out += 1
            u += w + R.randrange(0, 192, 16)
    for _ in range(int((x1 - x0) * (y1 - y0) / (900 * 900) * n_per)):
        sx, sy = R.uniform(x0 + 160, x1 - 160), R.uniform(y0 + 160, y1 - 160)
        r = R.randrange(48, 160 if big else 96, 16)
        ln = R.randrange(128, max(160, int(h * (0.35 if big else 0.3))), 16)
        v.w.add(S.cone(round(sx), round(sy), r, 8, z1 - ln, z1 + 8, M["rock"], "detail", 6))
        out += 1
    STATS["roches"] = STATS.get("roches", 0) + out


def caves(v):
    w = v.w
    LT, LC, RK = "255 186 120 300", "255 120 90 240", M["rock"]
    tunnels = []
    cts = {}
    for name, (x0, y0, x1, y1, h) in CAVES.items():
        w.space(name, "mine", (x0, y0, CZ0, x1, y1, h), floor="tools/toolsnodraw", wall=RK, ceil=RK,
                light=LC if name == "commandement" else LT, light_step=1024)
        ct = CaveFloor(x0, y0, x1, y1, CZ0)
        ct.default_mat = MUDT
        ct.regions = [(lambda x, y: fbm(x / 1500, y / 1500, 2, 97) > 0.25, ROCKT)]
        v.cave_t.append(((x0, y0, x1, y1), ct))
        cts[name] = ct

    def tunnel(name, box, axis):
        x0, y0, x1, y1 = box
        w.space(name, "mine", (x0, y0, 0, x1, y1, TH), floor=EARTH, wall=RK, ceil=RK, light=LT, light_step=1024)
        if axis == "x":
            areaportal(v, (x0, y0, 0, x0 + 16, y1, TH))
            areaportal(v, (x1 - 16, y0, 0, x1, y1, TH))
        else:
            areaportal(v, (x0, y0, 0, x1, y0 + 16, TH))
            areaportal(v, (x0, y1 - 16, 0, x1, y1, TH))
        tunnels.append((name, box, axis))

    # boucles entre cavernes
    for (xa, xb) in ((7936, 8576), (10880, 11520)):
        tunnel(f"t_mine_prison_{xa}", (xa, 3072, xb, 5120), "y")
        tunnel(f"t_prison_lac_{xa}", (xa, -5120, xb, -3072), "y")
    tunnel("t_mine_cmd", (12288, 5632, 12800, 6272), "x")
    tunnel("t_prison_cmd_n", (12288, 1280, 12800, 1920), "x")
    tunnel("t_prison_cmd_s", (12288, -1920, 12800, -1280), "x")
    tunnel("t_lac_cmd", (12288, -6272, 12800, -5632), "x")
    for (nm, (x0, y0, x1, y1), axis) in tunnels:            # bouches de tunnels : sol de caverne aplani
        for (r, ct) in v.cave_t:
            for (px, py) in ((x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2), ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)):
                if r[0] - 1 <= px <= r[2] + 1 and r[1] - 1 <= py <= r[3] + 1:
                    ct.flat_rect(px - 384, py - 384, px + 384, py + 384, -6, 700)
    # MINE (nord) : foreuses, tas de minerai, rails, wagons, grue
    ct = cts["mine"]
    v.info["MINE (foreuses)"] = (9700, 12600)
    for (dx, dy) in ((8448, 10752), (11264, 7680)):
        ct.flat_disc(dx, dy, 700, 8, 600)
        v.add(S.cylinder(dx, dy, 256, 0, 1100, M["dirty"], "world", 12))
        v.add(S.cylinder(dx, dy, 272, 700, 740, M["redlight"], "detail", 12), obst=False)
        v.light(dx + 360, dy, 600, "255 140 80 260")
    for (ox, oy) in ((10240, 11264), (8192, 6656), (11520, 10240)):
        v.add(frustum((ox - 448, oy - 448, -32, ox + 448, oy + 448, 224), 320, RK, top=RK))
    ct.flat_rect(7168, 7168, 12288, 7936, 2, 400)
    v.blk((7168, 7488, -16, 12288, 7520, 8), M["trim"])
    v.blk((7168, 7648, -16, 12288, 7680, 8), M["trim"])
    for k in range(5):
        v.prop(NIK + "tech/tech_mine_barrel.mdl", 7700 + k * 1000, 7584, 0, why="mine")
    v.prop(NIK + "construction/construction_crane_base.mdl", 9728, 6400, 0, why="mine")
    GH = 224                                                          # galerie haute (nord-est), brushes droits
    v.blk((11000, 11000, -64, 12288, 12288, GH), RK, top=RK, ground=True)
    for k in range(14):                                               # escalier taillé : 14 marches de 16, giron 24
        x_ = 11000 - (14 - k) * 24
        v.blk((x_, 11800, -64, x_ + 24, 11992, 16 * (k + 1)), RK, top=RK)
    for (lx, ly, mdl, a) in ((11300, 11300, NIK + "tech/tech_mining_drill_head.mdl", 30), (11800, 11500, CRATES[0], 10),
                             (11900, 11640, CRATES[1], 80), (11600, 12000, NIK + "tech/tech_mine_barrel.mdl", 0),
                             (11250, 11900, NIK + "tech/tech_mine_barrel.mdl", 0), (12000, 11150, LAMP, 0)):
        v.prop(mdl, lx, ly, a, z=GH, why="galerie_haute")
    v.light(11600, 11600, GH + 220, "255 170 110 240")
    v.light(11200, 12150, GH + 160, "255 170 110 200")
    v.light(10850, 11900, 200, "255 170 110 220")                       # escalier taillé
    v.prop(LAMP, 10960, 12030, 0, z=0, why="galerie_haute")
    v.prop(LAMP, 11060, 11760, 0, z=GH, why="galerie_haute")
    v.info["Galerie haute"] = (11600, 11600)
    v.scatter(CRATES, 9800, 11000, 900, 10, why="mine")
    # CAMP DE PRISONNIERS (centre) : tour de garde, 12 cellules à champ de force, interrogatoire
    ct = cts["prison"]
    v.info["CAMP DE PRISONNIERS"] = (9700, 3400)
    ct.flat_rect(7424, -2816, 12032, 2816, 8, 500)
    v.blk((7424, -2816, -48, 12032, 2816, 16), M["conc2"], ground=True, obst=False)
    mushroom_tower(v, 9728, 0, 256, 16, 768, cap=2.2)
    v.info["Tour de garde"] = (9728, -700)
    ncell = 0
    for (yy, face) in ((2304, -1), (-2304, 1)):
        for k in range(6):
            cx0 = 7680 + k * 704
            ya, yb = (yy, yy + 448) if face < 0 else (yy - 448, yy)
            for b in ((cx0, ya, cx0 + 32, yb), (cx0 + 480, ya, cx0 + 512, yb)):
                v.blk((b[0], b[1], 16, b[2], b[3], 304), M["wall2"])
            back = (cx0, yb - 32, cx0 + 512, yb) if face < 0 else (cx0, ya, cx0 + 512, ya + 32)
            v.blk((back[0], back[1], 16, back[2], back[3], 304), M["wall2"])
            v.blk((cx0, ya, 304, cx0 + 512, yb, 336), M["trim"])
            fy = ya if face < 0 else yb - 16
            v.w.ent("func_illusionary", solids=[Block((cx0 + 32, fy, 16, cx0 + 480, fy + 16, 304), "effects/combineshield/comshieldwall",
                                                      "detail")], rendermode=0)
            v.light(cx0 + 256, (ya + yb) / 2, 260, "150 170 230 70")
            crect = (cx0 + 32, ya + 16, cx0 + 480, yb - 32) if face < 0 else (cx0 + 32, ya + 32, cx0 + 480, yb - 16)
            ff = (crect[0], crect[1], crect[2], crect[1] + 56) if face < 0 else (crect[0], crect[3] - 56, crect[2], crect[3])
            rmc = IN.Room("cellule", crect if face < 0 else (-crect[2], -crect[3], -crect[0], -crect[1]), 16,
                          [ff if face < 0 else (-ff[2], -ff[3], -ff[0], -ff[1])], key=("cellule", cx0, yy), ceil=280)
            IN.compose(rmc)
            IN.emit(v, rmc, (lambda lx, ly: (lx, ly)) if face < 0 else (lambda lx, ly: (-lx, -ly)), 0 if face < 0 else 180,
                    light=None)
            ncell += 1
    v.info["Cellules (12, champs de force)"] = (9500, 1900)
    round_hall(v, 11648, 1536, 384, 16, 320, doors=(180,), roof="cone", wall=M["walld"], closed=True, light="255 70 50 200")
    dome_interior(v, 11648, 1536, 384, 16, 320, (180,), "interrogatoire", "observation", M["walld"])
    v.info["Interrogatoire"] = (11648, 2200)
    pillbox(v, 11264, -1024, 16, 180, r=240)
    # LAC SOUTERRAIN (sud) : eau, deux ponts de roche, îlot avec bunker
    ct = cts["lac"]
    v.info["LAC SOUTERRAIN"] = (9700, -12600)
    lcx, lcy = 9728, -8704

    def lake(x, y, h):
        d = math.hypot((x - lcx) / 1900, (y - lcy) / 2400)
        return h - 320 * (1 - smoothstep(0.55, 1.0, d))
    ct.features.append(lake)
    ct.flat_disc(lcx, lcy, 480, 40, 300)
    v.water.append((7168, -12288, CZ0, 12288, -5120, -40))
    for (y0b, y1b) in ((-11264, -9216), (-8192, -6144)):
        v.blk((lcx - 128, y0b, -16, lcx + 128, y1b, 24), RK, top=RK, ground=True)
    pillbox(v, lcx, lcy, 40, 0, r=280)
    v.info["Îlot (bunker)"] = (lcx + 600, lcy)
    # CENTRE DE COMMANDEMENT DROÏDE (est) : rempart à 3 portes, dôme fermé, réacteur
    ct = cts["commandement"]
    v.info["CENTRE DE COMMANDEMENT DROÏDE"] = (14300, 7500)
    ct.flat_rect(13056, -6912, 15616, 6912, 8, 500)
    v.blk((13056, -6912, -48, 15616, 6912, 16), M["floor2"], ground=True, obst=False)
    zf = lambda x, y: 16
    for (a, b) in ((-6912, -4096), (-3328, -768), (768, 3328), (4096, 6912)):
        wall_line(v, [(13440, a), (13440, b)], zf, h=416, thick=160)
    round_hall(v, 14592, 0, 1024, 16, 576, doors=(180, 90, 270), roof="dome", wall=M["sepwall"], roof_mat=M["hull3"],
               closed=True, light="255 110 80 260", segs=20)
    dome_interior(v, 14592, 0, 1024, 16, 576, (180, 90, 270), "commandement", "serveurs", M["sepwall"])
    v.info["Dôme de commandement"] = (14592, -1400)
    v.add(S.cylinder(15104, 5120, 288, 16, 2048, M["pkb"], "world", 16))
    v.add(S.cylinder(15104, 5120, 304, 900, 940, M["redlight"], "detail", 16), obst=False)
    v.info["Réacteur"] = (14600, 5800)
    for (dx, dy) in ((15360, -2048), (15360, 2048), (15232, -3840), (14208, 3584), (14208, -3584), (15488, 0), (15232, -6144)):
        v.droid_spawns.append((dx, dy, 24))
    # parois naturelles + stalactites (rien devant les bouches de tunnels ni dans les puits)
    avoid = [(bx0 - 400, by0 - 400, -64, bx1 + 400, by1 + 400, TH) for (_, (bx0, by0, bx1, by1), _) in tunnels]
    avoid += [(hx - 300, hy - 300, -64, hx + 1324, hy + 1324, 4000) for (hx, hy) in SHAFTS.values()]
    for n, (x0, y0, x1, y1, h) in CAVES.items():
        cave_rocks(v, (x0, y0, 0, x1, y1, h), 0.4 if n in ("prison", "commandement") else 0.5, avoid=avoid, big=True)
        for k in range(14):                              # blocs éboulés (props : zéro plane)
            v.prop(R.choice(ROCKS[2:] + [NIK + "caves/caves_rubble_mound_02b.mdl"]), R.uniform(x0 + 300, x1 - 300),
                   R.uniform(y0 + 300, y1 - 300), R.uniform(0, 360), sink=30, why="caverne")
    for (n, (x0, y0, x1, y1), a) in tunnels:
        av = ([(x0 - 1, y0 - 1, -64, x0 + 200, y1 + 1, TH), (x1 - 200, y0 - 1, -64, x1 + 1, y1 + 1, TH)] if a == "x"
              else [(x0 - 1, y0 - 1, -64, x1 + 1, y0 + 200, TH), (x0 - 1, y1 - 200, -64, x1 + 1, y1 + 1, TH)])
        cave_rocks(v, (x0, y0, 0, x1, y1, TH), 0.25, avoid=av)
    for _ in range(16):                                  # filons de minerai lumineux (lumière précalculée)
        x0, y0, x1, y1, h = CAVES[R.choice(list(CAVES))]
        side = R.randrange(4)
        x, y = [(x0 + 120, R.uniform(y0, y1)), (x1 - 120, R.uniform(y0, y1)), (R.uniform(x0, x1), y0 + 120),
                (R.uniform(x0, x1), y1 - 120)][side]
        v.light(x, y, R.uniform(160, 600), "90 220 200 140")
    STATS["cellules"] = ncell
    for (hx, hy) in SHAFTS.values():
        route(v, "principal", (hx + 512, hy + 512), (hx + 512, hy + 1600))
    route(v, "principal", (9728, 9000), (8256, 4096), (9728, 0), (8256, -4096), (9728, -8704))
    route(v, "principal", (9728, 0), (13440, 0), (14592, 0))
    route(v, "secondaire", (11200, 9000), (11200, 4096), (11200, -4096), (11200, -9000))
    route(v, "secondaire", (11200, 9000), (12544, 5952), (13440, 5952))
    route(v, "secondaire", (11200, -9000), (12544, -5952), (13440, -5952))
