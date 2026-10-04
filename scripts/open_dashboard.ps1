$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$port = 8765
$server = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $server) {
	if (-not (Test-Path $python)) {
		throw "Project virtual environment not found. Create it with: python -m venv .venv"
	}
	Start-Process -FilePath $python -ArgumentList "-m", "http.server", $port, "--directory", $root -WorkingDirectory $root
}
Start-Process "http://127.0.0.1:$port/web/index.html"