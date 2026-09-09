"""查询请求 schema 模块。

定义用户向 NL2SQL 查询接口提交的自然语言问题结构，
使用 Pydantic BaseModel 约束请求体中的查询文本字段。
"""

from pydantic import BaseModel


class QuerySchema(BaseModel):
    query: str
