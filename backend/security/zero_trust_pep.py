"""
Policy Enforcement Point (PEP)
================================
Zero Trust: Çdo kërkesë kalon nëpër PEP para ekzekutimit.
PEP është "garda" që zbaton vendimet e Policy Engine.

Funksionet kryesore:
- verify_request(): Verifiko + Autorizo çdo kërkesë
- enforce_agent(): Zbato politikat për agjentët
- continuous_auth(): Vërteto token-in vazhdimisht
"""
from __future__ import annotations
import time
import os
import sys
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.security.policy_engine import (
    PolicyEngine, PolicyDecision, RequestContext,
    Resource, Action, policy_engine
)
from backend.security.audit_logger import log_event


class ZeroTrustPEP:
    """
    Policy Enforcement Point — zbaton Zero Trust në çdo kërkesë.
    
    Parimi: "Never Trust, Always Verify"
    - Asnjë user nuk besohet vetëm sepse është i loguar
    - Asnjë agjent nuk besohet vetëm sepse është brenda sistemit
    - Çdo veprim verifikohet dhe logohet
    """

    def __init__(self, engine: PolicyEngine = None):
        self.engine = engine or policy_engine
        self._active_sessions: dict[str, dict] = {}
        self._failed_attempts: dict[str, list] = {}

    def verify_request(
        self,
        username: str,
        role: str,
        token: str,
        resource: Resource,
        action: Action,
        query_text: str = "",
        agent_name: str = None,
        session_id: str = None,
    ) -> PolicyDecision:
        """
        Pika kryesore e zbatimit Zero Trust.
        Çdo kërkesë DUHET të kalojë këtu para ekzekutimit.
        """

        # Hapi 1: Continuous Authentication — verifiko token-in tani
        token_valid, token_reason = self._continuous_auth(username, token)
        if not token_valid:
            decision = PolicyDecision(
                allowed=False,
                reason=f"Zero Trust Continuous Auth: {token_reason}",
                risk_level="HIGH"
            )
            self._log_enforcement(username, resource, action, decision, query_text)
            return decision

        # Hapi 2: Krijo kontekstin e kërkesës
        ctx = RequestContext(
            username=username,
            role=role,
            token=token,
            resource=resource,
            action=action,
            agent_name=agent_name,
            timestamp=time.time(),
            session_id=session_id,
            query_text=query_text[:200] if query_text else None,
        )

        # Hapi 3: Thirr Policy Engine për vendim
        decision = self.engine.evaluate(ctx)

        # Hapi 4: Logo rezultatin
        self._log_enforcement(username, resource, action, decision, query_text)

        # Hapi 5: Detekto aktivitet të dyshimtë
        if not decision.allowed:
            self._track_failed_attempt(username, resource, action)

        return decision

    def enforce_agent_access(
        self,
        agent_name: str,
        target_resource: str,
        action: str = "read",
        context_username: str = "system",
    ) -> PolicyDecision:
        """
        Zbato Least Privilege për agjentët.
        Çdo agjent ka vetëm akseset e nevojshme — jo më shumë.
        """
        decision = self.engine.evaluate_agent(agent_name, target_resource, action)

        # Logo aksesin e agjentit
        log_event(
            username=context_username,
            event_type="AGENT_ACCESS",
            details=f"Agent '{agent_name}' → '{target_resource}' [{action}]: {'ALLOW' if decision.allowed else 'DENY'} — {decision.reason}",
            success=decision.allowed,
            risk_level=decision.risk_level,
        )

        return decision

    def _continuous_auth(self, username: str, token: str) -> tuple[bool, str]:
        """
        Vërteto token-in vazhdimisht — jo vetëm në login.
        Zero Trust: autentifikimi nuk është event i vetëm, por proces i vazhdueshëm.
        """
        if not token or not username:
            return False, "Token ose username mungon"

        # Importo verify_session nga auth module
        try:
            from backend.auth.auth import verify_session
            payload = verify_session(token)
            if not payload:
                return False, "Token i pavlefshëm ose i skaduar"
            if payload.get("username") != username:
                return False, "Token nuk i përket këtij user-i (mismatch)"
            return True, "Token valid"
        except Exception as e:
            return False, f"Gabim gjatë verifikimit: {str(e)}"

    def _track_failed_attempt(self, username: str, resource: Resource, action: Action):
        """Gjurmo tentativat e dështuara — detekto sulme potenciale."""
        now = time.time()
        if username not in self._failed_attempts:
            self._failed_attempts[username] = []

        # Hiq tentativat e vjetra (>1 orë)
        self._failed_attempts[username] = [
            t for t in self._failed_attempts[username]
            if now - t["time"] < 3600
        ]

        self._failed_attempts[username].append({
            "time": now,
            "resource": str(resource),
            "action": str(action),
        })

        # Alert nëse shumë tentativa
        count = len(self._failed_attempts[username])
        if count >= 5:
            log_event(
                username=username,
                event_type="ZERO_TRUST_ALERT",
                details=f"Zero Trust: {count} tentativa aksesi të paautorizuara nga '{username}' në 1 orë",
                success=False,
                risk_level="CRITICAL",
            )

    def _log_enforcement(
        self,
        username: str,
        resource: Resource,
        action: Action,
        decision: PolicyDecision,
        query_text: str = "",
    ):
        """Logo çdo zbatim PEP në audit log."""
        status = "ALLOW" if decision.allowed else "DENY"
        log_event(
            username=username,
            event_type=f"ZERO_TRUST_{status}",
            details=f"PEP: {status} — {decision.reason}",
            sql=query_text[:200] if query_text else None,
            success=decision.allowed,
            risk_level=decision.risk_level,
        )

    def get_session_info(self, username: str) -> dict:
        """Merr informacion mbi sesionin aktiv."""
        return self._active_sessions.get(username, {})

    def get_failed_attempts(self, username: str) -> list:
        """Merr tentativat e dështuara për një user."""
        return self._failed_attempts.get(username, [])

    def get_zero_trust_stats(self) -> dict:
        """Statistika të plotë Zero Trust."""
        engine_stats = self.engine.get_stats()
        alert_users = [
            u for u, attempts in self._failed_attempts.items()
            if len(attempts) >= 5
        ]
        return {
            **engine_stats,
            "active_sessions": len(self._active_sessions),
            "users_with_alerts": alert_users,
            "recent_decisions": self.engine.get_recent_decisions(10),
        }


