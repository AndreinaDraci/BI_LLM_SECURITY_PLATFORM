# Prompt Library – OLAP BI Assistant
## 20 Tested Prompts Covering All Operations

---

## Category 1: Slice (Single Filter)

### P01 – Slice by Year
```
Show only 2024 sales. What is the total revenue and profit for that year?
```
**Expected operation**: Slice on year=2024  
**Expected agent**: cube_operations

---

### P02 – Slice by Quarter
```
Show only Q4 sales data with total revenue, total profit, and average order value.
```
**Expected operation**: Slice on quarter='Q4'  
**Expected agent**: cube_operations

---

### P03 – Slice by Category
```
Filter to Electronics category only. Show me revenue and profit by year.
```
**Expected operation**: Slice on category='Electronics', group by year  
**Expected agent**: cube_operations

---

## Category 2: Dice (Multiple Filters)

### P04 – Dice: Region + Category
```
Show Electronics sales in Europe. Break it down by year.
```
**Expected operation**: Dice(region='Europe', category='Electronics')  
**Expected agents**: cube_operations

---

### P05 – Dice: Quarter + Segment
```
Show Q4 data for Corporate segment only. What is the revenue by region?
```
**Expected operation**: Dice(quarter='Q4', customer_segment='Corporate')  
**Expected agents**: cube_operations

---

### P06 – Dice: Multiple dimensions
```
Filter to Asia Pacific, year 2023, Electronics category. Show revenue by subcategory.
```
**Expected operation**: Dice with 3 filters  
**Expected agents**: cube_operations, dimension_navigator

---

## Category 3: Drill-Down

### P07 – Drill Year → Quarter
```
Break down 2024 revenue by quarter. Which quarter performed best?
```
**Expected operation**: Drill-Down year=2024 → quarter  
**Expected agents**: dimension_navigator, kpi_calculator

---

### P08 – Drill Quarter → Month
```
Drill down Q4 2024 by month. Show me the revenue trend.
```
**Expected operation**: Drill-Down quarter='Q4', year=2024 → month  
**Expected agents**: dimension_navigator, visualization

---

### P09 – Drill Region → Country
```
Show revenue by region, then drill into North America by country.
```
**Expected operation**: Drill-Down region → country (for North America)  
**Expected agents**: dimension_navigator

---

### P10 – Complex Drill (Showcase Query)
```
Break down Q4 sales by region, then drill into the top performer by month.
```
**Expected operation**: Dice → KPI → Drill-Down  
**Expected agents**: cube_operations, kpi_calculator, dimension_navigator, visualization, report_generator

---

## Category 4: Roll-Up

### P11 – Roll-Up Month → Quarter
```
Roll up the monthly sales to show quarterly totals for each region in 2024.
```
**Expected operation**: Roll-Up month → quarter  
**Expected agents**: dimension_navigator

---

### P12 – Roll-Up Country → Region
```
Show revenue by country, then roll it up to show regional totals.
```
**Expected operation**: Roll-Up country → region  
**Expected agents**: dimension_navigator

---

## Category 5: KPI & Comparisons

### P13 – Year-over-Year Growth
```
Compare 2023 vs 2024 revenue by region. Calculate the year-over-year growth percentage.
```
**Expected KPI**: YoY growth with LAG window function  
**Expected agents**: kpi_calculator, visualization

---

### P14 – Top-N Ranking
```
Top 5 countries by profit in 2024. Rank them and show their profit margins.
```
**Expected KPI**: RANK() with LIMIT 5  
**Expected agents**: kpi_calculator

---

### P15 – Profit Margin Analysis
```
Which product category has the highest profit margin? Compare all categories.
```
**Expected KPI**: AVG(profit_margin) by category  
**Expected agents**: kpi_calculator, visualization

---

### P16 – Segment Profitability
```
Which customer segment is most valuable? Show revenue, profit, and margin for each.
```
**Expected KPI**: Multi-metric comparison  
**Expected agents**: kpi_calculator, report_generator

---

## Category 6: Pivot

### P17 – Region Pivot
```
Pivot revenue by region as columns, with years as rows. I want to see the matrix.
```
**Expected operation**: PIVOT using CASE WHEN  
**Expected agents**: cube_operations

---

### P18 – Category by Quarter Pivot
```
Show a pivot table with categories as rows and quarters (Q1-Q4) as columns for 2024.
```
**Expected operation**: PIVOT on quarter  
**Expected agents**: cube_operations

---

## Category 7: Anomaly Detection

### P19 – Find Anomalies
```
Find unusual patterns or anomalies in our sales data. What looks unexpected?
```
**Expected operation**: Statistical analysis  
**Expected agents**: anomaly_detection, report_generator

---

### P20 – Business Analysis (Complex Multi-Agent)
```
Give me a full analysis of 2024 performance: top regions, YoY growth, best categories, and any anomalies.
```
**Expected operation**: Multi-step analysis  
**Expected agents**: kpi_calculator, anomaly_detection, visualization, report_generator

---

## Prompt Engineering Notes

**What makes these prompts effective**:
1. **Natural language** – no SQL knowledge required
2. **Business intent** – framed as business questions, not technical requests
3. **Specificity** – include dimension values when filtering ("Q4", "Europe")
4. **Follow-up ready** – results always include 3 suggested follow-up questions
5. **Context-aware** – multi-turn conversation maintains history

**Tested edge cases**:
- Ambiguous time references ("last year" → resolved to 2023)
- Implicit filters ("best region" → inferred as MAX(revenue))
- Multi-step requests (→ planner chains multiple agents)
- Pivot requests (→ CASE WHEN SQL pattern)
