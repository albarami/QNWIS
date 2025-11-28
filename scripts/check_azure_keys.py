#!/usr/bin/env python3
"""Check Azure API keys."""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("Checking Azure environment variables...")
print()

keys = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "API_KEY_5",
    "QNWIS_PRIMARY_ENDPOINT",
    "QNWIS_PRIMARY_API_KEY",
    "QNWIS_FAST_ENDPOINT",
    "QNWIS_FAST_API_KEY",
]

for key in keys:
    value = os.getenv(key)
    if value:
        # Mask the value for security
        masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "****"
        print(f"  {key}: SET ({masked})")
    else:
        print(f"  {key}: NOT SET")

