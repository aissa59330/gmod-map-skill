# Compile rp_cw_triple_front (style Vexis) : vbsp -> vvis -> vrad -> contenu embarqué (bspzip) -> copie dans garrysmod\maps
# Même chaîne que rp_cw_arsenal_vexis : profil de compilation compile_game (mount.cfg des packs extraits),
# contenu des packs + LOD embarqués dans le .bsp (tools/embed_content.py), grosses textures réduites (tools/shrink_vtf.py).
# Usage : tools\compile.ps1 [-Fast] [-Final] [-Tag nom] [-NoCopy]
param([switch]$Final, [switch]$Fast, [switch]$NoCopy, [string]$Tag = "latest",
      [string]$GMod = "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Bin = Join-Path $GMod "bin\win64"
if (-not (Test-Path (Join-Path $Bin "vbsp.exe"))) { $Bin = Join-Path $GMod "bin" }
$GmodGame = Join-Path $GMod "garrysmod"
$Map = "rp_cw_triple_front"
$Src = Join-Path $Root "maps_src\$Map"
$Logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force $Logs | Out-Null
$Log = Join-Path $Logs "compile_$Tag.log"
"=== compile $Tag $(Get-Date -Format s) final=$Final fast=$Fast bin=$Bin" | Out-File $Log -Encoding utf8

# profil de compilation (dans le projet, rien n'est modifié dans Garry's Mod) : gameinfo + mount.cfg des packs extraits
$Prof = Join-Path $Root "compile_game"
New-Item -ItemType Directory -Force (Join-Path $Prof "cfg") | Out-Null
Copy-Item (Join-Path $GmodGame "gameinfo.txt") $Prof -Force
foreach ($rad in (Join-Path $GmodGame "lights.rad"), (Join-Path $GMod "bin\lights.rad")) {
    if (Test-Path $rad) { Copy-Item $rad $Prof -Force; break }
}
$mounts = @("`t`"garrysmod`"`t`"$GmodGame`"")
foreach ($line in Get-Content (Join-Path $PSScriptRoot "content_paths.txt")) {
    if (-not $line -or $line.StartsWith("#")) { continue }
    if (-not (Test-Path $line)) { Write-Host "Contenu introuvable : $line"; exit 4 }
    $mounts += "`t`"$(Split-Path $line -Leaf)`"`t`"$line`""
}
"`"mountcfg`"`r`n{`r`n$($mounts -join "`r`n")`r`n}" | Out-File (Join-Path $Prof "cfg\mount.cfg") -Encoding ascii
$Game = $Prof
if (-not (Test-Path (Join-Path $Prof "models\vxl"))) { Write-Host "LOD absents : copier gmod_arsenal_vexis\compile_game\models\vxl dans compile_game\models"; exit 4 }

function Run-Tool($exe, $toolArgs) {
    "`n>>> $exe $toolArgs" | Out-File $Log -Append -Encoding utf8
    $p = Start-Process -FilePath (Join-Path $Bin $exe) -ArgumentList $toolArgs -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput "$Log.tmp" -RedirectStandardError "$Log.err"
    Get-Content "$Log.tmp", "$Log.err" -ErrorAction SilentlyContinue | Out-File $Log -Append -Encoding utf8
    Remove-Item "$Log.tmp", "$Log.err" -ErrorAction SilentlyContinue
    return $p.ExitCode
}
Remove-Item "$Src.bsp", "$Src.lin", "$Src.prt" -ErrorAction SilentlyContinue
$rc = Run-Tool "vbsp.exe" "-game `"$Game`" `"$Src.vmf`""
if (Test-Path "$Src.lin") { Write-Host "LEAK detecte ($Src.lin) - voir $Log"; exit 2 }
if ($rc -ne 0 -or -not (Test-Path "$Src.bsp")) { Write-Host "vbsp a echoue (code $rc) - voir $Log"; exit 1 }
$vis = if ($Fast) { "-fast " } else { "" }
$rc = Run-Tool "vvis.exe" "$vis-game `"$Game`" `"$Src`""
if ($rc -ne 0) { Write-Host "vvis a echoue (code $rc)"; exit 1 }
$rad = if ($Final) { "-ldr -final -StaticPropLighting -StaticPropPolys" } elseif ($Fast) { "-fast -ldr -StaticPropLighting" } else { "-ldr -StaticPropLighting" }
$rc = Run-Tool "vrad.exe" "$rad -game `"$Game`" `"$Src`""
if ($rc -ne 0) { Write-Host "vrad a echoue (code $rc)"; exit 1 }
$unread = Select-String -Path $Log -Pattern "Unable to load file" | ForEach-Object { $_.Line.Trim() } | Select-Object -Unique
if ($unread) { Write-Host "ALERTE fichiers illisibles :"; $unread | ForEach-Object { Write-Host "  $_" } }

