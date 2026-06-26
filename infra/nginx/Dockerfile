# nginx — reverse proxy + SPA. Build context = raiz do repo (ver docker-compose.yml).
# Multi-stage: stage 1 builda o frontend React+Vite; stage 2 serve os estáticos + proxy.

# --- stage 1: build da SPA ---
FROM node:22-alpine AS build
WORKDIR /app
# Camada de deps primeiro (cache): só muda quando o lockfile/manifesto muda.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- stage 2: nginx servindo a SPA + proxy da API ---
FROM nginx:1.27-alpine
COPY infra/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
