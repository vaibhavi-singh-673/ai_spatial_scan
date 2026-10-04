$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Project virtual environment not found. Create it with: python -m venv .venv"
}

Push-Location $root
try {
    & $python -m spatialscan run `
        --tier video `
        --input fixtures\video `
        --output runs\video_fixture.json
}
finally {
    Pop-Location
}