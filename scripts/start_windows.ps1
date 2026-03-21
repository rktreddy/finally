$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ImageName = "finally"
$ContainerName = "finally-app"
$VolumeName = "finally-data"
$Port = 8000

Set-Location $ProjectDir

# Build image if needed or if -Build flag passed
$NeedsBuild = $args -contains "--build"
if (-not $NeedsBuild) {
    $inspect = docker image inspect $ImageName 2>&1
    if ($LASTEXITCODE -ne 0) { $NeedsBuild = $true }
}

if ($NeedsBuild) {
    Write-Host "Building Docker image..."
    docker build -t $ImageName .
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

# Stop existing container if running (idempotent)
$running = docker ps -q -f "name=$ContainerName" 2>$null
if ($running) {
    Write-Host "Stopping existing container..."
    docker stop $ContainerName | Out-Null
    docker rm $ContainerName | Out-Null
} else {
    $exists = docker ps -aq -f "name=$ContainerName" 2>$null
    if ($exists) {
        docker rm $ContainerName | Out-Null
    }
}

# Ensure .env file exists
if (Test-Path ".env") {
    $EnvFile = ".env"
} else {
    Write-Host "Warning: .env file not found. Copy .env.example to .env and configure it."
    Write-Host "Using .env.example as fallback..."
    $EnvFile = ".env.example"
}

# Run container
Write-Host "Starting FinAlly..."
docker run -d `
    --name $ContainerName `
    -v "${VolumeName}:/app/db" `
    -p "${Port}:${Port}" `
    --env-file $EnvFile `
    $ImageName

if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "FinAlly is running at http://localhost:$Port"
Write-Host ""

# Open browser
Start-Process "http://localhost:$Port"
