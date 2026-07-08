"""
Unit tests for the safety-critical part of the project: query validation.
Run with: python -m pytest tests/ -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agent.tools import validate_sql, run_query, get_schema, SQLValidationError


def test_select_passes():
    validate_sql("SELECT * FROM customers")


def test_lowercase_select_passes():
    validate_sql("select name from customers")


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM customers",
        "DROP TABLE orders",
        "UPDATE customers SET name='x'",
        "INSERT INTO customers VALUES (1,2,3)",
        "ALTER TABLE customers ADD COLUMN x TEXT",
        "PRAGMA table_info(customers)",
    ],
)
def test_forbidden_statements_rejected(query):
    with pytest.raises(SQLValidationError):
        validate_sql(query)


def test_multiple_statements_rejected():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM customers; DROP TABLE customers")


def test_schema_returns_expected_tables():
    schema = get_schema()
    for table in ["customers", "products", "orders", "order_items"]:
        assert table in schema


def test_run_query_returns_rows():
    result = run_query("SELECT COUNT(*) as n FROM customers")
    assert result["row_count"] == 1
    assert result["columns"] == ["n"]


def test_run_query_rejects_write():
    with pytest.raises(SQLValidationError):
        run_query("DELETE FROM customers")
