#!/usr/bin/env python3
"""
Run Phase 0 tests and save results to file.
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Change to project root
    project_root = Path(__file__).parent.parent
    
    # Run pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_phase0_environment.py", "-v", "--tb=short"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    
    # Write results
    output_file = project_root / "phase0_test_results.txt"
    with open(output_file, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("PHASE 0 TEST RESULTS\n")
        f.write("=" * 60 + "\n\n")
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\n\nSTDERR:\n")
        f.write(result.stderr)
        f.write(f"\n\nExit Code: {result.returncode}\n")
    
    print(f"Results written to: {output_file}")
    print(f"Exit code: {result.returncode}")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())

