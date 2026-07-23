param(
    [ValidateSet("validate", "all")]
    [string]$Stage = "all"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BasePython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creating the local Python environment..."
    if (Test-Path -LiteralPath $BasePython) {
        & $BasePython -m venv .venv
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        py -3.12 -m venv .venv
    }
    else {
        throw "Python 3.12 was not found. Install Python or set up .venv manually."
    }
}

& $VenvPython -c "import pandas, numpy, scipy, sklearn, skbio, statsmodels, matplotlib, seaborn, openpyxl" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing missing dependencies..."
    & $VenvPython -m pip install --disable-pip-version-check -r requirements.txt
}
else {
    Write-Host "Dependencies are ready."
}

$env:MPLBACKEND = "Agg"
$env:LOKY_MAX_CPU_COUNT = "8"

Write-Host "Validating the official workbook..."
& $VenvPython scripts\01_validate_and_prepare.py

if ($Stage -eq "all") {
    Write-Host "Running descriptive and multivariate analyses..."
    & $VenvPython scripts\02_run_analysis.py
}
