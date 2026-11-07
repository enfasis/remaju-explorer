FROM node:22-bookworm-slim
WORKDIR /app
COPY src/web/package*.json ./
COPY src/web/.npmrc ./
RUN npm ci --no-audit --no-fund
COPY src/web/ ./
CMD ["npm", "run", "build"]
