"""MySQL 异步数据库客户端管理模块。

基于 SQLAlchemy asyncmy 驱动封装异步引擎与会话工厂的
创建/关闭逻辑，并提供两个全局单例：`dw_manager`
（数据仓库库 dw）与 `meta_manager`（元数据库 meta），
供应用其他模块统一使用。
"""

from config.app_config import DBConfig, app_config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class MySQLManager:
    def __init__(self, config: DBConfig):
        self.config = config
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    def _get_url(self) -> str:
        """获取MySQL链接地址"""
        return f"mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}?charset=utf8mb4"

    def init(self):
        # 创建异步引擎
        self.engine = create_async_engine(
            url=self._get_url(), pool_size=10, pool_pre_ping=True
        )
        # 创建会话工厂，之后即可通过 session_factory() 创建 AsyncSession 执行事务
        self.session_factory = async_sessionmaker(
            self.engine,
            autoflush=True,  # 自动刷新
            expire_on_commit=False,  # 提交后不过期
        )

    async def close(self):
        """释放MySQL链接"""
        if self.engine is not None:
            await self.engine.dispose()


dw_mysql_manager = MySQLManager(app_config.db_dw)
meta_mysql_manager = MySQLManager(app_config.db_meta)

if __name__ == "__main__":
    try:
        meta_mysql_manager.init()
    except Exception as e:
        print("数据库连接失败:", e)
