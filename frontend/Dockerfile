FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# Rate-limit defaults; override in .env (limit-public-traffic D8).
ENV ASK_RATE_PER_MINUTE=10 ASK_RATE_BURST=5 MAX_CONNECTIONS_PER_IP=20
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
