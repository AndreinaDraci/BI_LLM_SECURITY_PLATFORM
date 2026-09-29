"""
FastAPI backend – exposes OLAP multi-agent endpoints.
"""
from __future__ import annotations
import os
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.agents.planner import Planner
from backend.db import database as db

app = FastAPI(
    title="OLAP BI Platform API",
    description="Multi-agent Business Intelligence OLAP Assistant",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy planner cache per provider
_planners: dict[str, Planner] = {}


def _get_planner(provider: str) -> Planner:
    if provider not in _planners:
        _planners[provider] = Planner(provider=provider)
    return _planners[provider]


# ── Request / Response models ────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    provider: str = "anthropic"
    history: list[dict] = []


class QueryResponse(BaseModel):
    query: str
    plan: dict
    final_data: list[dict]
    final_columns: list[str]
    report: dict | None
    viz_config: dict | None
    anomalies: list[dict]
    agent_results: dict
    error: str | None


class SQLRequest(BaseModel):
    sql: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "message": "OLAP BI Platform is running"}


@app.get("/schema")
def get_schema():
    """Return database schema information."""
    try:
        schema = db.get_schema_info()
        return {"schema": schema, "ddl": db.DDL_SCRIPTS}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/overview")
def get_overview():
    """Return dataset overview statistics."""
    try:
        stats = db.query("""
            SELECT
                COUNT(*) AS total_orders,
                ROUND(SUM(revenue), 0) AS total_revenue,
                ROUND(SUM(profit), 0) AS total_profit,
                ROUND(AVG(profit_margin), 2) AS avg_margin_pct,
                MIN(year) AS min_year,
                MAX(year) AS max_year,
                COUNT(DISTINCT country) AS countries,
                COUNT(DISTINCT category) AS categories
            FROM fact_sales
        """)
        by_region = db.query("""
            SELECT region, ROUND(SUM(revenue), 0) AS revenue
            FROM fact_sales GROUP BY region ORDER BY revenue DESC
        """)
        by_year = db.query("""
            SELECT year, ROUND(SUM(revenue), 0) AS revenue
            FROM fact_sales GROUP BY year ORDER BY year
        """)
        return {
            "summary": stats.to_dict("records")[0],
            "by_region": by_region.to_dict("records"),
            "by_year": by_year.to_dict("records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
def run_query(req: QueryRequest):
    """Main endpoint: run a natural language OLAP query."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    provider = req.provider.lower()
    api_key_env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    if not os.getenv(api_key_env):
        raise HTTPException(
            status_code=400,
            detail=f"{api_key_env} not set. Add it to your .env file.",
        )

    planner = _get_planner(provider)
    result = planner.execute(req.query, history=req.history)

    return QueryResponse(
        query=result["query"],
        plan=result["plan"],
        final_data=result["final_data"],
        final_columns=result["final_columns"],
        report=result["report"],
        viz_config=result["viz_config"],
        anomalies=result.get("anomalies", []),
        agent_results=result["agent_results"],
        error=result.get("error"),
    )


@app.post("/sql")
def run_sql(req: SQLRequest):
    """Execute raw SQL (for power users / debugging)."""
    try:
        df = db.query(req.sql)
        return {
            "data": df.to_dict("records"),
            "columns": list(df.columns),
            "row_count": len(df),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/examples")
def get_example_queries():
    """Return example queries organized by OLAP operation."""
    return {
        "examples": [
            {"operation": "Slice", "query": "Show only Q4 2024 sales"},
            {"operation": "Dice", "query": "Show Electronics sales in Europe for 2024"},
            {"operation": "Drill-Down", "query": "Break down 2024 revenue by quarter, then drill into Q4 by month"},
            {"operation": "Roll-Up", "query": "Roll up monthly sales to quarterly totals by region"},
            {"operation": "YoY Growth", "query": "Compare 2023 vs 2024 revenue by region"},
            {"operation": "Top-N", "query": "Top 5 countries by profit in 2024"},
            {"operation": "Pivot", "query": "Show revenue by region as columns, with years as rows"},
            {"operation": "Anomaly", "query": "Find unusual patterns or anomalies in our sales data"},
            {"operation": "Profit Analysis", "query": "Which category has the highest profit margin?"},
            {"operation": "Complex", "query": "Break down Q4 sales by region, then drill into the top performer by month"},
        ]
    }
