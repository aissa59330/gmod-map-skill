"""Terrain de Vexis : carte de hauteur -> dalles à déplacement (displacements) + bloqueurs de visibilité.

La hauteur h(x, y) = relief de base (bruit) + montagnes en bordure + reliefs dessinés (plateaux, canyon,
crêtes, sillon du crash) ; puis des zones aplanies (dalles des bâtiments) et des pistes.
Chaque dalle de TILE x TILE porte un déplacement de puissance POWER ; sous chaque dalle, une colonne
nodraw en world (jusqu'au point le plus bas de la dalle) bloque la visibilité derrière les collines.
"""
import math

TILE = 1024
POWER = 3
N = 2 ** POWER + 1          # sommets par côté
STEP = TILE // (N - 1)      # 128


# ---------------- bruit déterministe ----------------
def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def _smooth(t):
    return t * t * (3 - 2 * t)


def vnoise(x, y, seed=1):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = _smooth(x - ix), _smooth(y - iy)
    a = _hash(ix, iy, seed); b = _hash(ix + 1, iy, seed)
    c = _hash(ix, iy + 1, seed); d = _hash(ix + 1, iy + 1, seed)
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy   # 0..1


def fbm(x, y, octaves=4, seed=1):
    s, amp, f, tot = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        s += amp * (vnoise(x * f, y * f, seed + o * 17) * 2 - 1)
        tot += amp; amp *= 0.5; f *= 2.03
    return s / tot     # -1..1


def smoothstep(e0, e1, x):
    if e1 == e0:
        return 1.0 if x >= e1 else 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy), qx, qy


def poly_dist(px, py, pts):
    best = (1e18, 0, 0)
    for i in range(len(pts) - 1):
        d = seg_dist(px, py, *pts[i], *pts[i + 1])
        if d[0] < best[0]:
            best = d
    return best


class Terrain:
    def __init__(self, x0, y0, x1, y1, floor_z):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.floor_z = floor_z
        self.features = []      # fonctions (x, y, h) -> h, appliquées dans l'ordre
        self.flats = []         # (kind, geom, z, falloff)
        self.tracks = []        # (points, half_width) : pistes (alpha terre + aplanies en travers)
        self.regions = []       # (fn(x, y) -> bool, material) : premier qui répond
        self.holes = set()      # (x0, y0) des dalles de 1024 SANS déplacement ni bloqueur (puits vers les cavernes)
        self.default_mat = "nature/blendrockdirt006a"
        self.alpha_fn = None
        self._cache = {}

    # ---- relief ----
    def base(self, x, y):
        h = 80 + 260 * fbm(x / 5200, y / 5200, 4, 3) + 70 * fbm(x / 1300, y / 1300, 3, 11)
        # montagnes de bordure : la zone de jeu est une grande cuvette
        d = min(x - self.x0, self.x1 - x, y - self.y0, self.y1 - y)
        if d < 3400:
            k = (1 - d / 3400) ** 1.7
            h += k * (2600 + 1100 * fbm(x / 2600, y / 2600, 4, 23)) + k * 380 * abs(fbm(x / 700, y / 700, 3, 31))
        for f in self.features:
            h = f(x, y, h)
        return h

    def h(self, x, y):
        key = (round(x), round(y))
        v = self._cache.get(key)
        if v is not None:
            return v
        h = self.base(x, y)
        # pistes : on aplanit en travers (hauteur prise sur l'axe), pente douce le long
        for pts, hw in self.tracks:
            d, qx, qy = poly_dist(x, y, pts)
            if d < hw + 640:
                hc = self.base(qx, qy)
                w = 1 - smoothstep(hw, hw + 640, d)
                h = h + (hc - h) * w
        # dalles aplanies (bâtiments, places, plateformes)
        for kind, g, z, fall in self.flats:
            if kind == "rect":
                ax, ay, bx, by = g
                dx = max(ax - x, 0, x - bx); dy = max(ay - y, 0, y - by)
                d = math.hypot(dx, dy)
            else:
                cx, cy, r = g
                d = max(0.0, math.hypot(x - cx, y - cy) - r)
            if d < fall:
                w = 1 - smoothstep(0, fall, d)
                h = h + (z - h) * w
        self._cache[key] = h
        return h

    # ---- outils de dessin ----
    def flat_rect(self, x0, y0, x1, y1, z, fall=512):
        self._cache.clear()
        self.flats.append(("rect", (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), z, fall))

    def flat_disc(self, cx, cy, r, z, fall=512):
        self._cache.clear()
        self.flats.append(("disc", (cx, cy, r), z, fall))

    def track(self, pts, half_width=320):
        self._cache.clear()
        self.tracks.append((pts, half_width))

    def on_track(self, x, y, extra=0):
        for pts, hw in self.tracks:
            if poly_dist(x, y, pts)[0] < hw + extra:
                return True
        return False

    def slope(self, x, y, e=64):
        dx = (self.h(x + e, y) - self.h(x - e, y)) / (2 * e)
        dy = (self.h(x, y + e) - self.h(x, y - e)) / (2 * e)
        return math.hypot(dx, dy)

    def material(self, cx, cy):
        for fn, mat in self.regions:
            if fn(cx, cy):
                return mat
        return self.default_mat

    # ---- export ----
    def tiles(self):
        """-> liste de (x0, y0, x1, y1, base_z, heights[N][N] (ligne = y), alphas, mat, zmin, zmax)."""
        out = []
        x = self.x0
        while x < self.x1:
            y = self.y0
            while y < self.y1:
                hs, al = [], []
                for j in range(N):            # ligne j -> y
                    row, arow = [], []
                    for i in range(N):        # colonne i -> x
                        px, py = x + i * STEP, y + j * STEP
                        hz = self.h(px, py)
                        row.append(hz)
                        arow.append(self.alpha(px, py))
                    hs.append(row); al.append(arow)
                zmin = min(min(r) for r in hs); zmax = max(max(r) for r in hs)
                base = math.floor((zmin - 8) / 16) * 16
                out.append((x, y, x + TILE, y + TILE, base, hs, al, self.material(x + TILE / 2, y + TILE / 2), zmin, zmax))
                y += TILE
            x += TILE
        return out

    def alpha(self, x, y):
        """255 = 2e texture (terre / herbe), 0 = 1re (roche) : roche sur les pentes, terre sur le plat et les pistes."""
        if self.alpha_fn:
            a = self.alpha_fn(self, x, y)
            if a is not None:
                return a
        s = self.slope(x, y)
        a = 255 * (1 - smoothstep(0.28, 0.62, s))
        a *= 0.8 + 0.2 * (fbm(x / 900, y / 900, 2, 51) * 0.5 + 0.5)
        if self.on_track(x, y):
            a = 255
        return max(0, min(255, a))


