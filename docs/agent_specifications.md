# Agent Specifications

## Multi-Agent OLAP Platform

---

## Agent 1: Dimension Navigator

**Purpose**: Navigate OLAP hierarchies — drill down into detail or roll up to summaries.

**Input**:
```json
{
  "query": "Break down Q4 revenue by month for North America",
  "context": null
}
```

**Output**:
```json
{
  "agent": "Dimension Navigator",
  "operation": "drill_down_roll_up",
  "sql": "SELECT month_name, ROUND(SUM(revenue),2) AS revenue FROM fact_sales WHERE quarter='Q4' AND region='North America' GROUP BY month_name ORDER BY month",
  "data": [{"month_name": "October", "revenue": 680000}, ...],
  "columns": ["month_name", "revenue"],
  "row_count": 3,
  "explanation": "North America's Q4 2024 revenue peaked in November at $820K...",
  "error": null
}
```

**System Prompt Strategy**: Chain-of-thought SQL generation with explicit hierarchy rules. The agent receives the full star schema and is instructed to use WHERE clauses for filters and GROUP BY for the target hierarchy level.

**Hierarchies**:
- Time: `year → quarter → month_name`
- Geography: `region → country`  
- Product: `category → subcategory`

---

## Agent 2: Cube Operations

**Purpose**: Apply OLAP cube operations: Slice (1 filter), Dice (N filters), Pivot (rotate).

**Input**:
```json
{
  "query": "Show Electronics sales in Europe for Corporate segment",
  "context": null
}
```

**Output**:
```json
{
  "agent": "Cube Operations",
  "operation": "dice",
  "sql": "SELECT ...",
  "data": [...],
  "explanation": "...",
  "error": null
}
```

**Operation Detection Logic**:
- Contains "pivot" / "rotate" → `pivot`
- Multiple filters (≥2 dimension keywords) → `dice`
- Single filter → `slice`

**Pivot SQL Pattern**:
```sql
SELECT year,
  SUM(CASE WHEN region='North America' THEN revenue ELSE 0 END) AS "North America",
  SUM(CASE WHEN region='Europe' THEN revenue ELSE 0 END) AS "Europe"
FROM fact_sales GROUP BY year ORDER BY year
```

---

## Agent 3: KPI Calculator

**Purpose**: Compute business KPIs: YoY growth, MoM change, profit margins, Top-N rankings.

**KPI Types**:

| KPI | SQL Pattern |
|-----|-------------|
| YoY Growth | `LAG(revenue) OVER (PARTITION BY region ORDER BY year)` |
| MoM Change | `LAG(revenue) OVER (PARTITION BY region ORDER BY year, month)` |
| Top-N | `RANK() OVER (ORDER BY revenue DESC) LIMIT N` |
| Profit Margin | `AVG(profit_margin)` or `SUM(profit)/SUM(revenue)*100` |

**Example YoY SQL**:
```sql
WITH yearly AS (
  SELECT region, year, SUM(revenue) AS revenue
  FROM fact_sales GROUP BY region, year
)
SELECT region, year,
  revenue,
  LAG(revenue) OVER (PARTITION BY region ORDER BY year) AS prev_year,
  ROUND((revenue - LAG(revenue) OVER (PARTITION BY region ORDER BY year)) /
        LAG(revenue) OVER (PARTITION BY region ORDER BY year) * 100, 2) AS yoy_growth_pct
FROM yearly ORDER BY region, year
```

---

## Agent 4: Report Generator

**Purpose**: Transform raw analysis results into executive-ready reports with insights, formatting hints, and follow-up suggestions.

**Input**: Previous agent's result (data + context)

**Output JSON**:
```json
{
  "executive_summary": "North America led Q4 performance with $2.1M revenue...",
  "key_insights": [
    "Electronics drove 45% of total Q4 revenue",
    "Corporate segment outperformed Consumer by 2.5x",
    "November was the peak month across all regions"
  ],
  "formatting_hints": {
    "highlight_column": "revenue",
    "highlight_condition": "top",
    "chart_type": "bar",
    "chart_x": "region",
    "chart_y": "revenue"
  },
  "follow_up_questions": [
    "Which subcategory drove the most revenue in Q4?",
    "How does Q4 2024 compare to Q4 2023?",
    "What is the profit margin by region in Q4?"
  ]
}
```

---

## Agent 5: Visualization Agent *(Optional)*

**Purpose**: Select the optimal chart type and generate Plotly configuration.

**Chart Selection Rules**:
- Time series → **Line chart**
- Category comparison → **Bar chart** (horizontal if >6 categories)
- Proportions → **Pie chart**
- Hierarchical data → **Treemap**
- Two numeric variables → **Scatter**

**Output**:
```json
{
  "chart_type": "bar",
  "title": "Q4 Revenue by Region",
  "x_col": "region",
  "y_col": "revenue",
  "color_col": null,
  "orientation": "h",
  "rationale": "Horizontal bar chart best for regional comparison with 4 categories"
}
```

---

## Agent 6: Anomaly Detection Agent *(Optional)*

**Purpose**: Identify unusual patterns: outliers, sudden drops/spikes, underperformers, negative margins.

**Detection Methods**:
1. Statistical outliers (>2σ from mean)
2. YoY/MoM change >30%
3. Negative profit margins
4. Bottom 10% performers

**Output**:
```json
{
  "anomalies": [
    {
      "type": "spike",
      "description": "November 2024 revenue 40% above monthly average",
      "dimension": "month_name",
      "value": "November 2024",
      "severity": "medium"
    }
  ],
  "summary": "3 anomalies detected, 1 high severity (negative margin in Office Supplies Latin America)"
}
```

---

## Planner / Orchestrator

**Purpose**: Parse user intent, select the right combination of agents, coordinate execution.

**Selection Logic**:

| Query Pattern | Agents Selected |
|--------------|-----------------|
| "break down by" / "drill into" | dimension_navigator |
| "show only" / "filter to" | cube_operations |
| "compare X vs Y" / "growth" | kpi_calculator |
| "top N" / "ranking" | kpi_calculator |
| "anomaly" / "unusual" | anomaly_detection |
| "pivot" / "rotate" | cube_operations |
| Always | report_generator, visualization |

**Multi-step Example**:
```
"Break down Q4 by region, drill into top performer by month"
→ [cube_operations, kpi_calculator, dimension_navigator, visualization, report_generator]
```

**Context Passing**: Each agent receives the previous agent's full output as `context`, enabling chained analysis (e.g., KPI Calculator identifies "North America" as top region → Dimension Navigator drills into North America automatically).
