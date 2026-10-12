# Operations runbook

This document describes the **existing production deployment** at a high level. It is not an automated deployment recipe. Run commands only on infrastructure you administer.

## Components

| Component | Current approach |
| --- | --- |
| Telegram bot | Python 3.13 / aiogram 3, managed by `expense-bot.service` (systemd) |
| Database | PostgreSQL 17, Docker container `expense-postgres` |
| Schema changes | Alembic migrations |
| Backups | `expense-bot-backup.timer`, PostgreSQL custom-format dump, `pg_restore --list` validation, Google Drive upload |
| Monthly housekeeping | `expense-bot-monthly.timer`, archive and retention logic |
| Demo | Separate `compose.demo.yml`; never use the production Telegram token |

The bot and database use separate processes. The existing production `compose.yml` only manages PostgreSQL.

## Read-only health checks

Run these on the production host only if you have permission:

```bash
sudo systemctl status expense-bot.service --no-pager
sudo systemctl status expense-bot-backup.timer expense-bot-monthly.timer --no-pager
sudo systemctl list-timers --all | grep expense-bot
sudo journalctl -u expense-bot.service -n 100 --no-pager
sudo journalctl -u expense-bot-backup.service -n 100 --no-pager
docker ps --filter name=expense-postgres
docker exec expense-postgres pg_isready
```

Do not paste unredacted logs into public issues: Telegram identifiers, financial information and credentials can appear in runtime diagnostics.

## Deployment notes

- The production bot runs under a dedicated systemd service; its credentials are loaded from private host configuration.
- Do not run `compose.demo.yml` with the production `BOT_TOKEN`: concurrent Telegram long polling will conflict.
- Back up and test a restore **before** applying migrations or modifying retention logic.
- Apply schema migrations only with an approved maintenance plan; the demo's migration-on-start workflow does not apply to production.
- Do not run `monthly_maintenance.py` as a test: it contains retention operations that may delete older expense rows.

## Backup pipeline and current limitation

`app/tasks/database_backup.py` creates a PostgreSQL custom-format dump with `pg_dump -Fc`, checks archive readability using `pg_restore --list`, uploads it to Google Drive, and prunes older remote backups.

**Known risk:** the current task deletes its local dump in a `finally` block, even if the upload fails. A successful `pg_restore --list` also does **not** prove the archive can be fully restored. Until these issues are addressed, verify remote backups independently and perform restore drills in an isolated environment.

## Restore drill — isolated environment only

1. Obtain a backup through an authorized, private channel. Never add it to this repository or CI artifacts.
2. Provision a **separate disposable PostgreSQL 17 instance** and a fresh empty database; do not point restore commands at production.
3. Confirm the archive is readable with `pg_restore --list /secure/path/backup.dump`.
4. Restore into the disposable database, for example:
   ```bash
   pg_restore --no-owner --no-acl -h 127.0.0.1 -p <isolated-port> -U <test-user> -d <empty-test-db> /secure/path/backup.dump
   ```
5. Verify expected tables and row counts without exporting or sharing personal expense data.
6. Record the outcome privately, then securely remove the disposable database and backup copy.

The restore drill has **not** been claimed as completed in this repository.

## Incident response checklist

- **Bot not responding:** check systemd status, recent logs, outbound Telegram API connectivity, and whether another bot instance is polling with the same token.
- **Database unavailable:** check container state, `pg_isready`, disk space and database connectivity from the bot host.
- **Backup upload failed:** verify the Google Drive integration and confirm a valid remote backup exists; do not assume the local dump survived.
- **Monthly job failed:** inspect timer/service logs; do not rerun retention until the failure mode and affected month are understood.

## Monitoring and security

The commands above provide operational checks, **not** evidence that centralized monitoring or alerting is deployed. Do not expose database ports publicly. Keep OAuth credentials, `.env`, database dumps and spreadsheet exports outside Git.
