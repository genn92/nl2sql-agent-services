# nl2sql-agent-services

这是一个基于大语言模型的中文自然语言转 SQL（NL2SQL）代理项目，目标是把用户的中文分析诉求转成准确、可执行的 SQL，并在多个后端服务之间完成语义召回、上下文补全、SQL 生成、校验、修正和执行。

当前代码已经具备较完整的 Agent 流程骨架，核心链路通过 LangGraph 进行编排，数据访问层分别连接 MySQL、Elasticsearch、Qdrant 和文本嵌入服务。

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
- SQL 修正：在错误时自动进行修正并重试
- SQL 执行：调用数据仓库执行最终 SQL

## Agent 执行流程

当前链路由 LangGraph 的 StateGraph 组装，完整流程如下：

```text
extract_keywords
    ├── recall_column
    ├── recall_value
    ├── recall_metric
    └── merge_retrieved_info
          ├── filter_table
          ├── filter_metric
          └── add_extra_context
                 └── generate_sql
                         └── validate_sql
                              ├── run_sql     （校验通过）
                              └── correct_sql → run_sql   （校验失败）
```

这条链路中，状态对象 `DataAgentState` 在节点之间流转，基础设施依赖对象 `DataAgentContext` 在节点中共享，用于访问：

- MySQL 元数据库
- MySQL 数据仓库
- Elasticsearch
- Qdrant
- 词向量嵌入模型
- LLM 模型客户端

## 技术栈

| 类别 | 技术栈 | 说明 |
| --- | --- | --- |
| 运行环境 | Python 3.14、uv | 项目采用 uv 管理依赖，禁用 pip 直接安装 |
| LLM | LangChain、OpenAI 兼容协议 | 通过 `init_chat_model` 接入 SiliconFlow 兼容接口 |
| Agent 编排 | LangGraph | 用 StateGraph 编排多节点工作流 |
| Web 框架 | FastAPI | 当前项目已准备入口，主应用尚处于扩展阶段 |
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
├── .env
├── app/
│   ├── main.py                  # 当前为占位脚本，尚未完成正式 API 入口
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
│   ├── config/
│   │   ├── app_config.py
│   │   └── meta_config.py
│   ├── entities/
│   ├── logger/
│   ├── manager/
│   ├── middleware/
│   ├── models/
│   ├── prompt/
│   ├── repositories/
│   ├── scripts/
│   └── services/
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

### 当前状态

`app/main.py` 目前只是占位脚本，主要用于输出当前系统环境信息，不代表正式 API 服务已经完成。真正的 Agent 流程入口在 `app/agent/graph.py`。

### 未来正式启动方式

```bash
uv run uvicorn app.main:app --reload
```

如果 `app.main` 完成 FastAPI 应用初始化，再按常规方式启动即可。

## 代码质量检查

```bash
uv run ruff check .
uv run ruff format .
```

当前项目未配置测试框架、CI 和 pre-commit，只保留 Ruff 作为代码质量门禁。

## 数据库与向量库说明

### MySQL

分为两套库：

- `meta`：存储表、列、指标和映射关系
- `dw`：存储业务数据仓库，例如 `dim_date`、`dim_region`、`dim_customer`、`dim_product`、`fact_order`

### Elasticsearch

用于候选值召回，索引名由 `config/app_config.yaml` 中的 `es.index_name` 控制。

### Qdrant

用于列和指标的向量召回，embedding size 设为 1024。

## 备注

1. 项目文档、注释和 SQL 说明均使用中文。
2. `app/config` 目录位置是项目约定，不能随意移动或嵌套重命名，否则配置加载路径会失效。
3. 该工程仍处于持续迭代中，主要目标是完成可落地的中文 NL2SQL 代理链路。

## 相关文档

- [AGENTS.md](AGENTS.md)：开发与工程约束说明
- [config/app_config.yaml](config/app_config.yaml)：应用配置文件
- [docker/docker-compose.yaml](docker/docker-compose.yaml)：Docker 服务编排文件
- [prompts](prompts)：各节点提示词模板目录
