#!/usr/bin/env python3
"""Square catalog sync — idempotent sync of platform tiers and solution packages to Square.

Usage:
    python3 scripts/square_catalog_sync.py --dry-run --catalog both
    python3 scripts/square_catalog_sync.py --catalog tiers
    python3 scripts/square_catalog_sync.py --catalog solutions --output artifacts/square-sync.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.helpers.stripe_catalog import StripeCatalogOffer, load_commercial_catalog


@dataclass
class SquareSyncResult:
    offer: StripeCatalogOffer
    item_id: str = ""
    variation_id: str = ""
    created_item: bool = False
    skipped: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.offer.name,
            "billing_mode": self.offer.billing_mode,
            "item_id": self.item_id,
            "variation_id": self.variation_id,
            "created_item": self.created_item,
            "skipped": self.skipped,
            "error": self.error,
        }


def sync_offer_to_square(
    offer: StripeCatalogOffer,
    provider,
    dry_run: bool = False,
) -> SquareSyncResult:
    """Sync a single catalog offer to Square as a Catalog Item + Variation."""
    result = SquareSyncResult(offer=offer)

    if offer.billing_mode in ("free", "custom_quote"):
        result.skipped = True
        return result

    if dry_run:
        print(f"[dry-run] Would sync to Square: {offer.name} ({offer.billing_mode})")
        result.skipped = True
        return result

    try:
        # Create the catalog item (product)
        product = provider.create_product(
            name=offer.name,
            description=offer.description or "",
        )
        result.item_id = product.get("id", "")
        result.created_item = bool(result.item_id)

        # Create price variation(s)
        if offer.monthly_price_usd and offer.monthly_price_usd > 0:
            price = provider.create_price(
                product_id=result.item_id,
                unit_amount_cents=int(offer.monthly_price_usd * 100),
                currency="usd",
                recurring_interval="month",
            )
            result.variation_id = price.get("id", "")

        print(f"Synced to Square: {offer.name} → item={result.item_id}")

    except Exception as exc:
        result.error = str(exc)
        print(f"ERROR syncing {offer.name} to Square: {exc}", file=sys.stderr)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync product catalog to Square")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating")
    parser.add_argument("--catalog", choices=["tiers", "solutions", "both"], default="both")
    parser.add_argument("--output", help="Write JSON results to file")
    parser.add_argument("--mock", action="store_true", help="Use mock Square provider")
    args = parser.parse_args()

    from instruments.custom.stripe_payments.payment_router import PaymentRouter

    provider = PaymentRouter.get_provider("square", mock=args.mock)

    offers = load_commercial_catalog(
        include_platform_tiers=(args.catalog in ("tiers", "both")),
        include_solution_packages=(args.catalog in ("solutions", "both")),
    )
    print(f"Loaded {len(offers)} offers from catalog='{args.catalog}'")

    results: list[SquareSyncResult] = []
    for offer in offers:
        r = sync_offer_to_square(offer, provider, dry_run=args.dry_run)
        results.append(r)

    synced = sum(1 for r in results if r.created_item)
    skipped = sum(1 for r in results if r.skipped)
    errors = sum(1 for r in results if r.error)

    print(f"\nSquare sync complete: {synced} created, {skipped} skipped, {errors} errors")

    output_data = {
        "provider": "square",
        "dry_run": args.dry_run,
        "catalog": args.catalog,
        "results": [r.to_dict() for r in results],
        "summary": {"synced": synced, "skipped": skipped, "errors": errors},
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output_data, indent=2))
        print(f"Results written to {args.output}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
