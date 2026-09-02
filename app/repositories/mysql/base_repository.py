from sqlalchemy.ext.asyncio import AsyncSession


class BaseMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
