# Auditoría final y cierre técnico — Orionis Framework

**Fecha:** 13 de noviembre de 2026, America/Bogota.  
**Repositorio:** `D:\WORKSPACE\ORIONIS_FRAMEWORK\framework`.  
**Versión:** 1.5.1. **Python ejecutado:** CPython 3.14.6 Windows x64 y Linux amd64; CPython 3.15.2 Linux amd64.  
**Dictamen:** **GO CON OBSERVACIONES** para el alcance local auditado.

## 1. Resumen ejecutivo

Se verificaron completamente **21 de los 22 requisitos operativos de la matriz: 95,5 %**. Uno no es verificable retrospectivamente. El porcentaje mide requisitos de esta auditoría, con igual peso; **no es cobertura de código ni una afirmación de ausencia universal de defectos**. Redis, uvloop, Linux, Python 3.15 y los ejemplos finales ya tienen evidencia; la salvedad restante es histórica, R21.

- **Suite global reutilizada y comprobada independientemente:** 9668 aprobadas, 20 omitidas, cero fallos/errores, exit 0. Se contrastaron el log real, JSON, hashes de fuentes, intérprete, dependencias, cobertura de paquetes y barreras del runner; no se aceptó solamente el resumen del handoff.
- **Ejecución independiente nueva:** 164/164 pruebas de regresión e integración, 15 selectores, cero omisiones y cero accesos protegidos, 122,400 s acumulados.
- **Calidad nueva:** Ruff sin diagnósticos en 1956 Python/stubs; formato aprobado en 2246 entradas —1956 Python/stubs y 290 manuales fuente—. No se procesó documentación generada.
- **SonarLint:** análisis global de 1956 archivos contrastado, más análisis nuevo de `context.py` tras la corrección final: cero diagnósticos; 1955 archivos conservan su hash anterior y el modificado tiene cobertura nueva. Se conserva la observación de shutdown del análisis histórico.
- **Build e instalación nuevos:** wheel y sdist construidos offline, instalación a un destino aislado, imports de los 28 paquetes, exportaciones raíz y ciclo AES-GCM aprobados.
- **Correcciones finales:** marcador `orionis/py.typed` e inclusión en `MANIFEST.in`; posteriormente, una anotación de `McpRequest` para conservar los imports diferidos en Python 3.15. Su tipo público resuelto sigue siendo `Request | None`; se conservaron las pruebas que detectaron el problema.
- **DOCS.ps1:** sintaxis PASS; una ejecución, PASS, exit 0; diez artefactos esperados presentes y no vacíos; 2281 archivos contados únicamente mediante metadatos; cero errores críticos detectados.
- **Ejemplos reejecutados con las dependencias finales:** 62/62 bloques literales, 23/23 pares EN/ES, exit 0; cero violaciones y avisos de recursos; 2358/2358 hashes actuales coincidentes.
- **Docker/Redis:** 94/94 pruebas seleccionadas, incluidas 18 Redis reales y dos uvloop, sin omisiones. Suite global inicial Linux 3.14: 9686 PASS/1 FAIL/1 SKIP; Linux 3.15: 9684 PASS/6 FAIL/1 SKIP. Los fallos se corrigieron y sus selectores se reejecutaron: instalación 39/39 y MCP+Foundation 444/444 en cada versión. La cobertura acumulada por versión es **9687 casos únicos aprobados y uno omitido**. **No se presenta esa combinación como una nueva ejecución global con exit 0.**
- **Windows tras la corrección MCP:** 444/444 aprobadas, cero omisiones/violaciones. Los artefactos de distribución fueron reconstruidos con el código final.

**No se identificó un defecto bloqueante de producción sin corregir.** Permanecen límites propios de los escenarios ejecutados y la imposibilidad de certificar retrospectivamente la conservación total de un árbol protegido. No hay pruebas pendientes presentadas como aprobadas.

## 2. Alcance, método y exclusiones

Se reconstruyó el encargo original incluido íntegramente en `HANDOFF_ORIONIS.md`, las continuaciones 0.1–0.6 y su addendum. Las secciones históricas del handoff que dejaban pendientes Mail/Queues/etc. fueron contrastadas con la continuación posterior y las fuentes actuales; no se tomó aquel estado antiguo como estado vigente.

Se inspeccionaron configuración, historial Git, cambios de fuentes, runner CI, dependencias bloqueadas, fuentes relevantes de documentación y artefactos de validación. No existe `AGENTS.md` en la raíz ni en sus ancestros comprobados. El inventario estático cubrió **1196 fuentes/stubs de Orionis, incluidos dos módulos raíz, y 701 archivos de pruebas permitidos**: 1897 archivos, sin errores de `ast.parse` en Python 3.14.6.

La revisión semántica independiente se concentró en contratos y correcciones de mayor riesgo: cifrado, contextos, cancelación, propiedad de recursos, streams, scheduler, coerción, Mail y cierre de Queues. Se compararon declaraciones públicas de **1168 módulos `.py` existentes en HEAD**: no desaparecieron clases, funciones o métodos públicos declarados, considerando aliases. Esta comparación no demuestra equivalencia de todas las firmas o comportamientos.

**Cobertura honesta:** inventario y sintaxis completos, validación automatizada global contrastada, y revisión semántica selectiva guiada por riesgo. No se afirma una segunda lectura manual exhaustiva de todas las funciones ni una prueba formal de seguridad o ausencia de carreras.

### Exclusiones aplicadas

