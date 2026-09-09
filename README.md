# nl2sql-agent-services

这是一个基于大语言模型的中文自然语言转 SQL（NL2SQL）代理项目，目标是把用户的中文分析诉求转成准确、可执行的 SQL，并在多个后端服务之间完成语义召回、上下文补全、SQL 生成、校验、修正和执行。

当前代码已经具备“HTTP 查询 → Agent 执行 → 数据库返回结果”的完整闭环：FastAPI 提供 `POST /api/query` 流式接口，核心链路通过 LangGraph 编排，数据访问层分别连接 MySQL、Elasticsearch、Qdrant 和文本嵌入服务。

## 项目定位

该项目适合以下场景：

- 中文报表查询：如“统计华北地区销售总额”
- 数据资产检索：基于表、列、指标、候选值进行语义召回
- 自动 SQL 生成：从自然语言问题生成 SQL
- SQL 校验与修正：对 LLM 生成的 SQL 做合法性校验和修复
- 结果查询：执行生成的 SQL 并返回数据结果

## 主要能力

- 关键词抽取：基于 jieba 的中文分词和 TF-IDF 关键词提取
- 三路并行召回：列、值、指标分别做召回与匹配
- 过滤与合并：对召回结果进行过滤、归并和补全上下文
- SQL 生成：调用 LLM 生成 SQL，并将结构化元数据作为 prompt 上下文
- SQL 校验：对生成 SQL 做库内语法与结构校验
- SQL 修正：校验失败时自动修正（当前为单次修正，修正后直接执行）
- SQL 执行：调用数据仓库执行最终 SQL
- FastAPI 查询接口：以 SSE 流式返回 Agent 执行进度与查询结果

## Agent 执行流程

HTTP 请求进入后由 `QueryService` 构造状态与上下文，再交给 LangGraph 的 StateGraph 执行，完整流程如下：

```text
POST /api/query
      ↓ QueryService
extract_keywords
  ├── recall_column ──┐
  ├── recall_value ───┤
  ├── recall_metric ──┤
  └──────────────────→ merge_retrieved_info
                          ├── filter_table ──┐
                          ├── filter_metric ─┤
                          └──────────────────→ add_extra_context
                                                 ↓ generate_sql
                                                 ↓ validate_sql
                                                ├── 通过 → run_sql
                                                └── 失败 → correct_sql → run_sql
```

这条链路中，状态对象 `DataAgentState` 在节点之间流转，基础设施依赖对象 `DataAgentContext` 在节点中共享，用于访问：

- MySQL 元数据库
- MySQL 数据仓库
- Elasticsearch
- Qdrant
- 词向量嵌入模型
- LLM 模型客户端

> 当前实现中，校验失败只修正一次，修正后的 SQL 不再二次校验、直接执行；
> 多轮修正与重试仍在待完善清单中。

## 技术栈

| 类别 | 技术栈 | 说明 |
| --- | --- | --- |
| 运行环境 | Python 3.14、uv | 项目采用 uv 管理依赖，禁用 pip 直接安装 |
| LLM | LangChain、OpenAI 兼容协议 | 通过 `init_chat_model` 接入 SiliconFlow 兼容接口 |
| Agent 编排 | LangGraph | 用 StateGraph 编排多节点工作流 |
| Web 框架 | FastAPI | 提供 `POST /api/query` SSE 流式查询接口 |
| 关系数据库 | MySQL、SQLAlchemy、asyncmy | 分别管理 `meta` 与 `dw` 两套数据库 |
| 搜索引擎 | Elasticsearch + IK 分词 | 用于候选值召回与全文检索 |
| 向量库 | Qdrant | 用于列/指标的语义检索 |
| 文本嵌入 | TEI + BAAI/bge-large-zh-v1.5 | 负责中文文本向量化 |
| NLP | jieba | 做中文关键词抽取和过滤 |
| 配置 | OmegaConf、PyYAML、python-dotenv | 读取 YAML 配置和 `.env` 环境变量 |
| 日志 | loguru | 统一日志输出与请求追踪 |
| 代码质量 | Ruff | 仅使用 Ruff 做 lint 与格式化 |

