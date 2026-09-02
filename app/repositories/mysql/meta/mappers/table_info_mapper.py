"""TableInfoEntity 实体的数据映射器。

负责 TableInfoEntity 实体（entities.table_info.TableInfo）与
数据库模型（models.table_info_model.TableInfoModel）之间的相互转换。

- to_entity: 将 TableInfoModel 转换为业务实体 TableInfoEntity
- to_model:  将实体 TableInfoEntity 转换为 TableInfoModel（通过 asdict 展开字段）
"""

from dataclasses import asdict

from app.entities.table_info_entity import TableInfoEntity
from app.models.table_info_model import TableInfoModel


class TableInfoMapper:
    @staticmethod
    def to_entity(table_info_mysql: TableInfoModel) -> TableInfoEntity:
        return TableInfoEntity(
            id=table_info_mysql.id,
            name=table_info_mysql.name,
            role=table_info_mysql.role,
            description=table_info_mysql.description,
        )

    @staticmethod
    def to_model(table_info: TableInfoEntity) -> TableInfoModel:
        return TableInfoModel(**asdict(table_info))
