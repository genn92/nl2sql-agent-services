"""字段信息召回节点：召回与问题语义相关的候选字段（列）

代理图「三路并行召回」之一（extract_keywords → recall_column），
与候选值召回（recall_value）、指标召回（recall_metric）并行
执行，结果由 merge_retrieved_info 节点汇总。

召回流程：
1. 关键词扩展：将原始问题交给 LLM（extend_keywords_for_column_recall
   提示词），推断回答该问题所必需的字段名集合，与上游抽取的
   关键词合并去重，弥补分词召回的语义盲区；
2. 向量检索：逐个将关键词经嵌入客户端向量化，到 Qdrant 的
   column_info_collection 中按余弦相似度检索候选字段实体；
3. 按字段 id 去重汇总，写入状态字段 retrieved_column_infos。

执行进度经 runtime.stream_writer 流式上报，失败时记录日志并
抛出异常中断链路。
"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent import llm
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.entities.column_info_entity import ColumnInfoEntity
from app.logger import logger
from app.prompt import load_prompt


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    stream_writer = runtime.stream_writer
    context = runtime.context
    step: str = "字段信息召回"

    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        keywords = state.get("keywords")
        query = state.get("query")
        column_qdrant_repository = context.get("column_qdrant_repository")
        embedding_client = context.get("embedding_client")

        # 创建提示词模板
        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_column_recall"),
            input_variables=["query"],
        )

        out_parser = JsonOutputParser()

        # 创建调用链
        chain = prompt | llm | out_parser
        result = await chain.ainvoke({"query": query})

        keywords = set(keywords + result)
        column_info_map: dict[str, ColumnInfoEntity] = {}

        for keyword in keywords:
            # 将关键词向量化
            vector = await embedding_client.aembed_query(keyword)

            current_column_infos: list[
                ColumnInfoEntity
            ] = await column_qdrant_repository.search(vector=vector)

            # 查找符合条件的字段并去重
            for column_info in current_column_infos:
                if column_info.id not in column_info_map:
                    column_info_map[column_info.id] = column_info

        retrieved_column_infos: list[ColumnInfoEntity] = list(column_info_map.values())

        stream_writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_column_infos": retrieved_column_infos}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
