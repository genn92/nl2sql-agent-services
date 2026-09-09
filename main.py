"""应用入口模块。

负责创建 FastAPI 实例并挂载查询路由；同时通过 HTTP 中间件
为每一次请求生成唯一请求标识，便于后续链路日志与追踪。
"""

import uuid

from fastapi import FastAPI, Request

from app.api import lifespan
from app.api.routers import query_router
from app.context.request_id_var import request_id_var

# 创建FastAPI实例
app = FastAPI(lifespan=lifespan)

app.include_router(query_router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = uuid.uuid4()
    request_id_var.set(request_id)
    response = await call_next(request)

    return response