- `D:\WORKSPACE\ORIONIS_FRAMEWORK\framework\docs\`: excluido de búsquedas de código, inventarios Git, diffs, hashes de fuentes, Ruff y revisión de agentes. No se abrió contenido generado, no se inspeccionaron HTML individuales ni se cargó el inventario generado del handoff en el contexto. Las únicas operaciones sobre ese árbol fueron el flujo autorizado del generador y metadatos agregados de salida.
- `tests/real_database/`: excluido antes de descubrimiento, lectura, copia e importación. No se intentó resolver la incertidumbre histórica entrando a esa carpeta.
- `.env` real, credenciales, servicios y almacenamiento de producción: no usados para validar. Cachés, entornos virtuales y artefactos de compilación quedaron fuera del análisis de fuentes.

Las validaciones Windows se ejecutaron en snapshots propios, con entorno sintético y guard heredado por procesos hijos. Su autocomprobación pasó **18 rechazos esperados**, además de SQLite/loopback propios y propagación a hijos. El harness añadió exclusión Git explícita de `docs/` y rechazo de acceso al directorio generado real. Las validaciones Linux usaron los contenedores y snapshots descritos en 5.5. No se alteró el runner del framework. El guard Python **no es un sandbox del sistema operativo**.

## 3. Matriz de cumplimiento

Estados: **COMPLETADO** = evidencia suficiente para el requisito delimitado; **PARCIAL** = existe evidencia con un límite señalado; **PENDIENTE** = falta ejecución o corrección necesaria; **NO VERIFICABLE** = no puede certificarse con la evidencia disponible y las restricciones vigentes.

| ID | Requisito operativo del plan | Estado | Evidencia y límite |
|---|---|---|---|
| R01 | Reconstruir objetivo, alcance y decisiones posteriores | COMPLETADO | Encargo íntegro, handoff, fuentes y autorizaciones primarias contrastados |
| R02 | Cubrir los 28 paquetes y módulos raíz en inventario/sintaxis | COMPLETADO | 1196 fuentes/stubs; 1897 archivos fuente+tests sin errores AST |
| R03 | Contrastar arquitectura y contratos públicos afectados | COMPLETADO | Revisión por riesgo, consumidores y 1168 módulos comparados; sin desapariciones públicas declaradas |
| R04 | Verificar suite global permitida y regresiones conservadas | COMPLETADO | Log real 9668 aprobadas/20 omitidas; hashes verificados; omisiones separadas en R06 |
| R05 | Ejecutar integración independiente representativa | COMPLETADO | 164/164 nuevas, 15 selectores, exit 0, sin violaciones |
| R06 | Completar integración opcional y otras plataformas | COMPLETADO | 18 Redis y dos uvloop reales PASS; suites Linux 3.14/3.15 y revalidaciones descritas en 5.5; no se extrapola a macOS/free-threaded/proveedores remotos |
| R07 | Comprobar cancelación, concurrencia y liberación de recursos | COMPLETADO | Suite global, pruebas nuevas de lifecycle/streams/contextos/stores/hashing y revisión de ownership |
| R08 | Verificar correcciones de seguridad y errores conocidos | COMPLETADO | GCM/CBC, claves/inputs, aislamiento, rutas y conservación de error primario; sin pretensión de pentest completo |
| R09 | Ejecutar Python 3.14 y versiones posteriores soportadas disponibles | COMPLETADO | 3.14.6 Windows/Linux y 3.15.2 Linux; disponibilidad posterior comprobada mediante imagen oficial, fallo MCP corregido y revalidado |
| R10 | Comprobar anotaciones runtime, imports y distribución de tipos | COMPLETADO | Tests/hints fríos contrastados, imports del wheel y corrección PEP 561; no hay checker estático configurado |
| R11 | Ruff sobre fuentes completas permitidas | COMPLETADO | Nueva ejecución: 1956 archivos, exit 0 |
| R12 | Comprobación de formato | COMPLETADO | Nueva ejecución: 2246 entradas, exit 0 |
| R13 | SonarLint real con perfil autorizado y cobertura completa | COMPLETADO | 1955 hashes conservados más context.py reanalizado: cero diagnósticos; perfil idéntico; observación histórica de shutdown |
| R14 | Build e instalación del paquete real | COMPLETADO | Wheel/sdist offline, marker en ambos, instalación y smoke del wheel exit 0 |
| R15 | Validar configuración CI y operaciones locales equivalentes | COMPLETADO | Workflow leído, runner con poda previa, pruebas/calidad/build locales; no se atribuye una ejecución hosted |
| R16 | Validar sintaxis, rutas y errores de DOCS.ps1 | COMPLETADO | Parser PowerShell y revisión del script/dependencias fuente, sin errores |
| R17 | Ejecutar generador una vez y comprobar artefactos por metadatos | COMPLETADO | Exit 0; 10/10 artefactos; 2281 archivos; sin inspección de contenido generado |
| R18 | Revalidar todos los ejemplos manuales con dependencias finales | COMPLETADO | Nueva tanda íntegra 62/62, 23 pares EN/ES y 2358 hashes actuales coincidentes; cero violaciones/avisos de recursos |
| R19 | Sustentar optimizaciones relevantes y reconocer costes | COMPLETADO | View: cinco pares comparables, equivalencia semántica, memoria e imports; no promesa de aceleración global |
| R20 | Mantener exclusiones y conservación durante esta auditoría | COMPLETADO | Filtros previos, guard Windows, contenedores Linux, manifests; delta acotado a empaquetado, MCP, infraestructura autorizada e informes; no inspección de árboles excluidos |
| R21 | Certificar inmutabilidad histórica total del árbol protegido | NO VERIFICABLE | Incidente previo de formatter sin certeza retrospectiva; autorización posterior no reconstruye prueba faltante |
| R22 | Registrar Git, riesgos, corrección y dictamen reproducibles | COMPLETADO | Este informe y evidencias externas; sin staging, commit, push ni publicación remota |

**Resultado:** 21 COMPLETADOS, 0 PARCIALES, 0 PENDIENTES, 1 NO VERIFICABLE. **21/22 = 95,5 % plenamente verificado.** R21 no puede cerrarse con nuevas pruebas: haría falta evidencia histórica fiable del incidente. La autorización de conservar cambios no reconstruye esa evidencia.

## 4. Estado de todos los paquetes

Todos los paquetes de esta tabla están incluidos en el inventario/parsing independiente y en la suite global cuyo log se verificó. Las cantidades siguientes proceden de **ese log global reutilizado**, no de conteos AST ni de las 164 pruebas nuevas. “Verificado localmente” conserva los límites de alcance de la sección 2.

| Paquete | Fuentes/stubs | Aprobadas | Omitidas | Estado / foco contrastado |
|---|---:|---:|---:|---|
| aio | 2 | 74 | 2 | Base Windows; Linux añade los dos uvloop reales: 76/76 PASS |
| auth | 57 | 383 | 0 | Verificado; contexto/credencial por request, guards y caché débil |
| background | 5 | 83 | 0 | Verificado; trabajo síncrono cancelado y observación de fallos tardíos |
| cache | 22 | 234 | 0 | Verificado; TTL, ausencia/null, timers y propiedad de stores |
| console | 163 | 1511 | 0 | Verificado; CLI, descubrimiento vacío y cierre de scheduler |
| container | 23 | 264 | 0 | Verificado; resolución, scopes, hints y lifetimes |
| database | 48 | 326 | 0 | Verificado en entornos controlados; error primario, conexiones y compilación |
| encrypter | 5 | 59 | 0 | Verificado; GCM y rechazo CBC autorizados; smoke del wheel adicional |
| environment | 17 | 223 | 0 | Verificado; validación/persistencia controlada, sin .env real |
| failure | 15 | 183 | 0 | Verificado; reentrada, shutdown, claims y error original |
| foundation | 168 | 250 | 0 | Verificado; lifecycle, admisión y límites Argon compartidos |
| hashing | 12 | 178 | 0 | Verificado; configuración, hashes inválidos y caché concurrente |
| http | 128 | 978 | 4 | Base Windows; Linux incluye Redis real: 982/982 PASS |
| introspection | 30 | 792 | 0 | Verificado; anotaciones diferidas de Python 3.14 y cachés |
| localization | 14 | 153 | 0 | Verificado; fullmatch de locale, rutas y sustituciones |
| logging | 15 | 193 | 0 | Verificado; lifecycle, sinks y rotación |
| mail | 28 | 198 | 0 | Verificado con límites SMTP doblados/file real; validación anticipada y sin secretos |
| mcp | 43 | 194 | 0 | Verificado; coerción compartida, estado y contratos |
| metadata | 2 | 37 | 0 | Verificado; fuentes de verdad y exports |
| orm | 95 | 505 | 0 | Integrada completa ahora acreditada; consultas, relaciones, estado y factories |
| queues | 30 | 155 | 14 | Base Windows; Linux incluye Redis real: 169/169 PASS |
| realtime | 17 | 96 | 0 | Verificado; schemas compuestos y contexto/lifecycle |
| schemas | 67 | 586 | 0 | Verificado; instancias, coerción, constraints y errores |
| session | 15 | 260 | 0 | Verificado; cookies, flash, TTL y drenaje de stores |
| storage | 30 | 288 | 0 | Verificado con recursos controlados; streams, rutas y cleanup |
| support | 87 | 1006 | 0 | Verificado; colecciones, strings, grafos y helpers compartidos |
| test | 17 | 192 | 0 | Verificado; discovery, errores, filtros y códigos de salida |
| view | 39 | 190 | 0 | Integrada completa acreditada; URL, carga, caches y contrato warmup |

Se agregan dos módulos raíz y **77 pruebas globales fuera de esas carpetas: 14 del generador y 63 de raíz**, para el total de 9668 aprobadas. Ninguna omisión se suma a las aprobaciones.

## 5. Resultados automatizados y evidencia

### 5.1 Ubicaciones de evidencia

Para acortar las referencias de este informe:

```text
E = C:\Users\runate\.copilot\session-state\745eed3b-fbab-4e9d-992e-da09159ffc68\files
A = C:\Users\runate\AppData\Local\Temp\orionis-final-audit-20261113-cyk047fw
D = C:\Users\runate\AppData\Local\Temp\orionis-final-docs-audit-23733274d5d14c7c9fc3dd912c6665b8
L = E\docker-final-20261113-632fc91e
M = E\final-context315-validation-20261113-dc1e47a2
P = C:\Users\runate\AppData\Local\Temp\orionis-packaging-final-20261113-263ed5fd
```

`E` contiene evidencia durable de la continuación; `A` y `D` contienen logs y artefactos de esta auditoría. Sus rutas temporales no se presentan como almacenamiento permanente. Los resultados y límites esenciales quedan incorporados aquí aunque esos auxiliares desaparezcan.

| Control | Origen | Evidencia | Resultado |
|---|---|---|---|
| Global nativa | Reutilizada tras verificación | `E\continuation-3-final-deduplicated-f1305f2a.json` y log real | 9668 PASSED/20 SKIPPED, 0 FAILED/ERRORED; exit 0; 1201,55 s |
| Guard | Nueva | `A\guard-selfcheck.log` | 18 rechazos esperados, exit 0 |
| Integración/regresión | Nueva | `A\final-audit-independent-47307dd9.json` y 15 logs | 164/164; exit 0; 122,400 s; 0 violaciones |
| Ruff | Global + delta final | `A\quality.json`, `lint.log`; `L\ruff-context.log` | 1956 archivos globales y recheck del único Python modificado; exit 0 |
| Formato | Global + delta final | `A\quality.json`, `format.log`; `L\ruff-format-context.log` | 2246 entradas globales y recheck del único Python modificado; exit 0 |
| AST/API | Nueva | Inventario filtrado y comparación estática | 1897 AST válidos; 1168 módulos comparados |
| Sonar | Global contrastada + delta nuevo | `E\sonar-probe-14bb809a.json`; `L\sonar-probe-ffc7dc68.json` y traces | 1955 fuentes estables + context.py final reanalizado, cero diagnósticos; perfil conservado |
| Revisión independiente de evidencia | Nueva | `A\evidence-review.json` | Hashes, logs, reglas, plugins y decisiones primarias contrastados |
| Dependencias | Nueva y contraste de lock | `uv pip check` + metadata/uv.lock | 99 distribuciones compatibles y versiones presentes en el lock |
| Build/install final | Nueva tras MCP | `L\packaging-final\packaging-result.json`, logs y artefactos; originales en `P` | Todos exit 0; wheel/sdist/marker, 28 imports, MCP frío/hints y GCM aprobados |
| Generador | Nueva | `D\result.json`, `D\generator.log` | Sintaxis y ejecución PASS, una ejecución |
| Ejemplos manuales finales | Nueva tras MCP | `M\manual-scope-4f853e9a.json` y `summary.json` | 62/62 bloques, 23/23 pares, 102 invocaciones, exit 0; 0 violaciones/avisos de recursos |
| Windows tras MCP | Nueva | `M\windows-context315-1616c1ae.json` y logs | 194 MCP + 250 Foundation, 444/444 PASS; exit 0; cero omisiones/violaciones |
| Docker/Linux/Redis | Nueva | `L\combined-evidence.json` y resultados originales de cada ejecución | Resultados iniciales y rechecks separados en 5.5; 9687 casos únicos PASS + 1 SKIP por versión tras las correcciones |
| Pydoctor sobre fuentes finales | Nueva, sin HTML | `L\pydoctor-final-source.log` y código de salida | `--testing --warnings-as-errors`, exit 0; análisis de entradas finales sin regenerar el sitio |
| Git de fuentes | Nueva | `A\git-source-state.json` | `git diff --check` exit 0; excluidos ambos árboles prohibidos |

### 5.2 Selección independiente ejecutada

| Selector bajo `tests/` | Aprobadas |
|---|---:|
| `test/core/test_engine.py` | 48 |
| `view/test_global_regressions.py` | 6 |
| `mail/test_integration.py` | 2 |
| `queues/test_integration.py` | 1 |
| `realtime/test_integration.py` | 2 |
| `mcp/test_integration.py` | 11 |
| `http/adapters/test_sse_lifecycle.py` | 12 |
| `console/test_cli.py` | 13 |
| `foundation/test_application_lifecycle.py` | 8 |
| `foundation/test_failure_lifecycle.py` | 28 |
| `auth/test_context_regressions.py` | 4 |
| `session/stores/test_store_regressions.py` | 8 |
| `schemas/test_core_regressions.py` | 7 |
| `storage/test_resource_regressions.py` | 13 |
| `hashing/test_cache_concurrency.py` | 1 |
| **Total** | **164** |

Todos esos selectores devolvieron exit 0, sin skips ni violaciones. Ese checkpoint no repitió la suite Windows de veinte minutos porque su evidencia era verificable. La continuación Docker añadió suites globales en Linux y, tras F07, revalidó los paquetes afectados en Windows y Linux; no se oculta ese delta posterior.

### 5.3 Correspondencia de fuentes y limitación del delta

Antes de la corrección nueva coincidían los **2357/2357 hashes** del snapshot global, y los **1956/1956 hashes** Python/stubs de Sonar. También coincidían el perfil y los dos plugins del analizador. Se verificaron en el trace 1956 aperturas, 1957 publicaciones de diagnósticos y finalización del procesamiento antes del shutdown; no existe filtro posterior de diagnósticos en el cliente.

Tras PEP 561, `MANIFEST.in` difiere del snapshot anterior y `orionis/py.typed` es nuevo: **2358 entradas**. Después, la continuación Docker modificó únicamente `orionis/mcp/context.py` dentro de esas fuentes; no cambió pruebas, dependencias ni perfiles. Su SHA anterior era `84a656d39742112f60335206e82bfdfb5c97d1cd9e373b84ec26976dae0cef8c`; el final es `2764fb6e2ec2c1db1f39f5ecc52be292598c14fe0d3aa46fe705028d5c08e768`. Los manifiestos finales de Linux, Windows, manuales y empaquetado coinciden con las 2358 fuentes actuales. La evidencia global anterior se conserva para el código estable y se complementa con la revalidación del delta; **no se afirma que sus hashes antiguos sean todos actuales**.

Ruff lint y format check de `context.py` final devolvieron 0. Sonar volvió a procesarlo con cobertura completa y cero diagnósticos, sin cambiar el perfil ni añadir NOSONAR. Junto con las 1955 fuentes Python/stubs estables, esto mantiene la cobertura de las 1956 entradas. La única excepción nueva es Ruff UP045 en la línea de la referencia diferida, justificada por el comportamiento reproducido de dataclasses 3.15.

No hay mypy, pyright u otro checker estático configurado en el proyecto. Se verificaron sintaxis, resolución runtime de anotaciones mediante pruebas existentes/sondeos contrastados e imports; **no se inventa una ejecución de un checker no configurado**.

### 5.4 Rendimiento y ejemplos

`E\view-probes-8aeeae43.json` conserva código actual de los escenarios y cinco pares HEAD/current con hashes semánticos equivalentes, 2003 mensajes de regex por variante, GC habilitado y cero violaciones. Registró ocho procesos fríos, cada uno con 39 módulos/83 funciones inspeccionadas.

- Regex no coincidente de 2048 caracteres: mediana **11518,984 → 53,756 µs**.
- Retención de planes: **10000/3,575 MB → 1024/472–484 KB**.
- Costes que no se ocultan: URL absoluta **0,490 → 0,840 µs**; clave de bytecode **1,504 → 3,102 µs** por la validación portable.

Son resultados de escenarios específicos, no rendimiento global ni equivalencia a C. No se repitieron benchmarks sin cambios relevantes en esas rutas.

Los reportes manuales `manual-scope-167b3d5c.json` y `manual-scope-5c433379.json` documentan primero **58/62 aprobados y cuatro fallos**, después **4/4 rechecks aprobados**. Los 62 bloques literales resultantes coinciden por SHA con los actuales y 23 pares EN/ES son equivalentes. No se convierte el primer resultado en 62/62.

Cinco dependencias Python cambiaron después de esos snapshots: `orionis/auth/contracts/__init__.py`, `orionis/console/fluent/task.py`, `orionis/console/tasks/_backend.py`, `orionis/http/adapters/response/streams.py` y `orionis/mcp/__init__.py`. Para resolver esa limitación se ejecutó una nueva tanda completa el 13 de noviembre: **62/62 bloques aprobados**, Foundation 14, Console 14 y HTTP 34; **23/23 pares EN/ES**, 102 invocaciones de definiciones, exit 0, cero violaciones y cero avisos de recursos. Los **2358/2358 hashes de fuentes** y los 62 bloques coincidían con el checkpoint previo a F07, incluidos `MANIFEST.in` y `py.typed`. **R18 queda COMPLETADO.**

Evidencia durable: `E\manuals-final-current-2e1f1c33\manual-scope-1392856c.json`, SHA-256 `9fc74452d47bf4fbdf71af056305527ce5f4854964d071817911b7a1796caf01`, además de `summary.json`, `launcher.log` y el manifiesto del harness. Duración aproximada por marcas de archivos: 162,494 s, incluyendo snapshot, procesos y limpieza; no es un benchmark. El snapshot fue retirado. Se usaron Python 3.14.6, Orionis 1.5.1, msgspec 0.22.0, SQLAlchemy 2.1.6 y APScheduler 3.11.3. No se modificaron ejemplos ni dependencias para hacerlos pasar.

**Revalidación que prevalece tras F07:** `M\manual-scope-4f853e9a.json`, SHA-256 `09bb17365757974dc228c27229ea76c2de9a397985cc67d749066cfea423c2c6`: nuevamente **62/62 PASS**, 23/23 pares, 102 invocaciones, cero violaciones/avisos y **2358/2358 hashes actuales**; 407,115 s de pared incluyendo preparación y limpieza. `M\summary.json` conserva comandos, dependencias y la comparación exacta de un único archivo cambiado. La tanda anterior no se presenta como si hubiese ejecutado el cambio posterior.

### 5.5 Continuación autorizada con Docker: Linux, Redis y Python posterior

El usuario autorizó ajustar `D:\WORKSPACE\ORIONIS_FRAMEWORK\_UTILIDADES_\all_databases` y utilizar Docker. Se añadió una configuración independiente; `docker-compose.yml` existente conserva SHA-256 `0ba12dd2e27d53144cbaf2b8406a87b2f8973eaaad2bc0a53a43d9eb089971d4`, y no se recorrió ni operó su `data/`.

Docker Desktop en modo Linux ejecutó Python 3.14.6 y **3.15.2**, ambas desde imágenes oficiales fijadas por digest. Se comprobó 3.15 mediante el registro y el intérprete real; el inventario anterior de Windows no bastaba para descartar esa versión disponible. `pyproject.toml` acepta `>=3.14`; CI conserva su versión configurada 3.14 y no se atribuye un run remoto de CI.

Dependencias: `uv sync --frozen --all-groups --extra redshift --no-install-project`, uv 0.11.30, mismo `uv.lock`, uvloop 0.23.0 y cliente Redis 8.1.0. Servidor propio Redis **7.4.12**, imagen `redis:7.4-alpine@sha256:7f7d30b7fdd09467bac58198a1f166dd69789d348d4fe859cccb20e0cf287fbe`.

| Ejecución real | PASS | FAIL | SKIP | Exit / interpretación |
|---|---:|---:|---:|---|
| Selección aio + Redis, Linux 3.14 | 94 | 0 | 0 | 0; incluye 14 Queues, 4 HTTP y 2 uvloop reales |
| Global inicial, Linux 3.14 | 9686 | 1 | 1 | 1; 9688 casos; fallo de permiso de ejecución en tmpfs |
| Global inicial, Linux 3.15 | 9684 | 6 | 1 | 1; 9691 registros, incluidos cuatro subtests fallidos en lugar de un caso agregado |
| Instalación, Linux 3.14, tras corregir tmpfs | 39 | 0 | 0 | 0 |
| Instalación, Linux 3.15, tras corregir tmpfs | 39 | 0 | 0 | 0 |
| MCP + Foundation finales, Linux 3.14 | 444 | 0 | 0 | 0; 194 + 250 |
| MCP + Foundation finales, Linux 3.15 | 444 | 0 | 0 | 0; 194 + 250 |
| MCP + Foundation finales, Windows 3.14 | 444 | 0 | 0 | 0; guard, cero violaciones |

Las globales duraron 583,597 s y 599,116 s incluyendo preparación del runner, respectivamente. Son tiempos operativos bajo carga local, no benchmarks comparables de rendimiento.

**Cobertura acumulada:** reemplazando únicamente los selectores revalidados, cada versión Linux conserva **9688 casos base únicos: 9687 PASS y 1 SKIP**, sin nombres perdidos o duplicados. `L\combined-evidence.json` contiene conteos iniciales, paquetes y comparación de conjuntos. Las ejecuciones globales iniciales **siguen teniendo exit 1**; no se reescribieron sus resultados ni se sumaron rechecks duplicados para inflar aprobaciones. Se revisaron de nuevo los paquetes afectados, sin repetir innecesariamente todo lo que ya había pasado.

Todos los 28 paquetes están cubiertos en ambas versiones. Frente a las cifras Windows de la sección 4, la cobertura Linux acumulada cambia solo en aio **76/0**, HTTP **982/0**, Queues **169/0** y Mail **197/1** (PASS/SKIP). Los demás paquetes conservan sus conteos PASS, más 63 casos de raíz y 14 pruebas del generador. La omisión es `TestFileTransport.testRejectsAnchoredButRelativePaths`; la fuente `tests/mail/transports/test_file.py:355` llama a `skipTest` cuando la plataforma no reconoce rutas relativas a una unidad Windows. El motivo se comprobó en fuente: el JSON y log del runner no lo incluyen. No se suma ese caso a PASS Linux.

**Aislamiento observado:** usuario 1000, imagen de solo lectura, sin mounts del host, sin puertos publicados, capacidades eliminadas, red interna con Redis efímero autenticado, bases separadas para HTTP y Queues. Los snapshots excluyeron `docs/`, `tests/real_database/`, `.env` real, cachés y datos antes de abrir/copiar. El Linux runner permite procesos hijos propios, necesarios para comprobar atomicidad Redis entre procesos; no emplea el guard Windows como sustituto del contenedor.

**Correcciones de infraestructura verificadas:** `/work` pasó de `noexec` a `exec` para que la prueba pudiera ejecutar el intérprete de su venv; los 39 casos de instalación pasaron en cada Python. El lanzador ahora usa `run --rm`, una copia de Compose por ejecución y el Dockerfile del snapshot. Una ejecución inicial dejó su contenedor de tests y otra falló al limpiar porque el Compose compartido había cambiado; se retiraron únicamente esos recursos propios y las ejecuciones posteriores comprobaron la limpieza automática. No hubo cambios de permisos en el host ni limpieza global de Docker.

Los archivos nuevos de infraestructura son `compose.audit.yml`, `Run-OrionisAudit.ps1`, `README.audit.md` y `audit/{Dockerfile,prepare.py,run.py}` bajo `all_databases`. Sintaxis PowerShell/Python y lint aislado de los dos auxiliares Python: PASS. Los resultados completos y logs originales están preservados en `L`; snapshots e imágenes de caché permanecen fuera del checkout. No se iniciaron los servicios SQL del Compose existente.

Comprobación final de limpieza: **cero contenedores y cero redes de auditoría restantes**, registrada en `L\docker-cleanup-verification.json`. `L\final-integrity.json` acredita los 2358 hashes actuales, índice y Compose original conservados, `git diff --check` 0, y mismo perfil/plugins Sonar. El nuevo trace de Sonar no contiene mensajes de error, incluido su cierre; esto no borra la observación del trace histórico.

## 6. Hallazgos por severidad

| ID | Severidad | Estado | Hallazgo, impacto y tratamiento |
|---|---|---|---|
| F01 | P2 | **CORREGIDO** | Wheel con `Typing :: Typed` y 24 `.pyi` sin `py.typed`; distribución de tipos incompleta. Añadido marcador e inclusión explícita; ambos artefactos e instalación verificados |
| F02 | P2 / limitación | RESUELTA en Linux | 18 Redis y dos uvloop reales PASS en entornos propios; no se añadieron ni ocultaron skips |
| F03 | P2 / incertidumbre histórica | NO VERIFICABLE | Incidente previo de formatter impide demostrar retrospectivamente toda exclusión/conservación del árbol protegido. El usuario autorizó conservar y revalidar; no hay defecto de producción demostrado por ello |
| F04 | P3 | ABIERTA, no bloqueante | `ClosedSelectorException` en cierre HTTP de Sonar, posterior a cobertura/resultado completos y con exit 0; no se detectó pérdida de análisis |
| F05 | P3 / límite documental | RESUELTA | Nueva tanda íntegra de 62 bloques con dependencias finales y 2358 hashes actuales coincidentes; 62/62 aprobados, cero violaciones/avisos de recursos |
| F06 | P2 / infraestructura | CORREGIDA | tmpfs noexec impedía ejecutar el Python de la prueba de instalación. `/work:exec` y 39/39 rechecks en cada versión; limpieza del lanzador corregida y comprobada |
| F07 | P2 / compatibilidad | CORREGIDO | dataclasses 3.15 evaluaba una anotación textual de McpRequest y cargaba HTTP anticipadamente; referencia diferida explícita y 444/444 pruebas en Linux 3.14, Linux 3.15 y Windows 3.14 |

No hay hallazgos P0/P1 comprobados abiertos. La severidad se refiere a impacto demostrado; un riesgo potencial no se presenta como vulnerabilidad explotable.

### Perfil y autorizaciones Sonar

Se verificaron decisiones primarias de la sesión Copilot `745eed3b-fbab-4e9d-992e-da09159ffc68`, no solo el relato de un agente:

| Decisión | Fecha UTC | Evento de respuesta |
|---|---|---|
| S100 camelCase, manteniendo activa la regla | 2026-11-12 23:30:25 | `1c071e1f-b32a-4da7-909a-47274acbf040` |
| Conservar formato adicional y validar snapshots excluidos | 2026-11-13 02:30:57 | `257d5f53-af23-4b4d-a9ab-e834319c998d` |
| Excepciones por línea/regla solo con evidencia y justificación | 2026-11-13 10:12:47 | `d98714b2-e4a4-4a8f-8f94-3b31b1f2475e` |

Preguntas/respuestas completas quedaron en `A\evidence-review.json`. Se conservan las autorizaciones anteriores de S116/camelCase y GCM/rechazo CBC. El perfil actual mantiene S100/S116 activas; no se encontraron overrides que apaguen reglas globalmente.

Hay **147 comentarios NOSONAR: 47 específicos de regla y 100 generales preexistentes**. Los generales disminuyeron desde 111 en los mismos archivos de HEAD; ningún archivo aumentó su cantidad general. Los específicos cubren S1110×34, S7503×6, S5754×2, S1845×2, S2245×1, S930×1 y S5332×1. Su aplicación es nativa del analizador; no es un filtrado de resultados por el cliente. El análisis sin NOSONAR `sonar-probe-29a890b1.json` produjo **123 diagnósticos** y se conserva como tal, no como un análisis limpio.

La excepción de shutdown aparece después del mensaje de cero issues y de la cobertura completa. El campo `analysis_errors` del JSON se calcula antes del cierre: su valor no permite afirmar que el proceso nunca emitió un error.

## 7. Corrección final aplicada

### F01: señalización PEP 561 ausente

**Reproducción:** construir el wheel original de 1.5.1, inspeccionar su índice y metadata. Contenía `Typing :: Typed` y 24 stubs `.pyi`, pero no `orionis/py.typed`; tampoco existía el marcador en las fuentes. Es una deficiencia real de distribución de tipos, sin fallo de runtime demostrado. La especificación exige el marcador para distribuir información de tipos dentro de un paquete. [Especificación oficial de typing](https://typing.python.org/en/latest/spec/distributing.html#packaging-type-information).

**Cambio mínimo:**

- `orionis/py.typed`: archivo marcador vacío.
- `MANIFEST.in`: una línea `include orionis/py.typed`.

En F01 no se eliminaron classifiers, no se añadieron dependencias ni se cambiaron APIs, lógica, tests existentes, perfiles o validadores. La comprobación de regresión fue sobre **los artefactos reales**: ausencia antes, presencia en wheel/sdist/instalación después; no una aserción que solo repita el contenido del manifiesto.

**Validación del resultado:**

- Wheel final: 1264 entradas, 24 `.pyi`, 32 `.stub`, marcador presente.
- Sdist final: 1541 miembros, marcador presente.
- Instalación offline a destino propio y smoke: exit 0; 28 paquetes importados desde el wheel instalado, exportaciones raíz resueltas, versión 1.5.1, AES-GCM encrypt/decrypt real correcto.
- Ningún artefacto incluye el directorio generado raíz ni `tests/real_database/`.
- SHA-256 wheel del checkpoint PEP 561: `745a02416b0a49a2705111ae59c78b85b83cb64f073d4657dd0f76202bd4ff75`.
- SHA-256 sdist del checkpoint PEP 561: `0b1f55699e4e021825af4d9f5f2e310bcbccecc32e9276b860f1914eda0f1afe`.

Hubo dos errores en comprobaciones auxiliares iniciales del auditor: un predicado que confundía `resources/docs/` fuente con el directorio generado raíz, y un smoke que usaba una firma inexistente `Encrypter(key=..., cipher=...)`. Se corrigieron las comprobaciones, no el producto: el smoke final usa el contrato real `Encrypter(app)` con configuración sintética. Los logs iniciales se conservan y no se cuentan como defectos de Orionis ni como aprobaciones.

### F07: import diferido de MCP en Python 3.15

**Reproducción real:** la global Linux 3.15 falló en `tests.foundation.test_lazy_consumers.TestLazyConsumers.testMcpMetadataDoesNotLoadUnusedRuntimeImplementations` y cuatro subtests de `tests.mcp.test_integration.TestMcpIntegration.testRuntimeTypesPreserveColdImportsAndNativeRequestIdentity`, con entradas `orionis.mcp.context`, `invoker`, `server.compiler` y `transport.stdio`. Todos detectaban `orionis.http.request` cargado prematuramente.

**Causa comprobada:** `dataclasses._get_type_from_annotation` de Python 3.15 recorre los componentes de la cadena `"http_module.Request | None"` mediante `getattr`; eso activaba el export diferido de HTTP al construir `McpRequest`.

**Cambio mínimo:** en `orionis/mcp/context.py`, importar `Optional` y declarar `native_request: Optional["http_module.Request"] = None`, con comentario de la causa y `# noqa: UP045` únicamente en esa línea. El delta propio fue +4/-3; revertir solo sus tres reemplazos en memoria reproduce exactamente el hash anterior. `McpContext`, orden/defaults de campos y tipo público resuelto `Request | None` se conservan. No se modificaron tests ni se añadieron nuevas funcionalidades.

