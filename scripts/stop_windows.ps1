$ErrorActionPreference = "Stop"

$ContainerName = "finally"

$running = docker ps -q -f "name=$ContainerName" 2>$null
if ($running) {
    Write-Host "Stopping $ContainerName..."
    docker stop $ContainerName | Out-Null
    docker rm $ContainerName | Out-Null
    Write-Host "$ContainerName stopped. Data volume preserved."
} else {
    $stopped = docker ps -aq -f "name=$ContainerName" 2>$null
    if ($stopped) {
        docker rm $ContainerName | Out-Null
        Write-Host "Removed stopped $ContainerName container. Data volume preserved."
    } else {
        Write-Host "No $ContainerName container found."
    }
}
