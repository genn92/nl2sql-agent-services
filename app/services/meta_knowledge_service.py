"""
元数据知识库构建服务。

负责将配置文件（MetaConfig）中定义的元数据，同步到多个存储后端：

- MySQL（meta 库）：表和字段信息、指标信息及字段-指标关联关系
- Qdrant（向量库）：字段和指标的「名称 / 描述 / 别名」向量嵌入，供语义检索
- Elasticsearch：需要同步的字段枚举值，供搜索使用

整体流程由 build() 编排，先落 meta 库，再抽取向量、写入向量库，最后同步枚举值到搜索引擎。
"""

import uuid
from dataclasses import asdict
from pathlib import Path

from config.meta_config import MetaConfig
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf
from repositories.es.value_repository import ValueESRepository
from repositories.mysql.dw.dw_repository import DWMySQLRepository
from repositories.mysql.meta.meta_repository import MetaMySQLRepository
from repositories.qdrant.column_repository import ColumnQdrantRepository
from repositories.qdrant.metric_repository import MetricQdrantRepository

from app.entities.column_info_entity import ColumnInfoEntity
from app.entities.column_metric_entity import ColumnMetricEntity
from app.entities.metric_info_entity import MetricInfoEntity
from app.entities.table_info_entity import TableInfoEntity
from app.entities.value_info_entity import ValueInfoEntity
from app.logger.logger import logger