**Validación:** sondas independientes de imports y anotaciones en 3.14/3.15; 194 pruebas MCP y 250 Foundation en cada uno de Linux 3.14, Linux 3.15 y Windows 3.14; 62 ejemplos finales; Ruff/format del archivo y Sonar real, todos aprobados. La regresión ya estaba cubierta por pruebas existentes, que se conservaron.

**Distribución final que sustituye los artefactos anteriores:** `L\packaging-final\dist\orionis-1.5.1-py3-none-any.whl` y `orionis-1.5.1.tar.gz`. Build, instalación offline y smoke devolvieron 0; 1264 entradas wheel, 1541 miembros sdist, 24 stubs `.pyi`, 32 `.stub`, marcador en ambos y en instalación. Los 28 paquetes se importaron desde el destino instalado; MCP frío, hints de clase/constructor y AES-GCM real pasaron, con cero violaciones del guard. El hash de `context.py` coincide en fuente, wheel, sdist e instalación.

- Wheel final SHA-256: `d780be91596f79755b60e2b2e98c03a886db0773fbcf15707f365bb3a6677ea0`.
- Sdist final SHA-256: `1c5dc2de7bea497bb26895c5b38128ad8b167d0e0d6492cfb9d09464c518a33c`.

El primer intento de esta reconstrucción falló porque el harness de tests heredaba `UV_NO_BUILD=true`. Se retiró solo esa variable para el build, manteniendo modo offline y sin aislamiento de build; no se cambiaron dependencias ni se ocultó el intento fallido, conservado en `C:\Users\runate\AppData\Local\Temp\orionis-packaging-final-20261113-976d1899`.

