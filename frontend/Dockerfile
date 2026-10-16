# Build the Astro site, then serve the static output with nginx.
FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-fund --no-audit

COPY . .

# Browser-facing API URL, baked in at build time (astro static build).
ARG PUBLIC_API_URL=http://localhost:8000
ENV PUBLIC_API_URL=${PUBLIC_API_URL}
RUN npm run build

FROM nginx:stable-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
