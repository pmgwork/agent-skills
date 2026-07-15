#!/usr/bin/env python3
"""Small, dependency-free client for the BotHub Hardware REST API."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
from typing import Any


READ_COMMANDS = {
    "info": ("GET", "/axiDraw/"),
    "status": ("GET", "/axiDraw/status"),
    "solenoid-info": ("GET", "/solenoid/"),
    "solenoid-status": ("GET", "/solenoid/status"),
}

WRITE_COMMANDS = {
    "connect": "/axiDraw/connect",
    "disconnect": "/axiDraw/disconnect",
    "move-default": "/axiDraw/move_to_default",
    "move-to": "/axiDraw/move_to",
    "pulse": "/solenoid/pulse",
    "dispose": "/solenoid/dispose",
}


def finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("must be a finite number")
    return number


def positive_float(value: str) -> float:
    number = finite_float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BOTHUB_HARDWARE_URL", "http://localhost:8080"),
        help="API base URL (default: BOTHUB_HARDWARE_URL or http://localhost:8080)",
    )
    parser.add_argument("--timeout", type=positive_float, default=10.0)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in READ_COMMANDS:
        subparsers.add_parser(command)

    for command in ("connect", "disconnect", "move-default", "dispose"):
        child = subparsers.add_parser(command)
        child.add_argument("--execute", action="store_true")

    move = subparsers.add_parser("move-to")
    move.add_argument("--x", required=True, type=finite_float)
    move.add_argument("--y", required=True, type=finite_float)
    move.add_argument("--execute", action="store_true")

    pulse = subparsers.add_parser("pulse")
    pulse.add_argument("--duration", type=positive_float)
    pulse.add_argument("--port")
    pulse.add_argument("--pin")
    pulse.add_argument("--default-state", choices=("LOW", "HIGH"))
    pulse.add_argument("--execute", action="store_true")
    return parser


def request(method: str, url: str, body: dict[str, Any], timeout: float) -> int:
    data = json.dumps(body).encode("utf-8") if method == "POST" else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        print_response(error.code, raw)
        return 1
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"Request failed: {error}", file=sys.stderr)
        return 1

    print_response(status, raw)
    return 0


def print_response(status: int, raw: str) -> None:
    print(f"HTTP {status}")
    if not raw:
        return
    try:
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(raw)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    if args.command in READ_COMMANDS:
        method, path = READ_COMMANDS[args.command]
        return request(method, base_url + path, {}, args.timeout)

    path = WRITE_COMMANDS[args.command]
    body: dict[str, Any] = {}
    if args.command == "move-to":
        body = {"x": args.x, "y": args.y}
    elif args.command == "pulse":
        if (args.port is None) != (args.pin is None):
            parser.error("--port and --pin must be specified together")
        if args.duration is not None:
            body["duration"] = args.duration
        if args.port is not None:
            body["port"] = args.port
            body["pin"] = args.pin
        if args.default_state is not None:
            body["default_state"] = args.default_state

    if not args.execute:
        print("Dry run; no request sent. Add --execute to perform this operation.")
        print(f"POST {base_url + path}")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0

    return request("POST", base_url + path, body, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
