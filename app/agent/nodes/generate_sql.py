"""SQL 生成节点。

该模块负责根据检索到的表信息、指标信息、时间信息和数据库上下文，
结合用户自然语言查询，调用大语言模型生成对应的 SQL 查询语句。

它是 NL2SQL Agent 流程中的关键节点之一，通常位于表/指标过滤之后，
用于将结构化上下文转换成可执行的 SQL，并将生成结果写回状态对象。
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


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    stream_writer = runtime.stream_writer
    step: str = "生成SQL"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        table_infos = state.get("table_infos")
        metric_infos = state.get("metric_infos")
        date_info = state.get("date_info")
        db_info = state.get("db_info")
        query = state.get("query")

        # 创建提示词模板
        prompt = PromptTemplate(
            template=load_prompt("generate_sql"),
            input_variables=[
                "table_infos",
                "metric_infos",
                "date_info",
                "db_info",
                "query",
            ],
        )
        # 创建调用链
        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                "table_infos": yaml.dump(
                    table_infos, allow_unicode=True, sort_keys=False
                ),
                "metric_infos": yaml.dump(
                    metric_infos, allow_unicode=True, sort_keys=False
                ),
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
                "query": query,
            }
        )

        logger.info(f"生成的SQL：{result}")
        stream_writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": result}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
