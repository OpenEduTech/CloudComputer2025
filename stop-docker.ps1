# FactGuardian Docker 停止脚本
# 使用方法: .\stop-docker.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FactGuardian Docker 停止脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 切换到项目目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 停止并删除容器
Write-Host "正在停止并删除容器..." -ForegroundColor Yellow
docker-compose down

if ($?) {
    Write-Host ""
    Write-Host "  [OK] 服务已停止" -ForegroundColor Green
    Write-Host ""
    
    # 询问是否清理数据卷
    $response = Read-Host "是否删除 Redis 数据卷? (y/n) [警告: 会删除所有缓存数据]"
    if ($response -eq "y" -or $response -eq "Y") {
        docker-compose down -v
        Write-Host "  [OK] 数据卷已删除" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "  [ERROR] 停止服务时出现错误" -ForegroundColor Red
    exit 1
}
