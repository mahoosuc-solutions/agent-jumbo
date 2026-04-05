"""Browser-assisted payment account setup instrument.

Guides the operator through account creation on Stripe, Square, and PayPal
using Playwright / Chrome DevTools MCP tools, with explicit human-in-the-loop
handoffs for steps that require human interaction (CAPTCHA, 2FA, email
verification, document upload).
"""
