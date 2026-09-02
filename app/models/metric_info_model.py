"""
metric_info 指标元信息模型

对应 mysql 库中的 metric_info 表，用于存储数仓中业务指标的元数据信息，
包括指标 id、指标名称、指标描述、关联列信息及指标别名等。
"""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel


class MetricInfoModel(BaseModel):
    __tablename__ = "metric_info"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="指标id")
    name: Mapped[str] = mapped_column(String(128), comment="指标名称")
    description: Mapped[str] = mapped_column(Text, comment="指标描述")
    relevant_columns: Mapped[dict | list] = mapped_column(JSON, comment="关联的列")
    alias: Mapped[dict | list] = mapped_column(JSON, comment="指标别名")
