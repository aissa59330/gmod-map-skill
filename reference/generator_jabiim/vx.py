"""Copie des outils de rp_cw_arsenal_vexis (palette M, classe V, bâtiments ronds, voûtes, bunkers, remparts...).
Seules les briques sont utilisées par jabiim.py ; les zones propres à Vexis (zone_*) ne sont pas appelées.
"""
"""Plan de rp_cw_arsenal_vexis : planète-arsenal séparatiste, un seul grand champ de bataille.

Repère : x vers l'est, y vers le nord. Zone de jeu ±15872, sol (fond) à FLOOR, ciel à CEIL.
La République part de l'épave du Venator (sud-ouest) ; les séparatistes tiennent tout le reste.
"""
import json
import math
import os
import random

from srctools import Vec

from geom import World, Block, Poly, MAT_SKY, MAT_NODRAW, norm, overlap
from terrain import Terrain, fbm, smoothstep, poly_dist, seg_dist
import shapes as S

HERE = os.path.dirname(os.path.abspath(__file__))
BOUNDS = json.load(open(os.path.join(HERE, "prop_bounds_vexis.json"), encoding="utf-8"))
R = random.Random(4242)

XA, XB = -15872, 15872
FLOOR, CEIL = -1024, 10240

# ---------------- palette ----------------
M = {
    "wall": "rp_undercity/rp_undercity_metal_wall_13",
    "wall2": "rp_undercity/rp_undercity_metal_wall_17",
    "wall3": "rp_undercity/rp_undercity_metal_wall_38",
    "walld": "rp_undercity/rp_undercity_metal_wall_22",
    "dirty": "rp_anaxes/rp_anaxes_metal_dirty2",
    "pk": "pk02/pk02_wall_big01a",
    "pkb": "pk02/pk02_wall_big01b",
    "panel": "pk02/pk02_panels01c",
    "trim": "pk02/pk02_trim_set01a",
    "hazard": "old_glory/star_wars_materials/wall7",
    "sepwall": "old_glory/star_wars_materials/wall4",
    "redlight": "pk02/pk02_light02c",
    "whitelight": "pk02/pk02_light02a",
    "floor": "rp_undercity/rp_undercity_metal_floor_14",
    "grate": "rp_undercity/rp_undercity_metal_floor_12",
    "floor2": "rp_anaxes/rp_anaxes_metal_floor_7",
    "conc": "rp_anaxes/rp_anaxes_concrete_floor11",
    "conc2": "rp_anaxes/rp_anaxes_concrete_14",
    "hull": "lordtrilobite/isd_metal01_dirty",
    "hull2": "lordtrilobite/isd_exteriorgreebles_dirty",
    "hull3": "lordtrilobite/isd_exteriorpanels_dirty",
    "deck": "lordtrilobite/isd_floor01_dirty",
    "rock": "nature/cliffface002a",
    "rockred": "rp_geonosis/rp_geonosis_rock2_red_mumble",
    "glass": "lordtrilobite/glass_dirty",
    "lava": "renegade_mumble_facility/lava_solid",
    "door": "starwars/doomgiver/doormaint",
    "blast": "starwars/kejim/blastdoor_onoff",
}

MDL = "models/"
NIK = MDL + "niksacokica/"


