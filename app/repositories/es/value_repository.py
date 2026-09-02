"""Elasticsearch 字段取值仓储层

负责 value_index 索引的创建、批量写入和全文检索，
将 ValueInfoEntity 实体持久化到 ES 并支持按关键词搜索。
"""

from dataclasses import asdict
from typing import Any

from elasticsearch import ApiError, AsyncElasticsearch

from app.entities.value_info_entity import ValueInfoEntity


class ValueESRepository:
    """字段取值 ES 仓储，提供索引管理、批量索引和全文检索能力。"""

    index_name = "value_index"

    def __init__(self, client: AsyncElasticsearch):
        """初始化仓储，注入 Elasticsearch 异步客户端。"""
        self.client = client

    async def ensure_index(self):
        """确保 value_index 索引存在，不存在则按 ik 分词器创建 mapping。"""
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(
                index=self.index_name,
                mappings={
                    "dynamic": False,
                    "properties": {
                        "id": {"type": "keyword"},
                        "value": {
                            "type": "text",
                            "analyzer": "ik_max_word",
                            "search_analyzer": "ik_max_word",
                        },
                        "column_id": {"type": "keyword"},
                    },
                },
            )

    async def index(
        self, value_infos: list[ValueInfoEntity], batch_size: int = 20
    ) -> dict[str, Any]:
        """批量索引字段取值到 ES，按 batch_size 分批写入并汇总结果。

        Args:
            value_infos: 待索引的 ValueInfoEntity 列表。
            batch_size: 每批 bulk 操作的条数，默认 20。

        Returns:
            包含 success、failed 和 errors 的汇总字典。
        """
        if not value_infos:
            return {"success": 0, "failed": 0, "errors": []}

        total_success = 0
        total_failed = 0
        error_details: list[dict[str, Any]] = []

        for i in range(0, len(value_infos), batch_size):
            batch_value_infos = value_infos[i : i + batch_size]
            batch_operations = []
            for value_info in batch_value_infos:
                batch_operations.append(
                    {"index": {"_index": self.index_name, "_id": value_info.id}}
                )
                batch_operations.append(asdict(value_info))
            try:
                response = await self.client.bulk(
                    operations=batch_operations, refresh="wait_for"
                )
                if response.get("errors"):
                    for item in response["items"]:
                        op = item.get("index", {})
                        if op.get("error"):
                            total_failed += 1
                            error_details.append(
                                {
                                    "id": op["_id"],
                                    "error": op["error"],
                                }
                            )
                        else:
                            total_success += 1
                else:
                    total_success += len(batch_value_infos)
            except ApiError as e:
                total_failed += len(batch_value_infos)
                error_details.append({"batch_start": i, "error": str(e)})

        return {
            "success": total_success,
            "failed": total_failed,
            "errors": error_details,
        }

    async def search(
        self, keyword: str, score_threshold: float = 0.6, limit: int = 20
    ) -> list[ValueInfoEntity]:
        """按关键词全文检索字段取值，并还原为 ValueInfoEntity 实体。

        Args:
            keyword: 搜索关键词。
            score_threshold: 最低相关性分数阈值，低于该分数的结果将被过滤。
            limit: 返回结果数量上限。

        Returns:
            匹配的 ValueInfoEntity 列表。
        """
        result = await self.client.search(
            index=self.index_name,
            query={
                "match": {
                    "value": keyword,
                }
            },
            size=limit,
            min_score=score_threshold,
        )
        return [ValueInfoEntity(**hit["_source"]) for hit in result["hits"]["hits"]]
