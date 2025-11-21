#!/usr/bin/env python3
"""
Verification script for LLM Council API implementation.

Checks that all required files exist, imports work, and basic structure is correct.
"""

from __future__ import annotations

import sys
from pathlib import Path


def check_file_exists(filepath: Path) -> bool:
    """Check if file exists and print result."""
    exists = filepath.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {filepath.relative_to(Path.cwd())}")
    return exists


def check_import(module_path: str) -> bool:
    """Check if module can be imported."""
    try:
        parts = module_path.split(".")
        module = __import__(module_path)
        for part in parts[1:]:
            module = getattr(module, part)
        print(f"✅ Import: {module_path}")
        return True
    except Exception as e:
        print(f"❌ Import: {module_path} - {e}")
        return False


def main() -> int:
    """Run verification checks."""
    root = Path.cwd()
    all_ok = True

    print("=" * 80)
    print("LLM Council API - Verification")
    print("=" * 80)

    # Check files exist
    print("\n📁 File Existence Checks:")
    files_to_check = [
        root / "src/qnwis/api/routers/council_llm.py",
        root / "src/qnwis/api/routers/__init__.py",
        root / "src/qnwis/api/routers/council.py",
        root / "examples/api_client_llm.py",
        root / "src/qnwis/cli/query.py",
        root / "tests/integration/api/test_council_llm.py",
    ]

    for filepath in files_to_check:
        if not check_file_exists(filepath):
            all_ok = False

    # Check imports
    print("\n🔧 Import Checks:")
    imports_to_check = [
        "src.qnwis.api.routers.council_llm",
        "src.qnwis.api.routers",
        "src.qnwis.cli.query",
    ]

    sys.path.insert(0, str(root))
    for module_path in imports_to_check:
        if not check_import(module_path):
            all_ok = False

    # Check router registration
    print("\n📋 Router Registration Check:")
    try:
        from src.qnwis.api.routers import ROUTERS, council_llm

        if council_llm.router in ROUTERS:
            print("✅ council_llm.router registered in ROUTERS")
        else:
            print("❌ council_llm.router NOT in ROUTERS")
            all_ok = False
    except Exception as e:
        print(f"❌ Router registration check failed: {e}")
        all_ok = False

    # Check endpoint definitions
    print("\n🌐 Endpoint Checks:")
    try:
        from src.qnwis.api.routers import council_llm

        routes = [r.path for r in council_llm.router.routes]

        required_routes = ["/v1/council/stream", "/v1/council/run-llm"]
        for route in required_routes:
            if route in routes:
                print(f"✅ Endpoint defined: {route}")
            else:
                print(f"❌ Endpoint missing: {route}")
                all_ok = False
    except Exception as e:
        print(f"❌ Endpoint check failed: {e}")
        all_ok = False

    # Check CLI command
    print("\n⌨️  CLI Command Check:")
    try:
        from src.qnwis.cli.query import query_llm

        print("✅ CLI command 'query_llm' defined")
    except Exception as e:
        print(f"❌ CLI command check failed: {e}")
        all_ok = False

    # Check test file structure
    print("\n🧪 Test File Check:")
    try:
        test_file = root / "tests/integration/api/test_council_llm.py"
        if test_file.exists():
            content = test_file.read_text()
            test_functions = [
                "test_run_llm_complete_returns_structure",
                "test_streaming_endpoint_emits_sse_events",
                "test_legacy_endpoint_deprecation_warning",
            ]
            for test_func in test_functions:
                if f"def {test_func}" in content:
                    print(f"✅ Test defined: {test_func}")
                else:
                    print(f"❌ Test missing: {test_func}")
                    all_ok = False
        else:
            print("❌ Test file does not exist")
            all_ok = False
    except Exception as e:
        print(f"❌ Test file check failed: {e}")
        all_ok = False

    # Summary
    print("\n" + "=" * 80)
    if all_ok:
        print("✅ ALL CHECKS PASSED")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Run tests: pytest -v tests/integration/api/test_council_llm.py")
        print("2. Start server: uvicorn src.qnwis.api.server:app --reload --port 8001")
        print("3. Test client: python examples/api_client_llm.py 'Test question'")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
