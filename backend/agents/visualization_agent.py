"""
Optional Agent 5 – Visualization Agent
Selects appropriate chart types and builds Plotly figure configs.
"""
from __future__ import annotations
import pandas as pd
import json
from backend.agents.base import BaseAgent

SYSTEM_PROMPT = """You are the Visualization Agent for a BI platform.
Given a dataset (columns + sample rows) and the analytical context,
decide the BEST chart type and return a Plotly-compatible config JSON.

OUTPUT FORMAT (strict JSON, no markdown):
{
  "chart_type": "bar" | "line" | "pie" | "scatter" | "heatmap" | "treemap",
  "title": "Chart title",
  "x_col": "column for x-axis",
  "y_col": "column for y-axis",
  "color_col": "optional grouping column or null",
  "orientation": "v" | "h",
  "rationale": "one sentence why this chart type"
}

RULES:
- Time series (year/month/quarter on x) → line chart
- Categorical comparisons → bar chart (horizontal if many categories)
- Part-of-whole (proportions) → pie chart
- Two numeric variables → scatter
- Matrix/cross-tab data → heatmap
- Hierarchical data → treemap
- Return ONLY valid JSON.
"""


class VisualizationAgent(BaseAgent):
    name = "Visualization Agent"
    description = "Selects optimal chart types and generates Plotly configurations."

    def run(self, query: str, context: dict | None = None) -> dict:
        if not context or not context.get("data"):
            return {"agent": self.name, "config": None, "error": "No data provided"}

        data = context["data"]
        columns = context.get("columns", [])
        operation = context.get("operation", "")

        df = pd.DataFrame(data)
        sample = df.head(3).to_dict("records")

        raw = self._call_llm(
            system=SYSTEM_PROMPT,
            user=f"Operation: {operation}\nQuestion: {query}\n"
                 f"Columns: {columns}\nSample rows: {json.dumps(sample)}",
        )

        try:
            import re
            raw = raw.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
            config = json.loads(raw)
        except Exception:
            config = self._fallback_config(columns, df)

        return {
            "agent": self.name,
            "config": config,
            "error": None,
        }

    def _fallback_config(self, columns: list, df: pd.DataFrame) -> dict:
        time_cols = [c for c in columns if c in ("year", "quarter", "month", "month_name")]
        num_cols = df.select_dtypes(include=["float64", "int64"]).columns.tolist()
        cat_cols = [c for c in columns if c not in num_cols]

        chart_type = "line" if time_cols else "bar"
        x_col = time_cols[0] if time_cols else (cat_cols[0] if cat_cols else columns[0])
        y_col = "revenue" if "revenue" in num_cols else (num_cols[0] if num_cols else columns[-1])

        return {
            "chart_type": chart_type,
            "title": "Analysis Results",
            "x_col": x_col,
            "y_col": y_col,
            "color_col": None,
            "orientation": "v",
            "rationale": "Default configuration",
        }
