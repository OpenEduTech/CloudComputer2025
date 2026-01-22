# 第一阶段：构建 (Build Stage)
# 使用 Node.js 环境把你的 Vue 代码打包成静态文件
FROM node:23-alpine AS builder

# 设置工作目录
WORKDIR /app

# 先拷贝 package.json 安装依赖 (利用 Docker 缓存机制加速)
COPY package*.json ./
RUN npm install

# 拷贝所有源代码
COPY . .

# 执行构建命令 (这一步会生成 dist 文件夹)
RUN npm run build

# 第二阶段：部署 (Production Stage)
# 使用 Nginx 来运行打包好的网页 (体积更小，速度更快)
FROM nginx:alpine

# 第二阶段部署部分，在COPY dist之前/之后加这行
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# 把第一阶段构建好的 dist 文件夹里的内容，复制到 Nginx 的网站目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露 80 端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]