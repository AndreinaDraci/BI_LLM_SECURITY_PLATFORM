# OLAP BI Platform – AI Configuration

## Dataset: Global Retail Sales (2022–2024)

### Schema
```
fact_sales: order_id, order_date, year, quarter, month, month_name,
            region, country, category, subcategory, customer_segment,
            quantity, unit_price, revenue, cost, profit, profit_margin
```

### Dimension Values
- **year**: 2022, 2023, 2024
- **quarter**: Q1, Q2, Q3, Q4
- **region**: North America, Europe, Asia Pacific, Latin America
- **category**: Electronics, Furniture, Office Supplies, Clothing
- **customer_segment**: Consumer, Corporate, Small Business, Government

### Hierarchies
- Time: year → quarter → month_name
- Geography: region → country
- Product: category → subcategory

---

## OLAP Operations Guide

| Operation | When to use | Example |
|-----------|-------------|---------|
| Slice | Single dimension filter | "Show only Q4" |
| Dice | Multiple dimension filters | "Electronics in Europe" |
| Drill-Down | Go from summary to detail | "Break year into quarters" |
| Roll-Up | Aggregate detail to summary | "Monthly → Quarterly" |
| Pivot | Rotate the perspective | "Regions as columns" |
| KPI | Compute metrics | "YoY growth, Top 5" |

---

## Multi-Agent Architecture

```
User Query
    │
    ▼
┌─────────────────────────────┐
│   Planner / Orchestrator    │ ← Intent classification, agent selection
└─────────────┬───────────────┘
              │
    ┌─────────┴──────────────────────────┐
    │         │            │             │
    ▼         ▼            ▼             ▼
Dimension  Cube Ops    KPI Calc    Anomaly Det
Navigator  (Slice/     (YoY/       (Outliers)
(Drill/    Dice/Pivot)  Rankings)
Roll-Up)
    │         │            │             │
    └─────────┴────────────┴─────────────┘
                          │
                ┌─────────┴──────────┐
                │   Visualization    │
                │   Report Gen       │
                └────────────────────┘
```

## Agent Specifications

### 1. Dimension Navigator Agent
- **Input**: Natural language drill-down/roll-up request
- **Output**: SQL + DataFrame + business explanation
- **Hierarchies**: Time (year→quarter→month), Geography (region→country), Product (category→subcategory)

### 2. Cube Operations Agent
- **Input**: Slice/Dice/Pivot request
- **Output**: Filtered/pivoted SQL + DataFrame
- **Operations**: WHERE clauses, CASE WHEN pivoting

### 3. KPI Calculator Agent
- **Input**: Comparison/ranking/growth request
- **Output**: KPI table with LAG/RANK window functions
- **KPIs**: YoY%, MoM%, profit margin, Top-N

### 4. Report Generator Agent
- **Input**: Analysis result from another agent
- **Output**: Executive summary, key insights, follow-up questions, chart hints

### 5. Visualization Agent (Optional)
- **Input**: Dataset + context
- **Output**: Plotly chart configuration

### 6. Anomaly Detection Agent (Optional)
- **Input**: Sales data
- **Output**: List of anomalies with severity levels

---

## Response Guidelines

1. Always return formatted results with explanations
2. Suggest 3 follow-up questions after each analysis
3. Use $ formatting for revenue/profit values
4. Use % formatting for margins and growth rates
5. Order results by the primary metric descending
6. Include totals/subtotals where appropriate
