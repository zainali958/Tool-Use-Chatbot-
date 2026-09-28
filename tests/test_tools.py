import json
import pytest
from chatbot.tools import calculate, query_database, run_tool


@pytest.mark.parametrize("expr,expected", [
    ("2+2", "4"), ("15/100*2340", "351"), ("sqrt(144)*3", "36"),
    ("2^10", "1024"), ("-3 + 10 % 4", "-1"), ("125,000,000 / 47", "2659574.4680851065"),
])
def test_calculate_ok(expr, expected):
    assert calculate(expr) == expected


@pytest.mark.parametrize("bad", ["__import__('os').system('ls')", "open('x')", "1/0", "2**99999", "abc"])
def test_calculate_rejects_unsafe(bad):
    assert calculate(bad).startswith("Error")


def test_db_select():
    out = json.loads(query_database("SELECT COUNT(*) AS n FROM customers"))
    assert out["rows"][0]["n"] == 6


@pytest.mark.parametrize("sql", ["DELETE FROM orders", "DROP TABLE customers",
                                 "SELECT 1; DROP TABLE orders", "UPDATE products SET price=0"])
def test_db_blocks_writes(sql):
    assert query_database(sql).startswith("Error")


def test_db_bad_column_returns_error():
    assert "Error" in query_database("SELECT nope FROM customers")


def test_dispatcher_errors():
    assert "unknown tool" in run_tool("hack", {})
    assert "missing required" in run_tool("calculate", {})
    assert run_tool("calculate", '{"expression": "1+1"}') == "2"
    assert run_tool("calculate", {"expression": "1+1", "junk": 1}) == "2"
