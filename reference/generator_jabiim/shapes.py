"""Formes non cubiques (brushes convexes définis par leurs plans) : cylindres, cônes, dômes, murs circulaires,
voûtes, pièces de coque inclinées. Toute forme peut être tournée (lacet / tangage / roulis) puis déplacée.
"""
import math
from itertools import combinations

from srctools import Vec

from geom import Poly

GRID = 1.0


def _verts(planes):
    """Sommets d'un polyèdre convexe donné par (point, normale sortante)."""
    pl = [(n.norm(), n.norm().dot(p)) for p, n in planes]
    out = []
    for (n1, d1), (n2, d2), (n3, d3) in combinations(pl, 3):
        c = n2.cross(n3)
        det = n1.dot(c)
        if abs(det) < 1e-6:
            continue
        p = (c * d1 + n3.cross(n1) * d2 + n1.cross(n2) * d3) / det
        if all(n.dot(p) <= d + 0.05 for n, d in pl):
            out.append(p)
    return out


def bbox_of(planes):
    vs = _verts(planes)
    if not vs:
        raise ValueError("polyèdre vide")
    xs, ys, zs = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def mk(planes, mat, kind="detail", top=None):
    return Poly(planes, mat, kind, bbox_of(planes), top)


# ---------------- rotations ----------------
def rot(v, yaw=0.0, pitch=0.0, roll=0.0):
    """Roulis autour de X, puis tangage autour de Y, puis lacet autour de Z (degrés)."""
    x, y, z = v.x, v.y, v.z
    if roll:
        a = math.radians(roll); c, s = math.cos(a), math.sin(a)
        y, z = y * c - z * s, y * s + z * c
    if pitch:
        a = math.radians(pitch); c, s = math.cos(a), math.sin(a)
        x, z = x * c + z * s, -x * s + z * c
    if yaw:
        a = math.radians(yaw); c, s = math.cos(a), math.sin(a)
        x, y = x * c - y * s, x * s + y * c
    return Vec(x, y, z)


def xform(planes, origin=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0):
    o = Vec(*origin)
    return [(rot(p, yaw, pitch, roll) + o, rot(n, yaw, pitch, roll)) for p, n in planes]


# ---------------- primitives locales ----------------
def box_planes(x0, y0, z0, x1, y1, z1):
    return [(Vec(x0, y0, z1), Vec(0, 0, 1)), (Vec(x0, y0, z0), Vec(0, 0, -1)),
            (Vec(x0, y0, z0), Vec(-1, 0, 0)), (Vec(x1, y0, z0), Vec(1, 0, 0)),
            (Vec(x0, y0, z0), Vec(0, -1, 0)), (Vec(x0, y1, z0), Vec(0, 1, 0))]


def prism_planes(pts2d, z0, z1):
    """Prisme droit sur un polygone convexe (sens trigonométrique)."""
    pl = [(Vec(pts2d[0][0], pts2d[0][1], z1), Vec(0, 0, 1)), (Vec(pts2d[0][0], pts2d[0][1], z0), Vec(0, 0, -1))]
    n = len(pts2d)
    for i in range(n):
        ax, ay = pts2d[i]; bx, by = pts2d[(i + 1) % n]
        nx, ny = by - ay, -(bx - ax)
        L = math.hypot(nx, ny)
        pl.append((Vec(ax, ay, z0), Vec(nx / L, ny / L, 0)))
    return pl


def frustum_round_planes(r0, r1, z0, z1, sides=16, phase=0.0):
    """Tronc de cône à `sides` faces : rayon (apothème) r0 en bas, r1 en haut. Centré en (0, 0)."""
    pl = [(Vec(0, 0, z1), Vec(0, 0, 1)), (Vec(0, 0, z0), Vec(0, 0, -1))]
    h = z1 - z0
    for k in range(sides):
        a = math.radians(phase + 360.0 * k / sides)
        cx, cy = math.cos(a), math.sin(a)
        n = Vec(cx * h, cy * h, (r0 - r1)).norm()
        pl.append((Vec(cx * r0, cy * r0, z0), n))
    return pl


def ring_seg_planes(r_in, r_out, a0, a1, z0, z1):
    """Secteur d'anneau (morceau de mur circulaire) entre les angles a0 et a1 (degrés, a1 - a0 <= 45)."""
    am = math.radians((a0 + a1) / 2)
    r0, r1 = math.radians(a0), math.radians(a1)
    pl = [(Vec(0, 0, z1), Vec(0, 0, 1)), (Vec(0, 0, z0), Vec(0, 0, -1))]
    # face extérieure (corde) et intérieure
    pl.append((Vec(math.cos(am) * r_out, math.sin(am) * r_out, z0), Vec(math.cos(am), math.sin(am), 0)))
    rin = r_in * math.cos((r1 - r0) / 2)   # corde intérieure passant par les extrémités
    pl.append((Vec(math.cos(am) * rin, math.sin(am) * rin, z0), Vec(-math.cos(am), -math.sin(am), 0)))
    # côtés radiaux
    pl.append((Vec(0, 0, z0), Vec(math.sin(r0), -math.cos(r0), 0)))
    pl.append((Vec(0, 0, z0), Vec(-math.sin(r1), math.cos(r1), 0)))
    return pl


# ---------------- formes monde ----------------
def cylinder(cx, cy, r, z0, z1, mat, kind="detail", sides=16, top=None):
    return mk(xform(frustum_round_planes(r, r, z0, z1, sides), (cx, cy, 0)), mat, kind, top)