## 8. Validación limitada de DOCS.ps1

| Comprobación autorizada | Resultado |
|---|---|
| Sintaxis PowerShell | **PASS**, cero errores del parser; PowerShell 7.6.9 |
| Dependencias y rutas del generador | **PASS**; Pydoctor 25.10.1, setuptools 84.2.1, `$PSScriptRoot` y staging coherentes |
| Ejecución del generador | **PASS**, una sola ejecución, 550,859 s |
| Código de salida | **0** |
| Artefactos esperados | **10/10 presentes y no vacíos**, incluido `index.html` |
| Total generado | **2281 archivos**, conteo exclusivamente de metadatos |
| Errores críticos detectados | **0** |

Comando ejecutado desde la raíz: `pwsh -NoProfile -File .\DOCS.ps1`, con `UV_FROZEN=true` y `UV_NO_SYNC=true`, para impedir cambios de resolución/sincronización de dependencias. La salida extensa quedó en `D\generator.log`, fuera del directorio generado y del repositorio.

Se revisó únicamente el script y sus dependencias fuente necesarias: Pydoctor con `--warnings-as-errors`, comprobación de códigos nativos, staging previo, integridad de artefactos, rollback y cleanup acotado. El flujo ejecutó sus comprobaciones integradas; no se lanzó una segunda validación del sitio ni se abrió HTML generado para auditarlo.

