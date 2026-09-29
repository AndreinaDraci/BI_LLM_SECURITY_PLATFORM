"""
Agent 2 – Cube Operations Agent
Handles: Slice, Dice, Pivot
"""
from __future__ import annotations
import re
import pandas as pd
from backend.agents.base import BaseAgent
from backend.db import database as db

SYSTEM_PROMPT = """You are the Cube Operations Agent for an OLAP Business Intelligence system.
Your role is to translate Slice, Dice, and Pivot requests into DuckDB SQL.

STAR SCHEMA:
  fact_sales(order_id, order_date, year, quarter, month, month_name,
             region, country, category, subcategory, customer_segment,
             quantity, unit_price, revenue, cost, profit, profit_margin)

DIMENSION VALUES (exact strings):
  year: 2022, 2023, 2024
  quarter: 'Q1','Q2','Q3','Q4'  (ALWAYS string with Q prefix, NEVER just 4)
  region: 'North America','Europe','Asia Pacific','Latin America'
  category: 'Electronics','Furniture','Office Supplies','Clothing'
  customer_segment: 'Consumer','Corporate','Small Business','Government'

OPERATIONS:
  Slice: Filter on ONE dimension (WHERE single condition)
  Dice:  Filter on MULTIPLE dimensions (WHERE multiple conditions)
  Pivot: Use conditional aggregation (SUM(CASE WHEN ... END)) to rotate

STRICT SQL RULES:
1. Always SUM revenue, profit, quantity; AVG profit_margin for aggregates.
2. ALWAYS use ROUND(SUM(column), 2) AS alias — NEVER ROUND(SUM(column) AS alias).
3. NEVER use numbers in GROUP BY — always use column names (GROUP BY region NOT GROUP BY 1).
4. For pivot: SUM(CASE WHEN col=val THEN revenue ELSE 0 END) AS "val".
5. Return ONLY valid DuckDB SQL — no markdown, no explanation.

CORRECT EXAMPLES:
  SELECT region, ROUND(SUM(revenue), 2) AS revenue FROM fact_sales WHERE quarter='Q4' GROUP BY region
  SELECT year, ROUND(SUM(revenue), 2) AS revenue FROM fact_sales WHERE category='Electronics' GROUP BY year ORDER BY year
"""


class CubeOperationsAgent(BaseAgent):
    name = "Cube Operations"
    description = "Slice, Dice, and Pivot operations on the OLAP cube."

    def run(self, query: str, context: dict | None = None) -> dict:
        op_type = _detect_operation(query)
        ctx_str = f"\nPrevious context: {context}" if context else ""

        sql_raw = self._call_llm(
            system=SYSTEM_PROMPT,
            user=f"Operation type: {op_type}\nUser request: {query}{ctx_str}\n\nGenerate the SQL:",
        )

        sql = _extract_sql(sql_raw)

        try:
            result_df = db.query(sql)
            explanation = self._explain(query, op_type, result_df)
            return {
                "agent": self.name,
                "operation": op_type,
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
                "operation": op_type,
                "sql": sql,
                "data": [],
                "columns": [],
                "row_count": 0,
                "explanation": "",
                "error": str(e),
            }

    def _explain(self, query: str, operation: str, df: pd.DataFrame) -> str:
        if df.empty:
            return "No data matched the filter criteria."
        summary = df.head(3).to_dict("records")
        return self._call_llm(
            system="You are a BI analyst. Write 2 concise business insight sentences. No bullet points.",
            user=f"OLAP Operation: {operation}\nQuestion: {query}\nTop rows: {summary}",
        )


def _detect_operation(query: str) -> str:
    q = query.lower()
    if "pivot" in q or "as column" in q or "rotate" in q:
        return "pivot"
    keywords = ["and", "both", "filter", "where", "in", "for", "only"]
    count = sum(1 for k in keywords if k in q)
    if count >= 2:
        return "dice"
    return "slice"


def _extract_sql(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:sql)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"((?:WITH|SELECT)[\s\S]+?)(?:;?\s*$)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text
