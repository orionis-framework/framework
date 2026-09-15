<p align="center">
  <img src="https://docs.orionis-framework.com/prologue/logo.png" alt="Orionis Framework" width="180" />
</p>

<h1 align="center">Orionis Framework</h1>

<h3 align="center">Write Python. Build the whole application.</h3>

<p align="center">
  Async-first. Laravel-inspired. Built for Python 3.14+.
</p>

<p align="center">
  <a href="https://pypi.org/project/orionis/"><img src="https://img.shields.io/pypi/v/orionis?color=007f8b&amp;style=flat-square" alt="PyPI version" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.14%2B-3776ab?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.14+" /></a>
  <a href="https://github.com/orionis-framework/framework/actions/workflows/test.yml"><img src="https://github.com/orionis-framework/framework/actions/workflows/test.yml/badge.svg?branch=1.x" alt="Test suite" /></a>
  <a href="#project-status"><img src="https://img.shields.io/badge/status-alpha-d99a16?style=flat-square" alt="Status: alpha" /></a>
  <a href="LICENCE"><img src="https://img.shields.io/badge/license-MIT-16803d?style=flat-square" alt="MIT license" /></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#a-real-endpoint">Code Tour</a> &bull;
  <a href="#batteries-connected">Features</a> &bull;
  <a href="#documentation">Documentation</a> &bull;
  <a href="#build-it-with-us">Community</a>
</p>

---

**The endpoint is just the beginning.**

Then come the database, authentication, validation, file uploads, scheduled
work, and all the decisions that turn a demo into an application.

**Orionis is an async-first, full-stack Python framework that connects those
pieces.** A service container at the center. A fluent ORM for your data.
Shared conventions across HTTP, console commands, and tests.

For APIs, server-rendered applications, and internal tools that need more
than an HTTP layer, without leaving the Python ecosystem.

> **Early access:** Orionis is in **alpha**. APIs may change before 1.0;
> this is not a production-stability promise. Try it on a real problem,
> tell us where it gets in your way, and help shape the framework.

## Why Orionis

- **Structure that feels familiar.** Laravel-inspired providers, controllers,
  facades, migrations, and fluent APIs, built around Python's `async/await`.
- **Dependencies declared, not hunted down.** Type-hint a service contract;
  the container resolves it in controllers, commands, and test methods.
  Choose singleton, request-scoped, or transient lifetimes.
- **APIs and HTML belong in the same app.** Return JSON, render an async
  Jinja2 view, stream a file, or redirect with validation errors and old input.
- **Your infrastructure has a home.** Configuration, caching, storage,
  logging, and scheduling follow the same application lifecycle.

## Batteries, Connected

These are implemented capabilities, not a roadmap.

| Area | What you get today |
|---|---|
| **HTTP** | Granian with ASGI and RSGI, named routes, typed path parameters, middleware, CORS, rate limiting, streaming, and file responses. |
| **Validation** | `msgspec` schemas, nested payloads, field constraints, custom rules, and multi-error responses. Invalid API input becomes HTTP 422. |
| **Authentication** | Session login and opaque personal access tokens, request-scoped identity, roles, permissions, and resource policies. |
| **ORM & Database** | Async Active Record, a shared fluent query builder, relationships, eager loading, soft deletes, scopes, model events, pagination, transactions, and migrations. |
| **Views & Sessions** | Async Jinja2, CSRF integration, flash messages, old form input, error bags, and file, memory, cache, or database session stores. |
| **Cache** | Memory, file, Redis, Memcached, and database stores, with TTLs, counters, and lock APIs. |
| **Storage** | Local and in-memory drivers, uploads, streams, and optional S3, Azure Blob, and Google Cloud Storage integrations. |
| **Console & Scheduling** | Reactor commands, scaffolding, Rich output, and APScheduler tasks with memory, Redis, or database job stores. |
| **Everyday Essentials** | Argon2id and bcrypt hashing, AES encryption, rotating logs, translations, collections, and date/time utilities. |
| **Testing** | An integrated runner, async test cases, dependency injection, discovery, filtering, and CLI failure exit codes. |

Database backends include SQLite, PostgreSQL, MySQL, Oracle, and SQL Server.
External services require configuration; cloud SDKs and some database drivers
use the optional extras declared in [pyproject.toml](pyproject.toml).

