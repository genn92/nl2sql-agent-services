"""召回信息合并节点：汇总三路召回结果并生成 SQL 生成上下文

代理图召回阶段的汇聚点（recall_column / recall_metric /
recall_value 三路并行召回 → merge_retrieved_info），将字段、
指标、候选值三类召回结果去重合并，补全关联信息后组织为供下
游生成 SQL 使用的表结构与指标上下文。

合并流程：
1. 字段去重合并：按字段 id 将三路召回的字段信息汇总为字典；
2. 补齐指标依赖字段：遍历召回指标的依赖字段，缺失的按 id 从
   元数据库补查，不存在则记日志跳过；
3. 合并候选值示例：按字段 id 归属候选值，字段缺失时从元数据
   库补查，并将示例值去重追加到字段的 examples 中；
4. 按表组织字段：以表 id 分组字段，并为每张表补充主外键字段
   （get_key_columns_by_table_id），保证关联查询所需字段齐全；
5. 生成上下文：逐表读取表元信息，连同字段、指标分别转换为
   TableInfoState / MetricInfoState，写入状态字段 table_infos
   与 metric_infos。

执行进度经 runtime.stream_writer 流式上报，任一步骤失败时记
录日志并抛出异常中断链路。
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import (
    ColumnInfoState,
    DataAgentState,
    MetricInfoState,
    TableInfoState,
)
from app.entities.column_info_entity import ColumnInfoEntity
from app.entities.metric_info_entity import MetricInfoEntity
from app.entities.value_info_entity import ValueInfoEntity
from app.logger import logger


async def merge_retrieved_info(
    state: DataAgentState, runtime: Runtime[DataAgentContext]
):
    stream_writer = runtime.stream_writer
    step: str = "合并处理多路召回的信息"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        retrieved_column_infos: list[ColumnInfoEntity] = state.get(
            "retrieved_column_infos", []
        )
        retrieved_metric_infos: list[MetricInfoEntity] = state.get(
            "retrieved_metric_infos", []
        )
        retrieved_value_infos: list[ValueInfoEntity] = state.get(
            "retrieved_value_infos", []
        )

        meta_mysql_repository = runtime.context.get("meta_mysql_repository")

        # 按照column_id合并字段信息
        retrieved_column_infos_map: dict[str, ColumnInfoEntity] = {
            retrieved_column_info.id: retrieved_column_info
            for retrieved_column_info in retrieved_column_infos
        }

        # 补齐指标依赖字段
        for retrived_metric_info in retrieved_metric_infos:
            for relevant_column in retrived_metric_info.relevant_columns:
                if relevant_column not in retrieved_column_infos_map:
                    column_info = await meta_mysql_repository.get_column_info_by_id(
                        relevant_column
                    )
                    if column_info is None:
                        logger.warning(
                            f"指标依赖字段 {relevant_column} 在元数据库中不存在，跳过"
                        )
                        continue
                    retrieved_column_infos_map[relevant_column] = column_info

        # 补充字段示例
        for retrieved_value_info in retrieved_value_infos:
            value = retrieved_value_info.value
            column_id = retrieved_value_info.column_id
            # 补充字段信息
            if column_id not in retrieved_column_infos_map:
                column_info = await meta_mysql_repository.get_column_info_by_id(
                    column_id
                )
                if column_info is None:
                    logger.warning(
                        f"字段 {column_id} 在元数据库中不存在，跳过示例值合并"
                    )
                    continue
                retrieved_column_infos_map[column_id] = column_info
            # 补充字段值示例信息
            column_info = retrieved_column_infos_map[column_id]
            if value not in column_info.examples:
                column_info.examples.append(value)

        # 按表组织字段信息
        table_to_columns_map: dict[str, list[ColumnInfoEntity]] = {}
        for column_info in retrieved_column_infos_map.values():
            table_id = column_info.table_id
            if table_id not in table_to_columns_map:
                table_to_columns_map[table_id] = []
            table_to_columns_map[table_id].append(column_info)

        # 补充主外建字段
        for table_id in table_to_columns_map.keys():
            key_columns: list[
                ColumnInfoEntity
            ] = await meta_mysql_repository.get_key_columns_by_table_id(table_id)
            column_ids = [
                column_info.id for column_info in table_to_columns_map[table_id]
            ]
            for key_column in key_columns:
                if key_column.id not in column_ids:
                    table_to_columns_map[table_id].append(key_column)

        # 生成字段表结构
        table_infos: list[TableInfoState] = []
        for table_id, column_infos in table_to_columns_map.items():
            table_info = await meta_mysql_repository.get_table_info_by_id(table_id)
            if table_info is None:
                logger.warning(f"表 {table_id} 在元数据库中不存在，跳过")
                continue
            columns = [
                ColumnInfoState(
                    name=column_info.name,
                    type=column_info.type,
                    role=column_info.role,
                    examples=column_info.examples,
                    alias=column_info.alias,
                    description=column_info.description,
                )
                for column_info in column_infos
            ]
            table_info_state = TableInfoState(
                name=table_info.name,
                description=table_info.description,
                role=table_info.role,
                columns=columns,
            )
            table_infos.append(table_info_state)

        # 生成指标上下文
        metric_infos: list[MetricInfoState] = [
            MetricInfoState(
                name=retrieved_metric_info.name,
                description=retrieved_metric_info.description,
                relevant_columns=retrieved_metric_info.relevant_columns,
                alias=retrieved_metric_info.alias,
            )
            for retrieved_metric_info in retrieved_metric_infos
        ]
        logger.info(
            f"合并后的表信息：{[table_info['name'] for table_info in table_infos]}"
        )
        logger.info(
            f"合并后的指标信息：{[metric_info['name'] for metric_info in metric_infos]}"
        )
        stream_writer({"type": "progress", "step": step, "status": "success"})
        return {
            "table_infos": table_infos,
            "metric_infos": metric_infos,
        }

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
