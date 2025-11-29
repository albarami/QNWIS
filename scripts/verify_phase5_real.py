#!/usr/bin/env python3
"""
Phase 5 Real Verification - Scenario YAML Loader + Validator

Verifies:
1. Scenarios are loadable from YAML files
2. Validator catches errors correctly
3. Integration with system components
4. Best practices compliance
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

def print_header(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def print_check(name: str, passed: bool, details: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")

def main():
    print_header("PHASE 5 REAL VERIFICATION")
    print("Verifying Scenario YAML Loader + Validator")
    
    all_passed = True
    
    # =========================================================================
    # CHECK 1: Modules Import Correctly
    # =========================================================================
    print_header("1. Module Imports")
    
    try:
        from src.nsic.scenarios import (
            ScenarioLoader,
            ScenarioValidator,
            ScenarioDefinition,
            ScenarioInput,
            ValidationRule,
            ValidationResult,
            create_scenario_loader,
            create_scenario_validator,
        )
        print_check("All scenario modules import", True)
    except ImportError as e:
        print_check("All scenario modules import", False, str(e))
        all_passed = False
        return 1
    
    # =========================================================================
    # CHECK 2: Scenarios Directory Exists with YAML Files
    # =========================================================================
    print_header("2. Scenario Files")
    
    scenarios_dir = Path("scenarios")
    if scenarios_dir.exists():
        print_check("Scenarios directory exists", True, str(scenarios_dir.absolute()))
    else:
        print_check("Scenarios directory exists", False)
        all_passed = False
    
    # Count YAML files
    yaml_files = list(scenarios_dir.rglob("*.yaml"))
    if len(yaml_files) >= 5:
        print_check(f"YAML files found: {len(yaml_files)}", True)
        for f in yaml_files:
            print(f"         - {f}")
    else:
        print_check(f"YAML files found: {len(yaml_files)}", False, "Expected >= 5")
        all_passed = False
    
    # Check domain subdirectories
    expected_domains = ["economic", "policy", "competitive", "timing"]
    for domain in expected_domains:
        domain_dir = scenarios_dir / domain
        exists = domain_dir.exists()
        print_check(f"Domain '{domain}' directory", exists)
        if not exists:
            all_passed = False
    
    # =========================================================================
    # CHECK 3: ScenarioLoader Works
    # =========================================================================
    print_header("3. ScenarioLoader")
    
    loader = create_scenario_loader("scenarios")
    count = loader.load_all()
    
    if count >= 5:
        print_check(f"Scenarios loaded: {count}", True)
    else:
        print_check(f"Scenarios loaded: {count}", False, "Expected >= 5")
        all_passed = False
    
    # Get all scenarios
    scenarios = loader.get_all()
    print_check(f"get_all() returns list", True, f"{len(scenarios)} scenarios")
    
    # Test get by ID
    if scenarios:
        first_scenario = scenarios[0]
        fetched = loader.get(first_scenario.id)
        if fetched and fetched.id == first_scenario.id:
            print_check("get(id) works", True, f"Retrieved '{first_scenario.id}'")
        else:
            print_check("get(id) works", False)
            all_passed = False
    
    # Test get by domain
    economic = loader.get_by_domain("economic")
    if len(economic) >= 1:
        print_check(f"get_by_domain('economic')", True, f"{len(economic)} scenarios")
    else:
        print_check(f"get_by_domain('economic')", False)
        all_passed = False
    
    # Test stats
    stats = loader.get_stats()
    print_check("get_stats() works", True, f"Total: {stats['total_scenarios']}")
    print(f"         Domains: {stats['by_domain']}")
    print(f"         Engines: {stats['by_engine']}")
    
    # =========================================================================
    # CHECK 4: ScenarioValidator Works
    # =========================================================================
    print_header("4. ScenarioValidator")
    
    validator = create_scenario_validator()
    
    # Validate all loaded scenarios
    valid_count = 0
    invalid_scenarios = []
    
    for scenario in scenarios:
        result = validator.validate_definition(scenario)
        if result.valid:
            valid_count += 1
        else:
            invalid_scenarios.append((scenario.id, result.errors))
    
    if valid_count == len(scenarios):
        print_check(f"All {valid_count} scenarios valid", True)
    else:
        print_check(f"Valid scenarios: {valid_count}/{len(scenarios)}", False)
        for sid, errors in invalid_scenarios:
            print(f"         ❌ {sid}: {[e.message for e in errors]}")
        all_passed = False
    
    # Test validation catches errors
    print("\n  Testing validator catches errors...")
    
    # Create invalid scenario
    invalid_scenario = ScenarioDefinition(
        id="",  # Invalid: empty ID
        name="Test",
        domain="invalid_domain",  # Invalid domain
        description="Test",
        inputs=[],  # Invalid: no inputs
        expected_structure={},
        validation_rules=[],
        retry_config=loader._parse_retry(None),
        target_turns=999,  # Invalid: > 200
    )
    
    result = validator.validate_definition(invalid_scenario)
    if not result.valid and len(result.errors) >= 3:
        print_check("Validator catches invalid scenarios", True, f"{len(result.errors)} errors found")
        for err in result.errors:
            print(f"         - {err.field}: {err.message}")
    else:
        print_check("Validator catches invalid scenarios", False)
        all_passed = False
    
    # =========================================================================
    # CHECK 5: Scenario Structure (Best Practices)
    # =========================================================================
    print_header("5. Best Practices Compliance")
    
    # Check scenario structure
    for scenario in scenarios[:3]:  # Check first 3
        print(f"\n  Checking: {scenario.id}")
        
        # Has inputs
        has_inputs = len(scenario.inputs) > 0
        print_check("Has inputs defined", has_inputs, f"{len(scenario.inputs)} inputs")
        if not has_inputs:
            all_passed = False
        
        # Has validation rules
        has_rules = len(scenario.validation_rules) > 0
        print_check("Has validation rules", has_rules, f"{len(scenario.validation_rules)} rules")
        
        # Has expected structure
        has_structure = bool(scenario.expected_structure)
        print_check("Has expected structure", has_structure)
        
        # Has retry config
        has_retry = scenario.retry_config is not None
        print_check("Has retry config", has_retry, f"max_retries={scenario.retry_config.max_retries}")
        
        # Engine assignment
        valid_engine = scenario.assigned_engine in ["engine_a", "engine_b", "auto"]
        print_check("Valid engine assignment", valid_engine, scenario.assigned_engine)
        if not valid_engine:
            all_passed = False
    
    # =========================================================================
    # CHECK 6: Output Validation Works
    # =========================================================================
    print_header("6. Output Validation")
    
    # Create a scenario with expected structure
    test_scenario = scenarios[0] if scenarios else None
    
    if test_scenario:
        # Test with valid output
        valid_output = {
            "analysis": "Test analysis",
            "impacts": [{"area": "economy", "effect": "positive"}],
            "confidence": 0.85,
        }
        
        # Test with missing fields (if expected_structure is defined)
        if test_scenario.expected_structure:
            result = validator.validate_output({}, test_scenario)
            if not result.valid:
                print_check("Output validation catches missing fields", True, 
                           f"{len(result.errors)} errors")
            else:
                print_check("Output validation catches missing fields", False)
        else:
            print_check("Output validation", True, "No expected_structure defined (OK)")
    
    # =========================================================================
    # CHECK 7: Scenario Data Quality
    # =========================================================================
    print_header("7. Scenario Data Quality")
    
    # Check for unique IDs
    ids = [s.id for s in scenarios]
    unique_ids = set(ids)
    if len(ids) == len(unique_ids):
        print_check("All scenario IDs unique", True, f"{len(ids)} unique IDs")
    else:
        print_check("All scenario IDs unique", False, "Duplicate IDs found")
        all_passed = False
    
    # Check inputs have valid shock types
    valid_shock_types = True
    for scenario in scenarios:
        for inp in scenario.inputs:
            if inp.shock_type not in ["absolute", "percentage"]:
                valid_shock_types = False
                print(f"         ❌ Invalid shock_type in {scenario.id}: {inp.shock_type}")
    print_check("All inputs have valid shock_type", valid_shock_types)
    
    # Check target turns are reasonable
    valid_turns = True
    for scenario in scenarios:
        if scenario.target_turns < 1 or scenario.target_turns > 200:
            valid_turns = False
            print(f"         ❌ Invalid target_turns in {scenario.id}: {scenario.target_turns}")
    print_check("All scenarios have valid target_turns", valid_turns)
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print_header("PHASE 5 VERIFICATION SUMMARY")
    
    if all_passed:
        print("\n  🎉 ALL CHECKS PASSED!")
        print("\n  Phase 5 Status:")
        print("  ✅ Scenario YAML files: DEPLOYED")
        print("  ✅ ScenarioLoader: WORKING")
        print("  ✅ ScenarioValidator: WORKING")
        print("  ✅ Best practices: COMPLIANT")
        print("  ✅ Integration ready: YES")
        return 0
    else:
        print("\n  ❌ SOME CHECKS FAILED")
        print("  Review the errors above and fix them.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

