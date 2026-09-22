# Billing Ledger

The append-only double-entry ledger behind the billing service. Every entry is immutable
once written; a correction is a new pair of entries, never an update.

The schema in `schema.sql` is the source of truth. Migrations are forward only.

## Rules

- Debits and credits balance per transaction, checked in the database.
- No row is ever deleted or updated after commit.
- A reconciliation run compares the ledger against the payment provider daily.
