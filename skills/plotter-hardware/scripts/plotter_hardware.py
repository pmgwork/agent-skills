#!/usr/bin/env python3
"""Dependency-free client for the Plotter Hardware REST API.

Mutating commands are dry-run by default. Add --execute only after the
hardware state and the requested physical action have been confirmed.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any, Mapping, Optional


READ_COMMANDS = {
    "info": ("GET", "/plotter/"),
    "status": ("GET", "/plotter/status"),
    "solenoid-info": ("GET", "/solenoid/"),
    "solenoid-status": ("GET", "/solenoid/status"),
    "servo-status": ("GET", "/servo/status"),
    "actuators-status": ("GET", "/actuators/status"),
    "actuators-config": ("GET", "/actuators/config"),
    "drawing-status": ("GET", "/drawing/status"),
    "openapi": ("GET", "/openapi.json"),
}

JSON_WRITE_PATHS = {
    "connect": "/plotter/connect",
    "disconnect": "/plotter/disconnect",
    "home": "/plotter/home",
    "move-default": "/plotter/move_to_default",
    "move-to": "/plotter/move_to",
    "servo-up": "/servo/up",
    "servo-down": "/servo/down",
    "actuator-up": "/actuators/{tool}/up",
    "actuator-down": "/actuators/{tool}/down",
    "solenoid-toggle": "/solenoid/toggle",
    "pulse": "/solenoid/pulse",
    "dispose": "/solenoid/dispose",
    "draw-to": "/drawing/draw_to",
}


def finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("must be a finite number")
    return number


def non_negative_float(value: str) -> float:
    number = finite_float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return number


def positive_float(value: str) -> float:
    number = finite_float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def add_execute(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--execute",
        action="store_true",
        help="send the mutating request; without this flag only show a dry run",
    )


def add_boolean_option(parser: argparse.ArgumentParser, name: str) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f"--{name.replace('_', '-')}",
        dest=name,
        action="store_true",
    )
    group.add_argument(
        f"--no-{name.replace('_', '-')}",
        dest=name,
        action="store_false",
    )
    parser.set_defaults(**{name: None})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "PLOTTER_HARDWARE_URL",
            "http://localhost:8080",
        ),
        help="API base URL (default: PLOTTER_HARDWARE_URL or localhost:8080)",
    )
    parser.add_argument("--timeout", type=positive_float, default=10.0)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in READ_COMMANDS:
        subparsers.add_parser(command)

    for command in (
        "connect",
        "disconnect",
        "home",
        "move-default",
        "servo-up",
        "servo-down",
        "dispose",
    ):
        child = subparsers.add_parser(command)
        add_execute(child)

    move = subparsers.add_parser("move-to")
    move.add_argument("--x", required=True, type=finite_float)
    move.add_argument("--y", required=True, type=finite_float)
    add_execute(move)

    actuator_tools = ("pen", "eraser", "solenoid")
    for command in ("actuator-up", "actuator-down"):
        child = subparsers.add_parser(command)
        child.add_argument("--tool", required=True, choices=actuator_tools)
        add_execute(child)

    for command in ("pulse", "solenoid-toggle"):
        child = subparsers.add_parser(command)
        if command == "pulse":
            child.add_argument("--duration", type=positive_float)
        child.add_argument("--port")
        child.add_argument("--pin")
        child.add_argument("--default-state", choices=("LOW", "HIGH"))
        add_execute(child)

    draw = subparsers.add_parser("draw-to")
    draw.add_argument("--x", required=True, type=finite_float)
    draw.add_argument("--y", required=True, type=finite_float)
    draw.add_argument("--pen", required=True, choices=("pen", "eraser", "solenoid", "servo"))
    draw.add_argument("--delay", type=non_negative_float)
    add_boolean_option(draw, "eraser_position_correction")
    add_execute(draw)

    plot = subparsers.add_parser("plot-svg")
    plot.add_argument("--file", required=True, type=Path)
    plot.add_argument("--pen", required=True, choices=("pen", "eraser", "solenoid", "servo"))
    plot.add_argument(
        "--options",
        default="{}",
        help="JSON object for the server's SVG options field",
    )
    add_execute(plot)

    job_status = subparsers.add_parser("plot-status")
    job_status.add_argument("--job-id", required=True)

    cancel = subparsers.add_parser("plot-cancel")
    cancel.add_argument("--job-id", required=True)
    add_execute(cancel)
    return parser


def print_response(status: int, raw: str) -> None:
    print(f"HTTP {status}")
    if not raw:
        return
    try:
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(raw)


def request(
    method: str,
    url: str,
    timeout: float,
    body: Optional[Mapping[str, Any]] = None,
    data: Optional[bytes] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> int:
    if body is not None and data is not None:
        raise ValueError("body and data are mutually exclusive")
    request_data = (
        json.dumps(body, ensure_ascii=False).encode("utf-8")
        if body is not None
        else data
    )
    request_headers = {"Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=request_data,
        headers=request_headers,
        method=method,
    )

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


def multipart_svg(file_path: Path, pen: str, options: str) -> tuple[bytes, str]:
    try:
        parsed_options = json.loads(options)
    except json.JSONDecodeError as error:
        raise ValueError("--options must be valid JSON") from error
    if not isinstance(parsed_options, dict):
        raise ValueError("--options must be a JSON object")
    if not file_path.is_file():
        raise ValueError(f"SVG file not found: {file_path}")

    boundary = f"----PlotterHardware{uuid.uuid4().hex}"
    file_data = file_path.read_bytes()
    parts = []

    def add_field(name: str, value: str) -> None:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
            f"\r\n\r\n{value}\r\n".encode("utf-8")
        )

    add_field("pen", pen)
    add_field("options", options)
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; '
            f'name="file"; filename="{file_path.name}"\r\n'
            "Content-Type: image/svg+xml\r\n\r\n"
        ).encode("utf-8")
        + file_data
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def dry_run(method: str, url: str, body: Optional[Mapping[str, Any]] = None) -> int:
    print("Dry run; no request sent. Add --execute to perform this operation.")
    print(f"{method} {url}")
    if body is not None:
        print(json.dumps(body, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    if args.command in READ_COMMANDS:
        method, path = READ_COMMANDS[args.command]
        return request(method, base_url + path, args.timeout)

    if args.command == "plot-status":
        return request("GET", f"{base_url}/drawing/jobs/{args.job_id}", args.timeout)

    if args.command == "plot-cancel":
        url = f"{base_url}/drawing/jobs/{args.job_id}/cancel"
        if not args.execute:
            return dry_run("POST", url, {})
        return request("POST", url, args.timeout, body={})

    if args.command == "plot-svg":
        url = f"{base_url}/drawing/jobs"
        dry_body = {
            "file": str(args.file),
            "pen": args.pen,
            "options": args.options,
        }
        if not args.execute:
            return dry_run("POST", url, dry_body)
        try:
            data, content_type = multipart_svg(args.file, args.pen, args.options)
        except (OSError, ValueError) as error:
            print(f"Invalid SVG request: {error}", file=sys.stderr)
            return 2
        return request(
            "POST",
            url,
            args.timeout,
            data=data,
            headers={"Content-Type": content_type},
        )

    body: dict[str, Any] = {}
    path = JSON_WRITE_PATHS[args.command]
    if args.command == "move-to":
        body = {"x": args.x, "y": args.y}
    elif args.command in {"actuator-up", "actuator-down"}:
        path = JSON_WRITE_PATHS[args.command].format(tool=args.tool)
    elif args.command in {"pulse", "solenoid-toggle"}:
        if (args.port is None) != (args.pin is None):
            parser.error("--port and --pin must be specified together")
        if args.command == "pulse" and args.duration is not None:
            body["duration"] = args.duration
        if args.port is not None:
            body["port"] = args.port
            body["pin"] = args.pin
        if args.default_state is not None:
            body["default_state"] = args.default_state
        path = JSON_WRITE_PATHS[args.command]
    elif args.command == "draw-to":
        body = {"x": args.x, "y": args.y, "pen": args.pen}
        if args.delay is not None:
            body["delay"] = args.delay
        if args.eraser_position_correction is not None:
            body["eraser_position_correction"] = args.eraser_position_correction
        path = JSON_WRITE_PATHS[args.command]
    else:
        path = JSON_WRITE_PATHS[args.command]

    url = base_url + path
    if not args.execute:
        return dry_run("POST", url, body)

    return request("POST", url, args.timeout, body=body)


if __name__ == "__main__":
    raise SystemExit(main())
