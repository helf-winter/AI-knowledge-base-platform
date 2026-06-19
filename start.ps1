param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [string]$CondaEnv = "knowledge-base",
    [switch]$SkipInstall,
    [switch]$InstallDeps,
    [switch]$NoWorker,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $Root "frontend"
$ApiBase = "http://127.0.0.1:$BackendPort"
$FrontendUrl = "http://127.0.0.1:$FrontendPort"

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-PortInUse($Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Http($Url, $Name) {
    Write-Host "Waiting for ${Name}: $Url"
    for ($i = 0; $i -lt 40; $i += 1) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            Write-Host "$Name is ready."
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    Write-Warning "$Name is not ready yet. Check the service terminal logs."
}

if (-not (Test-Command "conda")) {
    throw "conda was not found. Please install Miniconda/Anaconda and add conda to PATH."
}
if (-not (Test-Command "npm")) {
    throw "npm was not found. Please install Node.js 18+."
}

Write-Host "Using conda environment: $CondaEnv"
conda run -n $CondaEnv python --version | Out-Host

$FrontendEnv = Join-Path $FrontendDir ".env.local"
if (-not (Test-Path $FrontendEnv)) {
    "NEXT_PUBLIC_API_BASE=$ApiBase" | Set-Content -Path $FrontendEnv -Encoding UTF8
    Write-Host "Created frontend/.env.local"
}

if ($InstallDeps) {
    Write-Host "Installing backend dependencies..."
    conda run -n $CondaEnv python -m pip install -r (Join-Path $Root "requirements.txt")

    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "Installing frontend dependencies..."
        Push-Location $FrontendDir
        npm install
        Pop-Location
    }
} else {
    Write-Host "Skipping dependency installation. Use -InstallDeps only when dependencies changed."
}

if (Test-PortInUse $BackendPort) {
    Write-Host "Backend port $BackendPort is already in use. Skipping backend start."
} else {
    Write-Host "Starting backend: $ApiBase"
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "cd '$Root'; conda run -n '$CondaEnv' python -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort --reload"
    ) | Out-Null
}

if (-not $NoWorker) {
    if (Test-PortInUse 6379) {
        Write-Host "Starting Celery worker for background document parsing"
        Start-Process powershell -ArgumentList @(
            "-NoExit",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            "cd '$Root'; conda run -n '$CondaEnv' celery -A app.worker.celery_app worker --pool=solo --loglevel=info"
        ) | Out-Null
    } else {
        Write-Warning "Redis port 6379 is not listening. Background parsing worker was not started."
        Write-Warning "Start Redis first, or run with Docker Compose. Small files can still parse synchronously."
    }
}

if (Test-PortInUse $FrontendPort) {
    Write-Host "Frontend port $FrontendPort is already in use. Skipping frontend start."
} else {
    Write-Host "Starting frontend: $FrontendUrl"
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "cd '$FrontendDir'; `$env:NEXT_PUBLIC_API_BASE='$ApiBase'; npm run dev -- --hostname 127.0.0.1 --port $FrontendPort"
    ) | Out-Null
}

Wait-Http "$ApiBase/health" "backend"
Wait-Http $FrontendUrl "frontend"

Write-Host ""
Write-Host "Started successfully."
Write-Host "  Frontend: $FrontendUrl"
Write-Host "  Backend:  $ApiBase"
Write-Host "  Default account: admin / 123456"
Write-Host "  Backend conda env: $CondaEnv"

if (-not $NoBrowser) {
    Start-Process $FrontendUrl | Out-Null
}
