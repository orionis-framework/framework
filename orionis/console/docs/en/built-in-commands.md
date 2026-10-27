# Built-in commands

The built-in registry lives in `orionis/console/core/commands.py`; applications can add commands. Inspect `python reactor list` and each signature's help before persistent operations. This guide groups the catalog by task rather than replacing individual argument help.

## Generate components

`make:console-command`, `make:model`, `make:factory`, `make:job`, `make:mail`, HTTP generators, providers, facades, services, contracts, tests, and MCP generators use stubs and application paths. Consult `list` for each signature instead of inferring options from similarly named commands in other frameworks.

```shell
python reactor make:job SendWelcomeEmail --help
python reactor make:factory ProductFactory --help
```

Generating a model does not migrate its table; generating a job does not start workers. Review generated imports, dependencies, and configuration before use.

### Realtime sockets and hubs

```shell
python -B reactor make:realtime-socket chat
python -B reactor make:realtime-hub chat
```

The first command creates `ChatSocket` in `app/realtime/sockets/chat_socket.py`; the second creates `ChatHub` in `app/realtime/hubs/chat_hub.py`. The invokable socket accepts the connection, echoes text messages and handles disconnects. The hub extends `Hub` and includes an `echo(message: str) -> str` method exposed with `@remote`.

The generators respect configured `app_realtime_sockets` and `app_realtime_hubs` paths, create nested directories, append each suffix only once and never overwrite existing files. For example, `make:realtime-hub rooms/chat_hub.py` creates `rooms/chat_hub.py` inside the configured hubs directory.

Generation does not modify routes or open connections. Register the classes with `Route.websocket("/ws/chat", ChatSocket)` or `Route.hub("/realtime/chat", ChatHub)` in your WebSocket routes. See [WebSocket](../../../http/docs/en/websockets.md) and [hubs](../../../realtime/docs/en/hubs-and-methods.md) for integration and authorization.

## Restore configuration

`bootstrap:config [file]` restores missing configuration from the official skeleton's `master` branch.

```shell
orionis bootstrap:config
orionis bootstrap:config app
```

Omit `file` to restore all missing files, or pass a configuration name without `.py` to restore only that file. Available names come from the remote `master` tree; an unknown name produces an error listing those options. Existing files are preserved without being overwritten.

## Evolve data

`migrate`, `migrate:status`, `migrate:rollback`, `migrate:reset`, `migrate:refresh`, `migrate:fresh`, `seed`, and `db:seed` are covered in [migrations and seeders](../../../database/docs/en/migrations-and-seeders.md). They share `--database`/`-d` connection selection. Rollback `--step` counts batches. `db:show` displays database information; `db:table` inspects tables; `db:wipe` removes schema data through its workflow and requires operational care.

```shell
python reactor migrate:status --database sqlite
python reactor db:show --help
python reactor db:table --help
```

Do not schedule `migrate:fresh`, `db:wipe`, or `queue:clear` as routine production housekeeping. They remove data or pending work, rather than cleaning completed-job records.

## Serve, inspect, and test

`serve` starts the development server with its supported options; see [HTTP](../../../http/docs/en/README.md) for the web lifecycle. `route:list` inspects registered routes. `test` runs Orionis testing; selection and modes belong to [Testing](../../../test/docs/en/README.md). Development servers and workers are long-running processes and need supervision in operational environments.

`schedule:list` and `schedule:work` belong to the [scheduler](task-scheduling.md). `queue:migrate` prepares all configured SQL queue tables and failed-job storage without removing data. `queue:work`, `queue:failed`, `queue:retry`, `queue:forget`, and `queue:clear` operate [queues](../../../queues/docs/en/workers-and-failures.md). MCP commands are covered under [MCP](../../../mcp/docs/en/README.md).

## Optimize and maintain

The catalog also covers optimization and clearing it, application/environment status, key generation, maintenance, and cleaning cache, logs, views, and test artifacts. Consult actual signatures/help. Generating a new application key affects existing encrypted data: coordinate changes with [encryption](../../../encrypter/docs/en/README.md). Clearing compiled metadata invalidates cached state and may affect the next startup time.

## Install extras from the catalog

The public signature is `packages`, although its implementation class is named `InstallCommand`:

```shell
orionis packages --list
orionis packages s3 redshift --yes
orionis packages group:dev --yes
```

`--list` only displays the catalog; the other examples install packages using `uv` for the interpreter running Orionis. `--yes` bypasses interactive confirmation. Reading this manual does not require executing installation examples.

The command first uses bundled `orionis/pyproject.toml`, then the framework root manifest for source/editable installations, and finally the application root manifest as fallback. Purpose text comes from `[tool.orionis.packages]`, using keys such as `extra:s3` or `group:dev`. Extras, markers, groups, and deduplication are preserved; the application manifest and lockfile are not rewritten. If expected catalog entries are absent, check the available manifest and active Python environment.
