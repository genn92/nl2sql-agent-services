# AGENTS.md

本项目是一个中文自然语言转 SQL（NL2SQL）的 Agent 系统，所有文档、注释和 SQL 都采用中文。它的目标是：

- 接收用户中文自然语言问题
- 通过语义召回、过滤和上下文补全找出最可能使用的表、列、指标和候选值
- 调用大语言模型生成 SQL
- 对生成的 SQL 做语法和逻辑校验
- 自动修正错误 SQL，并最终执行查询返回结果

> 语言要求：所有用户回复、代码注释、提交信息和文档内容都必须使用中文。

## 项目约束

### 1. 运行时要求

- Python 版本：3.14
- 包管理工具：uv
- 禁止使用 pip 直接安装依赖，统一使用 `uv sync` 和 `uv run ...`
- 如果需要执行 Python 文件，请优先使用 `.venv/bin/python` 或 `uv run`

### 2. 代码质量要求

项目当前仅使用 Ruff 做代码检查和格式化，命令如下：

```bash
uv run ruff check .
uv run ruff format .
```

配置项在 `pyproject.toml` 中：

- 行长：88
- lint 规则：E/F/I
- 忽略：E501

### 3. 配置目录约束

`app/config` 目录必须保持在项目根目录的第二级位置，不能被移动、重命名或增加额外嵌套层级，否则配置加载逻辑会失效。

这是因为 `app/config/app_config.py` 使用了类似下面的路径方式：

```python
Path(__file__).parents[2]
```

这意味着配置文件必须在项目根目录下的 `config/` 和 `app/config/` 结构中被正确解析。

### 4. 环境变量约束

- 机密信息统一写入项目根目录的 `.env`
- `.env` 需要从 `.env.example` 复制而来
- `config/app_config.yaml` 中使用 `${oc.env:...}` 语法解析环境变量
- 关键变量包括：
  - `MYSQL_USER`
  - `MYSQL_PASSWORD`
  - `LLM_API_KEY`

如果环境变量缺失，配置加载通常不会在启动时直接报错，但在具体功能使用时会触发异常。

## 技术栈

### 核心依赖

- LLM 与 Agent：`langchain`、`langgraph`
- OpenAI 兼容接口：`langchain` 通过 `init_chat_model` 接入 SiliconFlow 兼容端点
- 数据库：`sqlalchemy`、`asyncmy`
- 搜索引擎：`elasticsearch[async]`
- 向量库：`qdrant-client`
- 中文 NLP：`jieba`
- Web 框架：`fastapi[standard]`
- 配置与日志：`omegaconf`、`pyyaml`、`python-dotenv`、`loguru`

### 运行当前状态

项目已经具备以下核心功能骨架：

- Agent 图编排完成
- SQL 生成节点已接入 LLM
- SQL 校验节点已接入数据库校验
- SQL 修正节点已接入 LLM 修正逻辑
- SQL 执行节点已接入 DW MySQL 执行器

但 `app/main.py` 还处于占位状态，当前正式链路入口仍是 `app/agent/graph.py`。

## 项目结构

```text
app/
├── main.py                     # 当前占位脚本，尚未完成正式 FastAPI 应用入口
├── agent/
│   ├── graph.py                # LangGraph StateGraph 编排与条件边
│   ├── llm.py                  # LLM 客户端初始化
│   ├── state.py                # DataAgentState: 节点状态定义
│   ├── context.py              # DataAgentContext: 共享上下文定义
│   └── nodes/
│       ├── extract_keywords.py
│       ├── recall_column.py
│       ├── recall_value.py
│       ├── recall_metric.py
│       ├── merge_retrieved_info.py
│       ├── filter_table.py
│       ├── filter_metric.py
│       ├── add_extra_context.py
│       ├── generate_sql.py
│       ├── validate_sql.py
│       ├── correct_sql.py
│       └── run_sql.py
├── config/
│   ├── app_config.py           # 配置加载器
│   └── meta_config.py          # 元配置加载器
├── entities/
│   ├── table_info_entity.py
│   ├── column_info_entity.py
│   ├── metric_info_entity.py
│   ├── column_metric_entity.py
│   └── value_info_entity.py
├── logger/
│   └── logger.py
├── manager/
│   ├── mysql_manager.py
│   ├── es_manager.py
│   ├── qdrant_manager.py
│   └── embedding_manager.py
├── middleware/
│   └── request_id.py
├── models/
│   ├── base_model.py
│   ├── table_info_model.py
│   ├── column_info_model.py
│   ├── metric_info_model.py
│   └── column_metric_model.py
├── prompt/
│   └── loader.py
├── repositories/
│   ├── mysql/
│   │   ├── base_repository.py
│   │   ├── meta/
│   │   │   ├── meta_repository.py
│   │   │   └── mappers/
│   │   └── dw/
│   │       └── dw_repository.py
│   ├── es/
│   │   └── value_repository.py
│   └── qdrant/
│       ├── base_repository.py
│       ├── column_repository.py
│       └── metric_repository.py
├── services/
│   └── meta_knowledge_service.py
├── scripts/
│   └── build_meta_knowledge.py
└── __init__.py

config/
├── app_config.yaml
└── meta_config.yaml

docker/
├── docker-compose.yaml
├── mysql/
│   ├── meta.sql
│   └── dw.sql
├── elasticsearch/
│   ├── Dockerfile
│   └── plugins/
└── embedding/
    └── bge-large-zh-v1.5/

prompts/
├── correct_sql.prompt
├── extend_keywords_for_column_recall.prompt
├── extend_keywords_for_metric_recall.prompt
├── extend_keywords_for_value_recall.prompt
├── filter_metric_info.prompt
├── filter_table_info.prompt
├── generate_sql.prompt
└── ...

logs/
```

