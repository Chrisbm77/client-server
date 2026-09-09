#!/usr/bin/env python3
"""Fetch a JDE development reference document from the hosted skill API.

This is the ONLY thing that stands between this skill and its actual
knowledge content — the reference documents themselves are not on this
machine. Every call re-fetches from the server, so disabling this
deployment's key on the server side stops the skill from working
immediately, not just from receiving future updates.

Usage:
    python fetch_reference.py <topic>

Requires JDE_API_URL and JDE_API_KEY environment variables (set these in
whatever launches Claude Code / the skill's environment — the same two
variables used by the JDE Database Assistant connector, if this client
also has that; otherwise your own vendor-issued key for this skill).

Valid topics (ask the skill's SKILL.md, or run with no topic, for the
current list): par-file-structure, master-reference, table-design,
business-view-design, data-dictionary, data-structure-design,
event-rules, form-design-aid, report-design-aid, application-design,
business-function-programming, development-tools-overview, core-rules.
"""
import os
import sys

import requests

API_URL = os.environ.get("JDE_API_URL", "").rstrip("/")
API_KEY = os.environ.get("JDE_API_KEY", "").strip()
REQUEST_TIMEOUT_SECONDS = 20


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python fetch_reference.py <topic>", file=sys.stderr)
        return 1
    topic = sys.argv[1]

    if not API_URL or not API_KEY:
        print(
            "CONFIGURATION ERROR: JDE_API_URL and/or JDE_API_KEY are not set. "
            "Check this skill's environment variables."
        )
        return 1

    try:
        resp = requests.get(
            f"{API_URL}/v1/reference/{topic}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        print(f"CONNECTION ERROR: could not reach the reference service ({e}).")
        return 1

    if resp.status_code == 401:
        print("ACCESS ERROR: invalid API key. Contact your vendor.")
        return 1
    if resp.status_code == 403:
        try:
            detail = resp.json().get("detail", "Access denied.")
        except Exception:
            detail = "Access denied."
        print(f"ACCESS ERROR: {detail}")
        return 1
    if resp.status_code == 404:
        try:
            detail = resp.json().get("detail", f"Unknown topic '{topic}'.")
        except Exception:
            detail = f"Unknown topic '{topic}'."
        print(f"NOT FOUND: {detail}")
        return 1
    if resp.status_code != 200:
        print(f"SERVICE ERROR: unexpected response ({resp.status_code}).")
        return 1

    try:
        print(resp.json().get("content", ""))
    except Exception:
        print("SERVICE ERROR: could not parse the response.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
