#!/usr/bin/env python3
"""Run Phase 0 gate tests and report results."""

import subprocess
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_phase0_environment.py", "-v", "--tb=short"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    
    output_file = project_root / "phase0_gate_results.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("PHASE 0 GATE TEST RESULTS\n")
        f.write("=" * 70 + "\n\n")
        f.write(result.stdout)
        if result.stderr:
            f.write("\n\nSTDERR:\n")
            f.write(result.stderr)
        f.write(f"\n\nExit Code: {result.returncode}\n")
        
        if result.returncode == 0:
            f.write("\n" + "=" * 70 + "\n")
            f.write("✅ PHASE 0 GATE: PASSED\n")
            f.write("=" * 70 + "\n")
            f.write("\nNext steps:\n")
            f.write("  git add .\n")
            f.write('  git commit -m "feat(phase0): NSIC environment setup complete"\n')
            f.write("  git push origin HEAD\n")
        else:
            f.write("\n" + "=" * 70 + "\n")
            f.write("❌ PHASE 0 GATE: FAILED\n")
            f.write("=" * 70 + "\n")
    
    print(f"Results written to: {output_file}")
    print(f"Exit code: {result.returncode}")
    
    # Also print summary
    lines = result.stdout.split('\n')
    for line in lines[-15:]:
        print(line)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())

