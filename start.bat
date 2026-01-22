@echo off
chcp 65001 >nul 2>&1
REM 跨学科知识图谱系统 - Windows快速启动脚本

echo ========================================
echo Cross-Disciplinary Knowledge Graph - Docker Deployment
echo 跨学科知识图谱系统 - Docker快速部署
echo ========================================
echo.

REM 检查Docker是否运行
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running
    echo [错误] Docker未运行，请先启动Docker Desktop
    pause
    exit /b 1
)

echo [OK] Docker environment check passed
echo [成功] Docker环境检查通过
echo.

REM 检查.env文件
if not exist .env (
    echo [WARNING] .env file not found, creating from template...
    echo [警告] 未找到.env文件，正在创建...
    copy .env.example .env
    echo [INFO] Please edit .env file and add your OPENROUTER_API_KEY
    echo [提示] 请编辑.env文件，填入你的OPENROUTER_API_KEY
    echo File location: %cd%\.env
    pause
)

echo [INFO] Building and starting services...
echo [信息] 开始构建并启动服务...
echo.

REM 构建并启动
docker-compose up --build -d

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Services started successfully!
    echo [成功] 服务启动成功！
    echo.
    echo [URLS] Access Points:
    echo   - Frontend: http://localhost:3000
    echo   - Backend API: http://localhost:8000/docs
    echo   - Neo4j Browser: http://localhost:7474 (neo4j/conceptgraph123)
    echo.
    echo [COMMANDS] Useful Commands:
    echo   - View logs: docker-compose logs -f
    echo   - Stop services: docker-compose down
    echo.
    pause
) else (
    echo.
    echo [ERROR] Service startup failed, please check error messages
    echo [错误] 服务启动失败，请查看错误信息
    pause
    exit /b 1
)

