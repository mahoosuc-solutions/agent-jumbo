from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

CatalogFamily = Literal["platform_tier", "solution_package"]
BillingMode = Literal["free", "subscription", "one_time", "setup_and_subscription", "custom_quote"]


@dataclass(frozen=True)
class StripeCatalogOffer:
    catalog_family: CatalogFamily
    slug: str
    name: str
    tagline: str
    description: str
    monthly_price_usd: float
    setup_price_usd: float
    billing_mode: BillingMode
    active: bool
    source_path: str
    metadata: dict[str, str]

    @property
    def product_id(self) -> str:
        return f"mahoosuc_{self.catalog_family}_{_slugify(self.slug)}"

    @property
    def monthly_lookup_key(self) -> str | None:
        if self.monthly_price_usd <= 0:
            return None
        return f"{self.product_id}_monthly"

    @property
    def setup_lookup_key(self) -> str | None:
        if self.setup_price_usd <= 0:
            return None
        return f"{self.product_id}_setup"

    @property
    def is_free(self) -> bool:
        return self.billing_mode == "free"

    @property
    def is_custom_quote(self) -> bool:
        return self.billing_mode == "custom_quote"

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "product_id": self.product_id,
            "monthly_lookup_key": self.monthly_lookup_key,
            "setup_lookup_key": self.setup_lookup_key,
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_platform_tier_offers(root: Path | None = None) -> list[StripeCatalogOffer]:
    base = root or repo_root()
    path = base / "docs" / "product-page" / "pricing-model.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    offers: list[StripeCatalogOffer] = []
    for tier in data.get("tiers", []):
        name = str(tier.get("name", "")).strip()
        slug = _slugify(name)
        monthly = float(tier.get("price_monthly", 0) or 0)

        if slug == "community_free":
            billing_mode: BillingMode = "free"
        elif slug == "enterprise_custom":
            billing_mode = "custom_quote"
        else:
            billing_mode = "subscription"

        offers.append(
            StripeCatalogOffer(
                catalog_family="platform_tier",
                slug=slug,
                name=name,
                tagline=str(tier.get("tagline", "")).strip(),
                description=str(tier.get("cost_basis", "")).strip(),
                monthly_price_usd=monthly,
                setup_price_usd=0.0,
                billing_mode=billing_mode,
                active=True,
                source_path=str(path.relative_to(base)),
                metadata={
                    "catalog_family": "platform_tier",
                    "slug": slug,
                    "source_path": str(path.relative_to(base)),
                },
            )
        )
    return offers


def load_solution_package_offers(root: Path | None = None) -> list[StripeCatalogOffer]:
    base = root or repo_root()
    solutions_dir = base / "solutions"
    offers: list[StripeCatalogOffer] = []

    for solution_file in sorted(solutions_dir.glob("*/solution.json")):
        if solution_file.parent.name.startswith("_"):
            continue

        data = json.loads(solution_file.read_text(encoding="utf-8"))
        pricing = data.get("pricing", {})
        monthly = float(pricing.get("monthly", 0) or 0)
        setup = float(pricing.get("one_time_setup", 0) or 0)
        billing_mode: BillingMode = "setup_and_subscription"
        if monthly <= 0 < setup:
            billing_mode = "one_time"
        elif monthly <= 0 and setup <= 0:
            billing_mode = "custom_quote"

        offers.append(
            StripeCatalogOffer(
                catalog_family="solution_package",
                slug=str(data.get("slug", solution_file.parent.name)).strip(),
                name=str(data.get("name", solution_file.parent.name)).strip(),
                tagline=str(data.get("tagline", "")).strip(),
                description=str(data.get("description", "")).strip(),
                monthly_price_usd=monthly,
                setup_price_usd=setup,
                billing_mode=billing_mode,
                active=str(data.get("status", "draft")).strip().lower() != "archived",
                source_path=str(solution_file.relative_to(base)),
                metadata={
                    "catalog_family": "solution_package",
                    "slug": str(data.get("slug", solution_file.parent.name)).strip(),
                    "tier": str(data.get("tier", "")).strip(),
                    "source_path": str(solution_file.relative_to(base)),
                },
            )
        )
    return offers


def load_commercial_catalog(
    root: Path | None = None,
    include_platform_tiers: bool = True,
    include_solution_packages: bool = True,
) -> list[StripeCatalogOffer]:
    offers: list[StripeCatalogOffer] = []
    if include_platform_tiers:
        offers.extend(load_platform_tier_offers(root))
    if include_solution_packages:
        offers.extend(load_solution_package_offers(root))
    return sorted(offers, key=lambda offer: (offer.catalog_family, offer.slug))


def _slugify(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("&", "and")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("__", "_")
    )
