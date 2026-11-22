# Contrôle des trous de collision (addon jb_check) sur le SERVEUR DÉDIÉ local, fenêtre réduite (ne pas cliquer dedans).
# Usage : tools\check_server.ps1 -Tag v19b   -> logs\check_<Tag>\result.txt
param([string]$Tag = "latest", [string]$Srv = "C:\gn_srcds", [int]$Timeout = 900)
$ErrorActionPreference = "Stop"
$Map = "rp_cw_battle_of_jabiim"
$AddonName = "jb_check"
$Root = Split-Path -Parent $PSScriptRoot
$Game = Join-Path $Srv "server"
$Out = Join-Path $Root "logs\check_$Tag"
New-Item -ItemType Directory -Force $Out | Out-Null
$exe = if (Test-Path (Join-Path $Game "srcds_win64.exe")) { Join-Path $Game "srcds_win64.exe" } else { Join-Path $Game "srcds.exe" }
$cfg = Join-Path $Game "garrysmod\cfg"; $mountCfg = Join-Path $cfg "mount.cfg"; $mountBak = Join-Path $cfg "mount.cfg.check_bak"
if ((Test-Path $mountCfg) -and -not (Test-Path $mountBak)) { Copy-Item $mountCfg $mountBak }
$mounts = @()
foreach ($line in (Get-Content (Join-Path $PSScriptRoot "content_paths.txt"))) {
    if ($line -and -not $line.StartsWith("#")) { $mounts += "`t`"$(Split-Path $line -Leaf)`"`t`"$line`"" }
}
"`"mountcfg`"`r`n{`r`n$($mounts -join "`r`n")`r`n}" | Out-File $mountCfg -Encoding ascii
Copy-Item (Join-Path $Root "maps_src\$Map.bsp") (Join-Path $Game "garrysmod\maps\$Map.bsp") -Force
$addon = Join-Path $Game "garrysmod\addons\$AddonName"
if (Test-Path $addon) { Remove-Item $addon -Recurse -Force }
Copy-Item (Join-Path $Root "addons\$AddonName") $addon -Recurse
$data = Join-Path $Game "garrysmod\data\$AddonName"
if (Test-Path $data) { Remove-Item $data -Recurse -Force }
$p = Start-Process -FilePath $exe -ArgumentList "-console -condebug -game garrysmod -norestart +sv_lan 1 +sv_hibernate_think 1 +maxplayers 2 +map $Map" -WorkingDirectory $Game -WindowStyle Minimized -PassThru
Write-Host "Serveur de controle lance (PID $($p.Id)), fenetre reduite"
try {
    $deadline = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $deadline -and -not $p.HasExited) {
        Start-Sleep -Seconds 5
        if (Test-Path (Join-Path $data "result.txt")) { Start-Sleep -Seconds 3; break }
    }
} finally {
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }      # uniquement le srcds lancé ici
    Start-Sleep -Seconds 2
    if (Test-Path $data) { Copy-Item (Join-Path $data "*") $Out -Force }
    if (Test-Path $addon) { Remove-Item $addon -Recurse -Force }
    if (Test-Path $mountBak) { Move-Item $mountBak $mountCfg -Force }
}
if (Test-Path (Join-Path $Out "result.txt")) { Get-Content (Join-Path $Out "result.txt") -TotalCount 1 } else { Write-Host "pas de resultat" }
