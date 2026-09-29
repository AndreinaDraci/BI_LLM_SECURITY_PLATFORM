"""
Zero Trust Policy Engine
========================
Parimi kryesor: "Never Trust, Always Verify"

Çdo kërkesë — nga user, agjent, ose komponent — duhet të:
1. Vërtetohet (Identity Verification)
2. Autorizohet (Policy Check)
3. Kufizohet (Least Privilege)
4. Logohet (Audit)

Policy Engine është "truri" i Zero Trust — vendos PO/JO për çdo veprim.
"""
from __future__ import annotations
import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ── Resurset e sistemit ───────────────────────────────────────────────────────
class Resource(str, Enum):
    QUERY_OLAP       = "query:olap"
    QUERY_SQL_RAW    = "query:sql_raw"
    DATA_EXPORT      = "data:export"
    DATA_ALL         = "data:all"
    AUDIT_VIEW       = "audit:view"
    USER_MANAGE      = "user:manage"
    AGENT_PLANNER    = "agent:planner"
    AGENT_DIM_NAV    = "agent:dimension_navigator"
    AGENT_CUBE_OPS   = "agent:cube_operations"
    AGENT_KPI        = "agent:kpi_calculator"
    AGENT_REPORT     = "agent:report_generator"
    AGENT_VIZ        = "agent:visualization"
    AGENT_ANOMALY    = "agent:anomaly_detection"
    DB_READ          = "db:read"
    DB_WRITE         = "db:write"
    SECURITY_PANEL   = "security:panel"


# ── Veprimet e mundshme ───────────────────────────────────────────────────────
class Action(str, Enum):
    READ    = "read"
    WRITE   = "write"
    EXECUTE = "execute"
    EXPORT  = "export"
    DELETE  = "delete"


# ── Konteksti i kërkesës ──────────────────────────────────────────────────────
@dataclass
class RequestContext:
    """Konteksti i plotë i çdo kërkese — Zero Trust kërkon kontekst, jo vetëm identitet."""
    username: str
    role: str
    token: str
    resource: Resource
    action: Action
    agent_name: Optional[str] = None      # Nëse vjen nga agjent
    ip_address: Optional[str] = "unknown"
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    query_text: Optional[str] = None      # Query e përdoruesit


# ── Rezultati i Policy Check ─────────────────────────────────────────────────
@dataclass
class PolicyDecision:
    """Vendimi i Policy Engine: ALLOW ose DENY me arsyetim."""
    allowed: bool
    reason: str
    risk_level: str = "LOW"     # LOW / MEDIUM / HIGH / CRITICAL
    constraints: dict = field(default_factory=dict)  # Kufizime shtesë


# ── Politikat per Role ────────────────────────────────────────────────────────
ROLE_POLICIES = {
    "admin": {
        # Admin ka akses te gjitha, por jo DB write direkt
        Resource.QUERY_OLAP:    [Action.EXECUTE],
        Resource.QUERY_SQL_RAW: [Action.EXECUTE],
        Resource.DATA_EXPORT:   [Action.EXPORT],
        Resource.DATA_ALL:      [Action.READ],
        Resource.AUDIT_VIEW:    [Action.READ],
        Resource.USER_MANAGE:   [Action.READ, Action.WRITE, Action.DELETE],
        Resource.AGENT_PLANNER: [Action.EXECUTE],
        Resource.AGENT_DIM_NAV: [Action.EXECUTE],
        Resource.AGENT_CUBE_OPS:[Action.EXECUTE],
        Resource.AGENT_KPI:     [Action.EXECUTE],
        Resource.AGENT_REPORT:  [Action.EXECUTE],
        Resource.AGENT_VIZ:     [Action.EXECUTE],
        Resource.AGENT_ANOMALY: [Action.EXECUTE],
        Resource.DB_READ:       [Action.READ],
        Resource.DB_WRITE:      [],         # Admin NUK mund të shkruajë direkt në DB
        Resource.SECURITY_PANEL:[Action.READ, Action.EXECUTE],
    },
    "analyst": {
        Resource.QUERY_OLAP:    [Action.EXECUTE],
        Resource.QUERY_SQL_RAW: [],         # Analyst nuk mund të ekzekutojë SQL raw
        Resource.DATA_EXPORT:   [Action.EXPORT],
        Resource.DATA_ALL:      [Action.READ],
        Resource.AUDIT_VIEW:    [],         # Analyst nuk sheh audit
        Resource.USER_MANAGE:   [],
        Resource.AGENT_PLANNER: [Action.EXECUTE],
        Resource.AGENT_DIM_NAV: [Action.EXECUTE],
        Resource.AGENT_CUBE_OPS:[Action.EXECUTE],
        Resource.AGENT_KPI:     [Action.EXECUTE],
        Resource.AGENT_REPORT:  [Action.EXECUTE],
        Resource.AGENT_VIZ:     [Action.EXECUTE],
        Resource.AGENT_ANOMALY: [Action.EXECUTE],
        Resource.DB_READ:       [Action.READ],
        Resource.DB_WRITE:      [],
        Resource.SECURITY_PANEL:[],
    },
    "viewer": {
        Resource.QUERY_OLAP:    [Action.EXECUTE],
        Resource.QUERY_SQL_RAW: [],
        Resource.DATA_EXPORT:   [],         # Viewer NUK mund të eksportojë
        Resource.DATA_ALL:      [],         # Viewer sheh vetëm të dhëna të filtruara
        Resource.AUDIT_VIEW:    [],
        Resource.USER_MANAGE:   [],
        Resource.AGENT_PLANNER: [Action.EXECUTE],
        Resource.AGENT_DIM_NAV: [Action.EXECUTE],
        Resource.AGENT_CUBE_OPS:[Action.EXECUTE],
        Resource.AGENT_KPI:     [Action.EXECUTE],
        Resource.AGENT_REPORT:  [Action.EXECUTE],
        Resource.AGENT_VIZ:     [Action.EXECUTE],
        Resource.AGENT_ANOMALY: [],         # Viewer nuk akseson anomaly detection
        Resource.DB_READ:       [Action.READ],
        Resource.DB_WRITE:      [],
        Resource.SECURITY_PANEL:[],
    },
}