def add_displacements(vmf, terrain, lightmap=32, lightmap_far=64, dz=0):
    """Crée les brushes à déplacement (world) + les colonnes nodraw qui bloquent la vue sous le relief."""
    from srctools import Vec
    from srctools.vmf import DispVertex
    n_disp = n_block = 0
    tops = []
    for (x0, y0, x1, y1, base, hs, al, mat, zmin, zmax) in terrain.tiles():
        if (x0, y0) in terrain.holes:
            continue
        pr = vmf.make_prism(Vec(x0, y0, base - 16 + dz), Vec(x1, y1, base + dz), "tools/toolsnodraw")
        top = pr.top
        top.mat = mat
        # montagnes de bordure (hors de portée des combats) : éclairage moins fin
        d_edge = min(x0 - terrain.x0, terrain.x1 - x1, y0 - terrain.y0, terrain.y1 - y1)
        top.lightmap = lightmap_far if d_edge < 2048 else lightmap
        top.disp_power = POWER
        top.disp_pos = Vec(x0, y0, base + dz)
        top.disp_elevation = 0.0
        top.disp_allowed_vert = __import__("array").array("i", (-1,) * 10)
        verts = []
        for j in range(N):
            for i in range(N):
                v = DispVertex(i, j)
                v.normal = Vec(0, 0, 1)
                v.distance = hs[j][i] - base
                v.alpha = al[j][i]
                verts.append(v)
        top._disp_verts = verts
        vmf.add_brush(pr.solid)
        n_disp += 1
        tops.append((x0, y0, x1, y1, base))
    # bloqueurs de visibilité sous le relief : hauteurs arrondies (pas de 256) puis fusion en grands rectangles
    q = {}
    for (x0, y0, x1, y1, base) in tops:
        tz = math.floor((base - 32) / 256) * 256
        if tz > terrain.floor_z + 256:
            q[(x0, y0)] = tz
    done = set()
    for (x0, y0), tz in sorted(q.items()):
        if (x0, y0) in done:
            continue
        # étendre en x puis en y tant que la hauteur est identique
        w = 1
        while (x0 + w * TILE, y0) in q and q[(x0 + w * TILE, y0)] == tz and (x0 + w * TILE, y0) not in done:
            w += 1
        h = 1
        while all((x0 + i * TILE, y0 + h * TILE) in q and q[(x0 + i * TILE, y0 + h * TILE)] == tz
                  and (x0 + i * TILE, y0 + h * TILE) not in done for i in range(w)):
            h += 1
        for i in range(w):
            for j in range(h):
                done.add((x0 + i * TILE, y0 + j * TILE))
        blk = vmf.make_prism(Vec(x0, y0, terrain.floor_z + dz), Vec(x0 + w * TILE, y0 + h * TILE, tz + dz), "tools/toolsnodraw")
        vmf.add_brush(blk.solid)
        n_block += 1
    return n_disp, n_block
