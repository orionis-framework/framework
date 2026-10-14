# Installation and your first project

Orionis requires Python 3.14 or newer. This checkout declares version `0.901.0` and Alpha status in `pyproject.toml`. Use these manuals with the same framework revision: the described APIs and dependencies belong to this source tree.

## Prepare the environment

For the current checkout in Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -c "from orionis.metadata import VERSION; print(VERSION)"
```

On macOS or Linux:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -c 'from orionis.metadata import VERSION; print(VERSION)'
```

Run these commands from the checkout root. Editable installation is for developing against this source; it does not generate an application layout. This repository already includes `app/`, `bootstrap/`, `config/`, `routes/`, `resources/`, `database/`, `storage/`, and the `reactor` script. A project installing only the distribution must supply its own bootstrap and application files; the console entry point does not generate that skeleton.

The repository also maintains `uv.lock`; if you already use uv, `uv sync` prepares the declared dependencies. Keep the interpreter consistent: check `python --version` in the environment that will run the project. The installed `orionis` command imports `bootstrap.app` from the working directory.

## Dependencies for each task

SQLite, the template engine, hashing, and core components are base dependencies. Cloud providers and additional SQL engines use distribution extras. For example, `python -m pip install -e ".[pgsql]"` installs this revision's PostgreSQL driver. Available extras are `mysql`, `pgsql`, `oracle`, `sqlserver`, `redshift`, `database`, `s3`, `azure`, `gcs`, and `storage`. The `dev` and `docs` collections are development groups, not extras.

See [Database](../../../database/docs/en/README.md) and [Storage](../../../storage/docs/en/README.md) to configure services as well as installing drivers. Installing a dependency does not create tables, credentials, or infrastructure.

## Local environment and application key

Prepare a local `.env` following `.env.example`, keeping credentials private. `Env` uses the working-directory `.env`, whose values override matching process variables. Startup configures timezone and locale; the system locale may be unavailable on some machines.

`APP_KEY` protects encrypted data. If a key is missing when core configuration is constructed, the framework can generate and persist it. Configure a stable private key before the first multi-worker deployment. Do not copy fixed keys from these manuals' isolated examples. Changing a key without a strategy for reading earlier data may prevent decryption.

## Understand the first startup

`bootstrap/app.py` constructs `Application`, optionally enables bootstrap caching, registers routing, scheduler, exception handler, providers, and middleware, and calls `create()`. Declared route files must exist and use supported facade imports; a missing route file stops startup. Application configuration is discovered from frozen dataclasses in `config/`.

The `reactor` script imports this instance and uses `Loop.run` to execute `app.handleCommand(sys.argv)`. HTTP exposes the same instance through ASGI or RSGI. Learn the distinction between creation, provider readiness, and HTTP kernel readiness in [the application lifecycle](application-lifecycle.md).

## Diagnose startup problems

| Symptom | Check |
|---|---|
| A dependency raises `ModuleNotFoundError` | Confirm the interpreter and that the checkout or required extra was installed into that environment. |
| `bootstrap.app` cannot be found | Run the console from an application root containing that module. |
| Configuration type or value error | Check the dataclass, enum, and typed environment value; do not assume every value is text. |
| Configuration changes are missing | Check precedence and compiled cache before changing live services. |
| `withRouting` reports a route error | Check the actual file, its facade import, and the `Application` root. |

These installation steps describe reproducible commands; this reconstruction did not reinstall dependencies or contact external services. Local examples are checked against dependencies already present.



Sources: [pyproject.toml](../../../../pyproject.toml) · [app.py](../../../../bootstrap/app.py) · [cli.py](../../../console/cli.py).

[Module index](README.md).
