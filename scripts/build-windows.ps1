# build-windows.ps1 — Construye Gestor_biblioteca.exe
$ErrorActionPreference = "Stop"

$popplerUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
$popplerZip = "$env:TEMP\poppler.zip"
$popplerDir = "$env:TEMP\poppler"

if (-not (Test-Path "$popplerDir\pdftoppm.exe")) {
    Write-Output "Descargando poppler..."
    Invoke-WebRequest -Uri $popplerUrl -OutFile $popplerZip
    Expand-Archive -Path $popplerZip -DestinationPath $popplerDir -Force
}

$pdftoppm = Get-ChildItem -Path $popplerDir -Recurse -Filter "pdftoppm.exe" | Select-Object -First 1 -ExpandProperty FullName
Write-Output "pdftoppm en: $pdftoppm"

pyinstaller build.spec `
    --add-binary "$pdftoppm;." `
    --collect-all sv_ttk `
    --distpath dist `
    --workpath build `
    --onefile

Write-Output "Build completado: dist/Gestor_biblioteca.exe"
