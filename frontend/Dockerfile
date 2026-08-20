# ===== CCTV AI Frontend =====
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY frontend/ .
# Default API base for the containerized frontend (nginx proxies /api -> backend)
ENV VITE_API_BASE=/api
ENV VITE_WS_BASE=/ws
RUN npm run build

# Serve with nginx
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
