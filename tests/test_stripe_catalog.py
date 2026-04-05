from python.helpers.stripe_catalog import (
    load_commercial_catalog,
    load_platform_tier_offers,
    load_solution_package_offers,
)


def test_platform_tier_catalog_assigns_expected_billing_modes():
    tiers = {offer.slug: offer for offer in load_platform_tier_offers()}

    assert tiers["community_free"].billing_mode == "free"
    assert tiers["pro"].billing_mode == "subscription"
    assert tiers["enterprise"].billing_mode == "subscription"
    assert tiers["enterprise_custom"].billing_mode == "custom_quote"
    assert tiers["pro"].monthly_lookup_key == "mahoosuc_platform_tier_pro_monthly"


def test_solution_package_catalog_loads_setup_and_monthly_prices():
    packages = {offer.slug: offer for offer in load_solution_package_offers()}

    support = packages["ai-customer-support"]
    assert support.catalog_family == "solution_package"
    assert support.billing_mode == "setup_and_subscription"
    assert support.setup_price_usd == 3500
    assert support.monthly_price_usd == 750
    assert support.setup_lookup_key == "mahoosuc_solution_package_ai_customer_support_setup"
    assert support.monthly_lookup_key == "mahoosuc_solution_package_ai_customer_support_monthly"


def test_commercial_catalog_includes_tiers_and_solution_packages():
    offers = load_commercial_catalog()
    slugs = {(offer.catalog_family, offer.slug) for offer in offers}

    assert ("platform_tier", "pro") in slugs
    assert ("solution_package", "ai-customer-support") in slugs
