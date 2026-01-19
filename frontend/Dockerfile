FROM node:18-alpine

WORKDIR /app

# 复制依赖定义
COPY package*.json ./

# 安装依赖 (由于网络问题，如果在国内可能会慢，这里使用默认源，实际运行建议配置镜像源)
# RUN npm config set registry https://registry.npmmirror.com
RUN npm install

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 5173

# 启动开发服务器
CMD ["npm", "run", "dev", "--", "--host"]
