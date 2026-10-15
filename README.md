<p align="center">
  <img src="https://orionis-framework.com/favicon.svg" alt="Orionis Framework" width="180" />
</p>

<h1 align="center">Orionis Framework</h1>

<h3 align="center">Write Python. Build the whole application.</h3>

<p align="center">
  The async-first, full-stack framework for modern Python applications.
</p>

<p align="center">
  <a href="https://pypi.org/project/orionis/"><img src="https://img.shields.io/pypi/v/orionis?color=007f8b&amp;style=flat-square" alt="PyPI version" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.14%2B-3776ab?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.14+" /></a>
  <a href="https://github.com/orionis-framework/framework/actions/workflows/test.yml"><img src="https://github.com/orionis-framework/framework/actions/workflows/test.yml/badge.svg?branch=1.x" alt="Test suite" /></a>
  <a href="LICENCE"><img src="https://img.shields.io/badge/license-MIT-16803d?style=flat-square" alt="MIT license" /></a>
</p>

<p align="center">
  <a href="#installation">Get Started</a> &bull;
  <a href="https://docs.orionis-framework.com/">Documentation</a> &bull;
  <a href="#http-benchmarks">Benchmarks</a> &bull;
  <a href="#repositories">Repositories</a> &bull;
  <a href="https://orionis-framework.com/">Website</a>
</p>

---

## About Orionis

Orionis brings a complete application framework to asynchronous Python.
Build web applications, APIs and real-time services with expressive APIs,
clear conventions and a foundation that connects the pieces for you.

An application is more than its HTTP endpoints. Orionis brings routing,
data, security, background work and developer tools into one cohesive
experience, so you can spend more time building your application.

- **Expressive routing** with controllers, middleware and ASGI / RSGI support.
- **A powerful service container** with dependency injection, scoped services,
  service providers and facades.
- **An async ORM** with fluent queries, model relationships, migrations,
  factories and seeders.
- **Authentication and authorization** with sessions, API tokens, roles,
  permissions and policies.
- **Typed validation and server-rendered views** with reusable schema rules,
  Jinja2 templates and localization.
- **Queues and task scheduling** for background jobs and recurring commands.
- **Everyday application services** for caching, mail, logging and local or
  cloud file storage.
- **Real-time and MCP support** with WebSockets, server-sent events and
  Model Context Protocol servers.
- **Integrated developer tooling** with code generators, an application CLI
  and an async-aware test runner.

From a small API to a full web application, start with the same tools and
extend them through your own services and providers.

## Installation

You will need **Python 3.14+** and [uv](https://docs.astral.sh/uv/).
Create a new application with the Orionis installer:

```shell
uvx --from orionis-installer orionis new
```

Then, from your application's directory, install its dependencies and start
the development server:

```shell
uv sync
uv run orionis serve
```

Explore the available commands with `uv run orionis list`.
This repository contains the framework core; the installer creates your
application from the [application skeleton](https://github.com/orionis-framework/skeleton).

## Learning Orionis

The [official documentation](https://docs.orionis-framework.com/) is the place
to start, with guides and reference material for building with Orionis.

Visit the [project website](https://orionis-framework.com/) for an overview,
explore the [package on PyPI](https://pypi.org/project/orionis/), or ask questions
in [GitHub Discussions](https://github.com/orgs/orionis-framework/discussions).

## HTTP Benchmarks

The [HTTP comparison suite](benchmarks/http_compare/README.md) compares Orionis
(RSGI and ASGI), FastAPI, Litestar and Starlette on the same Granian server
with matching load settings.

The charts show median successful HTTP 200 requests per second with
**1, 2, 3 and 4 Granian workers**. Higher is better.

<table>
  <tr>
    <td width="50%" align="center">
      <strong>1 Worker</strong><br />
      <a href="https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md">
        <img src="https://raw.githubusercontent.com/orionis-framework/framework/benchmark-results/http-compare/throughput-1-workers.svg" alt="HTTP throughput with 1 worker" width="100%" />
      </a>
    </td>
    <td width="50%" align="center">
      <strong>2 Workers</strong><br />
      <a href="https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md">
        <img src="https://raw.githubusercontent.com/orionis-framework/framework/benchmark-results/http-compare/throughput-2-workers.svg" alt="HTTP throughput with 2 workers" width="100%" />
      </a>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <strong>3 Workers</strong><br />
      <a href="https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md">
        <img src="https://raw.githubusercontent.com/orionis-framework/framework/benchmark-results/http-compare/throughput-3-workers.svg" alt="HTTP throughput with 3 workers" width="100%" />
      </a>
    </td>
    <td width="50%" align="center">
      <strong>4 Workers</strong><br />
      <a href="https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md">
        <img src="https://raw.githubusercontent.com/orionis-framework/framework/benchmark-results/http-compare/throughput-4-workers.svg" alt="HTTP throughput with 4 workers" width="100%" />
      </a>
    </td>
  </tr>
</table>

Charts update automatically after each successful comparison on `1.x`.
[View the full results](https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md)
for latency, environment details and the source workflow run. Run the suite
locally or launch **HTTP Framework Comparison** from GitHub Actions to
download the reports and raw measurements.

> This Hello World microbenchmark does not represent a full application.
> GitHub-hosted runner performance varies between runs. Cross-framework
> benchmarks run separately from the regular test suite.

## Repositories

- [Framework Core](https://github.com/orionis-framework/framework): the framework source code.
- [Application Skeleton](https://github.com/orionis-framework/skeleton): the starting point for new applications.
- [Documentation](https://github.com/orionis-framework/docs): guides and documentation website.
- [CLI Installer](https://github.com/orionis-framework/installer): create a new Orionis application.
- [Website](https://github.com/orionis-framework/web): the Orionis project website.

## Contributing

Help shape Orionis through code, documentation, bug reports and ideas.
Report bugs or request features in
[GitHub Issues](https://github.com/orionis-framework/framework/issues), and
discuss ideas in [GitHub Discussions](https://github.com/orgs/orionis-framework/discussions).

## Sponsors

Support the ongoing development and maintenance of Orionis through
[GitHub Sponsors](https://github.com/sponsors/rmunate).

<a href="https://github.com/sponsors/rmunate"><img src="https://img.shields.io/badge/Sponsor_Orionis-GitHub-db2777?style=for-the-badge&amp;logo=github-sponsors&amp;logoColor=white" alt="Sponsor Orionis" /></a>

## Creator

Created and maintained by
[Raul Mauricio Uñate Castro](https://www.linkedin.com/in/raul-mauricio-unate-castro/).

## License

Orionis is open-source software licensed under the [MIT license](LICENCE).
