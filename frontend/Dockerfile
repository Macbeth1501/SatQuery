# SatQuery AI frontend: build the static bundle, then serve it with nginx.
#   docker build -t satquery-frontend --build-arg VITE_API_BASE_URL=http://127.0.0.1:8000 frontend
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Vite inlines this at build time, and it is the address the *browser* uses to reach the
# API, not an address between containers.
ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1