# ── Singleton PEP instance ────────────────────────────────────────────────────
zero_trust_pep = ZeroTrustPEP()


# ── Helper funksione për përdorim të thjeshtë ─────────────────────────────────

def check_permission(
    username: str,
    role: str,
    token: str,
    resource: Resource,
    action: Action,
    query_text: str = "",
) -> PolicyDecision:
    """
    Funksion i thjeshtë për verifikim Zero Trust.
    Përdoret direkt nga agjentët dhe API endpoints.
    
    Shembull:
        decision = check_permission(username, role, token,
                                    Resource.QUERY_OLAP, Action.EXECUTE)
        if not decision.allowed:
            raise PermissionError(decision.reason)
    """
    return zero_trust_pep.verify_request(
        username=username,
        role=role,
        token=token,
        resource=resource,
        action=action,
        query_text=query_text,
    )


def check_agent_permission(
    agent_name: str,
    target: str,
    action: str = "read",
    username: str = "system",
) -> PolicyDecision:
    """
    Funksion i thjeshtë për verifikim të agjentëve.
    Zbaton Least Privilege për çdo agjent.
    
    Shembull:
        decision = check_agent_permission("KPI Calculator", "database")
        if not decision.allowed:
            raise PermissionError(decision.reason)
    """
    return zero_trust_pep.enforce_agent_access(
        agent_name=agent_name,
        target_resource=target,
        action=action,
        context_username=username,
    )
