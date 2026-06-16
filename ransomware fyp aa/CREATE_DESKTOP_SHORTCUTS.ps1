$projectRoot = "C:\Users\Administrator\Desktop\ransomware fyp aa"
$exe = Join-Path $projectRoot "my_fyp frontend\build\windows\x64\runner\Release\my_fyp.exe"
$releaseDir = Split-Path $exe -Parent
$backendBat = Join-Path $projectRoot "START_BACKEND.bat"
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell

if (-not (Test-Path $exe)) {
  Write-Error "App exe not found. Run BUILD_WINDOWS_APP.bat first."
  exit 1
}

function New-Shortcut($name, $target, $workDir, $args = '') {
  $lnk = Join-Path $desktop "$name.lnk"
  $sc = $shell.CreateShortcut($lnk)
  $sc.TargetPath = $target
  $sc.WorkingDirectory = $workDir
  if ($args) { $sc.Arguments = $args }
  $sc.Save()
  Write-Host "OK: $lnk"
}

# Direct exe shortcut (double-click opens app)
New-Shortcut 'Ransomware App' $exe $releaseDir

# Backend shortcut
New-Shortcut 'Start Backend' $backendBat (Join-Path $projectRoot 'Ransomware FYP backend')

Write-Host "Done. Double-click 'Ransomware App' on Desktop."
