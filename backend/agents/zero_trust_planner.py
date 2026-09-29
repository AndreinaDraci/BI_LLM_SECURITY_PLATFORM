"""
Planner me Zero Trust të Integruar
====================================
Çdo hap i ekzekutimit kalon nëpër PEP:
1. User request → PEP check
2. Agent selection → Agent PEP check  
3. SQL generation → SQL Validator
4. Output → Output Validator
"""
from __future__ import annotations
import json
import re
import time
from typing import Any

from backend.agents.base import BaseAgent
from backend.security.policy_engine import Resource, Action
from backend.security.zero_trust_pep import zero_trust_pep, check_agent_permission
from backend.security.output_validator import output_validator
from backend.security.audit_logger import log_event

AGENT_POLICY_NAMES = {
    "dimension_navigator": "Dimension Navigator",
    "cube_operations":     "Cube Operations",
    "kpi_calculator":      "KPI Calculator",
    "report_generator":    "Report Generator",
    "visualization":       "Visualization Agent",
    "anomaly_detection":   "Anomaly Detection",
}

# Agjentët që aksesojnë DB-në (Report Generator dhe Visualization nuk e aksesojnë)
DB_AGENTS = {"dimension_navigator", "cube_operations",
             "kpi_calculator", "anomaly_detection"}


