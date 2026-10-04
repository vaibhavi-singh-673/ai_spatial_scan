param(
    [ValidateSet("lidar", "photos", "video")]
    [string]$Tier = "lidar",
    [Parameter(Mandatory = $true)]
    [string]$InputPath,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [string]$GroundTruthPath
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Project virtual environment not found. Create it with: python -m venv .venv"
}

Push-Location $root
try {
    New-Item -ItemType Directory -Force $OutputDirectory | Out-Null
    $quality = Join-Path $OutputDirectory "quality.json"
    $prediction = Join-Path $OutputDirectory "prediction.json"
    & $python -m spatialscan quality --tier $Tier --input $InputPath --output $quality
    & $python -m spatialscan run --tier $Tier --input $InputPath --output $prediction
    if ($GroundTruthPath) {
        $evaluation = Join-Path $OutputDirectory "evaluation.json"
        & $python -m spatialscan evaluate --prediction $prediction --ground-truth $GroundTruthPath --output $evaluation
    }
    Write-Host "Cold capture artifacts written to $OutputDirectory"
}
finally {
    Pop-Location
}