# contenu embarqué : LOD (compile_game\models\vxl) + tout ce que la map prend aux packs (tools/embed_content.py)
$Pack = Join-Path $Prof "pack_list.txt"
$lines = @()
$d = Join-Path $Prof "models\vxl"
# seulement les LOD vraiment utilisés par la map (pas les vaisseaux du ciel de Vexis)
$used = @{}
Select-String -Path "$Src.vmf" -Pattern '"models/vxl/([^"]+)\.mdl"' -AllMatches | ForEach-Object { $_.Matches } | ForEach-Object { $used[$_.Groups[1].Value.ToLower()] = 1 }
Get-ChildItem $d -Recurse -File | Where-Object { $used.ContainsKey(($_.Name -split '\.')[0].ToLower()) } | ForEach-Object {
    $lines += $_.FullName.Substring($Prof.Length + 1).Replace("\", "/")
    $lines += $_.FullName
}
& python (Join-Path $PSScriptRoot "embed_content.py") | Out-File $Log -Append -Encoding utf8
& python (Join-Path $PSScriptRoot "shrink_vtf.py") | Out-File $Log -Append -Encoding utf8
$Emb = "C:\gn_content\_tf"     # chemin court (limite des 260 caractères de bspzip)
if (Test-Path $Emb) {
    Get-ChildItem $Emb -Recurse -File | ForEach-Object {
        $lines += $_.FullName.Substring($Emb.Length + 1).Replace("\", "/")
        $lines += $_.FullName
    }
}
$lines | Out-File $Pack -Encoding ascii
$rc = Run-Tool "bspzip.exe" "-game `"$Game`" -addlist `"$Src.bsp`" `"$Pack`" `"$Src.packed.bsp`""
if ($rc -ne 0 -or -not (Test-Path "$Src.packed.bsp")) { Write-Host "bspzip a echoue (code $rc)"; exit 1 }
Move-Item "$Src.packed.bsp" "$Src.bsp" -Force
# contrôle : tout le contenu doit être DANS le .bsp (sinon textures violettes / modèles ERROR en jeu)
$inBsp = (& (Join-Path $Bin "bspzip.exe") -dir "$Src.bsp" | Select-String -Pattern "^(materials|models|sound)/").Count
$expected = $lines.Count / 2
"pack verifie : $inBsp / $expected" | Out-File $Log -Append -Encoding utf8
if ($inBsp -lt $expected) { Write-Host "ALERTE contenu incomplet dans le .bsp : $inBsp / $expected"; exit 5 }

Copy-Item "$Src.bsp" "$Src.$Tag.bsp" -Force
if (-not $NoCopy) { Copy-Item "$Src.bsp" (Join-Path $GmodGame "maps\$Map.bsp") -Force }
$size = [math]::Round((Get-Item "$Src.bsp").Length / 1MB, 1)
Write-Host "OK : $Map.bsp ($size Mo), contenu embarque $inBsp fichiers. Log : $Log"
exit 0
