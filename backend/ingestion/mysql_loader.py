# ingestion/mysql_loader.py
from __future__ import annotations

from typing import Any

from ingestion.base_loader import BaseLoader, LoaderError, SourceAuthenticationError, SourceConnectionError, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.MYSQL)
class MysqlLoader(BaseLoader):
    source_type = SourceType.MYSQL

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        host: str = source_config.get("host", "localhost")
        port: int = source_config.get("port", 3306)
        database: str = source_config["database"]
        username: str = source_config["username"]
        password: str = source_config.get("password", "")
        query: str = source_config["query"]
        id_column: str | None = source_config.get("id_column")
        text_columns: list[str] = source_config.get("text_columns", [])
        timeout: float = source_config.get("timeout", 30.0)

        try:
            import asyncmy
        except ImportError as exc:
            raise LoaderError("asyncmy is not installed; run: pip install asyncmy", source_type=self.source_type.value) from exc

        try:
            conn = await asyncmy.connect(host=host, port=port, db=database, user=username, password=password, connect_timeout=timeout)
        except asyncmy.errors.OperationalError as exc:
            message = str(exc)
            if "Access denied" in message:
                raise SourceAuthenticationError(message, source_type=self.source_type.value) from exc
            raise SourceConnectionError(message, source_type=self.source_type.value) from exc

        try:
            async with conn.cursor(asyncmy.cursors.DictCursor) as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()
        finally:
            conn.close()

        if not rows:
            return []

        columns = list(rows[0].keys())
        documents: list[dict[str, Any]] = []

        for index, row in enumerate(rows):
            target_cols = text_columns if text_columns else columns
            row_text = "\n".join(
                f"{col}: {row[col]}" for col in target_cols if col in row and row[col] is not None
            )
            if not row_text:
                continue
            source_id = str(row.get(id_column, index)) if id_column else f"row_{index}"
            documents.append(
                self._build_document(
                    row_text,
                    metadata={
                        "source_type": self.source_type.value,
                        "host": host,
                        "database": database,
                        "row_index": index,
                        "columns": columns,
                    },
                    source_id=source_id,
                )
            )
        return documents
    