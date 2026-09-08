"""SQL 执行节点。

该模块负责在 Agent 链路的最后一步执行已生成并校验通过的 SQL
语句，并将执行结果通过 stream_writer 回传给调用方。
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.logger import logger


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """执行最终 SQL，并将执行过程和结果写入流输出。"""
    stream_writer = runtime.stream_writer
    step = "执行SQL"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        sql = state.get("sql")
        if sql is None:
            raise ValueError("执行SQL失败：状态中缺少SQL语句")

        dw_mysql_repository = runtime.context.get("dw_mysql_repository")

        result = await dw_mysql_repository.run(sql)

        logger.info(f"SQL执行结果：{result}")
        stream_writer({"type": "progress", "step": step, "status": "success"})
        stream_writer({"type": "result", "data": result})
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
