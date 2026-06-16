# nginx — única porta exposta (issue #15/#25). Multi-stage: builda a SPA (frontend) e
# serve os estáticos + faz reverse proxy de /chat e /health para a api:8000.
# Contexto de build = raiz do repo (precisa acessar frontend/).

FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
