$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectDir ".venv\Scripts\python.exe"
$appFile = Join-Path $projectDir "app.py"

& $pythonExe $appFile
