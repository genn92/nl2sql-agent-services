"""ColumnInfoEntity 实体的数据映射器。

负责 ColumnInfoEntity 实体（entities.column_info.ColumnInfoEntity
数据库模型（models.column_info_model.ColumnInfoModel）之间的相互转换。

- to_entity: 将 ColumnInfoModel 转换为业务实体 ColumnInfoEntity
- to_model:  将实体 ColumnInfoEntity 转换为 ColumnInfoModel（通过 asdict 展开字段）
"""

from dataclasses import asdict

from app.entities.column_info_entity import ColumnInfoEntity
from app.models.column_info_model import ColumnInfoModel


class ColumnInfoMapper:
    @staticmethod
    def to_entity(column_info_model: ColumnInfoModel) -> ColumnInfoEntity:
        return ColumnInfoEntity(
            id=column_info_model.id,
            name=column_info_model.name,
            type=column_info_model.type,
            role=column_info_model.role,
            examples=list(column_info_model.examples)
            if column_info_model.examples
            else [],
            description=column_info_model.description,
            alias=list(column_info_model.alias) if column_info_model.alias else [],
            table_id=column_info_model.table_id,
        )

    @staticmethod
    def to_model(column_info_entity: ColumnInfoEntity) -> ColumnInfoModel:
        return ColumnInfoModel(**asdict(column_info_entity))
