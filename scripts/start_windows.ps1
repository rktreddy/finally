$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
Set-Location $ProjectDir

$ContainerName = "finally"
$ImageName = "finally"
$VolumeName = "finally-data"

# Build if --build flag or image doesn't exist
$shouldBuild = $false
if ($args -contains "--build") { $shouldBuild = $true }
try { docker image inspect $ImageName 2>&1 | Out-Null } catch { $shouldBuild = $true }
if ($shouldBuild) {
    Write-Host "Building $ImageName Docker image..."
    docker build -t $ImageName .
}

# Stop existing container if running
$running = docker ps -q -f "name=$ContainerName" 2>$null
if ($running) {
    Write-Host "Stopping existing $ContainerName container..."
    docker stop $ContainerName | Out-Null
    docker rm $ContainerName | Out-Null
} else {
    $stopped = docker ps -aq -f "name=$ContainerName" 2>$null
    if ($stopped) { docker rm $ContainerName | Out-Null }
}

Write-Host "Starting $ContainerName..."
docker run -d `
    --name $ContainerName `
    -p 8000:8000 `
    -v "${VolumeName}:/app/db" `
    --env-file .env `
    $ImageName

Write-Host ""
Write-Host "FinAlly is running at http://localhost:8000"
Write-Host "To stop: .\scripts\stop_windows.ps1"
