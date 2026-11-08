# Startet die Buchfuehrung per Doppelklick (Desktop-Verknuepfung, siehe install.ps1):
#   1. Backend unsichtbar im Hintergrund starten (liefert auch die App aus)
#   2. App in einem eigenen Fenster ohne Browserleiste oeffnen
#   3. Wird das Fenster geschlossen, wird auch das Backend beendet
# Laeuft das Backend schon (zweiter Doppelklick), wird nur ein Fenster geoeffnet.

$ErrorActionPreference = 'Stop'
$Port = 8765                     # bewusst nicht 8000, damit es nicht mit der Entwicklung kollidiert
$Url = "http://127.0.0.1:$Port"

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Backend = Join-Path $Root 'backend'
$WebDir = Join-Path $Root 'app\dist'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'
$State = Join-Path $env:LOCALAPPDATA 'Buchfuehrung'
New-Item -ItemType Directory -Force $State | Out-Null

function Show-Error([string]$text) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($text, 'Buchführung', 'OK', 'Error') | Out-Null
}

function Test-Backend {
    try { (Invoke-WebRequest "$Url/api/health" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 }
    catch { $false }
}

if (-not (Test-Path $Python) -or -not (Test-Path (Join-Path $WebDir 'index.html'))) {
    Show-Error "Die Buchführung ist noch nicht eingerichtet.`n`nBitte einmal desktop\windows\install.ps1 ausführen."
    exit 1
}

$server = $null
if (-not (Test-Backend)) {
    $env:BUCH_DATA_DIR = Join-Path $Backend 'data'   # Ablage wie beim Start aus dem Terminal
    $env:BUCH_WEB_DIR = $WebDir
    $server = Start-Process $Python -WorkingDirectory $Backend -WindowStyle Hidden -PassThru `
        -ArgumentList '-m', 'uvicorn', 'buchfuehrung.main:app', '--host', '127.0.0.1', '--port', $Port `
        -RedirectStandardOutput (Join-Path $State 'backend.log') `
        -RedirectStandardError (Join-Path $State 'backend-fehler.log')

    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Test-Backend)) {
        if ($server.HasExited -or (Get-Date) -gt $deadline) {
            if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
            Show-Error "Das Backend ist nicht gestartet.`n`nDetails: $State\backend-fehler.log"
            exit 1
        }
        Start-Sleep -Milliseconds 300
    }
}

# Eigenes App-Fenster mit Edge (gehoert zu Windows). Ein eigenes Profil sorgt dafuer, dass
# der Prozess genau so lange laeuft wie das Fenster und die App-Einstellungen erhalten bleiben.
$edge = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe' `
        -ErrorAction SilentlyContinue).'(default)'
if ($edge -and (Test-Path $edge)) {
    $profileDir = Join-Path $State 'fenster'
    $window = Start-Process $edge -PassThru -ArgumentList @(
        "--app=$Url", "--user-data-dir=`"$profileDir`"", '--no-first-run', '--no-default-browser-check',
        '--disable-features=msEdgeSidebarV2', '--start-maximized'
    )
    $window.WaitForExit()
    # Ein zweites Fenster derselben Sitzung endet sofort; dann laufen noch andere Fenster weiter.
    while (Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe'" |
            Where-Object { $_.CommandLine -like "*$profileDir*" }) {
        Start-Sleep -Seconds 2
    }
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}
else {
    # Ohne Edge: im Standardbrowser oeffnen. Das Backend laeuft dann weiter, bis Windows neu startet.
    Start-Process $Url
}
