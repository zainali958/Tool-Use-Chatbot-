"""Tool implementations + JSON schemas + a safe dispatcher.

Every tool returns a *string* (the model reads it) and never raises:
errors are returned as text so the model can retry or explain.
"""
from __future__ import annotations

import ast
import json
import math
import operator
import re
import sqlite3
from typing import Any, Callable

import requests

from .seed_db import DB_PATH, create_db

TIMEOUT = 10
MAX_ROWS = 50

# ---------------------------------------------------------------- calculator
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
          "log": math.log, "log10": math.log10, "exp": math.exp, "abs": abs,
          "round": round, "floor": math.floor, "ceil": math.ceil}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent too large")
        return _BIN[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS and not node.keywords):
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise ValueError("unsupported expression")


def calculate(expression: str) -> str:
    expr = expression.strip().replace("^", "**")
    if re.fullmatch(r"[\d\s,.+\-*/()%]+", expr):  # pure numbers: allow thousands separators
        expr = expr.replace(",", "")
    try:
        result = _eval(ast.parse(expr, mode="eval").body)
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception as exc:  # noqa: BLE001
        return f"Error: could not evaluate '{expression}' ({exc})"
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return str(result)


# ------------------------------------------------------------------- weather
_WMO = {0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
        45: "fog", 48: "rime fog", 51: "light drizzle", 53: "drizzle",
        55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
        71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
        81: "heavy rain showers", 95: "thunderstorm", 96: "thunderstorm with hail"}


def get_weather(city: str) -> str:
    try:
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": city, "count": 1}, timeout=TIMEOUT)
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return f"Error: city '{city}' not found"
        place = results[0]
        wx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": place["latitude"], "longitude": place["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"},
            timeout=TIMEOUT)
        wx.raise_for_status()
        cur = wx.json()["current"]
        return json.dumps({
            "location": f"{place['name']}, {place.get('country', '')}",
            "temperature_c": cur["temperature_2m"],
            "humidity_percent": cur["relative_humidity_2m"],
            "wind_kmh": cur["wind_speed_10m"],
            "conditions": _WMO.get(cur["weather_code"], f"code {cur['weather_code']}"),
        })
    except requests.RequestException as exc:
        return f"Error: weather service unavailable ({exc.__class__.__name__})"


# ---------------------------------------------------------------- web search
def search_web(query: str, max_results: int = 4) -> str:
    try:
        try:
            from ddgs import DDGS
        except ImportError:  # older package name
            from duckduckgo_search import DDGS
        hits = list(DDGS().text(query, max_results=max(1, min(int(max_results), 8))))
    except Exception as exc:  # noqa: BLE001
        return f"Error: search failed ({exc.__class__.__name__}: {exc})"
    if not hits:
        return "No results found."
    return json.dumps([{"title": h.get("title"), "snippet": h.get("body"),
                        "url": h.get("href")} for h in hits], ensure_ascii=False)


# ------------------------------------------------------------------ database
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum)\b", re.I)


def query_database(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    if not re.match(r"^(select|with)\b", sql, re.I):
        return "Error: only SELECT queries are allowed"
    if ";" in sql or _FORBIDDEN.search(sql):
        return "Error: query contains forbidden statements"
    create_db()
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=TIMEOUT)
        con.execute("PRAGMA query_only = ON")
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS + 1)
        con.close()
    except sqlite3.Error as exc:
        return f"Error: SQL failed ({exc}). Check table and column names."
    truncated = len(rows) > MAX_ROWS
    out = [dict(zip(cols, r)) for r in rows[:MAX_ROWS]]
    return json.dumps({"rows": out, "truncated": truncated}, default=str)


# ------------------------------------------------------- schemas + dispatcher
SCHEMA_DESC = ("SQLite store database. Tables: customers(id, name, city), "
               "products(id, name, category, price), "
               "orders(id, customer_id, product_id, quantity, order_date 'YYYY-MM-DD').")

TOOLS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city. Use for temperature, wind or conditions questions.",
        "parameters": {"type": "object", "properties": {
            "city": {"type": "string", "description": "City name, e.g. 'Islamabad'"}},
            "required": ["city"]}}},
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Evaluate a math expression exactly. Supports + - * / ** %, sqrt, log, sin, cos, pi. Always use this for arithmetic instead of computing in your head.",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string", "description": "e.g. '125000000 / 47' or 'sqrt(144) * 3'"}},
            "required": ["expression"]}}},
    {"type": "function", "function": {
        "name": "search_web",
        "description": "Search the web for current facts, news or anything you don't know. Returns titles, snippets and URLs.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Number of results (1-8), default 4"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "query_database",
        "description": "Run a read-only SQL SELECT on the store database. " + SCHEMA_DESC,
        "parameters": {"type": "object", "properties": {
            "sql": {"type": "string", "description": "A single SQLite SELECT statement"}},
            "required": ["sql"]}}},
]

REGISTRY: dict[str, Callable[..., str]] = {
    "get_weather": get_weather, "calculate": calculate,
    "search_web": search_web, "query_database": query_database,
}


def run_tool(name: str, args: Any) -> str:
    """Validate and execute a tool call. Never raises."""
    if name not in REGISTRY:
        return f"Error: unknown tool '{name}'. Available: {', '.join(REGISTRY)}"
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return "Error: arguments must be a JSON object"
    if not isinstance(args, dict):
        return "Error: arguments must be a JSON object"
    spec = next(t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == name)
    missing = [k for k in spec["required"] if k not in args]
    if missing:
        return f"Error: missing required argument(s): {', '.join(missing)}"
    args = {k: v for k, v in args.items() if k in spec["properties"]}
    try:
        return REGISTRY[name](**args)
    except Exception as exc:  # noqa: BLE001
        return f"Error: tool '{name}' crashed ({exc.__class__.__name__}: {exc})"
