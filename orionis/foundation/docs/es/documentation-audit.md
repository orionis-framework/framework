# Auditoría documental de la FASE 1

Revisión del 14 de octubre de 2026 contra Orionis `0.901.0` en la raíz Git `framework/`. Esta fase reconstruye manuales y propone navegación; no publica el portal Astro. La matriz siguiente se deriva del inventario final, no de una cantidad de páginas planificada. Los conteos incluyen el README de cada idioma y este informe.

## Cobertura por módulo

| Módulo | ES | EN | Paridad | Estado | Capacidades cubiertas |
|---|---:|---:|---|---|---|
| [aio](../../../aio/docs/es/README.md) | 2 | 2 | Verificada | Completo | Event loops, ejecución y puente sync/async |
| [auth](../../../auth/docs/es/README.md) | 5 | 5 | Verificada | Completo | Identidad, guards, autorización, remember y recuperación |
| [background](../../../background/docs/es/README.md) | 2 | 2 | Verificada | Completo | Tareas posrespuesta, orden y fallos |
| [cache](../../../cache/docs/es/README.md) | 4 | 4 | Verificada | Completo | Valores, stores, locks y artefactos de código |
| [console](../../../console/docs/es/README.md) | 5 | 5 | Verificada | Completo | Comandos, argumentos, salida y scheduler |
| [container](../../../container/docs/es/README.md) | 4 | 4 | Verificada | Completo | Bindings, invocación, scopes, providers y facades |
| [database](../../../database/docs/es/README.md) | 6 | 6 | Verificada | Completo | Conexiones, SQL, transacciones, schema, migraciones y seeders |
| [encrypter](../../../encrypter/docs/es/README.md) | 2 | 2 | Verificada | Completo | Cifrados AES, claves, formato portable y autenticidad |
| [environment](../../../environment/docs/es/README.md) | 3 | 3 | Verificada | Completo | Tipos, persistencia, recarga y claves |
| [failure](../../../failure/docs/es/README.md) | 3 | 3 | Verificada | Completo | Reporte, despacho, política HTTP/CLI y extensión |
| [foundation](../../../foundation/docs/es/README.md) | 8 | 8 | Verificada | Completo | Instalación, creación, ciclo de vida, config, paths y despliegue |
| [hashing](../../../hashing/docs/es/README.md) | 2 | 2 | Verificada | Completo | Algoritmos, verificación y rehash |
| [http](../../../http/docs/es/README.md) | 10 | 10 | Verificada | Completo | Routing, requests, uploads, responses, middleware, SSE y WebSocket |
| [introspection](../../../introspection/docs/es/README.md) | 3 | 3 | Verificada | Completo | Reflexión, firmas, dependencias y descubrimiento |
| [localization](../../../localization/docs/es/README.md) | 2 | 2 | Verificada | Completo | Catálogos, selección de locale y concurrencia |
| [logging](../../../logging/docs/es/README.md) | 3 | 3 | Verificada | Completo | Canales, rotación, ciclo de vida y fallos |
| [mail](../../../mail/docs/es/README.md) | 4 | 4 | Verificada | Completo | Declaración, composición MIME, adjuntos, transporte y resultados |
| [mcp](../../../mcp/docs/es/README.md) | 6 | 6 | Verificada | Completo | Servidores, tools, schemas, recursos, prompts, transportes y extensiones |
| [metadata](../../../metadata/docs/es/README.md) | 1 | 1 | Verificada | Completo | Identidad, release y compatibilidad Python |
| [orm](../../../orm/docs/es/README.md) | 7 | 7 | Verificada | Completo | Modelos, atributos, consultas, relaciones, eventos, scopes y factories |
| [queues](../../../queues/docs/es/README.md) | 4 | 4 | Verificada | Completo | Dispatch, drivers, workers, reservas, retries y fallos |
| [realtime](../../../realtime/docs/es/README.md) | 4 | 4 | Verificada | Completo | Hubs RPC, métodos remotos y límites por worker |
| [schemas](../../../schemas/docs/es/README.md) | 5 | 5 | Verificada | Completo | Declaraciones, conversión, reglas, errores y validación async |
| [session](../../../session/docs/es/README.md) | 4 | 4 | Verificada | Completo | Stores, cookies, flash, rotación y concurrencia |
| [storage](../../../storage/docs/es/README.md) | 4 | 4 | Verificada | Completo | Discos, archivos, directorios, streaming y drivers cloud |
| [support](../../../support/docs/es/README.md) | 4 | 4 | Verificada | Completo | Colecciones, cadenas, entidades, fechas y utilidades |
| [test](../../../test/docs/es/README.md) | 4 | 4 | Verificada | Completo | Casos async, DI, discovery, resultados y cliente MCP |
| [view](../../../view/docs/es/README.md) | 4 | 4 | Verificada | Completo | Templates Jinja, contextos, autoescape y extensiones |

