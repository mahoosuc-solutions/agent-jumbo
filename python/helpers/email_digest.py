"""
Email Digest — ambient email awareness for the agent.

Periodically reads recent emails from connected Gmail accounts,
extracts signal (sender, subject, key content), and writes a
structured digest to EXECUTIVE memory. This gives the agent
passive awareness of the operator's email flow without requiring
manual forwarding or explicit inbox queries.

The digest is intentionally lightweight: subject lines, senders,
and snippets — not full email bodies. The agent can always use
email_advanced to drill into specific threads when needed.

Used by: mos_scheduler_init.py (scheduled task)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("email.digest")


async def build_email_digest(
    *,
    hours: int = 4,
    max_emails: int = 30,
    account_name: str | None = None,
) -> dict[str, Any]:
    """Pull recent emails and build a structured digest.

    Args:
        hours: Look back this many hours for new emails.
        max_emails: Cap on emails to fetch per account.
        account_name: Specific Gmail account, or None for all configured accounts.

    Returns:
        Dict with status, account digests, and summary stats.
    """
    try:
        from python.helpers import settings

        current_settings = settings.get_settings()
        gmail_accounts = current_settings.get("gmail_accounts", {})

        if not gmail_accounts:
            return {"status": "skipped", "reason": "No Gmail accounts configured"}

        accounts_to_scan = (
            [account_name] if account_name and account_name in gmail_accounts else list(gmail_accounts.keys())
        )

        after_date = (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).strftime("%Y/%m/%d")
        all_digests: list[dict[str, Any]] = []
        total_emails = 0
        total_unread = 0

        for acct in accounts_to_scan:
            try:
                digest = _scan_account(acct, after_date, max_emails)
                all_digests.append(digest)
                total_emails += digest["email_count"]
                total_unread += digest["unread_count"]
            except Exception as e:
                logger.warning("Failed to scan account %s: %s", acct, e)
                all_digests.append(
                    {
                        "account": acct,
                        "error": str(e),
                        "email_count": 0,
                        "unread_count": 0,
                        "emails": [],
                    }
                )

        result = {
            "status": "ok",
            "scanned_at": datetime.now(tz=timezone.utc).isoformat(),
            "lookback_hours": hours,
            "accounts_scanned": len(accounts_to_scan),
            "total_emails": total_emails,
            "total_unread": total_unread,
            "digests": all_digests,
        }

        # Write to EXECUTIVE memory for ambient awareness
        if total_emails > 0:
            await _save_to_executive(result)

        return result

    except ImportError as e:
        return {"status": "skipped", "reason": f"Gmail dependencies not available: {e}"}
    except Exception as e:
        logger.warning("Email digest failed: %s", e, exc_info=True)
        return {"status": "error", "reason": str(e)}


def _scan_account(account_name: str, after_date: str, max_emails: int) -> dict[str, Any]:
    """Scan a single Gmail account for recent emails."""
    from python.helpers.gmail_api_client import GmailAPIClient

    client = GmailAPIClient(account_name=account_name)
    emails = client.read_emails(
        query=f"after:{after_date}",
        max_results=max_emails,
    )

    summaries = []
    unread_count = 0

    for email in emails:
        is_unread = email.get("is_unread", False)
        if is_unread:
            unread_count += 1

        summaries.append(
            {
                "from": email.get("from", ""),
                "subject": email.get("subject", "(no subject)"),
                "date": email.get("date", ""),
                "snippet": email.get("snippet", "")[:200],
                "unread": is_unread,
                "thread_id": email.get("thread_id", ""),
                "labels": email.get("labels", []),
            }
        )

    return {
        "account": account_name,
        "email_count": len(summaries),
        "unread_count": unread_count,
        "emails": summaries,
    }


async def _save_to_executive(digest: dict[str, Any]) -> None:
    """Write the digest to EXECUTIVE memory for ambient agent awareness."""
    try:
        from python.helpers.memory import Memory

        db = await Memory.get_by_subdir("default")

        # Build a human-readable summary for the memory entry
        lines = [
            f"## Email Digest — {digest['scanned_at'][:16]}",
            f"Accounts: {digest['accounts_scanned']} | "
            f"Emails: {digest['total_emails']} | "
            f"Unread: {digest['total_unread']}",
            "",
        ]

        for acct_digest in digest.get("digests", []):
            acct = acct_digest.get("account", "unknown")
            if acct_digest.get("error"):
                lines.append(f"### {acct} — ERROR: {acct_digest['error']}")
                continue

            lines.append(f"### {acct} ({acct_digest['email_count']} emails, {acct_digest['unread_count']} unread)")

            for email in acct_digest.get("emails", [])[:15]:
                flag = "📩" if email.get("unread") else "  "
                sender = email.get("from", "?")
                # Truncate sender for readability
                if len(sender) > 40:
                    sender = sender[:37] + "..."
                subject = email.get("subject", "(no subject)")
                lines.append(f"{flag} **{sender}** — {subject}")

            if acct_digest["email_count"] > 15:
                lines.append(f"  ... and {acct_digest['email_count'] - 15} more")
            lines.append("")

        summary_text = "\n".join(lines)

        await db.insert_text(
            summary_text,
            {
                "area": "executive",
                "source": "email_digest",
                "total_emails": digest["total_emails"],
                "total_unread": digest["total_unread"],
            },
        )
        logger.info(
            "Email digest written to EXECUTIVE memory: %d emails, %d unread",
            digest["total_emails"],
            digest["total_unread"],
        )
    except Exception:
        logger.warning("Failed to save email digest to EXECUTIVE memory", exc_info=True)
