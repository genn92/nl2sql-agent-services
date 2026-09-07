"""数据代理运行时的依赖上下文定义

采用 LangGraph 的 context_schema 模式（TypedDict）聚合代理图
各节点共享的基础设施依赖，由 app/manager 的各类管理器实例化，
在 graph.py 构建代理图时注入（StateGraph(context_schema=...)），
并在每次调用代理时以 DataAgentContext 传入。

与 DataAgentState（节点间流转的业务状态）不同，本上下文承载
的是贯穿整个请求生命周期、只读复用的能力对象：
- 元数据访问：MetaMySQLRepository 读取表、列、指标定义
- 数据查询：DWMySQLRepository 执行最终 SQL
- 语义检索：ColumnQdrantRepository / MetricQdrantRepository
  分别召回列与指标的向量候选，HuggingFaceEndpointEmbeddings
  负责生成查询文本的嵌入向量
- 值检索：ValueESRepository 召回字段候选值
"""

from typing import TypedDict

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.repositories.es.value_repository import ValueESRepository
from app.repositories.mysql.dw.dw_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_repository import MetaMySQLRepository
from app.repositories.qdrant.column_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_repository import MetricQdrantRepository


class DataAgentContext(TypedDict):
    """定义数据代理运行期间共享的基础设施依赖。"""

    column_qdrant_repository: ColumnQdrantRepository  # 用于检索列的语义向量
    embedding_client: HuggingFaceEndpointEmbeddings  # 用于生成文本嵌入向量
    metric_qdrant_repository: MetricQdrantRepository  # 用于检索指标的语义向量
    value_es_repository: ValueESRepository  # 用于检索字段候选值
    meta_mysql_repository: MetaMySQLRepository  # 用于读取表、列和指标元数据
    dw_mysql_repository: DWMySQLRepository  # 用于执行数据仓库查询