# ── Politikat per Agjentë (Least Privilege) ──────────────────────────────────
AGENT_POLICIES = {
    "Planner": {
    "can_access_agents": ["coordination", "Dimension Navigator", "Cube Operations",
                           "KPI Calculator", "Report Generator",
                           "Visualization Agent", "Anomaly Detection"],
    "can_access_db": False,
    "can_modify_data": False,
},
    "Dimension Navigator": {
        "can_access_agents": [],    # Agjentët nuk thërrasin njëri-tjetrin direkt
        "can_access_db": True,
        "can_modify_data": False,   # Vetëm READ
        "allowed_tables": ["fact_sales", "dim_date", "dim_geography",
                           "dim_product", "dim_customer"],
        "allowed_operations": ["SELECT", "WITH"],
    },
    "Cube Operations": {
        "can_access_agents": [],
        "can_access_db": True,
        "can_modify_data": False,
        "allowed_tables": ["fact_sales", "dim_date", "dim_geography",
                           "dim_product", "dim_customer"],
        "allowed_operations": ["SELECT", "WITH"],
    },
    "KPI Calculator": {
        "can_access_agents": [],
        "can_access_db": True,
        "can_modify_data": False,
        "allowed_tables": ["fact_sales"],
        "allowed_operations": ["SELECT", "WITH"],
    },
    "Report Generator": {
        "can_access_agents": [],
        "can_access_db": False,     # Report Gen nuk akseson DB — merr rezultatet nga agjentët
        "can_modify_data": False,
    },
    "Visualization Agent": {
        "can_access_agents": [],
        "can_access_db": False,     # Visualization nuk akseson DB direkt
        "can_modify_data": False,
    },
    "Anomaly Detection": {
        "can_access_agents": [],
        "can_access_db": True,
        "can_modify_data": False,
        "allowed_tables": ["fact_sales"],
        "allowed_operations": ["SELECT"],
    },
}


