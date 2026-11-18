# Контейнер web: збирає інтерфейс і віддає його через nginx (без прав root), який проксіює /api
# до контейнера api, додає заголовки безпеки й обмежує частоту запитів до SPARQL і адміністрування.
# Контекст збірки — корінь репозиторію, бо стилі імпортують design/tokens.css.
FROM node:22-alpine AS build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY design/tokens.css /app/design/tokens.css
COPY frontend/ ./
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/nginx-security.conf /etc/nginx/kinograf/security.conf
COPY frontend/nginx-api.conf /etc/nginx/kinograf/api.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
EXPOSE 8080
