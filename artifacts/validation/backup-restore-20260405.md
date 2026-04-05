# Backup and Restore Rehearsal — 2026-04-05

## Environment

- **Date:** 2026-04-05
- **Branch:** main
- **Tester role:** Operations
- **Target:** Local development environment (WSL2 / WD Black storage)

## Backup Creation

**Command:**

```bash
{"action": "create", "backup_name": "ga-rehearsal-backup-20260405"}
```

**Result:** ✅ Pass

| Metric | Value |
|--------|-------|
| Files captured | 241 |
| ZIP integrity | OK (`zipfile.is_zipfile` check passed) |
| SQLite databases captured | 38 |
| Backup size | Within expected range |
| Path translation | Verified — absolute paths round-trip correctly |

**Key paths verified in backup:**

- `instruments/custom/stripe_payments/data/stripe_payments.db`
- `instruments/custom/customer_lifecycle/data/customer_lifecycle.db`
- `instruments/custom/payment_account_setup/data/setup_sessions.db` (new — 2026-04-05)
- `data/chats/` (now gitignored; present in backup)

## Restore

**Command:**

```bash
{"action": "restore", "backup_file": "ga-rehearsal-backup-20260405.zip", "dry_run": false}
```

**Result:** ✅ Pass

| Check | Result |
|-------|--------|
| ZIP extracted without errors | ✅ |
| All 241 files restored | ✅ |
| All 38 databases accessible post-restore | ✅ |
| Path translation (stored → restored) | ✅ Correct |
| Application boot after restore | ✅ Health endpoint returned 200 |

## Rollback Path

If restore fails during a production incident:

1. Stop the application
2. Restore from the previous known-good backup
3. If both are corrupt, restore from the off-site copy (see GA Launch Runbook)
4. Do not promote to GA if this step fails

## Sign-off

- **Rehearsal status:** Complete — create and restore both pass
- **Ready for GA:** Yes, subject to refresh in the 2026-04-14 to 2026-04-17 collection window
