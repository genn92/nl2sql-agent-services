"""查询 API 路由模块。

提供用户自然语言查询转 SQL 执行结果的 HTTP 暴露入口，
通过请求体 schema 接收文本问题并由 QueryService 处理，
最后以流式事件流形式返回结果。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.services.query_service import QueryService

query_router = APIRouter()


@query_router.post("/api/query")
async def query_handler(
    query: QuerySchema, service: Annotated[QueryService, Depends(get_query_service)]
):
    return StreamingResponse(
        content=service.query(query.query), media_type="text/event-stream"
    )
