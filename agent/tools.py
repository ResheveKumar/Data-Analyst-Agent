"""
Tools the agent can call: schema inspection and safe, read-only SQL execution.
This is the part of the project that shows judgment, not just API-calling —
the agent is constrained to read-only queries, row limits, and timeouts.
"""

import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "ecommerce.db"

# Anything outside a plain SELECT is refused. This is a deliberate design
# choice worth calling out in an interview: the agent should never be able
# to mutate data, even if a prompt injection or bad model output tries to
# make it run DELETE/DROP/UPDATE/ATTACH/PRAGMA etc.
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|TRIGGER)\b",
    re.IGNORECASE,
)
MAX_ROWS = 200


def get_schema() -> str:
    """Return the database schema (tables + columns) as a string the LLM can read."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]

    schema_lines = []
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()
        col_desc = ", ".join(f"{c[1]} ({c[2]})" for c in cols)
        schema_lines.append(f"TABLE {table}: {col_desc}")

    conn.close()
    return "\n".join(schema_lines)


class SQLValidationError(Exception):
    pass


def validate_sql(query: str) -> None:
    stripped = query.strip().rstrip(";")
    if not stripped.upper().startswith("SELECT"):
        raise SQLValidationError("Only SELECT statements are allowed.")
    if FORBIDDEN_KEYWORDS.search(stripped):
        raise SQLValidationError("Query contains a forbidden keyword (write/DDL operation).")
    if ";" in stripped:
        raise SQLValidationError("Multiple statements are not allowed.")


def run_query(query: str) -> dict:
    """
    Execute a read-only SQL query safely and return rows + column names.
    Raises SQLValidationError for anything unsafe; caller should feed that
    error back to the LLM so it can self-correct.
    """
    validate_sql(query)

    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA query_only = ON;")  # belt-and-suspenders: DB-level read-only
    cur = conn.cursor()
    try:
        cur.execute(query)
        rows = cur.fetchmany(MAX_ROWS)
        columns = [desc[0] for desc in cur.description] if cur.description else []
    finally:
        conn.close()

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": len(rows) == MAX_ROWS,
    }
