"""Optional DuckDB analytical layer.

If the `duckdb` package is installed, Parquet tables can be queried with SQL.
Otherwise analytics fall back to Pandas (all tables are small aggregates).
"""
from __future__ import annotations

from src.config import PARQUET_DIR
from src.utils import get_logger

log = get_logger("duckdb_layer")


def available() -> bool:
    try:
        import duckdb  # noqa: F401
        return True
    except ImportError:
        return False


def query(sql: str, params=None):
    """Run SQL against the Parquet warehouse. Each table is exposed as a view."""
    if not available():
        raise RuntimeError("duckdb not installed")
    import duckdb
    import pandas as pd
    con = duckdb.connect(database=":memory:")
    for p in PARQUET_DIR.glob("*.parquet"):
        con.execute(
            f"CREATE VIEW {p.stem} AS SELECT * FROM read_parquet('{p.as_posix()}')")
    if params:
        return con.execute(sql, params).fetchdf()
    return con.execute(sql).fetchdf()
