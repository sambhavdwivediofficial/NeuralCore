# retrieval/metadata_search.py
from __future__ import annotations

import re
from typing import Any

from vector_stores.base import FilterOperator, MetadataFilter


def build_metadata_filters(filter_spec: dict[str, Any]) -> list[MetadataFilter]:
    filters: list[MetadataFilter] = []
    for field_expr, value in filter_spec.items():
        parts = field_expr.split("__", 1)
        field = parts[0]
        operator_str = parts[1] if len(parts) > 1 else "equals"
        try:
            operator = FilterOperator(operator_str)
        except ValueError:
            operator = FilterOperator.EQUALS
        filters.append(MetadataFilter(field=field, operator=operator, value=value))
    return filters


def validate_filter_spec(filter_spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    valid_operators = {op.value for op in FilterOperator}
    for field_expr in filter_spec:
        parts = field_expr.split("__", 1)
        if len(parts) == 2 and parts[1] not in valid_operators:
            errors.append(f"unknown operator '{parts[1]}' in filter '{field_expr}'")
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", parts[0]):
            errors.append(f"invalid field name '{parts[0]}' in filter '{field_expr}'")
    return errors


def apply_metadata_filters_in_memory(
    documents: list[dict[str, Any]], filters: list[MetadataFilter]
) -> list[dict[str, Any]]:
    if not filters:
        return documents

    def _matches(metadata: dict[str, Any], flt: MetadataFilter) -> bool:
        value = metadata.get(flt.field)
        op = flt.operator
        if op == FilterOperator.EQUALS:
            return value == flt.value
        if op == FilterOperator.NOT_EQUALS:
            return value != flt.value
        if op == FilterOperator.GT:
            return value is not None and value > flt.value
        if op == FilterOperator.LT:
            return value is not None and value < flt.value
        if op == FilterOperator.GTE:
            return value is not None and value >= flt.value
        if op == FilterOperator.LTE:
            return value is not None and value <= flt.value
        if op == FilterOperator.IN:
            return value in (flt.value or [])
        if op == FilterOperator.NOT_IN:
            return value not in (flt.value or [])
        if op == FilterOperator.CONTAINS:
            return value is not None and str(flt.value) in str(value)
        if op == FilterOperator.STARTS_WITH:
            return value is not None and str(value).startswith(str(flt.value))
        if op == FilterOperator.ENDS_WITH:
            return value is not None and str(value).endswith(str(flt.value))
        if op == FilterOperator.EXISTS:
            return (flt.field in metadata) == bool(flt.value)
        return True

    return [
        doc for doc in documents
        if all(_matches(doc.get("metadata", {}), flt) for flt in filters)
    ]
