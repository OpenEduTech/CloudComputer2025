#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的HTTP服务器，用于提供前端文件
解决file://协议的CORS问题
"""

import http.server
import socketserver
import os
import sys

PORT = 8080
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), 'frontend')

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)
    
    def end_headers(self):
        # 添加CORS头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    os.chdir(FRONTEND_DIR)
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"前端服务器启动: http://127.0.0.1:{PORT}")
        print(f"访问地址: http://127.0.0.1:{PORT}/index.html")
        print("按 Ctrl+C 停止服务器")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
            sys.exit(0)

if __name__ == '__main__':
    main()
