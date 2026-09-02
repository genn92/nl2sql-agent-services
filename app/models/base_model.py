"""ORM 基类模块。

提供 SQLAlchemy 声明式基类 `Base`，所有数据模型（表）均继承此类，用于集中管理元数据、统一建表与查询的声明式映射。
"""

from sqlalchemy.orm import DeclarativeBase


class BaseModel(DeclarativeBase):
    pass
