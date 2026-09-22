# Billing Service

Invoicing, subscriptions, and the dunning schedule. Reads the price book from the catalogue
service and writes every money movement to the ledger.

Money is stored in minor units as integers. No floating point ever touches an amount.

## Rules

- A charge is idempotent on its request key.
- Refunds are new entries, never edits to an existing one.
- Anything that moves money is reviewed by a second person before release.
