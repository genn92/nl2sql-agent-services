"""
column_metric 列-指标关联模型

对应 mysql 库中的 column_metric 表，用于建立数据列与业务指标之间的多对多关联关系，
通过列编号（column_id）和指标编号（metric_id）联合主键唯一标识一条关联记录。
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class ColumnMetricModel(BaseModel):
    __tablename__ = "column_metric"

    column_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="列编号"
    )
    metric_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="指标编号"
    )
