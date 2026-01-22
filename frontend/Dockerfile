FROM docker.m.daocloud.io/node:18-alpine

WORKDIR /app

# 复制依赖定义
COPY package*.json ./

# 设置 npm 淘宝镜像源
RUN npm config set registry https://registry.npmmirror.com
RUN npm install

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 5173

# 启动开发服务器
CMD ["npm", "run", "dev", "--", "--host"]
