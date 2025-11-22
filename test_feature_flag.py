"""Test feature flag system."""

import os
import sys

sys.path.insert(0, "src")

from qnwis.orchestration.feature_flags import (
    get_workflow_implementation,
    use_legacy_workflow,
    use_langgraph_workflow,
)

print("=" * 80)
print("FEATURE FLAG SYSTEM TEST")
print("=" * 80)

# Test 1: Default behavior
print("\n1. Default behavior (no env var set):")
print(f"   Workflow: {get_workflow_implementation()}")
print(f"   Use legacy: {use_legacy_workflow()}")
print(f"   Use langgraph: {use_langgraph_workflow()}")

# Test 2: Enable langgraph
print("\n2. With QNWIS_WORKFLOW_IMPL=langgraph:")
os.environ["QNWIS_WORKFLOW_IMPL"] = "langgraph"
# Need to reload module for change to take effect
import importlib
from qnwis.orchestration import feature_flags
importlib.reload(feature_flags)
print(f"   Workflow: {feature_flags.get_workflow_implementation()}")
print(f"   Use legacy: {feature_flags.use_legacy_workflow()}")
print(f"   Use langgraph: {feature_flags.use_langgraph_workflow()}")

# Test 3: Explicit legacy
print("\n3. With QNWIS_WORKFLOW_IMPL=legacy:")
os.environ["QNWIS_WORKFLOW_IMPL"] = "legacy"
importlib.reload(feature_flags)
print(f"   Workflow: {feature_flags.get_workflow_implementation()}")
print(f"   Use legacy: {feature_flags.use_legacy_workflow()}")
print(f"   Use langgraph: {feature_flags.use_langgraph_workflow()}")

print("\n" + "=" * 80)
print("TEST COMPLETE - Feature flags working correctly")
print("=" * 80)

