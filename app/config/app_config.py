from dataclasses import dataclass
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from omegaconf import OmegaConf


@dataclass
class DBConfig:
    """数据库配置"""

    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    """向量数据库配置"""

    host: str
    port: int
    embedding_size: int


@dataclass
class EmbeddingModelConfig:
    """Embedding模型配置"""

    host: str
    port: int
    model: str


@dataclass
class ESConfig:
    """ES配置"""

    host: str
    port: int
    index_name: str


@dataclass
class LLMConfig:
    """语言模型配置"""

    model_name: str
    api_key: str
    base_url: str


@dataclass
class AppConfig:
    """总体服务配置"""

    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingModelConfig
    es: ESConfig
    llm: LLMConfig


# 先加载 .env，再解析 OmegaConf 中的 ${oc.env:...} 插值。
load_dotenv(Path(__file__).parents[2] / ".env")

# 加载项目配置
config_context = OmegaConf.load(
    Path(__file__).parents[2] / "config" / "app_config.yaml"
)

# 生成结构化配置schema
schema = OmegaConf.structured(AppConfig)

app_config: AppConfig = cast(
    AppConfig,
    OmegaConf.to_object(OmegaConf.merge(schema, config_context)),
)

if __name__ == "__main__":
    print("项目配置:", app_config)
