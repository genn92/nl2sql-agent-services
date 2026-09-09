"""查询服务模块。

聚合元数据库、Embedding、数仓数据库以及向量/全文检索仓储，
构造 Agent 执行所需的状态与上下文对象，并以流式 SSE 的方式
向客户端返回 SQL 生成、校验、修正与执行过程中的内容块或错误。
"""

import json

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.agent import graph
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.repositories.es.value_repository import ValueESRepository
from app.repositories.mysql.dw.dw_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_repository import MetaMySQLRepository
from app.repositories.qdrant.column_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_repository import MetricQdrantRepository


class QueryService:
    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
    ) -> None:
        self.meta_mysql_repository = meta_mysql_repository
        self.embedding_client = embedding_client
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self, query: str):
        state = DataAgentState(query=query)
        context = DataAgentContext(
            column_qdrant_repository=self.column_qdrant_repository,
            embedding_client=self.embedding_client,
            metric_qdrant_repository=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
        )

        try:
            async for chunk in graph.astream(
                input=state, context=context, stream_mode="custom"
            ):
                # SSE 要求每条消息以 data: 开头，并以两个换行符结束
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:
            error = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error, ensure_ascii=False, default=str)}\n\n"
