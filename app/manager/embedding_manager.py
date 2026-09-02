"""Embedding 模型客户端管理模块。

封装 HuggingFace 文本向量化客户端（HuggingFaceEndpointEmbeddings）
的创建逻辑，并提供全局单例 `embedding_manager`，
供应用其他模块统一使用。
"""

from config.app_config import EmbeddingModelConfig, app_config
from langchain_huggingface import HuggingFaceEndpointEmbeddings


class EmbeddingManager:
    def __init__(self, config: EmbeddingModelConfig):
        self.config = config
        self.client: HuggingFaceEndpointEmbeddings | None = None

    def _get_url(self) -> str:
        """获取配置的Embedding模型地址"""
        return f"http://{self.config.host}:{self.config.port}"

    def init(self) -> None:
        """创建Embedding实例"""
        self.client = HuggingFaceEndpointEmbeddings(model=self._get_url())


# 创建Embedding管理对象
embedding_manager: EmbeddingManager = EmbeddingManager(app_config.embedding)

if __name__ == "__main__":
    try:
        embedding_manager.init()
    except Exception as e:
        print("Embedding模型初始化失败", e)
