# syntax=docker/dockerfile:1

# ── Stage 1: build ───────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

# Enable corepack so pnpm is available without a separate install step
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Install deps before copying source so this layer is cached when only
# source files change.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Compile TypeScript
COPY tsconfig.json ./
COPY src ./src
RUN pnpm build

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM node:22-alpine AS runner

ENV NODE_ENV=production

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Only install production dependencies in the final image
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod

# Copy compiled output from builder
COPY --from=builder /app/dist ./dist

# Session files are stored here at runtime; mount a volume in k8s
RUN mkdir -p sessions

EXPOSE 4000

# Run as non-root
RUN addgroup -S app && adduser -S app -G app
USER app

CMD ["node", "dist/index.js"]