Los 28 módulos tienen manual oficial reconstruido. La paridad comprende archivos, capítulos, imports, ejemplos principales y advertencias revisadas; los 204 bloques Python por idioma son idénticos; las pruebas automáticas de forma del código complementan la revisión editorial. El directorio `http/default` aporta dos índices auxiliares, uno por idioma, hacia HTTP y no añade un manual independiente.

## Archivos y material anterior

Cada módulo recibe `docs/es/README.md`, `docs/en/README.md` y los capítulos siguientes, con nombres idénticos en ambos idiomas. Se revisaron los manuales anteriores, se trasladó su información técnica válida y se corrigieron discrepancias de APIs. Las referencias de implementación complementan los tutoriales, sin sustituirlos.

- `aio`: `async-execution.md`.
- `auth`: `account-recovery.md`, `authorization.md`, `identity-and-session.md`, `personal-access-tokens.md`.
- `background`: `response-tasks.md`.
- `cache`: `caching-values.md`, `source-artifacts.md`, `stores-and-locks.md`.
- `console`: `built-in-commands.md`, `commands-and-arguments.md`, `output-and-programmatic-execution.md`, `task-scheduling.md`.
- `container`: `bindings-and-invocation.md`, `providers-and-facades.md`, `scopes-and-concurrency.md`.
- `database`: `connections.md`, `dialects-and-production.md`, `migrations-and-seeders.md`, `schema.md`, `transactions.md`.
- `encrypter`: `encrypting-values.md`.
- `environment`: `operations-and-reference.md`, `typed-configuration.md`.
- `failure`: `handling-exceptions.md`, `policies-and-reference.md`.
- `foundation`: `application-lifecycle.md`, `configuration.md`, `deployment-and-reference.md`, `documentation-audit.md`, `getting-started.md`, `installation.md`, `paths-and-caching.md`.
- `hashing`: `password-storage.md`.
- `http`: `default-responses.md`, `forms-and-uploads.md`, `middleware-and-security.md`, `request-lifecycle.md`, `requests-and-validation.md`, `responses.md`, `routing.md`, `streaming-and-sse.md`, `websockets.md`.
- `introspection`: `dependencies-and-discovery.md`, `reflection.md`.
- `localization`: `translating-content.md`.
- `logging`: `rotation-and-lifecycle.md`, `writing-logs.md`.
- `mail`: `composing-mail.md`, `sending-and-results.md`, `transports-and-extensions.md`.
- `mcp`: `advanced-workflows.md`, `resources-and-prompts.md`, `responses-and-content.md`, `servers-and-tools.md`, `transports-and-configuration.md`.
- `metadata`: manual único en `README.md`.
- `orm`: `events-and-scopes.md`, `factories-and-testing.md`, `models-and-attributes.md`, `querying.md`, `relationships.md`, `schema-and-type-reference.md`.
- `queues`: `drivers-and-configuration.md`, `jobs-and-dispatch.md`, `workers-and-failures.md`.
- `realtime`: `groups-and-deployment.md`, `hubs-and-methods.md`, `protocol-and-streaming.md`.
- `schemas`: `application-rules.md`, `constraints-and-reference.md`, `declaring-schemas.md`, `validation-and-errors.md`.
- `session`: `configuration-and-security.md`, `state-and-flash.md`, `stores-and-concurrency.md`.
- `storage`: `disks-and-drivers.md`, `files-and-directories.md`, `streaming-and-uploads.md`.
- `support`: `collections-and-strings.md`, `entities-and-structures.md`, `facades-and-runtime-utilities.md`.
- `test`: `mcp-testing.md`, `results-and-reference.md`, `writing-and-running-tests.md`.
- `view`: `configuration-and-extensions.md`, `rendering-templates.md`, `template-language.md`.

Los README antiguos quedan como rutas de compatibilidad. Hay dos excepciones justificadas: el catálogo de 13 ejemplos de Mail se conserva porque `tests/mail/test_docs.py` lo consume, y el informe histórico español de benchmarks de `http/default` se conserva con aviso de su carácter histórico. Ninguno es capítulo del menú nuevo ni evidencia de pruebas actuales. No se crearon copias adicionales bajo `history/`.

## Verificación efectiva

Se utilizó CPython 3.14.3 del sistema con las dependencias existentes de `.venv/Lib/site-packages` y `-B`. El launcher Python de `.venv` no pudo iniciar su intérprete por permisos del sandbox; no se instalaron dependencias. Las suites usaron un contenedor aislado fijado a la facade de Application, sin importar el bootstrap real.

