# Mesurer (avant / après, toujours)

- **FPS client** (avec l'utilisateur) : `sv_cheats 1`, `net_graph 1`, `fps_max 0`, mêmes points `setpos x y z; setang p y r`
  à chaque fois (spawn, en l'air dehors, chaque grande salle, pendant les effets lourds) ; noter FPS normal et minimum.
- **Serveur** : bench sur **serveur dédié local** (méthode complète : `reference/tools/bench_server.ps1` +
  `reference/addons/givre_noir_srvbench/`) : SteamCMD app 4020 dans un dossier à chemin court, `+sv_hibernate_think 1`,
  1 bot (ou 100) + PNJ par paliers 0/200/400/600, 60 s par palier ; CPU mesuré de l'extérieur
  (TotalProcessorTime toutes les 5 s → ms CPU par tick ; `engine.ServerFrameTime` renvoie 0 en dédié) ; intervalle de tick
  max (> 50 ms = freeze ; ~30 ms = normal sous Windows) ; ticks ratés.
- Conditions : **rien d'autre de lourd sur le PC** (une compilation en parallèle crée de faux freezes de 200–700 ms),
  fenêtre du serveur **réduite** (un clic dedans le met en pause), une seule différence entre les deux versions,
  garder une copie de chaque .bsp testé et installer celle qui gagne.
- Après une compilation interrompue, vérifier qu'aucun `vbsp/vvis/vrad/srcds` ne tourne encore (ils mangent le CPU et
  les FPS du joueur jusqu'au redémarrage) ; ne tuer que ceux lancés par nos outils.
- Côté event : la limite vient du **nombre de PNJ vivants en même temps**, pas de la map. Conseiller aux staffs de trouver
  leur seuil sur leur serveur (seul, paliers 300/400/500 : ping stable, `net_graph 4` « sv » proche du tickrate, loss/choke 0),
  de garder ~30 % de marge pour les joueurs (souvent 200 PNJ max) et de faire apparaître les droïdes par vagues par zone.
  Un ping qui grimpe en solo sur le serveur dédié = serveur surchargé (pas le réseau).

Méthode détaillée du bench serveur : `METHODE_BENCH_SERVEUR.md`. Outils : `tools/bench.ps1`, `tools/bench_server.ps1`, addons `givre_noir_bench`, `givre_noir_srvbench`, `jb_fps` (FPS client par point de vue).
