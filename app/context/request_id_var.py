"""请求链路上下文标识模块。

使用 ContextVar 在单次请求的上下文执行范围内保存唯一的请求标识，
避免多请求并发时日志、诊断信息与上下文状态发生串扰。
"""

import uuid
from contextvars import ContextVar

request_id_var: ContextVar[uuid.UUID | int] = ContextVar("request_id", default=999)
