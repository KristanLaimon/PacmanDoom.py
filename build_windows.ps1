$ErrorActionPreference = "Stop"

$env:UV_CACHE_DIR = ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = ".uv-python"
$env:UV_PROJECT_ENVIRONMENT = ".venv-game-py313"

$appName = "Pycman"
$python = Join-Path $PSScriptRoot ".venv-game-py313\Scripts\python.exe"
$buildRoot = Join-Path $PSScriptRoot "build"
$workPath = Join-Path $buildRoot "pyinstaller-work"
$assetsPath = Join-Path $PSScriptRoot "assets"
$entryPoint = Join-Path $PSScriptRoot "pycman\__main__.py"
$exePath = Join-Path $buildRoot "$appName\$appName.exe"

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

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host ""
    Write-Host "uv is required to build this project, but it was not found on PATH." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Install uv first, then run this script again:"
    Write-Host "  https://docs.astral.sh/uv/getting-started/installation/"
    Write-Host ""
    exit 1
}

Push-Location $PSScriptRoot
try {
    if (-not (Test-Path $python)) {
        Write-Host "Creating local Python 3.13 environment with uv..."
        Invoke-Step "uv" "venv" "--managed-python" "--python" "3.13" ".venv-game-py313"
    } else {
        Write-Host "Using existing local environment: .venv-game-py313"
    }

    if (-not (Test-Path $python)) {
        throw "Expected Python executable was not created: $python"
    }

    Write-Host "Installing build dependencies..."
    Invoke-Step "uv" "pip" "install" "--python" $python "pygame>=2.6.1" "pyinstaller>=6.0"

    New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null

    Write-Host "Building standalone Windows app..."
    Invoke-Step $python "-m" "PyInstaller" `
        "--noconfirm" `
        "--clean" `
        "--windowed" `
        "--name" $appName `
        "--distpath" $buildRoot `
        "--workpath" $workPath `
        "--specpath" $buildRoot `
        "--paths" $PSScriptRoot `
        "--add-data" "$assetsPath;assets" `
        $entryPoint

    if (-not (Test-Path $exePath)) {
        throw "Build finished, but the executable was not found: $exePath"
    }

    Write-Host ""
    Write-Host "Build complete." -ForegroundColor Green
    Write-Host "Executable:"
    Write-Host "  $exePath"
    Write-Host ""
    Write-Host "Distribute the whole folder:"
    Write-Host "  $(Join-Path $buildRoot $appName)"
    Write-Host ""
} finally {
    Pop-Location
}
