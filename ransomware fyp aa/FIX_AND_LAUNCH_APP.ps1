$ErrorActionPreference = 'Stop'
$root = "C:\Users\Administrator\Desktop\ransomware fyp aa"
$frontend = Join-Path $root "my_fyp frontend"
$release = Join-Path $frontend "build\windows\x64\runner\Release"
$data = Join-Path $release "data"
$exe = Join-Path $release "my_fyp.exe"

Write-Host "Step 1: Building Windows app..."
Push-Location $frontend
flutter pub get | Out-Null
flutter build windows
$buildExit = $LASTEXITCODE
Pop-Location

Write-Host "Step 2: Copying app assets into Release/data..."
New-Item -ItemType Directory -Force -Path $data | Out-Null

$appSo = Join-Path $frontend "build\windows\app.so"
$assets = Join-Path $frontend "build\flutter_assets"

if (Test-Path $appSo) {
  Copy-Item -Force $appSo (Join-Path $data "app.so")
  Write-Host "  copied app.so"
} else {
  Write-Warning "app.so not found - build may have failed"
}

if (Test-Path $assets) {
  $destAssets = Join-Path $data "flutter_assets"
  if (Test-Path $destAssets) { Remove-Item -Recurse -Force $destAssets }
  Copy-Item -Recurse -Force $assets $destAssets
  Write-Host "  copied flutter_assets"
} else {
  Write-Warning "flutter_assets not found"
}

if (-not (Test-Path (Join-Path $data "icudtl.dat"))) {
  $icu = Get-ChildItem -Path (Join-Path $frontend "build") -Recurse -Filter "icudtl.dat" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($icu) {
    Copy-Item -Force $icu.FullName (Join-Path $data "icudtl.dat")
    Write-Host "  copied icudtl.dat"
  }
}

if (-not (Test-Path $exe)) {
  Write-Error "my_fyp.exe not found at $exe"
}

Write-Host "Step 3: Launching app..."
Start-Process -FilePath $exe -WorkingDirectory $release
Write-Host "Done."

if ($buildExit -ne 0) {
  Write-Host "Note: flutter build reported errors, but app files were copied if available."
}
