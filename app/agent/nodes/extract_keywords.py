"""代理图入口节点：抽取用户问题中的检索关键词

作为整条链路的起点（START → extract_keywords），对用户的自然
语言问题执行关键词抽取：基于 jieba 的 TF-IDF 算法并按词性白
名单过滤，仅保留名词、地名、专有名词、动词等对检索有意义的
词，供下游「列 / 候选值 / 指标」三路并行召回节点使用。

抽取结果与原始问题合并去重后写入状态字段 keywords；执行进度
经 runtime.stream_writer 流式写出（调用方以 stream_mode="custom"
接收），失败时记录日志并抛出异常中断链路。
"""

import jieba
import jieba.analyse
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.logger.logger import logger


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    # stream_writer：向调用方流式上报本节点的执行进度（running/success/error）
    stream_writer = runtime.stream_writer
    step = "关键词拆分"
    stream_writer(
        {
            "type": "progress",
            "step": step,
            "status": "running",
        }
    )

    try:
        query = state.get("query", "")
        # 词性过滤：仅保留对元数据检索有意义的实词，剔除标点、虚词等噪声
        allow_pos = (
            "n",  # 名词: 商品、订单、销售额
            "nr",  # 人名: 张三、李四
            "ns",  # 地名: 华北、北京、上海
            "nt",  # 机构团体名: 门店、品牌、渠道
            "nz",  # 其他专有名词: SKU、GMV、AOV
            "v",  # 动词: 统计、对比、查询
            "vn",  # 名动词: 销售、成交、退款
            "a",  # 形容词: 新增、有效、活跃
            "an",  # 名形词: 可用、有效、异常
            "eng",  # 英文: GMV、SKU、ROI
            "i",  # 成语或习用语，避免遗漏整体表达
            "l",  # 常用固定短语，例如“销售总额”
        )

        # TF-IDF 关键词抽取，allowPOS 限定只有白名单词性参与抽取
        extract_tags = jieba.analyse.extract_tags(query, allowPOS=allow_pos)
        # 保留查询内容原文兜底：抽取可能丢失关键表达，合并原文后去重，
        # 确保下游召回节点始终能拿到完整语义
        keywords = list(set(extract_tags + [query]))

        stream_writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"抽取关键词成功: {keywords}")
        # 写回共享状态，交由下游召回节点读取
        return {"keywords": keywords}

    except Exception as e:
        logger.error(f"抽取关键词失败: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
