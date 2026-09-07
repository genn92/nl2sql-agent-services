"""Qdrant 向量数据库客户端管理模块。

封装 Qdrant 客户端的创建与关闭逻辑，并提供全局单例
`qdrant_manager`，供应用其他模块统一使用。
"""

from qdrant_client import AsyncQdrantClient

from app.config.app_config import QdrantConfig, app_config


class QdrantManager:
    def __init__(self, config: QdrantConfig):
        self.config = config
        self._client: AsyncQdrantClient | None = None

    @property
    def client(self) -> AsyncQdrantClient:
        """获取Qdrant客户端，未初始化时抛出异常"""
        if self._client is None:
            raise RuntimeError("QdrantManager 尚未初始化，请先调用 init()")
        return self._client

    def _get_url(self) -> str:
        """获取配置的Qdrant实例地址"""
        return f"http://{self.config.host}:{self.config.port}"

    def init(self) -> None:
        """创建Qdrant客户端"""
        self._client = AsyncQdrantClient(self._get_url())

    async def close(self) -> None:
        """关闭Qdrant客户端"""
        if self._client is None:
            return

        await self._client.close()


# 创建Qdrant客户端管理对象
qdrant_manager = QdrantManager(app_config.qdrant)

if __name__ == "__main__":
    try:
        qdrant_manager.init()
    except Exception as err:
        print("Qdrant初始化失败", err)
