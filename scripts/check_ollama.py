#!/usr/bin/env python3
"""Throwaway sanity check: confirms the local Ollama install has the models
MAYA expects (plan.md §1.1/§1.3, §10 Verification Plan). Run manually:

    python scripts/check_ollama.py
"""
import sys

import httpx

REQUIRED_MODELS = {"qwen2.5vl:7b", "qwen2.5vl:3b", "qwen2.5:7b-instruct"}
OLLAMA_HOST = "http://localhost:11434"


def main() -> int:
    try:
        response = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"FAIL: could not reach Ollama at {OLLAMA_HOST}: {exc}", file=sys.stderr)
        return 1

    installed = {m["name"] for m in response.json().get("models", [])}
    missing = REQUIRED_MODELS - installed

    if missing:
        print(f"FAIL: missing required Ollama models: {sorted(missing)}", file=sys.stderr)
        print(f"  installed: {sorted(installed)}", file=sys.stderr)
        print("  fix: ollama pull " + " && ollama pull ".join(sorted(missing)), file=sys.stderr)
        return 1

    print(f"OK: all required models present: {sorted(REQUIRED_MODELS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
