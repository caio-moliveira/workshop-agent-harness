# nginx — única porta exposta: serve a SPA (React+Vite) + proxy da API.
# Build multi-stage: estágio Node compila a SPA; estágio nginx serve o `dist`.
# Build context = raiz do repo (ver docker-compose.yml).

# --- estágio de build da SPA ---
FROM node:22-alpine AS build
WORKDIR /app
# Camada de deps separada (cacheável): só muda quando o lockfile muda.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- estágio de runtime (nginx) ---
FROM nginx:1.27-alpine
COPY infra/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
