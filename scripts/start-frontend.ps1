$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot 'frontend')
try {
    if (!(Test-Path 'node_modules')) { throw 'Run npm.cmd ci in frontend first; see docs/SETUP.md.' }
    & npm.cmd run dev
    if ($LASTEXITCODE -ne 0) { throw 'Frontend exited with an error.' }
} finally { Pop-Location }
