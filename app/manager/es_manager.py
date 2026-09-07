"""Elasticsearch 客户端管理模块。

封装 ES 客户端的创建与关闭逻辑，并提供全局单例
`es_manager`，供应用其他模块统一使用。
"""

from elasticsearch import AsyncElasticsearch

from app.config.app_config import ESConfig, app_config


class ESManager:
    def __init__(self, config: ESConfig):
        self.config = config
        self._client: AsyncElasticsearch | None = None

    @property
    def client(self) -> AsyncElasticsearch:
        """获取ES客户端，未初始化时抛出异常"""
        if self._client is None:
            raise RuntimeError("ESManager 尚未初始化，请先调用 init()")
        return self._client

    def _get_url(self) -> str:
        """获取配置的实例地址"""
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        """创建ES客户端"""
        self._client = AsyncElasticsearch(hosts=[self._get_url()])

    async def close(self):
        """关闭ES客户端"""
        if self._client is None:
            return

        await self._client.close()


# 创建ES实例管理对象
es_manager = ESManager(app_config.es)

if __name__ == "__main__":
    try:
        es_manager.init()
    except Exception as e:
        print("ES初始化失败", e)
