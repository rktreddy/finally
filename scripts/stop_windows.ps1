$ErrorActionPreference = "Stop"

$ContainerName = "finally-app"

# Stop and remove container (idempotent)
$running = docker ps -q -f "name=$ContainerName" 2>$null
if ($running) {
    Write-Host "Stopping FinAlly..."
    docker stop $ContainerName | Out-Null
}

$exists = docker ps -aq -f "name=$ContainerName" 2>$null
if ($exists) {
    docker rm $ContainerName | Out-Null
    Write-Host "Container removed."
} else {
    Write-Host "No running FinAlly container found."
}

Write-Host "Note: Data volume 'finally-data' is preserved. Use 'docker volume rm finally-data' to delete it."
