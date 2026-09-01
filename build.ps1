$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $Root '.venv')
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root 'requirements.txt')
& $Python -m unittest discover -s (Join-Path $Root 'tests') -v

Push-Location $Root
try {
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name FormatBridge `
        --version-file version_info.txt `
        --add-data 'formatbridge\office_bridge.ps1;formatbridge' `
        --collect-all py7zr `
        app.py
} finally {
    Pop-Location
}

Write-Output "Build complete: $Root\dist\FormatBridge.exe"
