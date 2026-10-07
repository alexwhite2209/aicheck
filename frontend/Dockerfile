FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ARG NEXT_PUBLIC_OPERATOR_NAME=
ARG NEXT_PUBLIC_OPERATOR_INN=
ARG NEXT_PUBLIC_OPERATOR_OGRN=
ARG NEXT_PUBLIC_OPERATOR_ADDRESS=
ARG NEXT_PUBLIC_OPERATOR_EMAIL=
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_PUBLIC_OPERATOR_NAME=$NEXT_PUBLIC_OPERATOR_NAME \
    NEXT_PUBLIC_OPERATOR_INN=$NEXT_PUBLIC_OPERATOR_INN \
    NEXT_PUBLIC_OPERATOR_OGRN=$NEXT_PUBLIC_OPERATOR_OGRN \
    NEXT_PUBLIC_OPERATOR_ADDRESS=$NEXT_PUBLIC_OPERATOR_ADDRESS \
    NEXT_PUBLIC_OPERATOR_EMAIL=$NEXT_PUBLIC_OPERATOR_EMAIL \
    NEXT_TELEMETRY_DISABLED=1 \
    NEXT_STANDALONE=1
RUN npm run build

FROM node:22-alpine AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /app/.next/standalone ./
COPY --from=build --chown=app:app /app/.next/static ./.next/static
COPY --from=build --chown=app:app /app/public ./public
USER app
EXPOSE 3000
CMD ["node", "server.js"]
