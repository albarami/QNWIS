"""CLI helpers for running and managing the QNWIS API service."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence

from ..api.server import create_app
from ..config.settings import Settings
from ..security import AuthProvider


def _load_provider() -> AuthProvider:
    return AuthProvider()


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("uvicorn is not installed. Run `pip install uvicorn[standard]`.", file=sys.stderr)
        return 1

    settings = Settings()
    app = create_app(settings)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        log_level=args.log_level,
    )
    return 0


def cmd_keys_create(args: argparse.Namespace) -> int:
    provider = _load_provider()
    plaintext, record = provider.issue_api_key(
        subject=args.subject,
        roles=args.roles,
        ttl_seconds=args.ttl,
        ratelimit_id=args.ratelimit_id,
    )
    print("API key issued")
    print(f"Key ID: {record.key_id}")
    print(f"Subject: {record.principal.subject}")
    print(f"Roles: {', '.join(record.principal.roles)}")
    if args.ttl:
        print(f"Expires in: {args.ttl} seconds")
    print("\nStore this key securely:\n")
    print(plaintext)
    return 0


def cmd_keys_list(_: argparse.Namespace) -> int:
    provider = _load_provider()
    records = provider.list_api_keys()
    if not records:
        print("No API keys registered.")
        return 0
    for record in records:
        remaining = int(record.expires_at - time.time()) if record.expires_at else None
        print(
            f"{record.key_id} :: subject={record.principal.subject} "
            f"roles={','.join(record.principal.roles)} "
            f"ratelimit={record.principal.ratelimit_id} "
            f"expires_in={remaining if remaining is not None else 'never'}"
        )
    return 0


def cmd_keys_revoke(args: argparse.Namespace) -> int:
    provider = _load_provider()
    if provider.revoke_api_key(args.key_id):
        print(f"Revoked key {args.key_id}")
        return 0
    print(f"Key {args.key_id} not found.", file=sys.stderr)
    return 1


def cmd_openapi(_: argparse.Namespace) -> int:
    app = create_app(Settings())
    schema = app.openapi()
    print(json.dumps(schema, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QNWIS API management CLI")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start API server")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--workers", type=int, default=1)
    serve.add_argument("--reload", action="store_true")
    serve.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug"],
    )
    serve.set_defaults(func=cmd_serve)

    keys = sub.add_parser("keys", help="API key management")
    keys_sub = keys.add_subparsers(dest="keys_command")

    k_create = keys_sub.add_parser("create", help="Create API key")
    k_create.add_argument("--subject", required=True)
    k_create.add_argument("--roles", nargs="+", default=["analyst"])
    k_create.add_argument("--ratelimit-id", default=None)
    k_create.add_argument("--ttl", type=int, default=None, help="TTL in seconds")
    k_create.set_defaults(func=cmd_keys_create)

    k_list = keys_sub.add_parser("list", help="List API keys")
    k_list.set_defaults(func=cmd_keys_list)

    k_revoke = keys_sub.add_parser("revoke", help="Revoke API key")
    k_revoke.add_argument("key_id")
    k_revoke.set_defaults(func=cmd_keys_revoke)

    openapi_cmd = sub.add_parser("print-openapi", help="Print OpenAPI schema")
    openapi_cmd.set_defaults(func=cmd_openapi)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
