$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

if (-not $env:CODEX_HOME) {
    $env:CODEX_HOME = Join-Path $HOME ".codex"
}

$skillsDir = Join-Path $env:CODEX_HOME "skills"
$target = Join-Path $skillsDir "coderoblox"
$source = Join-Path $repoRoot "skills\\coderoblox"

New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null

if (Test-Path $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path $source '*') -Destination $target -Recurse -Force

Write-Host "Installed Codex skill at $target"
