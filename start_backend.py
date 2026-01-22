"""
快速启动后端服务
"""
import subprocess
import sys
import os
from pathlib import Path

# 切换到backend目录
backend_dir = Path(__file__).parent / "backend"
os.chdir(backend_dir)

print("="*70)
print("启动ConceptGraph后端服务")
print("="*70)
print(f"工作目录: {os.getcwd()}")
print(f"Python版本: {sys.version}")
print()

# 启动uvicorn
cmd = [
    sys.executable,
    "-m", "uvicorn",
    "main:app",
    "--reload",
    "--port", "8000",
    "--host", "0.0.0.0"
]

print(f"执行命令: {' '.join(cmd)}")
print()
print("API接口:")
print("  - 功能1（自动跨学科）: POST http://localhost:8000/api/v1/discover")
print("  - 功能2（指定学科）: POST http://localhost:8000/api/v1/discover/disciplined")
print("  - 功能3（桥梁发现）: POST http://localhost:8000/api/v1/discover/bridge")
print("  - API文档: http://localhost:8000/docs")
print("="*70)
print()

try:
    subprocess.run(cmd, check=True)
except KeyboardInterrupt:
    print("\n服务已停止")
except Exception as e:
    print(f"\n启动失败: {e}")
    sys.exit(1)
