import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 可通过 VITE_API_BASE 环境变量覆盖后端地址（例如：http://localhost:8000）
const apiBase = process.env.VITE_API_BASE || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    proxy: {
      "/api": {
        target: apiBase,
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
