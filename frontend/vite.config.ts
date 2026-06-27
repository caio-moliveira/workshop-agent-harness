import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// API só via nginx (regra frontend.md): em dev, o Vite faz proxy de /chat e /health
// para o nginx (porta 8080), nunca direto para o container `api`. O proxy preserva o
// streaming SSE (sem buffer). Sobrescreva o alvo com VITE_PROXY_ALVO se o nginx mudar.
const ALVO = process.env.VITE_PROXY_ALVO ?? "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/chat": { target: ALVO, changeOrigin: true },
      "/health": { target: ALVO, changeOrigin: true },
    },
  },
});
