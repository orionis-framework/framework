# MCP 2026-07-28 verification

These development tools never become framework runtime dependencies. Install them
in an external temporary directory; the application does not download tooling.
When redirecting Reactor output on Windows, set `$env:PYTHONIOENCODING='utf-8'`;
the full repository test runner already does this for its child processes.

`verification.json` preserves the verified required and unscored check outcomes;
`verification.txt` explains their scope. Regenerate the structured report from
saved oracle output with `write_report.py --conformance TEMP_RESULTS --inspector
TEMP_INSPECTOR_RESULTS --log TEMP_CONFORMANCE_LOG --output verification.json`.
Add `--rsgi TEMP_RSGI_RESULTS --rsgi-log TEMP_RSGI_LOG` to preserve the independent
native RSGI run in the same report. Run that fixture with Granian's `--interface
rsgi` and an independent port and `ORIONIS_MCP_TEST_PORT` value.

```powershell
npm install --prefix TEMP_TOOLS --no-audit --no-fund @modelcontextprotocol/conformance@0.2.0-alpha.12 @modelcontextprotocol/inspector@2.9.0
python tests/mcp/conformance/run_conformance.py --tools TEMP_TOOLS --list
python tests/mcp/conformance/run_conformance.py --tools TEMP_TOOLS --url http://127.0.0.1:8765/mcp --output-dir TEMP_RESULTS
```

Start the isolated native Orionis fixture from the repository root:

```powershell
python -B -m granian --interface asgi --host 127.0.0.1 --port 8765 tests.mcp.conformance.app:app
```

The fixture uses an isolated configuration directory, no compiled application
cache, temporary framework storage, an explicit loopback Origin allowlist and
GCM-encrypted client-carried request state. Set `ORIONIS_MCP_TEST_PORT` when
changing the port. Its fixed encryption key is exclusively a reproducible test
fixture; production applications use their own application key. Its `routes.py`
is loaded by `Application.withRouting(ai=...)`, independently of sample app routes.

The runner checks the installed package version and passes only
`--requirements 2026-07-28`. This selects
the revision's frozen requirement set and wire protocol. A known-failure baseline
is deliberately not supplied: missing fixtures and failed required checks remain
visible. Optional extension scenarios are reported separately by the official
tool; they do not authorize implementing extensions outside this component's scope.

`fixture-requirements.json` records the required scenario inventory, expected
fixture names, and upstream source locations. Each source scenario is authoritative
about exact assertions. A diagnostic fixture being absent is a failure, not proof
that the protocol feature is inapplicable. The framework must not expose these
diagnostic primitives from ordinary application servers.

## Inspector interoperability

Inspector 2.9.0 requires Node.js >=22.19.0. Its default protocol era is legacy;
`--protocol-era modern` pins 2026-07-28 and disables fallback.

```powershell
TEMP_TOOLS/node_modules/.bin/mcp-inspector --cli --server-url http://127.0.0.1:8765/mcp --transport http --protocol-era modern --method tools/list --format json --stored-auth-only
```

For STDIO, create a temporary read-only Inspector config:

```json
{
  "mcpServers": {
    "orionis": {
      "type": "stdio",
      "command": "ABSOLUTE_PYTHON",
      "args": ["-B", "-m", "tests.mcp.conformance.reactor"],
      "protocolEra": "modern"
    }
  }
}
```

Run `mcp-inspector --cli --config TEMP_CONFIG --server orionis --method tools/list
--format json`. Repeat for tools/call, resources/list, resources/read, prompts/list,
and prompts/get using the fixture names. The Inspector CLI is a smoke test; it
does not replace the conformance suite or concurrency/subscription tests.

The repeatable matrix checks eight operations over both transports and records
each CLI stdout/stderr separately, with a summary. It verifies Inspector's pinned
version, explicitly selects the modern era, runs STDIO through the ordinary
`mcp:start` native command, and leaves the installed tooling outside the project:

```powershell
python tests/mcp/conformance/run_inspector.py --tools TEMP_TOOLS --url http://127.0.0.1:8765/mcp --output-dir TEMP_INSPECTOR_RESULTS
```

## Independent JSON Schema oracle

The sibling `fixtures/official_schema.json` is the unmodified official dated schema.
Its provenance and SHA-256 are in `official_schema.source.json`; its upstream
license accompanies it. `schema_oracle.mjs` verifies the checksum and uses the
external conformance tool's AJV 2020-12 implementation to validate a samples file:

```json
[
  {
    "definition": "ListToolsResult",
    "value": {
      "resultType": "complete",
      "tools": [],
      "ttlMs": 0,
      "cacheScope": "private"
    }
  }
]
```

```powershell
node tests/mcp/conformance/schema_oracle.mjs TEMP_TOOLS TEMP_SAMPLES_JSON
```

Exit 0 means every sample validates; exit 1 means at least one schema failure.
Unknown definitions, modified snapshots, and malformed input fail visibly. Schema
validation complements behavioral tests; it cannot establish transport semantics,
authorization, cancellation, bounded memory, or subscription isolation.
