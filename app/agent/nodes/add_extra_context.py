"""额外上下文补充节点。

为代理状态补充生成 SQL 所需的额外上下文，包括当前日期信息
（日期、星期、季度）和数据仓库的数据库信息。
"""

from datetime import date

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState, DBInfoState
from app.logger import logger


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    stream_writer = runtime.stream_writer
    step = "添加额外上下文"
    stream_writer({"type": "progress", "step": step, "status": "running"})

    try:
        dw_mysql_repository = runtime.context.get("dw_mysql_repository")

        # 日期信息
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")
        weekday = today.strftime("%A")
        quarter = f"Q{(today.month - 1) // 3 + 1}"
        date_info = DateInfoState(date=date_str, weekday=weekday, quarter=quarter)

        # 数据库信息
        db = await dw_mysql_repository.get_db_infos()
        db_info = DBInfoState(**db)
        logger.info(f"数据库信息：{db_info}")
        logger.info(f"日期信息：{date_info}")

        stream_writer({"type": "progress", "step": step, "status": "success"})
        return {"date_info": date_info, "db_info": db_info}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        stream_writer({"type": "progress", "step": step, "status": "error"})
        raise
