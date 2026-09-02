from dataclasses import dataclass


@dataclass
class ColumnConfig:
    """字段配置：描述数仓表中单个字段的元数据，包含字段名、角色、语义描述、别名及是否参与同步。"""

    name: str
    role: str
    description: str
    alias: list[str]
    sync: bool


@dataclass
class TableConfig:
    """表配置：描述一张数仓表的元数据，包含表名、角色、语义描述及该表包含的所有字段列表。"""

    name: str
    role: str
    description: str
    columns: list[ColumnConfig]


@dataclass
class MetricConfig:
    """指标配置：描述一个业务指标的元数据，包含指标名、语义描述、相关字段及别名。"""

    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


@dataclass
class MetaConfig:
    """数仓全局配置：聚合所有表配置和指标配置，作为数据仓库元数据的顶层入口。"""

    tables: list[TableConfig]
    metrics: list[MetricConfig]