class MetaKnowledgeService:
    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
    ):
        """初始化服务，注入各存储后端仓库及文本嵌入客户端。"""
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository
        self.embedding_client = embedding_client

    async def _save_tables_to_meta_db(
        self, config: MetaConfig
    ) -> list[ColumnInfoEntity]:
        """将配置中的表、字段信息写入 meta 元数据库。

        表字段类型和枚举值需从数仓（dw 库）查询真实信息，最后在同一事务中写表。
        返回构建好的字段信息列表，供后续向量化使用。
        """
        table_infos: list[TableInfoEntity] = []
        column_infos: list[ColumnInfoEntity] = []

        for table in config.tables:
            table_info = TableInfoEntity(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description,
            )
            table_infos.append(table_info)

            # 字段类型属于数仓里的真实信息，这里需要在dw库中查询
            column_types = await self.dw_mysql_repository.get_column_types(
                table_name=table.name
            )

            for column in table.columns:
                column_values = await self.dw_mysql_repository.get_column_values(
                    table_name=table.name, column_name=column.name
                )
                column_info = ColumnInfoEntity(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_types[column.name],
                    role=column.role,
                    examples=column_values,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                )
                column_infos.append(column_info)

        # 执行事务和写表操作
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_table_infos(table_infos=table_infos)
            await self.meta_mysql_repository.save_column_infos(
                column_infos=column_infos
            )

        return column_infos

    def _build_embedding_points(self, entities) -> list[dict]:
        """为每个实体的「名称 / 描述 / 别名」各生成一个待嵌入向量点。

        返回包含 id、embedding_text、payload 的 point 字典列表。
        """
        points: list[dict] = []
        for entity in entities:
            payload = asdict(entity)
            points.append(
                {"id": uuid.uuid4(), "embedding_text": entity.name, "payload": payload}
            )
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": entity.description,
                    "payload": payload,
                }
            )
            for alias in entity.alias:
                points.append(
                    {
                        "id": uuid.uuid4(),
                        "embedding_text": alias,
                        "payload": payload,
                    }
                )
        return points

    async def _batch_embed(
        self, texts: list[str], batch_size: int = 20
    ) -> list[list[float]]:
        """将文本按批次调用嵌入服务，返回与输入顺序一致的向量列表。"""
        embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(batch)
            embeddings.extend(batch_embeddings)
        return embeddings

    async def _save_entities_to_qdrant(self, entities, qdrant_repository):
        """将实体（字段或指标）写入 Qdrant 向量库。

        通用流程：确保 collection 存在 -> 生成嵌入点 -> 批量嵌入 -> upsert。
        """
        await qdrant_repository.ensure_collection_exists()
        points = self._build_embedding_points(entities)
        embedding_texts = [point["embedding_text"] for point in points]
        embeddings = await self._batch_embed(embedding_texts)
        await qdrant_repository.upsert(
            collection_ids=[p["id"] for p in points],
            vectors=embeddings,
            payloads=[p["payload"] for p in points],
        )

    async def _save_value_info_to_es(
        self, meta_config: MetaConfig, column_infos: list[ColumnInfoEntity]
    ):
        """将配置中标记为 sync 的字段枚举值写入 Elasticsearch。

        仅同步 sync=True 的字段，每个字段最多取 10 万条去重值。
        """
        # 确保索引存在
        await self.value_es_repository.ensure_index()
        # 根据配置的sync字段来决定是否同步
        columns_to_sync: dict[str, bool] = {}
        for table in meta_config.tables:
            for column in table.columns:
                columns_to_sync[f"{table.name}.{column.name}"] = column.sync

        value_infos: list[ValueInfoEntity] = []
        for column_info in column_infos:
            sync = columns_to_sync.get(column_info.id, False)
            if sync:
                current_column_values = (
                    await self.dw_mysql_repository.get_column_values(
                        table_name=column_info.table_id,
                        column_name=column_info.name,
                        limit=100000,
                    )
                )
                current_value_infos = [
                    ValueInfoEntity(
                        id=f"{column_info.id}.{current_column_value}",
                        value=current_column_value,
                        column_id=column_info.id,
                    )
                    for current_column_value in current_column_values
                ]
                value_infos.extend(current_value_infos)
        # 创建索引
        await self.value_es_repository.index(value_infos=value_infos)

    async def _save_metrics_to_meta_db(self, meta_config: MetaConfig):
        """将配置中的指标信息及其关联字段写入 meta 元数据库。

        同一事务中写入指标信息和字段-指标关联关系，返回构建好的指标信息列表。
        """
        metric_infos: list[MetricInfoEntity] = []
        column_metrics: list[ColumnMetricEntity] = []

        for metric in meta_config.metrics:
            metric_info = MetricInfoEntity(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias,
            )
            metric_infos.append(metric_info)

            for column in metric.relevant_columns:
                column_metric = ColumnMetricEntity(
                    column_id=column, metric_id=metric.name
                )
                column_metrics.append(column_metric)

        # 执行事务和写表操作
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_metric_infos(
                metric_infos=metric_infos
            )
            await self.meta_mysql_repository.save_column_metrics(
                column_metrics=column_metrics
            )

        return metric_infos

    async def build(self, config_path: Path):
        """构建元数据知识库的总入口。

        加载配置文件，依次同步表和字段、指标到 meta 库与向量库，
        并将需同步的字段枚举值写入搜索引擎。
        """
        # 读取元数据仓库配置
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config = OmegaConf.to_object(OmegaConf.merge(schema, context))
        assert isinstance(meta_config, MetaConfig)

        if meta_config.tables:
            column_infos = await self._save_tables_to_meta_db(meta_config)
            logger.info(
                f"保存表和字段信息到元数据仓库成功，表数量: {len(meta_config.tables)}, 字段数量: {len(column_infos)}"
            )

            await self._save_entities_to_qdrant(
                column_infos, self.column_qdrant_repository
            )
            logger.info(f"保存字段信息到向量数据库成功，字段数量: {len(column_infos)}")

            await self._save_value_info_to_es(meta_config, column_infos)
            logger.info(f"保存字段值信息到搜索引擎成功，字段数量: {len(column_infos)}")

        if meta_config.metrics:
            metric_infos = await self._save_metrics_to_meta_db(meta_config)
            logger.info(f"保存指标信息到元数据仓库成功，指标数量: {len(metric_infos)}")

            await self._save_entities_to_qdrant(
                metric_infos, self.metric_qdrant_repository
            )
            logger.info(f"保存指标信息到向量数据库成功，指标数量: {len(metric_infos)}")
