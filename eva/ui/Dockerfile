# syntax=docker/dockerfile:1

# ── Stage 1: build ───────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY tsconfig*.json vite.config.ts eslint.config.js index.html ./
COPY src ./src
COPY public ./public

# VITE_ vars are baked into the JS bundle — they are public by nature
# (visible in browser source). Only non-secret config belongs here.
# Sensitive values must never be passed via ARG/ENV; use a secrets
# manager or inject them at runtime outside the image.
ARG VITE_AGENT_NAME
ARG VITE_AUTH_URL=/auth
ARG VITE_APIVIDEO_API_KEY

ENV VITE_AGENT_NAME=$VITE_AGENT_NAME
ENV VITE_AUTH_URL=$VITE_AUTH_URL
ENV VITE_APIVIDEO_API_KEY=$VITE_APIVIDEO_API_KEY

RUN pnpm build

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/app.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
