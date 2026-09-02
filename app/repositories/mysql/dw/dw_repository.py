"""数据仓库 MySQL 仓储层。

提供对 dw 数据库的只读查询能力，包括：
- 获取表的列定义与类型信息
- 获取列的枚举值（去重）
- 获取数据库版本与方言信息
- 校验 SQL 语法合法性
- 执行只读查询并返回结果集

所有标识符（表名、列名）均通过正则白名单校验后用反引号包裹，
防止 SQL 注入；查询执行前强制校验为 SELECT 语句。
"""

import re

from sqlalchemy import text

from repositories.mysql.base_repository import BaseMySQLRepository

# 标识符白名单：仅允许字母、数字、下划线，且以字母或下划线开头
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
# 写操作关键字：用于检测 SQL 中是否包含禁止的 DML/DDL 操作
_DML_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class DWMySQLRepository(BaseMySQLRepository):
    """数据仓库 MySQL 仓储实现，提供元数据查询与只读 SQL 执行能力。"""

    @staticmethod
    def _validate_identifier(name: str) -> None:
        """校验 SQL 标识符是否合法，仅允许字母/数字/下划线。"""
        if not _IDENTIFIER_RE.match(name):
            raise ValueError(f"非法标识符: {name}")

    @staticmethod
    def _quote_identifier(name: str) -> str:
        """校验标识符合法性并用反引号包裹，返回安全的 SQL 标识符。"""
        DWMySQLRepository._validate_identifier(name)
        return f"`{name}`"

    @staticmethod
    def _validate_sql(sql: str) -> None:
        """校验 SQL 语句安全性，禁止多语句（分号）和注释开头。"""
        stripped = sql.strip()
        if ";" in stripped:
            raise ValueError("不允许执行多条语句")
        if stripped.startswith("/*"):
            raise ValueError("不允许以注释开头")

    @staticmethod
    def _validate_read_only(sql: str) -> None:
        """校验 SQL 为只读查询，必须以 SELECT 开头且不含写操作关键字。"""
        stripped = sql.strip()
        if not stripped.upper().startswith("SELECT"):
            raise ValueError("只允许执行 SELECT 查询")
        if _DML_KEYWORDS.search(stripped):
            raise ValueError("SQL 中包含禁止的写操作关键字")

    async def get_column_types(self, table_name: str):
        """查询指定表的列定义，返回 {列名: 类型} 字典。

        Args:
            table_name: 数据仓库中的表名。

        Returns:
            字典，键为列名，值为 MySQL 列类型字符串。
        """
        sql = f"SHOW COLUMNS FROM {self._quote_identifier(table_name)}"
        result = await self.session.execute(text(sql))
        dicts = result.mappings().fetchall()
        return {row["Field"]: row["Type"] for row in dicts}

    async def get_column_values(
        self, table_name: str, column_name: str, limit: int = 10
    ):
        """查询指定列的去重枚举值，用于 LLM 生成 SQL 时参考可选值。

        Args:
            table_name: 数据仓库中的表名。
            column_name: 要查询的列名。
            limit: 返回的最大行数，默认 10。

        Returns:
            列值列表。
        """
        quoted_table = self._quote_identifier(table_name)
        quoted_column = self._quote_identifier(column_name)
        sql = f"SELECT DISTINCT {quoted_column} FROM {quoted_table} LIMIT :limit"
        result = await self.session.execute(text(sql), {"limit": limit})
        return [row[0] for row in result.fetchall()]

    async def get_db_infos(self):
        """获取数据库版本与方言信息。

        Returns:
            字典，包含 dialect（数据库方言）和 version（版本号）。
        """
        sql = "SELECT version()"
        result = await self.session.execute(text(sql))
        version = result.scalar()
        dialect = self.session.bind.dialect.name
        return {"dialect": dialect, "version": version}

    async def validate(self, sql: str):
        """通过 EXPLAIN 校验 SQL 语法是否合法，不实际执行。

        Args:
            sql: 待校验的 SQL 语句。
        """
        self._validate_sql(sql)
        check_sql = f"EXPLAIN {sql}"
        await self.session.execute(text(check_sql))

    async def run(self, sql: str):
        """执行只读查询并返回结果集。

        仅允许 SELECT 语句，禁止任何写操作。

        Args:
            sql: 待执行的 SELECT SQL 语句。

        Returns:
            字典列表，每个字典对应一行结果。
        """
        self._validate_sql(sql)
        self._validate_read_only(sql)
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]