## 项目结构

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── main.py                  # FastAPI 应用入口
├── app/
│   ├── agent/
│   │   ├── graph.py             # LangGraph 图编排入口
│   │   ├── llm.py               # LLM 客户端初始化
│   │   ├── state.py             # DataAgentState 状态定义
│   │   ├── context.py           # DataAgentContext 基础设施上下文
│   │   └── nodes/
│   │       ├── extract_keywords.py
│   │       ├── recall_column.py
│   │       ├── recall_value.py
│   │       ├── recall_metric.py
│   │       ├── merge_retrieved_info.py
│   │       ├── filter_table.py
│   │       ├── filter_metric.py
│   │       ├── add_extra_context.py
│   │       ├── generate_sql.py
│   │       ├── validate_sql.py
│   │       ├── correct_sql.py
│   │       └── run_sql.py
│   ├── api/
│   │   ├── dependencies.py      # FastAPI 依赖注入与仓储装配
│   │   ├── lifespan.py          # 依赖服务启动/关闭
│   │   ├── routers/query_router.py
│   │   └── schemas/query_schema.py
│   ├── config/
│   ├── context/request_id_var.py
│   ├── entities/
│   ├── logger/
│   ├── manager/
│   ├── models/
│   ├── prompt/
│   ├── repositories/
│   ├── scripts/
│   └── services/
│       ├── query_service.py
│       └── meta_knowledge_service.py
├── config/
│   ├── app_config.yaml
│   └── meta_config.yaml
├── docker/
│   ├── docker-compose.yaml
│   ├── mysql/
│   ├── elasticsearch/
│   └── embedding/
├── prompts/
├── logs/
└── .vscode/
```

## 环境准备

### 1. 创建环境变量

在项目根目录执行：

```bash
cp .env.example .env
```

随后修改 `.env`，至少补充：

```bash
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_USER=genn
MYSQL_PASSWORD=your_db_password
LLM_API_KEY=your_llm_api_key
```

说明：

- `.env` 不纳入版本控制
- `.env.example` 只提供变量模板且默认值为空，复制后必须逐项手工填写
- `app/config/app_config.py` 会先加载 `.env`，再读取 `config/app_config.yaml`
- `MYSQL_USER` 需保持为 `genn`，因为 MySQL 初始化 SQL 中的 `GRANT` 语句已写死该用户名
- `LLM_API_KEY` 会用于连接服务端 OpenAI 兼容接口

### 2. 安装依赖

```bash
uv sync
```

### 3. 启动基础设施

```bash
docker compose --env-file .env -f docker/docker-compose.yaml up -d
```

可用服务包括：

- MySQL：3306
- Elasticsearch：9200
- Kibana：5601
- Qdrant：6333 / 6334
- TEI embedding：8081

## 构建元知识库

在启动数据库和向量服务后，需要先构建元知识库，让表、列、指标和候选值进入对应数据库：

```bash
uv run python -m app.scripts.build_meta_knowledge -c config/meta_config.yaml
```

## HTTP 查询接口

正式入口为根目录 `main.py`，服务启动后通过 `POST /api/query` 提交查询：

```bash
curl -N -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "统计华北地区的销售总额"}'
```

请求体使用 [app/api/schemas/query_schema.py](app/api/schemas/query_schema.py)
中定义的 `{"query": "..."}` 结构；响应为 `text/event-stream`，按 SSE 事件下发：

- `progress`：各节点执行进度（关键词拆分、召回、过滤、SQL 生成/校验/执行等）
- `result`：最终查询结果
- `error`：链路执行过程中的异常信息（当前仍以 HTTP 200 响应）

请求级仓储与依赖由 [app/api/dependencies.py](app/api/dependencies.py) 注入，
依赖服务的启动/关闭由 [app/api/lifespan.py](app/api/lifespan.py) 统一管理。

## 本地调试

### 调试 Agent 图

项目当前提供了 `app/agent/graph.py` 的本地调试入口：

```bash
uv run python -m app.agent.graph
```

该入口会：

- 初始化 MySQL、Qdrant、ES、Embedding 等管理器
- 构造示例状态和上下文
- 使用 `stream_mode="custom"` 输出各节点的进度信息

### 调试 LLM 配置

```bash
uv run python -m app.agent.llm
```

这可以用来验证：

- `.env` 是否正确加载
- `app_config.yaml` 是否能被直接解析
- LLM 端点是否可访问

## 运行方式

```bash
uv run uvicorn main:app --reload
```

也可以使用 FastAPI 开发服务器：

```bash
uv run fastapi dev main.py
```

应用启动后会初始化 Qdrant、Embedding、Elasticsearch、meta/dw MySQL 等依赖；
`.env` 缺失或对应服务未启动时，查询阶段会返回 SSE `error` 事件。

## 代码质量检查

```bash
uv run ruff check .
uv run ruff format .
```

当前项目未配置测试框架、CI 与 pre-commit 配置，只保留 Ruff 作为代码质量门禁。

## 数据库与向量库说明

### MySQL

分为两套库：

- `meta`：存储表、列、指标和映射关系
- `dw`：存储业务数据仓库，例如 `dim_date`、`dim_region`、`dim_customer`、`dim_product`、`fact_order`

### Elasticsearch

用于候选值召回。当前索引名由
[app/repositories/es/value_repository.py](app/repositories/es/value_repository.py)
中的 `index_name = "value_index"` 常量决定；
`config/app_config.yaml` 的 `es.index_name` 字段尚未被该仓储读取。

### Qdrant

用于列和指标的向量召回，embedding size 设为 1024，collection 名称分别在
`ColumnQdrantRepository` 与 `MetricQdrantRepository` 中定义。

## 备注

1. 项目文档、注释和 SQL 说明均使用中文。
2. `app/config` 目录位置是项目约定，不能随意移动或嵌套重命名，否则配置加载路径会失效。
3. 该工程仍处于持续迭代中，主要目标是完成可落地的中文 NL2SQL 代理链路。
4. 当前已知限制：SQL 校验失败后仅修正一次且不再二次校验；元知识库重复构建时
   不会清理向量库旧数据；ES 索引配置尚未接入。

## 相关文档

- [AGENTS.md](AGENTS.md)：开发与工程约束说明
- [app/api](app/api)：FastAPI 依赖注入、路由与请求 Schema
- [config/app_config.yaml](config/app_config.yaml)：应用配置文件
- [docker/docker-compose.yaml](docker/docker-compose.yaml)：Docker 服务编排文件
- [prompts](prompts)：各节点提示词模板目录