class PolicyEngine:
    """
    Zero Trust Policy Engine.
    Çdo vendim dokumentohet dhe logohet.
    """

    def __init__(self):
        self._decision_log: list[dict] = []

    def evaluate(self, ctx: RequestContext) -> PolicyDecision:
        """
        Evaluo kërkesën sipas politikave Zero Trust.
        Hapat: Identity → Role → Resource → Action → Context → Decision
        """
        # Hapi 1: Verifiko identitetin (token duhet të jetë valid)
        if not ctx.token or not ctx.username or not ctx.role:
            decision = PolicyDecision(
                allowed=False,
                reason="Zero Trust: Identitet i paplotë — mungon token/username/role",
                risk_level="HIGH"
            )
            self._log(ctx, decision)
            return decision

        # Hapi 2: Verifiko rolin
        if ctx.role not in ROLE_POLICIES:
            decision = PolicyDecision(
                allowed=False,
                reason=f"Zero Trust: Roli '{ctx.role}' nuk ekziston në politika",
                risk_level="HIGH"
            )
            self._log(ctx, decision)
            return decision

        # Hapi 3: Merr politikën për rolin
        role_policy = ROLE_POLICIES[ctx.role]

        # Hapi 4: Kontrollo resursin
        if ctx.resource not in role_policy:
            decision = PolicyDecision(
                allowed=False,
                reason=f"Zero Trust: Resursi '{ctx.resource}' nuk gjendet në politikë",
                risk_level="MEDIUM"
            )
            self._log(ctx, decision)
            return decision

        # Hapi 5: Kontrollo veprimin
        allowed_actions = role_policy[ctx.resource]
        if ctx.action not in allowed_actions:
            decision = PolicyDecision(
                allowed=False,
                reason=(f"Zero Trust: Roli '{ctx.role}' nuk lejohet të kryejë "
                        f"'{ctx.action}' mbi '{ctx.resource}'"),
                risk_level="MEDIUM"
            )
            self._log(ctx, decision)
            return decision

        # Hapi 6: Kontrollo kohen e tokens (Max 1 orë)
        token_age = time.time() - ctx.timestamp
        if token_age > 3600:
            decision = PolicyDecision(
                allowed=False,
                reason="Zero Trust: Token ka skaduar — autentifikohu sërish",
                risk_level="LOW"
            )
            self._log(ctx, decision)
            return decision

        # ✅ Vendimi: ALLOW
        decision = PolicyDecision(
            allowed=True,
            reason=f"Zero Trust: '{ctx.role}' lejohet për '{ctx.action}' mbi '{ctx.resource}'",
            risk_level="LOW",
            constraints=self._get_constraints(ctx.role, ctx.resource)
        )
        self._log(ctx, decision)
        return decision

    def evaluate_agent(self, agent_name: str, target_resource: str,
                       action: str = "access") -> PolicyDecision:
        """
        Evaluo aksesin e një agjenti ndaj një resursi.
        Least Privilege: çdo agjent ka vetëm akseset e nevojshme.
        """
        if agent_name not in AGENT_POLICIES:
            return PolicyDecision(
                allowed=False,
                reason=f"Zero Trust: Agjenti '{agent_name}' nuk njeh sistemin",
                risk_level="HIGH"
            )

        policy = AGENT_POLICIES[agent_name]

        # Kontrollo aksesin DB
        if target_resource == "database" and not policy.get("can_access_db", False):
            return PolicyDecision(
                allowed=False,
                reason=f"Zero Trust Least Privilege: '{agent_name}' nuk ka akses direkt DB",
                risk_level="MEDIUM"
            )

        # Kontrollo modifikimin
        if action == "write" and not policy.get("can_modify_data", False):
            return PolicyDecision(
                allowed=False,
                reason=f"Zero Trust: '{agent_name}' ka vetëm akses READ (Least Privilege)",
                risk_level="HIGH"
            )

        # Kontrollo aksesin ndaj agjentëve të tjerë
        if target_resource.startswith("agent:"):
            target_agent = target_resource.replace("agent:", "")
            if target_agent not in policy.get("can_access_agents", []):
                return PolicyDecision(
                    allowed=False,
                    reason=f"Zero Trust: '{agent_name}' nuk mund të thërrasë '{target_agent}'",
                    risk_level="MEDIUM"
                )

        return PolicyDecision(
            allowed=True,
            reason=f"Zero Trust: '{agent_name}' lejohet — Least Privilege OK",
            risk_level="LOW",
            constraints=policy
        )

    def _get_constraints(self, role: str, resource: Resource) -> dict:
        """Merr kufizime specifike bazuar në rol dhe resurs."""
        constraints = {}
        if role == "viewer" and resource == Resource.QUERY_OLAP:
            constraints["max_rows"] = 1000
            constraints["no_export"] = True
        if role == "analyst" and resource == Resource.QUERY_OLAP:
            constraints["max_rows"] = 10000
        return constraints

    def _log(self, ctx: RequestContext, decision: PolicyDecision):
        """Logo çdo vendim të Policy Engine."""
        self._decision_log.append({
            "timestamp": time.time(),
            "username": ctx.username,
            "role": ctx.role,
            "resource": str(ctx.resource),
            "action": str(ctx.action),
            "allowed": decision.allowed,
            "reason": decision.reason,
            "risk_level": decision.risk_level,
            "agent": ctx.agent_name,
        })

    def get_recent_decisions(self, limit: int = 50) -> list:
        """Merr vendimet e fundit për monitoring."""
        return list(reversed(self._decision_log[-limit:]))

    def get_denied_count(self) -> int:
        """Numri i kërkesave të refuzuara."""
        return sum(1 for d in self._decision_log if not d["allowed"])

    def get_stats(self) -> dict:
        """Statistika të Policy Engine."""
        total = len(self._decision_log)
        denied = self.get_denied_count()
        return {
            "total_decisions": total,
            "allowed": total - denied,
            "denied": denied,
            "denial_rate": round(denied / total * 100, 1) if total > 0 else 0,
        }


# ── Singleton instance ────────────────────────────────────────────────────────
policy_engine = PolicyEngine()
