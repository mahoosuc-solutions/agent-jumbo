#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.helpers.stripe_catalog import StripeCatalogOffer, load_commercial_catalog


@dataclass
class OfferSyncResult:
    offer: StripeCatalogOffer
    product_id: str
    monthly_price_id: str | None
    setup_price_id: str | None
    created_product: bool
    created_monthly_price: bool
    created_setup_price: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "offer": self.offer.to_dict(),
            "product_id": self.product_id,
            "monthly_price_id": self.monthly_price_id,
            "setup_price_id": self.setup_price_id,
            "created_product": self.created_product,
            "created_monthly_price": self.created_monthly_price,
            "created_setup_price": self.created_setup_price,
        }


class StripeCliClient:
    def __init__(self, api_key: str, config_home: Path, live_mode: bool = False) -> None:
        self.api_key = api_key
        self.config_home = config_home
        self.live_mode = live_mode

    def _run(self, *args: str) -> dict[str, Any]:
        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = str(self.config_home)
        env["STRIPE_CLI_LOG_PATH"] = str(self.config_home / "stripe.log")
        self.config_home.mkdir(parents=True, exist_ok=True)

        cmd = ["stripe", "--api-key", self.api_key]
        if self.live_mode:
            cmd.append("--live")
        cmd.extend(args)
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "Stripe CLI command failed")
        return json.loads(proc.stdout)

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        try:
            return self._run("products", "retrieve", product_id)
        except RuntimeError as exc:
            if "No such product" in str(exc) or "resource_missing" in str(exc):
                return None
            raise

    def create_product(self, offer: StripeCatalogOffer) -> dict[str, Any]:
        args = [
            "products",
            "create",
            "--confirm",
            "--id",
            offer.product_id,
            "--name",
            offer.name,
            "--description",
            offer.description or offer.tagline or offer.name,
            "--type",
            "service",
        ]
        for key, value in offer.metadata.items():
            args.extend(["-d", f"metadata[{key}]={value}"])
        return self._run(*args)

    def update_product(self, offer: StripeCatalogOffer) -> dict[str, Any]:
        args = [
            "products",
            "update",
            offer.product_id,
            "--confirm",
            "--name",
            offer.name,
            "--description",
            offer.description or offer.tagline or offer.name,
            "-d",
            f"active={'true' if offer.active else 'false'}",
        ]
        return self._run(*args)

    def list_prices_by_lookup_key(self, lookup_key: str) -> list[dict[str, Any]]:
        result = self._run("prices", "list", "--lookup-keys", lookup_key, "--limit", "10")
        return result.get("data", [])

    def create_price(
        self,
        *,
        product_id: str,
        unit_amount: int,
        lookup_key: str,
        recurring_interval: str | None = None,
        nickname: str | None = None,
    ) -> dict[str, Any]:
        args = [
            "prices",
            "create",
            "--confirm",
            "--product",
            product_id,
            "--currency",
            "usd",
            "--unit-amount",
            str(unit_amount),
            "--lookup-key",
            lookup_key,
            "--transfer-lookup-key",
        ]
        if nickname:
            args.extend(["--nickname", nickname])
        if recurring_interval:
            args.extend(["--recurring.interval", recurring_interval])
        return self._run(*args)

    def deactivate_price(self, price_id: str) -> dict[str, Any]:
        return self._run("prices", "update", price_id, "--confirm", "--active=false")


def _active_matching_price(
    prices: list[dict[str, Any]], *, unit_amount: int, recurring_interval: str | None
) -> dict[str, Any] | None:
    for price in prices:
        recurring = price.get("recurring") or {}
        interval = recurring.get("interval")
        if price.get("active") and price.get("unit_amount") == unit_amount and interval == recurring_interval:
            return price
    return None


def sync_offer(client: StripeCliClient, offer: StripeCatalogOffer) -> OfferSyncResult:
    product = client.get_product(offer.product_id)
    created_product = False
    if product is None:
        product = client.create_product(offer)
        created_product = True
    else:
        client.update_product(offer)

    monthly_price_id, created_monthly = _sync_price(
        client,
        offer,
        lookup_key=offer.monthly_lookup_key,
        unit_amount=int(offer.monthly_price_usd * 100),
        recurring_interval="month",
        nickname="Monthly subscription",
    )
    setup_price_id, created_setup = _sync_price(
        client,
        offer,
        lookup_key=offer.setup_lookup_key,
        unit_amount=int(offer.setup_price_usd * 100),
        recurring_interval=None,
        nickname="One-time setup",
    )

    return OfferSyncResult(
        offer=offer,
        product_id=offer.product_id,
        monthly_price_id=monthly_price_id,
        setup_price_id=setup_price_id,
        created_product=created_product,
        created_monthly_price=created_monthly,
        created_setup_price=created_setup,
    )


def _sync_price(
    client: StripeCliClient,
    offer: StripeCatalogOffer,
    *,
    lookup_key: str | None,
    unit_amount: int,
    recurring_interval: str | None,
    nickname: str,
) -> tuple[str | None, bool]:
    if not lookup_key or unit_amount <= 0:
        return None, False

    prices = client.list_prices_by_lookup_key(lookup_key)
    matching = _active_matching_price(prices, unit_amount=unit_amount, recurring_interval=recurring_interval)
    if matching is not None:
        return str(matching["id"]), False

    created = client.create_price(
        product_id=offer.product_id,
        unit_amount=unit_amount,
        lookup_key=lookup_key,
        recurring_interval=recurring_interval,
        nickname=nickname,
    )
    for existing in prices:
        existing_id = str(existing.get("id", ""))
        if existing_id and existing_id != created["id"] and existing.get("active"):
            client.deactivate_price(existing_id)
    return str(created["id"]), True


def build_dry_run_summary(offers: list[StripeCatalogOffer]) -> dict[str, Any]:
    return {
        "offer_count": len(offers),
        "offers": [offer.to_dict() for offer in offers],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Mahoosuc commercial catalog to Stripe via Stripe CLI.")
    parser.add_argument("--catalog", choices=["both", "tiers", "solutions"], default="both")
    parser.add_argument("--api-key", default=os.environ.get("STRIPE_API_KEY", ""))
    parser.add_argument("--config-home", default="/tmp/stripe-config")
    parser.add_argument("--live", action="store_true", help="Use Stripe live mode instead of test mode.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Only print the normalized catalog and planned identifiers."
    )
    parser.add_argument("--output", default="", help="Optional JSON output path for the sync report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    include_tiers = args.catalog in {"both", "tiers"}
    include_solutions = args.catalog in {"both", "solutions"}
    offers = load_commercial_catalog(
        include_platform_tiers=include_tiers,
        include_solution_packages=include_solutions,
    )

    if args.dry_run:
        report = build_dry_run_summary(offers)
        print(json.dumps(report, indent=2))
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 0

    if not args.api_key:
        raise SystemExit("Missing Stripe API key. Set STRIPE_API_KEY or pass --api-key.")

    client = StripeCliClient(
        api_key=args.api_key,
        config_home=Path(args.config_home),
        live_mode=args.live,
    )
    results = [sync_offer(client, offer).to_dict() for offer in offers]
    report = {
        "mode": "live" if args.live else "test",
        "offer_count": len(results),
        "results": results,
    }
    print(json.dumps(report, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