def cone(cx, cy, r0, r1, z0, z1, mat, kind="detail", sides=16, top=None):
    return mk(xform(frustum_round_planes(r0, r1, z0, z1, sides), (cx, cy, 0)), mat, kind, top)


def dome(cx, cy, r, z0, mat, kind="detail", rings=4, sides=16, squash=1.0):
    """Dôme plein (calotte) en tranches de troncs de cône."""
    out = []
    for i in range(rings):
        a0 = math.pi / 2 * i / rings; a1 = math.pi / 2 * (i + 1) / rings
        ra, rb = r * math.cos(a0), max(r * math.cos(a1), 24)
        za, zb = z0 + r * squash * math.sin(a0), z0 + r * squash * math.sin(a1)
        out.append(cone(cx, cy, ra, rb, round(za), round(zb), mat, kind, sides))
    return out


def ring_wall(cx, cy, r, thick, z0, z1, mat, kind="detail", segs=16, gaps=(), gap_h=None, phase=0.0):
    """Mur circulaire en `segs` morceaux. gaps = indices des morceaux ouverts (portes) ;
    gap_h = hauteur de la porte (au-dessus : linteau) ou None = ouvert sur toute la hauteur."""
    out = []
    step = 360.0 / segs
    for k in range(segs):
        a0, a1 = phase + k * step, phase + (k + 1) * step
        if k in gaps:
            if gap_h is None or z0 + gap_h >= z1 - 8:
                continue
            out.append(mk(xform(ring_seg_planes(r - thick, r, a0, a1, z0 + gap_h, z1), (cx, cy, 0)), mat, kind))
            continue
        out.append(mk(xform(ring_seg_planes(r - thick, r, a0, a1, z0, z1), (cx, cy, 0)), mat, kind))
    return out


def disc(cx, cy, r, z0, z1, mat, kind="detail", sides=16, top=None):
    return cylinder(cx, cy, r, z0, z1, mat, kind, sides, top)


def obox(cx, cy, z0, length, width, height, yaw, mat, kind="detail", pitch=0.0, roll=0.0, top=None):
    """Boîte orientée centrée en (cx, cy), base à z0 (avant rotation de tangage/roulis autour de sa base)."""
    pl = box_planes(-length / 2, -width / 2, 0, length / 2, width / 2, height)
    return mk(xform(pl, (cx, cy, z0), yaw, pitch, roll), mat, kind, top)


def vault(cx, cy, z0, length, span, wall_h, rise, yaw, mat, roof_mat, kind="detail", segs=8, thick=32):
    """Hangar voûté : deux murs latéraux + voûte en berceau (morceaux inclinés). Bouts ouverts.
    Axe long = direction yaw."""
    out = []
    hw = span / 2
    for side in (-1, 1):
        out.append(mk(xform(box_planes(-length / 2, side * hw - (thick if side > 0 else 0), 0,
                                       length / 2, side * hw + (0 if side > 0 else thick), wall_h), (cx, cy, z0), yaw),
                      mat, kind))
    # voûte : arc de cercle passant par (±hw, wall_h) et (0, wall_h + rise)
    R = (hw * hw + rise * rise) / (2 * rise)
    zc = wall_h + rise - R
    a_end = math.asin(hw / R)
    for k in range(segs):
        t0 = -a_end + 2 * a_end * k / segs
        t1 = -a_end + 2 * a_end * (k + 1) / segs
        p0 = (R * math.sin(t0), zc + R * math.cos(t0))
        p1 = (R * math.sin(t1), zc + R * math.cos(t1))
        tm = (t0 + t1) / 2
        nout = (math.sin(tm), math.cos(tm))
        # plaque entre p0 et p1, épaisseur thick vers l'extérieur, longueur `length`
        pl = [(Vec(-length / 2, 0, 0), Vec(-1, 0, 0)), (Vec(length / 2, 0, 0), Vec(1, 0, 0))]
        pl.append((Vec(0, p0[0] + nout[0] * thick, p0[1] + nout[1] * thick), Vec(0, nout[0], nout[1])))
        pl.append((Vec(0, p0[0], p0[1]), Vec(0, -nout[0], -nout[1])))
        # bords radiaux
        e0 = (math.cos(t0), -math.sin(t0)); e1 = (math.cos(t1), -math.sin(t1))
        pl.append((Vec(0, p0[0], p0[1]), Vec(0, -e0[0], -e0[1])))
        pl.append((Vec(0, p1[0], p1[1]), Vec(0, e1[0], e1[1])))
        out.append(mk(xform(pl, (cx, cy, z0), yaw), roof_mat, kind))
    return out


def hull_piece(pts, mat, kind="detail", origin=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0):
    """Pièce convexe définie par ses sommets locaux (<= 16) : enveloppe convexe par force brute."""
    P = [Vec(*p) for p in pts]
    planes = []
    seen = []
    cen = sum(P, Vec()) / len(P)
    for a, b, c in combinations(P, 3):
        n = (b - a).cross(c - a)
        if n.mag() < 1e-3:
            continue
        n = n.norm()
        d = n.dot(a)
        sides = [n.dot(p) - d for p in P]
        if all(s <= 0.5 for s in sides):
            pass
        elif all(s >= -0.5 for s in sides):
            n, d = -n, -d
        else:
            continue
        if any((n - m).mag() < 1e-4 and abs(d - e) < 0.5 for m, e in seen):
            continue
        seen.append((n, d))
        planes.append((a, n))
    return mk(xform(planes, origin, yaw, pitch, roll), mat, kind)
