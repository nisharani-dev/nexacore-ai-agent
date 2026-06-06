FROM node:20-alpine AS build
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_USE_MOCK=false
RUN npm run build

FROM nginx:1.27-alpine
ENV BACKEND_URL=http://backend:8000
COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
