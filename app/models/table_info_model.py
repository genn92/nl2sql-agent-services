"""
table_info 数据表元信息模型

对应 mysql 库中的 table_info 表，用于存储数仓中各数据表的元数据信息，
包括表 id、表名、表类型（事实表/维度表）及表描述。
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class TableInfoModel(BaseModel):
    __tablename__ = "table_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="表id")
    name: Mapped[str] = mapped_column(String(128), comment="表名称")
    role: Mapped[str] = mapped_column(String(32), comment="表类型(fact/dim)")
    description: Mapped[str] = mapped_column(Text, comment="表描述")
