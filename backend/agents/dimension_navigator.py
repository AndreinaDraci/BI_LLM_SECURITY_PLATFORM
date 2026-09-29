"""
Agent 1 – Dimension Navigator
Handles: Drill-Down, Roll-Up, Hierarchy Navigation
"""
from __future__ import annotations
import re
import pandas as pd
from backend.agents.base import BaseAgent
from backend.db import database as db

SYSTEM_PROMPT = """You are the Dimension Navigator Agent for an OLAP Business Intelligence system.
Your role is to translate natural language drill-down and roll-up requests into DuckDB SQL.

STAR SCHEMA:
  fact_sales(order_id, order_date, year, quarter, month, month_name,
             region, country, category, subcategory, customer_segment,
             quantity, unit_price, revenue, cost, profit, profit_margin)

HIERARCHIES:
  Time:      year → quarter → month_name
  Geography: region → country
  Product:   category → subcategory

DIMENSION VALUES:
  quarter: 'Q1', 'Q2', 'Q3', 'Q4'  (ALWAYS use string format with Q prefix)
  year: 2022, 2023, 2024 (integer)
  region: 'North America','Europe','Asia Pacific','Latin America'

OPERATIONS:
  Drill-Down: Group by a FINER level (e.g., year→quarter, region→country)
  Roll-Up:    Group by a COARSER level (e.g., month→quarter, country→region)

STRICT SQL RULES:
1. Always SUM revenue, profit, quantity; AVG profit_margin.
2. ALWAYS use ROUND(SUM(column), 2) AS alias — NEVER ROUND(SUM(column) AS alias).
3. ORDER BY revenue DESC or by the grouping column.
4. NEVER use numbers in GROUP BY — always use column names (GROUP BY region, year NOT GROUP BY 1, 2).
5. Return ONLY valid DuckDB SQL — no markdown, no explanation, no comments.
6. Use WHERE clauses to filter when the user specifies a dimension value.

CORRECT EXAMPLES:
  SELECT region, ROUND(SUM(revenue), 2) AS total_revenue FROM fact_sales GROUP BY region ORDER BY total_revenue DESC
  SELECT month_name, month, ROUND(SUM(revenue), 2) AS revenue FROM fact_sales WHERE quarter = 'Q4' GROUP BY month_name, month ORDER BY month
"""

class DimensionNavigatorAgent(BaseAgent):
    name = "Dimension Navigator"
    description = "Drill-Down & Roll-Up across Time, Geography, and Product hierarchies."

    def run(self, query: str, context: dict | None = None) -> dict:
        ctx_str = f"\nPrevious context: {context}" if context else ""

        sql_raw = self._call_llm(
            system=SYSTEM_PROMPT,
            user=f"User request: {query}{ctx_str}\n\nGenerate the SQL query:",
        )

        sql = _extract_sql(sql_raw)

        try:
            result_df = db.query(sql)
            explanation = self._explain(query, sql, result_df)
            return {
                "agent": self.name,
                "operation": "drill_down_roll_up",
                "sql": sql,
                "data": result_df.to_dict("records"),
                "columns": list(result_df.columns),
                "row_count": len(result_df),
                "explanation": explanation,
                "error": None,
            }
        except Exception as e:
            return {
                "agent": self.name,
                "operation": "drill_down_roll_up",
                "sql": sql,
                "data": [],
                "columns": [],
                "row_count": 0,
                "explanation": "",
                "error": str(e),
            }

    def _explain(self, query: str, sql: str, df: pd.DataFrame) -> str:
        if df.empty:
            return "No data found for this query."
        top = df.iloc[0]
        return self._call_llm(
            system="You are a BI analyst. Write a concise 2-sentence business insight. No bullet points.",
            user=f"Question: {query}\nTop result: {top.to_dict()}\nColumns: {list(df.columns)}",
        )


def _extract_sql(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:sql)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"((?:WITH|SELECT)[\s\S]+?)(?:;?\s*$)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text
