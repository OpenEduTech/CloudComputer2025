# Cross-Disciplinary Knowledge Graph - Quick Start Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cross-Disciplinary Knowledge Graph - Docker Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker (with timeout)
Write-Host "[Check] Verifying Docker environment..." -ForegroundColor Yellow
$job = Start-Job -ScriptBlock { docker version }
$completed = Wait-Job $job -Timeout 10
if ($completed) {
    Receive-Job $job | Out-Null
    Remove-Job $job
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} else {
    Stop-Job $job
    Remove-Job $job
    Write-Host "[WARN] Docker check timeout. Continuing anyway..." -ForegroundColor Yellow
    Write-Host "       If deployment fails, try restarting Docker Desktop" -ForegroundColor Gray
}

Write-Host ""

# Check .env file
if (-not (Test-Path .env)) {
    Write-Host "[!] .env file not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "[i] Please edit .env and add your OPENROUTER_API_KEY" -ForegroundColor Cyan
    Write-Host "    Location: $(Get-Location)\.env" -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to continue"
}

Write-Host "[Start] Building and starting services..." -ForegroundColor Yellow
Write-Host ""

# Build and start (with explicit project name to avoid Chinese path issues)
docker-compose -p conceptgraph up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Services started successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "Access URLs:" -ForegroundColor Cyan
    Write-Host "  - Frontend:  " -NoNewline -ForegroundColor White
    Write-Host "http://localhost:3000" -ForegroundColor Yellow
    Write-Host "  - Backend:   " -NoNewline -ForegroundColor White
    Write-Host "http://localhost:8000/docs" -ForegroundColor Yellow
    Write-Host "  - Neo4j:     " -NoNewline -ForegroundColor White
    Write-Host "http://localhost:7474" -ForegroundColor Yellow
    Write-Host "    (username: neo4j, password: conceptgraph123)" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Useful Commands:" -ForegroundColor Cyan
    Write-Host "  - View logs:  " -NoNewline -ForegroundColor White
    Write-Host "docker-compose logs -f" -ForegroundColor Yellow
    Write-Host "  - View status:" -NoNewline -ForegroundColor White
    Write-Host "docker-compose ps" -ForegroundColor Yellow
    Write-Host "  - Stop all:   " -NoNewline -ForegroundColor White
    Write-Host "docker-compose down" -ForegroundColor Yellow
    Write-Host ""
    
    # Ask to open browser
    $open = Read-Host "Open frontend in browser? (Y/n)"
    if ($open -ne 'n' -and $open -ne 'N') {
        Start-Process "http://localhost:3000"
    }
} else {
    Write-Host ""
    Write-Host "[ERROR] Failed to start services. Please check the error messages above." -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
