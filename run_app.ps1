$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localVenvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
$parentVenvPython = Join-Path (Join-Path $projectDir "..") ".venv\Scripts\python.exe"
$appFile = Join-Path $projectDir "app.py"

if (Test-Path $localVenvPython) {
	$pythonExe = $localVenvPython
} elseif (Test-Path $parentVenvPython) {
	$pythonExe = $parentVenvPython
} else {
	Write-Error "Could not find a virtual environment Python executable in '.venv\\Scripts\\python.exe' (project or parent directory)."
	exit 1
}

& $pythonExe $appFile
