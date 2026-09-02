"""列与指标关联实体类

定义列（字段）与指标之间的多对多关联关系。
通过 column_id 和 metric_id 将数据仓库中的列与业务指标关联，
用于 NL2SQL 代理在生成查询时识别哪些列可用于计算特定指标。
"""

from dataclasses import dataclass


@dataclass
class ColumnMetricEntity:
    column_id: str
    metric_id: str