| Comprobación | Resultado |
|---|---|
| Metadata, schemas, container, environment, failure, introspection y support | 3.025 pruebas aprobadas |
| HTTP, auth, session, realtime y MCP, selección sin servicios reales | 1.732 pruebas aprobadas |
| Database, ORM, console y queues, 18 módulos focalizados | 442 pruebas aprobadas |
| Compatibilidad documental Mail | 2 pruebas aprobadas |
| Total de las selecciones aprobadas | 5.201 pruebas, sin fallos ni errores |
| Programas base reproducibles | 40 programas autónomos, más 3 smokes reales: provider/facade, política HTTP y cliente MCP |
| Infraestructura | 48 snippets ejecutados; smokes adicionales de background, cuatro templates y correo completo a archivo |
| Web y protocolo | 21 ejemplos operacionales y tres roundtrips MCP adicionales de progreso y elicitation |
| Persistencia | Siete escenarios SQLite: CRUD, joins/agregados/paginación, relaciones/eager loading, factories/transacciones, eventos/soft deletes, blueprint y migración/seeder/reversión |
| Python documental | 408 apariciones compiladas, incluyendo fragmentos que requieren contexto async |
| Imports del framework | 736 apariciones resueltas contra implementación instalada/local |
| Firmas de llamadas directas | 608 compatibles por aridad; 44 llamadas adicionales sobre parámetros tipados comprobadas |
| Enlaces locales | 1172 destinos comprobados; sin referencias ausentes |

Compilar un bloque o ejecutar su definición de función/clase no equivale a ejecutar su handler. Los ejemplos de servicios externos, transporte HTTP real, SMTP, Redis, Memcached, cloud y dialectos SQL distintos de SQLite se contrastaron estáticamente. No se efectuó una certificación de esas integraciones. Tres casos Realtime quedaron fuera de la selección aprobada: uno necesitaba providers reales y dos pruebas Granian alcanzaron timeout/WinError32 durante cleanup en el sandbox; sus procesos fueron identificados y cerrados. No se atribuyen esos resultados a una regresión del framework.

## Hallazgos y limitaciones documentadas

- La creación de `Schema` no valida entrada externa; se usa `Validator`. Los campos desconocidos se rechazan solo con la opción correspondiente.
- `Response.json`, `Tool(name=..., handler=...)`, `Cache.put` y `Collection.toList` no pertenecen a estas APIs. Se sustituyeron los ejemplos por `JSONResponse`, subclases `Tool`, `set(..., ttl=...)` y `all()`.
- `Application.compile()` devuelve `None`. `create`, boot eager y readiness HTTP son fases distintas; los scopes limpian referencias pero no cierran recursos arbitrarios.
- Las flags debug/producción de Application se cachean al crearla; cambiar runtime config no reconfigura universalmente managers existentes.
- `SeederRunner.seed()` no acepta selección de clase ni `force`; timestamps y soft deletes requieren columnas explícitas. `Model.create()` devuelve una instancia aunque un evento vete `save()`.
- Bulk update/delete no ejecutan eventos por instancia ni aplican límites de lectura. Pivot no tiene `updateExistingPivot`; `sync()` no abre transacción automáticamente.
- La preparación MIME y lectura de adjuntos es secuencial y completa en memoria; el resultado STORED del transporte file no es entrega SMTP.
- Los handlers `Tool` devuelven `McpResponse`; retornar un valor crudo puede compilar sin funcionar en dispatch. El enlace predeterminado de verificación de email cifra identidad sin un plazo dedicado y el registro predeterminado puede exponer `str(exception)`; ambos requieren política de aplicación.
- Locale es estado compartido; usa selección explícita por solicitud. Realtime y el event bus MCP predeterminados son locales al worker.
- CBC y GCM ofrecen garantías diferentes; locks/leases, expiración file, spooling cloud, scheduler y reintentos tienen límites explicados en sus manuales.
- `Stringable.toHtmlString()` usa `html.escape`; `forPage(page, number)` normaliza page inferior a 1. Los tests no hacen rollback automático de caché o base de datos.

Posible problema de implementación para herramientas: `inspect.signature(AuthorizationSnapshot)` falla por `Iterable` importado únicamente bajo `TYPE_CHECKING` en [snapshot.py](../../../auth/authorization/snapshot.py). Se reprodujo el `NameError`; `annotation_format=annotationlib.Format.STRING` y la construcción directa funcionan. No se cambió la implementación.

## Navegación y preparación de FASE 2

El archivo [documentation-menu.proposal.json](../../../../documentation-menu.proposal.json) está en la raíz Git real. Contiene 11 secciones principales, 115 páginas conceptuales con fuentes ES/EN y dos archivos de índice auxiliar localizados, explícitamente no publicados. El idioma predeterminado es `en`; las rutas públicas propuestas conservan el mismo sufijo tras `/en/` y `/es/`. La validación comprueba IDs, orden, parentId, slugs únicos, fuentes existentes, paridad y cobertura completa, sin páginas publicables huérfanas.

Los manuales usan Markdown portable y permanecen en sus módulos. Astro no se modificó: no se copiaron contenidos, no se instaló nada ni se activaron rutas o i18n. La FASE 2 deberá transformar enlaces relativos entre módulos a rutas públicas y resolver los enlaces a código/tests mediante enlaces de repositorio o una política de recursos; el JSON es una propuesta y no configuración activa de Astro. Los Markdown no requieren MDX ni componentes específicos del portal.

[Volver a fundamentos](README.md).
