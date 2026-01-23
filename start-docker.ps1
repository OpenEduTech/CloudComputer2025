# FactGuardian Docker 启动脚本
# 使用方法: .\start-docker.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FactGuardian Docker 启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否运行
Write-Host "[1/6] 检查 Docker 状态..." -ForegroundColor Yellow
try {
    $null = docker --version 2>&1
    Write-Host "  [OK] Docker 已安装" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Docker 未安装或无法访问" -ForegroundColor Red
    exit 1
}

try {
    $null = docker info 2>&1 | Out-Null
    Write-Host "  [OK] Docker 正在运行" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 切换到项目目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
Write-Host "[2/6] 切换到项目目录: $scriptDir" -ForegroundColor Yellow

# 检查 .env 文件
Write-Host "[3/6] 检查环境配置..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  [OK] 找到 .env 文件" -ForegroundColor Green
} else {
    Write-Host "  [WARN] 未找到 .env 文件，请确保已配置 DEEPSEEK_API_KEY" -ForegroundColor Yellow
}

Write-Host ""

# 停止并删除旧容器（如果存在）
Write-Host "[4/6] 清理旧容器..." -ForegroundColor Yellow
docker-compose down 2>&1 | Out-Null
# 强制删除可能冲突的容器（防止名称冲突错误）
docker rm -f factguardian-backend factguardian-frontend factguardian-redis 2>&1 | Out-Null
Write-Host "  [OK] 旧容器已清理" -ForegroundColor Green

Write-Host ""

# 构建镜像
Write-Host "[5/6] 构建 Docker 镜像..." -ForegroundColor Yellow
docker-compose build --no-cache
if ($?) {
    Write-Host "  [OK] 镜像构建成功" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] 镜像构建失败" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 启动服务
Write-Host "[6/6] 启动服务..." -ForegroundColor Yellow
docker-compose up -d
if ($?) {
    Write-Host "  [OK] 服务启动成功" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] 服务启动失败" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 等待服务就绪
Write-Host "等待服务就绪..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 检查容器状态
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  容器状态" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  服务信息" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  - 后端 API: http://localhost:8000" -ForegroundColor Green
Write-Host "  - API 文档: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  - Redis: localhost:6379" -ForegroundColor Green
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Yellow
Write-Host "  - 查看日志: docker-compose logs -f" -ForegroundColor White
Write-Host "  - 停止服务: docker-compose down" -ForegroundColor White
Write-Host "  - 重启服务: docker-compose restart" -ForegroundColor White
Write-Host "  - 查看状态: docker-compose ps" -ForegroundColor White
Write-Host ""

# 询问是否查看日志
$response = Read-Host "是否查看实时日志? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host ""
    Write-Host "按 Ctrl+C 退出日志查看" -ForegroundColor Yellow
    docker-compose logs -f
}

