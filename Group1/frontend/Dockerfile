FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

# 创建启动脚本，使用 node 直接运行 vite
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'echo "Current directory: $(pwd)"' >> /app/start.sh && \
    echo 'echo "Checking vite entry point: $(ls -la node_modules/vite/bin/vite.js 2>/dev/null || echo "No vite.js")"' >> /app/start.sh && \
    echo 'echo "Starting vite..."' >> /app/start.sh && \
    echo 'node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]

