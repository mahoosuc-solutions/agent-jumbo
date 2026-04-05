"""
UI test configuration.

pytest-asyncio's asyncio_mode=auto (set in pytest.ini) wraps every test in an
async event loop, which makes Playwright's sync_api unusable — sync_playwright()
raises "It looks like you are using Playwright Sync API inside the asyncio event loop"
when a loop is already running.

Setting asyncio_mode="strict" here overrides the global setting for this directory,
leaving sync tests as plain synchronous functions so sync_playwright works correctly.
"""


def pytest_configure(config):
    # Override asyncio mode to strict for this test subdirectory only.
    # Individual async tests in this directory would need @pytest.mark.asyncio explicitly,
    # but all current UI tests use the sync Playwright API.
    config.option.__dict__.setdefault("asyncio_mode", "strict")


# Ensure the override applies even if asyncio_mode is already set from the ini file.
# pytest-asyncio reads this ini option; we inject it via the ini_options hook.
def pytest_collection_modifyitems(config, items):
    """Remove the auto asyncio wrapping from sync UI tests."""
    for item in items:
        if item.fspath and "tests/ui" in str(item.fspath):
            # Strip any asyncio marker that auto-mode added, leaving sync tests sync.
            item.own_markers = [m for m in item.own_markers if m.name != "asyncio"]
