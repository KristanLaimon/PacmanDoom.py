$ErrorActionPreference = "Stop"

$env:UV_CACHE_DIR = ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = ".uv-python"
$env:UV_PROJECT_ENVIRONMENT = ".venv-game-py313"

function Test-PygamePython {
    param([string]$PythonPath)

    if (-not (Test-Path $PythonPath)) {
        return $false
    }

    & $PythonPath -c "import pygame" *> $null
    return $LASTEXITCODE -eq 0
}

$pythonCandidates = @(
    (Join-Path $PSScriptRoot ".venv-game-py313\Scripts\python.exe"),
    (Join-Path $PSScriptRoot ".venv-game\Scripts\python.exe"),
    (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")
)

$python = $pythonCandidates | Where-Object { Test-PygamePython $_ } | Select-Object -First 1

if (-not $python) {
    uv venv --managed-python --python 3.13 .venv-game-py313
    $python = Join-Path $PSScriptRoot ".venv-game-py313\Scripts\python.exe"
    uv pip install --python $python pygame
}

& $python -m doom_search
