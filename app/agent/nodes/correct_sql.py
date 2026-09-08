"""SQL 修正节点。

该模块负责在 SQL 生成或校验阶段发现语法、语义或数据库适配问题时，
调用大语言模型基于表信息、指标信息、日期上下文和原始错误信息，
生成修正后的 SQL，并返回给后续执行节点继续处理。

核心职责：
- 读取当前状态中的表/指标/查询上下文和错误信息
- 构造修正提示词模板
- 通过 LLM 生成修正后的 SQL
- 将修正结果写回状态，供后续执行流程使用
"""

import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent import llm
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.logger import logger
from app.prompt.loader import load_prompt


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """根据原始 SQL 和数据库/业务上下文修正错误 SQL。

    该节点通常在 SQL 校验失败后执行，输入包含：
    - 表元信息与指标元信息
    - 日期和数据库上下文
    - 原始提问 query
    - 当前生成的 SQL 及其错误信息

    输出为修正后的 SQL，写回到状态中，确保后续的执行阶段能够继续运行。
    """
    stream_writer = runtime.stream_writer
    step: str = "修正SQL"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        table_infos = state.get("table_infos")
        metric_infos = state.get("metric_infos")
        date_info = state.get("date_info")
        db_info = state.get("db_info")
        query = state.get("query")

        sql = state.get("sql")
        sql_error = state.get("sql_error")

        # 创建提示词模板
        prompt = PromptTemplate(
            template=load_prompt("correct_sql"),
            input_variables=[
                "table_infos",
                "metric_infos",
                "date_info",
                "db_info",
                "query",
                "sql",
                "error",
            ],
        )

        # 创建调用链
        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                # 与生成节点保持一致，用 YAML 向模型提供稳定 可读的结构化上下文
                "table_infos": yaml.dump(
                    table_infos, allow_unicode=True, sort_keys=False
                ),
                "metric_infos": yaml.dump(
                    metric_infos, allow_unicode=True, sort_keys=False
                ),
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
                "query": query,
                "sql": sql,
                "error": sql_error,
            }
        )

        logger.info(f"校正后的SQL：{result}")
        stream_writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": result}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
