# 修复 python_pptx 导入问题 - 添加在 main.py 最开头
import sys
try:
    import pptx
    sys.modules['python_pptx'] = pptx  # 关键：创建别名
except ImportError:
    print("错误：请安装 python-pptx: pip install python-pptx")
    sys.exit(1)
#!/usr/bin/env python3
"""
PPT内容扩展智能体 - 主程序
单机完整版，包含所有核心功能
"""

import os
import sys
import logging
import uvicorn
from dotenv import load_dotenv
from typing import Optional
import argparse

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log',encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """检查依赖"""
    required_vars = ['SILICONFLOW_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        logger.error(f"缺少环境变量: {', '.join(missing)}")
        logger.info("请创建 .env 文件并设置以下变量:")
        logger.info("SILICONFLOW_API_KEY=你的硅基流动API密钥")
        return False

    try:
        # 检查核心依赖
        import fastapi
        import pydantic
        import python_pptx
        import httpx
        logger.info("✅ 所有依赖检查通过")
        return True
    except ImportError as e:
        logger.error(f"❌ 依赖导入失败: {e}")
        logger.info("请运行: pip install -r requirements.txt")
        return False


def run_api():
    """运行API服务"""
    from api import app
    logger.info("🚀 启动API服务...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8010,
        log_level="info"
    )


def run_web():
    """运行Web界面"""
    import subprocess
    import webbrowser
    import time
    import sys

    print("启动Web界面...")

    try:
        # 启动Streamlit（使用正确的路径）
        web_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "web_app.py", "--server.port=8501"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding='utf-8'
        )

        print("等待Streamlit启动...")
        time.sleep(5)  # 等待更长时间

        # 检查进程是否在运行
        if web_process.poll() is None:
            print("Web界面已启动: http://localhost:8501")
            print("按 Ctrl+C 停止服务")

            # 打开浏览器
            try:
                webbrowser.open("http://localhost:8501")
            except:
                print("无法自动打开浏览器，请手动访问: http://localhost:8501")

            try:
                web_process.wait()
            except KeyboardInterrupt:
                print("\n停止服务...")
                web_process.terminate()
                web_process.wait()
                print("服务已停止")
        else:
            # 读取错误输出
            stdout, stderr = web_process.communicate()
            print(f"Streamlit启动失败:\n{stderr}")

    except Exception as e:
        print(f"启动Web界面失败: {e}")
        print("请尝试手动启动: python -m streamlit run web_app.py")


def run_cli():
    """运行命令行界面"""
    from cli import main as cli_main
    cli_main()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PPT内容扩展智能体')
    parser.add_argument('--mode', choices=['api', 'web', 'cli'], default='web',
                        help='运行模式: api(API服务), web(Web界面), cli(命令行)')
    parser.add_argument('--port', type=int, default=8000, help='API端口')
    parser.add_argument('--web-port', type=int, default=8501, help='Web端口')

    args = parser.parse_args()

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("📚 PPT内容扩展智能体 v1.0")
    logger.info("=" * 50)

    if args.mode == 'api':
        os.environ['API_PORT'] = str(args.port)
        run_api()
    elif args.mode == 'web':
        os.environ['WEB_PORT'] = str(args.web_port)
        run_web()
    elif args.mode == 'cli':
        run_cli()


if __name__ == "__main__":
    main()