Los hashes de `DOCS.ps1`, `pyproject.toml`, `uv.lock`, `resources/docs/pydoctor/system.py` y `validate.py` permanecieron iguales. Después de F07 se comprobó además el procesamiento de las fuentes finales con Pydoctor `--testing --warnings-as-errors`, el mismo `DocumentationSystem`, Python 3.14.6 y salida 0. Esa comprobación se hizo en un contenedor sin red, sobre el snapshot final y **sin producir HTML ni invocar DOCS.ps1 de nuevo**; su log está en `L\pydoctor-final-source.log`. No revalida renderizado ni enlaces: preserva la distinción entre la generación anterior satisfactoria y el análisis posterior de entradas.

**Este PASS certifica el generador y la estructura esperada; no una revisión exhaustiva de enlaces, firmas o contenidos generados.** No se incluyen inventarios ni análisis individuales de salida.

## 9. Riesgos residuales y límites

1. **Integraciones externas:** Redis real quedó validado en Linux, incluidos procesos concurrentes. Esto no certifica todas las versiones/proveedores de Redis ni servicios SQL/cloud reales; `tests/real_database/` sigue excluido. No se ejecutaron servicios de producción.
2. **Plataformas/intérpretes:** se validaron CPython 3.14.6 Windows/Linux y 3.15.2 Linux. No se certifican macOS, free-threaded, variantes futuras ni una ejecución remota de CI. Las globales Linux iniciales fallaron; el resultado corregido combina esas evidencias con rechecks de los selectores afectados, no un nuevo run global verde.
3. **Conservación retrospectiva:** la pregunta original del incidente de formatter reconoció comandos sin selectores previstos, 366 cambios fuera de Console y falta de certeza retrospectiva. La respuesta `retain-and-validate` permite conservarlos; no demuestra que nunca se visitó o alteró el árbol protegido. No se inspeccionó ese árbol para intentar certificarlo.
4. **Ejemplos/manuales y salida generada:** los 62 bloques quedaron reejecutados tras F07, con hashes actuales. La generación completa corresponde al checkpoint previo; las fuentes finales pasaron Pydoctor sin generación. No se certifica identidad byte a byte del sitio con el último árbol ni revisión universal de contenidos/enlaces.
5. **Scheduler:** depende de hooks protegidos de APScheduler 3, limitado a `<4`. Una actualización mayor exige revalidar lifecycle/finalización; no es una vulnerabilidad nueva demostrada.
6. **Migración CBC:** la ruptura aprobada exige gestionar datos CBC existentes antes de actualizar una aplicación que los conserve. No se migraron datos reales ni se deduce autorización para hacerlo.
7. **Rendimiento:** mejoras y costes específicos están medidos; no se certifica rendimiento máximo ni ausencia universal de degradación bajo cargas no ejecutadas.
8. **Seguridad/typing:** esta auditoría contrasta correcciones y pruebas; no es pentest, escaneo completo de advisories de terceros ni ejecución de un checker estático no configurado.

