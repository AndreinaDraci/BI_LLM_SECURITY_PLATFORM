# Prompt Design Document

## System Prompt Strategy – OLAP Multi-Agent Platform

---

## Core Design Philosophy

Each agent uses a **narrow, task-specific system prompt** rather than a single general-purpose prompt. This produces more consistent, accurate SQL and reduces hallucination.

### The Three-Part Prompt Structure

Every agent system prompt contains:

1. **Role declaration** – "You are the [X] Agent for an OLAP BI system"
2. **Schema grounding** – Exact table/column names, dimension values, and hierarchies
3. **Output contract** – Strict format rules (SQL only, JSON only, etc.)

---

## Planner Prompt Strategy

The Planner's prompt uses a **structured JSON output contract**:

```
Output EXACTLY this JSON:
{
  "intent": "...",
  "agents": [...],
  "primary_agent": "...",
  "complexity": "simple" | "multi_step",
  "parameters": {...}
}
```

**Why**: LLMs are better at classification than free-form routing. Constraining to a JSON schema forces explicit decisions rather than hedged prose.

**Agent selection trigger keywords**:
- drill/break down/by month → `dimension_navigator`
- show only/filter/just → `cube_operations`
- compare/growth/top N/rank → `kpi_calculator`
- anomaly/unusual/outlier → `anomaly_detection`

---

## SQL Generation Prompt Strategy

Agents that generate SQL (Dimension Navigator, Cube Operations, KPI Calculator) use:

1. **Schema first**: The full star schema is in the system prompt so the LLM "knows" the columns
2. **Dimension values**: Exact strings ("Q1" not "q1", "North America" not "north america")
3. **Formula templates**: YoY uses LAG(), rankings use RANK() – explicitly told
4. **Single instruction**: "Return ONLY valid DuckDB SQL — no markdown, no explanation"

**SQL extraction robustness**: A `_extract_sql()` function strips markdown fences (```sql...```) in case the LLM ignores the "no markdown" instruction.

---

## Report Generator Prompt Strategy

The Report Generator uses a **JSON output schema with specific keys**:

```json
{
  "executive_summary": "2-3 sentences for C-suite",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "formatting_hints": {"chart_type": "...", "x_col": "...", "y_col": "..."},
  "follow_up_questions": ["Q1", "Q2", "Q3"]
}
```

**Persona**: "You are a CFO-level analyst" — persona framing improves business-appropriate language and specificity.

**Data grounding**: The top 5 rows + column statistics are passed to ensure insights reference actual numbers, not hallucinated ones.

---

## Context Passing Strategy

Each agent receives the previous agent's full output as a `context` dict:

```python
result = agent.run(query, context=last_analysis_result)
```

The context contains:
- `data`: List of records from previous analysis
- `columns`: Column names
- `operation`: What was done
- `agent`: Which agent produced it

This enables chained prompts like:
> *Planner → Cube Operations (Q4 data) → KPI Calculator (ranks regions using Q4 data as context) → Dimension Navigator (drills into #1 region) → Report Generator (formats all results)*

---

## Conversation History Strategy

The Planner receives the last 3 user messages as context:

```python
history_str = f"Conversation history (last 3 turns): {json.dumps(recent)}"
```

**Why 3**: Balances context awareness with token cost. More than 5 turns rarely changes agent selection.

---

## Error Handling Strategy

All prompts have fallback behavior:

1. **SQL errors**: Caught in `try/except`, error returned in result dict
2. **JSON parse errors**: Each agent has a hardcoded fallback JSON
3. **Missing API key**: FastAPI returns HTTP 400 with clear message
4. **Empty results**: Agents return empty data with informative explanation

---

## Lessons from Prompt Iteration

| Problem | Solution |
|---------|----------|
| LLM returned markdown SQL | Added `_extract_sql()` stripper |
| Wrong column names generated | Added full schema to every agent prompt |
| Inconsistent dimension values | Added exact value lists ("Q1","Q2","Q3","Q4") |
| Generic insights | Added "Be specific and data-driven, mention actual numbers" |
| Pivot SQL failing | Added explicit CASE WHEN template to Cube Ops prompt |
| Report not JSON | Added "Return ONLY valid JSON. No markdown." |
