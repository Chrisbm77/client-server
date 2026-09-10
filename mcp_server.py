#!/usr/bin/env python3
"""
JDE Assistant — Thin Client
=====================================
This is the ONLY file that runs on the client's machine. It contains no
table allowlists, no SQL validation, no schema definitions, no JDE
development reference content, and no business logic — all of that lives
on the hosted API this file talks to. There is nothing meaningful here to
strip out or reuse elsewhere; without a valid API key pointed at a live
server, this file does nothing at all.

Provides three tools: querying the live JDE database, fetching its schema,
and fetching JDE EnterpriseOne development reference documents (PAR file
structure, table/view/event-rule design, etc.) — all gated by the same
API key, all served fresh from the hosted API on every call.

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


def _handle_response(resp, result_key: str) -> str:
    if resp.status_code == 401:
        return "ACCESS ERROR: invalid API key. Contact your vendor."
    if resp.status_code == 403:
        try:
            detail = resp.json().get("detail", "Access denied.")
        except Exception:
            detail = "Access denied."
        return f"ACCESS ERROR: {detail}"
    if resp.status_code == 404:
        try:
            detail = resp.json().get("detail", "Not found.")
        except Exception:
            detail = "Not found."
        return f"NOT FOUND: {detail}"
    if resp.status_code != 200:
        return f"SERVICE ERROR: unexpected response ({resp.status_code})."
    try:
        return resp.json().get(result_key, "")
    except Exception:
        return "SERVICE ERROR: could not parse the response."


def call_api(path: str, payload: Optional[dict] = None) -> str:
    """POST helper — used by the database tools. Response body is {"result": ...}."""
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
    return _handle_response(resp, "result")


def call_api_get(path: str) -> str:
    """GET helper — used by the reference-lookup tool. Response body is {"content": ...}."""
    if not API_URL or not API_KEY:
        return (
            "CONFIGURATION ERROR: JDE_API_URL and/or JDE_API_KEY are not set. "
            "Check this connector's environment variables."
        )
    try:
        resp = requests.get(
            f"{API_URL}{path}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        return f"CONNECTION ERROR: could not reach the JDE service ({e})."
    return _handle_response(resp, "content")


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


@mcp.tool()
def get_jde_reference(topic: str) -> str:
    """Fetch a JDE EnterpriseOne 9.2 development reference document — table
    design rules, event rule syntax, PAR file structure, and so on. Use this
    whenever asked about JDE object development: creating or modifying a
    table (F-prefix), business view (V-prefix), data structure (D/T-prefix),
    business function (B/N-prefix), application (P-prefix), or report
    (R-prefix); working with PAR files; or any question about JDE naming
    conventions, object relationships, or the development lifecycle.

    Always call this with topic="core-rules" first if you haven't already
    in this conversation — it covers naming conventions and object prefixes
    that apply to every task. Then fetch only the specific topic(s) the
    task actually needs, from:

        core-rules                     - naming conventions, object prefixes, rules for every task (fetch first)
        par-file-structure              - PAR ZIP architecture, XML schemas, cross-object references, templates
        master-reference                 - unified dev guide: architecture, naming, relationships, workflow
        table-design                     - table creation, indices, triggers, column design
        business-view-design             - view creation, joins, column selection, security
        data-dictionary                  - DD items, aliases, data types, edit rules, UDCs
        data-structure-design            - BSFN and PO data structures, parameters, templates
        event-rules                      - ER logic, variables, conditions, BSFN calls, DB I/O
        form-design-aid                  - form types, controls, grids, interconnects, events
        report-design-aid                - report sections, data selection, runtime, batch
        application-design               - app architecture, form flow, processing options
        business-function-programming    - C and NER BSFNs, APIs, error handling, DLLs
        development-tools-overview       - OMW, OCM, UTB, deployment pipeline

    Each call re-fetches from the server rather than caching locally, so
    access always reflects the current state of this API key.
    """
    return call_api_get(f"/v1/reference/{topic}")


if __name__ == "__main__":
    mcp.run()
