# Richtet den Start per Doppelklick ein (einmalig und nach jedem Update erneut ausfuehren):
#   - Backend-Pakete installieren (inkl. PaddleOCR)
#   - Web-App bauen (app\dist)
#   - Symbol zeichnen und Verknuepfung "Buchführung" auf dem Desktop und im Startmenue anlegen
# Voraussetzungen: uv und Node.js.
# Aufruf: powershell -ExecutionPolicy Bypass -File desktop\windows\install.ps1

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$State = Join-Path $env:LOCALAPPDATA 'Buchfuehrung'
New-Item -ItemType Directory -Force $State | Out-Null

function Invoke-Step([string]$title, [scriptblock]$action) {
    Write-Host "== $title" -ForegroundColor Cyan
    & $action
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "$title fehlgeschlagen (Code $LASTEXITCODE)" }
}

Push-Location (Join-Path $Root 'backend')
try { Invoke-Step 'Backend-Pakete' { uv sync --extra paddle } } finally { Pop-Location }

Push-Location (Join-Path $Root 'app')
try {
    if (-not (Test-Path 'node_modules')) { Invoke-Step 'App-Pakete' { npm install } }
    Invoke-Step 'App bauen' { npm run build:web }
}
finally { Pop-Location }

$icon = Join-Path $State 'buchfuehrung.ico'
Invoke-Step 'Symbol' {
    & (Join-Path $Root 'backend\.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'make_icon.py') $icon
}

Invoke-Step 'Verknuepfungen' {
    $shell = New-Object -ComObject WScript.Shell
    $name = "Buchf$([char]0x00FC)hrung.lnk"
    $targets = @(
        [Environment]::GetFolderPath('Desktop'),
        (Join-Path ([Environment]::GetFolderPath('Programs')) '')
    )
    foreach ($dir in $targets) {
        $link = $shell.CreateShortcut((Join-Path $dir $name))
        $link.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $link.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $PSScriptRoot 'Buchfuehrung.ps1')`""
        $link.WorkingDirectory = $Root
        $link.IconLocation = $icon
        $link.Description = 'Monats-Buchführung öffnen'
        $link.WindowStyle = 7   # minimiert, damit kein Konsolenfenster aufblitzt
        $link.Save()
        Write-Host "   $($link.FullName)"
    }
}

Write-Host "`nFertig. Die Buchführung startet jetzt per Doppelklick auf das Symbol." -ForegroundColor Green
