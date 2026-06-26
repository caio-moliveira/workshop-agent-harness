import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Em dev, o proxy manda /chat e /health para a API local (8000) — em produção quem
// faz o proxy é o nginx (mesma origem). Sem segredo no bundle: a única origem é o nginx.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/chat": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
