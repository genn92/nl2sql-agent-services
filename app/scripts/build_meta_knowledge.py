import argparse
import asyncio
from pathlib import Path

from app.manager.embedding_manager import embedding_manager
from app.manager.es_manager import es_manager
from app.manager.mysql_manager import dw_mysql_manager, meta_mysql_manager
from app.manager.qdrant_manager import qdrant_manager
from app.repositories.es.value_repository import ValueESRepository
from app.repositories.mysql.dw.dw_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_repository import MetaMySQLRepository
from app.repositories.qdrant.column_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_repository import MetricQdrantRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


async def build_meta_knowledge(config_path: Path):
    # 初始化客户端
    meta_mysql_manager.init()
    dw_mysql_manager.init()
    qdrant_manager.init()
    es_manager.init()
    embedding_manager.init()

    meta_session_factory = meta_mysql_manager.session_factory
    dw_session_factory = dw_mysql_manager.session_factory
    assert meta_session_factory is not None
    assert dw_session_factory is not None

    qdrant_client = qdrant_manager.client
    es_client = es_manager.client
    embedding_client = embedding_manager.client
    assert qdrant_client is not None
    assert es_client is not None
    assert embedding_client is not None

    async with (
        meta_session_factory() as meta_session,
        dw_session_factory() as dw_session,
    ):
        # 创建 repository 对象
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client)
        value_es_repository = ValueESRepository(es_client)
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client)

        # 创建 service 对象，并把 repository 注入进去
        meta_knowledge_service = MetaKnowledgeService(
            meta_mysql_repository=meta_mysql_repository,
            dw_mysql_repository=dw_mysql_repository,
            column_qdrant_repository=column_qdrant_repository,
            embedding_client=embedding_client,
            value_es_repository=value_es_repository,
            metric_qdrant_repository=metric_qdrant_repository,
        )

        # 真正进入服务层的构建逻辑
        await meta_knowledge_service.build(config_path)

    # 结束后关闭客户端连接
    await meta_mysql_manager.close()
    await dw_mysql_manager.close()
    await qdrant_manager.close()
    await es_manager.close()


if __name__ == "__main__":
    # 解析命令行参数，由外部决定本次构建使用哪份配置文件
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--conf", required=True)
    args = parser.parse_args()

    # 将字符串路径转成 Path，再启动异步 build
    asyncio.run(build_meta_knowledge(Path(args.conf)))
