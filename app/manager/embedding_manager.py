"""Embedding 模型客户端管理模块。

封装 HuggingFace 文本向量化客户端（HuggingFaceEndpointEmbeddings）
的创建逻辑，并提供全局单例 `embedding_manager`，
供应用其他模块统一使用。
"""

from huggingface_hub import AsyncInferenceClient, InferenceClient
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.config.app_config import EmbeddingModelConfig, app_config


class EmbeddingManager:
    def __init__(self, config: EmbeddingModelConfig):
        self.config = config
        self._client: HuggingFaceEndpointEmbeddings | None = None

    @property
    def client(self) -> HuggingFaceEndpointEmbeddings:
        """获取Embedding客户端，未初始化时抛出异常"""
        if self._client is None:
            raise RuntimeError("EmbeddingManager 尚未初始化，请先调用 init()")
        return self._client

    def _get_url(self) -> str:
        """获取配置的Embedding模型地址"""
        return f"http://{self.config.host}:{self.config.port}"

    def init(self) -> None:
        """创建Embedding实例"""
        # self._client = HuggingFaceEndpointEmbeddings(model=self._get_url())
        # HuggingFaceEndpointEmbeddings 的 model 参数只接受 HF repo ID，
        # 实际的推理端点 URL 需要直接注入到底层 InferenceClient 中
        self._client = HuggingFaceEndpointEmbeddings(model=self.config.model)
        endpoint_url = f"{self._get_url()}/embed"
        self._client.client = InferenceClient(model=endpoint_url)
        self._client.async_client = AsyncInferenceClient(model=endpoint_url)


# 创建Embedding管理对象
embedding_manager: EmbeddingManager = EmbeddingManager(app_config.embedding)

if __name__ == "__main__":
    try:
        embedding_manager.init()
    except Exception as e:
        print("Embedding模型初始化失败", e)
