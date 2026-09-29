"""
Output Validator — Zero Trust Output Validation
================================================
Parimi Zero Trust: Edhe outputi i agjentëve duhet verifikuar.
Asnjë rezultat nuk besohet automatikisht — kontrollohet para se t'i kthehet user-it.

Funksionet:
- validate_sql_output(): Kontrollo SQL-in e gjeneruar nga AI
- validate_agent_output(): Kontrollo outputin e çdo agjenti
- sanitize_response(): Pastro të dhëna sensitive nga outputi
- check_data_leakage(): Kontrollo nëse outputi ekspozon të dhëna sensitive
"""
from __future__ import annotations
import re
import json
from typing import Any


# ── Kolona sensitive që nuk duhen ekspozuar ───────────────────────────────────
SENSITIVE_COLUMNS = [
    "password", "password_hash", "token", "api_key", "secret",
    "credit_card", "ssn", "email", "phone", "address"
]

# ── Patterns të dhënash sensitive ─────────────────────────────────────────────
SENSITIVE_PATTERNS = [
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',            # Credit card
    r'sk-[a-zA-Z0-9]{32,}',                                      # API keys
    r'gsk_[a-zA-Z0-9]{32,}',                                     # Groq keys
    r'sk-ant-[a-zA-Z0-9-]{32,}',                                 # Anthropic keys
]


class OutputValidator:
    """
    Zero Trust Output Validator.
    Çdo output i sistemit kalon nëpër validim para se të kthehet user-it.
    """

    def validate_agent_output(
        self,
        agent_name: str,
        output: dict,
        user_role: str = "viewer",
    ) -> tuple[bool, str, dict]:
        """
        Valido outputin e një agjenti.
        Returns: (is_valid, message, cleaned_output)
        """
        if not output:
            return True, "Output bosh — OK", output

        cleaned = dict(output)

        # 1. Kontrollo nëse outputi përmban SQL të rrezikshëm
        if "sql" in cleaned:
            sql_valid, sql_msg = self._validate_sql_content(cleaned["sql"])
            if not sql_valid:
                cleaned["sql"] = "[REDACTED — SQL i rrezikshëm]"
                return False, f"Zero Trust Output: SQL i rrezikshëm nga '{agent_name}': {sql_msg}", cleaned

        # 2. Kontrollo data leakage
        if "data" in cleaned and isinstance(cleaned["data"], list):
            cleaned["data"], leak_found = self._check_data_leakage(
                cleaned["data"], user_role
            )
            if leak_found:
                return False, f"Zero Trust Output: Data leakage i detektuar nga '{agent_name}'", cleaned

        # 3. Apliko row limit bazuar në role
        if "data" in cleaned and isinstance(cleaned["data"], list):
            max_rows = self._get_max_rows(user_role)
            if len(cleaned["data"]) > max_rows:
                cleaned["data"] = cleaned["data"][:max_rows]
                cleaned["_zero_trust_note"] = f"Të dhënat u kufizuan në {max_rows} rreshta (Zero Trust Least Privilege)"

        # 4. Redakto informacion sensitive nga explanation/error
        for field in ["explanation", "error", "message"]:
            if field in cleaned and cleaned[field]:
                cleaned[field] = self._redact_sensitive_info(str(cleaned[field]))

        return True, "Output valid", cleaned

    def validate_sql_output(self, sql: str, agent_name: str) -> tuple[bool, str]:
        """
        Valido SQL-in e gjeneruar nga AI para ekzekutimit.
        Shtresë shtesë mbi SQL Validator ekzistues.
        """
        if not sql or not sql.strip():
            return False, "SQL bosh"

        # Kontrollo nëse SQL u gjenerua nga agjenti i duhur
        dangerous_in_output = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
            "TRUNCATE", "EXEC", "GRANT", "REVOKE"
        ]
        sql_upper = sql.upper()
        for kw in dangerous_in_output:
            if re.search(r'\b' + kw + r'\b', sql_upper):
                return False, f"Zero Trust Output Validation: AI gjeneroi keyword të rrezikshëm '{kw}'"

        # Kontrollo nëse SQL ekspozon tabela të ndjeshme
        suspicious_tables = ["users", "auth", "passwords", "tokens", "secrets", "keys"]
        for table in suspicious_tables:
            if re.search(r'\b' + table + r'\b', sql, re.IGNORECASE):
                return False, f"Zero Trust: SQL tenton të aksesojë tabelën e ndjeshme '{table}'"

        return True, "SQL output valid"

    def sanitize_for_role(self, data: list[dict], role: str) -> list[dict]:
        """
        Filtro të dhënat bazuar në rolin e user-it.
        Viewer sheh vetëm kolona analitike, jo sensitive.
        """
        if not data or role == "admin":
            return data

        # Kolona të lejuara per Viewer (vetëm analitike)
        viewer_allowed = {
            "region", "country", "category", "subcategory",
            "customer_segment", "year", "quarter", "month",
            "month_name", "revenue", "profit", "cost",
            "quantity", "profit_margin", "unit_price",
            "rank", "growth", "yoy_growth_pct", "mom_change_pct",
            "total_revenue", "total_profit", "avg_margin",
        }

        sanitized = []
        for row in data:
            if role == "viewer":
                sanitized.append({
                    k: v for k, v in row.items()
                    if k.lower() in viewer_allowed
                })
            else:
                sanitized.append(row)

        return sanitized

    def _validate_sql_content(self, sql: str) -> tuple[bool, str]:
        """Valido përmbajtjen e SQL."""
        if not sql:
            return True, "OK"
        dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]
        sql_upper = sql.upper()
        for kw in dangerous:
            if re.search(r'\b' + kw + r'\b', sql_upper):
                return False, f"Keyword i rrezikshëm: {kw}"
        return True, "OK"

    def _check_data_leakage(
        self, data: list[dict], role: str
    ) -> tuple[list[dict], bool]:
        """Kontrollo dhe pastro data leakage."""
        leak_found = False
        cleaned = []

        for row in data:
            clean_row = {}
            for key, value in row.items():
                # Kontrollo nëse kolona është sensitive
                if any(s in key.lower() for s in SENSITIVE_COLUMNS):
                    clean_row[key] = "****"
                    leak_found = True
                    continue

                # Kontrollo nëse vlera përmban patterns sensitive
                if isinstance(value, str):
                    for pattern in SENSITIVE_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            clean_row[key] = "****"
                            leak_found = True
                            break
                    else:
                        clean_row[key] = value
                else:
                    clean_row[key] = value

            cleaned.append(clean_row)

        return cleaned, leak_found

    def _get_max_rows(self, role: str) -> int:
        """Merr numrin maksimal të rreshtave bazuar në rol."""
        limits = {"admin": 50000, "analyst": 10000, "viewer": 1000}
        return limits.get(role, 500)

    def _redact_sensitive_info(self, text: str) -> str:
        """Redakto informacion sensitive nga teksti."""
        for pattern in SENSITIVE_PATTERNS:
            text = re.sub(pattern, "****", text, flags=re.IGNORECASE)
        return text


# ── Singleton instance ────────────────────────────────────────────────────────
output_validator = OutputValidator()
