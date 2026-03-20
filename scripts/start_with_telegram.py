#!/usr/bin/env python3
"""Start Agent Jumbo with tunnel + auto-wired Telegram webhook.

Usage:
    python scripts/start_with_telegram.py [--provider serveo|cloudflared] [--port 5000]

This script:
1. Starts the Flask web UI
2. Starts a public tunnel (serveo by default)
3. Auto-registers the Telegram webhook whenever the tunnel URL changes
4. Keeps the tunnel alive via watchdog (checks every 30s)
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Agent Jumbo with Telegram auto-wiring")
    parser.add_argument("--provider", default="serveo", choices=["serveo", "cloudflared"])
    parser.add_argument("--port", type=int, default=int(os.getenv("WEB_UI_PORT", "5000")))
    parser.add_argument("--host", default=os.getenv("WEB_UI_HOST", "0.0.0.0"))
    args = parser.parse_args()

    # Set env vars before any imports that read them
    os.environ["WEB_UI_PORT"] = str(args.port)
    os.environ["WEB_UI_HOST"] = args.host

    import dotenv

    dotenv.load_dotenv()

    # Validate Telegram config
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("WARNING: TELEGRAM_BOT_TOKEN not set in .env — webhook auto-wiring disabled")
        print("         Set it via: echo 'TELEGRAM_BOT_TOKEN=your-token' >> .env")
    else:
        print(f"Telegram bot token: ...{token[-8:]}")

    # Start tunnel + watchdog before the blocking server
    from python.helpers.tunnel_manager import TunnelManager
    from python.helpers.tunnel_watchdog import TunnelWatchdog

    print(f"Starting {args.provider} tunnel on port {args.port}...")
    manager = TunnelManager.get_instance()
    tunnel_url = manager.start_tunnel(port=args.port, provider=args.provider)

    if tunnel_url:
        print(f"Tunnel ready: {tunnel_url}")
        print(f"Webhook URL:  {tunnel_url}/telegram_webhook")
    else:
        print("Tunnel not ready yet — watchdog will keep trying")

    # Start watchdog with auto-wiring enabled
    watchdog = TunnelWatchdog.get_instance()
    watchdog.start(interval=30, provider=args.provider, auto_wire_telegram=bool(token))
    print("Watchdog started (30s interval, auto-wire Telegram: {})".format("ON" if token else "OFF"))

    # Give the watchdog one cycle to register the webhook
    if tunnel_url and token:
        time.sleep(2)
        print(f"Webhook registered: {watchdog._last_registered_url or 'pending...'}")

    # Start the Flask app (blocking)
    print(f"\nStarting web UI on {args.host}:{args.port}...")
    print("Press Ctrl+C to stop\n")

    from run_ui import run

    try:
        run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        watchdog.stop()
        manager.stop_tunnel()


if __name__ == "__main__":
    main()
