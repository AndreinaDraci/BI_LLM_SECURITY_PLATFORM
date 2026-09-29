"""
Agent 4 – Report Generator Agent
Handles: Executive summaries, formatted tables, conditional formatting hints,
         follow-up question suggestions.
"""
from __future__ import annotations
import pandas as pd
from backend.agents.base import BaseAgent

SYSTEM_PROMPT = """You are the Report Generator Agent for an OLAP Business Intelligence platform.
Your role is to transform raw analytical results into polished business reports.

Given:
- The user's original question
- The OLAP operation performed
- A data summary (top rows + statistics)

You must produce a JSON object with EXACTLY these keys:
{
  "executive_summary": "2-3 sentence high-level finding for C-suite",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "formatting_hints": {
    "highlight_column": "column name to highlight",
    "highlight_condition": "top" | "bottom" | "none",
    "chart_type": "bar" | "line" | "pie" | "table",
    "chart_x": "column for x-axis",
    "chart_y": "column for y-axis (numeric)"
  },
  "follow_up_questions": [
    "Suggested follow-up question 1",
    "Suggested follow-up question 2",
    "Suggested follow-up question 3"
  ]
}

RULES:
1. Return ONLY valid JSON. No markdown, no extra text.
2. Be specific and data-driven in insights (mention actual numbers).
3. chart_type: use 'line' for time trends, 'bar' for comparisons, 'pie' for proportions.
4. follow_up_questions must be natural language business questions.
"""


class ReportGeneratorAgent(BaseAgent):
    name = "Report Generator"
    description = "Formats analytical results into executive summaries and follow-up suggestions."

    def run(self, query: str, context: dict | None = None) -> dict:
        """Generate a formatted report from analysis results."""
        if not context or "data" not in context:
            return self._empty_report()

        data = context.get("data", [])
        operation = context.get("operation", "analysis")
        columns = context.get("columns", [])
        agent_name = context.get("agent", "")

        # Build data summary for LLM
        df = pd.DataFrame(data)
        if df.empty:
            return self._empty_report()

        stats = {}
        for col in df.select_dtypes(include=["float64", "int64"]).columns:
            stats[col] = {
                "sum": round(float(df[col].sum()), 2),
                "mean": round(float(df[col].mean()), 2),
                "max": round(float(df[col].max()), 2),
                "min": round(float(df[col].min()), 2),
            }

        summary = {
            "question": query,
            "operation": operation,
            "agent": agent_name,
            "total_rows": len(df),
            "columns": columns,
            "top_5_rows": df.head(5).to_dict("records"),
            "statistics": stats,
        }

        import json
        raw = self._call_llm(
            system=SYSTEM_PROMPT,
            user=f"Analysis summary:\n{json.dumps(summary, indent=2)}",
            max_tokens=1000,
        )

        try:
            # Strip possible markdown fences
            import re
            raw = raw.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
            report = json.loads(raw)
        except Exception:
            report = {
                "executive_summary": f"Analysis completed: {len(df)} rows returned for '{query}'.",
                "key_insights": [f"Data contains {len(df)} records.", "See table for details."],
                "formatting_hints": {
                    "highlight_column": "",
                    "highlight_condition": "none",
                    "chart_type": "bar",
                    "chart_x": columns[0] if columns else "",
                    "chart_y": "revenue" if "revenue" in columns else (columns[-1] if columns else ""),
                },
                "follow_up_questions": [
                    "Can you break this down further?",
                    "What is the year-over-year growth?",
                    "Which segment performs best?",
                ],
            }

        return {
            "agent": self.name,
            "operation": "report_generation",
            "report": report,
            "error": None,
        }

    def _empty_report(self):
        return {
            "agent": self.name,
            "operation": "report_generation",
            "report": {
                "executive_summary": "No data available to generate report.",
                "key_insights": [],
                "formatting_hints": {"chart_type": "table"},
                "follow_up_questions": [],
            },
            "error": None,
        }
