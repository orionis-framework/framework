<p align="center">
  <img src="https://docs.orionis-framework.com/prologue/logo.png" alt="Orionis Framework" width="180" />
</p>

<h1 align="center">Orionis Framework</h1>

<h3 align="center">Write Python. Build the whole application.</h3>

<p align="center">
  Async-first Python framework for web applications and APIs.
</p>

<p align="center">
  <a href="https://pypi.org/project/orionis/"><img src="https://img.shields.io/pypi/v/orionis?color=007f8b&amp;style=flat-square" alt="PyPI version" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.14%2B-3776ab?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.14+" /></a>
  <a href="https://github.com/orionis-framework/framework/actions/workflows/test.yml"><img src="https://github.com/orionis-framework/framework/actions/workflows/test.yml/badge.svg?branch=1.x" alt="Test suite" /></a>
  <a href="LICENCE"><img src="https://img.shields.io/badge/license-MIT-16803d?style=flat-square" alt="MIT license" /></a>
</p>

<p align="center">
  <a href="https://docs.orionis-framework.com/">Documentation</a> &bull;
  <a href="#repositories">Repositories</a> &bull;
  <a href="https://orionis-framework.com/">Website</a>
</p>

---

## About Orionis

Orionis is an open-source, async-first Python framework for building web
applications and APIs. This repository contains the framework core. To start
a new application, visit the [Orionis Skeleton repository](https://github.com/orionis-framework/skeleton).

## Learning Orionis

Visit the [official documentation](https://docs.orionis-framework.com/) for
guides and reference material. You can also explore the [project website](https://orionis-framework.com/)
or find the package on [PyPI](https://pypi.org/project/orionis/).

## Application CLI

From the application root, run commands through the installed `orionis` entry
point:

```shell
uv sync
uv run orionis serve
```

With the project's virtual environment activated, run `orionis serve` directly.
The entry point loads the project's `bootstrap.app` and runs commands in the
same process with bytecode writes disabled; it does not require a `reactor`
script. Command arguments and exit codes are preserved. The legacy command
`python -B reactor serve` remains available.

## Native MCP servers

Expose application services through MCP **2026-07-28** using the existing Orionis
container, schemas, authentication and HTTP pipeline. The same server declaration
supports Streamable HTTP through ASGI/RSGI and local STDIO:

```python
# routes/ai.py
from orionis.mcp import McpResponse, Server, Tool
from orionis.support.facades.mcp import Mcp


class StatusTool(Tool):
    async def handle(self) -> McpResponse:
        return McpResponse.text("ready")


class StatusServer(Server):
    name = "Status"
    tools = (StatusTool,)


Mcp.web("/mcp/status", StatusServer)
Mcp.local("status", StatusServer)
```

Configure `app.withRouting(ai="routes/ai.py")` before `app.create()`. Start the
local server with `python reactor mcp:start status`. Every request declares its
version and capabilities; no initialization session is required.

Read the [MCP guide](orionis/mcp/docs/README.md) or [guía en español](orionis/mcp/docs/README.es.md)
for typed tools, resources, prompts, HTTP headers, security, subscriptions and
verification commands.

## Repositories

- [Framework Core](https://github.com/orionis-framework/framework) — source code for the framework.
- [Application Skeleton](https://github.com/orionis-framework/skeleton) — starting point for Orionis applications.
- [Documentation](https://github.com/orionis-framework/docs) — source for the documentation website.
- [CLI Installer](https://github.com/orionis-framework/installer) — command-line installer.
- [Website](https://github.com/orionis-framework/web) — source for the project website.
- [Inertia Adapter](https://github.com/orionis-framework/inertia-orionis) — Orionis integration for Inertia.js.

## Contributing

Contributions and feedback are welcome. Report bugs or request features in
[GitHub Issues](https://github.com/orionis-framework/framework/issues), or join
the conversation in [GitHub Discussions](https://github.com/orgs/orionis-framework/discussions).

## Sponsors

<a href="https://github.com/sponsors/rmunate"><img src="https://img.shields.io/badge/Sponsor_Orionis-GitHub-db2777?style=for-the-badge&amp;logo=github-sponsors&amp;logoColor=white" alt="Sponsor Orionis" /></a>

## Creator

Created and maintained by
[Raul Mauricio Uñate Castro](https://www.linkedin.com/in/raul-mauricio-unate-castro/).

Orionis is open-source software released under the [MIT license](LICENCE).
