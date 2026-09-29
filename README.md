# olap-bi-llm-platform_security
BI LLM Security Platform

An OLAP business-intelligence platform driven by LLM agents, with a zero-trust security layer around every query and response. Users ask questions in natural language; agents plan the analysis, run cube operations, calculate KPIs and build reports, while a policy engine validates each step.

Features
LLM agents for planning, cube operations, dimension navigation, KPI calculation, anomaly detection, report generation and visualization
Zero-trust security: policy engine, policy enforcement point (PEP), SQL validation, output validation
Authentication with user management and password handling
Audit logging with a dashboard for reviewing activity
Streamlit frontend and REST API backend (Swagger docs included)
Project structure
.
├── backend/
│   ├── agents/          # LLM agents (planner, zero_trust_planner, kpi_calculator,
│   │                    #   cube_operations, dimension_navigator, anomaly_detection,
│   │                    #   report_generator, visualization_agent, base)
│   ├── api/             # API entry point (main.py)
│   ├── auth/            # Authentication and user management
│   ├── db/              # Database connection and queries
│   └── security/        # Zero-trust layer
│       ├── policy_engine.py      # Access rules and decisions
│       ├── zero_trust_pep.py     # Policy enforcement point
│       ├── sql_validator.py      # Checks generated SQL before execution
│       ├── output_validator.py   # Checks results before returning them
│       ├── audit_logger.py       # Records every action
│       ├── encryption.py         # Encryption helpers
│       └── email_service.py      # Email notifications
├── frontend/
│   ├── app.py           # Streamlit entry point
│   ├── helpers/         # Login, password, audit and security dashboard components
│   └── pages/           # Additional Streamlit pages
├── data/                # Datasets
├── docs/screenshots/    # API documentation screenshots
├── scripts/             # Utility scripts
├── .streamlit/          # Streamlit configuration
├── .env.example         # Template for environment variables
├── requirements.txt     # Python dependencies
└── README.md
Getting started
1. Clone and install
bash
git clone https://github.com/<your-username>/BI_LLM_SECURITY_PLATFORM.git
cd BI_LLM_SECURITY_PLATFORM
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
2. Configure environment variables

Copy the template and fill in your own values:

bash
cp .env.example .env         # Windows: copy .env.example .env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GMAIL_ADDRESS=your_email_here
GMAIL_APP_PASSWORD=your_app_password_here

Never commit .env. It is listed in .gitignore. Only .env.example (with placeholder values) belongs in the repository.

3. Run

Start the backend API:

bash
uvicorn backend.api.main:app --reload

Interactive API docs are then available at http://localhost:8000/docs.

In a second terminal, start the frontend:

bash
streamlit run frontend/app.py
Security notes
Secrets are loaded from environment variables, never hard-coded.
Generated SQL and model output pass through validators before execution or display.
All actions are written to the audit log.
Do not commit real user data (users.json, audit_logs.json) to a public repository.
Tech stack

Python, Streamlit, FastAPI, Anthropic API

License

Add your license here.

