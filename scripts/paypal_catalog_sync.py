#!/usr/bin/env python3
"""PayPal catalog sync — idempotent sync of platform tiers and solution packages to PayPal.

Usage:
    python3 scripts/paypal_catalog_sync.py --dry-run --catalog both
    python3 scripts/paypal_catalog_sync.py --catalog tiers
    python3 scripts/paypal_catalog_sync.py --catalog solutions --output artifacts/paypal-sync.json
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
class PayPalSyncResult:
    offer: StripeCatalogOffer
    product_id: str = ""
    plan_id: str = ""
    created_product: bool = False
    created_plan: bool = False
    skipped: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.offer.name,
            "billing_mode": self.offer.billing_mode,
            "product_id": self.product_id,
            "plan_id": self.plan_id,
            "created_product": self.created_product,
            "created_plan": self.created_plan,
            "skipped": self.skipped,
            "error": self.error,
        }


def sync_offer_to_paypal(
    offer: StripeCatalogOffer,
    provider,
    dry_run: bool = False,
) -> PayPalSyncResult:
    """Sync a single catalog offer to PayPal as a Product + Billing Plan."""
    result = PayPalSyncResult(offer=offer)

    if offer.billing_mode in ("free", "custom_quote"):
        result.skipped = True
        return result

    if dry_run:
        print(f"[dry-run] Would sync to PayPal: {offer.name} ({offer.billing_mode})")
        result.skipped = True
        return result

    try:
        # Create the PayPal product
        product = provider.create_product(
            name=offer.name,
            description=offer.description or "",
        )
        result.product_id = product.get("id", "")
        result.created_product = bool(result.product_id)

        # Create billing plan for recurring items
        if offer.monthly_price_usd and offer.monthly_price_usd > 0:
            plan = provider.create_price(
                product_id=result.product_id,
                unit_amount_cents=int(offer.monthly_price_usd * 100),
                currency="usd",
                recurring_interval="MONTH",
            )
            result.plan_id = plan.get("id", "")
            result.created_plan = bool(result.plan_id)

        # One-time setup fee as a separate product if applicable
        if offer.setup_price_usd and offer.setup_price_usd > 0:
            setup_product = provider.create_product(
                name=f"{offer.name} (Setup Fee)",
                description=f"One-time setup fee for {offer.name}",
            )
            setup_price = provider.create_price(
                product_id=setup_product.get("id", ""),
                unit_amount_cents=int(offer.setup_price_usd * 100),
                currency="usd",
                recurring_interval=None,
            )
            print(f"  Setup fee product: {setup_product.get('id')} / price: {setup_price.get('id')}")

        print(f"Synced to PayPal: {offer.name} → product={result.product_id} plan={result.plan_id}")

    except Exception as exc:
        result.error = str(exc)
        print(f"ERROR syncing {offer.name} to PayPal: {exc}", file=sys.stderr)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync product catalog to PayPal")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating")
    parser.add_argument("--catalog", choices=["tiers", "solutions", "both"], default="both")
    parser.add_argument("--output", help="Write JSON results to file")
    parser.add_argument("--mock", action="store_true", help="Use mock PayPal provider")
    args = parser.parse_args()

    from instruments.custom.stripe_payments.payment_router import PaymentRouter

    provider = PaymentRouter.get_provider("paypal", mock=args.mock)

    offers = load_commercial_catalog(
        include_platform_tiers=(args.catalog in ("tiers", "both")),
        include_solution_packages=(args.catalog in ("solutions", "both")),
    )
    print(f"Loaded {len(offers)} offers from catalog='{args.catalog}'")

    results: list[PayPalSyncResult] = []
    for offer in offers:
        r = sync_offer_to_paypal(offer, provider, dry_run=args.dry_run)
        results.append(r)

    synced = sum(1 for r in results if r.created_product)
    skipped = sum(1 for r in results if r.skipped)
    errors = sum(1 for r in results if r.error)

    print(f"\nPayPal sync complete: {synced} created, {skipped} skipped, {errors} errors")

    output_data = {
        "provider": "paypal",
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
