#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.helpers import schema_governance


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate schema governance artifacts.")
    parser.add_argument(
        "--artifact-root",
        action="append",
        default=[],
        help="Artifact root containing data_dictionary.json, schema_model.json, schema_change_log.json, migration_spec.json",
    )
    args = parser.parse_args()

    roots = [Path(root) for root in args.artifact_root]
    if not roots:
        print("Schema governance check skipped: no artifact roots provided.")
        return 0

    has_errors = False
    for root in roots:
        bundle = schema_governance.load_schema_bundle_from_artifact_root(root)
        errors = schema_governance.validate_schema_bundle(bundle)
        if errors:
            has_errors = True
            for error in errors:
                print(f"{root}: {error}", file=sys.stderr)

    if has_errors:
        return 1

    print("Schema governance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
