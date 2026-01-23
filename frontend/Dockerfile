# FactGuardian Frontend Dockerfile
# 多阶段构建：构建阶段 + 运行阶段

# ========== 构建阶段 ==========
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 配置 npm（增加超时时间和重试次数，可选：使用国内镜像源）
# 如果需要使用淘宝镜像，取消下面这行的注释：
# RUN npm config set registry https://registry.npmmirror.com
RUN npm config set fetch-timeout 300000 && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000

# 复制 package 文件
COPY package*.json ./

# 安装依赖（使用 npm ci 更快更可靠，适合 CI/CD）
RUN if [ -f package-lock.json ]; then \
        npm ci --legacy-peer-deps; \
    else \
        npm install --legacy-peer-deps; \
    fi

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# ========== 开发阶段（用于开发环境）==========
FROM node:18-alpine AS development

WORKDIR /app

# 配置 npm
RUN npm config set fetch-timeout 300000 && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000

# 复制 package 文件
COPY package*.json ./

# 安装依赖
RUN if [ -f package-lock.json ]; then \
        npm ci --legacy-peer-deps; \
    else \
        npm install --legacy-peer-deps; \
    fi

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 3000

# 启动开发服务器
# --host 0.0.0.0 允许外部访问
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ========== 生产阶段（用于生产环境）==========
FROM nginx:alpine AS production

# 安装 curl 用于健康检查
RUN apk add --no-cache curl

# 复制构建产物到 nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 创建 nginx 配置文件，支持 SPA 路由
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # Gzip 压缩 \
    gzip on; \
    gzip_vary on; \
    gzip_min_length 1024; \
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript; \
    \
    # 支持 SPA 路由 \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    \
    # 健康检查端点 \
    location /health { \
        access_log off; \
        return 200 "healthy\n"; \
        add_header Content-Type text/plain; \
    } \
    \
    # 静态资源缓存 \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
    \
    # 安全头 \
    add_header X-Frame-Options "SAMEORIGIN" always; \
    add_header X-Content-Type-Options "nosniff" always; \
    add_header X-XSS-Protection "1; mode=block" always; \
}' > /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]

# 默认使用开发阶段（docker-compose 中可以通过 target 指定 production）
FROM development