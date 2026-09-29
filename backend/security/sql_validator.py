"""
SQL Injection Prevention Module
"""
import re
from typing import Tuple

DANGEROUS_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
    "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
    "PRAGMA", "ATTACH", "DETACH",
    "SHUTDOWN", "LOAD_FILE", "OUTFILE", "DUMPFILE"
]

DANGEROUS_PREFIXES = ["xp_", "sp_cmdshell"]

DANGEROUS_PATTERNS = [
    r";\s*DROP\s+",
    r";\s*DELETE\s+",
    r";\s*INSERT\s+",
    r";\s*UPDATE\s+",
    r"'\s*OR\s*'1'\s*=\s*'1",
    r"'\s*OR\s*1\s*=\s*1",
    r"1\s*=\s*1\s*--",
    r"SLEEP\s*\(\s*\d+\s*\)",
    r"BENCHMARK\s*\(",
    r"WAITFOR\s+DELAY",
]

ALLOWED_TABLES = [
    "fact_sales", "dim_date", "dim_geography",
    "dim_product", "dim_customer"
]


def _extract_cte_names(sql: str) -> list:
    """Merr emrat e CTE-ve nga WITH clause."""
    cte_names = re.findall(r'\b(\w+)\s+AS\s*\(', sql, re.IGNORECASE)
    return [name.lower() for name in cte_names]


def validate_sql(sql: str) -> Tuple[bool, str]:
    if not sql or not sql.strip():
        return False, "SQL query është bosh!"

    sql_upper = sql.upper().strip()

    # 1. Vetëm SELECT ose WITH lejohet
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return False, "⛔ Vetëm SELECT queries lejohen!"

    # 2. Kontrollo keywords të rrezikshme
    for keyword in DANGEROUS_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, sql_upper):
            return False, f"⛔ SQL Injection detected: keyword '{keyword}' i ndaluar!"

    # 3. Kontrollo prefixe të rrezikshme
    for prefix in DANGEROUS_PREFIXES:
        if prefix.upper() in sql_upper:
            return False, f"⛔ Prefix i rrezikshëm: '{prefix}'"

    # 4. Kontrollo patterns të rrezikshme
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, "⛔ SQL Injection pattern detected!"

    # 5. Kontrollo tabelat — por lejo CTE names
    cte_names = _extract_cte_names(sql)
    
    tables_in_query = re.findall(
        r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)', sql, re.IGNORECASE
    )
    
    # Alias të zakonshme që lejohen
    common_aliases = {
        "cte", "subq", "t", "a", "b", "s", "f", "q",
        "t1", "t2", "t3", "main", "sub", "data", "result",
        "results", "summary", "base", "ranked", "filtered"
    }
    
    for match in tables_in_query:
        table = (match[0] or match[1]).lower()
        if not table:
            continue
        # Lejo nëse është CTE name
        if table in cte_names:
            continue
        # Lejo alias të zakonshme
        if table in common_aliases:
            continue
        # Lejo tabela të lejuara
        if table in ALLOWED_TABLES:
            continue
        # Blloko vetëm nëse nuk është asnjë nga sa sipër
        return False, f"⛔ Tabela '{table}' nuk lejohet!"

    # 6. Kontrollo gjatësinë
    if len(sql) > 10000:
        return False, "⛔ SQL query është shumë e gjatë!"

    return True, "✅ SQL query është e sigurt!"


def sanitize_input(user_input: str) -> str:
    if not user_input:
        return ""
    sanitized = re.sub(r"['\";\\]", "", user_input)
    for keyword in ["DROP", "DELETE", "INSERT", "UPDATE", "EXEC"]:
        sanitized = re.sub(r'\b' + keyword + r'\b', "", sanitized, flags=re.IGNORECASE)
    return sanitized[:500].strip()


def check_rate_limit(username: str, query_count: dict) -> Tuple[bool, str]:
    import time
    current_time = int(time.time())
    hour_ago = current_time - 3600
    if username not in query_count:
        query_count[username] = []
    query_count[username] = [t for t in query_count[username] if t > hour_ago]
    if len(query_count[username]) >= 50:
        return False, "⛔ Rate limit: Max 50 queries/orë!"
    query_count[username].append(current_time)
    return True, "OK"


def get_security_report(sql: str) -> dict:
    is_valid, message = validate_sql(sql)
    risks = []
    sql_upper = sql.upper()

    for keyword in DANGEROUS_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, sql_upper):
            risks.append({"type": "dangerous_keyword", "value": keyword, "severity": "HIGH"})

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            risks.append({"type": "dangerous_pattern", "value": pattern, "severity": "CRITICAL"})

    return {
        "is_valid": is_valid,
        "message": message,
        "risks": risks,
        "risk_level": "CRITICAL" if any(r["severity"] == "CRITICAL" for r in risks)
                      else "HIGH" if risks else "LOW",
        "sql_length": len(sql),
        "starts_with_select": sql_upper.strip().startswith(("SELECT", "WITH"))
    }
