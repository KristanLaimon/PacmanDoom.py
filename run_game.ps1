$ErrorActionPreference = "Stop"

$env:UV_CACHE_DIR = ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = ".uv-python"
$env:UV_PROJECT_ENVIRONMENT = ".venv-game"

uv run --managed-python python pacman_search.py
