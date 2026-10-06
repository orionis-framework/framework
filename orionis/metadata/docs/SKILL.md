---
name: "orionis-metadata"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.metadata module. Consult the bundled documentation and inspect the local
  implementation to select verified APIs, respect behavioral constraints,
  and validate proposed usage.
---

# Work with orionis.metadata

Read README.md or README.es.md for the verified public-surface table. Inspect ../__init__.py and the linked source file before choosing an import; do not infer behavior from a symbol name.

Use only package-level imports listed in the API reference. Validate syntax, import resolution, dependencies, configuration, and focused behavior independently. For async APIs, inspect concrete awaited calls before making non-blocking or concurrency claims.

Report unavailable dependencies, services, resources, and behavior not verifiable from local source. Dependency, callback, I/O, and configuration failures may propagate unless the concrete implementation handles them.
