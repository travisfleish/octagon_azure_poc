#!/usr/bin/env python3
"""
Debug script to check environment variables
"""

import os
from dotenv import load_dotenv

print("🔍 Environment Variables Debug")
print("=" * 50)

# Load .env file
load_dotenv()

# Check key environment variables
env_vars = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY", 
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION"
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask the API key for security
        if "KEY" in var:
            masked = value[:8] + "*" * (len(value) - 12) + value[-4:] if len(value) > 12 else "*" * len(value)
            print(f"✅ {var}: {masked}")
        else:
            print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: Not set")

print("\n🔍 All Azure-related environment variables:")
azure_vars = {k: v for k, v in os.environ.items() if "AZURE" in k.upper()}
for k, v in azure_vars.items():
    if "KEY" in k:
        masked = v[:8] + "*" * (len(v) - 12) + v[-4:] if len(v) > 12 else "*" * len(v)
        print(f"  {k}: {masked}")
    else:
        print(f"  {k}: {v}")
