# Next.js web app (v2 §8). Consumes the same Django API as the Flutter app;
# nginx routes /api/* to Django on the same origin, so no CORS setup needed.
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --omit=dev || npm install --omit=dev

COPY . .
# Dev-only rewrites in next.config.mjs don't apply to `next start`; nginx
# handles /api in production.
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
# No public/ directory in this app — nothing static to copy.

EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
