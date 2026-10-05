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
$timer = [System.Diagnostics.Stopwatch]::StartNew()
    & $python -m spatialscan quality --tier $Tier --input $InputPath --output $quality
    if ($LASTEXITCODE -ne 0) { throw "Capture readiness check failed with exit code $LASTEXITCODE" }
$qualitySeconds = $timer.Elapsed.TotalSeconds
$timer.Restart()
    & $python -m spatialscan run --tier $Tier --input $InputPath --output $prediction
    if ($LASTEXITCODE -ne 0) { throw "Capture processing failed with exit code $LASTEXITCODE" }
$processingSeconds = $timer.Elapsed.TotalSeconds
$timer.Stop()
    if ($GroundTruthPath) {
        $evaluation = Join-Path $OutputDirectory "evaluation.json"
        & $python -m spatialscan evaluate --prediction $prediction --ground-truth $GroundTruthPath --output $evaluation
        if ($LASTEXITCODE -ne 0) { throw "Ground-truth evaluation failed with exit code $LASTEXITCODE" }
    }
    $files = Get-ChildItem -LiteralPath $InputPath -File -Recurse -ErrorAction SilentlyContinue
    $pythonVersion = (& $python --version 2>&1 | Out-String).Trim()
    $record = [ordered]@{
        schema_version = "1.0"
        evidence_class = "COLD_REPRODUCTION_ONLY"
        tier = $Tier
        input_path = (Resolve-Path -LiteralPath $InputPath).Path
        input_file_count = @($files).Count
        input_bytes = [long](($files | Measure-Object -Property Length -Sum).Sum)
        python_version = $pythonVersion
        readiness_seconds = $qualitySeconds
        processing_seconds = $processingSeconds
        total_seconds = $qualitySeconds + $processingSeconds
        prediction_path = $prediction
        ground_truth_path = $GroundTruthPath
        recorded_at_utc = [DateTime]::UtcNow.ToString("o")
    }
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputDirectory "cold_run.json") -Encoding utf8
    Write-Host "Cold capture artifacts written to $OutputDirectory"
}
finally {
    Pop-Location
}
