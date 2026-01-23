# --- Stage 1: 构建阶段 ---
FROM node:18-alpine as build-stage

WORKDIR /app

# 拷贝 package.json (利用缓存)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# 拷贝源代码
COPY frontend/ .

# 开始构建 (生成 dist 文件夹)
RUN npm run build

# --- Stage 2: 运行阶段 ---
FROM nginx:stable-alpine as production-stage

# 移除默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 拷贝我们的自定义 Nginx 配置
COPY deploy/nginx.conf /etc/nginx/conf.d/

# 从构建阶段拷贝编译好的文件
COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
