# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Offline exact-match evaluation of explicitly supplied result records."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.results.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"cases"}:
            raise ValueError("Expected an object with cases")
        cases = data["cases"]
        if not isinstance(cases, list) or not cases:
            raise ValueError("At least one evaluation case is required")
        seen, failed = set(), []
        for case in cases:
            if not isinstance(case, dict) or set(case) != {"id", "expected", "actual"}:
                raise ValueError("Each case needs id, expected and actual")
            if not all(isinstance(value, str) for value in case.values()):
                raise ValueError("Case fields must be strings")
            if not case["id"].strip() or case["id"] in seen:
                raise ValueError("Case identifiers must be nonempty and unique")
            seen.add(case["id"])
            if case["actual"] != case["expected"]:
                failed.append(case["id"])
        print(
            json.dumps(
                {
                    "check": "llm-exact-match",
                    "total": len(cases),
                    "failed": failed,
                    "status": "fail" if failed else "pass",
                },
                sort_keys=True,
            )
        )
        return 1 if failed else 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"check": "llm-exact-match", "status": "invalid", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
