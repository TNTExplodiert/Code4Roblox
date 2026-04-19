$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

$env:CODEROBLOX_ROOT = $repoRoot

if (-not $env:CODEX_HOME) {
    $env:CODEX_HOME = Join-Path $HOME ".codex"
}

$codexBin = Join-Path $env:CODEX_HOME "bin"
if ((Test-Path $codexBin) -and -not (($env:PATH -split ';') -contains $codexBin)) {
    $env:PATH = "$codexBin;$env:PATH"
}

Write-Host "CODEROBLOX_ROOT=$env:CODEROBLOX_ROOT"
Write-Host "CODEX_HOME=$env:CODEX_HOME"
