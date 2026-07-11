FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
# NOTE: no public/ dir exists in this repo today — if one is added later, also add:
#   COPY --from=builder /app/public ./public
# or static assets will 404 in production (dev server serves public/ automatically, standalone doesn't).
EXPOSE 3000
CMD ["node", "server.js"]
