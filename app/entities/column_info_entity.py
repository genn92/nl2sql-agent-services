"""列信息实体类

定义数据仓库中列（字段）的元数据结构，包含列的基本信息、
类型、用途角色、示例值、描述以及所属表的关联信息。
用于 NL2SQL 代理对数据仓库 schema 的理解和查询构建。
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnInfoEntity:
    id: str
    name: str
    type: str
    role: str
    examples: list[Any]
    description: str
    alias: list[str]
    table_id: str