<details>
<summary><strong>A place for every part of your application</strong></summary>

```text
app/
  http/          Controllers, schemas, and middleware
  models/        Application models
  contracts/     Service interfaces
  services/      Business logic
  providers/     Dependency bindings and startup hooks
  console/       Commands and schedules
bootstrap/       Application composition
config/          Typed application configuration
database/        Migrations
resources/       Views and translations
routes/          Web, API, and console entry points
tests/           Application tests
orionis/         Framework source in this development repository
```

</details>

## Quick Start

You need **Python 3.14+** and [uv](https://docs.astral.sh/uv/).
To explore the current implementation, run this repository's development app:

```bash
git clone --branch=1.x https://github.com/orionis-framework/framework.git
cd framework
uv sync --python=3.14
```

Copy [.env.example](.env.example) to `.env`: use `cp .env.example .env` on
macOS/Linux or `Copy-Item .env.example .env` in PowerShell. Keep these local
settings for a first run without external database or cache servers:

```dotenv
DB_CONNECTION=sqlite
DB_DATABASE=database/database.sqlite
CACHE_STORE=memory
SESSION_DRIVER=file
```

On Windows, set `$env:PYTHONIOENCODING = "utf-8"` before running Reactor.

```bash
uv run python reactor migrate
uv run python reactor serve
```

Open the address printed by `serve`. This is a **framework development
checkout**, not a generated application skeleton.

Already have a Python project? `uv add orionis` installs the package;
application bootstrap and configuration are still required.

## A Real Endpoint

Accept a project name, validate it, persist a model, and return **201 Created**.
The supporting model and migration are included below.

**Declare the input** in `app/http/schemas/create_project.py`:

```python
from orionis.schemas import Schema
from orionis.schemas.constraints import MaxLength, MinLength
from orionis.schemas.fields import Field


class CreateProject(Schema):
    name: Field[str, MinLength(3), MaxLength(120)]
```

**Write the action** in `app/http/controllers/project_controller.py`:

```python
from app.http.schemas.create_project import CreateProject
from app.models.project import Project
from orionis.http import HttpResponse, response


class ProjectController:
    __slots__ = ()

    async def store(self, payload: CreateProject) -> HttpResponse:
        project = await Project.create(payload.toDict())
        return response.json(project.toDict(), status_code=201)
```

**Register the route** in [routes/api.py](routes/api.py):

```python
from app.http.controllers.project_controller import ProjectController
from orionis.support.facades.router import Route

Route.post("/projects", [ProjectController, "store"]).name("projects.store")
```

The container supplies a validated `CreateProject` instance before the action
runs. A missing, too-short, or too-long name produces **422 with field errors**.
No manual body parsing or validation call in the controller.

<details>
<summary><strong>Complete the example: model and migration</strong></summary>

Create `app/models/project.py`:

```python
from typing import ClassVar
from orionis.orm import BigInteger, Model, String


class Project(Model):
    __slots__ = ()

    fillable: ClassVar[list[str]] = ["name"]
    timestamps: ClassVar[bool] = False

    id = BigInteger().primary().autoIncrement()
    name = String(120)
```

Add `m202609140001_create_projects_table.py` under `database/migrations/`:

```python
from orionis.database.contracts.migration import Migration
from orionis.support.facades.schema import Schema


class CreateProjectsTable(Migration):
    __slots__ = ()

    async def up(self) -> None:
        async with Schema.create("projects") as table:
            table.id()
            table.string("name", 120)

    async def down(self) -> None:
        await Schema.drop("projects")
```

Run `uv run python reactor migrate` again, then send a JSON request body such
as `{"name": "Orionis Playground"}` to the new route. This is a public demo
endpoint; add authentication and authorization for protected application data.

</details>

### Models or Tables. One Query Language.

Inside an async controller or service, after applying the migration:

```python
from app.models.project import Project
from orionis.support.facades.db import DB

page = await (
    Project.where("name", "like", "Orionis%")
    .orderBy("id", "desc")
    .paginate(per_page=20, page=1)
)

rows = await DB.table("projects").select("id", "name").get()
```

Models add hydration, casts, relationships, and lifecycle behavior. Direct table
queries return records without requiring a model. Both use the same query
language and **SQLAlchemy Core's async engine**, not SQLAlchemy's ORM session.

## Reactor, Every Day

One entry point for the work around your application:

| Command | Purpose |
|---|---|
| `uv run python reactor serve` | Start the development HTTP server. |
| `uv run python reactor make:command DailyReport` | Scaffold an application command. |
| `uv run python reactor make:provider ProjectServiceProvider` | Scaffold a service provider. |
| `uv run python reactor migrate` | Apply pending database migrations. |
| `uv run python reactor migrate:status` | Inspect migration status. |
| `uv run python reactor schedule:list` | Inspect registered scheduled tasks. |
| `uv run python reactor schedule:work` | Run the scheduler. |
| `uv run python reactor test --start-dir=tests/orm --verbosity=1` | Run a focused test suite in this checkout. |
| `uv run python reactor list` | Discover the available commands. |

Custom commands can use the same injected services as your HTTP controllers.
Scheduled tasks run those command signatures through APScheduler.

## Familiar Foundations

Orionis builds on the ecosystem rather than asking you to leave it:

**[Granian](https://github.com/emmett-framework/granian)** for Rust-powered HTTP.
**[msgspec](https://jcristharif.com/msgspec/)** for typed validation and encoding.
**[SQLAlchemy Core](https://www.sqlalchemy.org/)** for async database execution.
**[Jinja2](https://jinja.palletsprojects.com/)** for templates.
**[APScheduler](https://apscheduler.readthedocs.io/)** for scheduling.
**[Rich](https://rich.readthedocs.io/)** for the terminal.

Orionis supplies the application architecture that connects them. Its request
path uses precompiled routing and cached reflection metadata; actual throughput
depends on your routes, middleware, database, and deployment.

## Documentation

The [documentation website](https://docs.orionis-framework.com/) is still
growing alongside the alpha. For implementation-level detail, start with these
versioned guides:

| Guide | Explore |
|---|---|
| [Container & DI](orionis/container/docs/README.md) | Providers, service lifetimes, scopes, and facades. |
| [Validation](orionis/schemas/docs/README.md) | Schemas, field constraints, custom rules, and errors. |
| [ORM & Database (Spanish)](orionis/orm/README.es.md) | Models, relationships, queries, migrations, and transactions. |
| [Views](orionis/view/docs/README.md) | Async templates and their integration with forms and sessions. |
| [Storage](orionis/storage/docs/README.md) | Disks, uploads, streams, and cloud drivers. |
| [Testing](orionis/test/docs/README.md) | Async test cases, injected dependencies, and the runner. |

Most module guides also have a sibling `README.es.md`. Authentication code
lives in [orionis/auth](orionis/auth); the
[project website](https://orionis-framework.com/) introduces the framework.

## Project Status

**Alpha. Open source. Actively evolving.** Pin the version you evaluate and
review changes before upgrading. Compatibility and production readiness should
be assessed against your own application requirements.

Background tasks run **in process**, after a response; they are not a durable
queue. Mail delivery, durable queues, WebSockets, and Inertia/Vite integrations
are **not implemented yet**. Authentication currently covers sessions and
personal access tokens, not JWT, OAuth, MFA, or password-reset flows.

## Build It With Us

The most useful contribution is a real use case. Build a small feature, bring
a reproducible bug, improve an example, or tell us which API feels awkward.
You do not need to know the whole framework to improve one part of it.

- [Report a bug or request a feature](https://github.com/orionis-framework/framework/issues).
- [Ask questions and share what you are building](https://github.com/orgs/orionis-framework/discussions).
- Submit focused pull requests with relevant tests. Check the touched module
  with Ruff and run its tests through Reactor; see the
  [test workflow](.github/workflows/test.yml) for the current CI commands.
- Send security-sensitive reports privately to
  [raulmauriciounate@gmail.com](mailto:raulmauriciounate@gmail.com).

[![Sponsor Orionis](https://img.shields.io/badge/Sponsor_Orionis-GitHub-db2777?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/rmunate)

Created and maintained by
[Raul Mauricio Uñate Castro](https://www.linkedin.com/in/raul-mauricio-unate-castro/).
Released under the [MIT license](LICENCE).

---

<p align="center"><strong>The next part of your application already has a home.</strong></p>
