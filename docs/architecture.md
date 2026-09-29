# System Architecture Document

## OLAP Business Intelligence Platform

### Overview

This platform implements a **multi-agent AI architecture** for OLAP analysis. Instead of a single monolithic LLM call, each analytical task is delegated to a specialized agent that excels at a specific responsibility.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                     │
│                  Streamlit Frontend                      │
│  Chat UI · Charts · Data Tables · Follow-up Buttons     │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP / direct Python call
┌─────────────────────────▼───────────────────────────────┐
│                     API LAYER                            │
│                FastAPI (port 8000)                       │
│  /query · /sql · /schema · /overview · /examples        │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│              PLANNER / ORCHESTRATOR                      │
│  1. Parse natural language intent                        │
│  2. Select appropriate agent(s)                         │
│  3. Pass context between agents                          │
│  4. Aggregate and return combined result                 │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ Dim  │ │ Cube │ │ KPI  │ │Reprt │ │ Viz  │ │Anoml │
│ Nav  │ │ Ops  │ │ Calc │ │ Gen  │ │Agent │ │ Det  │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
   └────────┴────────┴────────┴────────┴─────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   DATA ACCESS LAYER                      │
│              DuckDB In-Memory Database                   │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   STAR SCHEMA                            │
│   fact_sales                                             │
│   ├── dim_date (year, quarter, month, month_name)       │
│   ├── dim_geography (region, country)                   │
│   ├── dim_product (category, subcategory)               │
│   └── dim_customer (customer_segment)                   │
└─────────────────────────────────────────────────────────┘
```

---

## Star Schema ER Diagram

```
dim_date                    dim_geography
─────────                   ─────────────
order_date PK               region
year                        country PK (region, country)
quarter
month                       dim_product
month_name                  ───────────
                            category
                            subcategory PK (category, subcategory)

                            dim_customer
                            ────────────
                            customer_segment PK

fact_sales
──────────
order_id PK
order_date FK → dim_date
year
quarter
month
month_name
region    FK → dim_geography
country
category  FK → dim_product
subcategory
customer_segment FK → dim_customer
quantity
unit_price
revenue
cost
profit
profit_margin
```

---

## Agent Decision Flow

```
User: "Break down Q4 sales by region, drill into top performer by month"

Planner Analysis:
  - Mentions "Q4" → filter (Dice)
  - "by region" → group by region
  - "drill into" → Drill-Down operation
  - "top performer" → KPI ranking needed
  - "by month" → Time hierarchy traversal

→ Plan: [cube_operations, kpi_calculator, dimension_navigator, visualization, report_generator]

Step 1: cube_operations → Dice(year=2024, quarter=Q4) GROUP BY region
  Result: {North America: $2.1M, Europe: $1.8M, Asia Pacific: $1.2M, ...}

Step 2: kpi_calculator → Identify top performer (North America)
  Result: {rank_1: North America, revenue: $2.1M}

Step 3: dimension_navigator → Drill-Down North America by month
  Result: {October: $680K, November: $820K, December: $600K}

Step 4: visualization → Selects bar chart (comparison) + line chart (trend)

Step 5: report_generator → Executive summary + insights + follow-up questions
```

---

## Technology Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | DuckDB | In-memory OLAP, zero setup, SQL-native, fast aggregations |
| LLM Integration | Anthropic + OpenAI | User choice, redundancy, cost optimization |
| Backend | FastAPI | Async, auto-docs (Swagger), Pydantic validation |
| Frontend | Streamlit | Rapid BI development, native charting, Python-only |
| Visualization | Plotly | Interactive, dark theme support, multiple chart types |
| Agent Framework | Custom (no LangChain) | Full control, minimal dependencies, easier debugging |

---

## Data Flow

1. CSV loaded into DuckDB once at startup (`@st.cache_resource`)
2. User query hits Planner via direct call (or FastAPI)
3. Planner LLM call → plan JSON
4. Each agent: LLM call → SQL → DuckDB query → DataFrame
5. Results chained: each agent receives previous agent's output as context
6. ReportGenerator formats final output
7. VisualizationAgent selects chart type
8. Streamlit renders: table + chart + insights + follow-up buttons
