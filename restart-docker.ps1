# FactGuardian Docker 重启脚本
# 使用方法: .\restart-docker.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FactGuardian Docker 重启脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 切换到项目目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 重启服务
Write-Host "正在重启服务..." -ForegroundColor Yellow
docker-compose restart

if ($?) {
    Write-Host ""
    Write-Host "  [OK] 服务已重启" -ForegroundColor Green
    Write-Host ""
    
    # 等待服务就绪
    Write-Host "等待服务就绪..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    # 显示状态
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  容器状态" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    docker-compose ps
    
    Write-Host ""
    Write-Host "  - 后端 API: http://localhost:8000" -ForegroundColor Green
    Write-Host "  - API 文档: http://localhost:8000/docs" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  [ERROR] 重启服务时出现错误" -ForegroundColor Red
    Write-Host "  尝试运行 .\start-docker.ps1 重新构建并启动" -ForegroundColor Yellow
    exit 1
}
