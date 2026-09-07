"""指标信息召回节点：召回与问题语义相关的候选指标

代理图「三路并行召回」之一（extract_keywords → recall_metric），
与字段召回（recall_column）、候选值召回（recall_value）并行
执行，结果由 merge_retrieved_info 节点汇总。

召回流程：
1. 关键词扩展：将原始问题交给 LLM（extend_keywords_for_metric_recall
   提示词），识别问题的度量意图并生成概念级指标检索关键词
   （含同义词、别名与常见英文缩写），与上游抽取的关键词合并
   去重，提升指标召回率；
2. 向量检索：逐个将关键词经嵌入客户端向量化，到 Qdrant 的
   metric_info_collection 中按余弦相似度检索候选指标实体；
3. 按指标 id 去重汇总，写入状态字段 retrieved_metric_infos。

执行进度经 runtime.stream_writer 流式上报，失败时记录日志并
抛出异常中断链路。
"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent import llm
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.entities.metric_info_entity import MetricInfoEntity
from app.logger import logger
from app.prompt.loader import load_prompt


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    stream_writer = runtime.stream_writer
    step: str = "召回信息"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state.get("query", "")
        keywords = state.get("keywords", "")
        embedding_client = runtime.context.get("embedding_client")
        metric_qdrant_repository = runtime.context.get("metric_qdrant_repository")

        # 创建提示词模版
        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_metric_recall"),
            input_variables=["query"],
        )
        # 创建管道调用链
        out_parser = JsonOutputParser()
        chain = prompt | llm | out_parser

        result = await chain.ainvoke({"query": query})

        # 强化查询的关键词
        keywords = set(keywords + result)

        metric_info_map: dict[str, MetricInfoEntity] = {}

        for keyword in keywords:
            # 将查询的关键词转换成向量
            vector = await embedding_client.aembed_query(keyword)
            current_metric_infos: list[
                MetricInfoEntity
            ] = await metric_qdrant_repository.search(vector)
            for metric_info in current_metric_infos:
                if metric_info.id not in metric_info_map:
                    metric_info_map[metric_info.id] = metric_info

        # 处理之后的元指标信息
        retrieved_metric_infos: list[MetricInfoEntity] = list(metric_info_map.values())

        logger.info(f"检索到指标信息：{list(metric_info_map.keys())}")
        stream_writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_metric_infos": retrieved_metric_infos}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
