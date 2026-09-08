"""SQL 校验节点。

该模块负责检查大模型生成的 SQL 是否具备可执行性，通常通过
数据仓库中的 validate 方法验证语法与结构，并将校验错误返回到
状态中，供后续修正节点处理。
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.logger import logger


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """校验生成 SQL 的合法性，并返回校验错误信息。"""
    stream_writer = runtime.stream_writer
    step: str = "校验SQL"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        sql = state.get("sql")
        if not sql:
            raise ValueError("缺少生成的SQL语句，无法校验")
        # 验证大模型生成的SQL是否真实可用
        dw_mysql_repository = runtime.context.get("dw_mysql_repository")
        try:
            await dw_mysql_repository.validate(sql)
            stream_writer({"type": "progress", "step": step, "status": "success"})
            logger.info("SQL语法正确")
            return {"sql_error": None}
        except Exception as e:
            logger.info(f"SQL语法错误：{str(e)}")
            stream_writer({"type": "progress", "step": step, "status": "success"})
            return {"sql_error": str(e)}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