## 10. Estado Git, reproducción y recomendación de cierre

Rama `1.x`, HEAD `036d04bac1381cc4f35c49431bb41a77d18419c3`, sin cambios de commit. Todo estado Git citado **excluye `docs/` y `tests/real_database/`**. No se comparó ni enumeró salida generada mediante Git.

Al comenzar había 1955 rutas pendientes en el alcance permitido: 1873 ` M`, seis `M `, una `AM`, dos `MM` y 73 `??`. Después de la corrección, antes del informe: 1957 rutas —1874 ` M`, seis `M `, una `AM`, dos `MM` y 74 `??`—. Este informe agrega otra ruta sin seguimiento. El índice existente se preservó; no hubo staging, commit, push, eliminación de cambios ajenos o publicación remota.

La continuación Docker modifica `context.py` sobre su estado previo, actualiza este informe y el encabezado de `HANDOFF_ORIONIS.md`, y crea los seis auxiliares de infraestructura fuera del repositorio `framework`. La carpeta de utilidades no pertenece a este repositorio Git. El índice filtrado conserva SHA-256 `300b56277ec7e5f47a32bb458913eda5d91e622165dca380b6e94cc85a00722f`. El estado final permitido conserva **1958 rutas: 1874 ` M`, seis `M `, una `AM`, dos `MM` y 75 `??`**; los archivos modificados de esta continuación ya eran pendientes, por eso sus cantidades no aumentan.

