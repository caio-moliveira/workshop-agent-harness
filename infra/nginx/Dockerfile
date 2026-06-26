# nginx — reverse proxy + estáticos. Build context = raiz do repo (ver docker-compose.yml).
# Placeholder de SPA até a issue #32, que troca por um build multi-stage do React+Vite.
FROM nginx:1.27-alpine

COPY infra/nginx/nginx.conf /etc/nginx/conf.d/default.conf

RUN printf '%s' \
    '<!doctype html><html lang="pt-br"><head><meta charset="utf-8">' \
    '<title>Bússola — Agente Analítico de Vendas</title></head>' \
    '<body><h1>Bússola</h1><p>API no ar. Endpoints: <code>/health</code>, <code>/chat</code>.</p>' \
    '</body></html>' > /usr/share/nginx/html/index.html
