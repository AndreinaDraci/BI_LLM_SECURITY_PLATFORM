"""
Optional Agent 6 – Anomaly Detection Agent
Identifies unusual patterns: outliers, sudden drops, unexpected spikes.
"""
from __future__ import annotations
import pandas as pd
import json
from backend.agents.base import BaseAgent
from backend.db import database as db

SYSTEM_PROMPT = """You are the Anomaly Detection Agent for a BI platform.
Your role is to identify unusual patterns in business data.

You will receive a data table. Analyze it for:
1. Revenue/profit outliers (>2 std deviations from mean)
2. Negative profit margins
3. Sudden MoM or YoY drops/spikes (>30% change)
4. Underperforming segments (bottom 10%)
5. Zero or near-zero revenue periods

OUTPUT FORMAT (strict JSON, no markdown):
{
  "anomalies": [
    {
      "type": "outlier" | "drop" | "spike" | "negative_margin" | "underperformer",
      "description": "Clear description of what was found",
      "dimension": "which column/dimension is affected",
      "value": "the anomalous value",
      "severity": "low" | "medium" | "high"
    }
  ],
  "summary": "1-2 sentence overall assessment"
}

Return ONLY valid JSON.
"""

ANOMALY_SQL = """
SELECT
    year,
    quarter,
    region,
    category,
    ROUND(SUM(revenue), 2)       AS total_revenue,
    ROUND(SUM(profit), 2)        AS total_profit,
    ROUND(AVG(profit_margin), 2) AS avg_margin,
    COUNT(*) AS transactions
FROM fact_sales
GROUP BY year, quarter, region, category
ORDER BY year, quarter, region, category
"""


class AnomalyDetectionAgent(BaseAgent):
    name = "Anomaly Detection"
    description = "Identifies unusual patterns, outliers, and unexpected changes in the data."

    def run(self, query: str, context: dict | None = None) -> dict:
        # Use provided data or fetch aggregated summary
        if context and context.get("data"):
            df = pd.DataFrame(context["data"])
        else:
            df = db.query(ANOMALY_SQL)

        stats_summary = {
            "shape": list(df.shape),
            "numeric_stats": df.describe().round(2).to_dict(),
            "sample": df.head(20).to_dict("records"),
        }

        raw = self._call_llm(
            system=SYSTEM_PROMPT,
            user=f"Question: {query}\n\nData summary:\n{json.dumps(stats_summary, indent=2)}",
            max_tokens=1200,
        )

        try:
            import re
            raw = raw.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
            result = json.loads(raw)
        except Exception:
            result = {
                "anomalies": [],
                "summary": "Could not parse anomaly results. Check the raw data manually.",
            }

        return {
            "agent": self.name,
            "operation": "anomaly_detection",
            "anomalies": result.get("anomalies", []),
            "summary": result.get("summary", ""),
            "data": df.to_dict("records"),
            "columns": list(df.columns),
            "error": None,
        }
