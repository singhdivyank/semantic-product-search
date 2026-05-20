"""Utility helper functions for v1 endpoint."""

from typing import Any

from fastapi import HTTPException, status

from config.read_configs import read_vector_search
from consts import _ALLOWED_COLUMNS, _DEFAULT_COLUMNS, SQL_SEARCH_QUERY

vector_configs = read_vector_search()


def _validate_fields(requested: list[str]) -> list[str]:
    """Return whitelisted column names; raise 400 on any unknown field."""
    if not requested:
        return _DEFAULT_COLUMNS
    invalid = [f for f in requested if f not in _ALLOWED_COLUMNS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid field(s): {invalid}. Allowed: {sorted(_ALLOWED_COLUMNS)}",
        )
    cols = list(requested)
    if "parent_asin" not in cols:
        cols.insert(0, "parent_asin")
    return cols


def _build_two_stage_query(
    vector_str: str,
    columns: list[str],
    candidate_k: int,
    final_k: int,
    max_price: float | None,
    min_rating: float | None,
    only_in_stock: bool,
) -> tuple[str, dict]:
    """
    Build the two-stage SQL query using named params (no string interpolation
    of user data — SQL injection safe).

    Stage 1 CTE: HNSW Hamming scan on binary_quantize(embedding) → candidate_k rows
    Stage 2:     Cosine rerank on full embedding → final_k rows
    """
    select_cols = ", ".join(f"p.{c}" for c in columns)
    where_clauses = ["TRUE"]
    params: dict[str, Any] = {
        "query_vector": vector_str,
        "candidate_k": candidate_k,
        "final_k": final_k,
        "ef_search": vector_configs["hnsw_ef_search"],
    }

    if max_price is not None:
        where_clauses.append("p.price <= :max_price")
        params["max_price"] = max_price
    if min_rating is not None:
        where_clauses.append("p.average_rating >= :min_rating")
        params["min_rating"] = min_rating
    if only_in_stock:
        where_clauses.append("p.rating_number > 0")

    where_sql = " AND ".join(where_clauses)

    sql = SQL_SEARCH_QUERY.format(select_cols=select_cols, where_sql=where_sql)
    return sql, params
