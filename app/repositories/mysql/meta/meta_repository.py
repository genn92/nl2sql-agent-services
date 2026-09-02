"""元数据 MySQL 仓储层。

负责对 mysql 库中四张元数据表的增删改查：
- table_info    : 数据表目录
- column_info   : 数据列目录
- metric_info   : 指标目录
- column_metric : 列与指标的关联

所有方法均为异步，通过 SQLAlchemy async session 执行操作。
"""

import logging
from typing import Any, Callable, Sequence

from sqlalchemy import text

from app.entities.column_info_entity import ColumnInfoEntity
from app.entities.column_metric_entity import ColumnMetricEntity
from app.entities.metric_info_entity import MetricInfoEntity
from app.entities.table_info_entity import TableInfoEntity
from app.models.column_info_model import ColumnInfoModel
from app.models.table_info_model import TableInfoModel
from app.repositories.mysql.base_repository import BaseMySQLRepository
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper

logger = logging.getLogger(__name__)


class MetaMySQLRepository(BaseMySQLRepository):
    async def _save_entities(
        self,
        entities: Sequence,
        to_model: Callable[..., Any],
    ) -> None:
        if not entities:
            return
        for entity in entities:
            await self.session.merge(to_model(entity))

    async def save_table_infos(self, table_infos: Sequence[TableInfoEntity]) -> None:
        await self._save_entities(table_infos, TableInfoMapper.to_model)

    async def save_column_infos(self, column_infos: Sequence[ColumnInfoEntity]) -> None:
        await self._save_entities(column_infos, ColumnInfoMapper.to_model)

    async def save_metric_infos(self, metric_infos: Sequence[MetricInfoEntity]) -> None:
        await self._save_entities(metric_infos, MetricInfoMapper.to_model)

    async def save_column_metrics(
        self, column_metrics: Sequence[ColumnMetricEntity]
    ) -> None:
        await self._save_entities(column_metrics, ColumnMetricMapper.to_model)

    async def get_column_info_by_id(self, id: str) -> ColumnInfoEntity | None:
        try:
            column_info: ColumnInfoModel | None = await self.session.get(
                ColumnInfoModel, id
            )
            if column_info:
                return ColumnInfoMapper.to_entity(column_info)
            return None
        except Exception:
            logger.exception("根据 ID 查询 ColumnInfoEntity 失败: id=%s", id)
            raise

    async def get_table_info_by_id(self, id: str) -> TableInfoEntity | None:
        try:
            table_info: TableInfoModel | None = await self.session.get(
                TableInfoModel, id
            )
            if table_info:
                return TableInfoMapper.to_entity(table_info)
            return None
        except Exception:
            logger.exception("根据 ID 查询 TableInfoEntity 失败: id=%s", id)
            raise

    async def get_key_columns_by_table_id(
        self, table_id: str
    ) -> list[ColumnInfoEntity]:
        try:
            sql = (
                "select * from column_info "
                "where table_id = :table_id "
                "and role in ('primary_key','foreign_key')"
            )
            result = await self.session.execute(text(sql), {"table_id": table_id})
            return [
                ColumnInfoMapper.to_entity(ColumnInfoModel(**dict(row)))
                for row in result.mappings().fetchall()
            ]
        except Exception:
            logger.exception("根据 table_id 查询关键列失败: table_id=%s", table_id)
            raise
