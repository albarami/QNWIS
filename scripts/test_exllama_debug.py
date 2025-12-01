import sys
import faulthandler
faulthandler.enable()

print("Faulthandler enabled", flush=True)
print("Python:", sys.version, flush=True)
print("Importing exllamav2...", flush=True)
import exllamav2
print("Done!", flush=True)

