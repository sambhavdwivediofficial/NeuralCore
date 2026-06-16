# ingestion/postgres_loader.py
from __future__ import annotations

from typing import Any

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.POSTGRES)
class PostgresLoader(BaseLoader):
    source_type = SourceType.POSTGRES

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        dsn: str | None = source_config.get("dsn")
        host: str = source_config.get("host", "localhost")
        port: int = source_config.get("port", 5432)
        database: str = source_config.get("database", "postgres")
        username: str = source_config.get("username", "postgres")
        password: str = source_config.get("password", "")
        query: str = source_config["query"]
        id_column: str | None = source_config.get("id_column")
        text_columns: list[str] = source_config.get("text_columns", [])
        row_as_document: bool = source_config.get("row_as_document", True)
        timeout: float = source_config.get("timeout", 30.0)

        try:
            import asyncpg
        except ImportError as exc:
            from ingestion.base_loader import LoaderError
            raise LoaderError("asyncpg is not installed", source_type=self.source_type.value) from exc

        try:
            conn = await asyncpg.connect(
                dsn=dsn or f"postgresql://{username}:{password}@{host}:{port}/{database}",
                timeout=timeout,
            )
        except asyncpg.InvalidPasswordError as exc:
            raise SourceAuthenticationError(str(exc), source_type=self.source_type.value) from exc
        except (asyncpg.PostgresConnectionError, OSError) as exc:
            raise SourceConnectionError(str(exc), source_type=self.source_type.value) from exc

        try:
            rows = await conn.fetch(query)
        finally:
            await conn.close()

        if not rows:
            return []

        columns = list(rows[0].keys())
        documents: list[dict[str, Any]] = []

        for index, row in enumerate(rows):
            row_dict = dict(row)
            target_cols = text_columns if text_columns else columns
            row_text = "\n".join(
                f"{col}: {row_dict[col]}"
                for col in target_cols
                if col in row_dict and row_dict[col] is not None
            )
            if not row_text:
                continue
            source_id = str(row_dict.get(id_column, index)) if id_column else f"row_{index}"
            documents.append(
                self._build_document(
                    row_text,
                    metadata={
                        "source_type": self.source_type.value,
                        "host": host,
                        "database": database,
                        "row_index": index,
                        "columns": columns,
                        **{f"pk_{id_column}": str(row_dict[id_column]) for id_column in ([id_column] if id_column and id_column in row_dict else [])},
                    },
                    source_id=source_id,
                )
            )
        return documents
    