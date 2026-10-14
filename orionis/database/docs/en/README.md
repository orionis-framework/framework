# Database

Orionis separates query construction from execution. The `database` module manages named SQL connections, compiles [ORM](../../../orm/docs/en/README.md) plans, executes parameterized SQL, and controls transactions, schemas, migrations, and seeders. Models are optional when querying a table.

Start with SQLite, included in the base installation. Database I/O is asynchronous; declaring columns, selecting a connection, and composing a query are synchronous operations. Python 3.14 or later is required.

1. [Configure connections and execute SQL](connections.md): driver installation, connection selection, bindings, and results.
2. [Transactions and concurrency](transactions.md): atomicity, savepoints, task ownership, and cancellation.
3. [Create schemas](schema.md): blueprints, constraints, and versioned definitions.
4. [Evolve and populate the database](migrations-and-seeders.md): migrations, batches, reversal, and tracked seeder execution.
5. [Backends and production operation](dialects-and-production.md): dialect differences, Redshift, security, and troubleshooting.

A booted application receives services through providers and can use the `DB` and `Schema` facades. Examples constructing `Connection` directly are standalone programs and close the resources they own. Facade fragments require [Foundation](../../../foundation/docs/en/README.md) bootstrap.
