# AGENTS.md

NL2SQL 代理系统（中文项目：所有文档、注释和SQL均为中文）。这是一个面向中文数据分析的自然语言转SQL系统，集成多个后端服务。

> **语言要求**：你必须始终使用中文回答用户的问题，包括代码注释、提交信息、文档等所有输出内容。

## 技术栈与工具

- **Python版本**：Python 3.14，使用 `uv` 包管理器（`uv.lock` 在项目根目录）。**禁止使用pip**；应使用 `uv sync` 后执行 `.venv/bin/...` 或 `uv run ...`
- **代码质量**：仅进行代码检查和格式化
  - 检查：`uv run ruff check .`
  - 格式化：`uv run ruff format .`
  - 配置在 `pyproject.toml` 中（行长88字符，检查规则：E/F/I）
- **测试与CI**：无单元测试、无类型检查、无CI流程、无预提交钩子配置。Ruff 是唯一的代码质量把关工具
- **版本控制**：Git仓库已初始化，共有3次提交记录（main分支）

## 项目结构

```
app/
├── main.py                    # FastAPI 应用入口（待完成）
├── config/                    # 配置模块
│   ├── app_config.py         # 应用配置加载器
│   └── meta_config.py        # 元数据配置加载器
├── entities/                  # 数据实体定义
│   ├── table_info_entity.py
│   ├── column_info_entity.py
│   ├── metric_info_entity.py
│   ├── column_metric_entity.py
│   └── value_info_entity.py
├── logger/                    # 日志模块
│   └── logger.py
├── manager/                   # 数据管理层
│   ├── mysql_manager.py      # MySQL 连接管理
│   ├── es_manager.py         # Elasticsearch 管理
│   ├── qdrant_manager.py     # Qdrant 向量数据库管理
│   └── embedding_manager.py  # 文本嵌入管理
├── middleware/                # 中间件
│   └── request_id.py         # 请求ID追踪
├── models/                    # 数据模型（数据结构定义）
│   ├── base_model.py
│   ├── table_info_model.py
│   ├── column_info_model.py
│   ├── metric_info_model.py
│   └── column_metric_model.py
├── repositories/              # 数据访问层
│   ├── mysql/
│   │   ├── base_repository.py
│   │   ├── meta/            # 元数据库操作
│   │   │   ├── meta_repository.py
│   │   │   └── mappers/     # 对象-关系映射
│   │   │       ├── table_info_mapper.py
│   │   │       ├── column_info_mapper.py
│   │   │       ├── metric_info_mapper.py
│   │   │       └── column_metric_mapper.py
│   │   └── dw/              # 数据仓库操作
│   │       └── dw_repository.py
│   ├── es/
│   │   └── value_repository.py
│   └── qdrant/
│       ├── base_repository.py
│       ├── column_repository.py
│       └── metric_repository.py
├── services/                  # 业务逻辑层
│   └── meta_knowledge_service.py
└── scripts/                   # 工具脚本
    └── build_meta_knowledge.py
config/                       # 配置文件目录
├── app_config.yaml          # 应用配置文件
└── meta_config.yaml         # 元数据配置文件
docker/                       # Docker 配置
├── docker-compose.yaml
├── mysql/                   # MySQL 服务配置
│   ├── meta.sql            # 元数据库 SQL 初始化脚本
│   └── dw.sql              # 数据仓库 SQL 初始化脚本
├── elasticsearch/           # Elasticsearch 配置
│   ├── Dockerfile
│   └── plugins/
└── embedding/              # 文本嵌入服务
    └── bge-large-zh-v1.5/  # 中文嵌入模型（1024维，已提交仓库）
logs/                        # 日志输出目录
```

## 配置管理

- **环境变量**：机密信息存放在项目根目录 `.env` 文件（已忽略版本控制；使用 `cp .env.example .env` 创建）
- **应用配置**：
  - `app/config/app_config.py` 通过 `Path(__file__).parents[2]` 加载 `.env` 和 `config/app_config.yaml`
  - **关键约束**：`app/config/` 目录必须保持在项目根目录下的第二级，否则配置加载路径失效
  - **严禁操作**：不可移动、重命名此目录，也不可增加嵌套层级
