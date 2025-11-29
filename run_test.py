import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_phase1_embeddings.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
)

with open("test_output.txt", "w") as f:
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\n\nEXIT CODE: {result.returncode}")

print(f"Exit code: {result.returncode}")
print("Output written to test_output.txt")

