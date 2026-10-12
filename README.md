# Expense Bot


[![CI](https://github.com/cherninilyaigorevich-ui/expense-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/cherninilyaigorevich-ui/expense-bot/actions/workflows/ci.yml)
[![Gitleaks](https://github.com/cherninilyaigorevich-ui/expense-bot/actions/workflows/security-audit.yml/badge.svg)](https://github.com/cherninilyaigorevich-ui/expense-bot/actions/workflows/security-audit.yml)


A production-operated Telegram expense tracker built with **Python 3.13, aiogram 3, PostgreSQL 17, SQLAlchemy and Alembic**.

## Features

- Track expenses by category, amount and date
- Shared budgets with Telegram members, chat and topic support
- Statistics and spreadsheet export
- Soft deletion of expenses
- Monthly archive and data retention workflows
- PostgreSQL custom-format backups, archive validation and Google Drive upload
- Automated tests with GitHub Actions and PostgreSQL

## Architecture

```text
Telegram users
      |
      v
aiogram bot (long polling)
      |
      v
SQLAlchemy async / asyncpg
      |
      v
PostgreSQL 17
      |
      +-- Alembic schema migrations
      +-- Scheduled pg_dump + pg_restore validation -> Google Drive
      +-- Monthly export / retention -> Google Drive
```

## Local demo with Docker Compose

**Use a separate test Telegram bot token.** Never run the demo and production instance with the same token: long polling instances will conflict.

1. Copy `.env.example` to `.env` and set `BOT_TOKEN` and `POSTGRES_PASSWORD`.
2. Run `docker compose -f compose.demo.yml --env-file .env up -d --build`.
3. Inspect logs with `docker compose -f compose.demo.yml logs -f bot`.
4. Stop with `docker compose -f compose.demo.yml down`.

The demo stack runs PostgreSQL privately on its own Docker network, applies Alembic migrations before starting the bot, and persists the database in a named volume. Do not use `down -v` unless you explicitly intend to delete demo data.

> Passwords used in the example connection URL should be URL-safe. The Compose demo is separate from the existing production deployment.

## Existing production deployment

The current production installation runs the Python bot through a dedicated **systemd** service and PostgreSQL 17 in Docker. Separate systemd timers schedule database backup and monthly maintenance. The demo Compose stack is **not** the production deployment procedure.

The backup task currently relies on production-specific paths and a container name; monthly maintenance uses a configured-in-code budget ID. These tasks are not part of the standalone demo Compose stack.

## CI

GitHub Actions runs Python compilation and `pytest` against PostgreSQL 17 on pushes and pull requests. See `.github/workflows/ci.yml`.

## Security

- Do not commit `.env`, OAuth tokens, private keys, backups or expense exports.
- Treat database dumps and spreadsheets as sensitive personal data.
- Audit **Git history**, not just the current working tree, before making this repository public.
- Never reuse production credentials in a demo environment.

## Planned improvements

- Parameterize backup container/database names and archive budget IDs
- Preserve local backups on cloud-upload failures
- Add container build and migration smoke tests to CI
- Add a restore drill and deployment runbook