- **YAML配置插值**：使用 OmegaConf 格式 `${oc.env:VARS}` 进行环境变量替换
  - 支持的环境变量：`MYSQL_USER`、`MYSQL_PASSWORD`、`LLM_API_KEY`
  - 缺失的环境变量不会在加载时报错，仅在使用时触发异常

## Docker 容器编排

### 启动与停止

从项目根目录执行：

```bash
# 启动所有服务
docker compose --env-file .env -f docker/docker-compose.yaml up -d

# 停止并移除容器
docker compose --env-file .env -f docker/docker-compose.yaml down

# 停止并删除数据卷（重置数据库）
docker compose --env-file .env -f docker/docker-compose.yaml down -v
```

### MySQL 服务

- **初始化脚本**：`docker/mysql/meta.sql` 和 `dw.sql` 仅在MySQL卷首次创建时自动执行
- **重新应用Schema**：编辑SQL文件后，需执行 `down -v` 删除卷，再执行 `up -d` 重建
- **关键限制**：SQL文件中 `GRANT` 语句硬编码用户为 `genn`
  - `.env` 中的 `MYSQL_USER` **必须设置为** `genn`，否则应用无法获得访问权限
  
### Elasticsearch 服务

- 基于自定义 Dockerfile 构建（ES 8.19.10 + IK 分词插件）
- 支持自定义插件配置（`docker/elasticsearch/plugins/`）

### Kibana 服务

- ES 可视化面板，端口 5601

### 文本嵌入服务

- 使用 **TEI (Text Embeddings Inference)** CPU 镜像
- 架构固定为 `platform: linux/amd64`（Apple Silicon 上通过模拟运行）
- 模型：`bge-large-zh-v1.5`（百度开源的中文向量模型，1024维）
- 模型文件已提交至版本控制，路径 `docker/embedding/bge-large-zh-v1.5/`

## 数据库Schema

### MySQL 元数据库（`mysql`）

代理系统的元数据存储，维护数据资产目录：

| 表名 | 用途 |
|------|------|
| `table_info` | 表元信息（表名、描述、数据类型等） |
| `column_info` | 列元信息（列名、数据类型、业务含义等） |
| `metric_info` | 业务指标定义（指标名、计算逻辑、单位等） |
| `column_metric` | 列与指标的映射关系 |

### MySQL 数据仓库（`dw`）

分析数据集市，存放维度表和事实表：

| 表名 | 类型 | 用途 |
|------|------|------|
| `dim_date` | 维度表 | 日期维度 |
| `dim_region` | 维度表 | 地域维度 |
| `dim_customer` | 维度表 | 客户维度 |
| `dim_product` | 维度表 | 产品维度 |
| `fact_order` | 事实表 | 订单事实表 |

### Qdrant 向量数据库

- 存储列和指标的向量表示，支持语义搜索和相似度匹配
- HTTP 端口 6333，gRPC 端口 6334

## 核心服务模块说明

| 模块 | 职责 |
|------|------|
| **Manager** | 连接池、资源生命周期管理（MySQL、ES、Qdrant、嵌入服务） |
| **Repository** | 数据访问逻辑，抽象不同存储后端的操作接口 |
| **Model** | 数据结构定义，用于API请求/响应序列化 |
| **Entity** | 域模型，代表业务概念的核心对象 |
| **Service** | 业务逻辑编排，协调多个Repository和Manager完成功能 |
| **Mapper** | 对象映射，在数据库DTO和业务Entity间转换 |

## 开发工作流

1. **环境准备**
   ```bash
   cp .env.example .env
   # 编辑 .env，填入正确的数据库密码、LLM API密钥等
   uv sync
   ```

2. **启动基础设施**
   ```bash
   docker compose --env-file .env -f docker/docker-compose.yaml up -d
   ```

3. **验证服务健康**
   ```bash
   # 检查各服务是否就绪
   docker compose logs -f
   ```

4. **构建元知识库**
   ```bash
   uv run python -m app.scripts.build_meta_knowledge -c config/meta_config.yaml
   ```

5. **运行应用**
   ```bash
   uv run python -m app.main
   # 或通过 uvicorn
   uv run uvicorn app.main:app --reload
   ```

6. **代码质量检查**
   ```bash
   uv run ruff check .
   uv run ruff format .
   ```