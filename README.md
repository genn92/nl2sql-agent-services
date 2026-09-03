# nl2sql-agent

## Docker 服务组

`docker/docker-compose.yaml` 定义了一组基础服务：MySQL 数据库、Elasticsearch（含 Kibana）、Qdrant 向量数据库、Embedding 模型服务。

### 环境变量

环境变量统一维护在项目根目录的 `.env` 文件中，应用侧与 Docker 服务读取同一份配置。请参照 `.env.example` 创建 `.env`：

```bash
cp .env.example .env
```

然后在 `.env` 中填入实际值（如 `MYSQL_ROOT_PASSWORD`、`MYSQL_USER`、`MYSQL_PASSWORD` 等）。
VS Code 工作区已在 `.vscode/settings.json` 中配置 `NO_PROXY`，避免本地服务请求被 HTTP 代理转发。修改后请新建一个 VS Code 集成终端使设置生效。

### 启动 Docker 服务

在**项目根目录**执行：

```bash
docker compose --env-file .env -f docker/docker-compose.yaml up -d
```

> 说明：`--env-file .env` 显式指定根目录的 `.env`，保证 compose 中的 `${MYSQL_*}` 等变量能正确解析；`-f docker/docker-compose.yaml` 指定 compose 文件位置。

### 其他常用命令

```bash
# 停止服务
docker compose --env-file .env -f docker/docker-compose.yaml down

# 查看日志
docker compose --env-file .env -f docker/docker-compose.yaml logs -f

# 查看配置解析结果（校验环境变量是否正确加载，不会启动容器）
docker compose --env-file .env -f docker/docker-compose.yaml config
```

### 服务端口

| 服务 | 端口 |
| --- | --- |
| MySQL | 3306 |
| Elasticsearch | 9200 |
| Kibana | 5601 |
| Qdrant (HTTP / gRPC) | 6333 / 6334 |
| Embedding | 8081 |
