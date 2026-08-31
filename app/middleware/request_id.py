"""请求 ID 中间件。

为每个 HTTP 请求生成或透传 request_id，并通过 ContextVar 注入到 loguru
日志上下文，使整个请求链路内的日志自动带上该 ID（无需手动 logger.bind）；
同时在响应头 X-Request-ID 中回传给客户端，便于前后端对齐排查。
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logger.logger import logger, request_id_var

HEADER_NAME = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """透传/生成 request_id，并绑定到日志上下文。"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # 优先透传客户端传入的 ID，方便与服务端日志对齐
        request_id = request.headers.get(HEADER_NAME) or uuid.uuid4().hex
        request.state.request_id = request_id

        token = request_id_var.set(request_id)
        logger.info("开始处理请求 method={} path={}", request.method, request.url.path)
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            logger.exception("请求处理异常 path={} error={}", request.url.path, exc)
            raise
        else:
            response.headers[HEADER_NAME] = request_id
            logger.info(
                "请求处理完成 status={} path={}", response.status_code, request.url.path
            )
            return response
        finally:
            request_id_var.reset(token)