## 核心执行流程

`app/agent/graph.py` 中的链路是项目的核心：

1. `extract_keywords`：关键词抽取
2. `recall_column` / `recall_value` / `recall_metric`：三路召回
3. `merge_retrieved_info`：信息合并
4. `filter_table` / `filter_metric`：双路过滤
5. `add_extra_context`：补充上下文
6. `generate_sql`：生成 SQL
7. `validate_sql`：校验 SQL
8. `correct_sql`：修正 SQL
9. `run_sql`：执行 SQL

其中：

- `generate_sql` 与 `correct_sql` 使用 `PromptTemplate + llm + StrOutputParser`
- `validate_sql` 会使用 `dw_mysql_repository.validate(sql)` 做合法性检查
- `run_sql` 会调用 `dw_mysql_repository.run(sql)` 执行最终语句

## 配置管理规范

### `.env` 文件

项目根目录中的 `.env` 是运行前必须准备的文件：

```bash
cp .env.example .env
```

示例环境变量：

```bash
MYSQL_ROOT_PASSWORD=
MYSQL_USER=genn
MYSQL_PASSWORD=
LLM_API_KEY=
```

### YAML 配置

配置文件位于：

- [config/app_config.yaml](config/app_config.yaml)
- [config/meta_config.yaml](config/meta_config.yaml)

配置通过 OmegaConf 处理，支持 `${oc.env:VAR}` 语法注入环境变量。

### 关键配置规则

- `MYSQL_USER` 必须为 `genn`
- 这是因为 `docker/mysql/*.sql` 初始化脚本中写死了 `GRANT ... TO 'genn'@'%'`
- 如果不保持该值，应用后续连接 MySQL 时会出现权限问题
- `app/config` 路径不能改动，否则本地加载 `.env` 与配置文件会失效

## Docker 服务编排

启动方式：

```bash
docker compose --env-file .env -f docker/docker-compose.yaml up -d
```

停止方式：

```bash
docker compose --env-file .env -f docker/docker-compose.yaml down
```

重置数据卷：

```bash
docker compose --env-file .env -f docker/docker-compose.yaml down -v
```

服务列表：

- MySQL：元数据库 + 数据仓库
- Elasticsearch：候选值搜索
- Kibana：ES 可视化
- Qdrant：向量召回
- Embedding TEI：文本向量模型服务

## 开发工作流

### 1. 环境准备

```bash
cp .env.example .env
uv sync
```

### 2. 启动依赖服务

```bash
docker compose --env-file .env -f docker/docker-compose.yaml up -d
```

### 3. 初始化元知识库

```bash
uv run python -m app.scripts.build_meta_knowledge -c config/meta_config.yaml
```

### 4. 本地调试 Agent

```bash
uv run python -m app.agent.graph
```

该命令会构造测试上下文并以流式形式输出各节点状态。

### 5. 检查代码质量

```bash
uv run ruff check .
uv run ruff format .
```

## 变更与维护建议

- 如果新增节点，请同步更新 `app/agent/graph.py` 中的 `StateGraph` 编排
- 如果新增提示词文件，请同时在 `app/prompt/loader.py` 中补充加载逻辑
- 如果新增依赖，请更新 `pyproject.toml`，并使用 `uv sync` 同步环境
- 如果修改配置文件，优先确认 `.env` 和 `app_config.yaml` 一致性

## 结论

当前项目已经从“概念性 NL2SQL 架构”推进到“可运行的 Agent 流程骨架”，关键节点和依赖服务均已落到代码中。下一步重点应当放在：

- 完善 FastAPI 应用入口
- 测试真实 SQL 生成与校验链路
- 修正运行中的 prompt 与数据库交互细节
- 逐步补全实际查询对接逻辑

这两份说明文件是项目的维护入口，后续新增功能时应同步更新。
