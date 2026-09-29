"""
Planner / Orchestrator
Understands user intent, selects agents, coordinates multi-step analysis.
"""
from __future__ import annotations
import json
import re
from typing import Any
from backend.agents.base import BaseAgent
from backend.agents.dimension_navigator import DimensionNavigatorAgent
from backend.agents.cube_operations import CubeOperationsAgent
from backend.agents.kpi_calculator import KPICalculatorAgent
from backend.agents.report_generator import ReportGeneratorAgent
from backend.agents.visualization_agent import VisualizationAgent
from backend.agents.anomaly_detection import AnomalyDetectionAgent

PLANNER_SYSTEM = """You are the Planner/Orchestrator for a multi-agent OLAP BI platform.
Your job: analyze a user's natural language question and decide which agent(s) to invoke.

AVAILABLE AGENTS:
1. "dimension_navigator" – Drill-Down & Roll-Up (Year→Quarter→Month, Region→Country, Category→Subcategory)
2. "cube_operations"     – Slice (single filter), Dice (multi-filter), Pivot (rotate view)
3. "kpi_calculator"      – YoY growth, MoM change, profit margins, Top-N rankings
4. "anomaly_detection"   – Find outliers, drops, spikes, underperformers
5. "report_generator"    – ALWAYS include last (formats final output, generates insights)
6. "visualization"       – ALWAYS include when data should be charted

OUTPUT FORMAT (strict JSON):
{
  "intent": "one sentence describing what the user wants",
  "agents": ["agent1", "agent2", ...],
  "primary_agent": "the main agent doing the analysis",
  "complexity": "simple" | "multi_step",
  "parameters": {
    "filters": {},
    "groupby": [],
    "metric": "revenue | profit | quantity | profit_margin",
    "top_n": null
  },
  "reasoning": "why these agents were selected"
}

RULES:
- Always include "report_generator" as the last agent.
- Always include "visualization" when the question involves trends or comparisons.
- For "drill into top performer by month" → use dimension_navigator then kpi_calculator.
- For "compare X vs Y" → use kpi_calculator.
- For "show only / filter to" → use cube_operations.
- For "find anomalies / what's unusual" → use anomaly_detection.
- Return ONLY valid JSON.
"""


class Planner:
    """Orchestrates multi-agent OLAP analysis."""

    def __init__(self, provider: str = "openrouter"):
        self.provider = provider
        self._base = BaseAgent(provider=provider)
        self._agents = {
            "dimension_navigator": DimensionNavigatorAgent(provider=provider),
            "cube_operations": CubeOperationsAgent(provider=provider),
            "kpi_calculator": KPICalculatorAgent(provider=provider),
            "report_generator": ReportGeneratorAgent(provider=provider),
            "visualization": VisualizationAgent(provider=provider),
            "anomaly_detection": AnomalyDetectionAgent(provider=provider),
        }

    def plan(self, query: str, history: list[dict] | None = None) -> dict:
        """Call LLM to decide which agents to invoke."""
        history_str = ""
        if history:
            recent = history[-3:]
            history_str = f"\nConversation history (last {len(recent)} turns): " + json.dumps(recent)

        raw = self._base._call_llm(
            system=PLANNER_SYSTEM,
            user=f"User query: {query}{history_str}\n\nProduce the plan JSON:",
        )

        try:
            raw = raw.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
            plan = json.loads(raw)
        except Exception:
            # Fallback plan
            plan = {
                "intent": query,
                "agents": ["cube_operations", "report_generator", "visualization"],
                "primary_agent": "cube_operations",
                "complexity": "simple",
                "parameters": {"filters": {}, "groupby": [], "metric": "revenue", "top_n": None},
                "reasoning": "Default fallback plan",
            }

        # Ensure report_generator is always last
        agents = plan.get("agents", [])
        if "report_generator" not in agents:
            agents.append("report_generator")
        if "visualization" not in agents:
            agents.append("visualization")
        # Move report_generator to last
        agents = [a for a in agents if a != "report_generator"] + ["report_generator"]
        plan["agents"] = agents
        return plan

    def execute(self, query: str, history: list[dict] | None = None) -> dict[str, Any]:
        """Full pipeline: plan → execute agents → return combined result."""
        plan = self.plan(query, history)
        agents_to_run = plan.get("agents", [])

        results: dict[str, Any] = {
            "query": query,
            "plan": plan,
            "agent_results": {},
            "final_data": [],
            "final_columns": [],
            "report": None,
            "viz_config": None,
            "anomalies": [],
            "error": None,
        }

        last_analysis_result = None

        for agent_name in agents_to_run:
            agent = self._agents.get(agent_name)
            if not agent:
                continue

            try:
                if agent_name == "report_generator":
                    result = agent.run(query, context=last_analysis_result)
                    results["report"] = result.get("report")
                elif agent_name == "visualization":
                    result = agent.run(query, context=last_analysis_result)
                    results["viz_config"] = result.get("config")
                elif agent_name == "anomaly_detection":
                    result = agent.run(query, context=last_analysis_result)
                    results["anomalies"] = result.get("anomalies", [])
                    if result.get("data"):
                        last_analysis_result = result
                        results["final_data"] = result["data"]
                        results["final_columns"] = result.get("columns", [])
                else:
                    result = agent.run(query, context=last_analysis_result)
                    if result.get("error"):
                        results["error"] = result["error"]
                    else:
                        last_analysis_result = result
                        results["final_data"] = result.get("data", [])
                        results["final_columns"] = result.get("columns", [])

                results["agent_results"][agent_name] = result

            except Exception as e:
                results["agent_results"][agent_name] = {"error": str(e)}
                results["error"] = str(e)

        return results