`git diff --check` filtrado devolvió **0**. Git emitió advertencias de conversión LF→CRLF; no son errores de whitespace ni autorización para normalizar de nuevo. Los auxiliares/builds se guardaron fuera del checkout. La generación local autorizada es la única operación sobre la salida documental; se omiten sus detalles Git conforme a la exclusión.

### Comandos esenciales reproducibles

```powershell
Set-Location -LiteralPath 'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework'
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
$audit = 'C:\Users\runate\AppData\Local\Temp\orionis-final-audit-20261113-cyk047fw'

& $python -X utf8 -B "$audit\validation\verify_guard.py"
& $python -X utf8 -B "$audit\validation\native_suite.py" `
    (Get-Location).Path 'tests/test/core/test_engine.py' `
    'tests/view/test_global_regressions.py' 'tests/mail/test_integration.py' `
    'tests/queues/test_integration.py' 'tests/realtime/test_integration.py' `
    'tests/mcp/test_integration.py' 'tests/http/adapters/test_sse_lifecycle.py' `
    'tests/console/test_cli.py' 'tests/foundation/test_application_lifecycle.py' `
    'tests/foundation/test_failure_lifecycle.py' 'tests/auth/test_context_regressions.py' `
    'tests/session/stores/test_store_regressions.py' 'tests/schemas/test_core_regressions.py' `
    'tests/storage/test_resource_regressions.py' 'tests/hashing/test_cache_concurrency.py' `
    --label 'final-audit-independent' --continue-on-error

