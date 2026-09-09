"""表信息过滤节点模块。

本模块实现了一个 LangGraph 代理节点，负责根据用户查询从已召回的表信息中
筛选出与查询相关的表，并进一步过滤每张表中与查询相关的列。

核心功能：
    - 接收代理状态中的用户查询和已召回的表信息列表
    - 调用 LLM 分析查询与表/列的关联性
    - 返回过滤后的表信息（仅保留相关表和相关列）
    - 将过滤结果写回代理状态供后续节点使用

工作流程：
    1. 从状态中获取查询语句和表信息列表
    2. 将表信息序列化为 YAML 格式传递给 LLM
    3. LLM 返回需要保留的表名和列名映射
    4. 根据 LLM 返回结果过滤表和列
    5. 更新代理状态并发送进度通知
"""

import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, TableInfoState
from app.logger import logger
from app.prompt.loader import load_prompt


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    stream_writer = runtime.stream_writer
    step: str = "过滤表信息"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state.get("query")
        table_infos: list[TableInfoState] = state.get("table_infos", [])
        # 创建提示词模板
        prompt = PromptTemplate(
            template=load_prompt("filter_table_info"),
            input_variables=["query", "table_infos"],
        )
        # 创建调用链
        out_parser = JsonOutputParser()
        chain = prompt | llm | out_parser

        result = await chain.ainvoke(
            {
                "query": query,
                "table_infos": yaml.dump(
                    table_infos, allow_unicode=True, sort_keys=False
                ),
            }
        )

        # 过滤需要的表信息
        filtered_table_infos: list[TableInfoState] = []
        for table_info in table_infos:
            if table_info["name"] in result:
                table_info["columns"] = [
                    column_info
                    for column_info in table_info["columns"]
                    if column_info["name"] in result[table_info["name"]]
                ]
                filtered_table_infos.append(table_info)

        logger.info(
            f"过滤后的表信息：{[filtered_table_info['name'] for filtered_table_info in filtered_table_infos]}"
        )
        stream_writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": filtered_table_infos}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
