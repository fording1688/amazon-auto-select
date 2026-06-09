ARG NODE_IMAGE=docker.m.daocloud.io/library/node:20-alpine
ARG NGINX_IMAGE=docker.m.daocloud.io/library/nginx:1.27-alpine

FROM ${NODE_IMAGE} AS build

WORKDIR /app

ARG NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8005
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM ${NGINX_IMAGE} AS production

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/out /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
