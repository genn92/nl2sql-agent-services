"""表信息实体类

定义数据仓库中表的元数据结构，包含表名、用途角色和描述。
用于 NL2SQL 代理在生成 SQL 查询时选择正确的数据源表，
并理解每张表在数据仓库中的业务含义。
"""

from dataclasses import dataclass


@dataclass
class TableInfoEntity:
    id: str
    name: str
    role: str
    description: str
