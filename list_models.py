#!/usr/bin/env python3
"""
Lists all Gemini models accessible to your API key, with their supported methods
and which ones are usable for generateContent (what our agent needs).

Usage:
    pip install google-generativeai
    GEMINI_API_KEY=AIzaSy... python3 list_models.py

OR put the key in a .env file (same folder) with: GEMINI_API_KEY=AIzaSy...
"""

import os
import sys
from pathlib import Path

# Optional: load from .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

key = os.environ.get("GEMINI_API_KEY", "").strip()
if not key:
    print("ERROR: set GEMINI_API_KEY env var (or put it in .env)")
    sys.exit(1)

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: pip install google-generativeai")
    sys.exit(1)

genai.configure(api_key=key)

print("Models available to your API key:\n")
print(f"{'Model name':<50} {'Methods':<40}")
print("-" * 95)

generation_models = []
for m in genai.list_models():
    methods = ", ".join(m.supported_generation_methods) if m.supported_generation_methods else "(none)"
    name = m.name.replace("models/", "")
    print(f"{name:<50} {methods:<40}")
    if "generateContent" in m.supported_generation_methods:
        generation_models.append(name)

print("\n" + "=" * 95)
print(f"\nModels usable in our agent (support generateContent):")
print("-" * 50)
for n in generation_models:
    flag = ""
    if "flash" in n and "lite" not in n and "vision" not in n and "tts" not in n and "image" not in n:
        flag = "  ← good for our scoring + composing"
    print(f"  {n}{flag}")

print("\nUse one of the 'flash' models in your GitHub Actions:")
print("  GEMINI_MODEL: '<paste model name here>'")
