"""
column_info 数据列元信息模型

对应 mysql 库中的 column_info 表，用于存储数仓中各数据表列的元数据信息，
包括列 id、列名、数据类型、列角色（主键/外键/度量/维度）、数据示例、
列描述、列别名以及所属表 id 等。
"""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class ColumnInfoModel(BaseModel):
    __tablename__ = "column_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="列id")
    name: Mapped[str] = mapped_column(String(128), comment="列名称")
    type: Mapped[str] = mapped_column(String(64), comment="数据类型")
    role: Mapped[str] = mapped_column(
        String(64), comment="列类型(primary_key,foreign_key,measure,dimension)"
    )
    examples: Mapped[dict | list] = mapped_column(JSON, comment="数据示例")
    description: Mapped[str] = mapped_column(Text, comment="列描述")
    alias: Mapped[dict | list] = mapped_column(JSON, comment="列别名")
    table_id: Mapped[str] = mapped_column(String(64), comment="所属表id")