class ZeroTrustPlanner:
    """
    Planner/Orchestrator me Zero Trust të integruar.
    Çdo agjent autorizohet para aktivizimit.
    """

    PLANNER_SYSTEM = """You are the Planner/Orchestrator for a multi-agent OLAP BI platform.
Analyze the user query and decide which agents to invoke.

AVAILABLE AGENTS:
1. "dimension_navigator" - Drill-Down & Roll-Up
2. "cube_operations" - Slice, Dice, Pivot  
3. "kpi_calculator" - YoY, MoM, Top-N
4. "anomaly_detection" - Outliers, spikes
5. "report_generator" - ALWAYS last
6. "visualization" - ALWAYS include

OUTPUT (strict JSON):
{
  "intent": "one sentence",
  "agents": ["agent1", "agent2", "report_generator", "visualization"],
  "primary_agent": "main agent",
  "complexity": "simple|multi_step",
  "parameters": {"filters": {}, "groupby": [], "metric": "revenue"}
}

RULES:
- Always include report_generator last
- Always include visualization
- Return ONLY valid JSON
"""

    def __init__(self, provider: str = "anthropic", username: str = "system",
                 role: str = "viewer", token: str = ""):
        self.provider = provider
        self.username = username
        self.role = role
        self.token = token
        self._base = BaseAgent(provider=provider)

        # Importo agjentët
        from backend.agents.dimension_navigator import DimensionNavigatorAgent
        from backend.agents.cube_operations import CubeOperationsAgent
        from backend.agents.kpi_calculator import KPICalculatorAgent
        from backend.agents.report_generator import ReportGeneratorAgent
        from backend.agents.visualization_agent import VisualizationAgent
        from backend.agents.anomaly_detection import AnomalyDetectionAgent

        self._agents = {
            "dimension_navigator": DimensionNavigatorAgent(provider=provider),
            "cube_operations": CubeOperationsAgent(provider=provider),
            "kpi_calculator": KPICalculatorAgent(provider=provider),
            "report_generator": ReportGeneratorAgent(provider=provider),
            "visualization": VisualizationAgent(provider=provider),
            "anomaly_detection": AnomalyDetectionAgent(provider=provider),
        }

        # Mapa agent_name → Resource
        self._agent_resources = {
            "dimension_navigator": Resource.AGENT_DIM_NAV,
            "cube_operations": Resource.AGENT_CUBE_OPS,
            "kpi_calculator": Resource.AGENT_KPI,
            "report_generator": Resource.AGENT_REPORT,
            "visualization": Resource.AGENT_VIZ,
            "anomaly_detection": Resource.AGENT_ANOMALY,
        }

    def execute(self, query: str, history: list[dict] | None = None) -> dict[str, Any]:
        """
        Ekzekuto query me Zero Trust në çdo hap.
        """
        start_time = time.time()

        # ── Hapi 1: Zero Trust — Kontrollo aksesin e user-it ──────────────────
        zt_decision = zero_trust_pep.verify_request(
            username=self.username,
            role=self.role,
            token=self.token,
            resource=Resource.QUERY_OLAP,
            action=Action.EXECUTE,
            query_text=query,
        )

        if not zt_decision.allowed:
            log_event(
                username=self.username,
                event_type="QUERY_DENIED",
                details=f"Zero Trust bllokoi query-n: {zt_decision.reason}",
                success=False,
                risk_level=zt_decision.risk_level,
            )
            return {
                "query": query,
                "error": f"⛔ Zero Trust: {zt_decision.reason}",
                "zero_trust_denied": True,
                "final_data": [],
                "final_columns": [],
                "plan": {},
                "agent_results": {},
                "report": None,
                "viz_config": None,
                "anomalies": [],
            }

        # ── Hapi 2: Zero Trust — Kontrollo Planner agent ──────────────────────
        planner_decision = check_agent_permission(
            "Planner", "agent:coordination", "execute", self.username
        )
        if not planner_decision.allowed:
            return self._denied_result(query, planner_decision.reason)

        # ── Hapi 3: Planifiko ──────────────────────────────────────────────────
        plan = self._plan(query, history)
        agents_to_run = plan.get("agents", [])

        # Siguro report_generator dhe visualization
        if "report_generator" not in agents_to_run:
            agents_to_run.append("report_generator")
        if "visualization" not in agents_to_run:
            agents_to_run.append("visualization")
        agents_to_run = [a for a in agents_to_run if a != "report_generator"] + ["report_generator"]

        # ── Hapi 4: Ekzekuto agjentët me Zero Trust ───────────────────────────
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
            "zero_trust_log": [],
        }

        last_result = None

        for agent_key in agents_to_run:
            agent = self._agents.get(agent_key)
            if not agent:
                continue

            # ── Zero Trust: Kontrollo aksesin e agjentit ──────────────────────
            resource = self._agent_resources.get(agent_key, Resource.AGENT_PLANNER)
            agent_zt = zero_trust_pep.verify_request(
                username=self.username,
                role=self.role,
                token=self.token,
                resource=resource,
                action=Action.EXECUTE,
                query_text=query,
                agent_name=agent_key,
            )

            results["zero_trust_log"].append({
                "agent": agent_key,
                "allowed": agent_zt.allowed,
                "reason": agent_zt.reason,
                "risk_level": agent_zt.risk_level,
            })

            if not agent_zt.allowed:
                results["agent_results"][agent_key] = {
                    "error": f"Zero Trust Denied: {agent_zt.reason}",
                    "zero_trust_blocked": True,
                }
                continue

            # ── Least Privilege: Kontrollo aksesin DB të agjentit ─────────────
            if agent_key in DB_AGENTS:
                agent_display_name = AGENT_POLICY_NAMES.get(agent_key, agent_key)
                db_check = check_agent_permission(
                    agent_display_name, "database", "read", self.username
                )
                if not db_check.allowed:
                    results["agent_results"][agent_key] = {
                        "error": f"Zero Trust Denied: {db_check.reason}",
                        "zero_trust_blocked": True,
                    }
                    continue

            try:
                if agent_key == "report_generator":
                    raw_result = agent.run(query, context=last_result)
                    results["report"] = raw_result.get("report")
                elif agent_key == "visualization":
                    raw_result = agent.run(query, context=last_result)
                    results["viz_config"] = raw_result.get("config")
                elif agent_key == "anomaly_detection":
                    raw_result = agent.run(query, context=last_result)
                    results["anomalies"] = raw_result.get("anomalies", [])
                    if raw_result.get("data"):
                        last_result = raw_result
                        results["final_data"] = raw_result["data"]
                        results["final_columns"] = raw_result.get("columns", [])
                else:
                    raw_result = agent.run(query, context=last_result)
                    if not raw_result.get("error"):
                        last_result = raw_result
                        results["final_data"] = raw_result.get("data", [])
                        results["final_columns"] = raw_result.get("columns", [])
                    else:
                        results["error"] = raw_result["error"]

                # ── Output Validation (Zero Trust) ─────────────────────────────
                is_valid, msg, cleaned = output_validator.validate_agent_output(
                    agent_key, raw_result, self.role
                )
                if not is_valid:
                    log_event(
                        username=self.username,
                        event_type="OUTPUT_VALIDATION_FAILED",
                        details=f"Output validation dështoi për '{agent_key}': {msg}",
                        success=False,
                        risk_level="HIGH",
                    )

                results["agent_results"][agent_key] = cleaned

            except Exception as e:
                results["agent_results"][agent_key] = {"error": str(e)}
                results["error"] = str(e)

        # ── Hapi 5: Apliko row limits bazuar në role ───────────────────────────
        if results["final_data"]:
            results["final_data"] = output_validator.sanitize_for_role(
                results["final_data"], self.role
            )

        # ── Log query i suksesshëm ─────────────────────────────────────────────
        elapsed = round(time.time() - start_time, 2)
        log_event(
            username=self.username,
            event_type="QUERY",
            details=f"Zero Trust Query OK — {elapsed}s — Agjentë: {agents_to_run}",
            success=True,
            risk_level="LOW",
        )

        return results

    def _plan(self, query: str, history: list | None = None) -> dict:
        """Thirr LLM për të planifikuar agjentët."""
        history_str = ""
        if history:
            recent = history[-3:]
            history_str = f"\nHistory: {json.dumps(recent)}"

        raw = self._base._call_llm(
            system=self.PLANNER_SYSTEM,
            user=f"Query: {query}{history_str}\n\nJSON plan:",
        )

        try:
            raw = raw.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
            return json.loads(raw)
        except Exception:
            return {
                "intent": query,
                "agents": ["cube_operations", "report_generator", "visualization"],
                "primary_agent": "cube_operations",
                "complexity": "simple",
                "parameters": {"filters": {}, "groupby": [], "metric": "revenue"},
            }

    def _denied_result(self, query: str, reason: str) -> dict:
        return {
            "query": query,
            "error": f"⛔ Zero Trust: {reason}",
            "zero_trust_denied": True,
            "final_data": [],
            "final_columns": [],
            "plan": {},
            "agent_results": {},
            "report": None,
            "viz_config": None,
            "anomalies": [],
            "zero_trust_log": [],
        }
