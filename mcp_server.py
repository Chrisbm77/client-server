#!/usr/bin/env python3
"""
JDE Database Assistant — Thin Client
=====================================
This is the ONLY file that runs on the client's machine. It contains no
table allowlists, no SQL validation, no schema definitions, and no
business logic — all of that lives on the hosted API this file talks to.
There is nothing meaningful here to strip out or reuse elsewhere; without
a valid API key pointed at a live server, this file does nothing at all.

Setup:
    pip install mcp requests

Connect it to Claude Desktop:
    Settings -> Connectors -> Add custom connector
    Command: python3
    Args: /full/path/to/mcp_server.py
    Environment variables:
        JDE_API_URL = https://your-server.example.com
        JDE_API_KEY = <the deployment-specific key you were given>
"""
import os
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

API_URL = os.environ.get("JDE_API_URL", "").rstrip("/")
API_KEY = os.environ.get("JDE_API_KEY", "").strip()
REQUEST_TIMEOUT_SECONDS = 20

mcp = FastMCP("jde-database")


def call_api(path: str, payload: Optional[dict] = None) -> str:
    if not API_URL or not API_KEY:
        return (
            "CONFIGURATION ERROR: JDE_API_URL and/or JDE_API_KEY are not set. "
            "Check this connector's environment variables."
        )
    try:
        resp = requests.post(
            f"{API_URL}{path}",
            json=payload or {},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        return f"CONNECTION ERROR: could not reach the JDE service ({e})."

    if resp.status_code == 401:
        return "ACCESS ERROR: invalid API key. Contact your vendor."
    if resp.status_code == 403:
        try:
            detail = resp.json().get("detail", "Access denied.")
        except Exception:
            detail = "Access denied."
        return f"ACCESS ERROR: {detail}"
    if resp.status_code != 200:
        return f"SERVICE ERROR: unexpected response ({resp.status_code})."

    try:
        return resp.json().get("result", "")
    except Exception:
        return "SERVICE ERROR: could not parse the response."


@mcp.tool()
def query_jde_database(sql: str) -> str:
    """Execute a read-only SQL SELECT statement against the JDE database
    and return the results as text. Only single SELECT statements against
    approved tables are permitted, and results are capped — ask a more
    specific question if you need a narrower slice of data.
    """
    return call_api("/v1/query", {"sql": sql})


@mcp.tool()
def get_jde_schema() -> str:
    """Return the database schema, column descriptions, and example
    question/SQL pairs for the JDE database. Call this first if you don't
    already know the schema, before writing SQL.
    """
    return call_api("/v1/schema")


if __name__ == "__main__":
    mcp.run()
