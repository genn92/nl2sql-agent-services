"""字段取值召回节点：召回与问题语义相关的候选字段取值

代理图「三路并行召回」之一（extract_keywords → recall_value），
与字段召回（recall_column）、指标召回（recall_metric）并行
执行，结果由 merge_retrieved_info 节点汇总。

召回流程：
1. 关键词扩展：将原始问题交给 LLM（extend_keywords_for_value_recall
   提示词），从问题中识别可能出现在字段取值空间的候选（枚举
   值、业务实体、时间语义词等），与上游抽取的关键词合并去重；
2. 全文检索：逐个关键词到 Elasticsearch 的 value_index 索引中
   全文检索（IK 分词 + 相关性分值阈值），与字段/指标召回的
   向量检索路径不同，此处不经过嵌入模型；
3. 按取值 id 去重汇总，写入状态字段 retrieved_value_infos。

执行进度经 runtime.stream_writer 流式上报，失败时记录日志并
抛出异常中断链路。
"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent import llm
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.entities.value_info_entity import ValueInfoEntity
from app.logger import logger
from app.prompt.loader import load_prompt


async def recall_value(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    stream_writer = runtime.stream_writer
    step: str = "召回字段值信息"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        keywords = state.get("keywords")
        query = state.get("query")
        value_es_repository = runtime.context.get("value_es_repository")

        # 创建提示词模板
        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_value_recall"),
            input_variables=["query"],
        )
        # 创建调用链
        out_parser = JsonOutputParser()
        chain = prompt | llm | out_parser

        result = await chain.ainvoke({"query": query})

        # 强化查询关键词
        keywords = set(keywords + result)

        value_infos_map: dict[str, ValueInfoEntity] = {}
        for keyword in keywords:
            current_value_infos: list[
                ValueInfoEntity
            ] = await value_es_repository.search(keyword)
            for current_value_info in current_value_infos:
                if current_value_info.id not in value_infos_map:
                    value_infos_map[current_value_info.id] = current_value_info

        # 处理后的字段值信息
        retrieved_value_infos: list[ValueInfoEntity] = list(value_infos_map.values())

        logger.info(f"检索到字段取值：{list(value_infos_map.keys())}")
        stream_writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_value_infos": retrieved_value_infos}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
