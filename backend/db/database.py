"""
Database module: loads CSV into DuckDB in-memory star schema.
"""
import os
import re
import duckdb
import pandas as pd

_conn = None
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "global_retail_sales.csv")


def get_connection() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        _conn = duckdb.connect(database=":memory:")
        _init_schema(_conn)
    return _conn


def _init_schema(conn: duckdb.DuckDBPyConnection):
    csv_path = os.path.abspath(_CSV_PATH)
    conn.execute(f"CREATE TABLE raw_sales AS SELECT * FROM read_csv_auto('{csv_path}')")
    conn.execute("""
        CREATE TABLE dim_date AS
        SELECT DISTINCT order_date, year, quarter, month, month_name
        FROM raw_sales ORDER BY order_date
    """)
    conn.execute("""
        CREATE TABLE dim_geography AS
        SELECT DISTINCT region, country FROM raw_sales ORDER BY region, country
    """)
    conn.execute("""
        CREATE TABLE dim_product AS
        SELECT DISTINCT category, subcategory FROM raw_sales ORDER BY category, subcategory
    """)
    conn.execute("""
        CREATE TABLE dim_customer AS
        SELECT DISTINCT customer_segment FROM raw_sales ORDER BY customer_segment
    """)
    conn.execute("""
        CREATE TABLE fact_sales AS
        SELECT order_id, order_date, year, quarter, month, month_name,
               region, country, category, subcategory, customer_segment,
               quantity, unit_price, revenue, cost, profit, profit_margin
        FROM raw_sales
    """)
    conn.execute("DROP TABLE raw_sales")
    print("[DB] Star schema initialized")


def _fix_sql(sql: str) -> str:
    """Auto-fix common SQL errors from LLM generation."""

    # Fix 1: quarter = 4 -> quarter = 'Q4'
    sql = re.sub(
        r"quarter\s*=\s*(\d+)",
        lambda m: f"quarter = 'Q{m.group(1)}'",
        sql, flags=re.IGNORECASE
    )

    # Fix 2: ROUND(SUM(x) AS alias -> ROUND(SUM(x), 2) AS alias
    sql = re.sub(
        r"ROUND\s*\(\s*(SUM|AVG|COUNT|MIN|MAX)\s*\(([^)]+)\)\s+AS\s+",
        lambda m: f"ROUND({m.group(1)}({m.group(2)}), 2) AS ",
        sql, flags=re.IGNORECASE
    )

    # Fix 3: GROUP BY 2), region -> GROUP BY region
    def clean_group_by(match):
        clause = match.group(1)
        # Remove "digit)," at start
        clause = re.sub(r'^\s*\d+\)?,?\s*', '', clause)
        # Remove ", digit)" anywhere
        clause = re.sub(r',\s*\d+\)', '', clause)
        # Remove stray ) at start
        clause = re.sub(r'^\s*\)+\s*,?\s*', '', clause)
        clause = clause.strip().strip(',').strip()
        if clause:
            return f"GROUP BY {clause}"
        return "GROUP BY 1"

    sql = re.sub(
        r"GROUP\s+BY\s+(.*?)(?=\s*ORDER\s+BY|\s*HAVING|\s*LIMIT|\s*;|\s*$)",
        clean_group_by,
        sql,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Fix 4: Remove stray ) before ORDER BY
    sql = re.sub(r"\)+\s*ORDER\s+BY", " ORDER BY", sql, flags=re.IGNORECASE)

    return sql


def query(sql: str, skip_validation: bool = False) -> pd.DataFrame:
    """Execute a SQL query and return a DataFrame."""
    conn = get_connection()
    sql = _fix_sql(sql)

    if not skip_validation:
        try:
            from backend.security.sql_validator import validate_sql
            is_valid, message = validate_sql(sql)
            if not is_valid:
                raise ValueError(f"Security Block: {message}")
        except ImportError:
            pass

    return conn.execute(sql).df()


def get_schema_info() -> dict:
    conn = get_connection()
    info = {}
    for table in ["fact_sales", "dim_date", "dim_geography", "dim_product", "dim_customer"]:
        cols = conn.execute(f"PRAGMA table_info({table})").df()
        info[table] = cols[["name", "type"]].to_dict("records")
    return info


DDL_SCRIPTS = """
CREATE TABLE fact_sales (
    order_id VARCHAR(20) PRIMARY KEY, order_date DATE, year INTEGER,
    quarter VARCHAR(2), month INTEGER, month_name VARCHAR(20),
    region VARCHAR(50), country VARCHAR(50), category VARCHAR(50),
    subcategory VARCHAR(50), customer_segment VARCHAR(50),
    quantity INTEGER, unit_price DECIMAL(10,2), revenue DECIMAL(12,2),
    cost DECIMAL(12,2), profit DECIMAL(12,2), profit_margin DECIMAL(5,2)
);
"""
