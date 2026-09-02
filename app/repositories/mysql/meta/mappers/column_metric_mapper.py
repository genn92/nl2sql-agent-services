"""ColumnMetricEntity 实体的数据映射器。

负责 ColumnMetricEntity 实体（entities.column_metric.ColumnMetricEntity
数据库模型（models.column_metric_model.ColumnMetricModel）之间的相互转换。

- to_entity: 将 ColumnMetricModel 转换为业务实体 ColumnMetricEntity
- to_model:  将实体 ColumnMetricEntity 转换为 ColumnMetricModel（通过 asdict 展开字段）
"""

from dataclasses import asdict

from app.entities.column_metric_entity import ColumnMetricEntity
from app.models.column_metric_model import ColumnMetricModel


class ColumnMetricMapper:
    @staticmethod
    def to_entity(column_metric_mysql: ColumnMetricModel) -> ColumnMetricEntity:
        return ColumnMetricEntity(
            column_id=column_metric_mysql.column_id,
            metric_id=column_metric_mysql.metric_id,
        )

    @staticmethod
    def to_model(column_metric: ColumnMetricEntity) -> ColumnMetricModel:
        return ColumnMetricModel(**asdict(column_metric))
