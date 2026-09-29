"""
OLAP BI Platform – Streamlit Frontend
A polished multi-agent Business Intelligence assistant.
"""
import os
import sys
import json
import time
import pandas as pd
import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FRONTEND_DIR)  # project root (one level up from frontend/)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OLAP BI Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (dark enterprise theme) ───────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --accent: #58a6ff;
    --accent2: #3fb950;
    --accent3: #f78166;
    --text: #c9d1d9;
    --muted: #8b949e;
    --highlight: #1f6feb26;
  }

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: var(--bg);
    color: var(--text);
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: var(--surface);
    border-right: 1px solid var(--border);
  }

  /* Chat messages */
  [data-testid="stChatMessage"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 12px;
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
  }

  /* Dataframe */
  [data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 8px;
  }

  /* Buttons */
  .stButton > button {
    background: transparent;
    border: 1px solid var(--accent);
    color: var(--accent);
    border-radius: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    transition: all 0.2s;
  }
  .stButton > button:hover {
    background: var(--highlight);
    border-color: var(--accent);
  }

  /* Agent badge */
  .agent-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    margin: 2px;
  }
  .badge-dim { background: #1f6feb40; color: #58a6ff; border: 1px solid #1f6feb; }
  .badge-cube { background: #3fb95040; color: #3fb950; border: 1px solid #3fb950; }
  .badge-kpi { background: #d29922_40; color: #e3b341; border: 1px solid #d29922; }
  .badge-report { background: #8957e540; color: #bc8cff; border: 1px solid #8957e5; }
  .badge-viz { background: #f7816640; color: #f78166; border: 1px solid #f78166; }
  .badge-anomaly { background: #da363340; color: #ff7b72; border: 1px solid #da3633; }

  /* Header */
  .hero-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.02em;
  }
  .hero-sub {
    font-size: 0.9rem;
    color: var(--muted);
    font-family: 'IBM Plex Mono', monospace;
  }

  /* SQL block */
  .sql-block {
    background: #0d1117;
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 10px 14px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: #e6edf3;
    white-space: pre-wrap;
    overflow-x: auto;
  }

  /* Insight card */
  .insight-card {
    background: var(--highlight);
    border: 1px solid #1f6feb;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.9rem;
    line-height: 1.6;
  }

  /* Anomaly badge */
  .anomaly-high { color: #ff7b72; }
  .anomaly-medium { color: #e3b341; }
  .anomaly-low { color: #3fb950; }

  /* Hide streamlit branding */
  #MainMenu, footer { visibility: hidden; }
  header[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "provider" not in st.session_state:
    st.session_state.provider = "groq"
if "db_ready" not in st.session_state:
    st.session_state.db_ready = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 16px">
      <div style="font-size:1.3rem; font-weight:700; color:#fff;">📊 OLAP Platform</div>
      <div style="font-size:0.75rem; color:#8b949e; font-family:'IBM Plex Mono',monospace;">Multi-Agent BI Assistant</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # API Provider
    st.markdown("**🤖 LLM Provider**")
    provider = "openai"
    st.session_state.provider = "groq"
    st.markdown("✅ **Groq (LLaMA 3.3)** selected — FREE")

    # API Key input
    key_label = "GROQ_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    existing = os.getenv(key_label, "")
    api_key = st.text_input(
        f"🔑 {key_label}",
        value=existing,
        type="password",
        help=f"Enter your {key_label}",
    )
    if api_key:
        os.environ[key_label] = api_key

    st.divider()
    st.markdown("**📋 OLAP Operations**")
    ops = [
        ("🔪", "Slice", "Filter on one dimension"),
        ("🎲", "Dice", "Filter on multiple dimensions"),
        ("🔽", "Drill-Down", "Summary → Detail"),
        ("🔼", "Roll-Up", "Detail → Summary"),
        ("🔄", "Pivot", "Rotate the view"),
        ("📈", "KPI", "YoY / MoM / Rankings"),
        ("🚨", "Anomaly", "Find unusual patterns"),
    ]
    for icon, op, desc in ops:
        st.markdown(f"<small>{icon} **{op}** – {desc}</small>", unsafe_allow_html=True)

    st.divider()
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    if st.button("📊 Show DB overview", use_container_width=True):
        st.session_state.show_overview = True

# ── Initialize DB ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def init_db():
    from backend.db import database as db
    db.get_connection()
    return db

@st.cache_resource(show_spinner=False)
def get_planner(provider: str):
    from backend.agents.planner import Planner
    return Planner(provider=provider)

# ── Helper functions ──────────────────────────────────────────────────────────
def fmt_money(v):
    try:
        return f"${float(v):,.0f}"
    except:
        return str(v)

def agent_badge(name: str) -> str:
    badge_map = {
        "Dimension Navigator": ("badge-dim", "🔽 Dimension Nav"),
        "Cube Operations": ("badge-cube", "🎲 Cube Ops"),
        "KPI Calculator": ("badge-kpi", "📈 KPI Calc"),
        "Report Generator": ("badge-report", "📄 Report Gen"),
        "Visualization Agent": ("badge-viz", "📊 Visualization"),
        "Anomaly Detection": ("badge-anomaly", "🚨 Anomaly"),
    }
    cls, label = badge_map.get(name, ("badge-dim", name))
    return f'<span class="agent-badge {cls}">{label}</span>'

def build_chart(df: pd.DataFrame, config: dict):
    """Build a Plotly chart from viz config."""
    try:
        import plotly.express as px
        chart_type = config.get("chart_type", "bar")
        x = config.get("x_col")
        y = config.get("y_col")
        color = config.get("color_col")
        title = config.get("title", "Analysis")
        orientation = config.get("orientation", "v")

        if x not in df.columns or y not in df.columns:
            # Try to auto-detect
            num_cols = df.select_dtypes(include=["float64", "int64"]).columns
            cat_cols = [c for c in df.columns if c not in num_cols]
            if not cat_cols or not num_cols.any():
                return None
            x = cat_cols[0]
            y = num_cols[0]

        color_col = color if (color and color in df.columns) else None

        kwargs = dict(data_frame=df, x=x, y=y, title=title, color=color_col,
                      template="plotly_dark", color_discrete_sequence=["#58a6ff","#3fb950","#e3b341","#f78166","#bc8cff"])

        if chart_type == "line":
            fig = px.line(**kwargs)
        elif chart_type == "pie":
            fig = px.pie(df, values=y, names=x, title=title, template="plotly_dark",
                         color_discrete_sequence=["#58a6ff","#3fb950","#e3b341","#f78166","#bc8cff"])
        elif chart_type == "scatter":
            fig = px.scatter(**kwargs)
        elif chart_type == "treemap":
            fig = px.treemap(df, path=[x], values=y, title=title, template="plotly_dark")
        else:
            if orientation == "h":
                fig = px.bar(df, x=y, y=x, title=title, color=color_col, orientation="h",
                             template="plotly_dark",
                             color_discrete_sequence=["#58a6ff","#3fb950","#e3b341","#f78166"])
            else:
                fig = px.bar(**kwargs)

        fig.update_layout(
            plot_bgcolor="#0d1117",
            paper_bgcolor="#161b22",
            font_color="#c9d1d9",
            title_font_size=14,
            height=380,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        return fig
    except Exception:
        return None

def render_result(result: dict):
    """Render a full OLAP analysis result."""
    plan = result.get("plan", {})
    report = result.get("report", {})
    data = result.get("final_data", [])
    columns = result.get("final_columns", [])
    viz_config = result.get("viz_config", {})
    anomalies = result.get("anomalies", [])
    error = result.get("error")
    agent_results = result.get("agent_results", {})

    # Agent badges
    agents_used = list(agent_results.keys())
    badges_html = "".join(agent_badge(
        next((v.get("agent","") for v in agent_results.values()
              if isinstance(v, dict) and v.get("agent","").lower().replace(" ","_") == a), a)
    ) for a in agents_used)
    st.markdown(f"**Agents:** {badges_html}", unsafe_allow_html=True)

    if error:
        st.error(f"⚠️ {error}")
        # Show SQL if available
        for ar in agent_results.values():
            if isinstance(ar, dict) and ar.get("sql"):
                with st.expander("🔍 SQL attempted"):
                    st.markdown(f'<div class="sql-block">{ar["sql"]}</div>', unsafe_allow_html=True)
        return

    # Intent
    if plan.get("intent"):
        st.markdown(f"<div style='color:#8b949e; font-size:0.85rem; margin-bottom:8px'>💭 {plan['intent']}</div>",
                    unsafe_allow_html=True)

    # Executive summary
    if report and report.get("executive_summary"):
        st.markdown(f'<div class="insight-card">📌 {report["executive_summary"]}</div>',
                    unsafe_allow_html=True)

    # Main content tabs
    tabs = ["📊 Data", "📈 Chart", "💡 Insights"]
    if anomalies:
        tabs.append("🚨 Anomalies")
    tabs.append("🔧 Debug")

    tab_objs = st.tabs(tabs)
    tab_idx = 0

    # Data tab
    with tab_objs[tab_idx]:
        tab_idx += 1
        if data:
            df = pd.DataFrame(data)

            # Format numeric columns
            num_cols = df.select_dtypes(include=["float64", "int64"]).columns
            display_df = df.copy()
            for col in num_cols:
                if "revenue" in col or "profit" in col or "cost" in col or "price" in col:
                    display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
                elif "margin" in col or "pct" in col or "growth" in col:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%")

            st.dataframe(display_df, use_container_width=True, height=300)
            st.caption(f"📦 {len(df):,} rows × {len(df.columns)} columns")

            # Download
            csv = df.to_csv(index=False)
            st.download_button("⬇️ Download CSV", csv, "olap_result.csv", "text/csv", key=f"dl_{hash(csv[:100])}")
        else:
            st.info("No data returned.")

    # Chart tab
    with tab_objs[tab_idx]:
        tab_idx += 1
        if data and viz_config:
            df = pd.DataFrame(data)
            fig = build_chart(df, viz_config)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                if viz_config.get("rationale"):
                    st.caption(f"ℹ️ {viz_config['rationale']}")
            else:
                st.info("Could not render chart for this data shape.")
        else:
            st.info("No visualization available.")

    # Insights tab
    with tab_objs[tab_idx]:
        tab_idx += 1
        if report:
            if report.get("key_insights"):
                st.markdown("**Key Insights**")
                for insight in report["key_insights"]:
                    st.markdown(f"• {insight}")

            if report.get("follow_up_questions"):
                st.markdown("**💬 Suggested Follow-Up Questions**")
                for q in report["follow_up_questions"]:
                    if st.button(f"→ {q}", key=f"followup_{hash(q)}"):
                        st.session_state._pending_query = q
                        st.rerun()

    # Anomalies tab
    if anomalies:
        with tab_objs[tab_idx]:
            tab_idx += 1
            for anom in anomalies:
                sev = anom.get("severity", "low")
                sev_class = f"anomaly-{sev}"
                icon = "🔴" if sev == "high" else "🟡" if sev == "medium" else "🟢"
                st.markdown(
                    f"{icon} **{anom.get('type','').upper()}** — "
                    f"<span class='{sev_class}'>{anom.get('description','')}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(f"Dimension: {anom.get('dimension','')} | Value: {anom.get('value','')}")

    # Debug tab
    with tab_objs[tab_idx]:
        for agent_name, ar in agent_results.items():
            if not isinstance(ar, dict):
                continue
            with st.expander(f"🤖 {agent_name}"):
                if ar.get("sql"):
                    st.markdown("**SQL Generated:**")
                    st.markdown(f'<div class="sql-block">{ar["sql"]}</div>', unsafe_allow_html=True)
                if ar.get("explanation"):
                    st.markdown(f"**Explanation:** {ar['explanation']}")
                if ar.get("operation"):
                    st.caption(f"Operation: {ar['operation']}")

        st.markdown("**Plan:**")
        st.json(plan)

# ── Main App ──────────────────────────────────────────────────────────────────
# Header
st.markdown("""
<div style="padding: 16px 0 24px">
  <div class="hero-title">📊 OLAP Business Intelligence Assistant</div>
  <div class="hero-sub">Multi-Agent Platform · Global Retail Sales 2022–2024 · 10,000 Transactions</div>
</div>
""", unsafe_allow_html=True)

# DB init with spinner
with st.spinner("Initializing star schema database..."):
    try:
        database = init_db()
        if not st.session_state.db_ready:
            st.session_state.db_ready = True
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        st.stop()

# Overview panel (if requested)
if st.session_state.get("show_overview"):
    with st.expander("📊 Dataset Overview", expanded=True):
        try:
            ov = database.query("""
                SELECT
                    COUNT(*) AS total_orders,
                    ROUND(SUM(revenue),0) AS total_revenue,
                    ROUND(SUM(profit),0) AS total_profit,
                    ROUND(AVG(profit_margin),2) AS avg_margin_pct
                FROM fact_sales
            """)
            row = ov.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Orders", f"{int(row.total_orders):,}")
            c2.metric("Total Revenue", fmt_money(row.total_revenue))
            c3.metric("Total Profit", fmt_money(row.total_profit))
            c4.metric("Avg Margin", f"{row.avg_margin_pct:.1f}%")
        except Exception as e:
            st.warning(str(e))
    st.session_state.show_overview = False

# Example queries
with st.expander("💡 Example Queries (click to use)", expanded=False):
    examples = [
        "Break down Q4 sales by region, then drill into the top performer by month",
        "Show Electronics sales in Europe for 2024",
        "Compare 2023 vs 2024 revenue by region with YoY growth",
        "Top 5 countries by profit — rank them",
        "Show monthly revenue trend for 2024 as a line chart",
        "Find anomalies or unusual patterns in our sales data",
        "Pivot revenue by region as columns with years as rows",
        "Which customer segment is most profitable?",
        "Drill down from category to subcategory for Furniture",
        "Show only Corporate segment sales in Asia Pacific",
    ]
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        if cols[i % 2].button(ex, key=f"ex_{i}"):
            st.session_state._pending_query = ex
            st.rerun()

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.write(msg["content"])
        else:
            if "result" in msg:
                render_result(msg["result"])
            else:
                st.write(msg["content"])

# Chat input
user_input = st.chat_input("Ask an OLAP question about your sales data...")

# Handle pending query from buttons
if "_pending_query" in st.session_state:
    user_input = st.session_state._pending_query
    del st.session_state._pending_query

if user_input:
    # Check API key
    key_env = "GROQ_API_KEY"
    if not os.getenv(key_env):
        st.error(f"⚠️ Please enter your {key_env} in the sidebar.")
        st.stop()

    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Run analysis
    with st.chat_message("assistant"):
        with st.spinner("🤖 Agents analyzing..."):
            try:
                history = [
                    {"role": m["role"], "content": m.get("content", m.get("query", ""))}
                    for m in st.session_state.messages[-6:]
                    if m["role"] == "user"
                ]
                planner = get_planner(st.session_state.provider)
                result = planner.execute(user_input, history=history)
                render_result(result)
                st.session_state.messages.append({
                    "role": "assistant",
                    "result": result,
                    "content": result.get("report", {}).get("executive_summary", "") if result.get("report") else "",
                })
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {e}",
                })
