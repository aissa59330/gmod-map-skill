"""Monde vivant (sans Lua, sans dégâts) : fumées, feux, étincelles, lumières qui clignotent, artillerie lointaine,
avions qui passent, bruits de bataille aléatoires, ambiance sonore propre à chaque secteur.

Les autres modules marquent les endroits qui ont une raison d'être animés (épave -> feu, éboulis -> fumée,
relais -> étincelles, checkpoint -> néon qui grésille) avec mark() ; apply() crée les entités en fin de secteur.
Budget FPS par secteur (plafonds) : 5 fumées, 6 feux, 3 étincelles, 6 lumières clignotantes, 8 points d'artillerie.
Aucune light_dynamic : les clignotements sont des styles de lumière précalculés.
Sons : uniquement ceux des VPK de HL2 / Garry's Mod (vérifiés).
"""
from kit import RNG

CAP = {"smoke": 5, "fire": 6, "spark": 3, "flicker": 6}
BEDS = {   # ambiance de fond par secteur (boucles, rayon limité au secteur)
    "urbain": ["ambient/wind/wind_rooftop1.wav", "ambient/alarms/city_siren_loop2.wav"],
    "rural": ["ambient/wind/wind_med1.wav"],
    "separatiste": ["ambient/wind/wasteland_wind.wav", "ambient/levels/citadel/citadel_drone_loop2.wav"],
}
SHOTS = {  # bruits de combat lointains joués au hasard
    "urbain": [f"ambient/levels/streetwar/city_battle{i}.wav" for i in (1, 3, 5, 7, 9, 11, 13, 15)],
    "rural": [f"ambient/levels/streetwar/city_battle{i}.wav" for i in (2, 6, 10, 14)] + ["ambient/machines/aircraft_distant_flyby1.wav",
                                                                                      "ambient/machines/aircraft_distant_flyby3.wav"],
    "separatiste": [f"ambient/levels/streetwar/city_battle{i}.wav" for i in (4, 8, 12, 16)] + ["ambient/machines/aircraft_distant_flyby1.wav",
                                                                                            "ambient/alarms/apc_alarm_pass1.wav"],
}
STATS = {}


def mark(c, kind, x, y, z=16):
    lst = c.__dict__.setdefault("life", [])
    lst.append((kind, x, y, z))


def apply(c, tag, rect):
    """Crée les entités d'ambiance du secteur `tag` (rect = x0, y0, x1, y1 de la zone jouable)."""
    w = c.w
    pts = c.__dict__.get("life", [])
    used = {k: 0 for k in CAP}
    for kind, x, y, z in RNG.sample(pts, len(pts)):
        if used[kind] >= CAP[kind]:
            continue
        used[kind] += 1
        n = f"{tag}_{kind}_{used[kind]}"
        if kind == "smoke":
            w.ent("env_smokestack", (x, y, z), InitialState=1, BaseSpread=40, SpreadSpeed=30, Speed=90, StartSize=60,
                  EndSize=220, Rate=10, JetLength=700, WindAngle=35, WindSpeed=50, SmokeMaterial="particle/SmokeStack.vmt",
                  rendercolor="70 66 62", renderamt=170, roll=10)
        elif kind == "fire":
            w.ent("env_fire", (x, y, z), health=0, firesize=96, fireattack=1, firetype=0,
                  spawnflags=1 + 2 + 4 + 16 + 128, damagescale=0, ignitionpoint=0)
            w.ent("ambient_generic", (x, y, z + 32), message="ambient/fire/fire_small_loop1.wav", health=6, radius=700,
                  spawnflags=0, pitch=100, pitchstart=100)
        elif kind == "spark":
            w.ent("env_spark", (x, y, z), targetname=n, MaxDelay=4, Magnitude=2, TrailLength=1, spawnflags=64 + 128 + 256)
            w.ent("ambient_generic", (x, y, z), message="ambient/energy/spark3.wav", health=5, radius=900, spawnflags=16 + 32,
                  targetname=n + "_snd", pitch=100, pitchstart=100)
            w.ent("logic_timer", (x, y, z + 32), UseRandomTime=1, LowerRandomBound=1.5, UpperRandomBound=6,
                  outputs=[("OnTimer", n, "SparkOnce", "", 0, -1), ("OnTimer", n + "_snd", "PlaySound", "", 0, -1)])
        elif kind == "flicker":                    # néon / projecteur abîmé : style 10 (fluo qui grésille), précalculé
            w.ent("light", (x, y, z), _light="255 214 170 110", style=RNG.choice([1, 6, 10]))
    # artillerie lointaine : impacts contre les falaises du bord nord / sud, hors des zones de combat
    x0, y0, x1, y1 = rect
    case = f"{tag}_artillerie"
    outs = []
    for i in range(8):
        x = RNG.uniform(x0 + 2000, x1 - 2000)
        y = (y0 + 300) if i % 2 else (y1 - 300)
        nm = f"{tag}_art_{i}"
        w.ent("env_explosion", (x, y, 260), targetname=nm, iMagnitude=0, iRadiusOverride=1, spawnflags=1 + 4 + 64 + 2048,
              fireballsprite="sprites/zerogxplode.spr", rendermode=5)
        w.ent("env_shake", (x, y, 260), targetname=nm, amplitude=2, radius=3200, duration=1.2, frequency=60, spawnflags=4 + 8)
        w.ent("ambient_generic", (x, y, 320), targetname=nm + "_snd", message=f"ambient/explosions/explode_{1 + i % 9}.wav",
              health=10, radius=9000, spawnflags=16 + 32, pitch=85, pitchstart=85)
        k = f"OnCase{i + 1:02d}"
        outs += [(k, nm, "Explode", "", 0, -1), (k, nm, "StartShake", "", 0, -1), (k, nm + "_snd", "PlaySound", "", 0, -1)]
    w.ent("logic_case", ((x0 + x1) / 2, 0, 1200), targetname=case, outputs=outs)
    w.ent("logic_timer", ((x0 + x1) / 2, 64, 1200), UseRandomTime=1, LowerRandomBound=9, UpperRandomBound=22,
          outputs=[("OnTimer", case, "PickRandomShuffle", "", 0, -1)])
    # bruits de combat lointains (un au hasard toutes les 5 à 14 s), joués depuis des points du secteur
    sc = f"{tag}_combat"
    outs = []
    for i, snd in enumerate(SHOTS[tag][:16]):
        nm = f"{tag}_shot_{i}"
        w.ent("ambient_generic", (RNG.uniform(x0, x1), RNG.choice([y0 + 600, y1 - 600]), 900), targetname=nm, message=snd,
              health=7, radius=14000, spawnflags=16 + 32, pitch=100, pitchstart=100)
        outs.append((f"OnCase{i + 1:02d}", nm, "PlaySound", "", 0, -1))
    w.ent("logic_case", ((x0 + x1) / 2, 128, 1200), targetname=sc, outputs=outs)
    w.ent("logic_timer", ((x0 + x1) / 2, 192, 1200), UseRandomTime=1, LowerRandomBound=5, UpperRandomBound=14,
          outputs=[("OnTimer", sc, "PickRandomShuffle", "", 0, -1)])
    # ambiance de fond : boucles réparties dans le secteur, rayon limité (on n'entend pas les autres secteurs)
    for i, snd in enumerate(BEDS[tag]):
        for k in range(3):
            w.ent("ambient_generic", (x0 + (x1 - x0) * (k + 0.5) / 3, 0, 700), message=snd, health=3 if i else 4,
                  radius=7000, spawnflags=0, pitch=100, pitchstart=100)
    STATS[tag] = dict(used, artillerie=8)
