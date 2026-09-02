"""Qdrant 向量数据库基础仓储层。

提供针对单个 collection 的通用异步操作：
- ensure_collection_exists : 确保集合存在（不存在则按配置维度创建）
- upsert                    : 按批次写入向量点
- search                    : 按向量相似度检索（可带分值阈值）

子类需指定 collection_name，并实现 _create_entity 将 payload 还原为领域实体。
"""

from typing import Generic, TypeVar

from config.app_config import app_config
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

T = TypeVar("T")


class BaseQdrantRepository(Generic[T]):
    collection_name: str

    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def ensure_collection_exists(self):
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size, distance=Distance.COSINE
                ),
            )

    async def upsert(
        self,
        collection_ids: list[str],
        vectors: list[list[int | float]],
        payloads: list[dict],
        batch_size: int = 10,
    ):
        points: list[PointStruct] = [
            PointStruct(id=cid, vector=vector, payload=payload)
            for cid, vector, payload in zip(collection_ids, vectors, payloads)
        ]

        for i in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.collection_name, points=points[i : i + batch_size]
            )

    def _create_entity(self, payload: dict) -> T:
        raise NotImplementedError()

    async def search(
        self, vector: list[float], score_threshold: float, limit: int
    ) -> list[T]:
        result = await self.client.query_points(
            collection_name=self.collection_name,
            limit=limit,
            vector=vector,
            score_threshold=score_threshold,
        )

        return [
            self._create_entity(point.payload)
            for point in result.points
            if point.payload is not None
        ]
