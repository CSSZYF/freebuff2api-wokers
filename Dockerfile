FROM node:20-alpine

WORKDIR /app

# 运行时工具：wget 用于容器内排查网络
RUN apk add --no-cache wget

# 保持零依赖：不装 npm 包，避免构建产物带平台相关的二进制导致架构不匹配
COPY package.json server.js worker.js ./

# ⚠️ 与原版的唯一差异：不再在启动时从上游仓库拉取 worker.js 覆盖本地副本。
# 原版 entrypoint 每次启动都会用 raw.githubusercontent.com 上的最新 worker.js
# 覆盖 /app/worker.js，会让本地对 PAUSED_MODELS 的修改在重启后失效。
# 需要跟随上游更新时，手动重新同步 worker.js 后再触发一次构建。
#
# 原版 entrypoint 逻辑（保留备查）：
#   wget -q --timeout=15 -O /tmp/worker.js "$WORKER_URL" && cp /tmp/worker.js /app/worker.js
#   exec node /app/server.js

RUN mkdir -p /app/credentials && chown -R node:node /app

USER node
EXPOSE 8787

CMD ["node", "server.js"]
