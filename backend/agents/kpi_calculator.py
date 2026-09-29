"""
Agent 3 – KPI Calculator Agent
Handles: Year-over-Year, Month-over-Month, Profit Margins, Rankings (Top N)
"""
from __future__ import annotations
import re
import pandas as pd
from backend.agents.base import BaseAgent
from backend.db import database as db

SYSTEM_PROMPT = """You are the KPI Calculator Agent for an OLAP Business Intelligence system.
Your role is to compute business KPIs: YoY growth, MoM change, profit margins, rankings.

STAR SCHEMA:
  fact_sales(order_id, order_date, year, quarter, month, month_name,
             region, country, category, subcategory, customer_segment,
             quantity, unit_price, revenue, cost, profit, profit_margin)

KPI FORMULAS:
  YoY Growth %  = (current_year_revenue - prev_year_revenue) / prev_year_revenue * 100
  MoM Change %  = (current_month - prev_month) / prev_month * 100
  Profit Margin = profit / revenue * 100
  Top N ranking = ORDER BY metric DESC LIMIT N

DuckDB WINDOW FUNCTIONS:
  LAG(revenue) OVER (PARTITION BY region ORDER BY year)
  RANK() OVER (ORDER BY revenue DESC)

STRICT SQL RULES:
1. For YoY: use self-join or LAG window function.
2. ROUND all percentages to 2 decimal places.
3. ALWAYS use ROUND(SUM(column), 2) AS alias — NEVER ROUND(SUM(column) AS alias).
4. NEVER use numbers in GROUP BY — always use column names.
5. Label growth columns clearly: "yoy_growth_pct", "mom_change_pct".
6. Return ONLY valid DuckDB SQL — no markdown, no explanation.

CORRECT EXAMPLES:
  SELECT region, year, ROUND(SUM(revenue), 2) AS revenue FROM fact_sales GROUP BY region, year ORDER BY region, year
  SELECT region, RANK() OVER (ORDER BY SUM(revenue) DESC) AS rank, ROUND(SUM(revenue), 2) AS revenue FROM fact_sales GROUP BY region
"""


class KPICalculatorAgent(BaseAgent):
    name = "KPI Calculator"
    description = "Computes YoY growth, MoM changes, profit margins, and Top-N rankings."

    def run(self, query: str, context: dict | None = None) -> dict:
        kpi_type = _detect_kpi(query)
        ctx_str = f"\nPrevious context: {context}" if context else ""

        sql_raw = self._call_llm(
            system=SYSTEM_PROMPT,
            user=f"KPI type: {kpi_type}\nUser request: {query}{ctx_str}\n\nGenerate the SQL:",
        )

        sql = _extract_sql(sql_raw)

        try:
            result_df = db.query(sql)
            explanation = self._explain(query, kpi_type, result_df)
            return {
                "agent": self.name,
                "operation": kpi_type,
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
                "operation": kpi_type,
                "sql": sql,
                "data": [],
                "columns": [],
                "row_count": 0,
                "explanation": "",
                "error": str(e),
            }

    def _explain(self, query: str, kpi_type: str, df: pd.DataFrame) -> str:
        if df.empty:
            return "No KPI data available for this query."
        summary = df.head(5).to_dict("records")
        return self._call_llm(
            system="You are a CFO-level analyst. Provide a 2-sentence insight. Be specific about numbers. No bullet points.",
            user=f"KPI: {kpi_type}\nQuestion: {query}\nResults: {summary}",
        )


def _detect_kpi(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ["year over year", "yoy", "compare year", "2022 vs 2023", "2023 vs 2024", "annual growth", "yearly"]):
        return "yoy_growth"
    if any(k in q for k in ["month over month", "mom", "monthly trend", "monthly change"]):
        return "mom_change"
    if any(k in q for k in ["top", "best", "worst", "ranking", "rank", "highest", "lowest"]):
        return "ranking"
    if any(k in q for k in ["margin", "profitability", "profit %"]):
        return "profit_margin"
    return "general_kpi"


def _extract_sql(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:sql)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"((?:WITH|SELECT)[\s\S]+?)(?:;?\s*$)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text
