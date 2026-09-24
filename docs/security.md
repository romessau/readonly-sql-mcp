# Security

## Threat model

The server assumes SQL may be supplied by an untrusted model or document. Its primary goals are
to prevent database mutation, block known filesystem and cross-database escape functions, limit
result size, bound query duration approximately, and keep secrets and stack traces out of client
errors.

The server does not make sensitive data safe to expose. Anyone who can use its tools can read
data allowed by the configured database file and infer information through permitted queries.

## Controls

1. sqlglot parses input using the SQLite dialect. Exactly one read-only statement is required:
   `SELECT`, compound queries (`UNION`, `INTERSECT`, `EXCEPT`), parenthesized queries, or
   `VALUES`.
2. The syntax tree is checked for write, DDL, transaction, attachment, copy, pragma, and
   `SELECT INTO` nodes. Table and function names starting with `pragma_` are rejected because
   `SELECT * FROM pragma_database_list` would otherwise return the absolute database path.
   `load_extension`, `sqlite3_load_extension`, `readfile`, and `writefile` are denied.
3. SQLite opens the resolved existing file with URI `mode=ro`. That mode is the write barrier.
   `query_only` is enabled at connect time and re-asserted after each statement as a
   best-effort extra check. It does not stop `ATTACH`, and `PRAGMA query_only = OFF` can clear
   it, so the adapter rejects `ATTACH`, `DETACH`, and `PRAGMA` at execute time even if AST
   validation is skipped.
4. Non-SQLite files are refused before a connection is opened. Public failures use fixed
   messages and never include the connection path or a traceback.
5. The adapter materializes no more than the row limit and reports truncation explicitly.
6. A progress handler interrupts SQLite virtual-machine execution after an approximate deadline.
7. SQL input is capped at 50,000 characters before parsing to bound parser work.

## Known limitations

- A function denylist cannot anticipate every dangerous extension. Do not load untrusted SQLite
  extensions, and expose only a database containing data the client may read.
- SQLite progress callbacks execute periodically, not continuously. A native operation that does
  not return control to the virtual machine can overrun the requested timeout.
- A row cap does not limit intermediate work, memory use inside SQLite, or information revealed
  through aggregates.
- Schema metadata itself may be sensitive.
- Filesystem permissions remain important even with URI read-only mode.

## Deployment guidance

Run the process as an unprivileged operating-system user, grant access only to the intended
database file, keep the timeout and row cap low, and avoid placing secrets in environment values
that may be logged by a process supervisor. Review dependency and denylist updates before
upgrading.
