"""NL2SQL 代理的全局状态定义

采用 LangGraph 惯用的 TypedDict 模式描述代理图（Agent Graph）在
各个节点间流转的共享状态。

两个层次：
1. 细粒度子状态（MetricInfoState / ColumnInfoState / TableInfoState /
   DateInfoState / DBInfoState）：面向 LLM 提示词的精简元数据视图，
   相比 app/entities 下的实体类剔除了 id、table_id 等内部主键，
   只保留生成 SQL 所需的业务语义字段。
2. 聚合主状态（DataAgentState）：代理图唯一的全局状态对象，
   串联「检索 → 过滤 → SQL 生成 → 校验/重试」的完整链路。
"""

from typing import Any, NotRequired, TypedDict

from app.entities.column_info_entity import ColumnInfoEntity
from app.entities.metric_info_entity import MetricInfoEntity
from app.entities.value_info_entity import ValueInfoEntity


class MetricInfoState(TypedDict):
    """指标的提示词视图：从检索到的指标实体中筛选、裁剪而来"""

    name: str  # 指标名称，如"销售额"
    description: str  # 指标的业务口径与计算逻辑说明
    relevant_columns: list[str]  # 指标计算涉及的数据仓库列名
    alias: list[str]  # 指标的业务别名/同义词，用于匹配用户口语化表述


class ColumnInfoState(TypedDict):
    """列的提示词视图：从检索到的列实体中筛选、裁剪而来"""

    name: str  # 列名（数据仓库中的物理字段名）
    type: str  # 列的数据类型，如 varchar、decimal
    role: str  # 列的用途角色，区分维度列/度量列
    examples: list[Any]  # 列的示例取值，帮助 LLM 理解数据的实际形态
    description: str  # 列的业务含义描述
    alias: list[str]  # 列的业务别名/同义词，用于匹配用户口语化表述


class TableInfoState(TypedDict):
    """表的提示词视图：表基础信息 + 其下相关列的嵌套集合"""

    name: str  # 表名（数据仓库中的物理表名）
    role: str  # 表的用途角色，区分维度表/事实表
    description: str  # 表的业务含义描述
    columns: list[ColumnInfoState]  # 该表下与查询相关的列信息


class DateInfoState(TypedDict):
    """日期信息：从用户查询中解析出的时间要素"""

    date: str  # 解析出的具体日期，如"2025-08-15"
    weekday: str  # 对应的星期，如"星期五"
    quarter: str  # 对应的季度，如"2025Q3"


class DBInfoState(TypedDict):
    """目标数据库信息：约束 SQL 生成所遵循的方言与语法特性"""

    dialect: str  # SQL 方言，如 MySQL
    version: str  # 数据库版本号，决定可用函数与语法特性


class DataAgentState(TypedDict):
    """代理图的全局状态：所有节点读写此对象，驱动流程流转

    字段按链路阶段分组：
    - 检索阶段：query / keywords / retrieved_*（Qdrant、ES 召回的原始实体）
    - SQL 生成与校验阶段：sql / sql_error（错误非空时触发重试回路）
    - 上下文注入阶段：metric_infos / table_infos / date_info / db_info
      （过滤后的元数据，拼装进提示词）

    除 query 外的字段均由各节点在图执行过程中逐步写回，
    初始状态只需提供 query，因此标记为 NotRequired。
    """

    query: str  # 用户查询的内容（代理的唯一必填输入）
    keywords: NotRequired[list[str]]  # 解析出的关键字，供向量检索/过滤使用
    retrieved_column_infos: NotRequired[list[ColumnInfoEntity]]  # 检索到的列信息
    retrieved_metric_infos: NotRequired[list[MetricInfoEntity]]  # 检索到的指标信息
    retrieved_value_infos: NotRequired[list[ValueInfoEntity]]  # 检索到的值信息

    sql: NotRequired[str]  # 生成的SQL语句
    sql_error: NotRequired[str]  # SQL校验错误信息（为空表示通过校验）

    metric_infos: NotRequired[list[MetricInfoState]]  # 过滤后的指标信息
    table_infos: NotRequired[list[TableInfoState]]  # 过滤后的表信息
    date_info: NotRequired[DateInfoState]  # 日期信息
    db_info: NotRequired[DBInfoState]  # 数据库信息
