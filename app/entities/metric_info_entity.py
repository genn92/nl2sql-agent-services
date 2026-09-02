"""指标信息实体类

定义业务指标的元数据结构，包含指标名称、描述、
相关列列表以及别名信息。
用于 NL2SQL 代理理解业务语义，将用户自然语言中的指标
映射到对应的数据仓库列和聚合计算。
"""

from dataclasses import dataclass


@dataclass
class MetricInfoEntity:
    id: str
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]
