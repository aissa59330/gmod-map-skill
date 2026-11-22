# Photos automatiques en jeu (addon local jb_photos, retiré à la fin). Lance Gmod en solo fenêtré, attend data/jb_photos/done.txt,
# copie les JPG dans shots\<Tag>, ferme UNIQUEMENT le Gmod lancé ici. Usage : tools\photos_jeu.ps1 -Tag v19b
param([string]$Tag = "latest", [int]$Timeout = 600)
$ErrorActionPreference = "Stop"
$Map = "rp_cw_battle_of_jabiim"
$Root = Split-Path -Parent $PSScriptRoot
$G = "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
$exe = "$G\bin\win64\gmod.exe"
$Out = Join-Path $Root "shots\$Tag"
New-Item -ItemType Directory -Force $Out | Out-Null
Copy-Item (Join-Path $Root "maps_src\$Map.bsp") "$G\garrysmod\maps\$Map.bsp" -Force
$addon = "$G\garrysmod\addons\jb_photos"
if (Test-Path $addon) { Remove-Item $addon -Recurse -Force }
Copy-Item (Join-Path $Root "addons\jb_photos") $addon -Recurse
$data = "$G\garrysmod\data\jb_photos"
if (Test-Path $data) { Remove-Item $data -Recurse -Force }
$p = Start-Process -FilePath $exe -ArgumentList "-windowed -w 1600 -h 900 -novid +maxplayers 1 +map $Map" -WorkingDirectory "$G\bin\win64" -PassThru
Write-Host "Gmod lance (PID $($p.Id))"
try {
    $deadline = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $deadline -and -not $p.HasExited) {
        Start-Sleep -Seconds 5
        if (Test-Path "$data\done.txt") { break }
    }
} finally {
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }      # uniquement le Gmod lancé ici
    Start-Sleep -Seconds 3
    if (Test-Path $data) { Copy-Item "$data\*.jpg" $Out -Force; Remove-Item $data -Recurse -Force }
    if (Test-Path $addon) { Remove-Item $addon -Recurse -Force }
}
(Get-ChildItem $Out -Filter "int_*.jpg").Count
