# syntax=docker/dockerfile:1
# Multi-stage build for the Next.js standalone server (next.config: output:"standalone").
# Build:  docker build -t knowledge-dashboard .
# Run:    docker run -p 3000:3000 -e DASHBOARD_API_KEY=... \
#                -v "$PWD/data:/app/data:ro" knowledge-dashboard
# The dashboard reads data/*.json at runtime; mount or sync it in (the app
# returns graceful empty states if the data dir is absent).

FROM node:20-alpine AS base

# deps: install with a clean, reproducible lockfile.
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# builder: compile the production bundle.
FROM base AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# runner: minimal standalone server as a non-root user.
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV KNOWLEDGE_DASHBOARD_DATA_DIR=/app/data

RUN addgroup --system --gid 1001 nodejs \
	&& adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
# Ensure a writable data mount point exists even when nothing is mounted yet.
# The API uses KNOWLEDGE_DASHBOARD_DATA_DIR, so nested standalone output never
# has to read a stale copied data directory.
RUN mkdir -p /app/data \
	&& if [ -d /app/projects/knowledge-dashboard ]; then \
		mkdir -p /app/projects/knowledge-dashboard/.next; \
		cp -r /app/public /app/projects/knowledge-dashboard/public; \
		cp -r /app/.next/static /app/projects/knowledge-dashboard/.next/static; \
	fi \
	&& chown -R nextjs:nodejs /app/data /app/public /app/.next \
	&& if [ -d /app/projects/knowledge-dashboard ]; then \
		chown -R nextjs:nodejs /app/projects/knowledge-dashboard/public /app/projects/knowledge-dashboard/.next; \
	fi

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
	CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["sh", "-c", "if [ -f server.js ]; then exec node server.js; fi; exec node projects/knowledge-dashboard/server.js"]
