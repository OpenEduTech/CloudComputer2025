# 前端构建阶段
FROM node:18-alpine as build

WORKDIR /app/frontend

# 配置 cnpm 镜像加速
RUN npm config set registry https://registry.npmmirror.com/

# 复制 package files
COPY package*.json ./

# 安装依赖
RUN npm ci --legacy-peer-deps || npm ci --legacy-peer-deps

# 复制前端代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 删除默认配置
RUN rm /etc/nginx/conf.d/default.conf && mkdir -p /etc/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建好的文件到 nginx 两个位置
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY --from=build /app/frontend/dist /etc/nginx/html

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
