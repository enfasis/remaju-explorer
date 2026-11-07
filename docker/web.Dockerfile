FROM node:22-bookworm-slim
WORKDIR /app
COPY web/package*.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
CMD ["npm", "run", "build"]
