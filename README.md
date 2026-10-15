<p align="center">
  <img src="https://orionis-framework.com/favicon.svg" alt="Orionis Framework" width="180" />
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

## Installation

Install the framework with `uvx --from orionis-installer orionis new`.

## Application CLI

From the application root, run commands through the installed `orionis` entry
point:

```shell
uv sync
uv run orionis serve
uv run orionis list
```

## Repositories

- [Framework Core](https://github.com/orionis-framework/framework) — source code for the framework.
- [Application Skeleton](https://github.com/orionis-framework/skeleton) — starting point for Orionis applications.
- [Documentation](https://github.com/orionis-framework/docs) — source for the documentation website.
- [CLI Installer](https://github.com/orionis-framework/installer) — command-line installer.
- [Website](https://github.com/orionis-framework/web) — source for the project website.

## Contributing

Contributions and feedback are welcome. Report bugs or request features in
[GitHub Issues](https://github.com/orionis-framework/framework/issues), or join
the conversation in [GitHub Discussions](https://github.com/orgs/orionis-framework/discussions).

## HTTP benchmarks

The [HTTP comparison suite](benchmarks/http_compare/README.md) measures Orionis
(RSGI and ASGI), FastAPI, Litestar and Starlette with the same Granian server and
load settings. Run it locally or start the **HTTP Framework Comparison** workflow
manually from GitHub Actions to download the reports and raw measurements.
Cross-framework benchmarks run separately from the regular test suite.

The charts update automatically after each successful comparison on `1.x`.
They show median successful HTTP 200 requests per second with **1, 2, 3 and 4
Granian workers**; higher is better. [Full results for 1–4 workers](https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md)
include latency, environment details and the source workflow run.

This Hello World microbenchmark does not represent a full application.
GitHub-hosted runner performance varies between runs.

### 1 worker

[![HTTP throughput with 1 worker](https://raw.githubusercontent.com/orionis-framework/framework/benchmark-results/http-compare/throughput-1-workers.svg)](https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md)

### 2 workers

[![HTTP throughput with 2 workers](https://raw.githubusercontent.com/orionis-framework/framework/benchmark-results/http-compare/throughput-2-workers.svg)](https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md)

### 3 workers

[![HTTP throughput with 3 workers](https://raw.githubusercontent.com/orionis-framework/framework/benchmark-results/http-compare/throughput-3-workers.svg)](https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md)

### 4 workers

[![HTTP throughput with 4 workers](https://raw.githubusercontent.com/orionis-framework/framework/benchmark-results/http-compare/throughput-4-workers.svg)](https://github.com/orionis-framework/framework/blob/benchmark-results/http-compare/summary.md)

## Sponsors

<a href="https://github.com/sponsors/rmunate"><img src="https://img.shields.io/badge/Sponsor_Orionis-GitHub-db2777?style=for-the-badge&amp;logo=github-sponsors&amp;logoColor=white" alt="Sponsor Orionis" /></a>

## Creator

Created and maintained by
[Raul Mauricio Uñate Castro](https://www.linkedin.com/in/raul-mauricio-unate-castro/).

Orionis is open-source software released under the [MIT license](LICENCE).