uv pip check --python $python
uv python list --only-installed
git --no-optional-locks diff --check -- . `
    ':(exclude)docs' ':(exclude)docs/**' `
    ':(exclude)tests/real_database' ':(exclude)tests/real_database/**'
```

La lista Python exacta y hashes están en `A\quality.json`. Ruff se ejecutó en lotes explícitos de 40 archivos, usando `check --no-cache` y `format --check --no-cache`; se añadieron al formato los 290 manuales fuente, **nunca `docs/`**. El inventario salió de `git ls-files --cached --others --exclude-standard -z` con las mismas exclusiones de pathspec y filtros de cachés/entornos/build antes de abrir archivos.

Build/instalación sobre la copia final propia ya generada, con destinos nuevos y sin tocar el entorno del proyecto:

```powershell
$packaging = 'C:\Users\runate\AppData\Local\Temp\orionis-packaging-final-20261113-263ed5fd'
$repro = Join-Path $env:TEMP ('orionis-build-repro-' + [guid]::NewGuid().ToString('N'))
$previousNoBuild = $env:UV_NO_BUILD
try {
    $env:UV_NO_BUILD = $null
    uv build --offline --no-build-isolation --python $python --sdist --wheel `
        --out-dir "$repro\dist" "$packaging\project"
} finally { $env:UV_NO_BUILD = $previousNoBuild }
uv pip install --offline --no-deps --no-config --python $python `
    --target "$repro\installed" "$repro\dist\orionis-1.5.1-py3-none-any.whl"
```

La copia se generó con `snapshot` del harness auditado, que conserva fuentes actuales rastreadas y nuevas y poda los árboles prohibidos. No ejecutar suites contra el checkout con `.env` real ni sustituir la copia por `git archive HEAD`, que perdería cambios sin confirmar. Si desaparecen estos temporales, reconstruir esa infraestructura antes de invocar sus rutas; no simular ejecuciones.

El comando documental reproducible es `pwsh -NoProfile -File .\DOCS.ps1` con las variables descritas en la sección 8. **No repetirlo como paso adicional de esta auditoría: ya se ejecutó una vez satisfactoriamente.**

### Reproducción de la continuación Docker y el delta final

Las invocaciones siguientes representan **alternativas de reproducción**, no una orden de repetirlas todas ahora. Cada ejecución Docker prepara fuentes actuales, usa proyecto/contraseña propios y conserva sus logs fuera del checkout. El Python de Windows prepara el snapshot; la suite corre con el intérprete indicado dentro de Linux.

```powershell
$launcher = 'D:\WORKSPACE\ORIONIS_FRAMEWORK\_UTILIDADES_\all_databases\Run-OrionisAudit.ps1'
$python315 = 'python:3.15.2-slim-bookworm@sha256:6cae5760197a96ea5d0a41ae2e045733c351d605c61148dd030aafdf4919e33a'

# Global Linux 3.14.6 (imagen predeterminada fijada por digest).
& $launcher
# Global Linux 3.15.2, mismo uv.lock.
& $launcher -PythonImage $python315

# Selección que verificó las 18 integraciones Redis y dos uvloop.
& $launcher -Selectors @('tests/aio',
    'tests/queues/drivers/test_redis_integration.py',
    'tests/http/layer/store/test_redis_rate_limit_integration.py')

# Rechecks mínimos usados tras las correcciones, en cada versión.
& $launcher -Selectors @('tests/console/commands/support/test_install.py')
& $launcher -PythonImage $python315 -Selectors @('tests/console/commands/support/test_install.py')
& $launcher -Selectors @('tests/mcp', 'tests/foundation')
& $launcher -PythonImage $python315 -Selectors @('tests/mcp', 'tests/foundation')

$evidence = 'C:\Users\runate\.copilot\session-state\745eed3b-fbab-4e9d-992e-da09159ffc68\files'
$finalWindows = Join-Path $evidence 'final-context315-validation-20261113-dc1e47a2'
$finalDocker = Join-Path $evidence 'docker-final-20261113-632fc91e'
& $python -X utf8 -B "$finalWindows\validation\manual_scope.py"
& $python -X utf8 -B "$finalWindows\validation\native_suite.py" `
    'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework' tests/mcp tests/foundation `
    --label windows-context315 --continue-on-error
& $python -m ruff check --no-cache orionis/mcp/context.py
& $python -m ruff format --check --no-cache orionis/mcp/context.py
& $python -X utf8 -B "$finalDocker\validation\sonar_probe.py" orionis/mcp/context.py
```

El parser de fuentes finales de Pydoctor se ejecutó con este comando, sin configuración de red/intersphinx y sin HTML. La imagen local contiene el snapshot final; no sirve para validar cambios futuros sin reconstruirla:

```powershell
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' run --rm `
    --network none --read-only --user 1000:1000 --cap-drop ALL `
    --security-opt 'no-new-privileges:true' `
    --tmpfs '/tmp:rw,size=512m,uid=1000,gid=1000,mode=1777' `
    --env 'PYTHONPATH=/opt/snapshot' --env 'PYTHONDONTWRITEBYTECODE=1' `
    --env 'HOME=/tmp' --workdir /tmp --entrypoint /opt/venv/bin/python `
    orionis-audit-tests:06408fa1e9e3 -m pydoctor --testing --warnings-as-errors `
    --project-base-dir /opt/snapshot `
    --system-class resources.docs.pydoctor.system.DocumentationSystem `
    --docformat numpy --project-name Orionis /opt/snapshot/orionis
```

El README de utilidades contiene el uso operativo. `L\tools` conserva una copia de los seis auxiliares, y `L\validation` los auxiliares Windows/Sonar usados para reproducir el delta. Ningún comando requiere leer HTML generado ni la carpeta de pruebas excluida.

### Dictamen definitivo

**GO CON OBSERVACIONES.** Las verificaciones esenciales del alcance local están sustentadas, los defectos de empaquetado e imports MCP quedaron corregidos y no hay un bloqueante de producción demostrado abierto. **21/22 requisitos, 95,5 %**; no quedan requisitos parciales o pruebas obligatorias pendientes en la matriz, pero **R21 permanece NO VERIFICABLE**. No se presenta como 100 % ni como ausencia universal de defectos.

Los 18 casos Redis, dos uvloop, Python 3.15 y los 62 ejemplos antes pendientes ya están cubiertos. Para convertir R21 en verificado se requeriría evidencia contemporánea fiable del incidente histórico, sin vulnerar la exclusión del árbol protegido; más ejecuciones Docker no pueden producirla. Antes de extender la recomendación a otros servicios/plataformas, validar esos escenarios. Una modificación futura de fuentes o perfiles requiere comprobar su delta y consumidores, sin reiniciar lo ya acreditado.
