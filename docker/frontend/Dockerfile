# syntax=docker/dockerfile:1.7
# Build context: ./frontend. Targets: `dev` (hot reload, used by docker-compose) and `runner` (prod).
ARG NODE_IMAGE=node:22-alpine

FROM ${NODE_IMAGE} AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

FROM ${NODE_IMAGE} AS dev
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM ${NODE_IMAGE} AS builder
WORKDIR /app
# Rewrites (API proxy target) are resolved at build time for standalone output.
ARG BACKEND_URL=http://backend:8000
# Build provenance (scripts/build-info.sh), inlined into the bundle by next.config.ts.
ARG POLYFLOW_GIT_SHA=unknown
ARG POLYFLOW_GIT_BRANCH=unknown
ARG POLYFLOW_BUILD_TIME=
ENV BACKEND_URL=${BACKEND_URL} \
    POLYFLOW_GIT_SHA=${POLYFLOW_GIT_SHA} \
    POLYFLOW_GIT_BRANCH=${POLYFLOW_GIT_BRANCH} \
    POLYFLOW_BUILD_TIME=${POLYFLOW_BUILD_TIME} \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM ${NODE_IMAGE} AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