class V:
    def __init__(self):
        self.w = World()
        self.t = Terrain(XA, XA, XB, XB, FLOOR)
        self.props = []        # (model, (x,y,z), yaw, solid, extra)
        self.dyn = []          # prop_dynamic (vaisseaux du ciel 3D)
        self.slabs = []        # ("disc", cx, cy, r, ztop) | ("rect", x0, y0, x1, y1, ztop)
        self.obst = {}
        self.labels = []       # (x, y, texte)
        self.zones = []        # (x0, y0, x1, y1, nom) pour le plan
        self.spawns = []
        self.droid_spawns = []
        self.nodes_extra = []
        self.fx = []           # entités d'ambiance (dicts pour World.ent)
        self.clear = []        # disques (cx, cy, r) à garder libres de décor
        self.rej = {}
        self.pending = []
        self.tilt = {}         # (modèle, x, y arrondis) -> (tangage, roulis) : véhicules renversés, épaves enfoncées
        self.ngroup = 0

    # ---------- obstacles ----------
    def _cells(self, b):
        for ix in range(int(b[0] // 512), int(b[3] // 512) + 1):
            for iy in range(int(b[1] // 512), int(b[4] // 512) + 1):
                yield ix, iy

    def add_obst(self, b, planes=None):
        """Obstacle : boîte englobante + (pour un brush tourné) ses plans, pour un test de forme exact."""
        for k in self._cells(b):
            self.obst.setdefault(k, []).append((b, planes))

    def hits(self, b, corners=None):
        """Collision d'une boîte de prop avec les obstacles. Pour un brush tourné, la boîte englobante (alignée sur les
        axes) recouvre l'intérieur d'une pièce : on teste alors les plans du brush (un plan qui laisse les 8 coins de la
        boîte du prop dehors = séparation, donc pas de collision)."""
        for k in self._cells(b):
            for (o, planes) in self.obst.get(k, ()):
                if not overlap(b, o):
                    continue
                if not planes:
                    return True
                if corners is None:
                    corners = [(x, y, z) for x in (b[0], b[3]) for y in (b[1], b[4]) for z in (b[2], b[5])]
                separated = False
                for (pt, n) in planes:
                    d = n.x * pt.x + n.y * pt.y + n.z * pt.z
                    if all(n.x * x + n.y * y + n.z * z - d > 0 for (x, y, z) in corners):
                        separated = True
                        break
                if not separated:
                    return True
        return False

    def add(self, items, obst=True):
        if not isinstance(items, (list, tuple)):
            items = [items]
        for it in items:
            self.w.add(it)
            if obst:
                if isinstance(it, Block):
                    self.add_obst(it.box)
                else:                                   # brush quelconque (souvent tourné) : on garde ses plans
                    self.add_obst(it.bbox, getattr(it, "planes", None))
        return items

    def door(self, door_planes, portal_planes):
        """Porte coulissante (descend dans le sol, s'ouvre au contact ou avec [E], se referme seule)
        + areaportal dans son épaisseur : intérieur non dessiné quand la porte est fermée."""
        self.ndoor = getattr(self, "ndoor", 0) + 1
        nm = f"porte_{self.ndoor}"
        self.w.ent("func_door", None, solids=[S.mk(door_planes, M["door"], "door")], targetname=nm, movedir="90 0 0",
                   speed=220, lip=2, wait=5, spawnflags=256 + 1024, forceclosed=0, dmg=0,
                   noise1="doors/heavy_metal_move1.wav", noise2="doors/heavy_metal_stop1.wav", rendercolor="255 255 255")
        self.w.ent("func_areaportal", None, solids=[S.mk(portal_planes, "tools/toolsareaportal", "portal")], target=nm,
                   StartOpen=0, PortalVersion=1)

    def window_portal(self, planes):
        """Areaportal toujours ouvert dans une fenêtre : on ne dessine que ce qui se voit à travers."""
        self.w.ent("func_areaportal", None, solids=[S.mk(planes, "tools/toolsareaportal", "portal")], StartOpen=1, PortalVersion=1)

    def occluder(self, cx, cy, r, z0, z1):
        """Bloc invisible (world) inscrit dans une forme ronde pleine : bloque la visibilité sans coût de rendu."""
        h = int(r * 0.68) // 16 * 16
        if h >= 128 and z1 - z0 >= 256:
            self.w.block((round(cx) // 16 * 16 - h, round(cy) // 16 * 16 - h, int(z0) // 16 * 16 + 16,
                          round(cx) // 16 * 16 + h, round(cy) // 16 * 16 + h, int(z1) // 16 * 16 - 16), MAT_NODRAW, "world")

    def blk(self, box, mat, kind="detail", top=None, obst=True):
        b = self.w.block(norm(box), mat, kind, top)
        if obst:
            self.add_obst(b.box)
        return b

    # ---------- sol ----------
    def slab_disc(self, cx, cy, r, ztop, mat, thick=32, kind="detail", sides=24, flat=True, fall=640):
        self.add(S.disc(cx, cy, r, ztop - thick, ztop, mat, kind, sides), obst=False)
        self.slabs.append(("disc", cx, cy, r - 8, ztop))
        if flat:
            self.t.flat_disc(cx, cy, r, ztop - 12, fall)

    def slab_rect(self, x0, y0, x1, y1, ztop, mat, thick=32, kind="detail", flat=True, fall=640):
        self.blk((x0, y0, ztop - thick, x1, y1, ztop), mat, kind, obst=False)
        self.slabs.append(("rect", x0, y0, x1, y1, ztop))
        if flat:
            self.t.flat_rect(x0, y0, x1, y1, ztop - 12, fall)

    def gz(self, x, y):
        z = self.t.h(x, y)
        for s in self.slabs:
            if s[0] == "disc":
                if (x - s[1]) ** 2 + (y - s[2]) ** 2 <= s[3] ** 2:
                    z = max(z, s[4])
            elif s[1] <= x <= s[3] and s[2] <= y <= s[4]:
                z = max(z, s[5])
        return z

    def in_clear(self, x, y, r=0):
        return any((x - cx) ** 2 + (y - cy) ** 2 < (cr + r) ** 2 for cx, cy, cr in self.clear)

    # ---------- props ----------
    def prop(self, model, x, y, yaw=0.0, z=None, solid=6, check=True, sink=4, why="divers", group=None, tilt=None):
        """Demande de prop : résolue à la fin (resolve), quand tout le relief est connu. tilt=(tangage, roulis) optionnel."""
        if tilt:
            self.tilt[(model.lower(), round(x), round(y))] = tilt
        self.pending.append((model.lower(), x, y, yaw, z, solid, check, sink, why, group))
        return True

    def scatter(self, models, cx, cy, r, n, why="scatter", avoid_clear=True, yaw=None, tries=4):
        self.ngroup += 1
        g = (self.ngroup, n)
        for _ in range(n * tries):
            a = R.random() * 2 * math.pi; d = r * math.sqrt(R.random())
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if avoid_clear and (self.in_clear(x, y, 64) or self.t.on_track(x, y, 96)):
                continue
            self.prop(R.choice(models), x, y, R.uniform(0, 360) if yaw is None else yaw, why=why, group=g)
        return n

    def resolve(self):
        used = {}
        for (model, x, y, yaw, z, solid, check, sink, why, g) in self.pending:
            if g is not None and used.get(g[0], 0) >= g[1]:
                continue
            b = BOUNDS.get(model)
            if b is None or b.get("static") is False:
                k = ("absent:" if b is None else "dynamique:") + model
                self.rej[k] = self.rej.get(k, 0) + 1
                continue
            bx = rot_box(model, x, y, 0, yaw)
            if z is None:
                pts = [(x, y), (bx[0], bx[1]), (bx[3], bx[1]), (bx[0], bx[4]), (bx[3], bx[4])]
                z = min(self.gz(px, py) for px, py in pts) - sink
            box = (bx[0] + 2, bx[1] + 2, z + b["min"][2] + 6, bx[3] - 2, bx[4] - 2, z + b["max"][2])
            cs, pl = rot_box(model, x, y, z, yaw, corners_only=True)
            if check:
                if abs(x) > XB - 300 or abs(y) > XB - 300 or self.hits(box, cs):
                    self.rej[why] = self.rej.get(why, 0) + 1
                    continue
            if solid:
                self.add_obst(box, pl)
            self.props.append((model, (round(x, 1), round(y, 1), round(z, 1)), yaw % 360, solid))
            if g is not None:
                used[g[0]] = used.get(g[0], 0) + 1
        self.pending = []

    def light(self, x, y, z, color="255 220 180 300", dist=0):
        e = self.w.ent("light", (x, y, z), _light=color, _quadratic_attn=1, _linear_attn=0, _constant_attn=0)
        if dist:
            e["kv"]["_distance"] = dist
        return e

    def label(self, x, y, txt):
        self.labels.append((x, y, txt))


P3 = __import__("collections").namedtuple("P3", "x y z")


def rot_box(model, x, y, z, yaw, corners_only=False):
    b = BOUNDS[model]
    (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    xs, ys = [], []
    if corners_only:                                   # boîte ORIENTÉE (8 coins, rétrécie de 2) et ses 6 plans extérieurs
        za, zb = z + z0 + 6, z + z1
        x0, y0, x1, y1 = x0 + 2, y0 + 2, x1 - 2, y1 - 2
        W = lambda px, py: (x + px * c - py * s, y + px * s + py * c)
        cs = [(*W(px, py), pz) for px in (x0, x1) for py in (y0, y1) for pz in (za, zb)]
        u, w_ = P3(c, s, 0), P3(-s, c, 0)
        pl = [(P3(*W(x1, 0), 0), u), (P3(*W(x0, 0), 0), P3(-c, -s, 0)), (P3(*W(0, y1), 0), w_), (P3(*W(0, y0), 0), P3(s, -c, 0)),
              (P3(x, y, zb), P3(0, 0, 1)), (P3(x, y, za), P3(0, 0, -1))]
        return cs, pl
    for px in (x0, x1):
        for py in (y0, y1):
            xs.append(px * c - py * s); ys.append(px * s + py * c)
    return (x + min(xs), y + min(ys), z + z0, x + max(xs), y + max(ys), z + z1)


# =====================================================================
#   RELIEF DESSINÉ
# =====================================================================
WRECK_S = (-11800.0, -11800.0)      # poupe du Venator
WRECK_YAW = 45.0
WRECK_L = 7200
WRECK_N = (WRECK_S[0] + WRECK_L * math.cos(math.radians(WRECK_YAW)), WRECK_S[1] + WRECK_L * math.sin(math.radians(WRECK_YAW)))
WRECK_Z = 64

CIT = (6600.0, 9900.0)              # citadelle sur plateau
CIT_R = 2500
CIT_Z = 1152

CANYON = [(2600, -13400), (5200, -11000), (8200, -9600), (11000, -8200), (13800, -7000)]

CITY = (-3200.0, 2600.0)
CITY_Z = 192
AGRI = (-9200.0, 8600.0)
AGRI_Z = 160
FACT = (1600.0, -5600.0)
FACT_Z = 96
PORT = (8600.0, 1200.0)
PORT_Z = 256


def relief(t: Terrain):
    sx, sy = WRECK_S
    nx, ny = WRECK_N
    ux, uy = math.cos(math.radians(WRECK_YAW)), math.sin(math.radians(WRECK_YAW))
    fx, fy = sx - 5200 * ux, sy - 5200 * uy      # début du sillon (dans la montagne)

    def wreck(x, y, h):
        # sillon creusé par le crash + aire plate autour de l'épave
        d, qx, qy = seg_dist(x, y, fx, fy, nx + 600 * ux, ny + 600 * uy)
        if d < 2400:
            along = ((qx - fx) * ux + (qy - fy) * uy) / (5200 + WRECK_L + 600)
            target = WRECK_Z - 40 + 200 * (1 - along) - 120 * math.exp(-((d / 520) ** 2))   # fond du sillon
            w = 1 - smoothstep(1100, 2400, d)
            h = h + (target - h) * w
            # bourrelets de terre rejetée de chaque côté
            h += 220 * math.exp(-(((d - 1500) / 380) ** 2)) * (0.4 + 0.6 * along)
        return h

    def plateau(x, y, h):
        cx, cy = CIT
        d = math.hypot(x - cx, y - cy)
        th = math.atan2(y - cy, x - cx)
        # pentes douces au sud (spatioport) et à l'ouest (cité) : rampes ; falaises ailleurs
        g = max(0.0, math.cos(th - math.radians(-100))) ** 6 + max(0.0, math.cos(th - math.radians(185))) ** 6
        fall = 520 + 2100 * min(1.0, g)
        r = CIT_R + 220 * fbm(math.cos(th) * 3, math.sin(th) * 3, 2, 77)
        if d < r + fall:
            w = 1 - smoothstep(r, r + fall, d)
            top = CIT_Z + 30 * fbm(x / 800, y / 800, 2, 5)
            h = max(h, h + (top - h) * w)
        return h

    def canyon(x, y, h):
        d, qx, qy = poly_dist(x, y, CANYON)
        if d < 2000:
            floor = -620 + 60 * fbm(qx / 1500, qy / 1500, 2, 91)
            w = 1 - smoothstep(560 + 180 * fbm(x / 900, y / 900, 2, 3), 1150, d)
            h = h + (floor - h) * w
            # rebords rocheux légèrement surélevés
            h += 260 * math.exp(-(((d - 1450) / 300) ** 2))
        return h

    def ridges(x, y, h):
        # crêtes qui séparent les couloirs d'attaque (avec des cols)
        for pts, hgt, wid in (
            ([(-9000, -3000), (-7000, -1400), (-5600, 600)], 520, 900),          # entre vallée et nord-ouest
            ([(-600, -1800), (2200, -2300), (4600, -1600)], 380, 700),             # entre cité et usines
            ([(-12500, 2600), (-10200, 3600)], 650, 900),                          # contrefort ouest
            ([(12400, -4200), (10800, -4800)], 600, 800),                          # contrefort est
        ):
            d, qx, qy = poly_dist(x, y, pts)
            if d < wid * 1.6:
                k = math.exp(-((d / wid) ** 2)) * (0.75 + 0.25 * fbm(qx / 700, qy / 700, 2, 13))
                # cols : baisse périodique le long de la crête
                k *= 0.45 + 0.55 * abs(math.sin(qx / 1300 + qy / 1700))
                h += hgt * k
        return h

    def mesas(x, y, h):
        # pitons rocheux isolés (couverts / repères)
        for cx, cy, r, hh in ((-6200, -7600, 520, 520), (-4400, -9800, 420, 380), (-9800, -4200, 600, 640),
                              (-2600, -7400, 360, 300), (3400, 6200, 520, 560), (-600, 9800, 700, 700),
                              (12000, 5600, 600, 650), (-13000, 6400, 700, 600)):
            d = math.hypot(x - cx, y - cy)
            if d < r + 500:
                k = 1 - smoothstep(r * 0.55, r + 500, d)
                h += hh * k * (0.85 + 0.15 * fbm(x / 300, y / 300, 2, 7))
        return h

    t.features += [wreck, canyon, ridges, mesas, plateau]

    # matériaux par région (dalle de 1024)
    def in_canyon(x, y):
        return poly_dist(x, y, CANYON)[0] < 1700
    def agri(x, y):
        return math.hypot(x - AGRI[0], y - AGRI[1]) < 4300 or (x < -4000 and y > 3000 and abs(x) < 12000 and y < 12000)
    def valley(x, y):
        return -11000 < x < -2500 and -11000 < y < -2500 and fbm(x / 3000, y / 3000, 2, 99) > -0.1
    def border(x, y):
        d = min(x - XA, XB - x, y - XA, XB - y)
        return d < 1800
    t.regions = [
        (border, "nature/blendcliffdirt001a"),
        (in_canyon, "rp_geonosis/rp_geonosis_rocksoil_1_redrock_blend"),
        (agri, "nature/blenddirtgrass008a"),
        (valley, "nature/blendrocksgrass006a"),
    ]
    t.default_mat = "nature/blendrockdirt006a"


def tracks(t: Terrain):
    t.track([(WRECK_N[0] + 300, WRECK_N[1] + 300), (-5200, -4700), (-3600, -1700), (CITY[0], CITY[1] - 2200)], 300)
    t.track([(CITY[0] + 900, CITY[1] + 2400), (-200, 6400), (2600, 8200), (CIT[0] - CIT_R - 900, CIT[1] - 600), (CIT[0] - 900, CIT[1] - 300)], 300)
    t.track([(-5200, -4700), (-2400, -5600), (FACT[0] - 2600, FACT[1])], 320)
    t.track([(FACT[0] + 3400, FACT[1] + 400), (5600, -3600), (PORT[0] - 1800, PORT[1] - 2600)], 320)
    t.track([(CITY[0] + 3000, CITY[1]), (1600, 2200), (PORT[0] - 3600, PORT[1] + 200)], 320)
    t.track([(PORT[0] - 400, PORT[1] + 3400), (7400, 5600), (CIT[0] + 300, CIT[1] - CIT_R - 300), (CIT[0] + 200, CIT[1] - 700)], 300)
    t.track([(AGRI[0] + 2200, AGRI[1] - 2400), (-6200, 5400), (CITY[0] - 2600, CITY[1] + 1200)], 280)
    t.track([(-11200, -7400), (-11900, -2600), (-11000, 1600), (AGRI[0] - 1200, AGRI[1] - 3000)], 280)
    t.track([(FACT[0] + 2600, FACT[1] - 2200), (5600, -9200), (7600, -9700)], 300)


# =====================================================================
#   BRIQUES ARCHITECTURALES
# =====================================================================
def round_hall(v, cx, cy, r, z, h, doors=(0, 180), roof="dome", wall=None, roof_mat=None, kind="world",
               windows=True, light="255 120 90 220", segs=16, floor_mat=None, droid=False, closed=False):
    """Bâtiment rond : sol, mur circulaire (portes + fenêtres), toit (dôme / cône / plat / champignon).
    closed=True : sol, murs et plafond en world étanche, vraies portes + areaportals (intérieur non dessiné porte fermée)."""
    wall = wall or M["pk"]
    roof_mat = roof_mat or M["hull3"]
    step = 360.0 / segs
    WK = "world!" if closed else kind
    gaps = set()
    for a in doors:
        gaps.add(int(((a % 360) + step / 2) // step) % segs)
    if closed:
        v.add(S.disc(cx, cy, r + 16, z - 32, z, floor_mat or M["floor"], "world!", segs), obst=False)
        v.slabs.append(("disc", cx, cy, r + 8, z))
        v.t.flat_disc(cx, cy, r + 16, z - 12, 640)
    else:
        v.slab_disc(cx, cy, r + 16, z, floor_mat or M["floor"], sides=segs)

    def sec(r0, r1, a0, a1, zz0, zz1):
        return S.xform(S.ring_seg_planes(r0, r1, a0, a1, zz0, zz1), (cx, cy, 0))

    out = []
    for k in range(segs):
        a0, a1 = k * step, (k + 1) * step

        def seg(zz0, zz1):
            return S.mk(sec(r - 32, r, a0, a1, zz0, zz1), wall, WK)

        if k in gaps:
            out.append(seg(z + 208, z + h))
            if closed:
                v.door(sec(r - 30, r - 2, a0, a1, z, z + 206), sec(r - 20, r - 12, a0, a1, z, z + 208))
        elif windows and k % 2 == 1 and h >= 300 and (k - 1) % segs not in gaps and (k + 1) % segs not in gaps:
            out.append(seg(z, z + 64))
            out.append(seg(z + 160, z + h))
            if closed:
                v.window_portal(sec(r - 20, r - 12, a0, a1, z + 64, z + 160))
        else:
            out.append(seg(z, z + h))
    v.add(out)
    zt = z + h
    v.add(S.disc(cx, cy, r + 24, zt, zt + 32, M["trim"], "world!" if closed else kind, segs))
    if roof == "dome":
        v.add(S.dome(cx, cy, r, zt + 32, roof_mat, "detail", 4, segs, squash=0.55))
    elif roof == "cone":
        v.add(S.cone(cx, cy, r, max(48, r * 0.15), zt + 32, zt + 32 + int(r * 0.7), roof_mat, "detail", segs))
    elif roof == "mushroom":
        v.add(S.cone(cx, cy, r, r * 1.45, zt + 32, zt + 32 + int(r * 0.35), roof_mat, "detail", segs))
        v.add(S.disc(cx, cy, r * 1.45, zt + 32 + int(r * 0.35), zt + 64 + int(r * 0.35), M["trim"], "detail", segs))
    if light:
        v.light(cx, cy, z + min(h - 48, 260), light)
    v.nodes_extra.append((cx + r * 0.4, cy, z + 16))
    v.nodes_extra.append((cx - r * 0.4, cy, z + 16))
    if droid:
        # repère devant la première porte (le réseau de nœuds est calculé portes fermées : les PNJ restent dehors)
        a = math.radians(doors[0])
        v.droid_spawns.append((cx + (r + 260) * math.cos(a), cy + (r + 260) * math.sin(a), z + 24))
    v.clear.append((cx, cy, r + 64))
    for a in doors:
        v.clear.append((cx + (r + 160) * math.cos(math.radians(a)), cy + (r + 160) * math.sin(math.radians(a)), 160))
    return out


def mushroom_tower(v, cx, cy, r, z, h, cap=2.6, mat=None, cap_mat=None, lights=True):
    """Tour champignon néimoïdienne (pleine) : fût + chapeau évasé + toit-terrasse."""
    mat = mat or M["pkb"]
    cap_mat = cap_mat or M["hull3"]
    v.add(S.cone(cx, cy, r * 1.25, r, z - 32, z + 240, mat, "world", 16))
    v.add(S.cylinder(cx, cy, r, z + 240, z + h, mat, "world", 16))
    v.occluder(cx, cy, r, z + 240, z + h)
    v.add(S.cone(cx, cy, r, r * cap, z + h, z + h + r * 0.9, cap_mat, "world", 16))
    zt = z + h + int(r * 0.9)
    v.add(S.disc(cx, cy, r * cap, zt, zt + 48, M["trim"], "detail", 16))
    v.add(S.dome(cx, cy, r * 0.9, zt + 48, M["hull"], "detail", 3, 16, 0.6))
    # bandeau lumineux rouge
    v.add(S.cylinder(cx, cy, r + 8, z + h - 96, z + h - 64, M["redlight"], "detail", 16), obst=False)
    v.clear.append((cx, cy, r * 1.3 + 32))
    if lights:
        v.light(cx + r + 40, cy, z + h - 120, "255 60 40 160")


def cooling_tower(v, cx, cy, r, z, h, mat=None):
    """Tour de refroidissement (hyperboloïde) en troncs de cône."""
    mat = mat or M["dirty"]
    prof = [(0.0, 1.0), (0.25, 0.82), (0.55, 0.66), (0.78, 0.68), (1.0, 0.78)]
    for (t0, k0), (t1, k1) in zip(prof, prof[1:]):
        v.add(S.cone(cx, cy, r * k0, r * k1, int(z + h * t0), int(z + h * t1), mat, "world", 16))
        v.occluder(cx, cy, r * min(k0, k1), z + h * t0, z + h * t1)
    v.fx.append(("smoke", (cx, cy, z + h + 32), {"rate": 7, "size": 520, "color": "90 85 80"}))
    v.clear.append((cx, cy, r + 48))


def chimney(v, cx, cy, r, z, h, smoke=True):
    v.add(S.cylinder(cx, cy, r * 1.6, z - 32, z + 160, M["dirty"], "world", 12))
    v.add(S.cone(cx, cy, r, r * 0.8, z + 160, z + h, M["dirty"], "world", 12))
    v.add(S.cylinder(cx, cy, r * 0.85, z + h - 160, z + h - 112, M["redlight"], "detail", 12), obst=False)
    if smoke:
        v.fx.append(("smoke", (cx, cy, z + h + 16), {"rate": 8, "size": 360, "color": "60 58 56"}))
    v.clear.append((cx, cy, r * 1.6 + 32))


def silo(v, cx, cy, r, z, h, mat=None):
    mat = mat or M["hull"]
    v.add(S.cylinder(cx, cy, r, z - 16, z + h, mat, "world", 16))
    v.occluder(cx, cy, r, z, z + h)
    v.add(S.cone(cx, cy, r + 16, 48, z + h, z + h + int(r * 0.6), M["trim"], "detail", 16))
    v.add(S.cylinder(cx, cy, r + 12, z + h * 0.3, z + h * 0.3 + 32, M["trim"], "detail", 16))
    v.clear.append((cx, cy, r + 48))


def vault_hall(v, cx, cy, z, length, span, wall_h, rise, yaw, mat=None, roof_mat=None, gate_w=None, gate_h=None,
               lights=True, droid=False, floor_mat=None, side_doors=True, closed=False):
    """Hangar / usine voûté(e), portails aux deux bouts, portes latérales. Axe long = yaw."""
    mat = mat or M["wall3"]
    roof_mat = roof_mat or M["hull3"]
    gate_w = gate_w or span * 0.55
    gate_h = gate_h or min(wall_h, 448)
    hw, gw = span / 2, gate_w / 2
    th = 32
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def W(lx, ly):
        return cx + lx * c - ly * s, cy + lx * s + ly * c

    WK = "world!" if closed else "world"
    # dalle de sol (rect orienté : on aplanit un disque englobant, et la dalle est une boîte orientée)
    v.add(S.obox(cx, cy, z - 32, length + 64, span + 64, 32, yaw, floor_mat or M["floor2"], WK if closed else "detail"), obst=False)
    v.t.flat_disc(cx, cy, max(length, span) / 2 + 64, z - 12, 700)
    if abs(c) > 0.99 or abs(s) > 0.99:
        lx, ly = (length / 2 + 32, span / 2 + 32) if abs(c) > 0.99 else (span / 2 + 32, length / 2 + 32)
        v.slabs.append(("rect", cx - lx, cy - ly, cx + lx, cy + ly, z))
    else:
        v.slabs.append(("disc", cx, cy, min(length, span) / 2, z))
    # murs latéraux avec portes
    for side in (-1, 1):
        y0 = side * hw - (th if side > 0 else 0)
        y1 = side * hw + (0 if side > 0 else th)
        doors = [-length / 4, length / 4] if side_doors else []
        xs = [-length / 2]
        for dx in doors:
            xs += [dx - 112, dx + 112]
        xs.append(length / 2)
        for i in range(0, len(xs), 2):
            v.add(S.mk(S.xform(S.box_planes(xs[i], y0, 0, xs[i + 1], y1, wall_h), (cx, cy, z), yaw), mat, WK))
        for dx in doors:
            v.add(S.mk(S.xform(S.box_planes(dx - 112, y0, 208, dx + 112, y1, wall_h), (cx, cy, z), yaw), mat, WK))
            v.clear.append((*W(dx, side * (hw + 200)), 180))
            if closed:
                v.door(S.xform(S.box_planes(dx - 112, y0 + 2, 0, dx + 112, y1 - 2, 206), (cx, cy, z), yaw),
                       S.xform(S.box_planes(dx - 112, y0 + 12, 0, dx + 112, y1 - 12, 208), (cx, cy, z), yaw))
            v.nodes_extra.append((*W(dx, side * (hw - 160)), z + 16))
    # voûte
    v.add(S.vault(cx, cy, z, length, span, wall_h, rise, yaw, mat, roof_mat, WK, 8, 32)[2:])
    # pignons : piliers, linteau, remplissage de l'arc
    Rr = (hw * hw + rise * rise) / (2 * rise)
    zc = wall_h + rise - Rr
    a_end = math.asin(hw / Rr)
    for end in (-1, 1):
        x0 = end * length / 2 - (th if end > 0 else 0)
        x1 = x0 + th
        for side in (-1, 1):
            ya, yb = sorted((side * hw, side * gw))
            v.add(S.mk(S.xform(S.box_planes(x0, ya, 0, x1, yb, wall_h), (cx, cy, z), yaw), mat, WK))
        if gate_h < wall_h:
            v.add(S.mk(S.xform(S.box_planes(x0, -gw, gate_h, x1, gw, wall_h), (cx, cy, z), yaw), mat, WK))
        for k in range(8):
            t0 = -a_end + 2 * a_end * k / 8; t1 = -a_end + 2 * a_end * (k + 1) / 8
            ya, za = Rr * math.sin(t0), zc + Rr * math.cos(t0)
            yb, zb = Rr * math.sin(t1), zc + Rr * math.cos(t1)
            pts = [(x0, ya, wall_h), (x0, yb, wall_h), (x0, ya, za), (x0, yb, zb),
                   (x1, ya, wall_h), (x1, yb, wall_h), (x1, ya, za), (x1, yb, zb)]
            if max(za, zb) - wall_h > 4:
                v.add(S.hull_piece(pts, mat, WK, (cx, cy, z), yaw))
        v.clear.append((*W(end * (length / 2 + 260), 0), gw + 120))
        if closed:
            v.door(S.xform(S.box_planes(x0 + 2, -gw, 0, x1 - 2, gw, gate_h - 2), (cx, cy, z), yaw),
                   S.xform(S.box_planes(x0 + 12, -gw, 0, x1 - 12, gw, gate_h), (cx, cy, z), yaw))
    if lights:
        n = max(2, int(length // 900))
        for i in range(n):
            lx = -length / 2 + length * (i + 0.5) / n
            v.light(*W(lx, 0), z + wall_h + rise * 0.5, "255 150 110 360")
    for i in range(int(length // 600)):
        lx = -length / 2 + 300 + i * 600
        v.nodes_extra.append((*W(lx, -hw * 0.5), z + 16))
        v.nodes_extra.append((*W(lx, hw * 0.5), z + 16))
    if droid:
        v.droid_spawns.append((*W(length / 2 + 320, 0), z + 24))
    return W


def pillbox(v, cx, cy, z, face, r=260):
    """Bunker droïde rond : meurtrières sur tout le tour, porte à l'arrière."""
    v.slab_disc(cx, cy, r + 16, z, M["conc"], sides=12, fall=420)
    segs = 12
    gate = int((((face + 180) % 360) + 15) // 30) % segs
    for k in range(segs):
        a0, a1 = k * 30, (k + 1) * 30
        pl = lambda zz0, zz1: S.mk(S.xform(S.ring_seg_planes(r - 48, r, a0, a1, zz0, zz1), (cx, cy, 0)), M["conc2"], "detail")
        if k == gate:
            v.add(pl(z + 192, z + 224))
        else:
            v.add([pl(z, z + 56), pl(z + 112, z + 224)])
    v.add(S.disc(cx, cy, r + 32, z + 224, z + 256, M["conc2"], "detail", 12))
    v.add(S.dome(cx, cy, r * 0.8, z + 256, M["conc2"], "detail", 2, 12, 0.45))
    v.clear.append((cx, cy, r + 48))
    v.nodes_extra.append((cx, cy, z + 16))


def wall_line(v, pts, z_fn, h=560, thick=160, towers=True, mat=None):
    """Rempart le long d'une ligne brisée, tours rondes aux sommets, chemin de ronde sur le dessus."""
    mat = mat or M["sepwall"]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        yaw = math.degrees(math.atan2(by - ay, bx - ax))
        n = max(1, int(L // 1024))
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            mx, my = ax + (bx - ax) * (t0 + t1) / 2, ay + (by - ay) * (t0 + t1) / 2
            zb = min(z_fn(ax + (bx - ax) * t, ay + (by - ay) * t) for t in (t0, (t0 + t1) / 2, t1)) - 48
            seg_l = L / n
            v.add(S.obox(mx, my, zb, seg_l + 8, thick, h + (z_fn(mx, my) - zb), yaw, mat, "world"))
            # créneaux
            for j in range(int(seg_l // 256)):
                tx = -seg_l / 2 + 128 + j * 256
                c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
                for side in (-1, 1):
                    px, py = mx + tx * c - side * (thick / 2 - 16) * s, my + tx * s + side * (thick / 2 - 16) * c
                    v.add(S.obox(px, py, z_fn(mx, my) + h, 96, 32, 64, yaw, M["trim"], "detail"))
    if towers:
        for (x, y) in pts:
            zz = z_fn(x, y)
            v.add(S.cylinder(x, y, 300, zz - 64, zz + h + 320, mat, "world", 16))
            v.occluder(x, y, 300, zz, zz + h + 320)
            v.add(S.cone(x, y, 300, 380, zz + h + 320, zz + h + 400, M["trim"], "detail", 16))
            v.add(S.disc(x, y, 380, zz + h + 400, zz + h + 432, M["trim"], "detail", 16))
            v.clear.append((x, y, 360))


def landing_pad(v, cx, cy, z, r, h=320, ramp_yaw=180.0, mat=None):
    """Plateforme d'atterrissage ronde surélevée sur piliers, rampe d'accès."""
    mat = mat or M["floor"]
    top = z + h
    v.add(S.disc(cx, cy, r, top - 48, top, mat, "detail", 24))
    v.add(S.cylinder(cx, cy, r + 16, top - 64, top - 48, M["trim"], "detail", 24))
    v.slabs.append(("disc", cx, cy, r - 8, top))
    for k in range(6):
        a = math.radians(30 + 60 * k)
        v.add(S.cylinder(cx + r * 0.7 * math.cos(a), cy + r * 0.7 * math.sin(a), 64, z - 64, top - 48, M["dirty"], "detail", 8))
    v.add(S.cylinder(cx, cy, r * 0.25, z - 64, top - 48, M["dirty"], "detail", 12))
    # anneau de lumière + rambarde basse
    v.add(S.ring_wall(cx, cy, r, 24, top, top + 40, M["hazard"], "detail", 24, gaps={int(((ramp_yaw % 360) + 7.5) // 15) % 24}))
    # rampe
    a = math.radians(ramp_yaw)
    L = h * 3.2
    rx, ry = cx + (r + L / 2 - 32) * math.cos(a), cy + (r + L / 2 - 32) * math.sin(a)
    pitch = math.degrees(math.atan2(h, L))
    # rampe réelle : prisme triangulaire (pleine)
    lx0 = r - 48
    pts = [(lx0, -128, top), (lx0, 128, top), (lx0 + L, -128, z - 16), (lx0 + L, 128, z - 16),
           (lx0, -128, z - 16), (lx0, 128, z - 16)]
    v.add(S.hull_piece(pts, M["grate"], "detail", (cx, cy, 0), ramp_yaw))
    v.clear.append((rx, ry, 200))
    v.clear.append((cx, cy, r + 32))
    v.nodes_extra.append((cx, cy, top + 16))
    return top


def rock_arch(v, x0, y0, x1, y1, z0, z1, width=520, mat=None):
    """Arche rocheuse naturelle entre deux points (piliers + tablier)."""
    mat = mat or M["rock"]
    yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
    L = math.hypot(x1 - x0, y1 - y0)
    for (x, y) in ((x0, y0), (x1, y1)):
        v.add(S.cone(x, y, 420, 300, z0 - 64, z1, mat, "world", 9))
    v.add(S.obox((x0 + x1) / 2, (y0 + y1) / 2, z1 - 40, L, width, 260, yaw, mat, "world"))


def venator_wreck(v):
    """Épave du Venator : coque en lame (flancs inclinés, pont dorsal), tranchée du hangar ouverte (spawn),
    cassure au milieu (sortie), réacteurs à la poupe, deux tours de passerelle (une effondrée)."""
    sx, sy = WRECK_S
    yaw, L = WRECK_YAW, WRECK_L
    Z0 = WRECK_Z
    o = (sx, sy, Z0)
    hw0 = 1550                 # demi-largeur à la poupe
    ch = 380                   # demi-largeur de la tranchée du hangar
    trench_end = 3400
    brk0, brk1 = 3650, 4050    # cassure
    floor_z = 150

    def half(x):
        return max(90.0, hw0 * (1 - x / (L * 1.03)))

    def top(x):
        return 1000 * (1 - 0.72 * x / L)

    span_tf = [(0, brk0, (yaw, 1.0, 2.5)), (brk1, L, (yaw + 3.0, 3.5, -1.5))]

    def piece(pts, mat, tf, kind="world"):
        y_, p_, r_ = tf
        return v.add(S.hull_piece(pts, mat, kind, o, y_, p_, r_))

    for (a, b, tf) in span_tf:
        cuts = [a + (b - a) * i / 3 for i in range(4)]
        for p, q in zip(cuts, cuts[1:]):
            ha, hb = half(p), half(q)
            ta, tb = top(p), top(q)
            # coque inférieure (enterrée)
            piece([(p, -ha * 0.6, -320), (p, ha * 0.6, -320), (q, -hb * 0.6, -320), (q, hb * 0.6, -320),
                   (p, -ha, 200), (p, ha, 200), (q, -hb, 200), (q, hb, 200)], M["hull"], tf)
            for side in (-1, 1):
                ia = ch if p < trench_end else 0.0
                ib = ch if q <= trench_end else 0.0
                oa, ob = max(ha * 0.55, ia + 40), max(hb * 0.55, ib + 40)
                # flanc incliné : de la ligne de flottaison au bord du pont dorsal
                piece([(p, side * ha, 200), (q, side * hb, 200), (p, side * oa, ta), (q, side * ob, tb),
                       (p, side * oa, 200), (q, side * ob, 200)], M["hull2"], tf)
                # pont dorsal (entre la tranchée et le flanc)
                piece([(p, side * ia, 200), (q, side * ib, 200), (p, side * oa, 200), (q, side * ob, 200),
                       (p, side * ia, ta), (q, side * ib, tb), (p, side * oa, ta), (q, side * ob, tb)], M["hull3"], tf)
    tf0 = span_tf[0][2]
    # sol du hangar + fond de tranchée
    piece([(380, -ch, -40), (380, ch, -40), (trench_end, -ch, -40), (trench_end, ch, -40),
           (380, -ch, floor_z), (380, ch, floor_z), (trench_end, -ch, floor_z), (trench_end, ch, floor_z)], M["deck"], tf0)
    # rampe de sortie : du hangar vers la cassure puis le sol
    piece([(trench_end, -ch, -60), (trench_end, ch, -60), (brk0 + 300, -ch, -60), (brk0 + 300, ch, -60),
           (trench_end, -ch, floor_z), (trench_end, ch, floor_z), (brk0 + 300, -ch, -40), (brk0 + 300, ch, -40)], M["grate"], tf0, "detail")
    # cloison de poupe avec porte centrale + rampe arrière
    for side in (-1, 1):
        piece([(380, side * 150, floor_z), (380, side * ch, floor_z), (430, side * 150, floor_z), (430, side * ch, floor_z),
               (380, side * 150, top(380)), (380, side * ch, top(380)), (430, side * 150, top(430)), (430, side * ch, top(430))], M["hull"], tf0)
    piece([(380, -150, floor_z + 220), (380, 150, floor_z + 220), (430, -150, floor_z + 220), (430, 150, floor_z + 220),
           (380, -150, top(380)), (380, 150, top(380)), (430, -150, top(430)), (430, 150, top(430))], M["hull"], tf0)
    piece([(400, -150, floor_z), (400, 150, floor_z), (-700, -150, -200), (-700, 150, -200),
           (400, -150, -60), (400, 150, -60), (-700, -150, -330), (-700, 150, -330)], M["grate"], tf0, "detail")
    # réacteurs (cylindres couchés vers l'arrière)
    for (yy, r) in ((-560, 300), (560, 300), (-1100, 210), (1100, 210)):
        pl = S.xform(S.frustum_round_planes(r, r * 0.9, -620, 40, 12), (0, yy, 420), 0, 90, 0)
        v.add(S.mk(S.xform(pl, o, *tf0), M["dirty"], "world"))
        pl2 = S.xform(S.frustum_round_planes(r * 0.75, r * 0.75, -660, -600, 12), (0, yy, 420), 0, 90, 0)
        v.add(S.mk(S.xform(pl2, o, *tf0), M["redlight"], "detail"), obst=False)
    # tours de passerelle (une debout, une effondrée sur le pont)
    for side, rl, tilt in ((-1, 0.0, 0.0), (1, 1.0, 28.0)):
        bx, by = 1150, side * 620
        stem = [(bx - 230, by - 130, 0), (bx + 230, by - 130, 0), (bx - 230, by + 130, 0), (bx + 230, by + 130, 0),
                (bx - 150, by - 90, 1300), (bx + 150, by - 90, 1300), (bx - 150, by + 90, 1300), (bx + 150, by + 90, 1300)]
        head = [(bx - 200, by - 520, 1300), (bx + 200, by - 520, 1300), (bx - 200, by + 520, 1300), (bx + 200, by + 520, 1300),
                (bx - 150, by - 460, 1560), (bx + 150, by - 460, 1560), (bx - 150, by + 460, 1560), (bx + 150, by + 460, 1560)]
        for pts, mat in ((stem, M["hull"]), (head, M["hull3"])):
            pl = S.xform([(pp, nn) for pp, nn in S.hull_piece(pts, mat).planes], (0, 0, top(bx) - 30), 0, 0, side * tilt)
            v.add(S.mk(S.xform(pl, o, *tf0), mat, "world"))
    # débris arrachés le long du sillon
    ux, uy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for k in range(10):
        d = -1000 - k * 520 + R.uniform(-150, 150)
        off = R.uniform(-1000, 1000)
        px, py = sx + d * ux - off * uy, sy + d * uy + off * ux
        if abs(px) > XB - 900 or abs(py) > XB - 900:
            continue
        zz = v.t.h(px, py)
        v.add(S.obox(px, py, zz - 60, R.uniform(240, 560), R.uniform(160, 380), R.uniform(120, 320), R.uniform(0, 360),
                     R.choice([M["hull"], M["hull2"]]), "detail", pitch=R.uniform(-25, 25), roll=R.uniform(-30, 30)))

    def W(lx, ly, lz=floor_z, tf=tf0):
        p = S.rot(Vec(lx, ly, lz), *tf) + Vec(*o)
        return p.x, p.y, p.z

    # feux et fumée sur l'épave
    for (lx, ly, lz) in ((brk0 - 150, -600, 820), (brk1 + 250, 450, 700), (1900, 1000, 640), (5600, 0, 450), (1150, -620, 1700), (-300, 0, 600)):
        x, y, z = W(lx, ly, lz)
        v.fx.append(("fire", (x, y, z + 16), {"size": 160}))
        if lx in (brk0 - 150, 1150, 5600):
            v.fx.append(("smoke", (x, y, z + 64), {"rate": 7, "size": 460, "color": "40 38 36"}))
    # spawns dans le hangar : 4 rangées x 16
    for i in range(16):
        for j in range(4):
            x, y, z = W(640 + i * 165, -255 + j * 170, floor_z + 24)
            v.spawns.append((round(x), round(y), round(z + 8)))
    for i in range(5):
        x, y, z = W(700 + i * 600, 0, floor_z + 360)
        v.light(x, y, z, "200 225 255 340")
    for i in range(6):
        v.nodes_extra.append(W(600 + i * 500, 0, floor_z + 16))
    # matériel de la République le long des parois du hangar
    for i in range(7):
        for side in (-1, 1):
            x, y, z = W(700 + i * 400, side * (ch - 60), floor_z)
            v.prop(NIK + R.choice(["republic/rep_crate.mdl", "republic/rep_crate_02_open.mdl", "republic/rep_console02.mdl"]),
                   x, y, yaw + 90, z=z, check=False, why="hangar")
    v.label(*W(1800, 0)[:2], "Épave du Venator (spawn)")
    return W


# =====================================================================
#   ZONES
# =====================================================================
def zone_wreck(v):
    W = venator_wreck(v)
    v.zones.append((WRECK_S[0] - 1500, WRECK_S[1] - 1500, WRECK_N[0] + 1200, WRECK_N[1] + 1200, "Épave"))
    nx, ny = WRECK_N
    # FOB avancée devant le nez : LAAT posés, barricades, caisses, AT-TE abattu
    v.clear.append((nx + 300, ny + 300, 400))
    fob = (nx + 1700, ny - 2000)
    v.slab_disc(fob[0], fob[1], 900, v.t.h(*fob) + 16, M["conc"], sides=20, fall=700)
    zf = v.gz(*fob)
    v.prop(MDL + "props/laat/laat.mdl", fob[0] - 300, fob[1] + 250, 225, why="laat")
    v.prop(MDL + "props/laat/laat.mdl", fob[0] + 420, fob[1] - 260, 200, why="laat")
    for k in range(10):
        a = math.radians(36 * k + 10)
        v.prop(NIK + "republic/rep_barricade_metal.mdl", fob[0] + 1000 * math.cos(a), fob[1] + 1000 * math.sin(a),
               math.degrees(a), why="fob")
    v.scatter([NIK + "republic/rep_crate.mdl", NIK + "republic/rep_crate_02_open.mdl", NIK + "imperial/imp_crate_02_x08.mdl",
               NIK + "republic/rep_computer_table.mdl", NIK + "republic/rep_lightpole.mdl"], fob[0], fob[1], 850, 26, "fob")
    v.prop(MDL + "props/starwars/vehicles/atte_crash.mdl", nx + 1500, ny + 2300, 70, why="atte")
    v.prop(MDL + "props/laat/laat.mdl", WRECK_S[0] + 2300, WRECK_S[1] + 3600, 300, why="laat")
    v.label(fob[0], fob[1], "Tête de pont")
    # débris de coque et caisses autour de l'épave
    v.scatter([NIK + "republic/rep_crate_02_broken.mdl", NIK + "debris/debris_generic_engine_01_env.mdl",
               NIK + "containers/con_crate_shipping02_destroyed.mdl", NIK + "republic/rep_barricade_metal.mdl"],
              (WRECK_S[0] + nx) / 2, (WRECK_S[1] + ny) / 2, 3200, 40, "epave")


def zone_valley(v):
    """Vallée rocheuse entre l'épave et la cité : rochers, arches, bunkers droïdes."""
    v.zones.append((-10000, -9000, -2500, -2500, "Vallée"))
    rocks = [MDL + "props_wasteland/rockcliff_cluster03a.mdl", MDL + "props_wasteland/rockcliff_cluster03b.mdl",
             MDL + "props_wasteland/rockcliff_cluster02a.mdl", MDL + "props_wasteland/rockcliff_cluster01b.mdl",
             MDL + "props_wasteland/rockgranite02a.mdl", MDL + "props_wasteland/rockgranite03a.mdl",
             MDL + "props_wasteland/rockcliff01b.mdl", MDL + "props_wasteland/rockcliff05a.mdl"]
    v.scatter(rocks, -6600, -6200, 3600, 70, "rochers")
    for (x0, y0, x1, y1) in ((-7200, -5200, -6000, -4300), (-4200, -7300, -3300, -6200)):
        zz = max(v.t.h(x0, y0), v.t.h(x1, y1))
        rock_arch(v, x0, y0, x1, y1, min(v.t.h(x0, y0), v.t.h(x1, y1)), zz + 620)
    for (x, y, f) in ((-5600, -3600, 225), (-3800, -5200, 225), (-7600, -2600, 250), (-2600, -3600, 220), (-8800, -6200, 230)):
        pillbox(v, x, y, v.t.h(x, y) + 8, f)
    v.droid_spawns.append((-3800, -5200, v.t.h(-3800, -5200) + 40))
    v.label(-6400, -6000, "Vallée des Rochers")
    trees = [MDL + "props_foliage/tree_cliff_01a.mdl", MDL + "props_foliage/tree_cliff_02a.mdl", MDL + "props_foliage/tree_poplar_01.mdl"]
    v.scatter(trees, -7000, -6400, 3800, 26, "arbres")
    bush = [MDL + "fallout_4/landscape/plants/shrubgrouplarge04.mdl", MDL + "fallout_4/landscape/plants/shrubgroupmedium02.mdl",
            MDL + "fallout_4/landscape/plants/shrubgroupsmall01.mdl"]
    v.scatter(bush, -6800, -6400, 3800, 60, "buissons")


def zone_city(v):
    """Cité ouvrière : tours champignons, habitations rondes, place du marché, rues pavées."""
    cx, cy, z = CITY[0], CITY[1], CITY_Z
    v.zones.append((cx - 4200, cy - 4000, cx + 4200, cy + 4000, "Cité ouvrière"))
    # grande place ronde au centre
    v.slab_disc(cx, cy, 1300, z, M["conc"], sides=32, fall=900)
    v.add(S.cylinder(cx, cy, 220, z, z + 64, M["trim"], "detail", 16))
    v.prop(NIK + "city/city_statue_02.mdl", cx, cy, 0, z=z + 64, why="statue")
    for k in range(8):
        a = math.radians(45 * k + 22.5)
        v.prop(NIK + "city/city_street_lamp_tall.mdl", cx + 1150 * math.cos(a), cy + 1150 * math.sin(a), math.degrees(a) + 180, why="lampe")
    for k in range(6):
        a = math.radians(60 * k)
        v.prop(NIK + "city/market_banner_canopy_02.mdl", cx + 800 * math.cos(a), cy + 800 * math.sin(a), math.degrees(a) + 90, why="marche")
        v.prop(NIK + "containers/con_box_crate_06.mdl", cx + 680 * math.cos(a + 0.2), cy + 680 * math.sin(a + 0.2), R.uniform(0, 90), why="marche")
    v.label(cx, cy, "Place du Marché")
    # avenues pavées (4 directions) : on les garde libres
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        for d in range(1500, 4100, 900):
            px, py = cx + d * math.cos(a), cy + d * math.sin(a)
            v.slab_rect(px - 460, py - 460, px + 460, py + 460, z, M["conc2"], fall=700)
            v.clear.append((px, py, 380))
    # anneau de tours champignons
    for (dx, dy, r, h) in ((-2300, -2200, 360, 1300), (2400, -2100, 400, 1500), (-2500, 2300, 380, 1700),
                           (2300, 2500, 340, 1250), (-3600, 200, 300, 1000), (3500, -500, 320, 1100), (0, 3600, 360, 1600)):
        mushroom_tower(v, cx + dx, cy + dy, r, v.t.h(cx + dx, cy + dy) if False else z, h)
        v.slab_disc(cx + dx, cy + dy, r * 1.5, z, M["conc2"], sides=16, fall=600)
    # habitations rondes à dôme, accessibles
    homes = [(-1500, -2600), (1500, -2700), (-2900, -1100), (2900, 1100), (-1300, 2700), (1400, 3000), (-3000, 1500),
             (3200, -1700), (-700, -3500), (800, 4200), (-3800, 3200), (3900, 2900), (-4100, -1900), (4200, 300)]
    for i, (dx, dy) in enumerate(homes):
        r = R.choice([320, 380, 440])
        face = math.degrees(math.atan2(-dy, -dx))
        round_hall(v, cx + dx, cy + dy, r, z, R.choice([320, 384]), doors=(face, face + 180),
                   roof=R.choice(["dome", "dome", "cone"]), wall=R.choice([M["pk"], M["wall"], M["wall2"]]),
                   kind="detail", droid=(i in (2, 9)), light="255 170 120 160")
    # grand bâtiment administratif (rond, haut, toit champignon)
    round_hall(v, cx - 1200, cy + 1300, 620, z, 560, doors=(225, 45, 135), roof="mushroom", kind="world", droid=True)
    v.label(cx - 1200, cy + 1300, "Administration")
    # décor de rue
    deco = [NIK + "city/city_furn_bench_metal.mdl", NIK + "city/city_street_lamp.mdl", NIK + "city/city_sign_billboard_red_animated.mdl",
            NIK + "containers/con_box_crate_02.mdl", NIK + "containers/con_crate_shipping02.mdl", NIK + "city/city_firebarrel.mdl",
            NIK + "underworld/und_barricade.mdl", NIK + "items/banner_separatist.mdl", NIK + "city/city_sign_vertical.mdl"]
    v.scatter(deco, cx, cy, 4200, 120, "rue", avoid_clear=True)
    v.label(cx, cy - 3300, "Cité ouvrière de Vexis")


def zone_agri(v):
    """Complexe de vivres : serres voûtées vitrées, dômes hydroponiques, silos à grain, stockage."""
    cx, cy, z = AGRI[0], AGRI[1], AGRI_Z
    v.zones.append((cx - 3800, cy - 3600, cx + 3800, cy + 3200, "Vivres"))
    for i, (dx, dy, yaw) in enumerate(((-1600, 900, 0), (-1600, -900, 0), (1500, 1200, 90), (2600, -900, 30))):
        W = vault_hall(v, cx + dx, cy + dy, z, 2200, 900, 260, 360, yaw, mat=M["wall2"], roof_mat=M["glass"],
                       lights=True, droid=(i == 0), closed=False)
        # rangées de cultures
        for j in range(5):
            for side in (-1, 1):
                px, py = W(-850 + j * 420, side * 230)
                v.prop(MDL + "props_foliage/hedgerow01_small-bushy.mdl", px, py, yaw, why="cultures")
    for (dx, dy, r) in ((300, 2600, 700), (-3000, -2200, 560)):
        v.slab_disc(cx + dx, cy + dy, r + 120, z, M["conc"], sides=20)
        v.add(S.ring_wall(cx + dx, cy + dy, r, 32, z, z + 120, M["wall2"], "detail", 16, gaps={0, 8}))
        v.add(S.dome(cx + dx, cy + dy, r, z + 120, M["glass"], "detail", 4, 16, 0.75), obst=True)
    for k, (dx, dy) in enumerate(((800, -2400), (1300, -2600), (1800, -2400), (2300, -2600), (-3400, 600), (-3400, 1300))):
        silo(v, cx + dx, cy + dy, 230, z, 900 + 120 * (k % 3))
    v.scatter([NIK + "slum/slum_food_storage_unit.mdl", NIK + "containers/con_box_crate_06.mdl",
               NIK + "construction/construction_storage_compactor_01.mdl", NIK + "misc/misc_campfire_barrel.mdl"],
              cx, cy, 3400, 50, "vivres")
    trees = [MDL + "props_foliage/tree_deciduous_01a.mdl", MDL + "props_foliage/tree_deciduous_02a.mdl",
             MDL + "props_foliage/tree_deciduous_03a.mdl", MDL + "props_foliage/oak_tree01.mdl", MDL + "props_foliage/tree_poplar_01.mdl"]
    v.scatter(trees, cx, cy, 4800, 70, "arbres")
    v.scatter([MDL + "fallout_4/landscape/plants/shrubgrouplarge05.mdl", MDL + "fallout_4/landscape/plants/shrubgroupmedium03.mdl",
               MDL + "props_foliage/hedgerow02_medium_long.mdl"], cx, cy, 4800, 80, "buissons")
    v.label(cx, cy, "Serres de vivres")


def zone_factories(v):
    """Fonderies et chaînes de montage de droïdes : halles voûtées, fonderie à lave, cheminées, tours de refroidissement."""
    cx, cy, z = FACT[0], FACT[1], FACT_Z
    v.zones.append((cx - 4200, cy - 3800, cx + 4600, cy + 3000, "Usines"))
    v.slab_disc(cx + 100, cy - 400, 3500, z, M["conc"], sides=32, fall=1000)
    v.slab_disc(cx + 2700, cy - 2200, 1500, z, M["conc"], sides=20, fall=800)
    # 3 halles de montage (axe est-ouest)
    halls = []
    for i, dy in enumerate((-1900, 0, 1700)):
        W = vault_hall(v, cx - 600, cy + dy, z, 3600, 1100, 420, 420, 0, mat=M["wall3"], roof_mat=M["hull3"],
                       droid=(i != 1))
        halls.append(W)
        # chaîne de montage : distributeurs de droïdes, bras, nacelles
        for j in range(6):
            px, py = W(-1400 + j * 560, -200)
            v.prop(MDL + R.choice(["props/starwars/vehicles/bd_dispenser.mdl", "props/starwars/vehicles/sbd_dispenser.mdl",
                                   "props/starwars/vehicles/droideka_dispenser.mdl"]), px, py, 90, why="chaine")
            qx, qy = W(-1400 + j * 560, 180)
            v.prop(NIK + "factory/factory_conveyor_arm.mdl", qx, qy, 180, check=False, why="chaine")
            rx, ry = W(-1150 + j * 560, 330)
            v.prop(NIK + "tech/tech_droid_pod.mdl", rx, ry, 0, z=z + 142, why="chaine")
        # tapis roulant (brush) le long de la chaîne
        ax, ay = W(-1600, 0); bx, by = W(1600, 0)
        v.blk((min(ax, bx), ay - 64, z, max(ax, bx), ay + 64, z + 48), M["grate"], "detail")
        v.label(*W(0, 0), ["Chaîne B1", "Chaîne B2", "Chaîne Droidekas"][i])
    # fonderie : halle ronde avec bassins de lave
    fx, fy = cx + 2600, cy - 300
    round_hall(v, fx, fy, 1000, z, 640, doors=(180, 0, 90, 270), roof="cone", wall=M["walld"], kind="world",
               light="255 120 60 600", segs=24, droid=True)
    for (dx, dy) in ((-380, -380), (380, 380), (-380, 380), (380, -380)):
        v.blk((fx + dx - 160, fy + dy - 160, z - 64, fx + dx + 160, fy + dy + 160, z - 24), M["lava"], "detail", obst=False)
        v.add(S.ring_wall(fx + dx, fy + dy, 200, 40, z - 32, z + 48, M["dirty"], "detail", 12))
        v.w.ent("trigger_hurt", None, solids=[Block((fx + dx - 160, fy + dy - 160, z - 64, fx + dx + 160, fy + dy + 160, z + 8), "tools/toolstrigger")],
                damage=60, damagetype=8, spawnflags=1 | 2 | 8)
        v.light(fx + dx, fy + dy, z + 64, "255 110 40 260")
    v.prop(NIK + "factory/factory_cauldron_stand.mdl", fx, fy, 0, why="fonderie")
    v.prop(NIK + "factory/factory_cauldron.mdl", fx, fy, 0, z=z + 70, check=False, why="fonderie")
    v.prop(NIK + "factory/factory_incinerator.mdl", fx + 700, fy, 180, why="fonderie")
    v.prop(NIK + "factory/factory_incinerator.mdl", fx - 700, fy, 0, why="fonderie")
    v.label(fx, fy, "Fonderie")
    # cheminées et tours de refroidissement
    for (dx, dy, h) in ((3600, 1600, 2600), (3900, 900, 2300), (-3200, 2100, 2400)):
        chimney(v, cx + dx, cy + dy, 150, z, h)
    for (dx, dy) in ((3400, -2600), (1900, -3000)):
        cooling_tower(v, cx + dx, cy + dy, 640, z, 2000)
    # tuyaux, grues, réservoirs
    for (dx, dy) in ((-3300, -2800), (-2900, 1900), (300, 2100)):
        v.prop(NIK + "construction/construction_crane_base.mdl", cx + dx, cy + dy, 0, why="grue")
        v.prop(NIK + "construction/construction_crane_sway.mdl", cx + dx, cy + dy, R.uniform(0, 360), check=False, why="grue")
    v.scatter([NIK + "containers/con_tank_toxic_damaged_01.mdl", NIK + "tech/tech_mine_barrel.mdl", NIK + "tech/tech_canister_fire.mdl",
               NIK + "containers/con_small_container_pipes_stack.mdl", NIK + "tech/tech_huge_generator.mdl",
               NIK + "imperial/imp_crate_02_x12.mdl", NIK + "construction/construction_dumpster_droid.mdl"],
              cx, cy, 4200, 110, "usine")


def zone_port(v):
    """Spatioport et dépôt d'armes : vaisseau de la Techno Union posé, plateformes, entrepôts, défense anti-aérienne."""
    cx, cy, z = PORT[0], PORT[1], PORT_Z
    v.zones.append((cx - 4200, cy - 4200, cx + 4000, cy + 4400, "Spatioport"))
    v.slab_disc(cx, cy + 100, 3900, z, M["floor2"], sides=32, fall=1100)
    # grande aire du vaisseau
    tx, ty = cx + 1500, cy + 600
    v.slab_disc(tx, ty, 2300, z + 16, M["floor"], sides=32, flat=False)
    v.add(S.ring_wall(tx, ty, 2300, 48, z + 16, z + 64, M["hazard"], "detail", 32, gaps={0, 8, 16, 24}))
    v.prop(MDL + "props/starwars/vehicles/techno_union.mdl", tx, ty, 200, z=z + 16, check=False, why="techno")
    v.add_obst((tx - 1500, ty - 1500, z, tx + 1500, ty + 1500, z + 8000))
    v.occluder(tx, ty, 1100, z + 400, z + 2400)
    v.label(tx, ty, "Vaisseau de la Techno Union")
    # plateformes d'atterrissage
    for (dx, dy, yaw) in ((-2400, 2600, 270), (-2600, -1900, 90), (600, -2900, 90)):
        landing_pad(v, cx + dx, cy + dy, z, 720, 320, yaw)
    v.label(cx - 2400, cy + 2600, "Plateforme Nord")
    # entrepôts d'armes (halles voûtées)
    for i, (dx, dy, yaw) in enumerate(((-1000, -500, 90), (-1500, 900, 0))):
        W = vault_hall(v, cx + dx, cy + dy, z, 2000, 900, 360, 320, yaw, mat=M["sepwall"], roof_mat=M["hull3"], droid=True)
        for j in range(8):
            for side in (-1, 1):
                px, py = W(-800 + j * 230, side * 300)
                v.prop(NIK + R.choice(["imperial/imp_crate_02_x12.mdl", "imperial/imp_crate_02_x08.mdl", "containers/crate_weapon_02.mdl"]),
                       px, py, yaw, why="armes")
        v.label(*W(0, 0), "Dépôt d'armes " + "AB"[i])
    # tour de contrôle
    tcx, tcy = cx - 3000, cy + 400
    v.add(S.cylinder(tcx, tcy, 260, z - 32, z + 1400, M["pkb"], "world", 16))
    v.occluder(tcx, tcy, 260, z, z + 1400)
    v.add(S.cone(tcx, tcy, 260, 640, z + 1400, z + 1650, M["hull3"], "world", 16))
    v.add(S.cylinder(tcx, tcy, 640, z + 1650, z + 1900, M["glass"], "detail", 16))
    v.add(S.cone(tcx, tcy, 640, 120, z + 1900, z + 2150, M["hull"], "detail", 16))
    v.clear.append((tcx, tcy, 300))
    v.label(tcx, tcy, "Tour de contrôle")
    # défense anti-aérienne + missiles + caisses
    for (dx, dy) in ((-3200, -3100), (3000, -3200), (3100, 3500), (-3300, 3500), (200, 3500)):
        v.prop(NIK + "turrets/neu_autoturret01.mdl", cx + dx, cy + dy, R.uniform(0, 360), why="defense")
    v.scatter([NIK + "tech/tech_missiles_large.mdl", NIK + "tech/tech_missile_medium.mdl", NIK + "containers/crate_weapon_01.mdl",
               NIK + "imperial/imp_crate_02_x04.mdl", NIK + "containers/con_crate_shipping02.mdl", NIK + "tech/tech_power_cores_shielded_01.mdl",
               NIK + "tech/tech_exterior_lightpost.mdl", NIK + "items/banner_separatist.mdl"], cx, cy, 4000, 130, "depot")
    v.droid_spawns.append((cx + 2900, cy - 1500, z + 24))


def zone_citadel(v):
    """Citadelle du gouverneur sur son plateau : rempart, palais rond, générateur de bouclier, canons."""
    cx, cy, z = CIT[0], CIT[1], CIT_Z
    v.zones.append((cx - CIT_R - 600, cy - CIT_R - 600, cx + CIT_R + 600, cy + CIT_R + 600, "Citadelle"))
    v.slab_disc(cx, cy, 1700, z + 16, M["conc"], sides=32, fall=600)
    # rempart polygonal avec 2 grandes portes (sud et ouest) laissées ouvertes
    def arc(a0, a1, n):
        return [(cx + 2150 * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + 2150 * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
                for i in range(n + 1)]
    # porte sud (260..300 deg) et porte ouest (140..220 deg) laissées ouvertes
    wall_line(v, arc(-60, 140, 5), lambda x, y: v.t.h(x, y), h=520, thick=176)
    wall_line(v, arc(220, 260, 1), lambda x, y: v.t.h(x, y), h=520, thick=176)
    v.label(cx - 2300, cy, "Porte Ouest")
    v.label(cx, cy - 2300, "Porte Sud")
    # palais : grande tour ronde + anneau d'ailes
    round_hall(v, cx, cy, 900, z + 16, 720, doors=(270, 180, 0, 90), roof="mushroom", wall=M["pk"], kind="world",
               segs=24, light="255 90 70 500", droid=True)
    v.add(S.cylinder(cx, cy, 420, z + 800, z + 2600, M["pkb"], "world", 16))
    v.occluder(cx, cy, 420, z + 800, z + 2600)
    v.add(S.cone(cx, cy, 420, 900, z + 2600, z + 2900, M["hull3"], "world", 16))
    v.add(S.disc(cx, cy, 900, z + 2900, z + 2950, M["trim"], "detail", 16))
    v.add(S.dome(cx, cy, 600, z + 2950, M["hull"], "detail", 4, 16, 0.5))
    v.add(S.cylinder(cx, cy, 30, z + 3250, z + 4200, M["trim"], "detail", 8))
    v.label(cx, cy, "Palais du Gouverneur")
    # postes de commandement CIS et ailes
    for (dx, dy, yaw) in ((-1300, -300, 0), (1300, 200, 180), (100, 1300, 270)):
        v.prop(MDL + "props/starwars/tech/cis_command.mdl", cx + dx, cy + dy, yaw, why="cis")
    # générateur de bouclier (dôme + émetteur)
    gx, gy = cx + 1500, cy + 1500
    v.add(S.cylinder(gx, gy, 360, z, z + 240, M["dirty"], "world", 16))
    v.add(S.dome(gx, gy, 360, z + 240, M["hull3"], "detail", 3, 16, 0.8))
    v.add(S.cylinder(gx, gy, 40, z + 520, z + 1300, M["trim"], "detail", 8))
    v.add(S.disc(gx, gy, 160, z + 1300, z + 1340, M["redlight"], "detail", 12))
    v.fx.append(("tesla", (gx, gy, z + 1320), {}))
    v.label(gx, gy, "Générateur de bouclier")
    for (dx, dy) in ((-1600, 1200), (1700, -1200), (-1500, -1500), (300, -1700)):
        v.prop(NIK + "turrets/neu_autoturret01_mortar.mdl", cx + dx, cy + dy, R.uniform(0, 360), why="defense")
    v.scatter([NIK + "items/banner_separatist.mdl", NIK + "imperial/imp_crate_02_x05.mdl", NIK + "tech/tech_exterior_lightpost.mdl",
               NIK + "underworld/und_barricade.mdl", NIK + "tech/tech_power_cores_shielded_01.mdl"], cx, cy, 2000, 60, "citadelle")
    v.droid_spawns += [(cx - 600, cy + 600, z + 40), (cx + 600, cy - 600, z + 40)]


def zone_mines(v):
    """Canyon des mines : foreuses, grues, pont rocheux, poste de garde droïde."""
    v.zones.append((3000, -13400, 13800, -6000, "Mines"))
    for (x, y) in CANYON[1:-1]:
        zz = v.t.h(x, y)
        for k in range(3):
            a = R.uniform(0, 2 * math.pi)
            v.prop(NIK + "tech/tech_mining_drill.mdl", x + 400 * math.cos(a), y + 400 * math.sin(a), R.uniform(0, 360), why="mine")
        v.prop(NIK + "construction/construction_crane_base.mdl", x + 200, y - 300, 0, why="grue")
        v.prop(NIK + "construction/construction_crane_sway.mdl", x + 200, y - 300, R.uniform(0, 360), check=False, why="grue")
    # pont de pierre au-dessus du canyon
    (ax, ay), (bx, by) = CANYON[2], CANYON[3]
    mx, my = (ax + bx) / 2, (ay + by) / 2
    dx, dy = -(by - ay), bx - ax
    L = math.hypot(dx, dy); dx, dy = dx / L, dy / L
    p0 = (mx - 1500 * dx, my - 1500 * dy); p1 = (mx + 1500 * dx, my + 1500 * dy)
    rock_arch(v, *p0, *p1, v.t.h(mx, my), max(v.t.h(*p0), v.t.h(*p1)) - 40, width=560, mat=M["rockred"])
    v.label(mx, my, "Pont du Canyon")
    v.scatter([NIK + "tech/tech_mine_canister.mdl", NIK + "tech/tech_mine_barrel.mdl", NIK + "construction/construction_storage_compactor_01.mdl",
               NIK + "caves/caves_large_boulder_neu.mdl", NIK + "caves/caves_medium_boulder_neu_01.mdl",
               MDL + "props_wasteland/rockcliff_cluster03c.mdl"], 8200, -9700, 4200, 90, "mine")
    # raffinerie de minerai sur le rebord sud
    W = vault_hall(v, 10200, -10900, v.t.h(10200, -10900) + 24, 2400, 1000, 380, 380, 25, mat=M["dirty"], roof_mat=M["hull3"], droid=True)
    v.label(10200, -10900, "Raffinerie")
    # passerelle de convoyeur au-dessus du canyon (praticable)
    (ax, ay) = CANYON[1]
    (bx, by) = CANYON[2]
    tx, ty = (bx - ax), (by - ay)
    L = math.hypot(tx, ty); tx, ty = tx / L, ty / L
    nx_, ny_ = -ty, tx
    p0 = (ax - 1700 * nx_, ay - 1700 * ny_); p1 = (ax + 1700 * nx_, ay + 1700 * ny_)
    zc = max(v.t.h(*p0), v.t.h(*p1)) + 160
    yawc = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    v.add(S.obox((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, zc - 32, 3600, 256, 32, yawc, M["grate"], "detail"))
    for side in (-1, 1):
        mx, my = (p0[0] + p1[0]) / 2 + side * 112 * -math.sin(math.radians(yawc)), (p0[1] + p1[1]) / 2 + side * 112 * math.cos(math.radians(yawc))
        v.add(S.obox(mx, my, zc, 3600, 16, 48, yawc, M["trim"], "detail"))
    for t in (-1200, 0, 1200):
        px, py = (p0[0] + p1[0]) / 2 + t * math.cos(math.radians(yawc)), (p0[1] + p1[1]) / 2 + t * math.sin(math.radians(yawc))
        v.add(S.cylinder(px, py, 56, v.t.h(px, py) - 64, zc - 32, M["dirty"], "detail", 8))
    v.label(ax, ay, "Passerelle du convoyeur")
    # chevalements de mine (tours à 4 pieds) au fond du canyon
    for (x, y) in (CANYON[1], CANYON[3]):
        x += 500; y -= 300
        zz = v.t.h(x, y)
        for dx, dy in ((-160, -160), (160, -160), (-160, 160), (160, 160)):
            v.add(S.cylinder(x + dx, y + dy, 28, zz - 32, zz + 1100, M["dirty"], "detail", 6))
        v.add(S.disc(x, y, 260, zz + 1100, zz + 1132, M["grate"], "detail", 12))
        v.add(S.cylinder(x, y, 120, zz + 1132, zz + 1180, M["trim"], "detail", 12))
        v.clear.append((x, y, 280))
    pillbox(v, 6400, -7600, v.t.h(6400, -7600) + 8, 200)
    pillbox(v, 9800, -6800, v.t.h(9800, -6800) + 8, 220)
    v.droid_spawns.append((8200, -9600, v.t.h(8200, -9600) + 40))
    v.label(8200, -10800, "Canyon des Mines")


def outposts(v):
    """Avant-postes dans les grands espaces : relais de communication (nord), dépôt de carburant (sud), batterie AA (est)."""
    # relais de communication sur le piton nord
    x, y = -600, 9800
    z = v.t.h(x, y)
    v.slab_disc(x, y, 700, z + 8, M["conc"], sides=20, fall=500)
    z = z + 8
    v.add(S.cylinder(x, y, 90, z, z + 1500, M["dirty"], "world", 10))
    v.add(S.cone(x, y, 60, 520, z + 1500, z + 1700, M["hull"], "detail", 16))
    v.add(S.cylinder(x, y, 20, z + 1700, z + 2100, M["trim"], "detail", 6))
    for a in (30, 150, 270):
        pillbox(v, x + 520 * math.cos(math.radians(a)), y + 520 * math.sin(math.radians(a)), z, a)
    v.fx.append(("tesla", (x, y, z + 2080), {}))
    v.droid_spawns.append((x, y - 300, z + 24))
    v.label(x, y, "Relais de communication")
    v.zones.append((x - 900, y - 900, x + 900, y + 900, "Relais"))
    # dépôt de carburant au sud
    x, y = -1800, -11300
    z = v.t.h(x, y) + 16
    v.slab_disc(x, y, 1500, z, M["conc2"], sides=24, fall=700)
    for k in range(5):
        a = math.radians(72 * k + 10)
        tx, ty = x + 900 * math.cos(a), y + 900 * math.sin(a)
        v.add(S.cylinder(tx, ty, 300, z, z + 420, M["hull"], "world", 16))
        v.add(S.dome(tx, ty, 300, z + 420, M["hull"], "detail", 3, 16, 0.5))
        v.add(S.cylinder(tx, ty, 310, z + 300, z + 340, M["hazard"], "detail", 16), obst=False)
        v.clear.append((tx, ty, 340))
        # conduite vers le centre
        v.add(S.obox((x + tx) / 2, (y + ty) / 2, z + 80, 600, 48, 48, math.degrees(a), M["dirty"], "detail"))
    pillbox(v, x, y, z, 45, r=300)
    v.scatter([NIK + "tech/tech_canister_fire.mdl", NIK + "containers/con_toxicwaste_barrel.mdl", NIK + "tech/tech_mine_barrel.mdl"],
              x, y, 1700, 30, "carburant")
    v.label(x, y - 1300, "Dépôt de carburant")
    v.zones.append((x - 1600, y - 1600, x + 1600, y + 1600, "Carburant"))
    # batterie anti-aérienne à l'est
    x, y = 12000, -2400
    z = v.t.h(x, y) + 16
    v.slab_disc(x, y, 1100, z, M["conc"], sides=20, fall=600)
    for k in range(3):
        a = math.radians(120 * k + 90)
        tx, ty = x + 600 * math.cos(a), y + 600 * math.sin(a)
        v.add(S.ring_wall(tx, ty, 300, 64, z, z + 96, M["conc2"], "detail", 12, gaps={0}))
        v.prop(NIK + "turrets/neu_autoturret01.mdl", tx, ty, math.degrees(a), z=z, check=False, why="aa")
    pillbox(v, x, y, z, 270)
    v.droid_spawns.append((x - 200, y, z + 24))
    v.label(x, y - 1000, "Batterie anti-aérienne")
    v.zones.append((x - 1200, y - 1200, x + 1200, y + 1200, "AA"))


def nature(v):
    """Rochers et végétation éparse sur le reste du terrain (hors zones construites)."""
    rocks = [MDL + "props_wasteland/rockgranite02a.mdl", MDL + "props_wasteland/rockgranite03b.mdl",
             MDL + "props_wasteland/rockcliff_cluster02b.mdl", MDL + "props_wasteland/rockcliff06d.mdl",
             NIK + "caves/caves_large_boulder_ald.mdl"]
    for _ in range(320):
        x, y = R.uniform(-12800, 12800), R.uniform(-12800, 12800)
        if any(z0 <= x <= z1 and w0 <= y <= w1 for (z0, w0, z1, w1, _) in v.zones) or v.in_clear(x, y, 200) or v.t.on_track(x, y, 200):
            continue
        if v.t.slope(x, y) > 0.35:
            v.prop(R.choice(rocks), x, y, R.uniform(0, 360), sink=24, why="nature")
        elif R.random() < 0.35:
            v.prop(R.choice([MDL + "props_foliage/tree_cliff_02a.mdl", MDL + "fallout_4/landscape/plants/shrubgrouplarge04.mdl",
                             MDL + "props_foliage/tree_dry01_big.mdl"]), x, y, R.uniform(0, 360), why="nature")
    # falaises de bord : gros rochers posés sur les pentes des montagnes
    for _ in range(140):
        side = R.randrange(4)
        d = R.uniform(1200, 2600)
        u = R.uniform(-13500, 13500)
        x, y = [(XA + d, u), (XB - d, u), (u, XA + d), (u, XB - d)][side]
        v.prop(R.choice([MDL + "props_wasteland/rockcliff01b.mdl", MDL + "props_wasteland/rockcliff05a.mdl",
                         MDL + "props_wasteland/rockcliff_cluster03a.mdl"]), x, y, R.uniform(0, 360), sink=48, why="bord")


def build():
    v = V()
    relief(v.t)
    tracks(v.t)
    zone_wreck(v)
    zone_valley(v)
    zone_city(v)
    zone_agri(v)
    zone_factories(v)
    zone_port(v)
    zone_citadel(v)
    zone_mines(v)
    outposts(v)
    nature(v)
    v.resolve()
    return v
