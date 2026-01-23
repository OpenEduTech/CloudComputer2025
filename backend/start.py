"""
启动脚本 - 配置更长的超时时间以支持 LLM 调用
使用方法: python start.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_keep_alive=120,  # 保持连接超时时间（秒）
        timeout_graceful_shutdown=30,  # 优雅关闭超时时间（秒）
    )
