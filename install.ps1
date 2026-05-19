$ErrorActionPreference = "Stop"

$env:UV_CACHE_DIR = ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = ".uv-python"
$env:UV_PROJECT_ENVIRONMENT = ".venv-game-py313"

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host ""
    Write-Host "uv is required to install this game, but it was not found on PATH." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Install uv first, then run this script again:"
    Write-Host "  https://docs.astral.sh/uv/getting-started/installation/"
    Write-Host ""
    Write-Host "After installing uv, open a new PowerShell window and run:"
    Write-Host "  .\install.ps1"
    Write-Host ""
    exit 1
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($Arguments -join ' ')"
    }
}

Push-Location $PSScriptRoot
try {
    $python = Join-Path $PSScriptRoot ".venv-game-py313\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        Write-Host "Creating local Python 3.13 environment with uv..."
        Invoke-Step "uv" "venv" "--managed-python" "--python" "3.13" ".venv-game-py313"
    } else {
        Write-Host "Using existing local environment: .venv-game-py313"
    }

    if (-not (Test-Path $python)) {
        throw "Expected Python executable was not created: $python"
    }

    Write-Host "Installing project dependencies..."
    Invoke-Step "uv" "pip" "install" "--python" $python "pygame>=2.6.1"

    Write-Host ""
    Write-Host "Install complete." -ForegroundColor Green
    Write-Host "Run the game with:"
    Write-Host "  .\run_game.ps1"
    Write-Host ""
} finally {
    Pop-Location
}
