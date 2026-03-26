#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.helpers import release_governance


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release governance artifacts.")
    parser.add_argument("--artifact-root", action="append", default=[], help="Artifact root to validate")
    args = parser.parse_args()

    roots = [Path(root) for root in args.artifact_root]
    if not roots:
        print("Release governance check skipped: no artifact roots provided.")
        return 0

    has_errors = False
    for root in roots:
        release_bundle = release_governance.load_release_artifact_payload(root, "release_bundle.json")
        if release_bundle and release_governance.should_validate_release_bundle(release_bundle):
            for error in release_governance.validate_release_bundle(release_bundle):
                has_errors = True
                print(f"{root}: {error}", file=sys.stderr)

        release_readiness = release_governance.load_release_artifact_payload(root, "release_readiness.json")
        if release_readiness and release_readiness.get("ready") is True:
            for error in release_governance.validate_release_readiness(release_readiness):
                has_errors = True
                print(f"{root}: {error}", file=sys.stderr)

        post_deploy_report = release_governance.load_release_artifact_payload(root, "post_deploy_report.json")
        if post_deploy_report and release_governance.should_validate_post_deploy_report(post_deploy_report):
            for error in release_governance.validate_post_deploy_report(post_deploy_report):
                has_errors = True
                print(f"{root}: {error}", file=sys.stderr)

    if has_errors:
        return 1

    print("Release governance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
