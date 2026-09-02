"""MetricInfoEntity 实体的数据映射器。

负责 MetricInfoEntity 实体（entities.metric_info.MetricInfo）与
数据库模型（models.metric_info_model.MetricInfoModel）之间的相互转换。

- to_entity: 将 MetricInfoModel 转换为业务实体 MetricInfoEntity
- to_model:  将实体 MetricInfoEntity 转换为 MetricInfoModel（通过 asdict 展开字段）
"""

from dataclasses import asdict
from typing import cast

from app.entities.metric_info_entity import MetricInfoEntity
from app.models.metric_info_model import MetricInfoModel


class MetricInfoMapper:
    @staticmethod
    def to_entity(model: MetricInfoModel) -> MetricInfoEntity:
        return MetricInfoEntity(
            id=model.id,
            name=model.name,
            description=model.description,
            relevant_columns=cast(list[str], model.relevant_columns),
            alias=cast(list[str], model.alias),
        )

    @staticmethod
    def to_model(entity: MetricInfoEntity) -> MetricInfoModel:
        return MetricInfoModel(**asdict(entity))
