"""FastAPI 应用生命周期管理模块。

在应用启动阶段依次初始化 Qdrant、Embedding、Elasticsearch、
元数据库与数仓 MySQL 等依赖服务；在应用关闭阶段执行对应的
资源清理与连接关闭，确保服务生命周期闭环。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.manager import (
    dw_mysql_manager,
    embedding_manager,
    es_manager,
    meta_mysql_manager,
    qdrant_manager,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化阶段，启动各项依赖服务
    qdrant_manager.init()
    embedding_manager.init()
    es_manager.init()
    meta_mysql_manager.init()
    dw_mysql_manager.init()

    yield

    # 服务停用，关闭各项依赖服务
    await qdrant_manager.close()
    await es_manager.close()
    await meta_mysql_manager.close()
    await dw_mysql_manager.close()
