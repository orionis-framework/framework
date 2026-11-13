# HANDOFF ORIONIS — revisión integral del framework

**Fecha del traspaso: 12 de noviembre de 2026, America/Bogota.**
**Destinatario: GitHub Copilot con GPT-6 Astra.**
**Repositorio: `D:\WORKSPACE\ORIONIS_FRAMEWORK\framework`.**

## Actualización vigente: cierre del 13 de noviembre de 2026

Este bloque prevalece sobre los estados pendientes históricos de las secciones
0–12. **El encargo original íntegro y el foco de los 28 paquetes siguen en la
sección 1; no se sustituyeron ni recortaron.** El usuario autorizó después una
auditoría de cierre, el informe `FINAL_AUDIT_ORIONIS.md` y el uso de Docker y de
`D:\WORKSPACE\ORIONIS_FRAMEWORK\_UTILIDADES_\all_databases` para las pruebas faltantes.

**Dictamen vigente: GO CON OBSERVACIONES; 21/22 requisitos operativos verificados
(95,5 %), cero parciales o pendientes de ejecución en esa matriz, un requisito
NO VERIFICABLE: R21, inmutabilidad histórica del árbol protegido durante el
incidente anterior del formateador.** No afirmar 100 %: nuevas pruebas no pueden
reconstruir evidencia histórica ausente. No hay defectos bloqueantes de producción
comprobados abiertos. El porcentaje no representa cobertura de líneas ni garantía
universal de seguridad o rendimiento.

Resultados esenciales que Copilot debe preservar:

- Base Windows contrastada: 9668 PASS/20 SKIP. Ejecución independiente inicial
  adicional: 164/164 PASS.
- Redis y uvloop reales: selección Linux 94/94 PASS, con 14 Queues Redis,
  cuatro HTTP Redis y dos uvloop. Linux usa Redis efímero propio, autenticado,
  sin puertos publicados, montajes del host o datos de producción.
- Global Linux 3.14.6: 9686 PASS/1 FAIL/1 SKIP. Global Linux 3.15.2:
  9684 PASS/6 FAIL/1 SKIP; 9691 registros por expansión de subtests fallidos.
  Esos resultados iniciales **siguen siendo fallidos**, no deben renombrarse PASS.
  Tras corregir el entorno de instalación y MCP, pasaron 39/39 pruebas de
  instalación y 444/444 de MCP+Foundation en cada Python. La combinación por
  selectores conserva 9688 casos base únicos: 9687 PASS/1 SKIP por Linux;
  no es una nueva ejecución global verde. La omisión es una prueba de rutas
  relativas a unidades Windows; no se contabiliza como PASS Linux.
- Sobre el código final: Windows MCP 194/194 y Foundation 250/250 PASS;
  62/62 bloques documentales, 23/23 pares EN/ES y 102 invocaciones, sin violaciones
  ni avisos de recursos; manifiestos de 2358 fuentes coincidentes.
- Ruff y formato globales se conservaron para las fuentes estables y se
  reejecutaron sobre el único Python modificado; Sonar hizo lo mismo: 1955
  archivos estables más `context.py` final, cero diagnósticos, mismo perfil.
- Wheel/sdist finales construidos e instalados offline; 28 imports, marcador
  `py.typed`, MCP frío/tipos resueltos y AES-GCM real aprobados.
- DOCS.ps1: sintaxis PASS, una generación PASS, exit 0, 2281 archivos contados
  solo por metadatos y 10/10 artefactos esperados. Tras el último cambio se
  procesaron las fuentes con Pydoctor `--testing --warnings-as-errors`, exit 0,
  **sin generar HTML ni repetir DOCS.ps1**. No se revisaron enlaces/contenidos
  generados ni se afirma identidad byte a byte del sitio con el último árbol.

Cambios mínimos propios del cierre: marcador `orionis/py.typed`, inclusión en
`MANIFEST.in` y, al probar Python 3.15 disponible, una anotación en
`orionis/mcp/context.py`: `Optional["http_module.Request"]` conserva el tipo
resuelto `Request | None` sin activar HTTP al construir el dataclass. La causa
fue reproducida en `dataclasses._get_type_from_annotation` de Python 3.15.
Se añadió `noqa: UP045` solo a esa línea, con explicación; no se modificaron las
pruebas ni el perfil Sonar. SHA final de `context.py`:
`2764fb6e2ec2c1db1f39f5ecc52be292598c14fe0d3aa46fe705028d5c08e768`.

Infraestructura nueva: `compose.audit.yml`, `Run-OrionisAudit.ps1`,
`README.audit.md` y `audit/{Dockerfile,prepare.py,run.py}` bajo `all_databases`.
El Compose original y su `data/` se preservaron. El lanzador copia fuentes
actuales permitidas, usa configuraciones por ejecución, `/work` ejecutable para
venvs de prueba, `run --rm` y limpieza exclusiva del proyecto propio. Los fallos
iniciales de tmpfs/limpieza y su corrección están registrados, sin atribuirlos al
framework. Imágenes y evidencias se conservaron; no se hizo Docker prune.

Para reproducir una global, ejecutar el lanzador de utilidades; por defecto usa
Python 3.14.6. Para 3.15.2, pasar
`-PythonImage 'python:3.15.2-slim-bookworm@sha256:6cae5760197a96ea5d0a41ae2e045733c351d605c61148dd030aafdf4919e33a'`.
Para el delta de MCP usar `-Selectors @('tests/mcp','tests/foundation')`.
Los comandos completos, todos los hallazgos, límites, hashes de distribución y
estado Git están en `FINAL_AUDIT_ORIONIS.md` en esta misma raíz. No repetir las
validaciones sin cambios nuevos o una razón concreta.

Evidencia durable bajo
`C:\Users\runate\.copilot\session-state\745eed3b-fbab-4e9d-992e-da09159ffc68\files`:
`docker-final-20261113-632fc91e` (resultados iniciales, rechecks, Sonar, paquetes
y auxiliares) y `final-context315-validation-20261113-dc1e47a2` (Windows/manuales
finales). No hubo staging, commit ni push; rama `1.x`, HEAD
`036d04bac1381cc4f35c49431bb41a77d18419c3`, índice filtrado preservado.

**Exclusiones de máxima prioridad para continuar:** no leer, listar, analizar ni
comparar el contenido de `framework/docs/`; tampoco cargar inventarios antiguos
de ese directorio que puedan aparecer en apéndices históricos de este handoff.
`tests/real_database/` sigue excluido antes de descubrir/copiar/importar pruebas.
Usar solo fuentes permitidas, snapshots propios y los filtros explícitos del
informe final. No iniciar otra revisión global ni ampliar funcionalidades para
intentar borrar la incertidumbre R21.

## Cómo usar este documento como fuente de verdad

Este archivo contiene **el encargo original íntegro**, las aclaraciones y autorizaciones posteriores, el estado comprobado al detenerse y las instrucciones para continuar. Copilot no necesita acceder al chat ni al adjunto original para conocer qué se pidió hacer. Las referencias a esos soportes indican procedencia, no requisitos para entender el encargo.

- **Qué se pidió y cómo se acepta:** sección 1, incluida la transcripción íntegra de sus once apartados y el foco obligatorio de cada uno de los 28 paquetes.
- **Qué está hecho y qué falta:** actualización vigente al principio de este archivo y `FINAL_AUDIT_ORIONIS.md`; la sección 0.6 y continuaciones anteriores conservan checkpoints históricos. Las secciones 2–7 son historial original, no el estado vigente. Los resultados históricos, las comprobaciones actuales y los límites se distinguen explícitamente.
- **Cómo continuar:** secciones 8–11, con comandos, prerrequisitos, orden de trabajo y riesgos.
- **Qué preservar:** sección 12, con el inventario y las huellas de los cambios existentes.

**Precedencia para interpretar el encargo:** las instrucciones posteriores expresas del usuario prevalecen sobre el texto original cuando lo modifican. En concreto: la creación de este informe quedó autorizada pese a la prohibición inicial de informes; se autorizaron S116/camelCase y GCM/rechazo de CBC. La orden de detener cambios correspondía al traspaso original. **El 12 de noviembre de 2026 el usuario autorizó expresamente a Copilot a continuar la revisión, mantener el progreso y actualizar este archivo.** Aplicar el objetivo y los criterios originales con esas modificaciones, desde el estado pendiente aquí descrito; no reiniciar lo ya corregido. La sección 0.1 distingue la evidencia nueva del historial original.

Conservar `HANDOFF_ORIONIS.md`: no eliminarlo al aplicar la prohibición histórica de informes. Una vez reanudado el encargo, no pedir otra confirmación para pasar de un paquete al siguiente. Las aprobaciones S116 y GCM tienen ese alcance específico: no autorizan otras rebajas de perfil, rupturas de API ni operaciones de migración sobre datos reales.

Este documento fija los requisitos y el punto de traspaso, **no convierte resultados antiguos en aprobación del código futuro**. El código del repositorio, las herramientas y los nuevos resultados siguen siendo los objetos que Copilot debe inspeccionar y validar. Los recursos temporales desaparecidos se identifican como ausentes; no se exige consultar un log inexistente para entender ninguna decisión.

## 0. Leer primero: estado y autorización vigente

El usuario ordenó detener las nuevas modificaciones y producir este informe. En esta fase se hicieron inspecciones de solo lectura y se creó este documento; no se continuaron refactorizaciones, pruebas del framework, formateos, commits, staging ni regeneración de documentación. La siguiente intervención sobre código debe corresponder a una instrucción de reanudación del usuario. Este archivo es la excepción expresamente autorizada a la prohibición original de añadir informes al repositorio.

Ese párrafo describe la congelación original de Codex. La instrucción posterior de
continuación ya levantó esa pausa; las secciones 0.1–0.4 registran la reanudación.

**La revisión global NO está terminada.** Veinte paquetes llegaron al cierre de implementación/revisión local registrado durante el trabajo, con las salvedades de análisis y verificación indicadas abajo. `view` quedó en cierre parcial. Faltan las revisiones integrales de `mail`, `queues`, `realtime`, `mcp`, `http`, `console` y `foundation`, además del cierre global. Haber tocado un archivo de integración de esos paquetes no equivale a haber revisado el paquete completo.

La evidencia se distingue así:

- **Actual, inspeccionada:** archivos, diffs, configuración, inventarios estáticos y estado Git leídos al preparar este traspaso. No equivale a ejecutar pruebas.
- **Histórica, registrada en la conversación:** resultados efectivamente observados durante la revisión anterior. Se conservan sus cifras y límites, pero no se vuelven a presentar como ejecuciones del 12 de noviembre.
- **Pendiente/no observada:** ejecución que faltaba, proceso cuyo final no se observó o validación invalidada por cambios posteriores. Nunca significa aprobada.

### Pérdida de artefactos temporales: acción prioritaria al reanudar

El 12 de noviembre se comprobó que **ya no existen** estos directorios:

```text
C:\Users\runate\AppData\Local\Temp\orionis-review-pwv5t8d5
C:\Users\runate\AppData\Local\Temp\orionis-sonar-a9db8fd9d9574066ae9b59b9b7c3d157
```

Contenían el runner aislado `native_suite.py`, sus barreras de acceso, logs, manifiestos SHA, verificadores de manuales, benchmarks y el cliente LSP real de SonarLint. **Los comandos históricos que apuntan allí no funcionarán hasta recuperar o reconstruir esos auxiliares.** No se ha reconstruido ni certificado un sustituto durante el traspaso. Los cambios durables y las regresiones sí permanecen en el repositorio. No se debe borrar ni rehacer ese trabajo por faltar los logs.

Los agentes antiguos `/root/test_cases_client`, `/root/test_engine` y `/root/validation_environment` no estaban disponibles al intentar detenerlos. Los procesos de la sesión anterior no deben considerarse aún activos ni exitosos sin comprobarlo. El último sondeo de imports de View se había lanzado como sesión `77484`; no se recibió su resultado final. Los agentes usados para redactar este informe trabajaron exclusivamente en lectura y texto de preparación temporal.

### 0.1 Reanudación por Copilot: evidencia nueva del 12 de noviembre

Este bloque actualiza el punto de continuación; las secciones posteriores conservan
el historial de Codex y sus límites, salvo actualizaciones expresamente identificadas.
La revisión integral sigue **en curso**, no aprobada globalmente.

**Conservación comprobada antes de editar:** lectura íntegra de las 5632 líneas
(709721 bytes UTF-8) del informe original, incluidas todas las filas del apéndice;
3388/3388 SHA-256 y estados XY coincidentes, sin discrepancias. La única ruta adicional
era este informe. HEAD sigue siendo `036d04bac1381cc4f35c49431bb41a77d18419c3`.
El estado inicial era 2250 `M `, 2 `A `, 1066 ` M` y 71 `??`. No se encontraron
`AGENTS.md` en los ancestros ni en los árboles de código permitidos. Se confirmaron
los 28 paquetes, 1171 archivos Python dentro de ellos y dos módulos raíz.
No se ejecutó una comparación de contenido de la carpeta excluida.

El manifiesto inicial se conserva fuera del repositorio:

```text
C:\Users\runate\.copilot\session-state\745eed3b-fbab-4e9d-992e-da09159ffc68\files\orionis-baseline.json
SHA-256 de git ls-files --stage -z:
1fba74434aed05646cc8c189ecf486876db591e1774e98a860bb1623cdf860ff
```

**Entorno comprobado ahora:** Python 3.14.6, 99 distribuciones instaladas compatibles
según `uv pip check`, ninguna versión distinta de `uv.lock`. Las 22 entradas del lock
no instaladas son extras opcionales o `uvloop`; no se instalaron dependencias.
No hay un Python posterior a 3.14 en `uv python list --only-installed`.
Se conservan la configuración S116 autorizada y el carácter ignorado de
`.vscode/settings.json`.

**Infraestructura recuperada:** los dos directorios temporales históricos siguen
ausentes. Se reconstruyeron auxiliares en el directorio durable de esta sesión:

```text
C:\Users\runate\.copilot\session-state\745eed3b-fbab-4e9d-992e-da09159ffc68\files\validation\
  native_suite.py
  native_entry.py
  review_guard.py
  sitecustomize.py
  verify_guard.py
```

El runner copia archivos actuales rastreados y nuevos a un directorio propio; filtra
la carpeta excluida por nombre antes de inspeccionar/copiar, no copia `.env` ni
almacenamiento real, usa configuración sintética y un entorno de proceso con claves
permitidas explícitas. Ejecuta Reactor sin modificarlo. Los hooks de auditoría
rechazan lecturas protegidas, escrituras ajenas, SQLite externo, procesos sin guard
y conexiones de red no propias; un ledger provoca fallo aunque la aplicación capture
la excepción. Se verificaron **ocho rechazos esperados**, propagación a un hijo y
operaciones permitidas sobre SQLite y loopback propios. **No es un sandbox del
sistema operativo ni una garantía contra código nativo hostil.**
Los snapshots se eliminan al terminar; los hashes, logs y resultados quedan en
`files`, fuera del repositorio. La comprobación de rechazos usa exclusivamente
fixtures propias, nunca el `.env` o contenido excluido reales.

**Resultados ejecutados sobre las fuentes actuales, no heredados:**

| Comprobación | Resultado |
|---|---|
| Autocomprobación del guard | Exit 0; ocho rechazos esperados |
| `tests\test` mediante Reactor aislado | 192/192 PASSED; 0 omitidas; 0 violaciones |
| `tests\view` mediante Reactor aislado | 190/190 PASSED; 0 omitidas; 0 violaciones |
| Ruff, `orionis\view tests\view` | Exit 0; sin diagnósticos |
| Formato de View | Exit 0; 64 archivos ya formateados |
| Sonar IDE: URL y dos archivos de regresión | Análisis solicitado; Problems sin diagnósticos. No certifica cobertura completa |

Evidencia funcional: `files\runner-view-baseline-90723cfb.json` y sus logs `-0.log`
y `-1.log` dentro de la sesión indicada. Los 190 casos incluyen la sexta regresión
de esquemas HTTP y el contrato opcional asíncrono `warmup`; su verde ya está observado.

Comandos reproducibles desde la raíz, sin usar los temporales desaparecidos:

```powershell
$python = 'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework\.venv\Scripts\python.exe'
$checks = 'C:\Users\runate\.copilot\session-state\745eed3b-fbab-4e9d-992e-da09159ffc68\files\validation'
& $python -X utf8 -B "$checks\verify_guard.py"
& $python -X utf8 -B "$checks\native_suite.py" `
    'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework' `
    'tests\test' 'tests\view' --label 'runner-view-baseline'
& '.venv\Scripts\ruff.exe' check orionis\view tests\view --output-format=concise
& '.venv\Scripts\ruff.exe' format --check orionis\view tests\view
```

Este fue el primer punto de control, anterior a los cambios de Mail. La sección
siguiente contiene la continuación y sustituye su lista de validaciones pendientes.
El formatter avisa de COM812; no se desactivó la regla. No se hicieron staging,
commits, publicaciones externas ni llamadas a servicios reales.

### 0.2 Continuación: View revalidado, correcciones Mail y ORM integrado

**View, evidencia adicional nueva:**

- Ocho órdenes de importación en procesos independientes: 39 módulos y 83 funciones
  inspeccionadas con `typing.get_type_hints` en cada proceso, sin namespaces
  artificiales ni accesos bloqueados.
- Cinco pares HEAD/current alternados, en procesos distintos con el mismo intérprete
  y dependencias integradas. Se sustituyeron únicamente las cinco fuentes comparadas
  de View en la copia baseline; se comprobaron las rutas efectivamente importadas.
  Los resultados comparables, sus tipos, entradas no mutadas y 2003 mensajes de regex
  coincidieron. Se midieron CPU y tiempo de pared con GC habilitado, sin otra suite
  concurrente. Los cambios funcionales intencionales quedan cubiertos por regresiones,
  no se exige reproducir los defectos antiguos como equivalencia.
- Regex sin coincidencias de 2048 caracteres: mediana 12359.268 -> 56.840 us.
  El intervalo observado fue 11287.468-33762.188 frente a 26.248-143.116 us.
  Diez mil claves de rutas retuvieron 10000 planes/3575834 bytes en HEAD frente a
  1024 planes/457329-475424 bytes actuales. Esto acredita la eliminación de la
  búsqueda cuadrática y la retención acotada, no rendimiento global máximo.
- Hay costes adicionales que no se ocultan: clave de bytecode 2.088 -> 4.613 us,
  URL absoluta 0.568 -> 0.933 us; otras rutas tuvieron dispersión amplia. No se
  aplicaron microoptimizaciones nuevas.
- Pruebas consumidoras HTTP factory: 25/25, 0 omitidas/violaciones.
  Mail previo a sus cambios: 195/195, 0 omitidas/violaciones.

Auxiliares adicionales: `validation\view_probe.py` y `validation\validate_view.py`.
Evidencia: `files\view-probes-c318e768.json` y
`files\view-consumers-mail-baseline-3f64654c.json`. El probe mide render frío/caliente,
Pending, URL, planes de rutas y claves de bytecode; no sustituye un benchmark completo
de publicación/recarga de bytecode ni los ejemplos documentales aún no reejecutados.

**Mail, defectos reproducidos y corregidos:**

1. Las anotaciones públicas producían `NameError` al resolver contratos, constructores
   generados y métodos mediante `typing.get_type_hints`. La regresión reprodujo
   **52 subcasos con error** (Recipients, Address, MailStatus, Mapping, Content,
   Envelope, Delivery, etc.). Se habilitaron los imports runtime necesarios sin
   sustituirlos por casts ni namespaces inyectados. El alias de destinatarios se
   define junto a Address y se reexporta desde `orionis.mail.types`, conservando ese
   acceso público; `contracts` utiliza el resolver lazy existente para evitar ciclos.
2. Los hosts/URLs SMTP admitían DEL y caracteres no imprimibles, incluidos controles
   C1, formato invisible y sustitutos Unicode aislados. **Ocho subcasos fallaron**
   antes de la corrección. La validación rechaza esas entradas antes del transporte,
   con `MailConfigurationException` sin incluir credenciales.
3. Se añadieron tres métodos pertinentes en los archivos existentes:
   anotaciones públicas, ocho órdenes de imports fríos, y endpoints no imprimibles.
   No se eliminaron pruebas ni se añadieron skips. Se conservan SMTP doblado en la
   frontera, MIME real, Bcc, adjuntos, cancelación, file real y arranques HTTP/CLI.
4. Se actualizó el manual de transportes EN/ES. Se aplicó el formatter del proyecto
   al paquete y sus tests (61 archivos reformateados, 9 ya conformes) y se resolvieron
   las seis comas COM812 detectadas después. Las excepciones runtime justificadas y
   las dispensas inline auditadas se concentran en cabecera, sin modificar Ruff global.

**Evidencia rojo/verde de Mail:** `files\mail-regressions-red-b3e929f9.json`
registró 195 resultados aprobados, 52 subcasos con error y ocho fallidos; sus 255
registros **no son 255 métodos de prueba**. La focalizada posterior
`files\mail-regressions-green-7b6e2849.json` pasó 5+11 métodos, incluidos los imports
fríos, sin violaciones.

**Integración posterior comprobada, en una misma invocación aislada:**

| Selector | Resultado nuevo |
|---|---|
| `tests\mail` | **198/198 PASSED**, 0 omitidas, 0 violaciones |
| `tests\view` | **190/190 PASSED**, 0 omitidas, 0 violaciones |
| `tests\orm` | **505/505 PASSED**, 0 omitidas, 0 violaciones |
| Ruff Mail | Exit 0, sin diagnósticos |
| Formato Mail | Exit 0, 70 archivos conformes |

Evidencia durable: `files\mail-view-orm-integrated-b95e1d5d.json` y logs `-0`, `-1`
y `-2`. **La validación integrada de las 505 pruebas ORM ya no está pendiente**;
sus hallazgos Sonar y el cierre global no quedan aprobados por ello.

```powershell
& $python -X utf8 -B "$checks\validate_view.py" `
    'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework'
& $python -X utf8 -B "$checks\native_suite.py" `
    'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework' `
    'tests\mail' 'tests\view' 'tests\orm' --label 'mail-view-orm-integrated'
& '.venv\Scripts\ruff.exe' check orionis\mail tests\mail --output-format=concise
& '.venv\Scripts\ruff.exe' format --check orionis\mail tests\mail
```

**Calidad que no debe confundirse con aprobación total:** la auditoría sin `noqa`
ni `per-file-ignores` devolvió 411 diagnósticos en View y 595 en Mail.
Mail incluye 56 en fuentes (anotaciones runtime, contrato de argumentos, imports
diferidos, reexports explícitos y captura del fallo secundario) y 539 en tests,
principalmente PT009/PT027 por el runner nativo. El JSON completo es
`files\mail-unsuppressed.json`; no se rebajó el perfil para ocultarlos.
Los tres `NOSONAR` preexistentes de Address/PendingMail y Sonar completo siguen
requiriendo cierre explícito. Problems vacío después de solicitar análisis de
archivos concretos no acredita el perfil, los hashes y la cobertura completa.

**Documentación global al guardar este punto histórico:** se lanzó el
`DOCS.ps1` real, con `UV_NO_SYNC=1` para preservar dependencias y codificación UTF-8;
log `files\docs-resumed.log`, proceso de herramienta `67`. Su fallo y las
reejecuciones posteriores están registrados en la sección 0.3; no tomar este
primer lanzamiento como aprobación. No se modificaron el script, sus validadores
ni los perfiles.

**Pendiente:** terminar el cierre de calidad/documentación de Mail y View, seguir
con Queues (incluida la intermitencia histórica), Realtime, MCP, HTTP, Console y
Foundation, y cerrar la validación global permitida. La revisión de Mail todavía
no se presenta como aceptación global por tener su suite verde.

### 0.3 Punto anterior de continuación de Copilot

Este bloque prevalece sobre los pendientes históricos anteriores. **La revisión
integral todavía no ha terminado.** No iniciar otra auditoría desde HEAD ni borrar
los cambios previos: el índice original se conserva y los nuevos cambios siguen
sin staging ni commits.

#### Queues: revisión parcial y tres regresiones corregidas

El baseline actual de almacenamiento pasó 19/19 pruebas del driver Database y
9/9 del repositorio de fallos, sin omisiones ni violaciones. Esto **no demuestra**
que la intermitencia histórica de SQLite/pool/WinError32 haya quedado explicada
o resuelta: no se cambiaron timeouts ni asyncio debug.

Se reprodujeron y corrigieron:

1. `_DatabaseStorage._ensureSchema()` sustituía el fallo de creación por el fallo
   de la consulta de recuperación. Afectaba tanto jobs como failed jobs.
2. `DatabaseFailedJobRepository.record()` sustituía el fallo de inserción por el
   fallo del lookup de duplicado. Ahora ambos caminos conservan el error primario
   y su causa, observan el secundario mediante `failure.runtime.capture` y no
   inventan estado confirmado. Se siguió el patrón de recuperación existente de
   Seeders, sin cambiar sus correcciones.
3. `JobSerializer` rechazaba jobs válidos con `from __future__ import annotations`;
   trataba las anotaciones string y `ClassVar` como estado no admitido.
   `inspect.get_annotations(..., eval_str=True)` evalúa las declaraciones de las
   clases **ya confiadas/registradas**, no nombres procedentes del payload.
   Se conservan herencia, tipos estrictos, copia de datos, límites y registro
   cerrado de identidades. La regresión incluye rechazo de un campo restaurado
   con tipo incorrecto.

Las dos regresiones de almacenamiento están en
`tests\queues\failed\test_repository.py`; la de anotaciones está en
`tests\queues\test_serializer.py`. Se actualizaron los cuatro manuales EN/ES de
drivers y dispatch. No se eliminó ninguna prueba ni se añadieron skips.

Evidencia: `queues-storage-baseline-c9f53788.json`,
`queues-recovery-red-eddf5cdb.json` (9 aprobadas, tres subcasos fallidos),
`queues-recovery-integrated-f3d7bf78.json` y
`queues-postponed-integrated-18ffe005.json`, dentro de `files` de esta sesión.
La regresión aislada de anotaciones falló con
`QueueConfigurationError: Job field annotations must describe primitive persistent data.`
antes de corregirse.

**Cobertura de lectura de Queues, para no duplicar ni inventar revisión:** leídos
completamente `_database.py`, `drivers\database.py`, `failed\repository.py`,
`worker.py`, `context.py`, `serializer.py`, `job.py`, `functions.py` y `pending.py`.
`manager.py` se leyó hasta su selección inicial de worker; continuar desde ese
método y revisar el resto de fuentes/contratos/entidades, Redis/sync, providers,
tests y manuales. Pasar su suite no equivale a haber revisado los 30 archivos.

#### Guard actual y revalidación integrada

Se detectó y corrigió un defecto del auxiliar reconstruido: sustituía el
`PYTHONPATH` propio solicitado por un hijo. Un fixture reprodujo
`ModuleNotFoundError: owned_probe`. Ahora conserva el orden de las rutas propias,
antepone el guard y rechaza rutas ajenas en vez de reemplazarlas silenciosamente.
La autocomprobación actual verifica **nueve rechazos esperados**, un hijo protegido
y otro que importa desde su directorio adicional propio. Se reejecutaron todos
los siguientes alcances después de ese ajuste, no solo el fixture del guard:

| Selector | PASSED | SKIPPED | Segundos |
|---|---:|---:|---:|
| `tests\test` | 192 | 0 | 36.897 |
| `tests\view` | 190 | 0 | 17.425 |
| `tests\mail` | 198 | 0 | 54.893 |
| `tests\orm` | 505 | 0 | 166.543 |
| `tests\http\test_factory.py` | 25 | 0 | 21.073 |
| `tests\docs` | 14 | 0 | 6.703 |
| `tests\test_backend_lazy_imports.py` | 9 | 0 | 11.078 |
| `tests\queues` | 149 | 14 | 134.829 |
| **Total de estos alcances** | **1282** | **14** | |

Código global 0 y **cero violaciones registradas por el guard**. Las 14 omisiones
son las pruebas Redis reales preexistentes, que exigen
`ORIONIS_QUEUE_REDIS_HOST`; no se configuró ni utilizó un servidor ajeno.
No se certifica Redis real, toda la suite permitida, otra plataforma ni otro Python.

Resultado completo: `files\resumed-final-scope-9da32472.json`; logs `-0.log`
a `-7.log`. La ejecución usa Python 3.14.6. Reproducción:

```powershell
& $python -X utf8 -B "$checks\verify_guard.py"
& $python -X utf8 -B "$checks\native_suite.py" `
    'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework' `
    'tests\test' 'tests\view' 'tests\mail' 'tests\orm' `
    'tests\http\test_factory.py' 'tests\docs' `
    'tests\test_backend_lazy_imports.py' 'tests\queues' `
    --label 'resumed-final-scope'
```

Los auxiliares son barreras de validación, no un sandbox del sistema operativo.
La cifra de violaciones corresponde a esas ejecuciones protegidas, no a todas las
herramientas de inspección. Una búsqueda recursiva auxiliar de un log se detuvo
(`shellId 43`); no se acredita su poda previa. No se leyó, importó ni ejecutó
contenido de la carpeta excluida como parte de las validaciones.

#### Ruff, formato y documentación

- Ruff pasa sobre todos los Python cambiados en esta reanudación.
  La comprobación de formato informó **96 archivos conformes**.
  Los cuatro manuales modificados de Queues pasan
  `ruff format --preview --check`; ese flag es necesario para los Markdown
  explícitos con el Ruff instalado. No se activó preview para el lint de Python,
  no se cambió `ruff.toml` y no se desactivó COM812.
  Evidencia: `files\resumed-final-quality.log`.
- Se ejecutó realmente `DOCS.ps1` completo. Su primer intento encontró campos sin
  descripción y referencias NumPy no resolubles en correcciones anteriores.
  Se repararon **solo docstrings en 21 archivos** de Auth, Database, Environment,
  ORM, Schemas, Support y View: destinos públicos canónicos para Collection,
  ModelQueryBuilder y Cipher; literales para tipos externos, variables genéricas
  y elipsis; y documentación de los dos atributos de conexión heredada de Relation.
  No se cambió la lógica previa ni el script/validador.
- La siguiente ejecución pasó con **2249 páginas HTML, 12966 objetos API,
  11656 tablas NumPy y `errors=[]`**, antes del último lote de Queues
  (`files\docs-resumed-fixed.log`). Se comprobaron páginas y anchors de URL,
  SMTP y conexiones heredadas. El alias `Recipients` tiene su anchor real en
  `orionis.mail.entities.address.module.html#Recipients`; no confundirlo con
  `_appendRecipients` ni exigir que una reexportación tenga otra definición.
- Un intento posterior recibió por error el argumento literal `REAL` como
  SiteUrl. Pydoctor y el validador pasaron (11658 tablas), pero el script rechazó
  correctamente esa URL y preservó la salida anterior. **No cuenta como build
  completo aprobado.** Log: `files\docs-resumed-final.log`.
- La repetición con el parámetro válido explícito **terminó con código 0** sobre
  las fuentes actuales: **2249 páginas HTML, 12966 objetos API, 11658 tablas NumPy,
  `errors=[]` y `API documentation generated successfully.`** Pasaron Pydoctor
  con warnings-as-errors, el validador real y las comprobaciones/publicación local
  del script. Log definitivo: `files\docs-current-verified.log`.
  El proceso `docs-current-verified` terminó; no queda un build activo que esperar.

```powershell
$env:UV_NO_SYNC = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
.\DOCS.ps1 -SiteUrl 'https://api.orionis-framework.com/'
$docsExit = $LASTEXITCODE
if ($docsExit -ne 0) { throw "Falló DOCS.ps1: $docsExit" }
```

#### Conservación final y archivos pendientes en Git

Se volvió a verificar HEAD y el inventario de blobs/modos del índice: **ambos
coinciden exactamente con el baseline**. De las 3388 rutas anteriores, 1124 conservan
su SHA, 2243 corresponden a salida documental regenerada y 21 a los arreglos
exclusivamente documentales enumerados antes. **No apareció ningún cambio inesperado
en contenido previo ni en staging.**

Hay **3473 rutas pendientes**:

| XY | Cantidad |
|---|---:|
| ` M` | 1138 |
| `MM` | 2240 |
| `MD` | 2 |
| `AM` | 1 |
| `M ` | 8 |
| `A ` | 1 |
| `??` | 83 |

Las 85 rutas adicionales frente al inventario original son: 31 bajo `orionis\mail`,
32 bajo `tests\mail`, siete bajo `orionis\queues` (tres Python y cuatro manuales),
dos tests de Queues, este informe y doce páginas generadas nuevas.
La regeneración también retiró dos páginas antiguas:
`docs\orionis.orm.schema.TableDefinition.html` y
`docs\orionis.support.types.sentinel._MISSING_TYPE.html`.
Sus páginas actuales son
`docs\orionis.orm.schema.table.TableDefinition.html` y
`docs\orionis.support.types.sentinel._MissingType.html`.
No se eliminaron fuentes ni pruebas. La salida se produjo mediante `DOCS.ps1`,
no mediante edición manual de HTML.

El inventario actual completo con estados y SHA está en
`files\resumed-integrity.json`, generado por `validation\verify_integrity.py`.
Ese script compara únicamente las rutas cambiadas de `git status`, no todas las
rutas limpias del índice; sustituye un primer resumen auxiliar sobreinclusivo.
No quedan snapshots `validation-work-*` ni directorios `.docs-build-*` de trabajo.
Los auxiliares y evidencias se conservan en la sesión, fuera del repositorio,
para que la validación sea reproducible. No se borraron temporales ajenos.

```powershell
& $python -X utf8 -B "$checks\verify_integrity.py"
```

El índice contiene todavía la versión anterior de gran parte de la documentación:
no hacer un commit solo de lo preparado suponiendo que incorpora esta reanudación.
No se hizo commit, push ni publicación externa.

#### Lo que queda y el orden exacto para continuar

1. Terminar Queues desde la frontera de lectura anterior, incluida la revisión de
   contratos/anotaciones runtime, Redis/sync, concurrencia y limpieza; no atribuir
   una causa definitiva a la intermitencia histórica por estos verdes.
2. Realtime, MCP, HTTP integral, Console y Foundation siguen sin revisión integral.
   Conservar las hipótesis y prioridades de las secciones 7.5 y 9.
3. Mail tiene sus 28 fuentes, 32 archivos de tests y diez manuales leídos, correcciones
   verificadas y documentación actualizada. View tiene revalidación funcional,
   imports y mediciones nuevas. Faltan cierre Sonar completo y verificadores
   documentales de ejemplos literales, no rehacer las correcciones ya verdes.
4. Sonar IDE se invocó sobre los deltas, pero sus respuestas de solicitud y un
   Problems vacío no prueban perfil, procesamiento, cobertura ni hashes. Restaurar
   una vía con manifiesto real. Los hallazgos heredados de la sección 7 siguen
   abiertos hasta reanalizarlos; los tres NOSONAR preexistentes de Mail no se
   presentan como autorización nueva ni como Sonar limpio.
5. Migración global de `per-file-ignores`, convenciones/supresiones pendientes y
   suite global permitida siguen sin cerrar. No extender este resultado parcial
   a tests no ejecutados, servicios remotos ni `tests\real_database`.

El apéndice 12 sigue siendo el inventario histórico original, no las huellas
actuales después de esta continuación. Conservarlo como línea base; los cambios
posteriores están descritos arriba y en la evidencia de esta sesión.

### 0.4 Segunda continuación: Queues, Realtime y MCP

Este bloque sustituye los pendientes de 0.3, sin borrar su evidencia histórica.
El usuario reiteró **«Continua con lo pendiente»**. También eligió expresamente
**`normalize`** para la salida MCP: transmitir el valor validado y normalizar su
texto JSON generado automáticamente, pero conservar el texto escrito por la
aplicación. Esa autorización no cambia otros contratos de respuesta.

Al comenzar esta continuación se contrastaron **3473/3473 entradas** del punto
anterior, sin discrepancias. Su copia inmutable está en
`files\continuation-2-baseline.json`; no sobrescribirla con el resultado nuevo.
Todos los nombres de evidencia siguientes son relativos al directorio `files`
de la sesión indicado en 0.1. **No se ha terminado la revisión integral.**

#### Queues: cierre de recursos, anotaciones y límites

- Se reprodujeron 40 subcasos `NameError` en anotaciones runtime y cuatro
  `OverflowError` con enteros desmesurados. Los contratos y servicios conservan
  sus tipos concretos; la validación numérica comparte `_is_finite_number` y
  conserva los errores propios de Queues y las fechas finitas ya pasadas.
- `QueueManager.close()` ya no abandona los recursos posteriores cuando falla
  uno. Espera inicializaciones admitidas, conserva el error primario, observa
  los secundarios y drena limpieza ante cancelaciones repetidas. La reentrada
  desde el mismo inicializador se rechaza explícitamente, evitando autoespera.
  No se introdujo un estado cerrado irreversible: detener nuevas resoluciones
  antes del shutdown sigue siendo responsabilidad del propietario.
- Permanecen las tres correcciones de recuperación/serialización de 0.3.
  Se añadieron seis métodos de regresión; el conjunto actual pasa **155** y
  mantiene **14 omisiones Redis preexistentes**. No se usó Redis real.

Evidencia principal: `queues-lifecycle-types-red-172d257a-*.log`,
`queues-close-reentry-red-97e9699e-0.log` y
`queues-complete-realtime-baseline-0e0e743f-0.log`.

La primera validación final de este lote encontró un timeout diferente:
`testSignalsStopWorkerAndRestorePreviousHandlers` excedió sus 15 segundos
(`continuation-2-final-scope-d3c46df2.json`: 154 aprobadas, un error, 14 omisiones).
El probe protegido observó 5.668 segundos importando el módulo entero de tests,
frente a entrega/restauración de señales prácticamente inmediata. Se hizo
autocontenido el doble del subproceso, preservando las señales, asserts, manejo
del proceso y límites originales de 5/15 segundos. El segundo probe midió
0.045 segundos para el import necesario y terminó correctamente. Esto corrige
una dependencia ajena dentro del presupuesto de la prueba; **no demuestra la
causa exacta del timeout original ni explica la intermitencia histórica de
SQLite/pool/WinError32**. Ambas evidencias se conservan:
`queue-signal-probe-6b188f7c.json` y `queue-signal-probe-016dc38a.json`.
Auxiliar reproducible: `validation\queue_signal_probe.py`.

#### Realtime: coerción, contratos y admisión

- La compilación prepara solo anotaciones que necesitan coerción o expansión
  de Struct. Se aplican `Coerce`, restricciones nativas y reglas propias a
  anulables, colecciones y envoltorios, sin coerción implícita de escalares ni
  mutación del input. Las instancias Struct se revalidan.
- Los tipos públicos resuelven sin namespaces artificiales; referencias
  calificadas por módulo evitan ciclos entre Hub, clientes y protocolos.
  Pasaron ocho órdenes de imports en procesos nuevos.
- La configuración solo usa defaults cuando es `None`; valores falsy inválidos
  fallan antes de registrar servicios.
- Una tarea rechazada cierra su coroutine y libera el lock de escritura, o no
  publica una invocación inexistente.
- El baseline integral tenía 87 aprobadas y dos errores porque la limpieza
  Windows intentaba `taskkill`, rechazado por el guard. El test ahora retiene
  identidades `psutil.Process` propias y limpia solo esos procesos. Se ejecutaron
  realmente los transportes Granian ASGI y RSGI, ambos verdes. Los procesos y
  el snapshot de aquel fallo se limpiaron; no reutilizar sus PID históricos.

Suite actual: **96/96**, sin omisiones ni violaciones. Evidencia:
`realtime-process-cleanup-green-46729511-0.log`,
`realtime-validation-admission-red-c7ad6b7e-*.log` y
`realtime-complete-6fd1370d-0.log`.

#### MCP y el helper compartido de Schemas

- Baseline: **178/178**. Dos regresiones iniciales produjeron cinco subcasos
  con error de coerción y cinco fallos por reglas omitidas.
- El recorrido genérico `_SchemaPlan`/`_schema_plans`/`_validate_schemas` se
  trasladó de Realtime a `orionis\schemas\rules_executor.py`. No se copiaron
  sus dos supresiones `NOSONAR`; se simplificó el flujo conservando el orden
  de validación local y anidada. MCP no depende de Realtime para validar.
- Cada primitiva compilada conserva su plan de preparación/reglas. No se añadió
  una caché global sin límite ni inspección de metadatos por cada petición.
  El camino directo de `Schema` conserva su validador y errores detallados.
- Ambas rutas de respuesta ahora utilizan el valor convertido. El texto generado
  se identifica por identidad del bloque inmutable, no por igualdad de strings.
  Sus anotaciones/metadata y la procedencia sobreviven a los builders y a
  `dataclasses.replace`; texto sustituido o de un `CallToolResult` directo
  permanece manual. No se mutan las respuestas originales ni se valida dos veces.
  Se verificó el JSON que sale realmente del dispatcher, no solo el convertidor.
- El provider rechaza seis valores falsy inválidos antes de registrar servicios.
  La admisión de tareas de limpieza/STDIO cierra coroutines rechazadas y conserva
  el error original y la posibilidad de reintentar el cierre.
- La reflexión de declaraciones públicas reprodujo **73 subcasos NameError**.
  Los imports necesarios son runtime; la referencia HTTP del contexto conserva
  evaluación diferida para no cargar el parser en usos STDIO. Los ocho órdenes
  fríos comprueban identidades reales, aliases y esa frontera de imports.
- Se actualizaron seis manuales EN/ES: herramientas, respuestas y transportes.
  Ruff conserva su perfil; excepciones runtime justificadas están en cabecera.
  No se añadió ningún skip/xfail ni `NOSONAR`.

Evidencia rojo/verde:
`mcp-composite-validation-red-396bf2a4-0.log`,
`mcp-conversion-output-red-0fdeff9f-*.log`,
`mcp-normalization-shared-green-1393b75a-*.log`,
`mcp-ownership-config-red-75cd9b5e-*.log`,
`mcp-runtime-annotations-red-b91e46c9.json` y
`mcp-runtime-and-wire-integrated-796284fe-0.log`.
El conjunto actual tiene **187/187** métodos aprobados.

#### Validación integrada actual

Después de corregir el fixture de señales se repitió todo el alcance, no solo
la prueba que había fallado:

| Selector | PASSED | SKIPPED |
|---|---:|---:|
| `tests\queues` | 155 | 14 |
| `tests\realtime` | 96 | 0 |
| `tests\mcp` | 187 | 0 |
| `tests\schemas` | 586 | 0 |
| `tests\test_backend_lazy_imports.py` | 9 | 0 |
| `tests\docs` | 14 | 0 |
| **Total del alcance** | **1047** | **14** |

Código global **0**, sin fallos ni violaciones. Evidencia:
`continuation-2-final-verified-80089029.json`, logs `-0.log` a `-5.log`.
El guard conserva sus nueve rechazos esperados. Intérprete: CPython 3.14.6;
Ruff real: 0.17.3. Un resumen auxiliar indicó erróneamente 0.15.16: el log y
la consulta directa al ejecutable confirmaron 0.17.3; no se cambiaron dependencias.

Ruff pasó para las fuentes/tests de Queues, Realtime, MCP y Schemas. El formatter
confirmó **122 Python** del alcance y los **seis manuales MCP** con `--preview`.
El check completo y el formato del fixture se repitieron después del último ajuste
de señales, ambos con código 0. No se desactivó COM812 ni se cambió el perfil.
Se solicitaron análisis Sonar IDE de los siete deltas principales (rule executor,
metadata Realtime, schemas/normalización/respuestas/streams y STDIO MCP).
Problems no mostró diagnósticos en esos archivos; la herramienta solo confirmó
las solicitudes, por lo que esto **no certifica** perfil ni cobertura Sonar global.

Se ejecutó `DOCS.ps1` completo con el SiteUrl válido y `UV_NO_SYNC=1`.
`docs-continuation-2.log` registra **2249 páginas HTML, 12979 objetos API,
11673 tablas NumPy, `errors=[]` y generación exitosa**. El script devolvió 0;
el comando envolvente terminó con 1 por un punto espurio añadido después de
`exit $docsExit`. No se ocultó ese error de ejecución: se ejecutó después,
independientemente, el validador real contra la salida local definitiva:

```powershell
& $python -X utf8 -B -m resources.docs.pydoctor.validate `
    'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework\docs'
```

Esa comprobación terminó con **código 0** y exactamente los mismos contadores,
sin errores. Se verificaron también los anchors reales `structured`,
`_copyContent` y `_structured_text` de McpResponse, y `_schema_plans`/
`_validate_schemas` con el enlace al nuevo `_SchemaPlan` en Schemas.
No se editaron HTML ni validadores manualmente. El build ya terminó; no hay
un proceso documental pendiente que esperar.

Reproducción funcional:

```powershell
& $python -X utf8 -B "$checks\verify_guard.py"
& $python -X utf8 -B "$checks\native_suite.py" `
    'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework' `
    'tests\queues' 'tests\realtime' 'tests\mcp' 'tests\schemas' `
    'tests\test_backend_lazy_imports.py' 'tests\docs' `
    --continue-on-error --label 'continuation-2-final-verified'
```

#### Frontera de lectura y pendientes reales

No confundir estos verdes con haber revisado íntegramente los 43 módulos de MCP.
Se han revisado contexto, servicios/contratos, provider, invocación, estado,
ownership de streams, event bus, declaraciones/catálogos/extensiones y los
transportes HTTP/STDIO/standard_io. Del compilador, dispatcher, normalización,
builders y validación se siguieron las rutas modificadas y sus dependencias;
queda la lectura integral de sus otras operaciones, protocolo/MRTR, headers,
política HTTP, matching URI, tests y manuales restantes. Retomar ahí, no rehacer
las regresiones ya verdes.

Después siguen HTTP integral (405/Allow, limpieza y `sys.exception()`, transportes),
Console (incluida discovery vacía) y Foundation (límites/Argon2 y lifecycle).
Sonar completo con perfil/procesamiento/hashes, auditoría de supresiones,
ejemplos literales y suite global permitida siguen pendientes. No se certifican
Redis, otros sistemas operativos o versiones de Python.

La verificación de conservación de esta continuación usa
`validation\verify_integrity.py --continuation-two`, compara el baseline de
3473 entradas y escribe `files\continuation-2-integrity.json` sin sobrescribir
los anteriores. Solo admite cambios en Queues/Realtime/MCP, el helper compartido
de Schemas, este informe y salida documental generada.

La comprobación posterior al build pasó: **HEAD y el inventario de blobs/modos del
índice siguen idénticos**, sin cambios inesperados. Hay **3576 rutas pendientes**,
103 adicionales respecto del checkpoint de 0.3. De las 3473 anteriores, 1212
conservan su SHA y 2261 cambiaron: 2253 de salida documental y ocho del informe/
fuentes permitidas. Los estados son 1240 ` M`, 2239 `MM`, tres `MD`, un `AM`,
ocho `M `, un `A ` y 84 `??`. La página privada de `_SchemaPlan` se trasladó
de Realtime a Schemas mediante la regeneración. No se eliminaron fuentes/tests.
No quedaron snapshots `validation-work-*` ni directorios `.docs-build-*`.
El chequeo de procesos con cwd perteneciente a esos snapshots tampoco encontró
procesos propios vivos (`continuation-2-cleanup.json`). Los dos logs auxiliares
que el ejecutor había dejado en Temp se trasladaron por nombre exacto a `files`;
no se borraron temporales ajenos. El manifiesto se regenera tras esta última
actualización del informe; repetir el verificador después de cualquier nueva
edición. No se hicieron staging, commits ni push.

### 0.5 Tercera continuación activa: completar el plan, sin afirmar un 100% parcial

El usuario ordenó continuar hasta completar el plan. Al iniciar se comprobaron
**3576/3576 rutas**, HEAD e índice contra `continuation-2-integrity.json`, sin
discrepancias; se preservó una copia en `files\continuation-3-baseline.json`.
No se reinició la auditoría ni se revirtieron correcciones anteriores.
**Este bloque registra trabajo en curso, no un cierre global.**

**Decisión adicional del usuario:** ante el contrato existente que devolvía 0
con cero pruebas, eligió **`fail`**: `reactor test` debe devolver un error y
explicar que no se ejecutaron pruebas. Esa autorización permite cambiar el
test que protegía el éxito vacío; no autoriza a tratar skips como aprobaciones.

**Decisión posterior S100:** al recibir los diagnósticos reales que exigían
snake_case para métodos, el usuario eligió **`camelCase`**. Autorizó también
`^[_a-z][_a-zA-Z0-9]*$` en S100, manteniendo la regla activa y verificando
separadamente que funciones de módulo/anidadas sigan en snake_case.
El ajuste está en `.vscode/settings.json`, ignorado por Git; no se añade al
índice. No autoriza ninguna otra dispensa Sonar.

**Decisión posterior de jitter:** tras reproducir que el default no modificaba
el firing time, el usuario eligió **`preserve`**: aplicarlo solo a los horarios
que ya admiten jitter; conservar exactos los restantes. No extenderlo a todos
los horarios recurrentes.

#### MCP: lectura pendiente completada y nuevas correcciones

Se completó la lectura de las operaciones restantes del dispatcher, compilador,
protocolo/MRTR, metadata, URI, headers y política HTTP; se contrastaron tests
y los 14 manuales. El índice AST fuera del repositorio
`review-mcp-{orionis,tests}.txt` conserva código completo sin las expresiones
documentales y con números de línea originales; su JSON guarda hashes.
No se ejecutaron los módulos para construir ese índice.

Nuevas regresiones y correcciones:

- Suscripciones a recursos: disponibilidad y autorización se vuelven a comprobar
  antes de cada actualización; eventos denegados no cierran los otros filtros.
  La regresión corrigió primero su registro de DI para operar sobre el scope real,
  comprobó identidad de la política, volvió a reproducir el rojo sin el arreglo
  y pasó después. No se ocultó aquel defecto inicial del fixture.
- Los presupuestos de streaming/catálogos no serializan la referencia privada
  al texto generado como si fuera payload adicional. Se verificaron los límites
  exactos del resultado transmitido y su rechazo con un byte menos.
- Metadata estática y resultados directos rechazan NaN/infinito, en lugar de que
  el encoder los convierta silenciosamente a null.
- El writer STDIO completa escrituras parciales antes de confirmar/flush.
  Un retorno de cero bytes o None produce error, no éxito ni bucle ocupado.
  El rojo mostró `b'{"v'` en lugar del frame completo y ausencia del OSError.
- Se auditó Ruff sin `noqa` (119 diagnósticos iniciales); las dispensas inline
  comprobadas de MCP se concentraron en cabecera, conservando tipos runtime,
  campos del protocolo y observación/sanitización en fronteras. No se añadieron
  NOSONAR, skips ni rebajas de perfil. La migración global de per-file-ignores
  y Sonar completo permanecen separadas.

Evidencia principal:
`continuation-3-mcp-boundaries-red-662bef4c-*.log`,
`continuation-3-mcp-policy-red-e3a983de-0.log`,
`continuation-3-mcp-short-write-red-800da4e0-0.log` y
`continuation-3-mcp-complete-30fe50e5-0.log`.
MCP pasó **194/194**, Ruff configurado y formato.
`mcp-manuals-ae5bfdd0.json` acredita **10 documentos con Python, 16 bloques
literales ejecutados**, incluidos registro real, compilación y test client,
en snapshots protegidos sin servicios externos. Los cuatro README no tienen
bloques Python. El lint `--preview` que ejecutó por error un auxiliar no es
el perfil de aceptación; el check configurado se repitió correctamente.

#### HTTP: baseline observado y arreglos comprobados hasta ahora

Baseline: **955 PASSED, 11 ERRORED, 4 SKIPPED**,
`continuation-3-http-baseline-c4f96f98-0.log`, sin violaciones.
Los 11 errores iniciales eran del fixture que llamaba
`_RecordingAuthorizer(True)` después de hacerse keyword-only.
Al corregir esa llamada aparecieron tres escenarios que usaban IDs de propietario
enteros en un token doble, aunque el repositorio real persiste la clave textual
canónica. Se corrigió el fixture y sus expectativas de lookup, no la protección
de `TokenGuard`; las 12 pruebas HTTP/Auth pasaron.

Correcciones con rojo/verde:

1. El kernel ya no consulta `sys.exception()` para inferir un fallo propio:
   retiene explícitamente el error que escapa de la petición/WebSocket. Una
   excepción que su llamador esté manejando no oculta errores locales de cierre.
2. OPTIONS/405 comprueban convertidores, no solo el regex. Un entero rechazado
   por el límite de conversión no anuncia una ruta disponible.
3. Las respuestas 405 del presenter normal incluyen el Allow real del resolver,
   sin reemplazar el presenter ni su contenido.
4. HEAD cierra también streams asíncronos ordinarios sin consumirlos.
5. Un `http.disconnect` antes del último frame impide publicar/cachar un cuerpo
   parcial y se propaga como ConnectionError.
6. La admisión SSE revierte un fallo de creación del emisor/monitor: cierra las
   coroutines no programadas y cancela/espera el emisor ya admitido.
7. Las cabeceras salientes validan tokens/controles, también tras mutación de
   listas o copias con headers cacheados. El helper comparte validación con
   los headers de aceptación WebSocket; tab y Latin-1 siguen admitidos.
8. CORS exige fullmatch del regex de origen y su wildcard incluye QUERY.
9. Los fallos Redis del limitador se observan centralmente antes de conservar
   la respuesta 503; no hay fallback a memoria ni Redis real en esa regresión.

Evidencia: `continuation-3-http-cleanup-routing-red-cbdae609-*.log`,
`continuation-3-http-allow-red-*`, `continuation-3-http-stream-ownership-red-*`,
`continuation-3-http-header-red-7f9cd9cf-0.log`,
`continuation-3-http-headers-cors-f5f284b5-*.log` y
`continuation-3-http-middleware-observation-*`.
La integrada posterior `continuation-3-http-integrated-ccaaf813.json` terminó
con código 0:

| Selector | PASSED | SKIPPED |
|---|---:|---:|
| `tests\http` | 975 | 4 |
| `tests\mcp` | 194 | 0 |
| `tests\realtime` | 96 | 0 |

Sin violaciones. Las cuatro omisiones HTTP son Redis reales preexistentes.
Las capturas de loop en helpers y sus anotaciones se corrigieron y revalidaron:
11 transport + 12 SSE lifecycle + 5 conventions. El Ruff del bloque pasó luego
de resolver sus comas mecánicas; no se confundió ese check con la suite funcional.

Correcciones posteriores a esa integrada:

- `_SyncStreamIterator` conserva el iterable síncrono antes de empezar a
  consumirlo y lo cierra una sola vez. Protege HEAD y fallos de inicio de
  respuesta en ASGI/RSGI. Cuatro subcasos reprodujeron el defecto; el arreglo
  pasó 134 pruebas focales. `_wrapSyncIterable` sigue entregando un iterable
  asíncrono, no una coroutine que se deba esperar.
- Registro de cuentas usa `async with DB.transaction()` nativo, rechaza
  `save() == False`, observa errores y muestra un mensaje genérico, sin
  exponer el backend al formulario. La regresión usa SQLite `:memory:`
  y verifica rollback ante fallo, cancelación y veto de persistencia.
- Verificación de email no presenta éxito cuando el modelo veta el guardado.
  Los dos tests nuevos de `tests\http\default\test_registration.py` y las
  cinco convenciones pasaron en `continuation-3-registration-final-*`.
  La última partición mecánica de un string largo aún necesita el check
  de formato/lint definitivo. No se rediseñó el token ni su caducidad.

La suite HTTP completa todavía debe repetirse con estos últimos cambios.
La salida API de 0.4 está desactualizada: se regenerará al congelar fuentes.

#### Console y corrección de la barrera de validación

El primer Console completo produjo 1489 PASSED, 2 FAILED y 2 SKIPPED.
No se acepta como resultado final: también registró dos violaciones del guard.
Una aserción esperaba ver un path largo completo en una consola Rich de 120
columnas que lo elidía deliberadamente; el fixture ahora reserva el ancho
necesario y conserva la aserción de path completo.

El otro fallo reveló que el guard comparaba `C:\...` y `\\?\C:\...` como
ubicaciones distintas. Un self-test sobre fixtures propios reprodujo además
la aceptación errónea de una lectura protegida con el segundo formato.
Se corrigió la canonicalización de paths locales con unidad ASCII, sin
autorizar namespaces UNC/device ni ampliar las operaciones permitidas.
`verify_guard.py` comprueba ahora 12 rechazos esperados y escrituras propias
con prefijo extendido. No se leyó `.env` ni `tests\real_database` reales.
El guard es una barrera de auditoría Python, no un sandbox del sistema operativo.
La revalidación focal pasó 89 pruebas, con dos omisiones existentes y sin
violaciones. Los alcances finales deben usar este guard corregido.

Console incorpora además regresiones reproducidas para:

- Resultado vacío de `reactor test`: error explícito y exit 1, conforme a la
  decisión del usuario. No cambia la clasificación de resultados omitidos.
- Detección del launcher por basename/stem: un nombre de comando que contiene
  `reactor` no se descarta.
- Restauración de convertidores: resolver módulos/atributos anidados y
  propagar fallos de dependencias, sin fallback silencioso a `type_=None`.
- Caché de argumentos: flags booleanos `const_missing`/`default_missing`
  distinguen ausencia de un literal `"__MISSING__"`; se conservan registros
  legacy sin flags. La regresión JSON/argparse falló antes del arreglo.

`continuation-3-console-dispatch-green-*` pasó 22 kernel + 39 loader +
16 comando test = **77 pruebas**, sin violaciones. Ruff configurado y formato
pasaron sobre los siete archivos Python de este bloque. Manuales EN/ES
actualizados. La integrada `continuation-3-console-complete-97e83476-0.log`
pasó **1495 PASSED, 2 SKIPPED, 0 violaciones** (223.08 s).
Los dos skips proceden del requisito `which("uv")` de tests de instalación
offline: falta comprobar si el entorno aislado está ocultando un `uv` ya
instalado, antes de clasificarlos como limitación real. Siguen pendientes
el recorrido CLI vacío real, resto de lectura y ejemplos.

Avance posterior al primer Console completo:

- Bootstrap rechaza helpers posteriores que sustituyen rutas mediante alias
  directos, anotados, encadenados o propagados entre iteraciones. El rojo
  `continuation-3-bootstrap-alias-red-e64bc4a5` mostró tres
  `BootstrapEditError not raised`; el cierre transitivo conserva posibles
  alias sin perderlos por un rebind condicional. Pasaron 126 tests bootstrap,
  dos registro HTTP y cinco convenciones en
  `continuation-3-bootstrap-alias-green-e55dd6f4-*`.
- La CLI vacía sí se probó ahora como proceso Reactor real:
  `cli-empty-888cf870.json` registra `child_exit_code=1`, diagnóstico exacto y
  cero violaciones. El exit 0 del probe corresponde a esa comprobación
  negativa esperada. Un intento anterior apuntó a un `__init__.py` inexistente
  y no se contó como evidencia.
- Los generadores que capturan fallos de validación/escritura ya devuelven 1,
  conservando el retorno None del éxito. Reactor no imprime `done` ni registra
  éxito para un resultado no-cero: conserva el código, usa `capture_result`
  y solo emite un log alternativo si no existe runtime activo. Rojo/verde en
  `continuation-3-console-outcomes-*`: 34 make + 37 Reactor + 16 comando test
  aprobadas. Se corrigió una aserción añadida por error al caso de éxito de
  fábrica, y se repitió el rojo real de duplicado/nombre ausente
  (`continuation-3-factory-outcomes-red-2bf321f1`) antes de tocar producción.
- Scheduler cierra coroutine y supervisor cuando la admisión falla, restaura
  STOPPED tras fallo de start, y actualiza el estado antes de notificar
  listeners. Un apagado exitoso limpia tracking activo/pausado. El rojo
  `continuation-3-scheduler-lifecycle-red-624a1fe2` reprodujo tres defectos;
  la revalidación pasó 71 tasks + 10 comandos schedule + 37 Reactor.
  El ciclo nativo en memoria comprobó STARTED/PAUSED/RESUMED/SHUTDOWN.
  Arranques repetidos/concurrentes y rollback de recursos tras start parcial
  siguen siendo preguntas separadas, no certificadas por esos tests.
- Ruff con el binario explícito `.venv\Scripts\ruff.exe` pasó en los bloques
  anteriores. No se cuenta el intento de un auxiliar que añadió por error
  `--ignore TC001`. TC001 es necesario para los imports runtime del controlador
  de registro y quedó conservado, justificado y movido a cabecera.

Continúa la lectura de Console; `review_reads` en SQLite registra rangos
realmente leídos del índice, no cobertura total de tests/documentación.
El rojo `continuation-3-stub-jitter-red-bc69629d` reprodujo cuatro nombres
keyword aceptados y un firing time sin el jitter heredado. Se corrigieron:

- Stub valida identificadores/keywords del nombre final (incluidos sufijos)
  antes de publicar su estado o crear directorios. Conserva el rechazo al
  reutilizar la misma instancia; `for` con sufijo `Service` sigue siendo válido.
- Task conserva explícitamente la política de cada trigger. `entity` aplica
  el jitter heredado sobre una copia cuando hace falta, sin modificar triggers
  ya entregados. Un cero explícito prevalece. `onceAt`, `everySeconds`,
  `everyMinuteAt`, `everyMinutesAt`, `hourlyAt`, `everyHoursAt` y sus wrappers
  mantienen tiempo exacto; un retraso positivo explícito se rechaza.

La integrada `continuation-3-stub-jitter-green-277cd3dd` pasó 17 templates +
194 fluent + 71 tasks + 34 make + 10 schedule + 65 editor = **391 pruebas**,
sin violaciones. Se eliminaron después dos comentarios redundantes que
excedían E501 al indentar los constructores; falta el lint final de ese lote.
Siguen pendientes las hipótesis de ciclo de vida de salida HTTP, redirección
de VarDumper y cierres forzados de Console, además del resto de lectura/tests.

Estas tres hipótesis de salida se resolvieron posteriormente:
`continuation-3-console-output-red-9586886e` reprodujo tiempos compartidos,
workers duplicados, cierre bloqueado, redirección inefectiva y dos cierres
sin finally/flush. HTTPRequestPrinter usa temporizadores por contexto, un lock
de ciclo de vida, rollback de admisión y `Queue.shutdown()` de Python 3.14.
VarDumper restaura y libera sus streams prestados; los helpers de Console
propagan el SystemExit ya prometido por los manuales, sin forzar os._exit.
No se cambia el modo `forceExit` explícito de VarDumper.
`continuation-3-console-output-http-green-7fcceccc` pasó **320 output +
978 HTTP**, con cuatro skips Redis preexistentes y cero violaciones.
Ruff/formato configurados del lote pasaron.

También se cerró la omisión artificial de los dos tests uv. El runner ofrece
`--offline-installer`, apagado por defecto. Primero se probó el rechazo original
(`continuation-3-installer-capability-red-da648163`, dos violaciones esperadas).
La capacidad nueva admite únicamente el wheel constante conocido, un launcher
copiado/verificado, venv propio sin site global, el comando uv exacto offline
y el programa fijo de importación con `-I -B`. Valida paths sin links/junctions,
contenido del wheel y paquete instalado; exige HOME/guard heredados y flags
sin red/configuración/build/descarga de Python. No autoriza uv genérico ni
Python aislado arbitrario. El self-check pasó **16 rechazos esperados**,
incluyendo destino ajeno, requisito remoto, red habilitada y código arbitrario.
La integración real `continuation-3-installer-capability-green-64f8842f` pasó
**39/39, sin skips ni violaciones**. Solo se instaló el wheel de prueba en su
venv temporal; no se modificó el entorno del proyecto.

Se reprodujo además un defecto estrechamente ligado a los flags de caché:
un flag explícito null se confundía con un flag ausente de un registro legacy.
Rojo `continuation-3-null-cache-flags-red-b43eecdc`: dos fallos. El productor
distingue ahora ausencia con `_MISSING` y rechaza null; falta el recheck.
Se corrigió también `list[type[Any], str | None]` a una lista de la unión en
Loader y su contrato, sin modificar la firma ejecutable.

#### Sonar: procesamiento real recuperado, aceptación aún abierta

El cliente LSP de la extensión instalada se reconstruyó en los auxiliares de
sesión, con snapshot permitido, home temporal, telemetría desactivada y sin
connected mode. Inicializar o recuperar reglas no se contó como analizar.
Los probes anteriores fallaron por parámetros posicionales, DTO incorrecto
de listado de archivos y ausencia de publicaciones; permanecen como evidencia
de intentos fallidos. Los errores textuales `[Error ...]` se registran aunque
la severidad del mensaje RPC no sea 1.

`sonar-probe-ce13c365.json` finalmente contiene una publicación diagnóstica
real para `orionis\mcp\transport\stdio.py`, hash
`ece968dcbb0ea43a3519cc6ba7e2410eadd166ff8c995e04de3c71fdf4eccc7e`,
Java exit 0 y `analysis_errors=[]`. El log confirma 407 reglas Python,
403 IPython y 30 secrets activas. No es un resultado limpio: reporta
S100 en `_readLoop` y `runStandardStreams`. El usuario autorizó después
el patrón camelCase para S100; falta reanalizar con ese cambio.
El plugin Python local es **5.32.0.37250**, confirmado en su manifiesto.

El lanzamiento con JARs Python/secrets **no impidió** que el backend
descargase automáticamente plugins C#/C++ a su home propio. Por ello no
describir este probe como una ejecución sin red ni como certificación global.
Antes de generalizarlo, comprobar el control real de descargas, perfil,
versión de plugins, finalización por archivo y manifiesto de hashes.
No se cambiaron dependencias del proyecto ni se añadió connected mode.

`sonar-probe-e0da1705.json` amplió la prueba a seis fuentes con hashes,
inventario/versiones de JARs, configuración y publicaciones por URI:
`coverage_complete=true`, `missing_publications=[]`, `analysis_errors=[]`.
S100 autorizado se aplicó sin desactivar la regla. STDIO, Reactor, Schedule
y ambos handlers make quedaron sin diagnósticos; `_editor.py` reportó tres
S1110. Se reexpresó la condición/backoff sin cambiar intentos ni demoras,
y se acortó "application import root" a "application root" en un diagnóstico.
Sus 65 tests volvieron a pasar; falta el reanálisis Sonar.
El SonarText empleado es 2.54.0.13918. Es evidencia de esos seis archivos,
no del framework ni de todas las pruebas.

#### Scheduler nativo y comprobaciones posteriores

Console integrado pasó **1513/1513, cero skips y cero violaciones** en
`continuation-3-console-integrated-93e38c1e`. El checker completo pasó, pero
el formatter detectó 181 archivos pendientes; se normalizaron los 251 archivos
Python entonces existentes del paquete/tests y se corrigieron dos incidencias
de estilo resultantes, sin reducir reglas.

La lectura de APScheduler instalado confirmó que su `shutdown()` solo encola
un callback y que su executor cancela futures sin esperarlas. El rojo nativo
`continuation-3-scheduler-native-red-a396ee0f` mostró tres schedulers en lugar
de uno, `wait()` terminado antes del listener SHUTDOWN y OSError del store
perdido por el llamador.

El nuevo módulo interno `orionis\console\tasks\_backend.py`, importado de forma
diferida, adapta esa frontera de APScheduler 3: transmite resultado/excepción
del callback real al worker que espera y conserva los futures cancelados
para esperar sus finalizadores. No modifica la dependencia instalada ni cambia
la referencia serializable de jobs. Usa hooks protegidos de APScheduler 3,
por lo que una actualización de ese backend debe revalidar estos contratos.
Schedule serializa boot/close, comparte arranques concurrentes/repetidos,
libera stores/executor tras start parcial y drena listeners tardíos.

`continuation-3-scheduler-native-green-fe92c3d0` pasó 74 tasks + 10 schedule +
34 make. `continuation-3-scheduler-owned-cleanup-e1be6b44` pasó **76/76**,
añadiendo comprobaciones reales de finalizadores de jobs cancelados y
liberación de un store cuyo start falla. Ruff de Console y format --check
pasaron sobre 252 archivos. **La ejecución de ese último check produjo el
incidente siguiente; no representa cierre de la revisión.**

#### Incidente de alcance del formatter: revisión pausada

Una ejecución auxiliar lanzó estos dos comandos sin los tres paths previstos:

```powershell
& '.\.venv\Scripts\ruff.exe' format
& '.\.venv\Scripts\ruff.exe' check --select COM812 --fix
```

El registro de sesión confirma los comandos sin selectores. La salida informa
367 archivos reformateados, 1883 sin cambios y 110 COM812 corregidos.
La comparación de los manifiestos previos/posteriores ya guardados encontró
**366 paths modificados fuera de `orionis/console` y `tests/console`**.
No se abrió ni recorrió el directorio protegido para investigar el incidente.
Los dos JSON de diagnóstico que el auxiliar guardó por error en `files\`
del repositorio se trasladaron al directorio de sesión.

Evidencia en la sesión:
`formatter-incident-triage.json`, `formatter-incident-manifest-delta.json`,
`formatter-incident-settings.txt`, `formatter-incident-index-metadata.json`
y `continuation-3-console-native-final-*.log`.
La configuración efectiva tiene `respect_gitignore=true`; `.gitignore`
excluye `/tests/real_database/` y `.env`, y el índice no contiene Python
trackeado bajo la carpeta protegida. Aun así, el comando global no tuvo el
manifiesto explícito de exclusión antes del descubrimiento y **no se certifica
su alcance exacto ni la conservación de esa exclusión a partir de esos datos**.
No intentar certificarlo leyendo/hashando contenido protegido.

HEAD sigue en `036d04bac1381cc4f35c49431bb41a77d18419c3`.
La comparación inicial del índice mezcló dos medidas diferentes: el archivo
binario de índice tiene SHA
`027233cdf8e6a2f5eeb359db577fd98375e98b1f0ecef553ee06076d4cfcba54`,
pero el checkpoint mide `git ls-files --stage -z`. Repetida esa misma medida
sin leer el worktree protegido, el inventario staged **coincide**:
`1fba74434aed05646cc8c189ecf486876db591e1774e98a860bb1623cdf860ff`.
No hay diferencia staged demostrada ni cambio de HEAD.
No restaurar desde HEAD: eso podría eliminar correcciones previas del usuario.
Los manifiestos conservan hashes, no copias completas de cada versión anterior.

Se pausaron nuevas ediciones de código y se solicita decisión sobre conservar
y revalidar este formato adicional o detenerse para evaluar recuperación.
Cualquier continuación deberá ejecutar herramientas sobre snapshots permitidos
o listas explícitas no vacías; nunca repetir comandos globales en el checkout.

**Decisión recibida después:** el usuario eligió **`retain-and-validate`**:
conservar el formato adicional y continuar con validación global sobre
snapshots excluidos. Se reanuda bajo esa condición; no autoriza leer contenido
protegido ni restaurar cambios desde HEAD.

#### Primera suite global y resolución de sus fallos

La primera ejecución global permitida, `continuation-3-global-allowed-baseline-2f3a8d79`,
terminó con **9661 PASSED, 7 ERRORED, 2 FAILED y 20 SKIPPED** en 969.85 s.
Hubo además tres violaciones de bind loopback fijo; esa ejecución **no se acepta
como verde**. Las omisiones corresponden a 18 casos Redis y dos casos uvloop
no disponibles en Windows, no al instalador uv.

Se resolvieron los nueve fallos observados:

- Los tres errores de templates eran del snapshot: faltaba copiar
  `.env.example`. Se admite ese template, nunca el `.env` real; sus diez
  pruebas pasaron.
- El hook externo de APScheduler se publica mediante el alias
  `_create_default_executor = _createDefaultExecutor`, sin dispensas nuevas.
  Las cinco pruebas de convenciones pasaron.
- SessionSweep conserva el filtro de staging names de producción; el fixture
  usa ahora `FileSessionStore._tempPath(...)` en vez de `abandoned.tmp`.
  Sus 14 pruebas pasaron.
- Un proceso limpio demostró el ciclo real entre `auth.entities.guard_result`
  y los imports eager de `auth.contracts`. Este último usa ahora los exports
  lazy compartidos, conserva los doce contratos y la identidad de tipos.
  Los imports runtime de GuardResult/IGuard no se ocultaron bajo TYPE_CHECKING.
- Los tres servidores nativos del benchmark solicitan ahora `--port 0`;
  el runner resuelve el listener vivo del proceso propio o sus workers, en
  vez de reservar/cerrar un socket y volver a enlazar ese puerto. Rechaza
  listeners ambiguos y no añade precalentamiento a otros frameworks.

La barrera conserva el rechazo de binds fijos. Para conexiones entre procesos
verifica la identidad PID/creation-time del dueño y un listener TCP vivo de su
árbol; el registro local conserva referencias débiles y descarta sockets
cerrados. El self-test pasó **18 rechazos controlados**, además de conexiones
positivas al listener propio de un proceso hijo. No es un sandbox del SO.

Revalidación `continuation-3-global-followup-93afeb27`:
**14 lazy imports + 383 Auth + 12 consumidores HTTP + 14 SessionSweep +
47 comparadores HTTP = 470 PASSED**, sin skips ni violaciones.
El formatter/check explícito del lote pasó (`explicit-format-20ef311a`).
Falta repetir la suite global en el estado integrado definitivo.

#### Foundation: correcciones comprobadas y revisión restante

Application cierra la coroutine cuando falla la admisión del handler HTTP.
Si se rechaza el monitor después de admitir el handler, cancela y drena este
último, observa sus fallos de cleanup y conserva el error primario de admisión.
ASGI y RSGI comparten el helper, sin cambiar sus fast paths o task factories.
Se reprodujeron los cuatro subcasos antes de corregirlos.

La entidad Argon2 comparte con el driver los límites nativos:
costes hasta `2**32 - 1`, paralelismo hasta `2**24 - 1` y al menos 8 KiB por
lane. Las pruebas no hashean ni reservan memoria con esos valores extremos.
La revalidación `continuation-3-foundation-admission-bounds-green-84f7ffb5`
pasó **250 pruebas** de configuración, Application, Hashing, naming y templates.
Los manuales EN/ES documentan los límites.

La precedencia defaults → overrides fluent → dataclasses de aplicación,
la combinación por sección y las claves de paths desconocidas son contratos
documentados/probados: no cambiarlos por intuición. La hipótesis de que se
ignoraba un retorno False de `Env.set` no se confirmó: la implementación real devuelve
True o propaga el error. La revisión de configuraciones restantes y del
ownership de rutas sigue en curso.

#### Frontera activa, sin inventar lectura ni aceptación

**Actualización posterior de esta continuación:** la revisión ejecutable de
Foundation quedó leída hasta el final del índice (9923 líneas). Se reprodujeron
y corrigieron dos selectores silenciosos: runtime desconocido que registraba
hooks globales y paths conocidos inválidos que sustituían la configuración
por defaults. Se conservan `None`, los valores `"http"`/`"cli"` existentes y las
claves desconocidas de paths ignoradas. Los tests del rojo
`continuation-3-foundation-selectors-red-7e992503` demostraron tanto la ausencia
del error como la mutación no deseada.

`continuation-3-foundation-fixture-integrated-65824e40` pasó
**250 Foundation + 978 HTTP + 25 Queue manager + 19 startup Console +
126 bootstrap + 47 benchmark = 1445 PASSED**, con cuatro skips Redis y cero
violaciones. Los fixtures HTTP/Queues/Console usan restauración contextual;
se retiraron catorce supresiones Sonar activas de fixtures sin debilitar
aserciones. El formatter/check explícito del lote pasó (`68996daa`).

**Corrección importante de evidencia Sonar:** el probe `fa2b50b1` no certifica
su tanda global. Contaba publicaciones por URI, pero envió shutdown en la
posición 28579 antes del segundo progress/end (29863). El helper ahora exige
configuración de análisis por archivo y finalización de todos los progresos
antes de cerrar. La auditoría `29a890b1` sí terminó ambos progresos antes del
shutdown y cubrió **1956 archivos .py/.pyi permitidos**, sin errores, retirando
NOSONAR solo en el snapshot: **123 diagnósticos**, no una aceptación.

El baseline normal corregido `f7b94cd0`, con las supresiones originales y
sin rebajar el perfil, procesó ese mismo alcance y produjo **56 diagnósticos**:
34 S1110, 6 S3776, 3 S1192, 3 S5778, 2 S1845, 2 S7503, 2 S5754 y uno de
S2638/S930/S3415/S5332. Está pendiente corregir los accionables y distinguir
las limitaciones reales de contratos/análisis. No presentar el exit 0 del
cliente LSP como calidad aprobada. La configuración efectiva nueva confirma
`disableTelemetry=true`; los primeros probes solo habían solicitado la
desactivación mediante propiedades de lanzamiento. El backend sigue haciendo
descargas de componentes a su home temporal; no es una ejecución offline.

La inspección Ruff sin supresiones `quality-all-4f263189` encontró 25382
diagnósticos, principalmente aserciones TestCase/fixtures, metadatos runtime
y docstrings de stubs. Es inventario, no un fallo nuevo del perfil de aceptación.
Falta revisar y concentrar las dispensas justificadas en cabeceras, eliminar
las obsoletas y retirar `per-file-ignores` sin ocultar diagnósticos adicionales.
La salida tabular ya explicita `zip(..., strict=False)` y tres fixtures SHA-1
de protocolos usan `usedforsecurity=False`; estas últimas ediciones esperan
revalidación. No se han reducido costes criptográficos.

**Nueva autorización posterior:** ante los falsos positivos demostrados, el
usuario eligió **`scoped-exceptions`**: permite excepciones por línea y regla
con evidencia y justificación, sin desactivar reglas globales. Esto modifica
la prohibición anterior de añadir NOSONAR únicamente para dichos casos.
No permite suprimir hallazgos accionables ni añadir awaits artificiales.
Los contrajemplos nativos de Python 3.14 confirmaron `annotation_format` y
demostraron que retirar agrupaciones de negación, desplazamiento y walrus
cambia resultados o produce errores. Se conservan asimismo el URI ACL
canónico de AWS, los nombres distintos de Faker, los hooks async opcionales
y la entrega de errores por Future. Las excepciones locales emplean S1110,
S930, S1845, S5332, S7503 y S5754 con comentarios específicos.

Stringable ahora admite `split()`/`split(None, limit)` con semántica nativa
de whitespace y rechaza chunks no positivos, booleanos y límites no enteros.
Los modos regex/chunks válidos y sus retornos se conservan. El rojo
`continuation-3-stringable-split-red-ae5fc34b` registró tres fallos y tres
errores nuevos. `continuation-3-split-protocol-green-9ea647e1` pasó
**611 Support types + 320 Console output + 25 bootstrap + 2 Realtime =
958 pruebas**, sin violaciones ni omisiones.

Los seis S3776 accionables se refactorizaron separando probing HTTP,
clasificación de errores, normalización de resultados tipados, codificación
de eventos, validación de inversos URI y visita recursiva de planes.
Se preservan el orden de observación y ownership; no se añadió una dispensa
de complejidad. Ruff/formato del lote explícito de 36 archivos pasó
(`632d0dc7`); Problems no detectó errores en las cinco fuentes funcionales.
El Sonar completo `020e67dc` procesó todo el alcance y dejó un S1192 en un
mensaje de límite de Stringable; se extrajo la constante compartida y falta
reanalizar. `quality-all-04b47c35` pasó Ruff/formato y mostró todos los 1956
Python/stubs, además de los dos TOML de configuración.

La integrada `continuation-3-quality-refactor-integrated-32b77342` pasó
194 MCP y 586 Schemas, pero **se invalidó y detuvo** por tres intentos
`cmd.exe` rechazados durante Schemas. No se ejecutaron los selectores
posteriores. Se añadió trazabilidad de frames sin leer código/variables
locales ni relajar permisos. Guard18 volvió a pasar; Schemas aislado
(`continuation-3-schema-guard-trace-ed80cca5`) pasó 586 sin violaciones.
El origen intermitente de esos intentos y la integrada restante aún deben
comprobarse; no atribuir causa por conjetura.

La secuencia MCP→Schemas se repitió sin analizadores paralelos y pasó
194 + 586 sin violaciones. No se reprodujo el intento de shell; la barrera
sigue rechazándolo y ahora preserva sus frames si vuelve a ocurrir.

**Migración Ruff aplicada:** tras dos previsualizaciones, el codemod
`noqa-relocation-75ebcbdc` publicó 819 rutas, incluida `ruff.toml`.
Conservó cabeceras ya correctas; trasladó las dispensas restantes al inicio,
retiró `lint.per-file-ignores` y códigos sin diagnósticos actuales.
Comparó AST antes/después de cada fuente, mantuvo las reglas globales y
verificó las máscaras completas: **25385 diagnósticos sin supresiones antes
y después, ninguno oculto adicional**. Ruff y formato pasaron dentro del
snapshot previo a publicar; faltan los cierres finales del checkout actual.
Una primera publicación se detuvo antes de escribir por una línea vacía en
`setup.py`; se formateó únicamente ese archivo y se repitió todo el proceso.
Los 2249 elementos del formatter son 1956 Python/stubs más 293 Markdown,
no una prueba de recorrido de contenido excluido.

La lectura de manuales principales EN de Foundation, Console y HTTP quedó
contrastada con la implementación; se corrigieron `http.cors.allow_origins`,
el cierre del ejemplo headless y la descripción de `on()` tras creación.
Los snippets literales y la paridad restante EN/ES, el flujo DOCS.ps1,
la suite global final, las mediciones pertinentes y el verificador de
conservación de esta tercera continuación siguen pendientes.

**Cierres posteriores comprobados:**

- Manuales Foundation/Console/HTTP: 62 bloques Python literales entre EN/ES.
  `manual-scope-167b3d5c` pasó 58; cuatro fallos eran prerrequisitos ausentes
  del harness (modelo User y Route del bloque anterior). Sin editar los
  ejemplos, `manual-scope-5c433379` pasó los cuatro restantes. Paridad AST
  entre idiomas: 23/23 manuales; cero violaciones. Se invocaron handlers,
  schema validation, middleware, uploads, SSE, WebSocket, rutas, comandos,
  triggers y lifecycle nativos, no solo sus definiciones.
- `continuation-3-global-final-937c3b28`: **9675 PASSED + 20 SKIPPED**,
  1328.57 s, exit 0 y cero violaciones. Skips: dos uvloop no disponibles en
  Windows, cuatro rate-limit Redis y catorce Queues Redis no configurados.
  Ningún skip nuevo ni omitido contado como aprobado.
- `sonar-probe-0757f68b`: 1956 Python/stubs procesados hasta progress/end,
  cero diagnósticos y errores, perfil conservado con las excepciones
  puntuales autorizadas. `quality-all-8e6c6f86`: Ruff/formato aprobados,
  cobertura 1958/1958 (incluye ambos TOML), sin faltantes ni inesperados.
- El primer DOCS.ps1 de este cierre preservó la API anterior porque ocho
  campos nuevos no tenían texto y tres tipos externos no estaban citados
  como literales. Se corrigieron solo docstrings en cinco módulos.
  `docs-continuation-3-63c4e085` ejecutó el flujo íntegro desde la raíz,
  `UV_NO_SYNC=1`, SiteUrl oficial, Pydoctor warnings-as-errors y validador
  real: **2253 páginas, 13026 objetos API, 11733 tablas NumPy, errors=[]**,
  exit 0 y sin accesos protegidos. Se inspeccionaron firmas/enlaces y
  contenido representativos de Stringable, scheduler, Application y exports.
- Tras esas correcciones exclusivamente documentales se inició
  `continuation-3-final-frozen`, para certificar nuevamente la suite sobre
  las fuentes definitivas. Al escribir este bloque está en ejecución.

No confundir las cifras de esta sección con una declaración de 100%:
faltan el cierre del último proceso, el manifiesto final de conservación y
el contraste final de revisión/pruebas/supresiones que aún figure abierto.

El último proceso anterior, `continuation-3-final-frozen-12be974f`, terminó
con **9675 PASSED + 20 SKIPPED**, cero violaciones, en 776.75 s.
El cierre posterior de pruebas inspeccionó 173 archivos y 2750 métodos de
Console/HTTP/Foundation (`final-test-audit-bed09743`), contrastando contratos,
helpers de aserciones, pruebas de procesos y regresiones de ownership.
Se eliminaron solo tres duplicados AST exactos de Executor y cuatro smokes
de BaseScheduler estrictamente cubiertos por `testEventMethodsReturnNone`.
Las aserciones originales siguen presentes en los tests conservados.
La prueba de saturación del printer comprueba ahora que la cola realmente
está llena, que no aumenta y que `/overflow` no se emite; conserva cleanup
en finally. No se cambiaron timeouts, skips ni expectativas de producción.
La suite `continuation-3-final-deduplicated` está validando ese ajuste final.

La repetición de rendimiento `view-probes-8aeeae43` comparó cinco pares
alternados contra HEAD, en procesos separados: tipos/valores equivalentes
en los cinco, ocho órdenes de imports con 39 módulos/83 funciones.
El caso regex no coincidente de 2048 caracteres pasó de mediana
11518.984 us a 53.756 us; la caché retuvo 1024 planes y
472369–484401 bytes frente a 10000 planes/3575787 bytes en HEAD.
La URL absoluta conserva un pequeño coste adicional (0.490 → 0.840 us);
otras rutas mostraron dispersión y no se declara aceleración global.
Se conservaron las correcciones y el límite de memoria; no se cambió
código para favorecer esta medición.

`sonar-probe-98295e87` y `quality-all-259157a6` aprobaron las fuentes después
de corregir los docstrings de API. Solo el último ajuste de tests exige
refrescar sus hashes y la comprobación final. DOCS.ps1 ya está aprobado
para las fuentes de producción definitivas, y el sitio generado no se
editó manualmente.

Se revisaron kernel, resolver/compiler/cache/router/loader, respuestas, payload,
adaptadores HTTP/WebSocket, SSE y middleware. Falta completar y contrastar la
lectura de respuestas/controladores/defaults, contratos y todos los tests/manuales
HTTP restantes; los índices `review-http-{orionis,tests}.txt` permiten retomar
por archivo. El ownership del iterable síncrono quedó corregido; sigue abierta
la hipótesis del registro de rutas ante aplicaciones sucesivas con módulos ya
importados, que requiere trazar Foundation antes de decidir un cambio.
Las observaciones y tareas están también en la base de sesión.

Console ya tiene corregidos discovery vacía, generadores, scheduler y salida;
faltan sus cierres documentales y de analizadores. Continúan Foundation
(configuraciones, bootstrap y apps repetidas) y el cierre global permitido:
suite completa, supresiones/convenciones, Sonar real con perfil/hashes,
ejemplos literales restantes, DOCS.ps1 y conservación final.
No afirmar 100% ni pedir nueva autorización para pasar al siguiente paquete.
No se han hecho staging, commits, push ni cambios de dependencias.

### 0.6 Cierre local verificado de la continuación

Esta sección prevalece sobre las listas de pendientes de 0.1–0.5 y el estado
histórico de las secciones 2–7. Se retomaron las correcciones existentes,
se completaron los paquetes pendientes y se cerraron los controles del
alcance permitido. No se declara certificación de servicios, plataformas
ni versiones no ejecutados.

#### Resultado definitivo

| Control | Evidencia final | Resultado |
|---|---|---|
| Suite global permitida, sobre las fuentes definitivas | `continuation-3-final-deduplicated-f1305f2a.json` | **9668 PASSED, 20 SKIPPED**, 1201.55 s, exit 0, cero violaciones |
| Ruff y formato completos | `quality-all-6cbf8c16.json` | Ambos exit 0; 1958/1958 archivos analizables, ninguno omitido |
| SonarLint real, archivos completos | `sonar-probe-14bb809a.json` | 1956 Python/stubs procesados, progress completo, cero diagnósticos/errores |
| Flujo íntegro DOCS.ps1 | `docs-continuation-3-63c4e085.json` | Exit 0, warnings-as-errors, validación, publicación y cleanup completos |
| Validación independiente del sitio publicado | `docs-continuation-3-verify-c4dac5bb.json` | 2253 páginas, 13026 objetos, 11733 tablas NumPy, `errors=[]` |
| Manuales nuevos del cierre | `manual-scope-167b3d5c.json` + `manual-scope-5c433379.json` | 62 bloques Python literales comprobados; 23/23 pares EN/ES equivalentes; sin violaciones |
| Medición y semántica View | `view-probes-8aeeae43.json` | Cinco pares semánticamente equivalentes; caché limitada a 1024 planes; imports verificados |
| Pruebas y ubicación de excepciones | `final-test-audit-d37cbbcf.json` | 173 archivos/2743 métodos estáticos; sin duplicados exactos ni noqa fuera de cabecera |
| Conservación final | `continuation-3-integrity.json` | HEAD/índice intactos, hashes finales coincidentes, `unexpected=[]`, sin workspaces o stages pendientes |

Las 20 omisiones son **18 casos Redis sin servicio configurado y dos
integraciones uvloop no disponibles en Windows**. No se añadieron skips o
xfails. Las pruebas del instalador uv se ejecutaron mediante su fixture
offline controlado. El intérprete de validación fue CPython 3.14.6;
el launcher registró 3.13, 3.14 y 3.14t, pero ningún Python posterior a 3.14.
No se certifica el build free-threaded ni se instaló otro intérprete.

La diferencia entre 9675 aprobaciones anteriores y 9668 finales son siete
pruebas redundantes retiradas con evidencia: tres cuerpos idénticos de
Executor y cuatro smokes de scheduler cubiertos por una prueba más estricta.
La comprobación de cola llena se reforzó sin modificar el descarte de
producción. Los 17 candidatos sin aserción directa del auditor estructural
se contrastaron: quince delegan en helpers/casos hijos con aserciones y dos
son smokes de ejecución/aceptación de eventos del contrato. No son pruebas
vacías ni un resultado fallido del runner.

#### Alcance cerrado y decisiones conservadas

Quedan integradas y verificadas las correcciones de MCP, HTTP, Console y
Foundation descritas en 0.5, además del ciclo frío de imports Auth, los
límites compartidos de Argon2 y los límites/compatibilidad de Stringable.
Se conservaron las correcciones anteriores de Queues, Realtime, Schemas,
Mail, ORM, View y los demás paquetes, revalidadas por la suite global.
Se contrastaron contratos, consumidores, manuales, fixtures, imports,
exportaciones, cachés frías/calientes y ownership de errores/cancelaciones.

Sonar usa el analizador instalado y el perfil real, sin reglas globales
desactivadas. S100/S116 conservan los patrones camelCase autorizados y las
funciones de módulo se verifican por separado. Las excepciones por
línea/regla para falsos positivos se añadieron **solo tras la elección
`scoped-exceptions` del usuario** y con justificaciones locales; no se
alteraron APIs, protocolos ni awaits para ocultar diagnósticos.
La auditoría sin NOSONAR conserva sus 123 hallazgos iniciales como evidencia,
no como un verde ni como autorización general para suprimir reglas.

La migración de dispensas Ruff preservó el AST y las máscaras antes/después;
retiró `per-file-ignores` sin reducir la selección global. El diff final no
presenta whitespace inválido fuera del HTML generado. `git diff --check`
informa 60319 líneas de espacios de plantillas en 2168 HTML generados
(exit 2); no se editaron manualmente para maquillar ese diagnóstico.
Ruff/formato y el validador oficial del sitio están aprobados.

#### Conservación y recursos

- HEAD: `036d04bac1381cc4f35c49431bb41a77d18419c3`.
- SHA256 del inventario `git ls-files --stage -z`:
  `1fba74434aed05646cc8c189ecf486876db591e1774e98a860bb1623cdf860ff`.
- Checkpoint conservado: `continuation-3-baseline.json`, 3576 rutas pendientes.
  Estado final: 4215 rutas pendientes, sin staging, commits, push ni despliegue.
- Se contrastaron 2357 archivos del snapshot nativo y 1956 hashes Sonar,
  además del snapshot Ruff y la configuración Sonar normalizada exactamente
  como la midió el analizador.
- `continuation-3-mechanical-proof.json` explica otros 65 paths originalmente
  limpios: AST completo o texto del manual y AST de sus bloques idénticos.
  No se aprobaron directorios completos ni diferencias desconocidas.
- Un JSON de diagnóstico antiguo que quedaba en `framework/files` se
  trasladó a la sesión con SHA idéntico; no se eliminó el directorio.
  Los recursos propios de validación y los stages documentales se limpiaron.

La evidencia está en
`C:\Users\runate\.copilot\session-state\745eed3b-fbab-4e9d-992e-da09159ffc68\files`.
Los scripts de sesión no son dependencias del framework ni nuevos entregables
del checkout. Los hashes y comparaciones están en los JSON, no solo en este
resumen.

#### Límites que no deben borrarse al retomar

`tests/real_database` y el `.env` real permanecieron fuera de las validaciones
controladas. No se operaron bases, correo, storage ni servicios de producción.
No se convierte en certificación retrospectiva el incidente de formatter
descrito en 0.5: se conserva su incertidumbre y la autorización posterior
`retain-and-validate`. El entorno es compartido, no un sandbox del SO.

Las tres tentativas de shell rechazadas en una ejecución intermedia de
Schemas no se reprodujeron en las repeticiones aislada, ordenada ni globales.
La barrera nunca se relajó; los globals definitivos no registraron violaciones.
No hay un defecto de producción demostrado pendiente de esa observación.

No quedan controles ejecutables pendientes dentro de esta continuación local.
Si se modifica código después de este cierre, los hashes finales dejan de
certificar ese nuevo estado: revalidar el delta y consumidores, no volver a
auditar desde cero ni eliminar las regresiones conservadas.

## 1. Objetivo original, alcance y restricciones

La solicitud original fue actuar como responsable de ingeniería, arquitectura, rendimiento y calidad: revisar **todos y cada uno** de los paquetes, subpaquetes, contratos, implementaciones, pruebas y documentación de `orionis/*`; corregir causas raíz directamente; preservar APIs; simplificar solo redundancias demostradas; medir rendimiento; validar realmente Python 3.14 y versiones posteriores soportadas disponibles; terminar con integración, Ruff, formato, SonarLint real y el flujo íntegro de `DOCS.ps1`.

El texto original se transcribe íntegramente más abajo, en esta misma sección. La siguiente ruta se conserva únicamente como procedencia histórica; no hace falta acceder a ella para continuar:

```text
C:\Users\runate\.codex\attachments\65b133ad-ec88-4dd0-b692-7321ca2f1d4c\Texto pegado.txt
```

Inventario físico actual: los 28 directorios de paquetes enumerados en la sección 3, más `orionis/__init__.py` y `orionis/_exports.py`. No se detectó un paquete raíz adicional en el listado actual. La revisión también alcanza archivos externos indispensables: configuración, CLI, runner CI, recursos documentales, pruebas raíz y generación de código.

Restricciones que deben conservarse:

1. **Excluir `tests/real_database/` antes de recorrer, descubrir, leer contenido, importar o ejecutar.** No modificar, mover ni usar esa carpeta para esconder pruebas. No ejecutar un comando global cuyo descubrimiento la visite para excluirla después.
2. Trabajar secuencialmente por paquetes sobre el estado integrado. Paralelizar tareas dentro del paquete; la preparación de lectura del siguiente es posible, sus cambios deben esperar al cierre del actual.
3. Preservar cambios e índice Git existentes. No `reset`, `clean`, `checkout --`, staging masivo, commits, push, publicación ni despliegue sin autorización. No crear `AGENTS.md`.
4. No leer ni alterar el `.env` real para validar. No enviar correo real ni operar sobre bases, credenciales, almacenamiento o servicios de producción. Usar copias controladas, configuración sintética y recursos propios.
5. No añadir funcionalidades por inferencia del nombre de un paquete, extensiones C/Rust, dependencias innecesarias o actualizaciones masivas. No reducir controles criptográficos ni costes de hashing para mejorar tiempos.
6. Métodos de clase en camelCase, funciones de módulo/anidadas en snake_case; conservar nombres obligatorios de Python, librerías externas y fixtures cuyo nombre sea el objeto de la prueba.
7. Docstrings en inglés, triple comilla doble, estilo NumPy, primera línea imperativa, sin sección `Examples`; parámetros, retornos y excepciones reales. El Pydoctor del proyecto exige documentar `Returns / None / No return value.` en numerosos métodos sin retorno: no describir efectos secundarios como un valor devuelto.
8. Actualizar manuales EN/ES existentes; no editar HTML generado a mano. No afirmar rendimiento máximo ni equivalencia a C. Conservar solo optimizaciones respaldadas por mediciones comparables.
9. No ocultar defectos con skips, `xfail`, capturas genéricas, aserciones débiles, filtros adicionales, `NOSONAR` o rebaja de perfiles. Excepciones Ruff imprescindibles en cabecera, códigos explícitos y justificación; revisar también sin `noqa`.

### Decisiones explícitas del usuario: NO volver a preguntar

- **S116/camelCase:** autorizó permitir `^[_a-z][_a-zA-Z0-9]*$` manteniendo activa la regla, para conservar campos públicos como `FileInfo.lastModified`, `mimeType` y `createdAt`. Está físicamente en `.vscode/settings.json`, que Git ignora. No forzar su adición al índice ni renombrar esa API.
- **Encrypter:** autorizó **AES-256-GCM como valor predeterminado y rechazo de CBC sin autenticación**, aun requiriendo migrar datos CBC antiguos antes de actualizar. El defecto reproducido permitía alterar texto descifrado modificando el IV no autenticado. No restablecer CBC por compatibilidad ni diseñar criptografía propia.

### Solicitud original íntegra: especificación de la revisión

La transcripción siguiente conserva el texto completo del adjunto del usuario, sin sustituirlo por el resumen anterior. Incluye objetivo, responsabilidades de cada paquete, exclusiones, depuración de tests, rendimiento, convenciones, documentación, Ruff/SonarLint, secuencia y criterios de aceptación. Solo se normalizan los saltos de línea al formato del documento. Aplicar la precedencia de instrucciones posteriores indicada al principio.

SHA-256 de los bytes del adjunto consultado: `f62ec9132c8e9c5b67259aae1f031ce875cdc3729836c981bc72677e34b7071d`.

<!-- ORIGINAL_REQUEST_BEGIN -->
````text
Actúa como responsable de ingeniería, arquitectura, rendimiento y calidad de Orionis Framework.

Realiza una revisión exhaustiva de TODOS los paquetes del framework y aplica directamente las correcciones necesarias en el repositorio. No te limites a presentar un diagnóstico, proponer cambios o escribir un plan.

Trabaja secuencialmente por paquetes sobre el mismo estado integrado del código y termina con una validación global. No solicites confirmación para pasar de un paquete al siguiente.

OBJETIVO FINAL

Entregar el código de Orionis corregido, simplificado, seguro, funcional e integrado, validado realmente en Python 3.14 y en las versiones posteriores soportadas que estén disponibles.

La implementación debe conservar únicamente el código y las pruebas necesarios, cumplir las convenciones del proyecto, tener su documentación existente actualizada y superar las comprobaciones de Ruff, SonarLint y documentación.

Busca el mayor rendimiento práctico posible dentro de la arquitectura del proyecto, minimizando el coste añadido por Orionis y aprovechando operaciones nativas. La aspiración de acercarse al rendimiento de C debe traducirse en optimizaciones medidas, no en afirmaciones sin evidencia.

El entregable son los cambios necesarios en implementación, pruebas y documentación existente. No generes informes adicionales.


1. ALCANCE OBLIGATORIO: TODO EL FRAMEWORK

Revisa completamente estos 28 paquetes, incluidos todos sus subpaquetes, archivos, contratos, implementaciones, pruebas y documentación:

01. orionis.aio
    Revisa gestión y propiedad de event loops, puentes síncronos/asíncronos, ejecución en hilos, propagación del contexto, cancelación, cierre y liberación de recursos. Comprueba integración con consumidores y evita bloqueos o reutilización indebida de loops.

02. orionis.auth
    Revisa autenticación y autorización, guards, identidad, credenciales, tokens, permisos, políticas, revocación y aislamiento entre solicitudes. Valida su integración con sesiones, hashing, ORM, HTTP y manejo de excepciones, sin elevar permisos accidentalmente.

03. orionis.background
    Revisa ejecución diferida de callables síncronos y asíncronos, argumentos, orden, propagación de errores, cancelación y ejecución tras la respuesta. Diferencia reejecuciones permitidas por contrato de duplicaciones accidentales en sus consumidores.

04. orionis.cache
    Revisa stores, serialización, claves, prefijos, valores ausentes, TTL, invalidación, operaciones múltiples y locks. Distingue la caché de aplicación de la caché de artefactos del framework y valida sus garantías reales de concurrencia.

05. orionis.console
    Revisa descubrimiento y ejecución de comandos, argumentos, salida, códigos de retorno, generadores, plantillas y scheduling. Comprueba integración con bootstrap, contenedor, logging y excepciones, sin ejecuciones o reportes duplicados.

06. orionis.container
    Revisa bindings, aliases, lifetimes, scopes, inyección, providers, facades, resolución diferida, dependencias circulares y concurrencia. Comprueba aislamiento, limpieza, propagación del contexto y corrección de las anotaciones utilizadas en tiempo de ejecución.

07. orionis.database
    Revisa configuración, conexiones, drivers, compilación SQL, parámetros, transacciones, savepoints, migraciones, seeders y cierre de recursos. Valida integración con ORM y consumidores sin ejecutar tests/real_database/ ni operar sobre bases de producción.

08. orionis.encrypter
    Revisa claves, algoritmos y modos existentes, aleatoriedad, integridad, formatos de payload, entradas manipuladas y errores seguros. Comprueba integración con configuración y consumidores. No desarrolles criptografía propia ni reduzcas garantías por rendimiento.

09. orionis.environment
    Revisa lectura y escritura de variables, conversión de tipos, valores ausentes, precedencia, caché, recarga y persistencia de .env. Evita filtraciones de secretos y modificaciones del entorno real durante las pruebas.

10. orionis.failure
    Revisa el manejo centralizado de excepciones, clasificación, exclusiones, reporte y presentación HTTP/CLI. Comprueba que los consumidores lo utilizan correctamente, sin capturas, conversiones, logs o respuestas redundantes ni pérdida del error original.

11. orionis.foundation
    Revisa aplicación, bootstrap, configuración, rutas internas, registro de servicios, providers, kernels, startup y shutdown. Comprueba arranques repetidos, limpieza, aislamiento entre aplicaciones y coherencia de la integración global.

12. orionis.hashing
    Revisa drivers, parámetros, verificación de contraseñas, hashes inválidos, rehash, dependencias opcionales y ejecución del trabajo costoso. No reduzcas costes criptográficos ni elimines protecciones para mejorar mediciones.

13. orionis.http
    Revisa routing, resolución, middleware, solicitudes, respuestas, headers, cookies, payloads, formularios, uploads, archivos y streaming. Valida seguridad, límites, desconexiones, ASGI/RSGI e integración con autenticación, sesiones, schemas, vistas y excepciones.

14. orionis.introspection
    Revisa reflexión, firmas, anotaciones, herencia, descriptors, callables, clasificación de miembros, imports y descubrimiento. Comprueba cachés, invalidación y compatibilidad real con Python 3.14 y con los consumidores del contenedor.

15. orionis.localization
    Revisa carga de traducciones, locales, precedencia, fallback, interpolación, pluralización, caché y errores. Comprueba rutas seguras y aislamiento del locale cuando corresponda, sin cambiar las reglas de resolución accidentalmente.

16. orionis.logging
    Revisa canales, niveles, formateadores, handlers, propagación, rotación, concurrencia y cierre. Evita handlers y registros duplicados, fugas de recursos y exposición de secretos, especialmente al integrarse con el manejador centralizado de excepciones.

17. orionis.mail
    Revisa composición, destinatarios, privacidad de Bcc, MIME, contenido, templates, adjuntos, transportes y errores. Comprueba aislamiento entre envíos y cierre de streams. Las pruebas no deben enviar mensajes a destinatarios reales.

18. orionis.mcp
    Identifica primero su responsabilidad y contratos reales. Revisa registro y ejecución de las capacidades existentes, validación de entradas, contexto, permisos, transportes, errores y ciclo de vida cuando correspondan. No inventes funcionalidades a partir del nombre.

19. orionis.metadata
    Identifica las fuentes de verdad, estructuras y consumidores reales. Revisa consistencia, validación, mutabilidad, registros, exportaciones y cachés. Elimina duplicaciones de metadatos únicamente cuando no representen contratos distintos.

20. orionis.orm
    Revisa modelos, metaclases, consultas, relaciones, hidratación, casts, asignación masiva, atributos ocultos, scopes, eventos, paginación y persistencia. Incluye factories y otros subpaquetes existentes. Valida integración con database sin ejecutar la carpeta excluida.

21. orionis.queues
    Revisa jobs, serialización, resolución de dependencias, conexiones, reservas, confirmaciones, reintentos, timeouts, fallos y cierre de workers. Comprueba aislamiento por trabajo y garantías reales de entrega; no confundas reintentos legítimos con duplicaciones de implementación.

22. orionis.realtime
    Identifica su implementación real. Revisa conexiones, transportes, mensajes, suscripciones, autorización, aislamiento, desconexiones, presión de carga y limpieza cuando correspondan. No prometas protocolos o garantías que el código no implemente.

23. orionis.schemas
    Revisa definición de schemas, metadatos, conversión, constraints, reglas, campos anidados y agregación de errores. Comprueba que las optimizaciones y cachés no omiten validaciones ni cambian los errores observables.

24. orionis.session
    Revisa stores, restauración, persistencia, cookies, expiración, regeneración, invalidación y flash data. Comprueba aislamiento entre solicitudes, protección de identificadores e integración con autenticación, HTTP y vistas.

25. orionis.storage
    Revisa drivers, normalización de rutas, traversal, enlaces, permisos, archivos, directorios, uploads, streams y operaciones de copia o movimiento. Comprueba atomicidad donde se prometa y liberación de recursos, sin modificar almacenamiento real del usuario.

26. orionis.support
    Revisa recursivamente entidades, colecciones, estructuras, patrones, utilidades, fechas, formateadores, medición y facades. Presta especial atención a sus numerosos consumidores antes de eliminar o cambiar una utilidad compartida.

27. orionis.test
    Revisa el propio motor de pruebas: descubrimiento, importaciones, filtros, inyección, aislamiento, resultados, subpruebas, omisiones, fallos y códigos de salida. Garantiza que los errores de colección o importación no desaparezcan silenciosamente ni produzcan falsos éxitos.

28. orionis.view
    Revisa configuración del motor, carga y renderizado, templates, contexto, globals, filtros, extensiones, escape y caché. Comprueba aislamiento entre solicitudes e integración con HTTP, sesiones, localización y servicios.

Esta lista es un inventario obligatorio, no un orden técnico rígido ni una especificación de funcionalidades nuevas.

Contrasta cada foco con el código real. Si una capacidad no existe, no la implementes únicamente por aparecer mencionada.

Descubre además cualquier paquete o módulo adicional existente dentro de orionis/ e inclúyelo en la revisión.

Incluye los archivos raíz de orionis/, especialmente __init__.py y _exports.py cuando existan, así como exportaciones, carga diferida y puntos de entrada.

Revisa también los archivos externos a orionis/ necesarios para su integración, configuración, generación de código, pruebas y documentación. Modifícalos únicamente cuando sea imprescindible para completar esta tarea.

Distingue orionis/test/, que es código del framework, de tests/, que contiene la suite de pruebas.


2. EXCLUSIONES Y PROTECCIÓN DEL REPOSITORIO

Exclusión obligatoria:

tests/real_database/

La exclusión comprende todos sus archivos y descendientes.

No modifiques, elimines, renombres, muevas, importes ni ejecutes su contenido. Exclúyelo antes del descubrimiento y de la importación de pruebas, no después de cargarlo.

Evita que formateadores, analizadores o correcciones masivas alteren esa carpeta.

No muevas pruebas hacia ella para eludir validaciones. No rompas contratos de utilidades compartidas que puedan utilizar sus pruebas.

Preserva los cambios previos del usuario. Compara contra el estado inicial de esta tarea, no presupongas que el repositorio comenzó limpio.

No reviertas cambios ajenos, no hagas limpieza destructiva y no realices commits, push, publicaciones o despliegues sin autorización.

No ejecutes operaciones sobre servicios de producción, credenciales reales, correos reales o almacenamiento real para validar el framework. Utiliza entornos de prueba controlados.

No crees AGENTS.md ni dependas de su existencia.

No añadas funcionalidades nuevas, dependencias innecesarias, rediseños generales o actualizaciones masivas de versiones ajenas a las correcciones.


3. PREPARACIÓN Y FIABILIDAD DE LA VALIDACIÓN

Antes de modificar código:

- Inspecciona el estado del repositorio.
- Lee pyproject.toml, el archivo de dependencias bloqueadas, DOCS.ps1 y las configuraciones reales de pruebas, Ruff y Sonar.
- Identifica el runner, sus reglas de descubrimiento y los mecanismos de exclusión.
- Verifica intérpretes y dependencias disponibles.
- Establece una línea base de pruebas y analizadores dentro del alcance permitido.

No asumas que el runner es pytest. No inventes comandos, parámetros, herramientas ni resultados.

Comprueba inicialmente que el sistema de pruebas informa correctamente los errores de colección, importación y ejecución. No bases toda la revisión en un motor que pueda ocultar fallos.

Distingue fallos preexistentes, fallos introducidos y limitaciones del entorno.

Organiza la revisión según dependencias y riesgos. Lleva el seguimiento durante la ejecución sin crear archivos de planificación, auditoría o progreso en el repositorio.


4. CORRECCIÓN DE LA IMPLEMENTACIÓN

Revisa el contenido completo de cada paquete, no solamente los archivos modificados recientemente o alcanzados por las pruebas actuales.

Contrasta contratos, documentación, interfaces y consumidores para establecer el comportamiento correcto. Ni las pruebas ni la implementación actual deben considerarse infalibles.

Corrige causas raíz relacionadas con:

- Lógica, validación, tipos y estados inconsistentes.
- Seguridad y exposición de información.
- Concurrencia, cancelación y estado compartido.
- Inicialización, cierre y liberación de recursos.
- Imports, exportaciones, configuración y resolución dinámica.
- Integración entre paquetes y dependencias opcionales.

Reutiliza los mecanismos centrales de Orionis. Evita crear rutas alternativas de validación, configuración, resolución de servicios o manejo de excepciones que dupliquen responsabilidades.

Elimina código muerto, ramas obsoletas, imports sin uso y duplicaciones reales. Antes de eliminar un elemento, comprueba contratos públicos, reflexión, registros, hooks y referencias por nombre.

No consideres innecesario un adaptador de compatibilidad solo porque delegue en otra implementación.

Cada defecto funcional corregido debe quedar protegido por una prueba de regresión pertinente. Siempre que el entorno lo permita, confirma que la prueba falla por la causa esperada antes de corregirla y que pasa después.

Mantén los cambios proporcionados al problema. No sacrifiques compatibilidad mediante renombrados o simplificaciones mecánicas.


5. DEPURACIÓN DE TODA LA SUITE DE PRUEBAS

Revisa todo tests/, excepto tests/real_database/, y relaciona las pruebas con los comportamientos de los paquetes.

Conserva un conjunto mínimo suficiente para proteger contratos, casos relevantes, límites, errores, seguridad, regresiones e integración.

No persigas una reducción arbitraria del número de pruebas.

Elimina o consolida pruebas redundantes únicamente cuando protejan el mismo comportamiento bajo condiciones equivalentes.

Dos pruebas que ejecutan las mismas líneas no son necesariamente redundantes.

Antes de eliminar una prueba, identifica qué prueba conservada protege su comportamiento o demuestra que ese comportamiento dejó de ser aplicable. No necesitas crear un informe para ello.

Utiliza parametrización, subpruebas o mecanismos equivalentes del runner para consolidar estructuras repetidas sin perder escenarios diferenciados ni claridad de diagnóstico.

Corrige expectativas incorrectas, aserciones débiles, mocks excesivos, preparación defectuosa, contaminación del estado y limpieza incompleta.

No sustituyas la lógica que se pretende validar por un mock que siempre devuelve el resultado esperado.

Evita dependencias accidentales del orden de ejecución, sleeps arbitrarios, reloj real y servicios externos no controlados. Mantén pruebas de integración reales donde aporten garantías distintas y puedan ejecutarse de forma segura.

No elimines una prueba por estar fallando, ser lenta o resultar compleja.

No introduzcas skip, xfail, expectedFailure, capturas genéricas, filtros adicionales o aserciones debilitadas para ocultar defectos.

Revisa las omisiones preexistentes. No las contabilices como pruebas aprobadas.

Compara el descubrimiento inicial y final. Comprueba que los renombrados no hacen desaparecer pruebas y distingue cantidad de métodos de cantidad de escenarios cuando corresponda.

No conviertas benchmarks dependientes del hardware en pruebas funcionales frágiles.

Las pruebas con dobles no certifican el comportamiento de un servicio externo real. No atribuyas validación a integraciones o motores que no hayas ejecutado.


6. PYTHON 3.14+ Y RENDIMIENTO

Ejecuta realmente la validación en Python 3.14. Una ejecución en otra versión no sustituye este requisito.

Valida también las versiones posteriores soportadas que estén disponibles. No declares compatibilidad comprobada con versiones, plataformas o variantes del intérprete no ejecutadas.

Revisa especialmente el comportamiento de anotaciones, introspección, imports, asyncio y dependencias que intervienen en tiempo de ejecución.

No apliques cambios automáticos a anotaciones o imports que rompan la inyección de dependencias, la reflexión o el descubrimiento.

Para optimizar:

- Identifica rutas críticas mediante mediciones o profiling.
- Compara antes y después con cargas equivalentes y el mismo entorno.
- Repite las mediciones para distinguir mejoras del ruido.
- Considera latencia, rendimiento sostenido, memoria y concurrencia según el componente.
- Comprueba inicialización y escenarios con cachés frías y calientes cuando corresponda.

Prioriza reducir complejidad algorítmica, recorridos, asignaciones, copias, serializaciones, reflexión y operaciones de entrada/salida innecesarias.

Aprovecha primitivas de la biblioteca estándar y dependencias existentes con implementación nativa. No agregues extensiones C/Rust ni rediseñes la arquitectura únicamente para perseguir una cifra.

No introduzcas cachés sin invalidación correcta, límites y aislamiento apropiados.

No rebajes costes criptográficos, controles de acceso, validaciones, garantías transaccionales o manejo de errores como supuesta optimización.

No cambies contratos síncronos/asíncronos sin necesidad ni añadas trabajo bloqueante a rutas asíncronas para mejorar una medición aislada.

Descarta microoptimizaciones especulativas que compliquen el código sin beneficio demostrado.

No afirmes “rendimiento máximo”, “equivalente a C” o una mejora porcentual sin mediciones que lo respalden.

Usa herramientas existentes o recursos temporales para medir. No añadas informes, archivos de resultados o benchmarks improvisados permanentes.


7. CONVENCIONES DE NOMBRES Y DOCSTRINGS

Revisa todos los métodos y funciones definidos por el proyecto dentro del alcance, no solamente los nuevos.

Métodos de clases:
- Públicos: camelCase.
- Protegidos: _camelCase.
- Privados: __camelCase.

Funciones fuera de clases:
- snake_case.

La regla comprende métodos de instancia, estáticos, de clase, asíncronos, auxiliares y de pruebas.

Los métodos de prueba deben conservar nombres descriptivos compatibles con el descubrimiento, por ejemplo testRejectsInvalidInput.

Conserva nombres especiales de Python y nombres obligatorios de hooks, protocolos y contratos externos.

Actualiza todas las referencias afectadas por un renombrado, incluidas referencias por nombre, templates, documentación y exportaciones. No rompas APIs públicas mediante renombrados mecánicos.

Todos los métodos y funciones deben tener docstrings:
- Delimitados con triple comilla doble.
- En inglés.
- En estilo NumPy.
- Con primera línea imperativa conforme a D401.
- Concisos y coherentes con el comportamiento real.
- Sin sección Examples.
- Con Parameters, Returns, Yields y Raises únicamente cuando correspondan.

No inventes parámetros, retornos, excepciones o garantías. No describas efectos secundarios como si fueran el valor devuelto.

Documenta también clases, módulos y elementos públicos según las necesidades de la referencia del proyecto.

Preserva fixtures cuyo nombre no convencional o ausencia de docstring sea intencional y constituya el objeto de la prueba. Explica esa intención en su contexto, sin destruir el escenario mediante normalizaciones automáticas.


8. DOCUMENTACIÓN DE LOS PAQUETES Y DOCS.ps1

Actualiza la documentación existente dentro de:

orionis/<paquete>/docs/

Incluye las carpetas docs/ de los subpaquetes afectados y mantén sincronizadas las variantes de idioma existentes.

La documentación debe corresponder a la implementación final:
- API, firmas, parámetros y retornos.
- Configuración y requisitos reales.
- Errores y límites.
- Integración y ciclo de vida.
- Ejemplos de uso correctos.
- Garantías reales de concurrencia, seguridad y rendimiento.

No conviertas los manuales en informes de auditoría ni añadas listas de cambios realizadas durante esta tarea.

La prohibición de una sección Examples se aplica a los docstrings, no a los ejemplos útiles de los manuales existentes.

Distingue las fuentes documentales de los paquetes de docs/ en la raíz, que contiene la salida generada.

No corrijas problemas editando manualmente HTML generado.

Lee y ejecuta DOCS.ps1 desde la raíz utilizando su configuración real en pyproject.toml y los recursos de resources/docs/pydoctor.

La validación debe incluir:
- La ejecución de Pydoctor con --warnings-as-errors.
- La ejecución de resources.docs.pydoctor.validate sobre el sitio generado.
- Las verificaciones adicionales de integridad y artefactos del propio script.

Comprueba páginas representativas, enlaces, referencias, firmas y contenido generado. Un proceso exitoso no sustituye revisar que el contenido sea correcto.

No desactives advertencias, exclusiones de calidad, validadores o comprobaciones para lograr un resultado satisfactorio.

No modifiques DOCS.ps1 para ocultar defectos de documentación. Si detectas un error real en su implementación, corrígelo conservando sus garantías de seguridad e integridad.

Respeta la política del repositorio sobre versionado de la salida generada. No sobrescribas cambios previos del usuario ni publiques el sitio fuera del repositorio.


9. RUFF Y SONARLINT

El código final debe superar Ruff, la comprobación de formato y SonarLint dentro de todo el alcance permitido.

Analiza archivos completos, no solamente líneas nuevas o modificadas.

Mantén la configuración de calidad del proyecto. No reduzcas reglas, perfiles o archivos analizados para simular un resultado limpio.

EXCEPCIONES DE RUFF

Las excepciones imprescindibles deben concentrarse al inicio del archivo donde se necesiten, con códigos explícitos, usando este formato:

# ruff: noqa: PLR0913, SLF001

Los códigos anteriores son un ejemplo, no una lista que debas copiar a todos los archivos.

Coloca el bloque después de shebang o declaración de codificación cuando existan y antes del contenido normal del módulo.

No dejes excepciones Ruff dispersas o inline. No uses noqa sin códigos.

No añadas per-file-ignores ni ignores globales para sustituir estas excepciones de cabecera.

Revisa las dispensas específicas de archivos que ya existan en la configuración y normaliza su ubicación cuando corresponda, sin alterar indiscriminadamente la selección global de reglas.

Antes de trasladar una excepción a la cabecera, inspecciona todas las infracciones de esa regla en el archivo. No amplíes silenciosamente una supresión a defectos que deben corregirse.

Ejecuta también una revisión sin respetar las supresiones noqa para comprobar qué diagnósticos quedan ocultos y justificar únicamente los imprescindibles.

Elimina códigos de excepción obsoletos. Cuando sea necesario, añade una explicación breve junto al bloque de cabecera, no en un informe separado.

SONARLINT

Ejecuta el análisis SonarLint disponible. Si el repositorio utiliza otro flujo Sonar, verifica que su perfil y alcance cubren las reglas requeridas; no presupongas equivalencia.

No inventes una CLI o comandos que no existan en el entorno.

No añadas NOSONAR ni desactives reglas para ocultar problemas. Revisa las supresiones existentes y corrige las que encubran defectos.

Una revisión manual, Ruff limpio o un analizador distinto no certifican automáticamente que SonarLint esté limpio.

Si el analizador obligatorio no está disponible o no puede procesar el código, continúa con las demás comprobaciones, pero deja esa validación explícitamente pendiente.


10. EJECUCIÓN SECUENCIAL Y CIERRE GLOBAL

Para cada paquete:

1. Identifica contratos, consumidores, pruebas y documentación.
2. Revisa íntegramente su implementación.
3. Corrige defectos con pruebas de regresión.
4. Elimina código y pruebas verdaderamente redundantes.
5. Normaliza nombres y docstrings.
6. Actualiza su documentación existente.
7. Ejecuta pruebas y analizadores del paquete y de sus consumidores afectados.
8. Comprueba rendimiento cuando hayas modificado rutas relevantes.
9. Continúa con el siguiente paquete conservando los cambios integrados.

Si modificas una dependencia compartida, vuelve a validar los paquetes afectados aunque ya se hubieran revisado.

No declares completo un paquete solo porque sus pruebas actuales pasen.

No detengas toda la revisión ante el primer bloqueo independiente: avanza en lo que sí pueda validarse y conserva claramente el estado pendiente, sin crear informes.

Cuando hayas revisado todos los paquetes, ejecuta sobre el estado final integrado:

- Toda la suite de tests/ permitida, excluyendo tests/real_database/ antes del descubrimiento y la importación.
- Ruff sobre todo el código del framework y las pruebas permitidas.
- La comprobación de formato correspondiente.
- El análisis Sonar requerido sobre ese mismo alcance.
- El flujo completo de DOCS.ps1.
- Las comprobaciones de imports, exportaciones públicas, bootstrap y configuración.
- Recorridos de integración representativos entre los paquetes.
- Las mediciones finales pertinentes para las optimizaciones realizadas.

Los recorridos integrados deben cubrir, cuando existan, HTTP, CLI, contenedor, schemas, autenticación, sesiones, vistas, background, colas y manejo centralizado de excepciones.

Comprueba especialmente ausencia de aislamiento roto, recursos pendientes, ejecuciones duplicadas y manejo repetido de errores.

No confundas cobertura de líneas, compilación, cero pruebas descubiertas, pruebas omitidas o una ejecución parcial con validación funcional completa.

Revisa el diff final. Solo deben quedar cambios necesarios en implementación, pruebas, documentación existente y archivos de integración imprescindibles.

La carpeta excluida debe conservar exactamente el estado que tenía al inicio de esta tarea.

Limpia únicamente los recursos temporales creados por esta ejecución. No elimines archivos previos del usuario.


11. CRITERIOS DE ACEPTACIÓN Y RESPUESTA FINAL

La tarea se considera completada únicamente cuando:

- Todos los paquetes y subpaquetes reales hayan sido revisados.
- Los defectos identificados dentro del alcance estén corregidos.
- Las pruebas restantes protejan comportamientos relevantes sin redundancias injustificadas.
- Se cumplan las convenciones de nombres y documentación, salvo contratos externos y fixtures intencionales justificados.
- Todas las pruebas permitidas y ejecutables pasen.
- Ruff, formato y el análisis Sonar requerido estén aprobados.
- DOCS.ps1 complete satisfactoriamente todas sus comprobaciones.
- La documentación existente describa fielmente la implementación.
- Los paquetes funcionen integrados, no solamente de forma aislada.
- Las optimizaciones conservadas tengan fundamento y no degraden corrección o seguridad.
- No queden informes, planes, resultados, scripts temporales ni artefactos ajenos al entregable.

No declares “100 % validado” mientras quede pendiente una comprobación obligatoria. No extrapoles los resultados a tests/real_database/, servicios no ejecutados o versiones de Python no comprobadas.

Si existe un bloqueo real, indica exactamente la comprobación pendiente sin inventar resultados ni presentar el trabajo parcial como finalizado.

No generes informes adicionales en el repositorio.

La respuesta final debe tener un máximo de tres líneas:
1. Alcance realmente completado.
2. Resultado real de pruebas, Ruff, formato, Sonar y documentación.
3. Bloqueos o validaciones pendientes, o confirmación de que no existen dentro del alcance definido.

Comienza la revisión completa y aplica los cambios necesarios.
````
<!-- ORIGINAL_REQUEST_END -->

### Aclaraciones y decisiones posteriores que modifican o refuerzan el encargo

1. **Alcance reiterado literalmente por el usuario:** «RECUERDA QUE DEBE SER TODOS Y CADA UNO DE LOS PAQUETES DEL FRAMEWORK `D:\WORKSPACE\ORIONIS_FRAMEWORK\framework\orionis\*`». No basta con los paquetes que ya pasaron tests ni con los archivos tocados; completar todos los subpaquetes y archivos raíz, y validar consumidores.
2. **Continuidad:** el usuario indicó que la revisión no había terminado y pidió concluirla tras recargar créditos. Es una exigencia de completar el alcance; no es evidencia de aprobación técnica ni permiso para omitir controles.
3. **Excepción de compatibilidad S116:** ante el conflicto de renombrar campos públicos `FileInfo.lastModified`, `mimeType` y `createdAt`, respondió «Sí, admitir camelCase en S116 y conservar la API». El único cambio de patrón autorizado fue `^[_a-z][_a-zA-Z0-9]*$`, manteniendo S116 y el resto del perfil.
4. **Excepción criptográfica autorizada:** tras reproducir manipulación de plaintext mediante IV CBC no autenticado, respondió «Sí, usar GCM y rechazar CBC sin autenticación». Autoriza default AES-256-GCM y rechazo de payloads CBC no autenticados; exige considerar migración de datos existentes antes de actualizar. No autoriza volver a admitirlos ni rebajar autenticación.
5. **Cambio de tarea vigente:** después ordenó detener nuevas modificaciones y entregar este handoff. Se reproduce a continuación para que la restricción no dependa del chat.
6. **Aclaración actual sobre el documento:** el usuario exige que `HANDOFF_ORIONIS.md` sea toda la fuente de verdad para Copilot e incluya también el detalle de lo que se pidió hacer. Por eso contiene el encargo íntegro, no solo el historial de cambios ni un enlace a otro archivo.

### Instrucción posterior íntegra de detención y traspaso

````text
Detén las nuevas modificaciones y prepara un informe técnico exhaustivo de todo el trabajo realizado hasta ahora en el framework Orionis.

Crea un archivo llamado `HANDOFF_ORIONIS.md` en la raíz del proyecto, diseñado para que otro agente de IA (GitHub Copilot con GPT-6 Astra) pueda continuar exactamente donde terminaste.

El informe debe incluir:

1. Objetivo original de la revisión y alcance de todos los paquetes.
2. Paquetes revisados, finalizados y pendientes.
3. Todos los errores encontrados y las correcciones implementadas.
4. Archivos modificados y justificación de los cambios.
5. Pruebas ejecutadas, resultados comprobados y pruebas pendientes.
6. Comandos exactos para reproducir las validaciones.
7. Problemas conocidos, riesgos y posibles regresiones.
8. Estado actual del repositorio Git, incluyendo cambios sin confirmar.
9. Orden recomendado de tareas para terminar la revisión global.
10. Instrucciones técnicas detalladas para que Copilot continúe sin duplicar trabajo ni perder correcciones.

Distingue claramente entre tareas completadas, parcialmente completadas y no iniciadas. No presentes ninguna prueba pendiente como aprobada.

Guarda el informe físicamente en el repositorio. No realices nuevas refactorizaciones: prioriza documentar y preservar todo el progreso existente.
````

### Criterios operativos para retomar y cerrar el encargo

Al recibir una instrucción de continuación, Copilot debe aplicar las once secciones originales a **todo el alcance** y preservar las dos decisiones autorizadas. El cierre requiere conjuntamente: revisión de todos los paquetes y subpaquetes; defectos identificados corregidos con regresiones; tests suficientes sin redundancia injustificada ni escenarios ocultos; convenciones y documentación correctas; toda la suite permitida y ejecutable aprobada; Ruff y formato completos; análisis Sonar obligatorio resuelto o limitación pendiente expresada; `DOCS.ps1` completo y contenido generado revisado; integración real entre paquetes; y mediciones pertinentes de optimizaciones conservadas.

No basta con completar el inventario, ejecutar tests parciales, compilar, obtener cobertura, dejar cero tests descubiertos o presentar scripts preparados. Si queda una comprobación obligatoria sin aprobar, el resultado sigue siendo parcial aunque el resto esté terminado. La respuesta final de la revisión original debe respetar el límite de tres líneas indicado por el usuario; este documento exhaustivo fue solicitado después como entregable específico y no está sujeto a ese límite de longitud.

En particular, considerar un diagnóstico Sonar como falso positivo **no equivale a una dispensa autorizada**. Los hallazgos abiertos de la sección 7 siguen pendientes respecto de los criterios de aceptación; describir su limitación con honestidad no convierte el análisis obligatorio en aprobado.

## 2. Estado Git comprobado al congelar el trabajo

```text
Rama: 1.x
HEAD: 036d04bac1381cc4f35c49431bb41a77d18419c3
Último commit: 2026-11-09T23:34:24-05:00
Asunto: 🎨 [test_failure_observation] - Add
```

Inventario previo a crear este archivo, excluyendo la carpeta prohibida mediante pathspec:

| Estado porcelain XY | Rutas | Interpretación |
|---|---:|---|
| ` M` | 1066 | Modificaciones en el directorio de trabajo |
| `M ` | 2250 | Modificaciones ya preparadas en el índice |
| `A ` | 2 | Archivos añadidos al índice |
| `??` | 70 | Archivos nuevos sin seguimiento |
| **Total** | **3388** | No incluye este informe |

`git diff --cached --shortstat` registró **2252 archivos, 19843 inserciones, 17517 eliminaciones**. `git diff --shortstat` registró **1056 archivos, 33822 inserciones, 28855 eliminaciones**. El número de rutas de `status` puede diferir del número de `diff` por metadatos/normalización de Git; no forzar su coincidencia ni interpretar eso como pérdida de cambios.

Hay **2243 rutas modificadas bajo `docs/`**, salida generada versionada. No certifican que la documentación corresponda a las últimas fuentes. Nueve rutas preparadas están fuera de `docs/`: los seis archivos de Aio y sus tres archivos de pruebas (`tests/aio/test_cancellation.py` aparece añadido). No se cambió el staging al redactar el informe. El registro histórico indicaba un árbol inicialmente limpio, pero no existe ya el manifiesto inicial para atribuir de nuevo cada acción de staging; se conserva lo encontrado.

Los 70 archivos sin seguimiento incluyen tres fuentes imprescindibles:

```text
orionis/database/migrations/discovery.py
orionis/localization/validators.py
orionis/support/types/_html.py
```

Los restantes son pruebas nuevas. Una copia que preserve solo `git diff` perderá estos archivos; una copia que preserve solo el índice perderá las modificaciones no preparadas. El apéndice de este informe enumera todas las rutas con su estado y huella de contenido. **No añadir este informe ni otros archivos al índice automáticamente.**

La inspección excluyó el contenido de `tests/real_database/`; no se ejecutó un diff que leyera sus archivos ni se dispone del snapshot inicial. Por ello no se presenta una nueva certificación byte a byte de esa carpeta. La restricción se mantuvo durante este traspaso.

## 3. Estado de los 28 paquetes

“Implementación local cerrada” significa revisión y validaciones locales registradas, no aceptación global ni resolución automática de hallazgos Sonar. Todos necesitan la validación final del estado integrado.

| Paquete | Estado de trabajo al detenerse | Última evidencia funcional histórica / salvedad |
|---|---|---|
| `test` | Implementación local cerrada; revisado primero para confiar en el runner | 192 aprobadas; no confundir fixtures AST con descubrimiento |
| `aio` | Implementación local cerrada | 74 aprobadas y 2 omisiones de uvloop en Windows; las omitidas NO son aprobadas |
| `metadata` y módulos raíz | Implementación local cerrada | 37 aprobadas |
| `background` | Implementación local cerrada | 83 aprobadas |
| `encrypter` | Implementación local cerrada; cambio incompatible autorizado | 59/59 y consumidores de configuración/CLI |
| `hashing` | Implementación local cerrada | 178 aprobadas |
| `environment` | Implementación local cerrada | 223 aprobadas; entorno real protegido |
| `localization` | Implementación local cerrada | 153 aprobadas |
| `logging` | Implementación local cerrada | 193 aprobadas |
| `container` | Implementación local cerrada | 264 aprobadas |
| `introspection` | Implementación local cerrada; Sonar pendiente por S930 | 792 aprobadas |
| `support` | Implementación local cerrada | 1004 aprobadas |
| `failure` | Implementación local cerrada | 183 aprobadas |
| `schemas` | Implementación local cerrada | 586 aprobadas |
| `cache` | Implementación local cerrada | 234 aprobadas |
| `storage` | Implementación local cerrada; Sonar S5332 pendiente | 288/288; 126 casos consumidores HTTP/Schemas |
| `database` | Implementación local cerrada; seguimiento de Queues abierto | 326/326; posteriormente 69 casos del compilador por integración ORM |
| `orm` | Revisión/implementación realizada; cierre funcional compuesto y Sonar pendiente | Baseline 489/489; ejecución 504 con 3 fallos corregidos y rechecks verdes; **505 integradas aún no ejecutadas juntas** |
| `auth` | Implementación local cerrada; Sonar S7503 pendiente | 383/383; ampliación posterior de regresión revalidada por separado |
| `session` | Implementación local cerrada | 260/260; analizadores, ejemplos e imports locales completados |
| `view` | **Parcial: cierre interrumpido** | 189/189 antes de la última regresión; ahora 190 métodos estáticos, calidad/delta/benchmarks finales pendientes |
| `mail` | **Revisión integral no iniciada**; baseline e inventario sí realizados | Baseline consumidor 195/195; preparación de lectura sin cambios |
| `queues` | **Revisión integral no iniciada**; diagnóstico previo parcial | Suite consumidora de base de datos con fallos intermitentes; no declararla verde |
| `realtime` | **No iniciado integralmente** | Solo hipótesis para revisar; no aceptación del paquete |
| `mcp` | **No iniciado integralmente**; cambios de integración/pruebas puntuales | 6 casos consumidores del cifrado; no valida sus 178 métodos estáticos |
| `http` | **No iniciado integralmente**; consumidores puntuales ejecutados | 25 casos de factory con View y otros recorridos; no valida todo HTTP |
| `console` | **No iniciado integralmente**; integración de clave GCM | Casos puntuales de keygen/CLI; no cierre de comandos/scheduling |
| `foundation` | **No iniciado integralmente**; configuración GCM integrada | Casos puntuales de configuración; bootstrap/lifecycle global aún pendientes |

Los inventarios AST actuales de paquetes pendientes son: Mail 32 archivos/195 métodos `test*`; Queues 15/151; Realtime 9/89; MCP 20/178; HTTP 69/970; Console 77/1493; Foundation 26/246. Son **conteos estáticos, no pruebas ejecutadas**. El recorrido AST puede contar fixtures o helpers no descubiertos por el motor.

## 4. Catálogo técnico de defectos, correcciones y archivos

Las subsecciones siguientes se contrastaron con los cambios actuales respecto de HEAD y las regresiones durables. Las correcciones de documentación, anotaciones e imports forman parte del trabajo: en Python 3.14 y el contenedor de Orionis pueden afectar ejecución/reflexión. Un diff voluminoso no implica que todos sus cambios sean funcionales.

### Alcance y procedencia de esta reconstrucción

Reconstrucción realizada el 12 de noviembre de 2026 **solo mediante lectura de git diff HEAD, código y regresiones actuales**. No se modificó implementación, no se ejecutaron pruebas ni se importó el framework para preparar este catálogo. No se inspeccionó tests/real_database/.

Las cifras de ejecución son evidencia histórica heredada de la conversación. Los temporales históricos con logs, harness y manifiestos ya no existen en sus ubicaciones originales; no se verificó su contenido durante el handoff. El inventario AST actual indica definiciones, no ejecución ni descubrimiento real.

### orionis.test y CI

**Archivos funcionales:** .github/scripts/run_tests.py, orionis/test/core/engine.py, orionis/test/cases/case.py, orionis/test/clients/mcp.py y orionis/test/executors/results.py. Los contratos, entidades, enums, provider, pruebas y manuales también tienen cambios de anotaciones, docstrings, formato o expectativas.

- El descubrimiento resolvía rutas relativas desde el directorio de trabajo, podía omitir errores de recorrido y no admitía correctamente un archivo Python individual. Ahora resuelve desde la raíz de la aplicación, exige existencia, rechaza rutas fuera de ella y archivos no Python, ordena el recorrido y propaga errores.
- Se evita usar silenciosamente un módulo homónimo importado desde otro proyecto: compara module.__file__ con el archivo seleccionado.
- _PatternTestLoader aplica el patrón al construir casos, incluyendo métodos con prefijos distintos de test; el ContextVar del patrón se instala y restaura con token durante el descubrimiento. setMethodPattern deja de contaminar el contexto del llamante.
- El wrapper de inyección de TestCase usa functools.partial conservando identidad y detección asíncrona; evita que unittest trate un método seleccionado individualmente como una fábrica de pruebas.
- TestingEngine.run usa asyncio.to_thread para conservar el contexto en el runner.
- La caché JSON deja de sobrescribir ejecuciones del mismo segundo: nombre timestamp-uuid.json, creación exclusiva y escritura fuera del loop.
- El procesador inicializa/restablece el temporizador para soportar errores de fixtures de clase anteriores a startTest. La línea de error se obtiene del traceback suministrado mediante traceback.walk_tb, no de una excepción ambiental que podría haber terminado.
- McpTestResponse.assertOk rechaza resultados ausentes o que no sean mappings, además de errores de protocolo/herramienta. assertTextContains exige bloques type="text" con texto string y estructura válida.
- CI cambió de rglob y exclusión posterior a Path.walk con poda de real_database antes de descender. Propaga errores del walker y selecciona archivos raíz individualmente.

**Regresiones existentes ampliadas:** tests/test/core/test_engine.py, tests/test/cases/test_case.py, tests/test/clients/test_mcp.py, tests/test/executors/test_result_protocols.py, tests/test/executors/test_results.py y tests/test/test_ci_runner.py.

**Precaución fundamental para Copilot:** el propio TestingEngine **no contiene una exclusión especial de tests/real_database**. No recomendar ni ejecutar reactor test --start-dir=tests directamente sobre el proyecto. La exclusión está en el descubridor CI y estuvo reforzada por el harness temporal ahora perdido.

**Estado histórico heredado:** 192 pruebas aprobadas. Inventario AST actual: 12 archivos Python, 193 funciones cuyo nombre comienza con test, incluyendo fixtures/nested; esto **no equivale a 193 pruebas descubiertas ni ejecutadas**.

### orionis.aio

**Archivo funcional:** orionis/aio/loop.py; pruebas tests/aio/test_cancellation.py, tests/aio/test_loop.py y tests/aio/test_package.py; manuales EN/ES de ejecución asíncrona.

- Un llamante cancelado podía abandonar una coroutine, generator coroutine o future devuelta tardíamente por trabajo síncrono.
- Loop.execute conserva el contexto con contextvars.copy_context, usa un future del executor y un marcador de cancelación para impedir ejecutar trabajo que todavía estaba en cola.
- La cancelación del awaiter no mata un hilo ya iniciado. Al completarse, _discardResult libera el awaitable abandonado mediante el helper compartido y observa errores tardíos.
- _reportAbandonedError conserva el error original y lo entrega al runtime central de fallos; sin runtime usa el exception handler del loop propietario. CancelledError no se reporta como fallo.
- Las regresiones cubren coroutine/future/generator coroutine, future en otro loop, error que gana la carrera de cancelación, fallo de limpieza y no ejecución del callable todavía en cola.
- Se eliminaron afirmaciones documentales de coste negligible/essentially free; se describen límites reales de propiedad y cancelación.

**Estado histórico:** 74 aprobadas y 2 omisiones de uvloop en Windows, no 76 aprobadas. Inventario AST actual: 3 archivos, 76 métodos test*.

### Metadata y raíz de orionis

**Archivos:** orionis/__init__.py, orionis/_exports.py, orionis/metadata/framework.py, manuales metadata EN/ES y pruebas.

- Cambios comprobados en los diffs actuales: docstrings, separación/formato y documentación de la identidad/exportación diferida.
- _exports.resolve_export mantiene la resolución lazy y las identidades originales; no se encontró una nueva lógica funcional en su diff.
- No presentar estas modificaciones como una reescritura de la API ni atribuir un defecto funcional inexistente.

**Estado histórico:** 37 aprobadas; inventario AST actual 2 archivos y 37 métodos.

### orionis.background

**Archivo funcional:** orionis/background/task.py; orionis/background/tasks.py recibe principalmente formato. Nuevo tests/background/test_cancellation.py.

- Se centralizó el trabajo síncrono en __executeSync. Tras cancelación espera la finalización del worker mediante complete_on_cancel y libera el awaitable devuelto que ya no será consumido.
- Los fallos de limpieza se observan mediante capture/capture_nowait, conservando la cancelación original.
- Se mantiene el aislamiento operation(..., isolated=True) y la propagación del fallo principal de la tarea. Los errores adicionales de logging se reportan sin sustituirlo.
- Documentación de is_async_callable corregida: detecta declaraciones coroutine/__call__ async; una fábrica síncrona que retorna un awaitable sigue siendo síncrona para el dispatch.
- No se cambió la ejecución secuencial pública de BackgroundTasks.

**Estado histórico y AST actual:** 83 métodos, 6 archivos.

### orionis.encrypter

**Archivo funcional principal:** orionis/encrypter/encrypter.py; integración en configuración de Foundation, config/app.py, .env.reference, generación de claves y CLI. Consultar también el detalle de integración en las demás secciones del informe.

- CBC antiguo no autenticaba el IV y permitía modificar el plaintext sin conocer la clave. **Cambio incompatible autorizado expresamente por el usuario:** AES-256-GCM predeterminado; rechazo de CBC sin autenticación.
- Se conserva únicamente AES-128-GCM/AES-256-GCM para cifrar/descifrar; se usa cryptography.AESGCM, sin criptografía propia.
- Se eliminan ramas de cifrado/descifrado CBC y su padding manual. Constantes de tamaños CBC/PKCS7 y nombres legacy del enum siguen presentes por compatibilidad descriptiva; el generador de claves todavía admite identificadores CBC únicamente para determinar longitud.
- Validación temprana de cipher string y clave bytes inmutable, con longitud exacta.
- Base64 estricto en envoltorio, IV, ciphertext y tag, evitando caracteres ignorados por decodificación permisiva.
- GCM exige nonce de 12 bytes y tag de 16 bytes; manipulación de cualquier campo binario falla autenticación.
- Se eliminaron capturas anidadas redundantes. Los errores públicos dicen Encryption failed / Decryption failed, conservan causa y no incorporan detalles sensibles.
- SecureKeyGenerator.generate ahora tiene default AES-256-GCM.

**Nuevo archivo de regresiones:** tests/encrypter/test_payload_validation.py, con 5 métodos actuales: rechazo CBC, autenticación de cada campo, caracteres Base64 ignorados, claves sin normalizar y tipos inválidos de cipher. La cuenta histórica de +4 nuevos no debe interpretarse como cantidad total de este archivo; el paquete actual tiene 59 métodos.

**Estado histórico:** 59/59 aprobadas. Riesgo obligatorio de handoff: migrar datos CBC existentes antes de actualizar; no restaurar CBC para hacer pasar pruebas antiguas.

### orionis.hashing

**Archivos funcionales:** orionis/hashing/hashers/argon2_hasher.py y orionis/hashing/hashers/bcrypt_hasher.py; otros archivos del paquete actualizan contratos/runtime imports/documentación.

- Carrera entre construcción del backend y setters: un trabajo iniciado con parámetros anteriores podía volver a publicar una instancia obsoleta. Ambos hashers toman snapshots bajo lock, construyen fuera de él y publican solo si los parámetros siguen coincidiendo. Operaciones ya iniciadas pueden terminar con el coste anterior, sin restaurarlo en caché.
- Argon2 valida límites nativos: memory/time 1..2**32-1, threads 1..2**24-1, memory mínima 8 KiB * threads; se rechazan bools. Constructor, overrides y setters mantienen la misma validación; setters inválidos no mutan el estado.
- Argon2 verifica codificación Base64 canónica de salt/hash, sin padding ni bits sobrantes; entradas malformadas requieren rehash en vez de propagar ValueError de check_needs_rehash.
- Bcrypt verifica formato canónico completo, coste 04..31 y bits finales válidos de salt/digest. Conserva prefijos legacy admitidos y el límite de bytes de contraseña.
- BcryptHasher._check transforma ValueError del backend al verificar un hash inválido en False.
- Las anotaciones BoundedExecutor se importan en runtime para introspección/DI. No se reducen costes criptográficos.

**Nuevas regresiones:** tests/hashing/test_cache_concurrency.py, tests/hashing/test_invalid_hashes.py y tests/hashing/test_parameter_validation.py.

**Estado histórico y AST actual:** 178 métodos en 16 archivos.

**Pendiente cruzado:** revisar la configuración Foundation de Argon2 para coherencia con estas validaciones, sin rebajar costes.

### orionis.environment

**Archivos funcionales:** orionis/environment/core/dot_env.py, orionis/environment/dynamic/caster.py, orionis/environment/validators/types.py y orionis/environment/key/key_generator.py; contratos/facade/imports/docstrings/manuales sincronizados.

- Se evita parsear dos veces .env y obtener interpolaciones inconsistentes entre os.environ y all(): una única lectura dotenv_values(stream=...) alimenta la snapshot y el proceso.
- Antes de publicar cualquier entrada se valida el conjunto completo; un error en una entrada posterior ya no deja publicadas las anteriores.
- Se conserva PYTHON_DOTENV_DISABLED: se puede leer la snapshot sin sobrescribir el proceso.
- Un directorio no puede hacerse pasar por un archivo dotenv vacío: lectura explícita mediante open.
- Se validan NUL y el límite Windows de asignación key=value de 32767 unidades UTF-16 **antes** de persistir o tocar caché/proceso.
- set valida/serializa fuera del lock; un __str__ proporcionado por usuario puede leer el entorno sin deadlock.
- Errores de casting/persistencia dejan de incrustar valores sensibles; se suprimen causas concretas cuando su mensaje contenía secretos.
- Prefijos de tipo con espacios/case se reconocen de manera consistente con EnvironmentCaster.
- Booleanos tipados inválidos ya no se convierten silenciosamente a False; ambas rutas usan el mismo vocabulario.
- Se preservan payloads de texto vacíos, Base64 de bytes arbitrarios y conversión bool a int como 0/1.
- Home ~ se expande antes de resolver relativo a cwd.
- Inferencia normaliza subclases a los tipos base admitidos, comprobando bool antes de int.
- Las anotaciones públicas relevantes quedan disponibles en runtime.
- El default GCM del generador pertenece a la aprobación de Encrypter.

**Nuevas regresiones:** tests/environment/test_persistence_regressions.py (8 métodos), tests/environment/test_validation_regressions.py (9 métodos). Cubren interpolación, atomicidad previa a publicación, switch disabled, archivo/directorio, hints, normalización, reentrada, secretos y límites Windows.

**Estado histórico y AST actual:** 223 métodos en 13 archivos.

**Contrato preservado:** DotEnv sigue siendo singleton seleccionado por su primer caller; get lee el proceso y all la snapshot del archivo. No confundir estas fuentes.

### orionis.localization

**Archivos funcionales:** orionis/localization/loader.py, orionis/localization/translator.py y orionis/localization/manager.py; **nuevo fuente sin seguimiento orionis/localization/validators.py**, que debe preservarse. orionis/localization/repository.py principalmente modifica imports/docstrings del comportamiento existente.

- Validación de locale compartida mediante fullmatch; rechaza path components y newline final que podía aceptar ^...$.
- Loader fija la raíz resuelta, valida locales antes de acceder y exige que directorios/archivos/symlinks resueltos permanezcan dentro del directorio configurado.
- availableLocales omite nombres inválidos y enlaces externos.
- Se conserva TranslationFileNotFoundException con causa si el archivo desaparece entre el chequeo y la lectura.
- Interpolación dejaba que valores insertados con :otraClave fueran interpretados nuevamente. Ahora las sustituciones son literales y de una sola pasada; conserva precedencia de nombres largos y variantes raw/capitalized/uppercase. Ruta rápida solo cuando no puede haber sustitución recursiva.
- LocalizationManager publica un único Translator en inicialización concurrente, protegido por lock.
- Runtime annotations de loader, repository, translator y contratos corregidas.

**Nuevas regresiones:** tests/localization/test_loading_regressions.py, tests/localization/test_translation_regressions.py y tests/localization/test_manager_concurrency.py.

**Estado histórico y AST actual:** 153 métodos en 18 archivos.

**No afirmar:** que se haya agregado un locale por-request si el contrato real conserva locale compartido del translator; manuales describen garantías reales.

### orionis.logging

**Archivos funcionales:** orionis/logging/logger.py, orionis/logging/handlers/advanced_rotating_file_handler.py y resolvers hourly/daily/weekly/monthly. queued.py, factory/contratos/provider reciben principalmente imports runtime, normalización de excepciones y documentación; no atribuir como nueva toda su lógica de drain, que ya existía.

- Llamadas públicas podían perder self.__logger entre el chequeo y su uso por un close concurrente. Retienen una referencia estable al logger seleccionado.
- Inicialización, reload y cambio de canal liberan handlers creados pero todavía no publicados si falla configuración. Se separa propiedad provisional de publicada.
- Reload intenta cerrar **todos** los sinks, desacopla handlers y conserva el primer error; errores secundarios se observan sin duplicar los ya reportados por el handler de cola.
- Canal stack respeta rutas absolutas configuradas mediante Path(app_root) / configured.
- Niveles string se resuelven usando logging.getLevelNamesMapping, no getattr(logging, ...), que podía devolver atributos ajenos a niveles.
- Rotación chunked reutiliza el suffix actual hasta alcanzar tamaño: antes el resolver único generaba un archivo por registro.
- Cálculo de bytes usa conteo UTF-8 cuando es exacto y stream.tell() para codecs con BOM/estado; no cuenta un BOM ficticio por mensaje.
- Retención trata archivos planos y comprimidos como elementos independientes; expirar un .log antiguo no elimina su .gz más reciente.
- Compresión publica un archivo completo desde temporal con rename; un fallo no destruye un archivo .gz previo. Limpieza del temporal se observa sin reemplazar el fallo original.
- Resolvers calendario convierten datetimes aware al timezone configurado; naive se interpreta allí. Weekly/monthly permiten la próxima hora de rotación en el período actual si todavía no ocurrió, en lugar de saltar siempre a semana/mes siguiente.
- Hints públicos de handlers/factory/queued resolubles.

**Nuevas regresiones:** tests/logging/test_handler_regressions.py, tests/logging/test_lifecycle_regressions.py y tests/logging/test_rotation_regressions.py.

**Estado histórico y AST actual:** 193 métodos en 16 archivos.

### orionis.container

**Archivos funcionales:** orionis/container/container.py, orionis/container/context/manager.py, orionis/container/entities/invocation.py y orionis/container/facades/meta.py; contratos, scope, facades/provider y manuales sincronizados.

- Allocation singleton publicaba instancia antes de concluir su inicialización; constructor concurrente podía reinitializar registros y perder bindings. __init__ usa el mismo lock y doble chequeo de inicialización.
- Detección de ciclos usa (id(container), concrete); evita falsos ciclos cuando otro contenedor independiente resuelve el mismo tipo dentro del mismo contexto.
- Una instancia explícita del scope tiene precedencia sobre singleton global ya caliente; al salir del scope vuelve a quedar visible el singleton.
- Instancias primitivas registradas en scope participan en la inyección.
- InvocationPlan conserva nombres positional-only; __resolveSignature no roba sus nombres del mapping de keywords, respetando el binding Python y **kwargs.
- Resolución compartida de parámetros ausentes elimina duplicación entre positional y keyword-only sin cambiar rutas centrales de DI/schema.
- Constructor plan trata correctamente descriptores y referencias deferred de clases; invalidación de reflection borra los planes derivados mediante callback registrado.
- ScopeManager.get no sobrescribe un reemplazo ni repuebla un scope limpiado mientras esperaba una Task; rechaza publicación tras cerrar el scope.
- Limpiar/reemplazar valores cierra únicamente coroutines nativas **no iniciadas**. No cancela tareas prestadas ni coroutines en ejecución, cuya propiedad pertenece al caller.
- Facades no inventan atributos de protocolo __dunder__ ausentes: lanzan AttributeError, permitiendo introspección correcta.
- Caché de dispatchers deja de ser dict ilimitado; lru_cache(maxsize=1024) permite liberar clases desalojadas. Se conserva dispatch awaitable/async-context-manager.
- Runtime hints corregidos, incluido retorno real bool | None de __aexit__.

**Nuevas regresiones:** tests/container/test_initialization_concurrency.py, tests/container/test_resolution_context.py, tests/container/test_resolution_regressions.py, tests/container/test_scope_regressions.py y tests/container/test_facade_regressions.py.

**Estado histórico y AST actual:** 264 métodos en 23 archivos.

**Limitación documentada:** constructor base protege sus registros; subclases siguen siendo responsables de inicializar su estado adicional de forma segura.

### orionis.introspection

**Archivos funcionales:** orionis/introspection/dependencies/reflection.py, orionis/introspection/abstract/reflection.py, orionis/introspection/concretes/reflection.py, orionis/introspection/instances/reflection.py, orionis/introspection/callables/reflection.py, orionis/introspection/modules/reflection.py, orionis/introspection/modules/inspector.py y orionis/introspection/reflection.py; contratos/entities/hints/manuales actualizados.

- Python 3.14 evalúa anotaciones diferidas nativas: NameError de una referencia desconocida ya no impide inspeccionar todo el objeto. Se usan annotationlib.get_annotations(..., Format.FORWARDREF) e inspect.signature(..., annotation_format=Format.FORWARDREF) como fallback.
- Se preservan tipos conocidos y ForwardRef para desconocidos; el contenedor puede invocar/build con argumentos explícitos aunque otra referencia no esté disponible.
- Ya no se excluyen dependencias por llamarse literalmente self/cls. La eliminación del receptor depende de binding real del descriptor; parámetros de usuario con esos nombres se conservan.
- Callables sin hash se inspeccionan sin entrar en las cachés LRU que requieren claves hashables.
- clearCache invalida firmas compartidas y planes derivados de Container. Actualiza defaults, firmas explícitas, hints, nombres/docstrings y metadatos cambiados.
- Name mangling solo reconoce el prefijo privado completo correspondiente; no elimina coincidencias parciales del nombre de clase. Se conservan nombres privados declarados al refrescar la identidad.
- Valores de atributos None pueden eliminarse; no se confunden con no existe.
- Métodos inyectados se descubren/eliminan y su mutación refresca cachés.
- Clasificación de métodos especiales excluye data descriptors.
- Instancias con __slots__ conservan acceso a valores y atributos privados sin mangling explícito.
- Clases de usuario no se clasifican como builtins/typing solo por compartir sus nombres.
- ReflectionAbstract valida tipo de entrada y actualiza abc.update_abstractmethods después de modificaciones; eliminar un método abstracto refresca la abstracción real de Python.
- Cambios de propiedades o atributos del módulo invalidan todas las vistas categorizadas, no solo una.
- ModuleInspector.loadClass usa el módulo de sys.modules pero obtiene su atributo clase actual; se elimina caché paralela obsoleta de clases.
- Inspección de imports usa tokenize.open, respetando codificación fuente Python.
- discoverModules permite directorio opcional ausente, pero propaga errores en directorios existentes; poda caches/venvs y rechaza target fuera de la raíz.

**Nuevas regresiones:** tests/introspection/abstract/test_regressions.py, tests/introspection/test_binding_regressions.py, tests/introspection/test_cache_invalidation.py, tests/introspection/test_callable_regressions.py, tests/introspection/test_deferred_annotations.py, tests/introspection/test_member_regressions.py y tests/introspection/test_module_regressions.py.

**Estado histórico y AST actual:** 792 métodos en 24 archivos.

**Sonar histórico pendiente, no limpio:** S930 sobre el argumento válido annotation_format=Format.FORWARDREF, por reconocimiento desactualizado de Python 3.14. No quitar el argumento ni desactivar regla para simular aprobación.

### Notas transversales de preservación para este grupo

- Las cifras de ejecución anteriores son **evidencia histórica heredada de la conversación**, no ejecuciones efectuadas al preparar el handoff. Los directorios temporales de logs/harness ya no existen, por lo que no se verificaron sus contenidos hoy.
- La inspección AST actual confirma cantidades de definiciones, pero no certifica descubrimiento, resultado, ausencia de skips ni integración.
- Mantener los nuevos archivos **untracked**, no solo el diff de archivos indexados. En este subconjunto destaca orionis/localization/validators.py como fuente nueva.
- Anotaciones sacadas de TYPE_CHECKING son necesarias para reflexión/DI en runtime; una limpieza automática podría reintroducir NameError o ciclos.
- Las cabeceras Ruff incluyen justificaciones explícitas para contratos públicos, tipos dinámicos y capturas coordinadas. La migración global de per-file-ignores permanece pendiente según el estado heredado.
- No se ha hecho una validación global posterior al conjunto integrado ni al cambio final de View. No declarar todos estos paquetes certificados en el estado final global; describirlos como **revisión local cerrada históricamente, pendiente revalidación final integrada**.

### Evidencia y alcance de esta reconstrucción

Reconstrucción **solo de lectura** de Support, Failure, Schemas, Cache, Storage y Database. No se ejecutaron pruebas, importaciones de Orionis, formateadores ni modificaciones del framework durante la preparación de este catálogo; tampoco se leyó `tests/real_database/`. Se contrastó el código actual y los cuerpos funcionales frente a `HEAD`. Las cifras de regresiones nuevas siguientes son **conteos AST, no ejecuciones**.

Dos fuentes nuevas sin seguimiento especialmente importantes:

- `orionis/support/types/_html.py`: implementación de `_TagStripper` basada en `HTMLParser`.
- `orionis/database/migrations/discovery.py`: descubrimiento común de migraciones y seeders con validación de identidad y nombres persistidos.

Regresiones nuevas actualmente presentes:

| Paquete | Archivos nuevos | Métodos nuevos |
|---|---:|---:|
| Support | 8 | 37 |
| Failure | 4 | 22 |
| Schemas | 3 | 28 |
| Cache | 3 | 19 |
| Storage | 4 | 37 |
| Database | 4 | 32 |

Los conteos no incluyen escenarios `subTest` ni correcciones de pruebas existentes. Los temporales históricos de revisión y Sonar ya no existen en las rutas heredadas; sus resultados se deben consignar como **evidencia histórica registrada en la conversación**, distinguiéndola de artefactos disponibles.

### Support: cambios funcionales confirmados

#### Colecciones

Archivos: `orionis/support/types/collection.py`, `orionis/support/types/contracts/collection.py`.

- Se conserva un diccionario vacío como diccionario; `items or []` lo convertía en lista.
- `pull()` de índice/clave ausente devuelve `None` sin intentar borrar ni alterar otros elementos.
- `random(0)` respeta el contrato de muestreo de cero elementos; antes entraba en la rama de un único elemento por usar truthiness.
- `mapInto()` transmite los argumentos nombrados al constructor, además de a las factorías nombradas.
- Los consumidores de colecciones aceptan el contrato `ICollection`, no solo la clase concreta.
- Agregados `avg`, `min`, `max`, `sum` distinguen «no se pidió selector» de «el selector no produjo valores»; no recuperan accidentalmente todos los datos originales.
- `__getValue()` distingue `None` de claves válidas falsy.
- Muestreo con `SystemRandom`; tipos públicos `all()`/constructor reflejan listas y diccionarios reales.
- Prueba nueva: `tests/support/test_collection_regressions.py` — 6 métodos.

#### Strings

Archivos: `orionis/support/types/stringable.py` y nueva `orionis/support/types/_html.py`.

- Reemplazos literales y delimitadores con barras invertidas ya no se interpretan como escapes de sustitución de regex.
- Reemplazo secuencial opera sobre ocurrencias originales sin volver a reemplazar texto recién insertado.
- `replaceMatches()` respeta límite cero y rechaza límites inferiores a `-1`.
- Sufijos vacíos no borran todo el texto.
- `scan()` escapa los literales del formato y conserva capturas completas; reconoce los placeholders soportados `%s`, `%d`, `%f`.
- Comparación de patrones sensible a mayúsculas es estable en Windows mediante `fnmatchcase`.
- Iterables de patrones de una sola pasada no se consumen dos veces.
- ULID exige alfabeto ASCII y rango efectivo de 128 bits, incluyendo límite superior válido.
- `toDate(None)` usa ISO, conserva offset explícito y aplica zona configurada solamente a fechas naïve.
- `stripTags()` procesa delimitadores dentro de atributos entrecomillados y respeta allowlist de etiquetas mediante `HTMLParser`; **no es sanitizador HTML y conserva atributos de etiquetas permitidas**.
- `substr`/`substrCount` normalizan offsets negativos antes de aplicar longitud.
- `substrReplace()` se descompone en validación/normalización y reemplazo acotado; se conserva contrato de inserción cuando longitud es `None`, cero u omitida.
- `isAscii()` aprovecha `str.isascii`; helpers de pluralización y comparación estructural sustituyen complejidad/supresiones previas.
- MD5/SHA1 quedan explícitamente como hashes no destinados a seguridad (`usedforsecurity=False`), sin `NOSONAR`.
- `encrypt`/`decrypt` mantienen el retorno real `str`; se corrigen anotaciones/documentación que prometían `Stringable` o una implementación ficticia.
- Prueba nueva: `tests/support/types/test_stringable_regressions.py` — 12 métodos.

#### Entidades, grafos y tipos

- `orionis/support/entities/base.py`: metadatos de campos pasan a ser propiedad de cada clase, consultando su propio `__dict__`; elimina retención global de clases dinámicas y ciclos por anotaciones autorreferentes, evita reutilizar campos del padre. `_default_value()` centraliza evaluación/serialización real de defaults.
- `orionis/support/structures/freezer.py`: recorrido del grafo resuelve descendientes compartidos independientemente del orden; los ciclos de mappings conservan identidad mediante proxies inmutables; ciclos solo de secuencias que no pueden representarse como tuplas inmutables se rechazan en lugar de exponer intermediarios mutables.
- `orionis/support/types/dot_dict.py`: `get(default)` no inserta el default; copia profunda preserva referencias compartidas y cierra ciclos sobre el nuevo mapping.
- `orionis/support/types/sentinel.py`: `MISSING` conserva identidad mediante copy/deepcopy/pickle.
- `orionis/support/types/uniqueness.py`: anotaciones runtime y separación del cálculo de claves; conserva fallback por igualdad para valores personalizados/cíclicos/no hashables pequeños.
- Nuevas pruebas: `tests/support/test_freezer_regressions.py` (3), `tests/support/test_utility_regressions.py` (5), `tests/support/types/test_type_regressions.py` (5), `tests/support/test_runtime_annotations.py` (1).

#### Runtime y facades

- `orionis/support/facades/datetime.py`: cambios de timezone/locale son atómicos ante rechazo; `isToday()` usa el día calendario configurado; `formatLocal()` convierte zona y utiliza locale.
- `orionis/support/patterns/singleton/meta.py`: construcción recursiva falla de forma recuperable en lugar de bloquearse.
- `orionis/support/system/workers.py`: presupuestos finitos muy grandes se convierten usando `as_integer_ratio`, evitando overflow de un producto flotante intermedio.
- `orionis/support/inspirational/inspire.py`: fallback válido cuando el consumidor vacía la lista suministrada.
- `orionis/support/concurrency.py`: `close_abandoned_awaitable()` y `_cancel_abandoned_future()` liberan awaitables abandonados respetando su loop propietario; cancelación se agenda en el loop correspondiente, resultados ya fallidos se observan y excepciones de cleanup se entregan al observador.
- Stubs de facades ajustados a contratos reales, imports y docstrings; **esto no certifica revisión completa de Mail/MCP/Queues/Realtime/Console**.
- Nuevas pruebas: `tests/support/facades/test_regressions.py` (4), `tests/support/inspirational/test_regressions.py` (1).

### Failure: cambios funcionales confirmados

Archivos centrales: `orionis/failure/runtime.py`, `orionis/failure/entities/handling.py`, `orionis/failure/base/handler.py`; además contratos, entidades, provider, catch y manuales bilingües.

- `FailureHandling.complete()` y `present()` detectan reentrada del mismo task antes de esperar su propio lock: error explícito en vez de deadlock.
- Las repeticiones de una operación fallida conservan identidad y causa de la excepción y restauran el traceback original, sin acumular frames de consumidores anteriores.
- `toThrowable()` conserva el mensaje nativo, excepciones con `__str__` personalizado y número de argumentos; el log diferido usa el traceback original.
- Shutdown rechaza trabajo nuevo hasta restart explícito, también bajo eager task factories.
- Restart externo espera el shutdown compartido; reentrada desde cleanup propietario falla pronto.
- Varias esperas de shutdown comparten el cierre; cancelación de un waiter no vuelve a cancelar cleanup ajeno.
- Se retienen/esperan tareas creadas por `finally` durante shutdown y recursos de trabajo cancelado.
- Los control signals no entran indebidamente en reporte standalone/callback; grupos mixtos se conservan intactos.
- Vínculos causales se resuelven por identidad, sin evaluar truthiness personalizada de excepciones.
- Contextos heredados de operaciones ya cerradas no suministran metadatos obsoletos a tareas tardías.
- Lookup/deduplicación de grupos profundos de excepciones evita recursión Python que podía desbordar la pila.
- Si falla el scheduling en loop/hilo, se liberan claims y wrappers propios; no se cierra el awaitable original que aún pertenece al llamador cuando la admisión falla.
- La cancelación del future de entrega de un hilo no abandona cleanup que sigue en el loop.
- Al terminar la entrega, no se retienen innecesariamente la aplicación y el trabajo original por conservar un receipt future.
- Un wrapper sin iniciar sigue siendo responsable de esperar el task previamente admitido que adoptó.
- Los guards de reentrada de startup/shutdown/drain también se respetan durante cleanup adoptado.
- Anotaciones públicas y de constructores generados disponibles en runtime.

Nuevos archivos/métodos:

- `tests/failure/test_contract_regressions.py` — 3: anotaciones, reentrada de efectos, traceback/identidad.
- `tests/failure/test_handler_regressions.py` — 2: mensajes/argumentos y log original.
- `tests/failure/test_runtime_regressions.py` — 10: lifecycle, cancelación, control signals, contexto, grupos, anotaciones.
- `tests/failure/test_scheduling_regressions.py` — 7: ownership en admisión/rechazo, cleanup y liberación de referencias.

### Schemas: cambios funcionales confirmados

#### Validación efectiva de instancias y anotaciones

- `orionis/schemas/coercion.py`, `orionis/schemas/instance_payload.py`: instancias existentes de `msgspec.Struct` se expanden antes de conversión nativa para revalidar campos que constructores/mutaciones pudieron dejar inválidos; aplica también cuando la raíz es mapping y las instancias aparecen dentro de contenedores.
- Se preserva validación estricta de escalares sin marca `Coerce`.
- Preparación usa copy-on-write; fast path de colecciones homogéneas evita reconstrucción si no existen instancias por expandir.
- `orionis/schemas/schema.py`: compila constraints también para namespaces con `__annotations__` explícito y modo future/string de Python 3.14, no solamente `__annotate_func__`.
- `orionis/schemas/compiler.py`: descomposición de validación de conflictos conserva restricciones numéricas, longitudes, timezone y valores individuales.
- `orionis/schemas/constraint_plan.py`: caché antes ilimitada pasa a LRU de **1024** planes, protegida por `RLock`; mensajes locales residen en el metadata de la anotación, sin registro global ilimitado.
- `orionis/schemas/instance_payload.py` usa `WeakKeyDictionary` con planes sin referencias fuertes al tipo.
- `orionis/schemas/exception_parser.py` y `orionis/schemas/failure_collector.py`: metadatos pasan a pertenecer a cada clase; se evitan retenciones globales de tipos dinámicos/recursivos y de claves arbitrarias provenientes de solicitudes.

#### Errores

- `ValidationException` acepta el contrato Sequence declarado y conserva identidad/orden de failures.
- Summary vacío explícito no se reemplaza por errores de campos.
- Parsing de errors nativos conserva el leaf ausente y su padre real.
- Palabras dentro de regex/texto citado no alteran clasificación del error.
- Nombres encoded con puntuación conservan nombre original.
- Rutas ambiguas de unions no toman el mensaje de otra rama.

#### Reglas

- Reglas textuales pertinentes usan match completo; rechazan newline final antes aceptado por `$`.
- `MaxDigits` valida signo/dígitos antes de contarlos.
- Enteros por encima del límite de conversión decimal de Python no necesitan modificar el límite global para validarse.
- ULID rechaza expansiones Unicode.
- `measure()` conserva precisión `Decimal`; NaN decimal produce comparación inválida sin disparar una excepción de señalización.
- Encoding rechaza uploads ilegibles.
- Lectura síncrona de upload se drena mediante `complete_on_cancel` antes de devolver cancelación; el stream sigue siendo del llamador.
- `orionis/schemas/rules/image_probe.py`: validación de headers PNG/BMP/WebP/JPEG, tamaños de segmentos/chunks y dimensiones positivas; soporta correctamente layouts BMP compacto/WebP lossless existentes.
- Reglas temporales rechazan strings no parseables.
- Dimensions rechaza ratios NaN/infinito.
- JSON rechaza Unicode no codificable sin filtrar excepción del encoder.

Nuevas pruebas:

- `tests/schemas/test_core_regressions.py` — 7.
- `tests/schemas/test_error_regressions.py` — 9.
- `tests/schemas/test_rules_regressions.py` — 12.

**Pendiente fuera del paquete ya revisado:** examinar si MCP y Realtime atraviesan `Validator`/`Coerce` correctamente; el arreglo de Schemas no certifica que esos consumidores no llamen directamente a `msgspec.convert`.

### Cache: cambios funcionales confirmados

- `orionis/cache/repository.py`: `_getCached()` distingue null serializado de ausencia aun con el comportamiento default de aiocache; `remember`, `rememberOnce` y `pull` lo usan.
- `rememberOnce`: propietario `_Resolution` con estado `active`; un child task que heredó contexto puede resolver después de finalizar el propietario original sin falso error recursivo.
- `orionis/cache/cache_manager.py`: publicación única del repositorio por store ante resolución concurrente.
- `orionis/cache/locks/lock.py`: cancelación durante adquisición de lease DB intenta liberar el owner aun si el commit ocurrió antes de recibir confirmación; cleanup conserva error primario.
- Los eventos globales de RedLock para backends de memoria se aíslan por identidad del backend; dos instancias independientes con la misma clave no se notifican erróneamente.
- `orionis/cache/stores/memory.py`: `_MemoryCache._clear()` cancela timers antiguos antes de reutilizar claves; evita que un timeout anterior borre el valor nuevo.
- `orionis/cache/stores/file.py`: `add` serializa/escribe en staging y publica atómicamente bajo lock; un fallo no deja entrada parcial ocupando la clave.
- TTL persistente usa **Unix epoch (`time.time`)**, antes monotonic no válido entre reinicios.
- Envelopes sin `v`, tipo inválido de expiration u otras estructuras malformadas se tratan como misses, preservando null explícito.
- Operaciones de archivo se drenan antes de propagar cancelación; batches terminan operación activa y paran antes de la siguiente.
- `orionis/cache/stores/database.py`: eliminar una fila expirada comprueba que sigue expirada, preservando renovación concurrente.
- Fallo de inserción no se reporta como éxito si retry update no encuentra fila; adquisición de lock distingue contención real de fallo sin fila rival.
- `orionis/cache/file_based_cache.py`: filename simple no vacío, sin traversal/separadores/colon/NUL; ruta relativa se fija al construir.
- Artefacto con JSON válido pero envelope inválido se reconstruye en lugar de provocar errores de estructura.
- Fingerprint de fuentes admite timestamps previos a epoch con entero firmado de 128 bits.
- `orionis/cache/serializer.py`: resolución de clases anidadas y valores typed de Enum recursivamente decodificados.

Nuevas pruebas:

- `tests/cache/test_artifact_regressions.py` — 5.
- `tests/cache/test_manager_regressions.py` — 6.
- `tests/cache/test_store_regressions.py` — 8.

Límites/riesgos:

- Entradas persistidas con deadlines monotonic **no se migran**; se regeneran al miss, según manual actualizado.
- Deadline epoch depende del reloj de pared.
- `cache.lock()` con file coordina solo el mismo loop/directorio; no confundirlo con los locks de escritura file entre procesos.
- RedLock es un lease, sin fencing ni renovación automática; expirar no cancela código del propietario.
- No afirmar certificación de Memcached/Redis remotos reales por pruebas con dobles. El historial específico de Redis controlado debe distinguirse de las comprobaciones actuales, que no se ejecutaron al elaborar el informe.

### Storage: cambios funcionales confirmados

Archivos centrales: `orionis/storage/buffering.py`, `orionis/storage/drivers/functions.py`, los cinco drivers (`local`, `memory`, `s3`, `gcs`, `azure`), `orionis/storage/stream.py`, `orionis/storage/uploaded_file.py`, `orionis/storage/file.py`, `orionis/storage/manager.py`, contratos y manuales.

#### Propiedad y cancelación

- Cancelación espera workers activos de lectura/escritura/avance de iterador/cierre antes de liberar buffers prestados o propios.
- Fallo del destino cierra el iterador que posee la operación; no cierra arbitrariamente la fuente del usuario.
- Spool valida límites de memoria antes de consumir la entrada.
- Chunk vacío de un iterable se conserva; no se confunde con fin de iteración.
- Fallos de cleanup dependen del error de la operación propietaria, no de `sys.exception()` ambiental heredado de un `except` ajeno.
- Context manager de stream conserva excepción del cuerpo si publicación/cierre falla y observa el secundario centralmente.
- Spool asignado se cierra si bootstrap SDK o download falla.

#### Semántica de drivers

- `_ModeBuffer` aplica permisos reales `rb/wb/ab/rb+/wb+/ab+`, también mediante métodos heredados de `BufferedIOBase`; append escribe al final incluso tras seek atrás.
- Move a la misma ruta normalizada no elimina contenido, tanto memoria como remotos.
- Valores de visibility se validan antes de consumir input, iniciar SDK o modificar datos.
- Chunk size inválido se rechaza aun para archivos vacíos; Azure lo valida antes de construir downloader.
- XOF/digests que requieren longitud explícita se rechazan; se conservan hashes de longitud fija por streaming.
- Inicialización concurrente de SDK publica un cliente por driver.
- S3 reconoce errores parciales de `delete_objects` y no devuelve éxito de borrado total.
- Resolución concurrente de discos publica uno y permite factories anidadas.
- Rename/storeAs rechaza nombres `.`/`..` que podrían resolver segmentos de directorio.
- Se conservan campos públicos camelCase de `FileInfo` por aprobación expresa del usuario de S116.

#### Local filesystem

- `PermissionError` y otros errores reales de read/open/stat/listado no se convierten en «ausente» o lista vacía.
- Errores al clasificar hijos o escanear recursivamente abortan el resultado parcial y conservan causa.
- Symlinks/junctions que llevan fuera del root se rechazan; el scan poda antes de entrar al árbol externo.
- Fallo de publicación elimina staging y conserva target anterior.
- Rename denegado no activa fallback de copy/delete; fallback se reserva a condiciones pertinentes.
- Archivos ordinarios terminados en `.tmp` sí se listan; solamente se ocultan nombres internos de staging reconocibles.

Nuevas pruebas:

- `tests/storage/drivers/test_remote_regressions.py` — 12.
- `tests/storage/test_api_regressions.py` — 6.
- `tests/storage/test_local_edges.py` — 6.
- `tests/storage/test_resource_regressions.py` — 13.

**Límites importantes:** pruebas de SDK con dobles no certifican proveedores remotos. Defensa traversal/junction no equivale a promesa de filesystem transaccional universal. `stripTags` de Support tampoco convierte automáticamente contenido HTML de consumidores en seguro.

### Database: cambios funcionales confirmados

#### Conexiones, propiedad y errores

- `orionis/database/connection.py`, `orionis/database/transaction.py`, `orionis/database/threaded/{connection,engine,result,worker}.py`: error primario de consulta/transacción conserva identidad/causa cuando rollback, materialización, cursor close, checkout release o reportes secundarios también fallan.
- Rollback fallido invalida checkout antes de devolverlo al pool, evitando reintentos de reset que expongan SQL/bindings por logs de SQLAlchemy.
- `_diagnostic_error()` sanea errores tardíos de driver antes de observación central.
- Cleanup exitoso no hereda una excepción ambiental ajena; cleanup que falla sin error propio previo sí se propaga.
- Cierres concurrentes comparten una operación de shutdown/release y esperan todo trabajo/cleanup perteneciente al worker.
- Close no adelanta cleanup de un resultado que llegó después de cancelación.
- `orionis/database/connection_manager.py`: lock para publicación única por nombre; default conserva key exacta configurada, con fallback legacy lowercase; disconnect de todas las conexiones espera todas y conserva el primer fallo.

#### Compilación/configuración

- `orionis/database/dialect.py`: contraseñas vacías o con espacios significativos se preservan en URL de conexión; parámetros de conexión no se normalizan como texto cosmético.
- Startup options sync de PostgreSQL escapan correctamente search_path como un argumento.
- `orionis/database/compiler.py`: valida forma de columnas de todas las filas en batch insert; no acepta silenciosamente bindings desconocidos.
- Planes UNION anidados conservan todas las ramas en `IN`, joins, expresiones escalares y `EXISTS`.
- Agregación sobre UNION usa relación derivada; follow-up desde ORM corrigió interacción de agregados/HAVING/arity.
- Referencias adelantadas de varias foreign keys al mismo destino conservan todas las columnas referidas.
- Anotaciones de compiler/dialect/Redshift y contratos disponibles en runtime.

#### Schema/migraciones/seeders

- Columnas duplicadas se rechazan antes de sustituir silenciosamente una declaración.
- Primary key vacía falla al declararla.
- `Blueprint.__getattr__` expone solamente factories de columnas; utilidades heredadas de tipos no se presentan como factories.
- `TableCreation` rechaza entradas solapadas y consume una declaración exitosa una sola vez.
- `orionis/database/migrations/context.py`: binding con propietario activo; un child task descarta selección heredada después de cerrar el scope.
- Nueva `orionis/database/migrations/discovery.py`: usa `ModuleInspector`/`ReflectionModule`, propaga errores reales de traversal/import, ignora package initializers, conserva clases propias del módulo, deduplica aliases de la misma clase y rechaza clases distintas con el mismo nombre persistido.
- Migrator/seeder publican resultado de discovery completo en vez de caché parcial.
- `orionis/database/migrations/events.py`: fallos de report/progress no reemplazan error de la ejecución.
- `orionis/database/seeders/runner.py`: fallo del recovery read conserva el error del claim original y su causa.

Nuevas pruebas:

- `tests/database/test_compilation_regressions.py` — 5.
- `tests/database/test_connection_regressions.py` — 14.
- `tests/database/test_schema_regressions.py` — 12.
- `tests/database/test_seeder_recovery.py` — 1.

**Pendiente de revisión global:** Queue mostró fallos intermitentes de pool timeout/SQLite busy/WinError32 en ejecuciones históricas. El profiling identificó fuerte overhead de `asyncio` debug/traceback/stat, pero **no demostró que todos los fallos fueran exclusivamente del entorno**. No omitir pruebas ni aumentar timeouts para declararlas aprobadas. No se ejecutaron bases reales dentro de `tests/real_database/`.

### Cambios transversales observados en estos seis paquetes

- Imports runtime necesarios para `get_type_hints`, inyección y reflexión en Python 3.14.
- Nombres de helpers internos, docstrings NumPy y retornos reales; eliminación de `NOSONAR` y traslado de dispensas Ruff explícitas a cabeceras donde procede.
- Manuales EN/ES actualizados para describir garantías reales, límites de leases, cancelación, ownership, persistencia y errores; no confundirlos con salida HTML generada.
- Pruebas antiguas fueron consolidadas/fortalecidas además de los archivos nuevos. El número de métodos no representa pérdida automática de escenarios.
- Las sumas históricas de cada paquete y aprobaciones Ruff/Sonar/Pydoctor figuran en la sección de evidencias del informe principal; este trabajo de handoff **no reejecutó ninguna validación**.

Verificación de este bloque: lecturas, `git diff HEAD` y AST. No se ejecutó Orionis, pruebas, Ruff, Sonar ni documentación durante la preparación del traspaso y no se modificó código.

### Corte real de View

**View permanece parcialmente completado.** Están físicamente presentes las dos últimas modificaciones que quedaron en curso:

- `orionis/view/globals/url.py` contiene `_split_scheme()`: usa `partition("://")`, convierte únicamente el esquema a minúsculas para reconocer HTTP/HTTPS y conserva exactamente el resto. `_absolute_url()` reconoce esquemas HTTP(S) con cualquier combinación de mayúsculas; `_to_secure_url()` eleva HTTP y URLs relativas al protocolo a HTTPS, sin normalizar otras partes.
- `tests/view/test_global_regressions.py` contiene **6 métodos**, incluido `testHttpSchemeRecognitionIgnoresCaseAndPreservesTheRemainder()`. Comprueba `url`, `secure_url`, `secure_asset`, origen HTTP de la petición, esquema HTTPS existente, mayúsculas, puerto, escapes, query/fragmento y otros esquemas/rutas que deben permanecer intactos.
- `tests/view/test_engine_regressions.py` conserva **4 métodos**. El cuarto verifica `IViewEngine.warmup` como coroutine no abstracta y ejecuta el método base sobre un motor real, esperando `None` sin cargar plantillas.
- El último resultado histórico integrado **189/189** no certifica el actual conjunto **190** ni el último cambio de URL. El antiguo mensaje del agente confirmó el rojo de 11 subcasos y anunció un verde en curso; no recibimos su terminación. El test ampliado de `warmup` sí tuvo mensaje histórico explícito de **4/4**, 0 accesos protegidos.
- Los benchmarks de View y el probe de imports fríos estaban preparados, pero no hay resultado final comprobado. El probe acababa de arrancar cuando se interrumpió la revisión. No presentar ninguno como aprobado.
- Tampoco certificar un delta final de Sonar tras `_split_scheme`: el último Sonar completo disponible en memoria era 54 archivos, con S7503 y dos S5332. Aunque desaparecieron los literales que originaban S5332, falta evidencia del análisis final sobre el código actual.

### Correcciones ORM conservadas

Archivos y causas funcionales comprobables en el diff:

- `orionis/orm/state.py`: `syncOriginal()` prepara el snapshot antes de sustituir el anterior; un fallo de deepcopy conserva el estado previo. Detección de cambios distingue atributos ausentes sin comparar valores de usuario contra el sentinel.
- `orionis/orm/metaclass.py`: reutilizar una declaración de columna entre modelos ya no modifica el nombre ligado en el modelo anterior. Resolución de columnas pendientes/deleted y metadatos ajustada.
- `orionis/orm/model.py`: persistencia e hidratación conservan la conexión y el manager realmente propietarios; eventos de escritura exitosa dependen de que exista una escritura real. Métodos de inserción, actualización, borrado y force-delete ajustados.
- `orionis/orm/query/base_builder.py`, `query/builder.py`, `query/raw_builder.py`, `query_builder.py`: conservar manager/conexión adoptados; respetar conexión explícita y hooks de modelos; preparar subconsultas con scopes y política de soft-delete; no mutar el plan reusable cuando un scope falla; `exists()` preserva proyecciones necesarias para HAVING/consultas compuestas.
- La corrección de agregados sobre todas las ramas de UNION también necesitó el compilador de `orionis.database`, por lo que no debe revertirse aisladamente.
- `orionis/orm/relations/belongs_to_many.py`: atributos adicionales del pivot no pueden sustituir sus claves; carga eager conserva orden y cardinalidad de lazy; selección de conexión y extracción de identificadores corregidas.
- `orionis/orm/relations/relation.py`: supresión contextual de constraints con propiedad temporal que no permanece utilizable por contextos hijos tras cerrar el propietario.
- `relations/mixin.py` y `has_one_or_many.py`: relaciones heredan la conexión de lectura del padre salvo destino explícito; creación del relacionado conserva destino.
- `soft_deletes.py`: eventos de restore/force-delete coherentes con la escritura.
- `schema/types/{large_binary,numeric,strict_decimal,string_type}.py`: rechazar booleanos en longitudes/precisiones donde `bool` pasaba como `int`.
- `contracts/belongs_to_many_relation.py`: `getResults()` documenta/anota correctamente la colección; helper de pruebas de contratos admite covarianza nominal válida, sin convertir `Any`, genéricos incorrectos o anotaciones ausentes en éxito.
- Restauración de anotaciones utilizables en runtime, imports compatibles con 3.14, docstrings, cabeceras Ruff, exportaciones y manuales bilingües.
- `factories/fake.pyi`: firmas sincronizadas con Faker instalado. `postalCode` y `postalcode` son APIs distintas del proveedor y deben conservarse; de ahí los dos S1845 conocidos.

Regresiones nuevas presentes:

- `tests/orm/test_model_regressions.py`: 7 métodos: fallo de snapshot conserva original; sentinel ausente; columnas reutilizadas; filas desaparecidas sin eventos de éxito; manager propietario; conexión de modelos hidratados; anotaciones públicas.
- `tests/orm/query/test_query_regressions.py`: 7: subqueries con scopes/soft-delete; planes no modificados siguen prestados; reintento tras scope fallido; exists con HAVING/compound; agregados de UNION; hooks/conexión explícita; anotaciones.
- `tests/orm/relations/test_pivot_regressions.py`: 5: claves pivot protegidas; orden/cardinalidad eager; conexión padre; hijo sin lease de constraints vencido; anotaciones.
- `tests/orm/schema/test_schema_regressions.py`: 3: tipos concretos de metadatos; booleanos rechazados como longitudes/precisiones; imports fríos de metadatos.
- `tests/orm/factories/test_factory_regressions.py`: 1: anotaciones runtime de factory/provider.

**Límite de validación ORM:** histórico baseline 489/489; primera integrada final 504 produjo 501 aprobadas y 3 fallos. Se corrigieron los tres y pasaron reejecuciones focalizadas (Package 6, Fake 23, contratos 12). Inventario actual 505 métodos; no existe evidencia de una ejecución integrada completa 505/505. Debe constar así aunque la revisión de fuentes se hubiese cerrado.

### Correcciones Auth conservadas

- `context/context.py`: lectores que esperan autorización revalidan propiedad/estado del contexto; un fork de contexto cuya identidad ha desaparecido borra el credential ID antiguo para no revocar la credencial anterior.
- `manager.py`: `attempt`, `login` y `logout` revalidan la solicitud dentro del lock después de esperar. Operaciones de autorización/token también ajustadas a propiedad del contexto.
- `guards/session_guard.py`, `guards/token_guard.py`, `remember.py`: rechazan cuentas explícitamente inactivas; fingerprints malformados fallan de forma cerrada; sigue admitiéndose el comportamiento compatible de identidades personalizadas sin propiedad `active`.
- `tokens/lookup.py`: hidrata al propietario ligado a la conexión correcta antes de eventos/hook `retrieved`.
- `identity/provider.py`: exige un modelo ORM concreto que implemente el contrato de identidad; no admite una clase abstracta o solamente un concern. Identificadores enteros gigantes se rechazan antes de conversión costosa/acceso a almacenamiento.
- `concerns/functions.py`: límites de identificadores autorizables antes de convertir enteros gigantes a texto.
- `authorization/registry.py`: caché derivada con `WeakKeyDictionary`; registros explícitos permanecen referencias fuertes. Evita retener clases de recursos consultadas pero nunca registradas.
- `authorization/registrar.py`: recuperación de una escritura no sustituye el fallo primario cuando también falla el lookup/update de recuperación; secundaria observada centralmente.
- `passwords/broker.py`: reset devuelve el estado realmente confirmado; recarga dentro de la transacción; rollback si la identidad actualizada desaparece; mantiene manager/conexión inyectados aunque cambie el resolver global; preserva fallo original en recuperación.
- Anotaciones runtime en contratos, guards, contexto, middleware, provider y servicios; aislamiento de fixtures y sincronización determinista en pruebas.
- Mantener `IIdentityProvider.updateRememberToken()` asíncrono opcional con retorno `False`; existe consumidor que lo espera. No resolver S7503 convirtiéndolo a sync, abstracto o añadiendo un await artificial.

Regresiones nuevas:

- `tests/auth/test_context_regressions.py`: 4: fork antiguo sin revocar credential; lectores esperando revalidan propiedad; anotaciones; transiciones en cola rechazan petición cerrada.
- `tests/auth/test_guard_regressions.py`: 11: sesión de cuenta desactivada; fingerprints de sesión; token con inactive; hidratación antes de retrieved; reset devuelve commit; rollback al desaparecer identidad; broker conserva conexión; fingerprint almacenado malformado; owner key enorme; preservación de error primario; anotaciones.
- `tests/auth/test_authorization_regressions.py`: 4: anotaciones; claves gigantes antes de DB; clases no registradas no retenidas; recuperación preserva error de escritura.
- `tests/auth/test_identity_regressions.py`: 3: identificadores gigantes; modelo concreto requerido; anotaciones y contrato asíncrono opcional de identidad/middleware.

Histórico final: **383/383**, 383.318 s, 0 omitidas y 0 accesos protegidos; posteriormente se amplió el test del hook opcional y pasó su archivo 3/3. Ruff/formato, AST, Pydoctor, ejemplos e imports fríos tuvieron resultados históricos aprobados. Sonar conservó **1 S7503**; por tanto no fue Sonar sin diagnósticos.

### Correcciones Session conservadas

- `flash.py`: normaliza mensajes de fallo a texto conservando `0` y `False`; `None` mantiene `""`; helper `_normalize_message` reduce ramas repetidas y permite eliminar NOSONAR.
- `session.py`: `_ageFlashData()` diferencia bolsa ausente de bolsa presente con valor `None`; eliminar la bolsa nula marca dirty y se persiste aunque no toque renovar.
- `manager.py`: borrado de cookie usa el mismo constructor de cookie que su emisión, con fecha expirada y max-age 0. Conserva Secure, HttpOnly, SameSite, Partitioned, path/domain y validez de cookies prefijadas.
- `stores/file.py`: las cinco operaciones async usan `complete_on_cancel(asyncio.to_thread(...))`; el propietario espera al worker y observa errores tardíos antes de propagar cancelación. Cancelar no promete deshacer un write ya publicado.
- File store resuelve el directorio relativo en el constructor, impidiendo que un `chdir` posterior redirija operaciones.
- GC de archivos sólo procesa nombres compatibles con el formato propio de sesión o staging; conserva archivos ajenos.
- `_deleteStaleTemp()` adquiere el lock de la sesión dueña del staging, vuelve a comprobar antigüedad y después elimina; evita borrar un staging de escritor activo. `_gcSweep()` descarta los jóvenes antes de esperar el lock.
- `stores/database.py`: expiraciones corruptas o fuera de rango se rechazan; si la recuperación posterior al insert falla, el error inicial permanece primario.
- `stores/cache.py`: TTL entero truncado, no redondeado hacia arriba. Menos de un segundo restante no se persiste/renueva; write elimina y update devuelve False, evitando TTL 0 interpretado como inmortal. Manual explica expiración hasta un segundo anticipada y límites de reloj/backend/transporte.
- Imports/anotaciones/docstrings, fixtures y manuales actualizados; se conserva préstamo/shallow-copy del payload según API. No se promete regeneración atómica que no existe.

Regresiones nuevas:

- `tests/session/stores/test_store_regressions.py`: 8: anotaciones; propiedad de workers tras cancelación; GC sólo archivos propios; ruta relativa estable; GC espera escritor de staging; expiraciones DB corruptas; error primario de write; fracción TTL no renueva expiración.
- `tests/session/test_flash_regressions.py`: 2: mensajes falsy a string; anotaciones.
- `tests/session/test_manager_regressions.py`: 2: identidad/política de cookie al expirar; anotaciones.
- Regresión de bolsas nulas añadida dentro de un archivo original.

Histórico: **260/260**, 146.134 s, 0 omitidas/protegidos. Sonar 30/30 hashes actuales y 0 diagnósticos al cierre; documentación/imports/consumidores comprobados históricamente. Benchmarks existen sólo en la memoria resumida porque se perdieron los temporales; no afirmar mejoras generales: varias rutas añaden coste necesario y las mediciones de I/O presentaron dispersión considerable.

### Resto de correcciones View

- `cache.py`: nombres de bytecode portables; impide que nombres con unidad, colon, reservados Windows o controles escapen del directorio o fallen por basename inválido.
- `engine.py`: errores Jinja al cargar/compilar se convierten a `ViewRenderException` con causa directa; missing-template mantiene su tipo especializado. `WorkQueueFullError` y OSError de carga no se convierten en errores de plantilla.
- `pending.py`: no vuelve a envolver excepciones ya clasificadas y conserva `WorkQueueFullError`; causa original accesible.
- Regex de limpieza de cualificadores ahora `r"(?<![\w.])(?:[\w.]*<locals>\.)+"`, para evitar reintentos cuadráticos sobre sufijos y conservar calificadores locales anidados. **Faltaba completar la comparación de 2003 mensajes y el benchmark preparado.**
- `globals/url.py`: query se inserta antes del fragmento. Último cambio case-insensitive detallado arriba.
- `globals/errors.py`: dict vacío nuevo cuando falta sesión, evitando contaminación entre solicitudes; `any()` requiere algún mensaje real, no sólo keys con listas vacías.
- `globals/route.py`: reemplaza dict sin límite por `@lru_cache(maxsize=1024)`; plantilla pura como key, sin datos de aplicación; preserva escape y parámetros sobrantes. Regresión weakref comprueba límite, recencia, expulsión y reconstrucción.
- Anotación `today` corregida a `pendulum.DateTime`, sin cambiar el valor.
- Runtime annotations reparadas en builders/callbacks/contracts/environment/factory/pending y `CsrfExtension.parse(Parser)`.
- Se conservó la regla pública de dot-notation: `page.html` sin `/` sigue resolviendo `page/html.html`. No cambiarla accidentalmente al corregir extensión.
- La caché de normalización del engine sigue siendo FIFO; manuales dejaron de llamarla LRU. La caché de rutas sí es LRU.
- Filtros siguen devolviendo texto, con autoescape comprobado; no se añadió sanitización o confianza Markup ajena a la API.
- Tests consolidados manteniendo escenarios/causas/mensajes; datetime fijo, restauración de globals al registrar cleanup, sincronización con Barrier/TaskGroup en vez de sleeps.

Pruebas nuevas: engine 4, globals **6 actuales**, render 3. Histórico completo antes de URL tardío: **189/189**, 23.112 s. Consumidores históricos: HTTP factory **25/25**, 4.694 s; Mail **195/195**, 37.549 s; todos sin omisiones ni accesos protegidos.

### Pendientes posteriores y límites

Confirmado: **Mail, Queues, Realtime y HTTP no tienen cambios de fuentes/pruebas respecto de HEAD**. Eso no significa que estén revisados.

- **Mail:** sólo baseline/read-only inventory. 28 fuentes, 32 archivos de pruebas, 195 métodos, 10 manuales. Reparto previsto: root manager/pending/provider/contrato + integración/config/docs; motor composer/functions/mailable/message/content/prepared; validación transportes file/SMTP y SMTP settings; cliente entidades/enums/exceptions/types y ejemplos. Ninguna implementación Mail empezó.
- **Queues:** revisión integral pendiente. Los fallos históricos pertenecían a un subconjunto consumidor de 19 casos, **no a toda la suite**, que actualmente contiene 151 métodos AST. Hubo WinError32, pool timeouts y SQLITE_BUSY. Un control HEAD pasó y profiling encontró sobrecoste de stat/debug de asyncio, pero eso **no prueba** que todos los fallos sean del entorno. No aumentar timeouts/desactivar debug para ocultarlos.
- **Realtime:** revisar conversión `DataArgument.convert` en `orionis/realtime/metadata.py`; usa `msgspec.convert` y validación posterior. Hipótesis pendiente de que Coerce no se aplique a schemas compuestos.
- **MCP:** revisar `orionis/mcp/server/schemas.py:251` (`convert_payload`) y `invoker.py`; una clase Schema directa sigue Validator, mientras otros tipos/Optional/composites siguen msgspec. Hipótesis pendiente, no defecto reproducido durante este traspaso. Único cambio de integración actual: `tests/mcp/test_state.py`.
- **HTTP:** verificar 405/Allow contra router real; revisar uso de estado ambiental `sys.exception()` en `kernel.py:1385`, `:1478`, `:1693` (RSGI/ASGI/closeWebSocket) que puede confundir una excepción externa con un fallo primario del recurso. Sin regresiones ejecutadas aún.
- **Console:** `orionis/console/commands/test/test.py:216-223` devuelve 0 si `run()` entrega lista vacía; pendiente decidir y proteger error de descubrimiento vacío según contrato. Únicos cambios actuales del paquete son key_generate y su test por GCM.
- **Foundation:** revisión integral pendiente; cambios de integración GCM en configuración de app/ciphers y tests, más documentación. Revisar candidatos previos de límites Argon, logging/facades, arranque/cierre.

Inventario AST actual, **no descubrimiento ni ejecución**:

| Paquete | Archivos Python de tests | Métodos con prefijo test |
|---|---:|---:|
| ORM | 100 | 505 |
| Auth | 29 | 383 |
| Session | 15 | 260 |
| View | 15 | 190 |
| Mail | 32 | 195 |
| Queues | 15 | 151 |
| Realtime | 9 | 89 |
| MCP | 20 | 178 |
| HTTP | 69 | 970 |
| Console | 77 | 1493 |
| Foundation | 26 | 246 |

Todos los resultados de ejecución citados son **históricos de la conversación**, no reejecuciones del 12 de noviembre. Los directorios TEMP y sus manifests ya no existen: reconstruir el harness seguro y recopilar nueva evidencia antes de certificar el estado actual.

### Integración externa y pruebas raíz: alcance limitado que sí cambió

- `.env.reference`, `config/app.py`, `orionis/foundation/config/app/entities/app.py` y `orionis/console/commands/support/key_generate.py`: default AES-256-GCM coherente. `App.__post_init__` rechaza CBC **antes** de generar o persistir una clave. `orionis/foundation/config/app/enums/ciphers.py` conserva identificadores legacy y define `_AUTHENTICATED_CIPHERS`; no confundir enum disponible con modo aceptado para cifrar.
- `tests/foundation/config/test_authenticated_ciphers.py` es nuevo; `test_regressions.py` y `tests/console/commands/support/test_support_commands.py` se ajustaron a esa decisión. Histórico: 95 casos de configuración, 11 de keygen y 14 de CLI aprobados. No equivalen a la revisión integral de Foundation/Console.
- `tests/mcp/test_state.py`: el caso de downgrade CBC verifica el rechazo de configuración de `McpState` usando un Encrypter válido; construir un Encrypter CBC habría fallado antes de alcanzar el contrato que el caso pretende probar. Sus seis casos consumidores pasaron históricamente. El archivo conserva `NOSONAR` preexistentes que deben auditarse al revisar MCP; no se ha completado la limpieza global de supresiones.
- `tests/test_naming_conventions.py`: el walker ahora poda toda la carpeta prohibida antes de escanear/parsing y propaga errores de lectura; fixtures propias verifican esa exclusión sin tocar el árbol real y aseguran que nombres parecidos en otras ubicaciones siguen comprobándose. Reconoce hooks heredados de `HTMLParser` importado explícitamente, sin dispensar métodos snake_case de clases ajenas ni helpers nuevos fuera del protocolo.
- `tests/test_backend_lazy_imports.py`: dispensa S603 trasladada de clase a cabecera con justificación de subprocess fijo; no se reescribió su comportamiento. El cierre global debe volver a ejecutar estas pruebas raíz, no limitarse a carpetas de paquetes.
- `.github/scripts/run_tests.py`: podado previo, errores de traversal explícitos, ejecución de cada archivo raíz mediante selector individual y fallo por inventario vacío; ver catálogo `test`. No basta para impedir efectos externos de las propias pruebas: conservar el guard aislado.
- Los seis manuales de Foundation modificados por integración no significan que se haya terminado su revisión de arranque, kernels, providers o lifecycle. `DOCS.ps1`, `pyproject.toml`, `uv.lock` y `ruff.toml` no figuran modificados en el inventario actual; no atribuirles cambios inexistentes.

## 5. Validaciones realizadas y límites de la evidencia

### 5.1 Entorno

- Python nativo **3.14.6**, confirmado otra vez durante este traspaso con `.venv\Scripts\python.exe -B --version`.
- `uv 0.11.30 (4cb3d0366 2026-07-20 x86_64-pc-windows-msvc)` confirmado actualmente.
- Metadatos de distribuciones comprobados actualmente, sin importar Orionis: Ruff 0.17.3, Pydoctor 25.10.1, Faker 40.44.0, msgspec 0.22.0, Jinja2 3.1.6, SQLAlchemy 2.1.6 y cryptography 50.0.2. Esto verifica instalación, no ejecución funcional.
- Históricamente se verificaron las 99 dependencias bloqueadas y `pip check` sin conflictos; no se volvió a ejecutar esa validación ahora.
- También se habían detectado 3.14.3 y 3.14.3t; su mera disponibilidad no certifica las últimas fuentes. 3.15b4 no se trató como versión posterior estable soportada. No se comprobó ahora de nuevo ese inventario.
- SonarLint instalado actualmente: `sonarsource.sonarlint-vscode-6.3.0-win32-x64`; existe `analyzers/sonarpython.jar`. La ejecución histórica usó Java 21 y analizador Python 5.32.0.37250: 452 reglas disponibles/407 activas por defecto, más configuración aplicable. Revalidar perfil real, no inferirlo solo de la extensión instalada.

### 5.2 Cómo se ejecutó la validación funcional histórica

Se usó el motor **nativo de Orionis**, no pytest. El auxiliar temporal `native_suite.py` generaba una copia propia del proyecto con exclusión previa de la carpeta prohibida y del `.env` real; construía entorno sintético, HOME/AppData/TEMP propios, SQLite/memoria/transporte de correo a archivo y un guard de acceso. Se prohibían escrituras en el repositorio real, lecturas del `.env` real y del árbol excluido, escrituras fuera de recursos propios y conexiones no autorizadas. Un registro de violaciones hacía fallar la ejecución incluso si la aplicación capturaba la excepción. Las copias se limpiaban al terminar.

Los resultados recientes citados como `0 accesos protegidos` provienen de ese guard, no de una ejecución sin aislamiento. Un mock no certifica un backend externo. No se validaron servicios de producción ni se enviaron mensajes reales.

### 5.3 Cierres recientes con evidencia detallada

| Alcance | Resultado observado | Archivo histórico de log, hoy ausente |
|---|---|---|
| Storage integrado | 288/288, 56.760 s; sin omisiones/violaciones | Evidencia local de Storage en el antiguo REVIEW |
| Database baseline | 298/298, 198.902 s | Evidencia local Database |
| Database final antes de seguimiento ORM | 326/326, 408.021 s; 0 violaciones | Evidencia local Database |
| Compilador Database tras corrección ORM | 69/69 | Seguimiento específico; no otro full 326 |
| ORM baseline | 489/489, 761.658 s | Baseline ORM |
| ORM primera integrada final | 501 aprobadas, **3 fallos**, total 504, 925.654 s | No convertir esta ejecución en 504/504 |
| ORM rechecks posteriores | Package 6, Fake 23, contratos 12 verdes; añadido un caso negativo del helper | La integrada de 505 sigue pendiente |
| Auth integrada | 383/383, 383.318 s, 0 omitidas/violaciones | `auth-final-integrated.log` |
| Auth ampliación final de contrato optional hook | 3/3, 0.429 s | Recheck de regresiones de identidad |
| Session baseline | 259/259, 62.343 s | Como consumidor de Auth |
| Session integrada | 260/260, 146.134 s; 0 omitidas/violaciones | `session-final-integrated.log` |
| Session regresiones stores finales | 8/8, 7.462 s | Posterior al último ajuste del GC |
| View baseline | 216/216, 28.844 s; 0 omitidas/violaciones | `view-baseline-session-consumer.log` |
| View integrada antes del cambio de esquemas HTTP | **189/189, 23.112 s**, 0 omitidas/violaciones | `view-final-integrated.log` |
| HTTP factory consumidor de View | 25/25, 4.694 s; 0 violaciones | `view-http-factory-consumer.log` |
| Mail baseline consumidor de View | 195/195, 37.549 s; 0 violaciones | `mail-baseline-view-consumer.log` |
| HTTP web consumidor de Session | 11/11, 1.817 s | Recorrido específico; no todo HTTP |
| Auth identity/session consumidor de Session | 28/28, 35.353 s | Fuentes de memoria congeladas; no ejercita el GC de archivos |

Cambios de cantidad que deben conservarse explícitos:

- Encrypter: 66 anteriores − 11 casos CBC obsoletos por la decisión autorizada + 4 regresiones = 59.
- Auth: 365 − 4 consolidaciones equivalentes + 22 regresiones = 383.
- Session: 259 − 5 constructores redundantes − 7 equivalencias de stores + 2 raíz + 2 manager + 1 cliente + 8 stores = 260.
- View: 216 − 39 consolidaciones equivalentes + 12 regresiones iniciales = 189; la sexta regresión de globals añadida al final produce **190**. Los escenarios conservados dentro de subpruebas no se reducen al número de métodos.
- ORM: 489 de baseline; 504 en primera integrada, tres fallos luego corregidos; un caso negativo adicional deja 505. No existe una ejecución única comprobada de esas 505 en el estado final.

### 5.4 View: frontera exacta del trabajo interrumpido

La revisión completa cubrió 39 fuentes, los 216 métodos originales en 12 archivos y 10 manuales. Quedaron 15 archivos de pruebas. La ejecución integrada verde de 189 antecede al último cambio de `globals/url.py` y a la última ampliación del test de contrato warmup.

Validaciones parciales observadas:

- Parte raíz: factory 11/11 (2.892 s), pending 36/36 (6.918 s), provider 12/12 (3.146 s), nuevas regresiones de render 3/3 (0.806 s); todas con 0 omisiones/violaciones.
- Regresión de saturación: rojo confirmado por conversión de `WorkQueueFullError` a `ViewRenderException`; corregido y verde. La prueba exige preservar el objeto/tipo original.
- Globals originales: 34/34 (11.976 s); las cinco regresiones anteriores, 5/5 (0.787 s). Límite de caché confirmado con weakrefs: rojo reteniendo 1100 templates; verde con capacidad 1024 y recencia/evicción.
- Nuevo reconocimiento de `HTTP://`/esquemas mixtos: **rojo observado en 11 subcasos**; cambio y sexto método presentes físicamente. El agente estaba ejecutando el verde cuando se interrumpió: **resultado verde no recuperado**. No contarlo como aprobado.
- Engine/cache/environment: grupos de 17, 16 y 27 aprobados; cuatro regresiones inicialmente verdes. Última ampliación de warmup dentro del cuarto método: 4/4, 0.774 s, 0 violaciones, comunicada antes de la interrupción. No cambió producción ni el número de métodos.
- Filters 6, extensions 8, exceptions 6 aprobados; el fallo previo de `Parser` en anotaciones runtime se reprodujo y corrigió.
- Último análisis completo antes del delta: Ruff 54 Python sin diagnósticos; formato 64 archivos incluyendo 10 manuales; AST 364 funciones (115 de fuente y 249 de pruebas/helpers); Pydoctor real 179 objetos sin advertencias. El nuevo helper de URL y sus tests requieren actualizar estos datos.
- Sonar completo anterior: 54/54 seleccionados, publicados y con SHA vigente en ese instante; 0 errores de procesamiento/cierre; **3 hallazgos**, detallados en la sección 7. El delta posterior no se observó.
- Manuales: 10/10; 14 bloques Python literales, 8 bloques HTML/Jinja renderizados, 38 enlaces locales; dos arranques/cierres reales de aplicación, scopes/request/session/CSRF, rutas y extensiones. Guard sin violaciones. Revalidar hashes después del último cambio si se reconstruye el verificador.
- Se preparó `probe_view_runtime.py`: ocho órdenes de imports en procesos frescos, 39 módulos y resolución de anotaciones; **final no observado**, aunque la preparación y lanzamiento sí ocurrieron.
- Se prepararon benchmarks de Pending, Engine y Route; el de URL se pidió. **Ninguno de esos resultados finales de View está acreditado**. No afirmar una mejora de rendimiento de View todavía.

### 5.5 Analizadores/documentación locales recientes

| Paquete | Ruff/formato local histórico | Sonar histórico | Documentación/imports históricos |
|---|---|---|---|
| Storage | Sin diagnósticos; 63 archivos formato | 53 archivos; 1 S5332 | 548 objetos Pydoctor; 18 ejemplos/30 enlaces |
| ORM | Sin diagnósticos; 211 archivos formato | 195 archivos actuales entonces; 2 S1845 | 1139 objetos; AST 2564 funciones; 32 ejemplos/36 enlaces |
| Auth | Sin diagnósticos; 98 archivos formato | 86/86; 1 S7503 | 520 objetos; AST 813 funciones; 16 bloques Python, 6 comandos CLI, 90 enlaces; 8 órdenes de imports |
| Session | Sin diagnósticos; 40 archivos formato | 30/30; 0 hallazgos | 227 objetos; AST 444 funciones; 12 bloques Python/66 enlaces; 8 órdenes × 117 funciones con tipos |
| View | Limpio antes del último delta; ver detalle | 54/54, 3 hallazgos antes del delta | 179 objetos antes del delta; manuales ejecutados; cold imports finales sin resultado |

Los paquetes anteriores también tuvieron cierres locales registrados; sus logs detallados no se recuperaron. Las cifras de tests de la sección 3 son la evidencia histórica conservada, no un sustituto del cierre global. Una ejecución documental anterior registró 2239 HTML, 12779 elementos API y 11432 tablas sin errores: **no corresponde al estado final actual**. No se ha ejecutado el `DOCS.ps1` final tras todos los cambios.

## 6. Rendimiento: qué se midió y qué no

Se usaron comparaciones HEAD/current con entradas equivalentes, cinco pares alternados cuando se indica, GC habilitado, comprobaciones semánticas fuera del intervalo y guard activo. Los números de microbenchmarks no son rendimiento global del framework. El coste de garantías nuevas no debe eliminarse para mejorar cifras.

### Mediciones históricas recientes (microsegundos por operación)

| Caso | HEAD → current | Interpretación y límite |
|---|---|---|
| GCM cifrar 16 B | 8.026 → 7.904 | No demuestra mejora general |
| GCM descifrar 16 B | 3.946 → 5.106 | Coste mayor en este caso; no ocultarlo |
| GCM cifrar/descifrar 4 KiB | 69.092 → 59.231 / 75.583 → 74.934 | Rangos amplios; sin afirmación global |
| Auth contexto cache hit | 0.628 → 0.599 | Microcaso específico |
| Auth contexto cold | 7.270 → 11.015 | Coste de corrección/aislamiento |
| Auth contexto 8 lectores | 107.26 → 113.90 | Solapamiento amplio |
| Auth policy registrada/heredada/negativa | 0.214 → 0.405 / 0.350 → 0.578 / 0.321 → 0.436 | Coste de retención débil correcta |
| Auth guard sesión/combinado/fallback | 3146 → 2743 / 10895 → 11895 / 11982 → 11404 | SQLite real controlado, conteos de consultas; ruido amplio |
| Session flash plano/estructurado/escalar | 0.748 → 0.986 / 1.353 → 1.467 / 1.606 → 1.772 | Incluye controles sin cambio de rama; no atribuir todo delta al código |
| Session flash failure/form ordinario/credential | 0.914 → 0.845 / 0.257 → 0.255 / 0.663 → 0.470 | Algunos son controles sin cambios; ruido |
| Session manager lazy/skip/persist | 0.837 → 0.843 / 26.237 → 26.098 / 148.592 → 156.634 | Se verificó persistencia real en cada iteración con 10051 operaciones |
| Session FileStore read/write/update | 6484 → 6180 / 10495 → 11062 / 14907 → 16841 | E/S real; rangos amplios, drenaje de cancelación añade garantías |

Los rangos de FileStore fueron read 4415–7466/3609–6749, write 8080–10898/9712–11760, update 12108–15479/14181–17791. En manager persist fueron aproximadamente 83–215/100–220. No se declaró mejora general.

Se descartó una microoptimización de identidad que convertía una vez a `str`: mejoraba UUID objeto, empeoraba UUID texto en los cinco pares. No reintroducirla sin evidencia nueva. En ORM las copias correctas de estado y preparación de scopes tienen costes justificados; no eliminar garantías para recuperar el tiempo anterior.

Parámetros recuperados de Session: flash, seis casos × cinco pares × 30000 iteraciones, 500 warmups; manager, tres casos × cinco pares × 2000 iteraciones, 50 warmups y reloj fijo; FileStore, tres casos × cinco pares × 100 iteraciones, 20 warmups y seis directorios propios. El primer diseño de benchmark manager tenía un contador que no demostraba persistir en cada iteración: se detectó y corrigió **antes de usar la medición final**. Mantener la comprobación fuera del intervalo, no copiar el diseño inválido.

**View sigue pendiente de medición:** el script de Pending planeaba 2003 mensajes de equivalencia semántica y 25 pares de regex (cortos, anidados y 512/1024/2048 caracteres no coincidentes); Engine 25 pares para key/hot/cold/warmup/bytecode con contadores reales de loader/compiler; Route cinco pares fríos/calientes y cinco trazas de memoria con 10000 claves, comparando caché ilimitada contra LRU 1024. No convertir la preparación de esos scripts en resultados.

Hubo una medición antigua inválida por omitir los argumentos del harness: creó 811 archivos sintéticos, 52.5 MB, bajo un directorio nuevo y propio `local-tests/database-70328`. Se verificaron nombres/hashes y se eliminaron únicamente esos archivos y directorios vacíos, tras rechazo automático de una limpieza recursiva; se informó al usuario. La medición se descartó y el guard se endureció. No usar aquellos números ni ejecutar los auxiliares antiguos `all.py`/`diagnose.py` que no tenían las garantías finales.

## 7. Problemas conocidos, riesgos y posibles regresiones

### 7.1 Hallazgos Sonar abiertos; no ocultar ni afirmar “cero”

1. **Introspection S930:** `inspect.signature(annotation_format=Format.FORWARDREF)` es API válida de Python 3.14; el analizador antiguo no la reconoce. Conservar comportamiento y documentar evidencia del runtime. Referencia técnica: <https://docs.python.org/3.14/library/inspect.html>.
2. **Storage S5332:** `http://acs.amazonaws.com/groups/global/AllUsers` es el identificador canónico de grupo ACL de S3, no una conexión HTTP insegura. No sustituirlo por HTTPS rompiendo la ACL. Referencia: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html>.
3. **ORM S1845, dos casos:** Faker expone tanto `postalCode` como `postalcode`; la clase normal y la opcional reproducen contratos reales. Se contrastaron 1409 firmas con Faker 40.44.0. No borrar un nombre solo para silenciar la regla.
4. **Auth S7503:** `IIdentityProvider.updateRememberToken` es un hook asíncrono opcional con fallback `False`, consumido mediante `await` por RememberMe. Convertirlo en sync, abstracto o insertar un `await` artificial cambiaría el contrato o engañaría al analizador. Hay prueba de contrato.
5. **View S7503:** `IViewEngine.warmup` es hook asíncrono opcional sin carga por defecto; prueba actual comprueba coroutine, no abstracto y `await` base sobre engine real → `None` sin loader. Misma restricción.

Son seis diagnósticos contando los dos de Faker, si el análisis actual los reproduce. Antes de la última corrección de URL, View tenía además **dos S5332** por literales de reconocimiento `http://`. El arreglo funcional de esquemas mixtos sustituyó esa lógica, pero **el delta Sonar no se observó**: no afirmar que desaparecieron ni cambiar lógica solamente para engañar a la regla.

### 7.2 Ruff pendiente global

`ruff.toml` conserva `select = ["ALL"]` y los ignores globales originales: CPY001, D100, D101, D104, I001, I002, INP001, N802, N818, PLR0917, TRY300, TRY301. No reducirlos ni ampliarlos durante la continuación por conveniencia.

La migración final de **per-file-ignores existentes** a cabeceras auditadas todavía está pendiente. Quedan mapas para `__init__.py`, `app/**`, `config/**`, `database/**`, `routes/**`, `orionis/database/**` y `tests/**`; este último contiene ANN001/201/202, PT009/PT027, SLF001, ARG003, FBT003, PTH110/113/118/123, PLC0415, PLR2004, DTZ001, ERA001, S324. No copiar todos esos códigos a todos los archivos. Primero ejecutar sin `noqa` y sin mapas, revisar todas las infracciones, corregir las reales y justificar solo las dispensas necesarias por archivo.

No interpretar una cabecera como obsoleta con RUF100 mientras el mapa global todavía enmascara su necesidad. Ruff soporta sintaxis Python 3.14 como `except A, B:`; no revertir mecánicamente por expectativas de versiones antiguas. La advertencia COM812 del formatter no autoriza desactivar la regla: ajustar las comas necesarias.

### 7.3 Riesgos de compatibilidad y concurrencia que requieren preservar pruebas

- CBC antiguo requiere migración explícita antes de actualizar; no hay migrador improvisado ni conversión automática de datos reales.
- `FileCacheBackend` pasó deadlines monotónicos a epoch Unix para sobrevivir procesos/reinicios; entradas antiguas no se migran, se regeneran tras miss. TTL fraccionario en sesiones sobre Memcached se redondea hacia abajo; menos de un segundo no debe convertirse en TTL 0 inmortal.
- Drenar workers al cancelar puede demorar la cancelación hasta completar la operación ya iniciada. No confundir ese contrato con fuga de tareas ni reemplazarlo por cancelación inmediata que deje mutaciones en background.
- Los cambios de hints/imports deben seguir pasando `typing.get_type_hints` y arranques fríos; `TYPE_CHECKING` puede volver a romper DI/reflexión aunque Ruff quede limpio.
- Guardar estado aislado de Auth después de cambios de scope, no revocar credenciales de un contexto reemplazado ni compartir resultados entre requests.
- Modelos/queries/scopes/relaciones deben usar la conexión y lease que realmente les pertenecen; no reintroducir un resolver global al hidratar un resultado.
- La caché de templates normalizados de engine es **FIFO 1024** por contrato actual; la caché de planes de rutas de globals es **LRU 1024**. No confundir ambas ni cambiar la traducción documentada de `page.html` a `page/html.html` en dot notation.
- `PendingView` conserva `WorkQueueFullError`, `ViewTemplateNotFoundException` y `ViewRenderException`; no duplicar wrappers ni perder `__cause__`.
- `stripTags` con etiquetas permitidas conserva atributos; **no es un sanitizador XSS**. No documentarlo como uno.
- Backends opcionales probados con dobles no quedan certificados contra servicios reales. No deducir garantías de entrega exactly-once en colas.

### 7.4 Queues: fallo independiente todavía sin diagnóstico definitivo

Una suite consumidora de Database de 19 casos produjo primero 18 aprobados/1 fallo `WinError 32` de limpieza (~501 s); otra vez 17 aprobados/2 fallos por timeout de pool y `SQLITE_BUSY` (~363 s). Un caso many-jobs aislado aprobó (~176 s). Control con Database de HEAD: 19/19 (~521 s, CPU ~559 s).

El subconjunto corresponde a `tests/queues/drivers/test_database.py` (19 métodos en el inventario estático actual), **no** a toda la suite de Queues. Su comando nativo, únicamente dentro de la copia aislada ya protegida, es `python -B reactor test --start-dir=tests/queues/drivers/test_database.py --verbosity=2 --fail-fast=0`; usar la ruta absoluta del intérprete 3.14 indicada antes.

El profiling mostró miles de `nt.stat` por traceback/linecache bajo asyncio debug: un caso pequeño ~7700 llamadas y ~80 % del tiempo; un control solo stdlib con 200 Future y `call_soon`, `asyncio.Runner(debug=True)`, 1.0016 s y 2424 stats/0.8699 s (~86.9 %). Esto prueba coste ambiental, **no prueba que todos los fallos de Queues sean ambientales**. Revisar reservas, contención, cierre y limpieza. No desactivar debug, subir timeouts arbitrariamente ni reintentar hasta verde para ocultar el problema.

### 7.5 Hipótesis pendientes, no defectos nuevos ya reproducidos

- HTTP: revisar `405 Allow` del router real y tres limpiezas que consultan `sys.exception()` en `orionis/http/kernel.py` alrededor de líneas 1385, 1478 y 1693.
- Console: `orionis/console/commands/test/test.py`, aproximadamente 216–223, puede informar éxito ante descubrimiento vacío; contrastar contrato y reproducir antes de corregir. El runner CI ya trata inventario vacío como error.
- MCP: inspeccionar validación de `Optional`/schemas compuestos y rutas que omitan Validator/Coerce; también hallazgos preliminares S3776 en server/templates y S1192 en `__init__`.
- Realtime: revisar si `DataArgument`/msgspec evita la coerción central y sus constraints.
- Foundation: límites Argon, facades/logging, default GCM y ciclo de vida integrado.
- El análisis preliminar global de 1636 archivos tras ORM no era cierre final; había además hallazgos en tests de Console S8997/S5778/S3415. No convertir la lista en cobertura final ni modificar reglas para hacerla desaparecer.

## 8. Comandos de reproducción y prerrequisitos reales

Los comandos siguientes están escritos para PowerShell. **Son instrucciones para la reanudación; no se ejecutaron durante la redacción, salvo las inspecciones explícitamente identificadas.** No ejecutar suites en el checkout real sin reconstruir el aislamiento.

### 8.1 Identidad, configuración y preservación (solo lectura)

```powershell
Set-Location -LiteralPath 'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework'
git --no-optional-locks branch --show-current
git --no-optional-locks rev-parse HEAD
git --no-optional-locks status --short --untracked-files=all -- . ':(exclude)tests/real_database' ':(exclude)tests/real_database/**'
git --no-optional-locks diff --stat -- . ':(exclude)tests/real_database' ':(exclude)tests/real_database/**'
git --no-optional-locks diff --cached --stat -- . ':(exclude)tests/real_database' ':(exclude)tests/real_database/**'
& '.venv\Scripts\python.exe' -B --version
uv --version
Get-Content -LiteralPath 'pyproject.toml'
Get-Content -LiteralPath 'ruff.toml'
Get-Content -LiteralPath 'DOCS.ps1'
Get-Content -LiteralPath '.vscode\settings.json'
git check-ignore .vscode/settings.json
```

No imprimir `.env` ni variables de entorno completas. Leer `uv.lock` para contrastar dependencias; no hacer `uv lock --upgrade`. Para los intérpretes y dependencias al reanudar:

```powershell
uv python list --only-installed
uv pip check --python '.venv\Scripts\python.exe'
```

### 8.2 Runner nativo: sintaxis histórica exacta y por qué hoy está bloqueada

Los siguientes fueron los comandos del harness real. **El archivo temporal no existe actualmente**; no presentarlos como reproducibles sin restaurarlo:

```powershell
$reviewRoot = 'C:\Users\runate\AppData\Local\Temp\orionis-review-pwv5t8d5'
$repoRoot = 'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework'
& '.venv\Scripts\python.exe' -B "$reviewRoot\native_suite.py" $repoRoot 'tests/view' --verbosity 2
& '.venv\Scripts\python.exe' -B "$reviewRoot\native_suite.py" $repoRoot 'tests/view/test_global_regressions.py' --verbosity 2
& '.venv\Scripts\python.exe' -B "$reviewRoot\native_suite.py" $repoRoot 'tests/view/test_engine_regressions.py' --verbosity 2
& '.venv\Scripts\python.exe' -B "$reviewRoot\native_suite.py" $repoRoot 'tests/mail' --verbosity 2
```

El harness aceptaba un único selector de suite. El modo global era `--all`; recuperar/verificar su parser antes de reconstruir la llamada exacta. No omitir el repositorio y la suite al invocarlo: ese error ya causó una medición inválida.

Para reconstruirlo fielmente, recuperar primero el script desde respaldo/historial si existe. Si no, implementar **fuera del repositorio** un nuevo harness con estas garantías y probar sus rechazos con fixtures propias antes de usarlo:

1. Inventariar con Git y filtrar rutas prohibidas **antes de abrir o copiar**; en walkers podar `real_database` de `children` antes de descender. No seguir enlaces/junctions a destinos externos.
2. Copiar tanto archivos rastreados modificados como nuevos sin seguimiento. No usar `git archive HEAD`: omite precisamente la revisión. No copiar `.git`, `.venv`, caches de ejecución, `.env` real, bases/almacenamiento reales ni logs del usuario. Usar el intérprete nativo existente por ruta absoluta.
3. Crear `.env` sintético y configuración de pruebas propia, limpiar secretos heredados, dar HOME/USERPROFILE/AppData/TEMP propios; dirigir SQLite, sesiones, caché, storage y transporte de correo a directorios propios. Bloquear SMTP real y red no autorizada también en procesos hijos.
4. Auditar lectura prohibida y escritura fuera del snapshot; guardar un ledger de intentos que haga fallar el padre aunque la aplicación capture la excepción. Propagar la barrera a subprocesos. No sustituir toda la lógica bajo prueba por mocks.
5. Capturar stdout, stderr y **exit code original antes de mostrar/tail de logs**; comprobar total/errores/omisiones/violaciones. Una suite vacía no es éxito.
6. Limpiar solo el directorio creado por esa ejecución, comprobando ruta absoluta y ausencia de redirecciones; preservar logs y SHA en una ubicación durable de trabajo acordada, no añadir scripts/resultados al repositorio por defecto.

Dentro de una copia que ya cumpla lo anterior, la invocación real del motor es:

```powershell
# Precondición: cwd es la COPIA AISLADA, no el checkout con .env real.
$nativePython = 'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework\.venv\Scripts\python.exe'
& $nativePython -B reactor test --start-dir=tests/view --verbosity=2 --fail-fast=0
$suiteExit = $LASTEXITCODE
if ($suiteExit -ne 0) { throw "Falló View: $suiteExit" }

# CI tiene poda previa de tests/real_database y ejecuta suites en procesos separados.
& $nativePython -B .github/scripts/run_tests.py --list
& $nativePython -B .github/scripts/run_tests.py --continue-on-error --verbosity 2
$allExit = $LASTEXITCODE
if ($allExit -ne 0) { throw "Falló la validación global: $allExit" }
```

**No ejecutar `reactor test --start-dir=tests` en el repositorio real.** `orionis/test/core/engine.py` no implementa por sí solo esa exclusión. La poda sí está en `.github/scripts/run_tests.py`, antes de recorrer; ello no sustituye el aislamiento de recursos de toda la suite.

### 8.3 Ruff y formato sin recorrer la carpeta prohibida

Para View, sobre archivos completos, la sintaxis directa es:

```powershell
& '.venv\Scripts\ruff.exe' check orionis/view tests/view
& '.venv\Scripts\ruff.exe' format --check orionis/view tests/view
```

Para el alcance Python global y documentos fuente, usar inventario explícito y filtrado antes de entregar archivos a Ruff. Este script solo comprueba; no formatea ni corrige:

```powershell
@'
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
raw = subprocess.run(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    cwd=root, capture_output=True, check=True,
).stdout.decode("utf-8")
paths = sorted(set(p for p in raw.split("\0") if p))
allowed = []
for value in paths:
    # Filter names before touching filesystem contents.
    normalized = value.replace("\\", "/")
    if normalized == "tests/real_database" or normalized.startswith("tests/real_database/"):
        continue
    if normalized.startswith((".venv/", ".git/", "docs/")):
        continue
    path = root / value
    if path.suffix in (".py", ".pyi") and path.is_file():
        allowed.append(value)
if not allowed:
    raise SystemExit("Empty Python inventory is not a passing validation")
ruff = root / ".venv/Scripts/ruff.exe"
failure = 0
for operation in (["check"], ["format", "--check"]):
    for offset in range(0, len(allowed), 40):
        result = subprocess.run([str(ruff), *operation, *allowed[offset:offset+40]], cwd=root)
        failure = failure or result.returncode
manuals = [p for p in paths if p.startswith("orionis/") and "/docs/" in p and p.endswith(".md")]
for offset in range(0, len(manuals), 40):
    result = subprocess.run([str(ruff), "format", "--check", *manuals[offset:offset+40]], cwd=root)
    failure = failure or result.returncode
raise SystemExit(failure)
'@ | & '.venv\Scripts\python.exe' -B -
```

Para la auditoría de supresiones, repetir `ruff check` con `--ignore-noqa`. Eso **todavía respeta los per-file-ignores**. El auxiliar histórico `ruff-without-file-ignores.toml` preservaba selección/ignores globales, fijaba target py314 y eliminaba únicamente el mapa para revelar diagnósticos; hoy no existe. Reconstruir una configuración temporal equivalente, usar `--config <ruta-temporal> --ignore-noqa` con la misma lista explícita, inspeccionar resultados y justificar cabeceras. No cambiar `ruff.toml` para simular aprobado.

### 8.4 SonarLint real

El análisis histórico no fue un lint aproximado: se implementó un cliente LSP contra la extensión instalada, con inicialización, perfil, publicación de diagnósticos, cobertura por archivo y SHA, espera de procesamiento y shutdown. El script `run_sonar.py` perdido aceptaba `--path <archivo-relativo>` repetible y `--changed-from <results.json>`. No reconstruir su línea de arranque de Java por conjetura ni sustituirlo por Ruff/SonarQube con otro perfil.

Comprobación actual de la instalación:

```powershell
Get-ChildItem -LiteralPath 'C:\Users\runate\.vscode\extensions' -Directory -Filter '*sonar*'
Test-Path -LiteralPath 'C:\Users\runate\.vscode\extensions\sonarsource.sonarlint-vscode-6.3.0-win32-x64\analyzers\sonarpython.jar'
```

Comandos reales confirmados en el `package.json` de la extensión, para la paleta de VS Code:

- `SonarLint.AnalyseOpenFile` — **Analyze Current File with SonarQube**.
- `SonarLint.ShowSonarLintOutput` — **Show SonarQube for IDE Output**.
- `SonarLint.EnableLogsAndShowOutput` — **Enable Verbose Logging and Show Output**.
- `SonarLint.AnalyzeVCSChangedFiles` — **Analyze Changed Files with SonarQube**; requiere IDE Labs y analiza solo cambiados, **no certifica todo el alcance**.

Para certificar todo el proyecto hay que restaurar el cliente LSP o conducir el análisis completo equivalente y registrar cada archivo permitido. La disponibilidad de esos comandos no es evidencia de análisis ejecutado. El delta de View debe incluir al menos `orionis/view/globals/url.py`, `tests/view/test_global_regressions.py` y `tests/view/test_engine_regressions.py`; como se perdieron los manifiestos antiguos, el camino verificable es analizar de nuevo los 54 Python de View. No fusionar una lista de hashes de archivos no analizados como si fueran diagnósticos publicados. `--changed-from` histórico incluía desconocidos: limitar paths al hacer deltas.

### 8.5 Documentación completa

Después de reanudar y congelar las fuentes finales:

```powershell
Set-Location -LiteralPath 'D:\WORKSPACE\ORIONIS_FRAMEWORK\framework'
.\DOCS.ps1
$docsExit = $LASTEXITCODE
if ($docsExit -ne 0) { throw "Falló DOCS.ps1: $docsExit" }
```

El script real usa `uv run --group docs python -m pydoctor --config pyproject.toml`, `DocumentationSystem`, tema/recursos de `resources/docs/pydoctor`, `--warnings-as-errors`, validación `resources.docs.pydoctor.validate`, staging seguro, sitemap/robots y comprobación de artefactos. Conserva CNAME y revierte la publicación local si falla. Ejecutarlo modifica la salida generada; **no se ejecutó durante la congelación actual**. No reemplazarlo por una ejecución parcial ni editar HTML para resolver advertencias.

La validación de un sitio ya generado, que no sustituye construirlo con las fuentes actuales, tiene esta sintaxis real:

```powershell
uv run --group docs python -m resources.docs.pydoctor.validate docs
```

Revisar visualmente páginas representativas de API, firmas, enlaces y tablas, además de salida exitosa. Ejecutar literalmente ejemplos EN/ES con dependencias reales locales controladas; restaurar los verificadores temporales o escribir equivalentes fuera del repo. Compilar ejemplos sin invocarlos no equivale a validarlos.

## 9. Orden recomendado para terminar, sin duplicar trabajo

1. **Preservar estado y recuperar infraestructura.** Leer este informe y el diff integrado, registrar HEAD/índice/archivos nuevos, restablecer aislamiento y trazabilidad durable. No empezar cambiando paquetes ya cerrados. No asumir que los logs temporales existen. No iniciar servicios desconocidos ni matar procesos por un puerto sin verificar propiedad.
2. **Cerrar View.** Revisar el último diff de URL, ejecutar sexta regresión y resto de globals, contrato warmup, paquete completo de 190, imports fríos/hints y consumidores afectados; repetir Ruff/AST/Pydoctor/Sonar de archivos actuales. Resolver o registrar los hallazgos sin ocultarlos. Medir Pending/Engine/Route/URL con pares equivalentes, contadores y control de memoria. No solapar benchmarks con otras suites/analizadores.
3. **Mail.** Baseline 195 ya existe históricamente; no confundirlo con revisión. Revisar las 28 fuentes/32 tests/10 manuales completas. Propuesta de reparto ya preparada: raíz manager/pending/provider/contract-manager/init + 9 tests/56 métodos y 6 manuales; composición composer/functions/mailable/message/content/prepared + 6 tests/51 y 2 manuales; transportes file/smtp/contracts/settings + 6 tests/42 y 2 manuales; entidades restantes/address/attachment/envelope/options/result/enums/exceptions/types + 11 tests/46. Total cubierto 28/32/195/10. Validar Bcc, MIME, adjuntos/streams, clones entre envíos, errores/cierre; transporte a archivo y dobles en el límite SMTP, nunca correo real.
4. **Queues.** Diagnosticar los fallos descritos, revisar todos los drivers/workers/reservas/retries/timeouts y su integración con Database/Failure. Separar problemas de entorno y bugs con experimentos causales. Mantener semántica de entrega real.
5. **Realtime**, luego **MCP**: identificar contratos existentes, revisar coerción/validación, contexto, cancelación, permisos y lifecycle; no inventar protocolos ni responsabilidades.
6. **HTTP** completo: routing/middleware/request/response/streaming/ASGI/RSGI, seguridad, límites, desconexión y los puntos de error/lifecycle señalados; revalidar consumidores Auth/Session/View/Storage/Schemas/Failure.
7. **Console** completo: discovery, args, output/exit codes, generadores/stubs, scheduling y detección vacía; revisar las rutas de integración GCM ya cambiadas sin revertirlas.
8. **Foundation** completo: boot/config/providers/kernels/startup/shutdown, aplicaciones repetidas y aislamiento; consolidar cambios compartidos y sus consumidores.
9. **Revisar tests raíz y archivos de integración**, exportaciones, imports fríos y configuración sobre las fuentes finales. Revalidar paquetes anteriores cuando una dependencia compartida cambie.
10. **Migrar dispensas Ruff existentes** solo tras auditoría sin mapas/noqa; no crear nuevas exclusiones globales. Cerrar convenciones y docstrings de todo el alcance, incluidos fixtures intencionales.
11. **Ejecutar cierre global real:** toda suite permitida en aislamiento, Ruff y formato completos, Sonar real sobre los mismos hashes, `DOCS.ps1` completo y QA del sitio, ejemplos, recorridos HTTP/CLI/container/schemas/Auth/Session/View/background/queues/failure, medidas finales. En particular ejecutar ORM 505 y View 190 integradas en su estado vigente; no extrapolar los rechecks.
12. **Inspección final del diff y recursos propios.** Conservar APIs y exclusión. Limpiar solo recursos creados por la revisión. Informar hallazgos obligatorios aún pendientes de forma honesta; no afirmar 100 %. No hacer commit/push/deploy por iniciativa propia.

## 10. Notas operativas para Copilot

- El cwd de todos los comandos es la raíz indicada, shell PowerShell. Usar `rg` acotado o inventario Git filtrado. Evitar `rg --files tests` sin exclusión previa; la variante más segura es un subdirectorio de paquete permitido o listado de nombres de Git antes de abrir.
- No revertir las correcciones para “recuperar verde” ni consolidar más tests sin demostrar equivalencia de comportamiento y condiciones. Los métodos nuevos incluyen regresiones funcionales, contratos, anotaciones runtime, cancelación y limpieza.
- Una anotación bajo `TYPE_CHECKING` que se usa en DI/reflexión debe estar disponible al ejecutar `get_type_hints`. Comprobar arranques desde distintos módulos; una suite con imports calientes puede ocultar ciclos.
- En Windows hubo `WinError 1224` por archivos mapeados. Algunos formateos mostraron aviso con código 0: verificar bytes/resultado. Si se reanuda edición y es indispensable, escribir a un temporal hermano y `os.replace` puede evitar el problema; comprobar contenido y AST antes. No hacer reemplazos masivos ni cambios durante la fase congelada.
- Conservar exit codes antes de imprimir logs. No usar `$HOME`, `$home` o `$CODEX_HOME` como variables de tarea. Usar nombres como `$repoRoot`, `$reviewRoot`, `$suiteExit`.
- Un proceso iniciado y una preparación de benchmark no son una ejecución exitosa. Verificar salida, conteos, guard y hashes antes de registrar aprobado.
- Redis histórico de prueba: 7.4.12 en WSL `docker-desktop`, loopback 127.0.0.1:36082, persistencia desactivada y contraseña propia en temporales. No existe ahora evidencia de que siga activo ni se conserva su secreto. No se arrancó un Docker daemon para la tarea. Verificar propiedad y recuperabilidad antes de usarlo o cerrarlo; nunca emitir shutdown a un Redis ajeno.
- No hay nueva autorización para publicar, enviar mensajes ni realizar acciones externas. La autorización GCM y S116 sí persiste y no necesita otra pregunta.
- La aspiración de rendimiento debe medirse; cambios correctivos pueden añadir coste necesario. No modificar contrato async, seguridad o transacciones para producir una cifra atractiva.

## 11. Artefactos históricos para localizar en respaldos

Todos los siguientes estaban en los dos directorios temporales desaparecidos; esta lista es para recuperación, no enlaces a evidencia todavía disponible:

```text
native_suite.py
run_sonar.py
ruff-without-file-ignores.toml
global-preliminary-after-orm-results.json
orm-complete-results.json
orm-final-scoped-sonar-results.json
auth-complete-results.json
auth-final-integrated.log
session-complete-results.json
session-final-integrated.log
session-documentation-final-hashes.json
verify_session_manuals.py
session-manuals-final.log
probe_session_runtime.py
session-cold-imports-final.log
benchmark_session_flash.py
benchmark_session_manager.py
benchmark_session_file.py
benchmark-session-*.json
view-readonly-inventory.json
view-requested-paths.json
view-complete-results.json
view-complete-sonar.log
view-whole-quality-hashes.json
view-all-function-doc-audit-final.json
audit_view_ast.py
audit_view_docs.py
view-final-integrated.log
view-http-factory-consumer.log
mail-baseline-view-consumer.log
view-manuals-final.json
view-manuals-en.log
view-manuals-es.log
verify_view_manuals.py
probe_view_runtime.py
view-cold-imports-final.log
benchmark_view_pending.py
benchmark_view_engine.py
benchmark_view_route.py
```

No ejecutar `normalize_view_root.py` otra vez si se recupera: ya se aplicó y duplicaría limpieza. `view_root_regressions_prepared.py` era un borrador obsoleto de dos métodos; el archivo real tiene tres. No sobreescribir los tests actuales con preparados temporales antiguos.

## 12. Inventario exhaustivo de rutas cambiadas y conservación

El apéndice se genera desde `git status --porcelain=v1 -z --untracked-files=all` con exclusión previa por pathspec. `XY` conserva las dos columnas exactas: índice y directorio de trabajo. La huella SHA-256 identifica el contenido **actual del working tree**, no la versión del índice ni prueba de validación. Las filas de HTML/índices bajo `docs/` son regeneración documental; no modificaciones manuales recomendadas. Los archivos de pruebas conservan escenarios/regresiones y normalización; los detalles funcionales se encuentran en el catálogo por paquete.

Este inventario es del momento previo a crear `HANDOFF_ORIONIS.md`; el informe queda como archivo nuevo adicional. La inspección de integridad al terminar se añade después de comprobar que ningún archivo de ese inventario cambió durante su preparación.

**Comprobación de conservación del traspaso:** se recalcularon las 3388 huellas SHA-256 y coincidieron todas; no cambió ninguno de sus estados Git XY; HEAD permaneció idéntico. La única ruta adicional encontrada fue `?? HANDOFF_ORIONIS.md`. Se comprobó que todas las 3388 rutas aparecen en el apéndice, que no quedan marcadores de inserción y que los bloques de código y desplegables están balanceados. Esto valida la conservación y estructura del informe, **no ejecuta ni aprueba el framework**. El informe no se añadió al índice.

### 12.1 Resumen por área

| Área | Rutas cambiadas |
|---|---:|
| `.github` | 1 |
| `Archivos raíz` | 1 |
| `config` | 1 |
| `docs` | 2243 |
| `orionis` | 2 |
| `orionis/aio` | 6 |
| `orionis/auth` | 65 |
| `orionis/background` | 8 |
| `orionis/cache` | 26 |
| `orionis/console` | 1 |
| `orionis/container` | 25 |
| `orionis/database` | 58 |
| `orionis/encrypter` | 6 |
| `orionis/environment` | 19 |
| `orionis/failure` | 16 |
| `orionis/foundation` | 8 |
| `orionis/hashing` | 13 |
| `orionis/introspection` | 25 |
| `orionis/localization` | 18 |
| `orionis/logging` | 21 |
| `orionis/metadata` | 3 |
| `orionis/orm` | 105 |
| `orionis/schemas` | 73 |
| `orionis/session` | 18 |
| `orionis/storage` | 34 |
| `orionis/support` | 81 |
| `orionis/test` | 16 |
| `orionis/view` | 42 |
| `tests` | 2 |
| `tests/aio` | 3 |
| `tests/auth` | 29 |
| `tests/background` | 6 |
| `tests/cache` | 15 |
| `tests/console` | 1 |
| `tests/container` | 23 |
| `tests/database` | 29 |
| `tests/encrypter` | 5 |
| `tests/environment` | 13 |
| `tests/failure` | 12 |
| `tests/foundation` | 2 |
| `tests/hashing` | 16 |
| `tests/introspection` | 24 |
| `tests/localization` | 18 |
| `tests/logging` | 16 |
| `tests/mcp` | 1 |
| `tests/metadata` | 2 |
| `tests/orm` | 100 |
| `tests/schemas` | 34 |
| `tests/session` | 15 |
| `tests/storage` | 23 |
| `tests/support` | 37 |
| `tests/test` | 12 |
| `tests/view` | 15 |

### 12.2 Archivos de implementación, pruebas, manuales e integración

Cada SHA-256 siguiente contiene 64 caracteres hexadecimales. La clasificación automática de documentación compara AST sin expresiones string documentales: no demuestra equivalencia de reflexión sobre docstrings, no reemplaza pruebas y no implica que se haya revalidado el archivo. El catálogo explica las correcciones funcionales; las filas conservan el inventario exacto.

<details>

<summary>.github — 1 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `.github/scripts/run_tests.py` | Poda previa de carpeta excluida y propagación de fallos reales del runner CI. | `57f324ffcc2b44bc208d64678dc5ea1d1589c9bd1d7224d062bab0eee973c37d` |

</details>

<details>

<summary>Archivos raíz — 1 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `.env.reference` | Configuración de AES-256-GCM predeterminado según autorización explícita. | `fbb2d0fa6b0e37710029b7cf0dd1935b9cc0ab406e102bc27eab5a1ef5632600` |

</details>

<details>

<summary>config — 1 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `config/app.py` | Configuración de AES-256-GCM predeterminado según autorización explícita. | `976d817155e713ecadef2503885d2382347a5927520d6c8166611b4f919aa55c` |

</details>

<details>

<summary>orionis — 2 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5cf18a1a5273fda7aed0d1f0127b6692852a01b41fd0c3e745d3a6f1d9924649` |
| ` M` | `orionis/_exports.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0f76b6f8d2180060cabeec20e1d554d41b58b622f44f264ae8dc82e10f9ca637` |

</details>

<details>

<summary>orionis/aio — 6 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| `M ` | `orionis/aio/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a48807e6101e970b38ec1cf6c0e3907a7c66c2305f9f95e689ec631a90cdfadc` |
| `M ` | `orionis/aio/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `13ceda196c5a1a42dd8194d4a0fc4cdc8e892f1d5e0a1cec638b17545da87ff6` |
| `M ` | `orionis/aio/docs/en/async-execution.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `ca2d58cf3cbef955a6615cef274c5f6df1f3eacb6c9b9f0850732270c30a6f74` |
| `M ` | `orionis/aio/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `4f963820e263a58b08fca3adbb98eaf289b7e51ebdbba684372a80cfdc1ab1d7` |
| `M ` | `orionis/aio/docs/es/async-execution.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `85423e2cb45e316a3a1a45a90bf1922ab6f69e05f2b86c209fa1dc9a8cc1ae38` |
| `M ` | `orionis/aio/loop.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `40d3cde419bf02a0b0e2a50a2a50a17fb47dff0724ada25c5689ad7675439ac6` |

</details>

<details>

<summary>orionis/auth — 65 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/auth/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0947eb8a6434e3bea5b3a5d519f243af706bb14fc82fe93fa33bb8b926e2b760` |
| ` M` | `orionis/auth/authorization/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b20eef5c449d91c6c177b88adb70d2c2d2a9dcb52b709cefe9651710dd56be7c` |
| ` M` | `orionis/auth/authorization/authorizer.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `459eeffe765289b6aee613930709424feb82c3db6dff4b54ffe79664b0db50ca` |
| ` M` | `orionis/auth/authorization/policy.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `1514d3671163bb2b3f9c0cbde224f257ed902829353197d1c8e681c1f4f8d419` |
| ` M` | `orionis/auth/authorization/registrar.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `f68caadeeb3dcd734e688801fb5e978e8eb09d3c0ccc1df5a9567c5ab6e202d6` |
| ` M` | `orionis/auth/authorization/registry.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5fa8fc9383038b4ea426385b39eaa94021648be59e1b0953969d2e3054b34020` |
| ` M` | `orionis/auth/authorization/repository.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c483075c2d09dfa65cdc49f6b94332aa2cdd3f53d80aaccb31bf883540faca26` |
| ` M` | `orionis/auth/authorization/schema.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `96f8b6b01c50178b4ca19487e55ee6291dba4721edc9a9d55ef14ac5eb51eea7` |
| ` M` | `orionis/auth/authorization/snapshot.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `f290a9e7708c361a93524c73b6264df4325c358f78409555363a4d56c0241003` |
| ` M` | `orionis/auth/concerns/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5fed0cc4877ba3eaf3f9627c7965a5fba7da9e88becb271cb2db0a066e890df3` |
| ` M` | `orionis/auth/concerns/authenticatable.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `321e1f2e35f89c4c194e91fa375152fd6f781c15eb8e7b3f593c6c0a4b03d832` |
| ` M` | `orionis/auth/concerns/authorizable.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3f4f260665bb92f4cd86eb6931ea4348e9a73977ee5c02845f76f3ace3a75c89` |
| ` M` | `orionis/auth/concerns/functions.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3f60f26dccf61d8034a2722b078f9d555b67b28fadb8e9dbbfdfb87c120e03e0` |
| ` M` | `orionis/auth/concerns/must_verify_email.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a1959cdebdb1a45352f92e0e722d14484473df6305df39982e9bdace02ac35ed` |
| ` M` | `orionis/auth/context/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4776957140b9def9f23ba46965795104e8d493a235b74aadb8b295293a9d5a79` |
| ` M` | `orionis/auth/context/context.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5f20206f0631ecff810618da021d068cd45cc6428de1f58eeeea2aa6e2e12107` |
| ` M` | `orionis/auth/context/functions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3696f9b1072d7049aab0391f635f37c01b7d797ba3fa7e56b8f5537422b52d37` |
| ` M` | `orionis/auth/contracts/authenticatable.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5cbb790cc4f6e932e972f17cb633ee7cdbaf8af664d7bab5ef2c30935d521f45` |
| ` M` | `orionis/auth/contracts/authorizable.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `89c9cd4a509c9b3db07111ebaad3c8267a9d323e4a66b61485921ea5ab2b9801` |
| ` M` | `orionis/auth/contracts/authorizer.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d8f6c72f1758001a1d1fa717cebe9e9fe4bba50bc02ed28c0305169fdd58c67e` |
| ` M` | `orionis/auth/contracts/context.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `47b9ed672385b0fbdd91624240830a9b7af515f141fcc281217b60d874e062a0` |
| ` M` | `orionis/auth/contracts/guard.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7d4b255794ea19103c1f7d6266feb350f023792708a14d1539180858d884106c` |
| ` M` | `orionis/auth/contracts/identity_provider.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5ed176d24a77cb4d37d8072fdbf25b81f100bb5e7ae39e943f5e7121400146d1` |
| ` M` | `orionis/auth/contracts/manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `46dc305fcd10b8135f18a2a8200b594a84ff984d410ca8009dda4149fa0365dc` |
| ` M` | `orionis/auth/contracts/permission_repository.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5d85cd1bd32270f2e903b02e6c291704d794ab3ad572f34601fda484583df283` |
| ` M` | `orionis/auth/contracts/policy.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0cce5bab3e4a99c45656fa909317564242d09eaa12db26457fea0cf150081d36` |
| ` M` | `orionis/auth/contracts/session_guard.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7c06e5046026df115983618d67252fbd1278bfb6255631b27e0f33767e8ce67a` |
| ` M` | `orionis/auth/contracts/snapshot.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ab35ca6f1495a52c929d1692c84c742f160ef00f7ddeee58b7413f049db9e5eb` |
| ` M` | `orionis/auth/contracts/token_repository.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `8b4cdd23a560e1b4ca668881a3fa38e34fdb9a11a621e2b6ed656632ef3efad4` |
| ` M` | `orionis/auth/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `2f54481d241e64fc56062debc81ad647099b75b6e814d351a340d82c437019a9` |
| ` M` | `orionis/auth/docs/en/account-recovery.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `b9d5345ee8ef4d37c04fad5fdf8b4e8c10e24c6e89c05055dc548cf3548d9061` |
| ` M` | `orionis/auth/docs/en/authorization.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `481ca481f896a813d1ac965e50ac5bc0cb0f4ec0e169299f653446b28f7cb74b` |
| ` M` | `orionis/auth/docs/en/identity-and-session.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `57065142805feb8deec348245448f7b06dc63a3d5d5efd32617c9c8f5aae6c2a` |
| ` M` | `orionis/auth/docs/en/personal-access-tokens.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `f3932421abd0f493a0d40d8424a0bb64d99db35244ea574c637b3e7a02e9a060` |
| ` M` | `orionis/auth/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `84fde1acd03fa2f5801ad386c7f81110737789a862561c7970c0fda3e47d8784` |
| ` M` | `orionis/auth/docs/es/account-recovery.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `ec6a96680b5da6ff3e2ff079e8a759fde5db4859dd4f29d83842b25456a48ef4` |
| ` M` | `orionis/auth/docs/es/authorization.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `81c51745cf88b3916a85a3ef704f389914b1d97fde8547232621f91333120487` |
| ` M` | `orionis/auth/docs/es/identity-and-session.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `b13e8760df0d247b4aab983a56c4c0cbc7a3727118346469b85f14ea50cda3e1` |
| ` M` | `orionis/auth/docs/es/personal-access-tokens.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `f91eef746321a4ecaa875ca7cbde3d7a31800e7f5ae6b853c35423137de14c66` |
| ` M` | `orionis/auth/entities/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `bd2d7eb4a90f303c6689918ff641afc5a4de6ca27baa26238d054751373cd31c` |
| ` M` | `orionis/auth/entities/access_token.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4ef90899c32f538e40bfb96f97b9d16afa2a68db45358598ddaef5b1c13b9b9c` |
| ` M` | `orionis/auth/entities/guard_result.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3cff25bc8bec1a65cb0e2d88d0287b41d747ccb4bd02d6f23992f899cf6fdbbe` |
| ` M` | `orionis/auth/entities/new_access_token.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8932edd58ef6534e26e52979141b8006250e1c45e58c75703502f4b6fe2f1094` |
| ` M` | `orionis/auth/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `508e3a55e25b303dc25f114bd5db07b856ac7d81484f1bfb6ae0990e0ac37deb` |
| ` M` | `orionis/auth/guards/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `87e1a69377108827dbcb5639023eb7be708687316b60a3869d0026db8ad699bc` |
| ` M` | `orionis/auth/guards/session_guard.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `fbe3c3aa68bea7e64979ac82fa617908da7626de981fbc8465b6fd797abdffa6` |
| ` M` | `orionis/auth/guards/token_guard.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `f852419d441ed4bae79248d86798a7866b7c0b685e21ef320bbadfc809c6fa99` |
| ` M` | `orionis/auth/identity/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `76e96321eb1459bd187c13f5e6b6195a88b9d3f510fd2aff95f200b863dbedc9` |
| ` M` | `orionis/auth/identity/provider.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `553a1b0e21398f243a3bd41d78ccd7d8a1e42f44a5315d9b8a0cf3cc2c0d7d20` |
| ` M` | `orionis/auth/manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5533289e6d5a418dd1e8290941392dde55fc3c0bbecfa9ee92e7676f109b92dd` |
| ` M` | `orionis/auth/middleware/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ba508c6ee132695e6fc9f5f3a7ccf58dbbb3c276cccaab6af377bbd66fb6175d` |
| ` M` | `orionis/auth/middleware/authenticate.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1ccccc9ee4cbcd884eb81aa1d69e67e6d907bc23ef08ccc8d93764704b212923` |
| ` M` | `orionis/auth/middleware/authorize.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `37d11ca28319c6874909d8e217d5a329a30ef4eff98f639c8b444a58d1d084fc` |
| ` M` | `orionis/auth/middleware/guest.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `13a3b16c26f01919ad74afe86e670474848d423faaee20567788eb97096ff851` |
| ` M` | `orionis/auth/middleware/policy.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `cafb6ff432e92f5fcbb0696a987e8f2cc6bd8bb34394c9a8345c796c6b8b2af9` |
| ` M` | `orionis/auth/middleware/resolve_identity.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `929f6159b57025714a7cef47b6e31a7ca6c9a54384dd12ef24f85a1ef346e203` |
| ` M` | `orionis/auth/passwords/broker.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d1f3f5394cf515e04b11f46f704295d73f0c14da14ab40d7d623bd36dbe96599` |
| ` M` | `orionis/auth/passwords/schema.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `d0a37398582c8024ab8fc745439b4ea63214adb6a8d559d1b3ab5a0e259fa898` |
| ` M` | `orionis/auth/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fe55cfb120a3abb2af9f774cb8309f03085315eb3c8d8d7367bd8a79d82e73be` |
| ` M` | `orionis/auth/remember.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7c4b963cbe3e281878dbb9b294c846d824f3585c29dca53dc989d464a932a21b` |
| ` M` | `orionis/auth/tokens/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `86d3444aee0a6a1997bb12aaa46c69dfeadc2b2c013ddf95fce747329fca7129` |
| ` M` | `orionis/auth/tokens/functions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4915ad4f9f74464ef1016e1e72131e94d15f38b57f3b208caae34a56f1042b91` |
| ` M` | `orionis/auth/tokens/lookup.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3fd7d1e4100648a734d1f2fc1988d257fc8fdaff642cf53ad86768cd324ee765` |
| ` M` | `orionis/auth/tokens/repository.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `fa24b9c6e21512581a82d92a0dc4ffd66bba08da6ad8856a287c6c313d5be23c` |
| ` M` | `orionis/auth/tokens/schema.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4ac26b74a61eb09acc8bbe6ff44c85817f1b68d63b1da77864aa22389b74fb4b` |

</details>

<details>

<summary>orionis/background — 8 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/background/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8ca10ad1636a8c1b4226092b2cbe8384edc29de857998d41e28338fc8df64e12` |
| ` M` | `orionis/background/contracts/task.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f2c28269fd088ea8acd51a600938ee0abb29a7195f220be0649eb082b04e9e6f` |
| ` M` | `orionis/background/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `46dd92069459f4bcdad7416e9f812f07f2ff605a1fb2661416aa07b0f2c98d5d` |
| ` M` | `orionis/background/docs/en/response-tasks.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `022c61c62f082d9ab902b3966222dc83e13a9d27d33e42dc5ebdfca8d93b3e26` |
| ` M` | `orionis/background/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `a37e5967b40bde8ead692fcf1efaa9f53cebcf3dd20121aeef4f7a74046370f6` |
| ` M` | `orionis/background/docs/es/response-tasks.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `a6358f1e1417939fc616b4424d64d9ff8086458f0f2030571af84fb4878e22c7` |
| ` M` | `orionis/background/task.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b38f3e44e97e65e535707c229eddb648015bc23087f423d4f8fab8f1d26c383a` |
| ` M` | `orionis/background/tasks.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5920ac4a87a8a7a40f1bd6e8602aa0e51322d1a495dd323cad508726ec0d8a31` |

</details>

<details>

<summary>orionis/cache — 26 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/cache/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `9a18601ae338992eeba9b83bd7e5cd05ec77b03cbc7f7f67f54ca497b748b6c3` |
| ` M` | `orionis/cache/cache_manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5c982adff694da0b8858d23e1b1f59e90e4096afc75edb0179e66f170419136d` |
| ` M` | `orionis/cache/contracts/cache_manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c992ecb9da6be19c633f0a5aabb78f9f864beb7ef2e494c26411282b5bdae963` |
| ` M` | `orionis/cache/contracts/file_based_cache.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `52ac8aee164b6ddd875e6c9545e844d3c222b862674e060ea0b29efe9bb84343` |
| ` M` | `orionis/cache/contracts/repository.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `26198573b5bf98268693367da5ecc4514af1505f8bda8a66d511c63e5e9157ae` |
| ` M` | `orionis/cache/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `c07e8f9d34763de99947db08aa32a5d3e12718f434098877a0b17c5aad67eb3d` |
| ` M` | `orionis/cache/docs/en/caching-values.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `a7f21145b1e0311b6858bde2040d99ce36960d3a703accf08ed35f1b05393811` |
| ` M` | `orionis/cache/docs/en/source-artifacts.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `e1379fd9872649719b6360e5651379f75a8698b604023acbbd4171e47b3009dc` |
| ` M` | `orionis/cache/docs/en/stores-and-locks.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `e8027e7d1e278c8d67b0a0e5f5e472d8580aa0e83a1829884cabdd8e38696c88` |
| ` M` | `orionis/cache/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `eea84a6947dbe717be7db8151d68d4a412f50ac164557699d029ac3ad35c9836` |
| ` M` | `orionis/cache/docs/es/caching-values.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `bffb36dfa043c1f468b6e127d433afc2f7509a1aa7b1be7e7320436240646d5a` |
| ` M` | `orionis/cache/docs/es/source-artifacts.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `554e4947dfa6a5ef41b795db984fb20b59ab0780a3f95a5bebc77d6eb7f64827` |
| ` M` | `orionis/cache/docs/es/stores-and-locks.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `0cc1bf497369936ea96965edfb40011ad20b9e47d9bdf4356f949940c87ba483` |
| ` M` | `orionis/cache/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `26e2a41249e1407009f88fb5dfa8c6787b4860639a679433c0d6f56bf7f652d2` |
| ` M` | `orionis/cache/file_based_cache.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `265f5f7a4e37e7a027adb4a1ea0f8f1d942a007cbc759c75fcc95a85b623accf` |
| ` M` | `orionis/cache/locks/coalescing.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `af18e35f4d986ea980ef9c1d2584c3569e0a0b4ed64ff46036ffb961e10bdad1` |
| ` M` | `orionis/cache/locks/lock.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `9ac00aa0588ff1c331461d268a073303a3efa3c25c36ff9417ce6312dd5df097` |
| ` M` | `orionis/cache/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `d2527578ab8a4868ab5c39c9a333a3e8d72cd0d9fd465e107915512f282b8854` |
| ` M` | `orionis/cache/repository.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `65b030da9f3bc8350a127a9a2161f48dbe4c60e0635f65f1650bc5021da8d154` |
| ` M` | `orionis/cache/serializer.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0db038bf827a15a1fbfd35358ff2d5df066f17714331ea19314cac8180fb8024` |
| ` M` | `orionis/cache/serializers/json.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4c0d9668338754954a283957c554bf2ffbda0a55f7c734bce52ca607859dbdc1` |
| ` M` | `orionis/cache/stores/database.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `374bd1bd683b2b3ba3c816ad581dc424fc96e0e5765ea1620b2bb4110a6a7705` |
| ` M` | `orionis/cache/stores/file.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `998ad2799cfccd298db2d339ef71fc8f6da3fe599e0167db9c15ac20d293a3c9` |
| ` M` | `orionis/cache/stores/memcached.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f0b7b59de4295a82030e0c0e038b01c68b478671d4ed623ebcbf0cb33f2a16fd` |
| ` M` | `orionis/cache/stores/memory.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b75ea9fea1eabd5c05643a05aed518789e99f241e80d6914859977d82f22e303` |
| ` M` | `orionis/cache/stores/redis.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `1d56a1d0e262177c747474eccbe730d0f65df0f6131d74e2a867acf368dc89a0` |

</details>

<details>

<summary>orionis/console — 1 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/console/commands/support/key_generate.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3aee5908e40dd32d9f678307a961c312b1b61d74cd61e7b5a050f4048ff56416` |

</details>

<details>

<summary>orionis/container — 25 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/container/container.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6d41b0ada6f4d2607e2a84e6cdc0eb9247d44f21429d496b0dcf8aacdd49f10f` |
| ` M` | `orionis/container/context/manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0c4351972d567489c1e78ac329cd48ddca48ba591385f7c0cfa1aea9dfac9778` |
| ` M` | `orionis/container/context/scope.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `13858aeb0bdfe16f859118eb1adeee26dc5b9473b78b19bc1e2e781e4116178a` |
| ` M` | `orionis/container/contracts/container.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `16632307a72cdaa5a2c779b1dd6a714e34ff7272c9cbda5c9352de150d525e4b` |
| ` M` | `orionis/container/contracts/deferrable_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `879d10625df5bdb682909d3f80b501cab0d9ce4ff1aea8ecdb1e7dec04e9ea86` |
| ` M` | `orionis/container/contracts/facade.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `040ad49299d27f23304a5c8fa49ef199fc56fdd219ff3c209f052d7806ac99f7` |
| ` M` | `orionis/container/contracts/service_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `402ad8ae662452b83eb42e388ecb80daa953c39ec8a37df4ee6e1bc07994a55d` |
| ` M` | `orionis/container/docs/README.es.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `665605623b7aa59e7e22982228fda6c25e2ce2a314dd16fbdbdd7efc3b66fbde` |
| ` M` | `orionis/container/docs/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `b7a45a778cd1dadc4eb42e4728e7980ea3ad39c357d8ddcaca291b6c9f4052f0` |
| ` M` | `orionis/container/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `b57bcc213bc61b89f3b9da0e4383638070b4a0622819c53c5725c7d3e27a7f45` |
| ` M` | `orionis/container/docs/en/bindings-and-invocation.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `c60f506c2f291df232d2e1dfbccf86dae4ef6fa7cbfaa6b2a6f0295dd077a5d7` |
| ` M` | `orionis/container/docs/en/providers-and-facades.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `af9338f74411fcfcb2fe8602ec61603efd4707e5e4fd2bee4913f65be6de3e0c` |
| ` M` | `orionis/container/docs/en/scopes-and-concurrency.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `0d0f1ceede10b400282e478a287f27eda90655a3badfd7a51a422979b6d5acfe` |
| ` M` | `orionis/container/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `694c8667408b00d0ea7ebf104db586b1ff95c5c9ed68461fee3d67c66f0132a8` |
| ` M` | `orionis/container/docs/es/bindings-and-invocation.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `cfd676eca8029b20db0ff81409e40d3bc99ab0409fe3d32ef1bdb0a7bfe6cdc7` |
| ` M` | `orionis/container/docs/es/providers-and-facades.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `62f3e72efe63ca7411c66dd4109480a7003f09d74caf031224df799da7d209a3` |
| ` M` | `orionis/container/docs/es/scopes-and-concurrency.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `56e77812cae482cfd68b7d02530b0365d629d01c29b15e2a6e9ed5f39b9b2f09` |
| ` M` | `orionis/container/entities/binding.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2125526667ebd4b939d8af040ddff2329b68b8fa788e7876ed1f6944be85ed22` |
| ` M` | `orionis/container/entities/invocation.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e43c79f3b38241a0e0805d58310608b65f2dec6b618bc35eb4328867987eb4e4` |
| ` M` | `orionis/container/enums/lifetimes.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a10fb526825fc13be500bc4b11ccaf09375b61c449d78685d914a918e7894d96` |
| ` M` | `orionis/container/exceptions/container.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4d71f62d78d47bfff3e1996b4995b47d27a8905319bb0852d1c53cbfafd6a1fc` |
| ` M` | `orionis/container/facades/facade.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `dc98f84c2af4e452948e3c9680a34a812675a466065646f745681a3e322385b1` |
| ` M` | `orionis/container/facades/meta.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a12138d0f498252e0123c830d9bdf4ad89e8df02367ff89b4f0f3784e19baf91` |
| ` M` | `orionis/container/providers/deferrable_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a1f5db4d811f8f690568963e39408aac61f4bbd58778a34e268f5c02c3bbaaf2` |
| ` M` | `orionis/container/providers/service_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c1091225bb9e58279d86e50f54bf30bed3b6bdc125e460ffd8cd823cb7564e55` |

</details>

<details>

<summary>orionis/database — 58 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/database/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3b4d2035eef22896749ff8e072e75e7394c38bffdac04baa8498cc6dd79b796f` |
| ` M` | `orionis/database/compiler.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5376e3578bd4cad290d64359d6027a90d5a35ace6bbc48b6bb8f85db148b21d3` |
| ` M` | `orionis/database/connection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ef6b59cb3e816492e6cc84f22156a6cf66540dae46c517ad817b94b3ac26ae52` |
| ` M` | `orionis/database/connection_manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b11d59525890c7255f493d3876be5e18b1daafec00274bbdaedcdd16cc0ec3ef` |
| ` M` | `orionis/database/contracts/connection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3034cef9a2d5e226907b5958be521fcec48d9584b23244143dfbbabc0d302c3f` |
| ` M` | `orionis/database/contracts/connection_manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c85b6e061da108fe71e19f633756845713bfc3c2ad2507295793aac843cd5d73` |
| ` M` | `orionis/database/contracts/migration.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a3263cb7ddd5512b64d7d7fc1452a71cfeb823e7ce5eccf715ad7dbc3ca2fea0` |
| ` M` | `orionis/database/contracts/migrator.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6afab18efed0bb1d0049b1c9a94dd826d2250df43f39f80f13769c70b03f0601` |
| ` M` | `orionis/database/contracts/schema.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `44550373a16c7442843a1e84cca2f706888f7ee7d33884a5c41fc628383e0fb5` |
| ` M` | `orionis/database/contracts/transaction.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1906da595f877f7cdce69f6f6314f2dc3201244991a3813f924a819607836176` |
| ` M` | `orionis/database/dialect.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5726977de854aa5bf2105e582728377a16ec0fbdf8511c9a9b9e5d239e05431c` |
| ` M` | `orionis/database/docs/README.es.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `27b8d5ca7d2b16e3b95fe8009efe32af394e93f2b47eb06814bcd4cfbc949aec` |
| ` M` | `orionis/database/docs/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `4d6ac53e84a016a48598b44c92fdc27f4514dcb9079ab658abbfcd8eaa6058ba` |
| ` M` | `orionis/database/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `fb3080b086c9b7cf7e7e30324dea92d166d027bb4773eb7e97496e1ef2c994db` |
| ` M` | `orionis/database/docs/en/connections.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `9677c10f03f31e8c111c4a8f2760044fa49ddf7297a0104556369654190f39d5` |
| ` M` | `orionis/database/docs/en/dialects-and-production.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `6559eb668463e37d7cf3808fc100b18cf51144dc1479eb79ea1faae6aa72bdbf` |
| ` M` | `orionis/database/docs/en/migrations-and-seeders.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `f3d88d4ae8d62c5df8b022762d741747add349c688195043f5ed5219f07ea0cb` |
| ` M` | `orionis/database/docs/en/schema.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `13fefd3394f5fdaae14008a290af4598827f8b43557fe71ccdd606ab7157f63e` |
| ` M` | `orionis/database/docs/en/transactions.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `1c7a5f271d6183116541752e0d37ae2e482696720b12752ab3d5e936a915264c` |
| ` M` | `orionis/database/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `f20edb7e8b5bd3f1d9a7c9fd5da23e30c48519a45f4b1a82e9a94277a6f602c1` |
| ` M` | `orionis/database/docs/es/connections.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `f41ab1776747e16bb03c3a8e34b6c9d1253272458cdf4682d70d14718cef5265` |
| ` M` | `orionis/database/docs/es/dialects-and-production.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `e0db63d193a845aee6166c7bd00259b0ffe819d0661bf652ce553a29a9ea8b96` |
| ` M` | `orionis/database/docs/es/migrations-and-seeders.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `940c1218edff2861fc7995be2f32ce52566287214f2760d164ac13195f87bbd0` |
| ` M` | `orionis/database/docs/es/schema.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `b3f534b438dfe2d32d5934f3448c57a9cb887b1fef8d6587c4321bf334d1464a` |
| ` M` | `orionis/database/docs/es/transactions.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `ec38945e1eb28616765fed0e366087a1ce8faa124d71c1c2ec6c23e34961c15b` |
| ` M` | `orionis/database/entities/result.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2a14fd4f82382e6e5a3ba664e7df89505a712eab2fdbd249ad0f784da19161cb` |
| ` M` | `orionis/database/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `79fcd8456b5bfa29f526f0407cb29c9eb2763e48bc39d97a336ab6d600a95409` |
| ` M` | `orionis/database/migrations/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `dd8b7afe028bf8f326630a8866919e0a8cb1591c09c75472432f8c51636f7267` |
| ` M` | `orionis/database/migrations/context.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ac64c161700abab00acc82ed6ba49ff78189c91f59b53c256e41fb337247ecfd` |
| `??` | `orionis/database/migrations/discovery.py` | Descubrimiento común seguro de migraciones/seeders, aliases y colisiones. | `c68922b12f3cfc449fc3353845c36aaf41b5b32bda2dc3df843562268fc2d235` |
| ` M` | `orionis/database/migrations/events.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `bbf30178e806ba25e4dc203ffac14cfd9e0a3b746d591b9f0785ab905358e63a` |
| ` M` | `orionis/database/migrations/migrator.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7696204ac9d809468adbb7b1ccfe7de8f879faf45bf32e83b75b6d733a61cee1` |
| ` M` | `orionis/database/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `673aa1a6183eb684633e99fc640b699fa9f07a0ecca9a25bbbab289b007ea37f` |
| ` M` | `orionis/database/redshift.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `59a74b2c36bcfcb51c0e9d1022e967912f2d6d308a46db02c30d7f0a35eccfa5` |
| ` M` | `orionis/database/schema/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f84a12aff3d794d4a5d5e8f68030729f86659b1439033e4b42f1eab51785bc5d` |
| ` M` | `orionis/database/schema/blueprint.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `388d630f57357fb962e514c995f5a3d71bc21de14dc1ac611eb4e1bcc2b795b2` |
| ` M` | `orionis/database/schema/blueprint.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6a26da5c4e6b2a8cbe7a3f1c7980a7d1545629364f793670509b87bd2f5630dc` |
| ` M` | `orionis/database/schema/column.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `8a509af6de9b214ed522c3220b2666dade9a1e3645e6bade3732da689b708a20` |
| ` M` | `orionis/database/schema/comment.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5172df6400d95d62c11f20a05989da58cf0c9386d317dc8b673e33fa96647b91` |
| ` M` | `orionis/database/schema/definition_bucket.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ebcdce24c2b335e21b4b12746fd1d2bf8b90b84732bee9a3a109812f7ffa7a7d` |
| ` M` | `orionis/database/schema/foreign.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `89e543d27378e01723ad900009772d80af7b000890b313daa398852ebd7edcd5` |
| ` M` | `orionis/database/schema/index.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3a1c4608cb3d4a60b495d2fa71e0361d71ec1c6ded82bb33379e07ec2ab6cd36` |
| ` M` | `orionis/database/schema/primary.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6cb3770055a9361edf419bab0496d10bbfa59cff99c74533b02aaae7547ba928` |
| ` M` | `orionis/database/schema/schema.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `fabc7e1315e93aa7608ceb2f887078adece3ebd1b54b81ffa1fe58eda6c8d257` |
| ` M` | `orionis/database/schema/table_creation.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6d380be313f0bbce7d349474a94c0e47eb51302981e9bbede92dff0eaecc59cc` |
| ` M` | `orionis/database/schema/timestamp.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `53ad59c1dfc6ef5c07c2a6ea60706a8fc1995bbe17564f1f50403df933e07899` |
| ` M` | `orionis/database/schema/unique.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `6cb3feb5d79c317580438f766ad113b1bcd116a8a03120cbcbec17cb248bdc73` |
| ` M` | `orionis/database/schema_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `19789db7107c2f07e35d2a9c3241cb39bbe9ca6d7fe019f50a044f41ac11e98c` |
| ` M` | `orionis/database/seeders/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `23066e67628bd626c832a8978c2484702096eefaba66d78740e8c3faf479046c` |
| ` M` | `orionis/database/seeders/events.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `82812b8ef2c1bbb18d9a2e5084358599ab75f8274761eccb86707bf60bac9cbb` |
| ` M` | `orionis/database/seeders/runner.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `08d45c200681db318dee98d3e09d1bfb18ce56dd3ba879050cce0e63067cc575` |
| ` M` | `orionis/database/seeders/seeder.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `cf0305593328c555983ef98334d2d192fe22590705d4ea5f00d98b3284133f45` |
| ` M` | `orionis/database/threaded/connection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c6c0ab7fdeffc34079e89ed383887e6939ed8152dd3e79365d30a9930e7dcfe5` |
| ` M` | `orionis/database/threaded/engine.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3da4ca6c8b71f37b38ab1c6702d3cbffe69ffc8536543269c4560eb9c43b75b1` |
| ` M` | `orionis/database/threaded/result.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6100d2a882391660e3a6e96dee905b761511e35ca3b93baac23961ad6f1055d9` |
| ` M` | `orionis/database/threaded/transaction.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `350f874fedba24c47e8bb8659439b4f8deacdadfd0d80094d211c397583a7e47` |
| ` M` | `orionis/database/threaded/worker.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `2918a972e3076c4c29e2057904944c840fa458e5f8581df990fe3a1ed6acd853` |
| ` M` | `orionis/database/transaction.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1d374e978174af1d31cc032c84424fb3255598155dd591de775f134e1b86a5a1` |

</details>

<details>

<summary>orionis/encrypter — 6 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/encrypter/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5c04e146c0cbdc5be98bc9341b1511dd3392664953c6864a266c24ca3fb00d09` |
| ` M` | `orionis/encrypter/contracts/encrypter.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `afa1554bf7c2f73b993a23b4d4584011f7f621aa9f2d2bdf6a69cfdb80fc0d3b` |
| ` M` | `orionis/encrypter/docs/en/encrypting-values.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `796ca5eaf373c6c1b3794ae11dc00f9b7cc3a7a310946a0d20b060bfd042c3a3` |
| ` M` | `orionis/encrypter/docs/es/encrypting-values.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `99892f426cd98d688a637f9730ba73e44ae95a36ebf6a5b95f6ff644a388d1c7` |
| ` M` | `orionis/encrypter/encrypter.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6ef220832530bf7dc8a3b8ffa1fddded0a407039fb98175e24011772e980fb26` |
| ` M` | `orionis/encrypter/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e410cb11bfb777ec947b0d6149895560678f4ce052a361254d68a374fb5ddab7` |

</details>

<details>

<summary>orionis/environment — 19 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/environment/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b5d8fbddebaf8fcfcceca52d68af0aa47c0414f2a57cb34b1003488acf8d5648` |
| ` M` | `orionis/environment/contracts/caster.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `78eb7792776324148c4d83dde31b54773c1ad4476806e264ffdcfc487aec1b4d` |
| ` M` | `orionis/environment/contracts/env.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d254b400b2706a7fa7fa9e2c9791df7740d7690be965ea419be6b97f3cc8417f` |
| ` M` | `orionis/environment/core/dot_env.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0ff05d116ec89b51bdbe77e81bca1e6470d548f790f563d0412f56798a5f63b8` |
| ` M` | `orionis/environment/docs/README.es.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `c2ba04033c78b6a67741ff0ce4e787a3d2aea216fbaae1ec7f945a283053f2ce` |
| ` M` | `orionis/environment/docs/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `209d2eb56ce4119604c1f27f3b35ba52ae5c7457c064216de86d8c5854323633` |
| ` M` | `orionis/environment/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `47ac942db7316dc3c546635799872e801c1b551e4a1b70f5ec0eb46a3d541ecf` |
| ` M` | `orionis/environment/docs/en/operations-and-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `2bf9f06548bd2f83ed54c0ed67e3b00ecf6b6f6e9e112a161bedf055e5c097f4` |
| ` M` | `orionis/environment/docs/en/typed-configuration.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `86102a1875345dad6b10ddcfaf6601d30a801d3eca093e46c4c4514bd24cf859` |
| ` M` | `orionis/environment/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `32ffa683557a6ee6e638aa5aafeccbd13c1a9a2aebaebc6ec0caa9cdd7791851` |
| ` M` | `orionis/environment/docs/es/operations-and-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `281e43aeabdc9cb560da38d8c3987743b99f125496f69c1de60c59eb54000e36` |
| ` M` | `orionis/environment/docs/es/typed-configuration.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `dfecc2e86a1449fc6f438a198b51809d054943a636cfdf06a395db52a792f68c` |
| ` M` | `orionis/environment/dynamic/caster.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a7e174b24a87663d03d065a56074ac14afa6c66af7e68c896f39a7150664ebe3` |
| ` M` | `orionis/environment/enums/value_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `604554c154df5d7e4c0e5df9c4af935f992a29cbcd2192469a285c5ab71f6894` |
| ` M` | `orionis/environment/facade.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `98f79d9d2824cfae693d99b6b9da28824b73a0b3cf369c5a52a0c507c88e0cd5` |
| ` M` | `orionis/environment/functions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `79910e9bf34778d6457e0d638058965898d3e023d05c220912731c0af0d82295` |
| ` M` | `orionis/environment/key/key_generator.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e962006699a48eaec24aff0686d1231bdb20c52643e3ceaa09f7e30249dda6fc` |
| ` M` | `orionis/environment/validators/key_name.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `221eb927530edc4e3442915b01eab9965f9dbf7846764635bdf24380f95ede47` |
| ` M` | `orionis/environment/validators/types.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `497632adefd3adee9bc8be26d3a8e94563f09bff75f4938a3cee8b4ee1bc1131` |

</details>

<details>

<summary>orionis/failure — 16 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/failure/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b2c9657c55da4b70bcc149ad7367b29ddf776ba203b69e2003ae68a01a2d3574` |
| ` M` | `orionis/failure/base/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a083abf0edf853f2e89a82c9849924aab0f956d485b0568ad017cfcfe08811a5` |
| ` M` | `orionis/failure/base/handler.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a58162952eafdf361a54eebe622e39d9871b103ee0d1a2fdb8d94eb43a03348e` |
| ` M` | `orionis/failure/catch.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2ec81fd4a680c69b32c486712e321c81ce54ab2a7fb83df88c2cc255dd7c2739` |
| ` M` | `orionis/failure/contracts/catch.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `81458b6e934fbc53e4c09709cf83843a7402bd8b9f44d416fd9ba6257356cb99` |
| ` M` | `orionis/failure/contracts/handler.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5526ff13dbe9a09efb94fc4377e795ea6544348bf0719422feccfa335767e7c3` |
| ` M` | `orionis/failure/docs/en/handling-exceptions.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `ed520c4daaca4f30a3c2506567bd8c817585a86550c390e20ad479b62167cd50` |
| ` M` | `orionis/failure/docs/en/policies-and-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `4ace6709ce0213209d39ac9e7fc5721b006aa40bdc8dddc9df54a946a225809a` |
| ` M` | `orionis/failure/docs/es/handling-exceptions.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `953a641961ca9ae8559fb1a2fefa818bd33043bfe4e6fd841488a0832b21eb68` |
| ` M` | `orionis/failure/docs/es/policies-and-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `4b8e22619434ff43e7c793bdd81656d6345ac76cf7e5042019162b6d9cc9c554` |
| ` M` | `orionis/failure/entities/context.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1ab3e8baf070349aea81712c99c195176d9faf24fbf250144ac1f0212e6cbf5d` |
| ` M` | `orionis/failure/entities/handling.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `955100a3c9a97b0ec102234781f3f1194a2286ce373194d3a651d7881bdb3c0a` |
| ` M` | `orionis/failure/entities/throwable.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e50040b1f105eb78171145eddf7c850f087f1529c97ecd23b579896159befd74` |
| ` M` | `orionis/failure/enums/kernel_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `bf6073ca7604dbc40adbd54d848e409456b7a2cf24c9f3109a6542b69c5e6678` |
| ` M` | `orionis/failure/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e8bbb5d2fdf1f2364ef2150b95d4890eb0b015e73b8fd7b5d4e168cdc071fb80` |
| ` M` | `orionis/failure/runtime.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `06e679c4b26703170533c4eba65ff513f98d796e7728cbbc1995e7bfea58899a` |

</details>

<details>

<summary>orionis/foundation — 8 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/foundation/config/app/entities/app.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `9d1e5164d32e79918cf3a090510f6a2667377652654fbbcaf81cb3309d23733c` |
| ` M` | `orionis/foundation/config/app/enums/ciphers.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a63fe7400a498ed3034219747eff3c7bbd9ebe30ed51cc781235b85f7ca1a8be` |
| ` M` | `orionis/foundation/docs/en/configuration.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `bea4270a6c326520f1fdc9bbda733c436d76af3c2581cbac37d0d120a3644ca0` |
| ` M` | `orionis/foundation/docs/en/documentation-audit.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `91c692d376fad9f6920226551e412ff7aaef1e412a7653c8ae5d382e6691a166` |
| ` M` | `orionis/foundation/docs/en/getting-started.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `225447eb080b29e4084276cb35a2f5618c79983dd4339f13e89ec1a37b9ed424` |
| ` M` | `orionis/foundation/docs/es/configuration.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `d6274f43466941f9ab90cd4b38aa71122085aebe5da8aeacb1df504377b078c6` |
| ` M` | `orionis/foundation/docs/es/documentation-audit.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `8f0051d7a3af9fd5d3d2de152db7d179d6b1b99c4ab87ca04949b9301766adb5` |
| ` M` | `orionis/foundation/docs/es/getting-started.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `8a823c15a46832140dd83471c53815748e919d173d4dc8da1da80123c49c9ebe` |

</details>

<details>

<summary>orionis/hashing — 13 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/hashing/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f8d552ad040db462d266a0adbb30bebab108edff0c45376af34638c883586133` |
| ` M` | `orionis/hashing/contracts/hash_manager.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `563cfe87225f98b25757c0b01b75fef1a4122ac819e79488c1c58e989f4d78fc` |
| ` M` | `orionis/hashing/contracts/hasher.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c68b1ef0ecd0a9e6dca24ebf84c1d5fe26ebd6d67c666040fe190a8ca3147f5d` |
| ` M` | `orionis/hashing/docs/en/password-storage.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `d1a375ade20c043c2410e62b81c06b89666039c26f762fe0ca2a1805e7fd2695` |
| ` M` | `orionis/hashing/docs/es/password-storage.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `73964b295674ad8331423c209af85b8a5008f08d3a471e8621f50e88de780158` |
| ` M` | `orionis/hashing/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `580874c2b060ce60a649ddf942cd9ac5306d3ce49e348681594fd96105139455` |
| ` M` | `orionis/hashing/execution.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `bac6019523b49b793f989c08b488fe60472b61d79f7e5cc35f2f870ecc47bf40` |
| ` M` | `orionis/hashing/hash_manager.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f31facd3da8c724b721d1ef884c9a9051a9cf058507027f7c8bb9d2d4bfccac1` |
| ` M` | `orionis/hashing/hashers/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `dd9c5bc696e404b228149bc51fd3a02567312d150fc4262b2d9de1a2621e8623` |
| ` M` | `orionis/hashing/hashers/argon2_hasher.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6eae53cb118380b388112a24e1e785d9a6bbef2e39a3b7959da887c4c8cd80e5` |
| ` M` | `orionis/hashing/hashers/bcrypt_hasher.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a722d8e022d972479fbc3fc60115ea2c1e73ab9b0bff132e8747f4cbf152b40b` |
| ` M` | `orionis/hashing/hashers/functions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `16b9f252240b9d2d11b6501b2ee68f08dca447de07d25dc1bf6d4eff3422e537` |
| ` M` | `orionis/hashing/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2c6fd4e6ddd293efed15882557b7b336640ebca43bad70930955ff519a20fc0c` |

</details>

<details>

<summary>orionis/introspection — 25 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/introspection/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3da6c6f95005a114800a9967edc0d8333a94e86068ecdba3dae80946cd4de957` |
| ` M` | `orionis/introspection/abstract/contracts/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `f2af2f1d338f70bbf7b1ff05e95807e575e599ab2f25c5e052fe7223642e01c7` |
| ` M` | `orionis/introspection/abstract/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `bf1d2e80e25a1808be88118997c55dc9c0a8abb59f9ea3de7403872374db79fe` |
| ` M` | `orionis/introspection/callables/contracts/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `00f6ca43a8647ceb6dbffaf2dfb2445489cb7f94b1e55e6a78fbe968f514d3dd` |
| ` M` | `orionis/introspection/callables/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `bda99e811504c82eafb538895d634f2079f8afdf4ce9b3308c8d082d533f2c0f` |
| ` M` | `orionis/introspection/concretes/contracts/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a08d4d7b7d361de7689afccab4d3d40f730184be23235784468528337b721609` |
| ` M` | `orionis/introspection/concretes/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3ea96abe908687da641021ed6038c1772aaed77ac235738e258ac8b9baccaed7` |
| ` M` | `orionis/introspection/dependencies/contracts/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `816a91e2e80fb8f0fa2cb56e8b304a180e0cf201d37bb10b0879c906d56700e0` |
| ` M` | `orionis/introspection/dependencies/entities/argument.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `9cc26106ee9475aae019db2c2380c1cbe383149e38baff0730d2f7768d18cb13` |
| ` M` | `orionis/introspection/dependencies/entities/signature.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `2cc892407e7dd0f9ecdd5b6385f23c652d9f9c4c7eb2cfe5322e9d3091aa29dc` |
| ` M` | `orionis/introspection/dependencies/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ee64ceebbf858f16baeeebef5a0990037064ec4cd4e50cafa983e1c405f5bb74` |
| ` M` | `orionis/introspection/docs/README.es.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `79a9aa782a90d56cef690f923132d180170bac351b0e67f87dbd3835dd84dca5` |
| ` M` | `orionis/introspection/docs/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `0bfa30f5c1266d9e5a0f1ca8e9f0da35e68568039c77ef19dd07a7508ee2fad6` |
| ` M` | `orionis/introspection/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `5132db2f9a77ab12ff6e12d78bedfbe82a800fd6b29a178098ccf862c28e1844` |
| ` M` | `orionis/introspection/docs/en/dependencies-and-discovery.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `1d5400be97a7b3e9269561ebb706c9798850d8ddb2fc529c25dcbca8757d8cd5` |
| ` M` | `orionis/introspection/docs/en/reflection.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `8648355fe497fafb76921a66c8b900cb11d75fc43c02438626447aae813afb22` |
| ` M` | `orionis/introspection/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `3e8cb263a1a4b79e61f2b1361b5fefaa2732db09eae2df106b3eb983375fc1b8` |
| ` M` | `orionis/introspection/docs/es/dependencies-and-discovery.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `5d59d25d7a64455ceb9df64862af7ac935c9e63d6be478c00c07d8e92ce3edbc` |
| ` M` | `orionis/introspection/docs/es/reflection.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `22ebb8bb7a72cb2930826dcc8a00f6503c1f9d44f81a5ba080819ea62a767ead` |
| ` M` | `orionis/introspection/instances/contracts/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `44e517d523582d28d03e9fe308d3b29aed35f405573e0612e2b804e385d6c916` |
| ` M` | `orionis/introspection/instances/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `79797e6ea69d08275e5ce38c85f82e3f74f670696dbfa8251a58461d9269d409` |
| ` M` | `orionis/introspection/modules/contracts/reflection.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ef334dd8913ce16735bad3bb4de742ebde7b9b5dd3406ce4b3d97b8def48af2a` |
| ` M` | `orionis/introspection/modules/inspector.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `62a30a99c751b18992152b6bec5106061a48e2f5077a7ce642f0f854d82b8f64` |
| ` M` | `orionis/introspection/modules/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0f4335f9b78f6b82c28c3155647fcc7771c1a2e5298c07bc0e7b3d5bd0e49b8e` |
| ` M` | `orionis/introspection/reflection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `078908088a138aee0155b3289acb7880f5176abe31ec4f0de4cf86463086c775` |

</details>

<details>

<summary>orionis/localization — 18 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/localization/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `14b6fe898a9a372d8cbf8d97bee50c602b7e1696a73dd8f4df20533378e3935b` |
| ` M` | `orionis/localization/contracts/loader.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `38ce971abbd1552abd70aab7fc941941b5acb332ef6119142615176f123b0aaf` |
| ` M` | `orionis/localization/contracts/manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `11798fac59884b173269226d44695179f8c2f739c829606e5cbe38f00260f096` |
| ` M` | `orionis/localization/contracts/repository.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4d5352abf7994bfe053f8fd4d3ac6e00bb00aa944c0ad55afe2290cb96244a7c` |
| ` M` | `orionis/localization/contracts/translator.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1ed065befd14d45d045f63b9734ee1306ca2ec81869813a6daf9b01a5732202c` |
| ` M` | `orionis/localization/docs/README.es.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `ff0da77cd8b9664f7037f93f49350e060daac399327d0b6c1738bbe7a3383ac0` |
| ` M` | `orionis/localization/docs/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `129d7733b20b3ecc804b26128c50318d4e6a1af55026acb10c6895885c719171` |
| ` M` | `orionis/localization/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `4aaf184f46d2d1f82ac7c1760cdfa6209dfab3a1404bfe7902d6bbdde1b7f243` |
| ` M` | `orionis/localization/docs/en/translating-content.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `119d6ab3f54da01066eef3c5b8f1dbcee04b98bc8d8ba73c6d6b5bd7c739420c` |
| ` M` | `orionis/localization/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `3d86294684934886be93e1e263c258ef80d658dc677b120b9be0998030f3c717` |
| ` M` | `orionis/localization/docs/es/translating-content.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `4560569773db879719630a37a2b713d08ee05e2d1b9d9599f60077bf5a6d5e73` |
| ` M` | `orionis/localization/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2bc18242300515b428785af0d6a8444605d304ea9f0e18e07f78fbb07f198ef8` |
| ` M` | `orionis/localization/loader.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `afc013c5aaf2a56cc72677a63c66cfef39c5e4da3b2e42ab803c77bae453a94a` |
| ` M` | `orionis/localization/manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7e10fe6c5c8c347ab38d7c0352589696506b6cdb4f0624a46574e4c7add288f5` |
| ` M` | `orionis/localization/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `00b70bf9bda250f50b77c1fb841084ab10f2dc2fb2f2b9d531417bed0290ec2a` |
| ` M` | `orionis/localization/repository.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `23f26d8fcca79aafb69541ed9dcb8f88f593028cf01d066fa160383f6dec70d9` |
| ` M` | `orionis/localization/translator.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b724c394a838f338537caa0a65ce3c79bb5780f52013272dd3ece0a207fbd06c` |
| `??` | `orionis/localization/validators.py` | Validación compartida y completa de identificadores de locale. | `eee470dfb38d7ac62e453471c036a26c046493a7518a14285806ad41e7a2cf5b` |

</details>

<details>

<summary>orionis/logging — 21 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/logging/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2c23b752bb325e091cdf1b9815851e8cf1106c796595f12ec85351e54e94f2fb` |
| ` M` | `orionis/logging/contracts/logger.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `f22652cf4f1f38b7329f70d757e3e47e3e71164b3dbbaaa8a7a32db174ea7346` |
| ` M` | `orionis/logging/contracts/suffix_resolver.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4b2fb79bf7e52e328979787bd427d8d194543b0461eafda5a9b6fba57d08e693` |
| ` M` | `orionis/logging/docs/README.es.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `f9744582f302e6a474b26c6e147026d39218eb5933305d1ac988a6c5226eaa80` |
| ` M` | `orionis/logging/docs/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `86c0cb8e23a7d359f4cdece792cd861eef53743fde7aa8eca70e723d6ed3badf` |
| ` M` | `orionis/logging/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `68267ba214ef89f2cb51371cd57dc12c45f67eac1bcbfdcea9241293003ef04c` |
| ` M` | `orionis/logging/docs/en/rotation-and-lifecycle.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `ec7d229d15931485a9e0da1a6479fd357ec18ed1ec0b8a40e14f2e531dfa97b4` |
| ` M` | `orionis/logging/docs/en/writing-logs.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `a6f27669925725ec7dc5bef2793e29030bb775bf66abd77bbd6bd84111e2ab32` |
| ` M` | `orionis/logging/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `80fd12fb23a68403476245905d1a1828027878c72cd685d9719a62427472366b` |
| ` M` | `orionis/logging/docs/es/rotation-and-lifecycle.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `b48fdf40e8800d709408146ea97f87d12c7f47dbee7635818c6a2ad7509391db` |
| ` M` | `orionis/logging/docs/es/writing-logs.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `6089896f5ec6088b26db4f34e0091bf9c01a447c78f7a72663ddcb11e16d921d` |
| ` M` | `orionis/logging/handlers/advanced_rotating_file_handler.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `10b24b31a2ba2f4d66520d3f78472459506af59397edaabd4574664905a88f05` |
| ` M` | `orionis/logging/handlers/chunked_suffix_resolver.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `55877bb4fc0ee5aa1c5a391ffdefbaec07acabab24e26cf763b8417de162d137` |
| ` M` | `orionis/logging/handlers/daily_suffix_resolver.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c33e09baf2f0eff1c1ddfae007e466d9c074f2ee03dc4104e542df0738ecc449` |
| ` M` | `orionis/logging/handlers/hourly_suffix_resolver.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a9badb91494939414223cf1b334dbfd69a628a2a4913a2397c035afd4fbbf63f` |
| ` M` | `orionis/logging/handlers/monthly_suffix_resolver.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `81201aa15bac1191b66033ae3b9ec59f2320f2d69b1387fd9e322f9945840bec` |
| ` M` | `orionis/logging/handlers/queued.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a01ea077dcd1da39420ebaa6233dbf73e37244f3ccb8520d6f8cf5ec39b6b9cf` |
| ` M` | `orionis/logging/handlers/rotating_handler_factory.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4c5327441253795d2e052601a286b19fba160c4c768f79f352557b01fd4e108a` |
| ` M` | `orionis/logging/handlers/weekly_suffix_resolver.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `673ecdd5cb43186de718af1c6bbe00e1f65af74e1b53a8d0f1a9810a968518ba` |
| ` M` | `orionis/logging/logger.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d7cdae3312c5d431c7af2d5f16fab6ba7cce791e560dfd5f7ba3092671b85b99` |
| ` M` | `orionis/logging/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fc723623ae6f516f0fce4695044878478fc4a86fe898bdad4900098502770ded` |

</details>

<details>

<summary>orionis/metadata — 3 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/metadata/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `7add05c48dc9ae6a6bd3124673b1a392d551f7b09f3908328828da86dba0cb12` |
| ` M` | `orionis/metadata/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `f5c7ffb9779ce5e69499aaae3a16f7c2dee146863dcddbb5770cea33c40419d6` |
| ` M` | `orionis/metadata/framework.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7a3253a710c05b5830766f67e04c68d66995a0d062b4b59c7ef1d8634bd12b45` |

</details>

<details>

<summary>orionis/orm — 105 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/orm/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a1f38795ccd6f7fd40872b55ef8bbbc0482f4ac6f6ffaf1548ad08e58960a1b1` |
| ` M` | `orionis/orm/attributes.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `072c8906a3af5506743094f5278dad9ea12c429bf46beefb48a5171cb21ce466` |
| ` M` | `orionis/orm/collections/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0b9c7313e0a32ba414c7eb3b37bf75e8cdabe391d67559f56824da32f8aa5cf6` |
| ` M` | `orionis/orm/collections/paginator.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1c6a17ee8fe19babe80288b15cee8f374c272513d832351212eb94cecd0da50b` |
| ` M` | `orionis/orm/contracts/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8074640fadd9855c8280614c574dc973592f05882d2ede43a7801237efcc7947` |
| ` M` | `orionis/orm/contracts/base_builder.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `421f0dac5a0d7ed451cbdd3ee890fecfac9c20f2d60a06d23c24fc2b5ef11d4f` |
| ` M` | `orionis/orm/contracts/belongs_to_many_relation.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `83fab458a4973005184ac4f4f451e60985a30728cce9494792134aea34b2d73a` |
| ` M` | `orionis/orm/contracts/builder.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `29d6c1e8cbae4741ea91679f16804606bebe3e24a7403509e8707f82b6498546` |
| ` M` | `orionis/orm/contracts/query_builder.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d41af6787be06ac960678f32a02c1ff2946f258b0bf6ca1e6c9b8668358aa27a` |
| ` M` | `orionis/orm/contracts/raw_builder.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `78ba4ba3707b59de4523a91f0c104bea1e91474bdfdc6537500c415d52bbab4f` |
| ` M` | `orionis/orm/contracts/relation.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b612c29d9d0b10bb38fe89531038f117d320ebc91b922b45c7cbdd1a1b0f788f` |
| ` M` | `orionis/orm/docs/en/events-and-scopes.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `7adc4131942a815e2850b7c76aa6bb96e917da05297a7869cbdf0dbd83b7fc54` |
| ` M` | `orionis/orm/docs/en/factories-and-testing.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `3c2c6ea39588eeddb56f5ddc91f90774565b675f86ef703d6a75806270c97873` |
| ` M` | `orionis/orm/docs/en/models-and-attributes.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `4165d9cdd10e607c9f1aa8e980ec8d15fb6dbb22e9694c750e128e8c6f8abd6b` |
| ` M` | `orionis/orm/docs/en/querying.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `07caa25e9bc295f61b76e41f5e3f4eb5c84a6b617cab3505270c958cbde0e2a0` |
| ` M` | `orionis/orm/docs/en/relationships.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `fe4282de0a72204d4c1152a6525a990bb112e93c317a6dff7fc2209b164bebb2` |
| ` M` | `orionis/orm/docs/en/schema-and-type-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `9020be45954a99fb4a08f912fdad3e0597005cdb981676322d7d2093c53a5e2e` |
| ` M` | `orionis/orm/docs/es/events-and-scopes.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `7f0ca0ac58567b7232e67cb08aaf46439df84b1c1a5e6f9ab0462baa25ea7840` |
| ` M` | `orionis/orm/docs/es/factories-and-testing.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `dfb2182c2595ac51e853a5ac8f0c568d522e18f9d1c4575bbcf6aa1c63f453eb` |
| ` M` | `orionis/orm/docs/es/models-and-attributes.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `e664dacefa3542fe80974c17729750b6fb06e2500a7e6cfdee2420fa728aeb7f` |
| ` M` | `orionis/orm/docs/es/querying.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `1c91bfd10e32af82543f8b493335b3d8f8604364d227560b9a2ce502c0e90a53` |
| ` M` | `orionis/orm/docs/es/relationships.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `aca9b071fa8285157f26ad841617659af98f713f5e16edfef0d58f78be399b30` |
| ` M` | `orionis/orm/docs/es/schema-and-type-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `9ab65bbcc062f1048c50b5dbb51557c4e0f819e5267a2cc2116d34c14c032622` |
| ` M` | `orionis/orm/events.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `aae951b6902709aad83be1550091a7d8437cae58699dc2c59f552f2ea93f6aa0` |
| ` M` | `orionis/orm/exceptions/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `416a9cc9bdf686ada29f1bf2191c727c0b19ddcd74936bee2de6cbbfadabfa07` |
| ` M` | `orionis/orm/factories/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6a1568bbfc1fdc37daaf10a680ee97b66e1e414478ee8aeed52ef6bc6c1b9d38` |
| ` M` | `orionis/orm/factories/_attributes.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3fcd15231ad5fa25a94d0eb90e36be33cc1474c2c176c9a45564cec04c8825f3` |
| ` M` | `orionis/orm/factories/_faker.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `39fe3ba3718c428f2a6488f8c9eaf43ff5d8c8c0e177b5e498079f11cd0380b1` |
| ` M` | `orionis/orm/factories/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ee864871cefba86c3de2ed97dccc1080cd41628ab551e4eaa874fd9eec58d02a` |
| ` M` | `orionis/orm/factories/factory.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `da368c2af68e9ff63c7766daf33b0dc97fe243453376ec25522ffe6ac4cc35a6` |
| ` M` | `orionis/orm/factories/fake.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7fecbfd1d3342408d7b9db0e99f6a928a2985f77dae0ace9ed70000b9c51676b` |
| ` M` | `orionis/orm/factories/fake.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c9327979efb7c6a3d5f1a81664d85a2777cabb206d9a3811fcf9f201d0f44004` |
| ` M` | `orionis/orm/factories/sequence.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `94ab082b3f7f7b7905d7b730f1a616ae76f891602355d2aceb87536313daf1eb` |
| ` M` | `orionis/orm/metaclass.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d7c89f1e252c82bc2db81ffcbe984d3534bdb9e200de27427422c8a4675b4d6e` |
| ` M` | `orionis/orm/model.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `547f2dac589190b728e5c7f1c67771c38aa6d018ed5dd43018e39a274c6d9dfe` |
| ` M` | `orionis/orm/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `177cc1db88159c8d73bf265e9b811cfd3353ec3ea07d247c9b1da46ba2dcd187` |
| ` M` | `orionis/orm/query/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `27b91284cb787d2431d53bca05c28851903860ba4b5bd7808cb6fc84eebef4dc` |
| ` M` | `orionis/orm/query/base_builder.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `daa6ee2098a43b44ac434b6ebf7c4f164a51967fd75685d9290f7de20468d449` |
| ` M` | `orionis/orm/query/builder.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7f477ea9b3e1aad706ca66c093c47c50962b3010f43b4cd871f576ecf1603768` |
| ` M` | `orionis/orm/query/expressions.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `86ee2bb318a4219bdbd68631033a14c3b98fd72ac6a7fed5a6f0ebd321ba9869` |
| ` M` | `orionis/orm/query/join_clause.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `8c77b933ab2bbb8c8a55e257162a98adaafeef67010977ce474f21f154b4a813` |
| ` M` | `orionis/orm/query/raw_builder.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `2583b1914283b45b485ce120ab888052be55bf95644e7ccb766a335aeb7a2914` |
| ` M` | `orionis/orm/query_builder.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e8738d766e81ff709398dd3079eeed16b0e4d54318f7c3a7990ca4d38d8dba90` |
| ` M` | `orionis/orm/relations/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b5025bbda20ba270c222a3bf7aada5571d3974e223201cd91ff4080fc22e6348` |
| ` M` | `orionis/orm/relations/belongs_to.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `89076c43c368a2034113c5a3c64090b8fded4d9521ba8055fcf13a9b8f454478` |
| ` M` | `orionis/orm/relations/belongs_to_many.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a52dbfc426770dc9af21054c91bbbec0997d9ac9e123a539561dff4fc4d30ca9` |
| ` M` | `orionis/orm/relations/has_many.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `fc99b429f3dac0df8bf8287c913596a15e5b849c5e10661500abb058109a1c2b` |
| ` M` | `orionis/orm/relations/has_one.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4168fe571fc06b7feb5c69645f05ed32b72e829b925f07bf0ee3ea76e9088976` |
| ` M` | `orionis/orm/relations/has_one_or_many.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b2a7fed35fb5a78200ec3eac96d4e69d29cf7e412983d8cd05f5cc97c90cfe44` |
| ` M` | `orionis/orm/relations/mixin.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `8c372ff45b9bf44bc7b3c04eeb6cbe1aeebc84e60d7ac532b56de9f705e725af` |
| ` M` | `orionis/orm/relations/relation.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4f5b263c69e89dc199eb220460dbd9eb7a45a79ab2b35df03200a087ad7e6d56` |
| ` M` | `orionis/orm/resolver.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `00e9159a782e45daa5c51b05e85cb10bd5b3c2c5a2330b50d6c7057e88853f1d` |
| ` M` | `orionis/orm/schema/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `2431a9a606c29c9325b72e739d34437186631bd5bf3b5745f157185e30cf9420` |
| ` M` | `orionis/orm/schema/column/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f65de97df0f8ea48af8be9b7b9241d939b263b27959da7535cfa1823e90d38b6` |
| ` M` | `orionis/orm/schema/column/definition.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `f1088b3cb2a4d8006dffdb3bdcc85ff4b01b06975d45bab9843b52dc2592a651` |
| ` M` | `orionis/orm/schema/column/options.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `942b8b3cac53283f5ed3b9829f5f7545e05cdf2d1ab2cc9d3121728c61355d99` |
| ` M` | `orionis/orm/schema/constraints/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `d6d5d6970f5d5784dbb4ee99006bce9d2c77b42ebeb8fc5934be7c57552c549e` |
| ` M` | `orionis/orm/schema/constraints/composite_foreign_key.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2baa2ff921384d47fe2625092c20d59c3b657461cc09ead56f6a6a86392fbc42` |
| ` M` | `orionis/orm/schema/constraints/foreign_reference.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b269c1627a85129851f455e5faa9d83c61e9cf1496c1c00814d880a57d4a474b` |
| ` M` | `orionis/orm/schema/constraints/table_index.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f5ff22e1c679a234745e8123059a85070988d44ac8484c8eb3789fc735ca3cb0` |
| ` M` | `orionis/orm/schema/constraints/unique_constraint.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `28dac54ee8a535652defad7ee142be3b942650cec088c26a248d0be1e5776c83` |
| ` M` | `orionis/orm/schema/table.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `44be2536780adf55f4f44df9d820a37ec67ab22a542f3fc7d942906e4572564a` |
| ` M` | `orionis/orm/schema/types/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4098c4bd46e80567601f97370c6b2afb74aab72e59fcf76472c6f419b422ba78` |
| ` M` | `orionis/orm/schema/types/big_integer.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `098e17108c4a423e405704551125584156bd4bbf0ac82f24708d12f3cd7f1a7a` |
| ` M` | `orionis/orm/schema/types/boolean.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `1a4389dddff6acf9ed016b6451670315f38166a127791b6114c42e08b56c7313` |
| ` M` | `orionis/orm/schema/types/column_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e35c0004db5957924e2b8baaae9c6bfbb576be33311621c8f5acaec17784547f` |
| ` M` | `orionis/orm/schema/types/date.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `bf047f5cd099c77c8320c32dbb1894110fa7494f1f73a94f6d14aad75973312a` |
| ` M` | `orionis/orm/schema/types/date_time.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a753c822080599e9081fd0f7e1e14361aee3ba942a720abb7e98e8c4f95252d0` |
| ` M` | `orionis/orm/schema/types/double.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `155b22e380e71268fd2ad35c742a93b5d235bf4bac839acc027b977aea054709` |
| ` M` | `orionis/orm/schema/types/enum_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3b9efbb2621722eea58302f61ee2199e47bbf4af9a2f4560921f88abe3bff39e` |
| ` M` | `orionis/orm/schema/types/float_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `89554de4187916c9edbbc00d9a7f8521c7f6c5c988f960c71e3ac02c884d9be6` |
| ` M` | `orionis/orm/schema/types/integer.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `da207dc0c82b2539358438b424ceaad474a66ffefa02e7304237af423efc387f` |
| ` M` | `orionis/orm/schema/types/interval.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5aab4c436db2d90ee62ba633a780a8c3b7f2d87b4bc90c94fca677ca6427449a` |
| ` M` | `orionis/orm/schema/types/large_binary.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e010007237495787a6c71d29e30039404b885829a0bf91595eb554c4db6fd5a9` |
| ` M` | `orionis/orm/schema/types/match_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f9e8703d1d4ff36fa1f31312b295a62d28e1dd5d5408498f2ab1b61d227d6d20` |
| ` M` | `orionis/orm/schema/types/numeric.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `adb367ac4930f36ce3648980a394765f3f31539dada2387f88ef7f46c7ac5aaf` |
| ` M` | `orionis/orm/schema/types/numeric_common.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `37fa76cb8983e6c5ffb59ee6494714aa865845a591292d832f3934dd905d70e2` |
| ` M` | `orionis/orm/schema/types/pickle_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5fa6bcdd14dcf05ac332ec34b0c97017286cbbad6f299035651d698a2bc288ce` |
| ` M` | `orionis/orm/schema/types/schema_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `6b5a632f89f87f1e6c3192121b4aa1b731f97ee3b17a3b9a9a02e883e3e03d15` |
| ` M` | `orionis/orm/schema/types/small_integer.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `660acf1b5a3583d1e39e183cff2aaf48f83bcb4017f4b6145c052518f0eea14a` |
| ` M` | `orionis/orm/schema/types/strict_array.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `96122697b7d53da85880d69831539580f71bce9ab0b6c8f53afcccef2ff416e4` |
| ` M` | `orionis/orm/schema/types/strict_big_int.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ce564edacc4646f0c2b757507707422d4d3055c9a934239a89c1659b963e0b53` |
| ` M` | `orionis/orm/schema/types/strict_binary.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `22889c8ebe8700348520d6f281be3b5036b317920285e3a69fab7d2a355a727b` |
| ` M` | `orionis/orm/schema/types/strict_blob.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `be1828c9649bb5b9449b47332de1ca5f765d7dc781419a8bbb65ded9aac89cd6` |
| ` M` | `orionis/orm/schema/types/strict_char.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `17f07a3e34a7c56c40ccc18e85cacf6a9784af90bd7f13848a6bacca857fa90a` |
| ` M` | `orionis/orm/schema/types/strict_clob.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c06960f084cc7bceb502c4078edb3b0ae72856bf56e9e78d8be44251605138a2` |
| ` M` | `orionis/orm/schema/types/strict_decimal.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `21b7f914f8014a20312b56438e5121602aa230bb13caf40db9ac18ede6d76e7a` |
| ` M` | `orionis/orm/schema/types/strict_double_precision.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `db1781e2b90694b69bc2be4caa422b0d15572e42f3ac0ffed952600401a40fa2` |
| ` M` | `orionis/orm/schema/types/strict_int.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e98bcd30f2dc98ea364d3cb298a38fb5b51da79fd9acea22b9750412102c5393` |
| ` M` | `orionis/orm/schema/types/strict_json.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7e40d2d28b66a3757180ae8cae12635ce6955fd4310e66a838907ac83d76e544` |
| ` M` | `orionis/orm/schema/types/strict_nchar.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5c5e1aa2dda240d8d08c1626a70cd5315a8ed943b16f13dbcaf7f896c9879992` |
| ` M` | `orionis/orm/schema/types/strict_nvarchar.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7580a6bde8280a7458e8cce33933bc8b4e335a521cb8669c99cd440cde039af4` |
| ` M` | `orionis/orm/schema/types/strict_real.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5103ee0832072db4cea2ab730b57d1882eb2834f4f5d0d0f85d3a2985300d506` |
| ` M` | `orionis/orm/schema/types/strict_small_int.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2b7205fcb6ce5094c2c1b5fe827e4ae99cd56d668c49b9295e5d3a55c860aa08` |
| ` M` | `orionis/orm/schema/types/strict_timestamp.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3f241c1c9695112a7b4ca6bc4d621b1282191844b905f7aca0cb44a52beb07a1` |
| ` M` | `orionis/orm/schema/types/strict_var_binary.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `9d3caf6903e6feeb92711589411eb7bb290f00c4758e70084bf6d0965acbd196` |
| ` M` | `orionis/orm/schema/types/strict_varchar.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fe9dd9d35992ae6d3a9c839fd87b844adb95de6e5e1b4c956faa2502e199c5dd` |
| ` M` | `orionis/orm/schema/types/string_type.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `9cb9c9e7f40c2ce34e528475997ea2f52c48c2f5d140754348138de5f7a5425e` |
| ` M` | `orionis/orm/schema/types/text.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `80c11a349e60f8dfc4afd59eb4afa5aa1a01fa6183e27d0282d5b3844bcb75d6` |
| ` M` | `orionis/orm/schema/types/time_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `79fee3b16536dc3a3a434b5fb14fe47cc927bfd76bdb9c8f8bdfa3c145043097` |
| ` M` | `orionis/orm/schema/types/unicode.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `897b5b69c6596a834e10ac4f2104c625b988a7df33dbdd3aa31801429e6778bb` |
| ` M` | `orionis/orm/schema/types/unicode_text.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0978da7e395885fb74c8df2379be70d8d366b1d5cc1741309545b8f0fb7e12bc` |
| ` M` | `orionis/orm/schema/types/uuid_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a43c1454585ec1a1fa9c87eed1090754ee9b6f7bfe011799b5e3ff8d9e2cc289` |
| ` M` | `orionis/orm/soft_deletes.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c931647ef4c65b3d788f27a5715c4143488199bbc75c501151f1065c9f373625` |
| ` M` | `orionis/orm/state.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6eb6de9087d621b0a7a6e20a2e12dafa93bddd6fd1298dd1f43e5405884de56a` |

</details>

<details>

<summary>orionis/schemas — 73 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/schemas/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `34ab4878a141570fb24652abc03cba0c555b453da442d3c7d3b72e7059405fb4` |
| ` M` | `orionis/schemas/coercion.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e20678dd4193b5e416e4f8687c111b7ae1012dd19ef7848bd4573bbdc32cda53` |
| ` M` | `orionis/schemas/compiler.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `f8b3e7e300382c8d1c7efbeb52973c70332bcf3ca6b91d8014a45228c94f723d` |
| ` M` | `orionis/schemas/constraint_plan.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `578190d8adb24d50f92c51c2f5f3914529b04baca721b482e8598e15e579197d` |
| ` M` | `orionis/schemas/constraints.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `627395ef97e9b2e3f531b58e468bcf3c2d9a8eec0c88a42c9dbce5f90acdc2ac` |
| ` M` | `orionis/schemas/contracts/constraint.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ca30adeb38ff05cea6ec46a58ec84fcc9fa130cead27b83702fe2f1847f9602e` |
| ` M` | `orionis/schemas/docs/README.es.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `eba55727c0eb5b404bac711d88eace7e3d820be14857fe3f5438a58fbfb2c4be` |
| ` M` | `orionis/schemas/docs/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `79d696017c60e5ac5fb325505cb51168ba32535310bd39726af6515758587f95` |
| ` M` | `orionis/schemas/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `847e15f9a0e7b4178eb6233c0179511202998105e3b51a61bb98286a1c6d6a2d` |
| ` M` | `orionis/schemas/docs/en/application-rules.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `fd9fdce7714a8752d09d6d13f961e1cd845fb53c6a720ba67b5be6141390cdce` |
| ` M` | `orionis/schemas/docs/en/constraints-and-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `27235adb4656995678e7bcff2a4bde528cf841d2dcf1718d4fabe98b18f1055a` |
| ` M` | `orionis/schemas/docs/en/declaring-schemas.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `49332f47874fdf2cc1a3de075995f79d2cb88beeaa323e493f4dc52bb78d3468` |
| ` M` | `orionis/schemas/docs/en/validation-and-errors.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `b811eb8f8a8e914f42057461ebce48cae65a3481084f68a7ecb40b6af6ef3898` |
| ` M` | `orionis/schemas/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `41d9c65a15f3470128c9bc8333695317ab5de5870d2aa08e2a6bc4d91b32a431` |
| ` M` | `orionis/schemas/docs/es/application-rules.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `5b369ad0ad002dd270adb7cccae86fc4255da2795bd505d95e17df3feeedecda` |
| ` M` | `orionis/schemas/docs/es/declaring-schemas.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `7a9d12de4775c17ce77e5cef672871337f1a3cfa605e2a32e127740136af08d4` |
| ` M` | `orionis/schemas/docs/es/validation-and-errors.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `34e862ccee80555a613d4a4ffe208f14eab725f45932a51d8b394a97224775c5` |
| ` M` | `orionis/schemas/entities/failure.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `32b2937538621fc8f64adc906c237f1e54b41a186317446cc264ce3714f36b45` |
| ` M` | `orionis/schemas/exception_parser.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `83abf76ca08e4bcb5e1a45e7a1b71da07c062abd3a5e5572e2362df5347be3d2` |
| ` M` | `orionis/schemas/exceptions/validation.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5eb4ce453b1087fb1976add5f74dffaecf5b59157872f27a8d7ef6d45c237a37` |
| ` M` | `orionis/schemas/failure_collector.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `fb3cf2549eee99af0a8db924383e76dadb347e9d2e28e3b6d116bec23f0b73bf` |
| ` M` | `orionis/schemas/instance_payload.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3f0ead88bbcfce6a9d51ab0f74a3364bdde559dbe32a5ea6e6e012e210d46cce` |
| ` M` | `orionis/schemas/meta/constraint.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `350ef4d2662e91d6650e3af28bd456a7e30e077c59265a78759c0df8c83d3bbd` |
| ` M` | `orionis/schemas/meta/document.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c60b2d8aed2864aaec11a1df330b198432f24f0a8dcd359ed7db5df016847053` |
| ` M` | `orionis/schemas/meta/validation.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8156f6c5163c35c4e083019f53500f15c9b77c61db9e4353ae29875a74c288ca` |
| ` M` | `orionis/schemas/metadata.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7b6d052e6bb97cdceca0e167aae04db43b1ef2d0653bbb79b566b2657b2a376f` |
| ` M` | `orionis/schemas/rule.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ff3822087fd042f9488776544c0351bb9a8d2f405b3fe1c1899a78d3e806d234` |
| ` M` | `orionis/schemas/rules/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `25f6c634f831ecb6cb68862ef6526758b51b1e05de58f2b4dc3f63de18e5f63e` |
| ` M` | `orionis/schemas/rules/accepted.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e0b1b23a4075ffde3ce1178adaec3f6210feb79a3e8617afbd343b648d377c01` |
| ` M` | `orionis/schemas/rules/active_url.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c8635be361a6b767e40ab95783759010bf01b06f4722524f9086fced7e9c4183` |
| ` M` | `orionis/schemas/rules/after.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `de9ffd6ddedf6a035b17a22b3787902efe5f43f9a12c3feb9c2469d2d5408710` |
| ` M` | `orionis/schemas/rules/after_or_equal.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `80d69f0dc895b511c4ce05c5a319e34bdefd4335cd8d5a28123bfe130016a7a5` |
| ` M` | `orionis/schemas/rules/alpha.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4faa2934562ebab7c8e9004c842a69148cca8d5f8e9ad25592b671ffdcbaed0f` |
| ` M` | `orionis/schemas/rules/ascii.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0b7f8300f8c335a93dd6a89bb6337ba9db421b5367facef1793ba51c7259173f` |
| ` M` | `orionis/schemas/rules/before.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a5f6950ffb291ce9e350a924618b2d97408f92cf09fe7f8ee0defbf09ab72aff` |
| ` M` | `orionis/schemas/rules/before_or_equal.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `537e93438d33531cd5e1345afca0e6c784507730cde731c0e6376279ae6faad7` |
| ` M` | `orionis/schemas/rules/between.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7bbd8cd8c7a9458bb057a934062e15c5732d30c2a85cdb42b0809b7dec52071c` |
| ` M` | `orionis/schemas/rules/confirm_password.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8e2b325ea9a7acad56779276112bb8528b6a7ecfa32c8c88b57f7d7bf9f60f35` |
| ` M` | `orionis/schemas/rules/date_format.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `153e4af8cdcf92ffef398f1f371b755ee9381561c312223b19a73d0b893b62c2` |
| ` M` | `orionis/schemas/rules/decimal_places.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4023303fc9513261355545e3e7f58f3f83e526c98acccd530125fca311c66bf5` |
| ` M` | `orionis/schemas/rules/different.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `da83e40c11eb9d271dc2b86f387aa5be598e76c3dd35a3b2c7c436f463cbe88d` |
| ` M` | `orionis/schemas/rules/dimensions.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c3bddfb63e35e2f1cfff8343f3b71c6f9433708d087beb3755204b3dfb2ce9fc` |
| ` M` | `orionis/schemas/rules/doesnt_end_with.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `717287509ca3ddc5bd951471e94f6317c2e533601f3af2432348f310bbfd0f9c` |
| ` M` | `orionis/schemas/rules/doesnt_start_with.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `10a7a21caed3c4b09ecbf956d2eae545c9c1ba822f6a13686e615977ee0ede3b` |
| ` M` | `orionis/schemas/rules/email.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `fd8263bd4ec49833eed7bda26db828e540d239d622b16f4c8caf53c223312863` |
| ` M` | `orionis/schemas/rules/empty.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `95dad5edacccc77e6fa74fd3205c70350092e6580177ed057754919f01346458` |
| ` M` | `orionis/schemas/rules/encoding.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `491ad96cee2fd8b5e0453b81590dba5d89ca16b947157f73d7b7f5c57f5e2e62` |
| ` M` | `orionis/schemas/rules/ends_with.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `441c92ffc13f302436bc93640e99c8eca3d1a5406823010f5b0ce170b3f79249` |
| ` M` | `orionis/schemas/rules/file.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `646cdf68ac865ecf88c6f2439a8b5369bca34f98899e4464f008bd1c034de019` |
| ` M` | `orionis/schemas/rules/greater_than_or_equal_field.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `87a69c3f6fe7acc4fc436fc70dfb67ca03c338365013326227956288506ebcfd` |
| ` M` | `orionis/schemas/rules/image.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7259d25df483122a8ebc93c5750756f1667a6f2b44e788916fc50f514760d00f` |
| ` M` | `orionis/schemas/rules/image_probe.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `de19082606cb996b7e1d2655e38fbc10b805451e57eb743f7800925404239447` |
| ` M` | `orionis/schemas/rules/integer.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d6885c90c2ea0c574d1bcb5b1fe7390a30d09471844fd728defb54d3109d24d9` |
| ` M` | `orionis/schemas/rules/ip_address.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `cd83c0540724f9cc205db8fe4d6fce4fc7d184162b5f4e19d19b76e01427c074` |
| ` M` | `orionis/schemas/rules/json_string.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0e18eb40f4b2012b80d65f34e2e6360e1f3cb2ec0245acc4256fbdf6f00d7f16` |
| ` M` | `orionis/schemas/rules/less_than_or_equal_field.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e73ff5d14df329c04ed55225600b1f18e4da96d86db26194c6ad09cd5626544e` |
| ` M` | `orionis/schemas/rules/lowercase.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `758306f687642ac794050b1bbde972a9ad11e022199142268981ac2955f2884b` |
| ` M` | `orionis/schemas/rules/mac_address.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `9e8d6485596c11976021e8c6ed670c37c52868dedbcd811e6c49e49a9f4eacad` |
| ` M` | `orionis/schemas/rules/max_digits.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0b552fada94067577107c2bfe8cfde9a7d86017a3f64ab77f772a7f27beef259` |
| ` M` | `orionis/schemas/rules/measure.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d0ad511572a40f9ca30997f4bb10931e400d111b1f1abbbabb967b026e923416` |
| ` M` | `orionis/schemas/rules/mime_types.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e47b9b19c79b3945dd76b17c6097ea4da3d72f811d8ff87f0ba0405e458e44c9` |
| ` M` | `orionis/schemas/rules/no_empty.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `9ed8ef935a27197ebeffbfc6160a12cbb3bef9d6611a1dcd718b51f9e92afa29` |
| ` M` | `orionis/schemas/rules/size.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `371696a496f6d0d68b974f475aa3f4b37c6ce68ace15562c7ff4be9aa785404a` |
| ` M` | `orionis/schemas/rules/starts_with.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3e386419b92cb5cfd8dd1d9e085a8d8f6adbc8f6038d792d07bb942100b92116` |
| ` M` | `orionis/schemas/rules/strong_password.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `628cfcd9dccfe845940ca10c742de94dc3497766199628a2fe43adec9ef03ec3` |
| ` M` | `orionis/schemas/rules/temporal.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `56e0b0c943c3a70c9e5f1d4c833191be26671a2a7ab33392ff9f338e81edbbd0` |
| ` M` | `orionis/schemas/rules/ulid.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `72330e2278743f6ebe42cfe3f546285340b0b4253193a394f3f5b63941992f5b` |
| ` M` | `orionis/schemas/rules/unique.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3536bc06234f4611d315bd959eebeb6195b7c0bceabd0d8ebc83f04c882c3b18` |
| ` M` | `orionis/schemas/rules/uppercase.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c2f5dd2debd594110267c56d3ab3865910fd8889d14511b7e4353642840687b5` |
| ` M` | `orionis/schemas/rules/uuid_string.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `046887e03a9563f33b5cf97e6ce087e7413deb97851eb3aef63f373feb2872e4` |
| ` M` | `orionis/schemas/rules_executor.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `505cd60e789448a59a0e016a4429911233926c83a7d35676da26a2a9812b6d77` |
| ` M` | `orionis/schemas/schema.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `953a23b6c2f16046d1d5438bcf364ec50b25e68855924ebc84a44a75462f3bbc` |
| ` M` | `orionis/schemas/validator.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `710b74c92f0e45fb431de3f4474205af3b2e2d96ab2f9ea0669cad4065269228` |

</details>

<details>

<summary>orionis/session — 18 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/session/contracts/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `6eabba5c4ee8875349e7694b415002737c4c303e1f6c260f866bf0fb04f16cdf` |
| ` M` | `orionis/session/contracts/session.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `dbb3d61bbfaf04bddfff7c750913693a1031dc92fe5ee7ad721c49c882ab66cc` |
| ` M` | `orionis/session/contracts/store.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `29f72b4209c5c767c875c8ee0f0adf1dc0f632d98bc0236ddb54bb24bdc5e155` |
| ` M` | `orionis/session/docs/en/configuration-and-security.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `d2d386df419de8b0053a9acf623e07892fe73d034c6b4eeaa62dd564804d6651` |
| ` M` | `orionis/session/docs/en/state-and-flash.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `066003ec2a2daef3fa2a7345df8299e7f820b983b752011e9d7ad75c1e2ace9f` |
| ` M` | `orionis/session/docs/en/stores-and-concurrency.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `8207bbbf58612ec3cfba41ce7d2dd2b770dcae763515f785eb3a08d750fee8f2` |
| ` M` | `orionis/session/docs/es/configuration-and-security.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `c179da6c277428853d7f04e230b4a910fb85fc8559616e90e7d9e5cbb3a9d259` |
| ` M` | `orionis/session/docs/es/state-and-flash.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `b245071b366947bd91a47544db91d93020b55938a7b801f74c30a88c61bb7710` |
| ` M` | `orionis/session/docs/es/stores-and-concurrency.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `725b7a5c34137dbc9a73460911dfa5cdb5b51be18d4f48d29aa874c900e648cc` |
| ` M` | `orionis/session/entities/record.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `903c5a91462bf73bfc28dad2a32c3b17492f940873773d9b199b5d3f8cbb712f` |
| ` M` | `orionis/session/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `1cae84fcb218e3040e515fe9dc82b4d3b5a9611bc6969a271f12d84763a4b923` |
| ` M` | `orionis/session/flash.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `236ae1af4468e5dcf4e2137f2ce9b8bf9aa917e5b00da1c00f51b8468f6ec004` |
| ` M` | `orionis/session/manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7c36292f84ad2bd0f65fe9085f88ca156d8a54be31fb9da8502d138aaf61cb59` |
| ` M` | `orionis/session/session.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ffd05b633054d568a83d9d8063d3c8aa329a969e8675d010bf6f3a93a8b514df` |
| ` M` | `orionis/session/stores/cache.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1be88111bfd9b093038cb3cbbd9c9dd05a0f04c09fe13e53e65b922eb18c1a7f` |
| ` M` | `orionis/session/stores/database.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `61c45afe3524b11f9658b36ec29462a1406c1ab65f413790cf91c2da1a788732` |
| ` M` | `orionis/session/stores/file.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `104495356a71a84e4960d38b00a030a1deb8aacd5cdfa04e918190ebc65748d8` |
| ` M` | `orionis/session/stores/memory.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6a2709242a3bb030fe721d98511b2361dc6215cd73c61bb4e81e11c4dba3fa71` |

</details>

<details>

<summary>orionis/storage — 34 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/storage/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2dd73f0518ebf90489cdef6d95c210d10fa4b16e0d918dd4f432c4fda8b972d4` |
| ` M` | `orionis/storage/buffering.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6fe833101970920307c7b04252de01d170648ce8dd540ba2497a7e104d202e19` |
| ` M` | `orionis/storage/contracts/directory.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `8ee519465ab3b9b4fbea6f59b976f29c680c38b0816fe5a037c3c1f717a4c20b` |
| ` M` | `orionis/storage/contracts/disk.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0ec6e3fb031a3edc2180d74e41f036008591843a40307c317677411d17df5aab` |
| ` M` | `orionis/storage/contracts/driver.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `718b456c181f551d3f894f049ffa265af7b0e052964f10d3fc62861e466a2eeb` |
| ` M` | `orionis/storage/contracts/file.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `2c77094df886f6098d393030fecf7fc9fdad28e8a888619365e5ae8d27e41d62` |
| ` M` | `orionis/storage/contracts/manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5c94c3855ec1486b11b2e8d230a94d2283959235131dbb6fc47ee60eef4c21be` |
| ` M` | `orionis/storage/contracts/stream.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `2a7eb3ece5eabd6427832d7e6c2819489976a0a76581a5a264d5bbf3eed0bd60` |
| ` M` | `orionis/storage/contracts/uploaded_file.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c66a5c985efc0e6c54d98ea98c4c96ccdbb1361d25a258d2c479f6f00ce8fb5c` |
| ` M` | `orionis/storage/directory.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `80be84a748464620d8096cb344c85588ce7edb328a4b36e98752097458597dd5` |
| ` M` | `orionis/storage/disk.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `edd7e68aa4c81f1a3512e0bacaa50cb1881595c8f45ed04afe8ee5761922f13b` |
| ` M` | `orionis/storage/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `bd78f02ab685460b78dc7f25592a16559632947490b32f3edeffc73154eaab54` |
| ` M` | `orionis/storage/docs/en/disks-and-drivers.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `4be28095db4b569ccbc5fc55ac8f1cc6a10e59c6dc6d4cf479ffea25dcf42b19` |
| ` M` | `orionis/storage/docs/en/files-and-directories.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `620ab915f11dfb30e7254bf41e2dce2e40da30e46a1460f1da5203bc583906ce` |
| ` M` | `orionis/storage/docs/en/streaming-and-uploads.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `bcca6a4bf37aa9a753bfe1a6394d1c0d1c1605b5a55365a73d40288d67267fe9` |
| ` M` | `orionis/storage/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `76a4a3c497fcb11b2cb4a1914a9b42e903c37c47bbd63a4075e880ceaca43e5a` |
| ` M` | `orionis/storage/docs/es/disks-and-drivers.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `fc703582c071970db79cdec454e5ca56e72e834fee0adf88e520ac1234df58c2` |
| ` M` | `orionis/storage/docs/es/files-and-directories.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `5cb49517f17323672b35561ebf7e15a0369f525f92bc8abef8d424a5fb7e85fc` |
| ` M` | `orionis/storage/docs/es/streaming-and-uploads.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `d60db00f25ec89ceb4bdce0a28b3f42c20eb74b36d236d0ed52739cee9fa1d39` |
| ` M` | `orionis/storage/drivers/azure.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `91f012390a97c6c6bdf7b0844aeba267f16ecf602284d6b30abc530feb594d38` |
| ` M` | `orionis/storage/drivers/functions.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b04127d1ec0adf45f5ae9981582692cd88c0ed294bd5566a096e57abb25d64fa` |
| ` M` | `orionis/storage/drivers/gcs.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4775f85cb65d94af1921d86e879248fe706590c0178ccb42f9d5da983343d9f9` |
| ` M` | `orionis/storage/drivers/local.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d98859c6ef6df7075b4ce5dcbe272bd5b7d98ca9c550d01a12c24ea40d2249cb` |
| ` M` | `orionis/storage/drivers/memory.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e6406961e3626d4edfb01aec67976d87b9d922dc69bc6fc580b4a8c73159a0db` |
| ` M` | `orionis/storage/drivers/s3.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `9029d7ae921c88ae4f8deff8faffb89a9b2a2b09e33e93ec6f0689b05465054b` |
| ` M` | `orionis/storage/entities/file_info.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e8b902becb58a0d4dce82f644ebec338e126636ddd6fea8666430bfc645f1236` |
| ` M` | `orionis/storage/enums/visibility.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c5a3ee06ab799e72dbd18675ab6f67feb81678d518a97154b4599aaffe7bcda6` |
| ` M` | `orionis/storage/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `886f7a59217068b2185dd34407358c0513fafd34ef5b57f0c821ecd624739586` |
| ` M` | `orionis/storage/file.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e57a9e0dbd2f1b960cdefe4e3c99944819c78037be3bf31498a8ec60817fb8d0` |
| ` M` | `orionis/storage/manager.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7525607119b18ca333a9f7daf48f33484c9fd7183d7af495ed6ca58369cc6198` |
| ` M` | `orionis/storage/paths.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4a022adcfc71057811f0c81da9b7a3692c8df1f67d469683807a9abf092dcc6c` |
| ` M` | `orionis/storage/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fe9f77ef9591143ebf6e31357c1072c99e49a31f4e89f61c8ab9e90ebaa4e7a1` |
| ` M` | `orionis/storage/stream.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4a635819274ab127a63b573fb57c4dd7c060cbaeaacc568bc5c55d237b175322` |
| ` M` | `orionis/storage/uploaded_file.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0246aef0aa1896838a6d8ce8484d02aae42c8f32bfaa05ee987760bab3b22e47` |

</details>

<details>

<summary>orionis/support — 81 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/support/concurrency.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `bd2540a8d0e7e15404c1fe35da14f978e703fdbc61d84b3e10c4d98032fe7450` |
| ` M` | `orionis/support/docs/README.es.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `1826eb1789ff60fd1e2508844c7b8cfe0cd7485070b020a450ad055b2a0f3e95` |
| ` M` | `orionis/support/docs/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `79d06d1b2b42f4e7778165caabefea76814e6abb0fab7810275d5139f4877e78` |
| ` M` | `orionis/support/docs/en/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `d645ac93767c16a3000662c0cb8afc4382c530fea9b2e32ca48926aba004c70d` |
| ` M` | `orionis/support/docs/en/collections-and-strings.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `61c2a7f9b5ffa9a085707034bd3e2f0efcb523f7338d6d54baa096678a563da9` |
| ` M` | `orionis/support/docs/en/entities-and-structures.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `a0c29ade384b08e66eafac693d7263fcdd80c7c10a5e26ebf7f9af716c234094` |
| ` M` | `orionis/support/docs/en/facades-and-runtime-utilities.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `8a03b50a4836a5becba1cce8429a8deb56c251e473c649529a0b9e1c6d351a88` |
| ` M` | `orionis/support/docs/es/README.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `28ffc6476d161a8c89131e5a30afeed62560fb33efe010df5c78c1cdfa89e286` |
| ` M` | `orionis/support/docs/es/collections-and-strings.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `12d6195adb87230bb92e7c4e99417446a879bb72119f10b0d9fc09758ff62105` |
| ` M` | `orionis/support/docs/es/entities-and-structures.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `1ea42795fe7e2377b17c8bddc180019855fca488051e840520967a5e633ad6d3` |
| ` M` | `orionis/support/docs/es/facades-and-runtime-utilities.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `cd79fd384d6e8060e566e70d153754d332422b519780b2e38b4357246c535e44` |
| ` M` | `orionis/support/entities/base.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ff20b15431d5e2cac0dd37257074620781737f2bc68ba96bcd4e1c466db2243d` |
| ` M` | `orionis/support/facades/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fe2b127f3ab22213a80263d2c738ca12d687bd65ec1babee413673066cb63cdf` |
| ` M` | `orionis/support/facades/application.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2b6021620ce60d956ecb9a8b4af956afea64993af99a0114023e0afe3af80bc1` |
| ` M` | `orionis/support/facades/application.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `52ff37e7afc04d52a772cb35a14f4c202a3a5a51ff8b9f1c9254c6ef8c94c6bc` |
| ` M` | `orionis/support/facades/auth.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `716f7b2e57272276bbb32e80ffff2702b6edf2d004ec175eaf44108cacc4ecac` |
| ` M` | `orionis/support/facades/auth.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `092de9e2ecb11f6c1b7de26fe1b4eb8df501b9942eac1c37995c1e6348d21cf6` |
| ` M` | `orionis/support/facades/cache.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a8c6c5064c091b8fc89804a72cd4fae3b7ad942f062abd47536d2699972ba213` |
| ` M` | `orionis/support/facades/cache.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b23efc91d622d20250c1174c8c825b40bac2fde827a5572a9e6626767ac20f2e` |
| ` M` | `orionis/support/facades/catch.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `9ba94ec21859fbbe704fe82deb38b127258933c9aa89fa5abaa17b5ac3d8c828` |
| ` M` | `orionis/support/facades/catch.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `230a3575fc74931388934edd6c72c33f935d3c7f8d3049b5829fe891e9b1e2bd` |
| ` M` | `orionis/support/facades/datetime.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ba9de5ce737d2413a1959eb34d4264d5d09b869d926ef9a51c8cdba9a5657d35` |
| ` M` | `orionis/support/facades/db.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c14f26667a69644dacde75708b1963146e6dc781da9f2bbcb3cb5d31dec1af5e` |
| ` M` | `orionis/support/facades/db.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `67159deac0ade9db5a019f49dc6989ef60da6a8812fd26ab8402fc7aba593ea9` |
| ` M` | `orionis/support/facades/debug.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `76d8788ea4747c4d75558538a38143ce76fd5834e24be84e98de07ebe76ea4e3` |
| ` M` | `orionis/support/facades/debug.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ab18b2097ce257c95dcc78cd758c4f7f4b83c4cb8ce7c6f1c82144b1269c48e4` |
| ` M` | `orionis/support/facades/encrypter.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c31920d253a3ab11f0703848ba4176a6cfc482bff0dc034cf51954bb87a80d81` |
| ` M` | `orionis/support/facades/encrypter.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `64967dce193e8a45259f78e9ce407c5fa8ee774483723e94cf1546236d5f9bbd` |
| ` M` | `orionis/support/facades/hash.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4446339273a535b47d570894b81de4ec30736900fb66c5fdda8bd8c11fd5cbe0` |
| ` M` | `orionis/support/facades/hash.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `994efc9c1ade9fd8bb700320c7d78942ffe41a74f7ce4d0671cb21872eb7b188` |
| ` M` | `orionis/support/facades/lang.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ae6a81d7d4ad696f9df51cab7b9500a1b7dd63f57c8e0d76c3095a1d93df0bab` |
| ` M` | `orionis/support/facades/lang.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4c306fba2b22245ff07485e51de8701bdd9417642613461d825809f6558b7faf` |
| ` M` | `orionis/support/facades/logger.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0b47ce313707ec3c5657a84f9af75e0cf551d21b7cc61beaf39e8202aee86120` |
| ` M` | `orionis/support/facades/logger.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8a830c51c6826ab9070bfb99b932ee214277475674a2fed98f30976d4d625b31` |
| ` M` | `orionis/support/facades/mail.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3705aef9f9299cc9490f228912ea35d274b269442920b0f5fb3322e9482cbe2f` |
| ` M` | `orionis/support/facades/mail.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `66cf8deb93c6774da956b2c447725ce1af60ddedb1358962fbc6b8c98aa6fd9c` |
| ` M` | `orionis/support/facades/mcp.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `84bb10d4d0b1cafca9c8b4978feade183bcd7f818a4a390d205df9095315e5f8` |
| ` M` | `orionis/support/facades/mcp.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `8d4d56101a754500e3d4fc575f7b54f06b71e7a84caddc2c2e859f1360a64049` |
| ` M` | `orionis/support/facades/queue.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `9367096f826a70175c44b24e9bd88a413fbba5f0f223e101accada457feb5137` |
| ` M` | `orionis/support/facades/queue.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a0ab17365c625c25aa0d3fde18dea1813099c6c35638b9e5158bb1c70c4cb605` |
| ` M` | `orionis/support/facades/reactor.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2a78d60507b4f1db560b7b1f6b467cc96be8d4f803659bf1f8ba05fd2b7d30a2` |
| ` M` | `orionis/support/facades/reactor.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ff22ba515a66349e7c8dd66dd0d35cd0eb434ccb3122ad2bbbf9ac6f54512643` |
| ` M` | `orionis/support/facades/realtime.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `64fa8411fb7ffd478a8dcceaf88937bafaca5dc76bd822952c4cdfa1effc8506` |
| ` M` | `orionis/support/facades/realtime.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0746d47dc49ed03e51b4ca9351ad1370180e5a14cf94f92a792f671be748b7b8` |
| ` M` | `orionis/support/facades/router.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e71f0ba535be6e00da9081cc29b78828cec5ec90b2c5f78a98ed417d6ec9ae8c` |
| ` M` | `orionis/support/facades/router.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e670fe61a1c8e42a7e61868a763e74e0c1d16057e5e9eaa2645af09ea0263cda` |
| ` M` | `orionis/support/facades/schedule.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `d18a7e40f5f56e6cbd5de73b9774255eaeafbd152d8295cbb79fe7926436ff6f` |
| ` M` | `orionis/support/facades/schedule.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `e2cf4acd313942cc86f64185731e1d809d7ba489399550b1e63f412b08cfdce4` |
| ` M` | `orionis/support/facades/schema.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `6c1fd6c60fee59aafa8d1828cb6b9139a082c83d1a109ee5d3dc1dd9b8dd23f9` |
| ` M` | `orionis/support/facades/schema.pyi` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `85352f5ec5dab7e1c5f1f94358ac360559f681e75da75630328c8835bb562d08` |
| ` M` | `orionis/support/facades/session.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7b66123052ebcb1d8d3d80c2b8a1113dd2a5aab60bbdc81483845208a6451b2c` |
| ` M` | `orionis/support/facades/session.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `dff3a4ead359b00ce60b1335afc8f1e523328f7c6595acb4f932bc8d5c849eb6` |
| ` M` | `orionis/support/facades/storage.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e16bd132e58565a1e1e8c99d74b7f80d168f8013b49e4f9df3f84defa7a88083` |
| ` M` | `orionis/support/facades/storage.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `cf8cbdc604390a22f7797093b15c9ec95123f0b981cbe64400d4a645ea6d71bb` |
| ` M` | `orionis/support/facades/testing.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4bde5e2b0fd9284a87afe14a71807f995aeceb7e940363e6a796ff57ea9161f8` |
| ` M` | `orionis/support/facades/testing.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0749a99684c2689c10fedafefe1229b933dcd412b5676429ab0fb65c31540401` |
| ` M` | `orionis/support/facades/view.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fb3a757e3f35e4695b737f8d2e3fc1b8559bcb0c1001e4e59487af4ea5ededd0` |
| ` M` | `orionis/support/facades/view.pyi` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b40ce6dfb20314039abab720da63eeb83a23846257a742a7cb1a743c07de4ee7` |
| ` M` | `orionis/support/formatter/exceptions/parser.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `408dd35537d0afcda60b9a6765d4870b8b4ffeff55c55e753c949ea449814cb3` |
| ` M` | `orionis/support/formatter/serializer.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `82e08fe523126bcdb56cff50e7bf22ec4253a4534b5e0d62570f99e96dc874ba` |
| ` M` | `orionis/support/inspirational/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `9056a6edc8f09e10dddfd49da50a0aeb2dcf3e56ef097d32ce491889f82eb303` |
| ` M` | `orionis/support/inspirational/contracts/inspire.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `02c5d5c335dabb7d01819013f7bd5f1f87d9277e7c58471aeae37557387bcc7f` |
| ` M` | `orionis/support/inspirational/inspire.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `552ae9a566379ca43144beceb07a2b5fecf294d5bee35bdb775a24d36adc41e0` |
| ` M` | `orionis/support/inspirational/quotes.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `564c330d4bf918be2b3dbc80b3db3e832793afd2d3729bbbacfbe4ed389fcd16` |
| ` M` | `orionis/support/patterns/final/meta.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `23251b01c743e3923615db13c9b152a4d51321c6e331b8d97362fb1906c85654` |
| ` M` | `orionis/support/patterns/singleton/meta.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `c359812edfc1f4b45b8abc33f735c657bade59b69ef14bcfa55cb94e0d3047eb` |
| ` M` | `orionis/support/performance/contracts/counter.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b2b0c83e8ce0445287dbe081bdcc301e738b8388b811d37fd5baa6d18f08971a` |
| ` M` | `orionis/support/performance/counter.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `975e1a50605ccf383bcd4055b7d2655f3037da5cd0d9a9db560a9590343a39da` |
| ` M` | `orionis/support/structures/freezer.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `603ec34b632406f205f8284ec5e4322cecd60d115e9fe3f8713055c76ecdbb77` |
| ` M` | `orionis/support/system/contracts/workers.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `091c41e41f9da04f9c60d9f576087eb18b1d8f6605efe054c15658024e0c50ec` |
| ` M` | `orionis/support/system/workers.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b0021fa1e961d0f85c1f674f31ecd98404083052bff1d705b181f814199f61df` |
| ` M` | `orionis/support/types/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fca4cd8f88d735175013f89654bd02f4e0b101349ec271c0b4160a7aa32c0b44` |
| `??` | `orionis/support/types/_html.py` | Parser de etiquetas para stripTags; no es sanitizador de atributos. | `f9dde59a005b24d9d243da7a8987f7b6d1e7fb4acb08dfded31c634ec6ecfd74` |
| ` M` | `orionis/support/types/collection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `7ed116bfdaf9d94f7b81d0e5259d223b2807cc83a5dfca50324152d21602be10` |
| ` M` | `orionis/support/types/contracts/collection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3d9ee8d58db502d6f7aa205f63e1ec3fed2da81269583e9d947ec4f86779917c` |
| ` M` | `orionis/support/types/contracts/std.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `58fd259e2eb9c27ba9b8f18ee3596df9bcb91d81b2c66df36cafd4c565680e70` |
| ` M` | `orionis/support/types/dot_dict.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5a7e755c91ee7fd780c46be893490f0ae6aacd22e13afcd95e366cb9bf800561` |
| ` M` | `orionis/support/types/sentinel.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `082b190034c6dd14db6367474361c78910a73ec3e5414f75eb3cd7845206e0dd` |
| ` M` | `orionis/support/types/std.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3638f79939f3141860a4cbaed3cd6c6eae0f839c21effbef671fe4ad287a36fa` |
| ` M` | `orionis/support/types/stringable.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `617c6dc35e1f568af3e639426233db3ec2bc822e8dd9a738ef80acea19c1c19e` |
| ` M` | `orionis/support/types/uniqueness.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1008a4201dbbc58add3f5a2d5c0f56331e6792fc7d5900478574c6171385fb72` |

</details>

<details>

<summary>orionis/test — 16 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/test/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `aeb4d0a4b74f19cadafe6fcc3d8353a2d46fd0937775230cf622b5adfc0ba493` |
| ` M` | `orionis/test/cases/case.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `323de3bd2649c0dffe625c1a0afd0c7f6d044dc2da5e3347f0e0573316b0e808` |
| ` M` | `orionis/test/clients/mcp.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `591877d23f608e3cad53fe5dcb154c54dc8fb094b972daef739210d46ad5ad9a` |
| ` M` | `orionis/test/contracts/engine.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `bb312ace335c272f59def7328c61aaed233a386ddd4bbe9ffae476964959d505` |
| ` M` | `orionis/test/core/engine.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4af23949c6e948594ce48167a3867b452e2f7ddd4a5f6fce80a43317e14ad4b8` |
| ` M` | `orionis/test/docs/en/mcp-testing.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `1a8d149b947807cc5864461fe6f23ae2b08baaa4769e77065b3a44b1baa0876f` |
| ` M` | `orionis/test/docs/en/results-and-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `e0d3ccab6e9aa62abf56ec84d5910796ab7d18bd6e121177bd17817c37968e0b` |
| ` M` | `orionis/test/docs/en/writing-and-running-tests.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `ec2aa969462cba5e257a88c834d7577975d97e6b8f8da7696ad29cc30fe83e6a` |
| ` M` | `orionis/test/docs/es/mcp-testing.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `acd58f48e2029ba53b53fc9f414cc221b9902c16c0c805269dacd3432cc42c81` |
| ` M` | `orionis/test/docs/es/results-and-reference.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `78dda842f4f9815b365e9725100db0209502340de76b6c9f27800b14ab59030b` |
| ` M` | `orionis/test/docs/es/writing-and-running-tests.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `2829f076a22d522a83fdb646275ca8d918ba6ed78efe6c7f0482ddf3516fbfb3` |
| ` M` | `orionis/test/entities/result.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4827e516eb88d3a12514290c9e9d1c369f851722b447db05205f7be6f1d550df` |
| ` M` | `orionis/test/enums/status.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0f7528653c28c6b0969bdd228ee00aec4c99dcbadc321f21ebf977c0687ab6c5` |
| ` M` | `orionis/test/executors/results.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `5062b10836527d06090f18a2169e90a48e484063d8b3e09ef9d18e6c728cf6c7` |
| ` M` | `orionis/test/executors/runner.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `91dc533ce25fcfbcfd39a68f0c5624b8d773b6562321fb329877336665acbab6` |
| ` M` | `orionis/test/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c706d7498e1bc5063742c9e5c675d62900466a8977b91d252bb19f4c6c0ebf00` |

</details>

<details>

<summary>orionis/view — 42 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `orionis/view/_failures.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7862ea35e1fda0eb92f9f494646d4c93b9b931b53a43f5be68cab534beac99d8` |
| ` M` | `orionis/view/cache.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4f890e929f47fac05d3d8af808981abe8c260f4615c260d7a7a5fa80cae0e10e` |
| ` M` | `orionis/view/contracts/engine.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b0b80306a5ea9d4c56857568b71376a8ffe115a1ee3c19d6fe9b208e0a94413a` |
| ` M` | `orionis/view/contracts/environment.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `fd4ca7c50b7fe9b2f0b16ce4aa204f61d8e41a75d7d8201ecd4fb47131892330` |
| ` M` | `orionis/view/contracts/factory.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `b8a03a8b7edafd7b552c13e88b65d42718a328bfff21dd3ff6a42cb985b1a4c2` |
| ` M` | `orionis/view/docs/en/configuration-and-extensions.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `84a5649e06c09e8af4a14c87926e5e0a8da806d7b3b2c5f78c555c54e2e52245` |
| ` M` | `orionis/view/docs/en/rendering-templates.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `affce97579acb561fd532ccdecd2ec942d19778a8d35b8507c654bb3850c0525` |
| ` M` | `orionis/view/docs/en/template-language.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `969bd7ed4696e188c6a31c6d9d43a105059785257cb633f0f54997d380daf244` |
| ` M` | `orionis/view/docs/es/configuration-and-extensions.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `44c4a862d7b8839a2ec03b604f4aadb6c973d7ecafbee1275055523b58484e81` |
| ` M` | `orionis/view/docs/es/rendering-templates.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `3a454e78bdb7a95ab490a0146c75db4792355048e6a5b8007ebb73e85d518126` |
| ` M` | `orionis/view/docs/es/template-language.md` | Manual existente: API, ejemplos, garantías y límites sincronizados con la implementación; ver catálogo. | `6b9ca585128f9d14ffd96df0d9e3fbdb99fdc26039e41b1ac91515cb912bf520` |
| ` M` | `orionis/view/engine.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `48bd0a9becce2e271c73e4706c0e7f2c7a526c3200e6198123d7ae6d0e5fd565` |
| ` M` | `orionis/view/environment.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `9a0182c0252281b6b2885ad1539ca70bb7d4c1e5fc21ab8d181679c87fc08bc6` |
| ` M` | `orionis/view/exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `08756071c0b02d9a10e9f16b981cbb9be7d804ad3bf0bca9db316dda96c9d6b1` |
| ` M` | `orionis/view/extensions/csrf.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `dad241c25c421a7535e91dcd421a66f9ecd2ec67892cbcd32f81e193e8ce26b0` |
| ` M` | `orionis/view/factory.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `70718a279daf9de845c6ff356ff1a40d7fe9fa46ab53df6ac13d1babd872dc58` |
| ` M` | `orionis/view/filters/__init__.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `95b6e5681c00197719fb087134c474c5b29827b33bd3f63493d1880edf7e2d2e` |
| ` M` | `orionis/view/filters/json.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `92d815f0b2a29b6c48f62bb020379c29ea15d5001ee81cb8b6468e4edb313d7b` |
| ` M` | `orionis/view/filters/markdown.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `109a80321ec66985eb13363c8a24c76c270967dc0dfa9d1c08fce538b840ccc3` |
| ` M` | `orionis/view/globals/__init__.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4fc4c4e428ed3b51854a6937cd09f87524d407268ab8d060d26472a786a217c0` |
| ` M` | `orionis/view/globals/app.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `77d7c482803ceb218a3b8a4b977ef03287abddbd9e1da5a3d4979678d89bd4ba` |
| ` M` | `orionis/view/globals/asset.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `269262a8c827f900d91e1d58ec6fdaa6471563b4abe3bff3f3913c6360d346e2` |
| ` M` | `orionis/view/globals/auth.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `69f73873035243da745af1e07d6ff6c069537627279e53d5a30209297cac48ba` |
| ` M` | `orionis/view/globals/bcrypt.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `8b85fcc8726df3c9f89345966dd0f9d440acfa56c96dbd56e963b63f03208a0f` |
| ` M` | `orionis/view/globals/cache.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `ad0b771e6eb45ed00ca5ee61a402f987b228b8d2139a86576e0a6509d7f8e0a7` |
| ` M` | `orionis/view/globals/collection.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `380fd2775f3c9f5b21d8aff450b63c9564f44cdb2d5c23b7aaa993f68bfe5781` |
| ` M` | `orionis/view/globals/config.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1e3936e7bee8d419cd1e86bac3008389a1376bb88d57ceaf6f092aa59f325bc6` |
| ` M` | `orionis/view/globals/csrf.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3b3d7d393bb63f8da349ab9554eee988d59bed09800ee815dc09732ac7c07beb` |
| ` M` | `orionis/view/globals/datetime.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `144dcf2570eb777e6595958cc0c2ad157295c0dc9ba09152da6331a1916cdf14` |
| ` M` | `orionis/view/globals/dump.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `4afb106a95347d0ee3a8e633191b8b1ed12b4abee14df6df831359df7dd83b2e` |
| ` M` | `orionis/view/globals/errors.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `f6c39a2d5d73984841f0f9e897f3e5086d8256884f3ab11a8d5910e85a5c8497` |
| ` M` | `orionis/view/globals/flash.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `8b297850cb1063e573c52018a1db258078ee02d2e0d3f5ebb2eb0a67e8d7f5fc` |
| ` M` | `orionis/view/globals/lang.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1255117e8828fb4cfa6882f6ddd7e1245fb7ae32a9dbe923d1107c1935cd4fb1` |
| ` M` | `orionis/view/globals/old.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `0802c4da1d7494f0a1a09201fefa928a65591a2dd93ee6e166a5ca48954e6f86` |
| ` M` | `orionis/view/globals/request.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `6f42c03b1554f7b940cbfe17abbfea5374882a0f5851858c55cdb05860c5858b` |
| ` M` | `orionis/view/globals/route.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `81235b4277bd060a1feeda9fc3e22e530ca14df8dc5ba79d5327b0bb50e70a99` |
| ` M` | `orionis/view/globals/session.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `af5aa8064d7978422bc78c0f46f2b8de912206840a5e303a8c8deb6d946c91d2` |
| ` M` | `orionis/view/globals/stringable.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `1338256fa12c0db3de52e72022ab91942c608549ade7c213469f9e5cdcad7e6f` |
| ` M` | `orionis/view/globals/url.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `d1de5fc19a90038c93c2f695e2e40a3bec7af025a8ceee2c0511d15a4e6c0880` |
| ` M` | `orionis/view/globals/version.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `a8cfdf098aeb5e04fcb87d2d82b4378ca806e0d4dd19f912cc9c4978da478285` |
| ` M` | `orionis/view/pending.py` | Implementación, contratos, anotaciones o imports corregidos; justificación detallada por paquete en §4. | `3ffc9077fe28a8649ceba33b1f8b3068b42360a204cf4fad3643f099e4a20576` |
| ` M` | `orionis/view/provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5eb9b1aa3e55c8051cd28e2ff447372439e519f8d61b2a34d979c353fca5af5a` |

</details>

<details>

<summary>tests — 2 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/test_backend_lazy_imports.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `632313b3f9e75f7bac825dfce2b917ec4e858cb909593d145b2ad73057cbe911` |
| ` M` | `tests/test_naming_conventions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `8ea1ef9ee9a4ab91cae74f3a050668f46e25cbe536f978a646467776e170a7f4` |

</details>

<details>

<summary>tests/aio — 3 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| `A ` | `tests/aio/test_cancellation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3e3c2fa2370f214f27671ad4d674f339968e60cf912215d63ac12d20ac3a5b2a` |
| `M ` | `tests/aio/test_loop.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `47482b7c91646b244ef2a3ae562ccb86d4c7568002367b8fb86080fd0ddcc28b` |
| `M ` | `tests/aio/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `f8bc0b4614190c7eed0237d65d112be7f5bdb32d1175199be532c948c72143cd` |

</details>

<details>

<summary>tests/auth — 29 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/auth/concerns/test_authenticatable.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `d451d1e2c48a1d62da2468b468f2f616e54d144f741baf83be79d4ae356c7020` |
| ` M` | `tests/auth/concerns/test_authorizable.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `13018ea47dacd914231f6340595d33aca96fc577b5ac7e17c0533e490dc5d777` |
| ` M` | `tests/auth/concerns/test_functions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `6279b43e093e92dba85b93d2c4ad5df45f2ee8b2e72bb9f277c915fdea248272` |
| ` M` | `tests/auth/concerns/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `30add7b34620642cf205d75eb0f448505f8458b51a60fdd2a8f853654553f3f3` |
| ` M` | `tests/auth/contracts/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2d625de2070936aca4f5cc40e3c76d5981099b9187813f374edaabdbf814080a` |
| ` M` | `tests/auth/entities/test_access_token.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `6ffa214cff7905b5b73fc03d55b7c216dd8d4b652e7bb408ce5c419699e975f8` |
| ` M` | `tests/auth/entities/test_guard_result.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `d9810a55a4e5da6af3f606fb9060732aa475a2b73ee37a11b5904e60dd1e3bee` |
| ` M` | `tests/auth/entities/test_new_access_token.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `96b477add0392a51440fc007a596b14788b68b290c586650fdcadb75cc0f657c` |
| ` M` | `tests/auth/test_auth_routes.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4cfb5ed57293495f36f7a00b404db12345ca9b076518b9a49d327736f2684d12` |
| `??` | `tests/auth/test_authorization_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `57c4391f9745c9d0edebe4b8a7c06a50c8b43eb111e75a5dd92b7c7a8fcb2e30` |
| ` M` | `tests/auth/test_authorizer.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2c14d7f6e01e98d970a6dc17de89b2ffc61c04b94d0fb9f27e7cb82d6b966ed7` |
| ` M` | `tests/auth/test_config.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `49994daa78dbf69a889c5df62aa296bead37176fe1eaec7dd2760cc4bb60f3ef` |
| ` M` | `tests/auth/test_context.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `a0685d5f64d869a124586e254a42dceea434250d2e10b26316bcebdf5c1ce5cd` |
| `??` | `tests/auth/test_context_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `ec1324f223850e92549e49fdb81a6539ce726097f1a8e96d7baf482ccf01c009` |
| ` M` | `tests/auth/test_exceptions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `534a8c4d2df5234767a7a207935e9d5caade3104c5feeb22a7ca6d09d61d7e9b` |
| `??` | `tests/auth/test_guard_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `eb950ca9724473f11a6049c17ce10df0bb052b59b95c28a76e68158950486628` |
| ` M` | `tests/auth/test_http.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `65521070858c0e276bf5246c9ec4f348ab40717b0a6b52dd03eef2d0e8872eee` |
| ` M` | `tests/auth/test_identity_and_session.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `ac498729b0c1927ec082abe7acb3b846c062264d61ffa9148439eade1e587025` |
| `??` | `tests/auth/test_identity_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `345674d7709040d7b698597ca4ffe5771802d1c22ba88f2c52ac55ca7fb5fc7e` |
| ` M` | `tests/auth/test_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5e8d6cbd05d8657be3a55b8e7d0387d000f120283256e0bf41ef3092a8d82381` |
| ` M` | `tests/auth/test_middleware.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `20f5dffa1acced24dd627fd485e68aef8d157ac33d571b7328cb17b4334f5f52` |
| ` M` | `tests/auth/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `704189633535b5d8be223ebecb64bcff5900c94afda52b755cf4bf7080b655bd` |
| ` M` | `tests/auth/test_password_reset.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `cd8eefda47323dc09ac0f464d55bfa2b5c50227773b447a05b42b556e769dea5` |
| ` M` | `tests/auth/test_permissions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c477c6115f98508783b53e395e6c61f591f6f4cd02a5c23616d076c4c3cdc331` |
| ` M` | `tests/auth/test_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `77528fcca2bcdaea608e2233922de411bca15eb56f5a3b36d52cd498fa07ade4` |
| ` M` | `tests/auth/test_remember.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `8b8a78b4ad0e28214b1fc08b7ccef584452323da101f120340ab67538547278f` |
| ` M` | `tests/auth/test_snapshot.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `38c1084fec28f3bf33f5c2e44e7c9bc4b0f5ad37b4386858c8be27230f3a7c50` |
| ` M` | `tests/auth/test_token_combined.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `1e3afa9416a755a09a0dd8c0fa4ef0fba0f950ef891504b8969926052eee19d1` |
| ` M` | `tests/auth/test_tokens.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `7348dcda9bd93748ecf1f13a59e26aff468dafd028f3d2d18b67ae8a8887ed32` |

</details>

<details>

<summary>tests/background — 6 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/background/contracts/test_task.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `258e6ab2b39229aacc2d8428e6acb7fcceb92fac44ce4793a6cead93c0afa7ab` |
| `??` | `tests/background/test_cancellation.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `4fa71582947329642ad38e5a5392424d0d64fedece769c829e9f7167feffeb03` |
| ` M` | `tests/background/test_failure_observation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2c3c6be2126776970b4dc319af36d350edf704e7c3dd9dd16f8e1ef81b0507ed` |
| ` M` | `tests/background/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `aabe0132f93c042a41cb2081398e5eb5ad3b68c1ff78d0e4abf570f55f79237c` |
| ` M` | `tests/background/test_task.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8193f243da0fa1c87ca291a5e3e892d19c0eb28c3a31bebaa84eb6b90529cb34` |
| ` M` | `tests/background/test_tasks.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `24c4dd4a83b7d54f9fb262dba45a33785b155eb9e4bbffecea9b93137700e047` |

</details>

<details>

<summary>tests/cache — 15 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| `??` | `tests/cache/test_artifact_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `e7e19f8b58d7c5267f4eb220100195ec96ed2b0cff79382600b53d2e899d66d3` |
| ` M` | `tests/cache/test_cache_lock.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `61df079b25f23ed9962c3ccdebd3668f95d34a6acc1c529ff8ee24e95f353d9c` |
| ` M` | `tests/cache/test_cache_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `bb692995cd91c3eb1289a68933a870f1ef37888f97ac69a7b590603821c13714` |
| ` M` | `tests/cache/test_coalescing.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2bb19d9469c75787d3c9793fddca1e97ba1eedacd4ee5a2688c6b9b8f165504c` |
| ` M` | `tests/cache/test_exceptions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `d12f18e658ec28ec55a12a36513683ab1feb2c018e338f5972afeeafa49ef117` |
| ` M` | `tests/cache/test_failure_observation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `962d8edd0827e5d3a76cd0eb6019e51354ca4b19fae045dbc5a3789169760a2c` |
| ` M` | `tests/cache/test_file_based_cache.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e92a2691304aa5af2959ee01bb8ea3818537589420d79dae6adc031a4cc725ed` |
| `??` | `tests/cache/test_manager_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `b21c294b1cfc3ad7afb7ab1c0863a47868aee10917bb5ba02e0f3445c24f5ac9` |
| ` M` | `tests/cache/test_repository.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `34bd454431cc224852ef88753f2c252709bb05b119cb4a592d0936979b1d8e72` |
| ` M` | `tests/cache/test_resolver_lease.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e602cdd27023a3fde3d7e8cb16f70422c941f5cb2d305921909b8bd69588640c` |
| ` M` | `tests/cache/test_serializer.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `1563b7c018069677832092cf0b3553b11ceeb89550a37fa5fe44faa0769e6749` |
| ` M` | `tests/cache/test_serializers_json.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `9194443b6ccc934a2aae80da786c827ebbfd38c6805aad750c11e5fabb4d43ee` |
| `??` | `tests/cache/test_store_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `83f04bf0f333fa6daebda759d0ce9631a665aa6b604c03effa9c62cdf05507d5` |
| ` M` | `tests/cache/test_stores_database.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5dc4598b9416ee551b6496a22b025f0248db859d78c4c423ed13588f0d342c24` |
| ` M` | `tests/cache/test_stores_file.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `26bb56a8fda59f02b53ab5ecb23bca3b7a24b64b16e38fed4546a1c32cd4632c` |

</details>

<details>

<summary>tests/console — 1 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/console/commands/support/test_support_commands.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3a86a5c06cc1d0cc0d751943f52c114f771077b945c50dc244dfa253d694ba43` |

</details>

<details>

<summary>tests/container — 23 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/container/context/test_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `261a11adc04b7dc047963b74725ccd70a474e9044cf0683f326817f3c4ca9c73` |
| ` M` | `tests/container/context/test_scope.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `33168e7d446fed190cd9fe9f331e59e9c817fc69e37944b19fab867804940c45` |
| ` M` | `tests/container/contracts/test_container.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9b5d0808efc06dc0feae943ac8dbfe59480c35b6f84de1b41f989861409d5073` |
| ` M` | `tests/container/contracts/test_deferrable_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `cb4923b793ce963c0a02bed9d902e813eb5ff5a6de948190a0457c70e8a04525` |
| ` M` | `tests/container/contracts/test_facade.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e57d5e051545fc87110d91b352167dca48e073745875bdf92985334003a7a63f` |
| ` M` | `tests/container/contracts/test_service_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `de7d05894f85530952a875b0bf5c9713eeb8fa329f5b5b52dd2f384179325619` |
| ` M` | `tests/container/entities/test_binding.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3068817a9088f94a51cbc86ec5647fb07815f62b29129ed8f7d478987d65e928` |
| ` M` | `tests/container/enums/test_lifetimes.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `49fe3682c1ef04e956e86715155692e9421d11633f4b80ea27b2edb679028bed` |
| ` M` | `tests/container/exceptions/test_container.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f0f80bcf0599fb04a08e0896fa64604ee0702d3ab942344641d39f03c889edf8` |
| ` M` | `tests/container/facades/test_facade.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5a167edb23a2d76d300ad2c6112b8817236042efcd8e425caf2aa1a6782612d2` |
| ` M` | `tests/container/facades/test_meta.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `614d5f7ca638d28e5e80a1873be60d5431de825903b08ffdbf5583cdc2c1764c` |
| ` M` | `tests/container/providers/test_deferrable_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e45314fe5105a9ee77ecab4aeeeda085d131d007b845d51d01e3930e1b5175da` |
| ` M` | `tests/container/providers/test_service_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f496444836b67558eb8cd8aceca3f9b9ebf187284d4dfd582937406b16e4c07e` |
| ` M` | `tests/container/test_container.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `08081414073e967d3d56341bd3f074abc1c986885d3e5fe03e084980b3654f83` |
| ` M` | `tests/container/test_dispatch_plans.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `54a8d0693ba19e1d7bb8f3ab1ee44213af3d1222b249220568974c7e4db3eee4` |
| ` M` | `tests/container/test_explicit_injection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `f6d20b1262905f8bc0d3b4bd807aaf5a6f8df077c10433d5446fa062fda592a8` |
| `??` | `tests/container/test_facade_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `9df20cc37ee799c608be91d195d2a606d12f19d384fee91df867552ee7f25222` |
| ` M` | `tests/container/test_future_constructor_annotations.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `8eabbfda3f647f0c80a7c27ad17df194f6d26646273ac24ae919f228ec569d74` |
| `??` | `tests/container/test_initialization_concurrency.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `2d47a771f9bfda966e7f7a773b579845c30cea42d7c38ccfaa13a3c0746e8a1f` |
| ` M` | `tests/container/test_lazy_imports.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5272b043c1fb649d86813ca72e77dce8c356f061b7e6e80b9c4121cd16bec726` |
| `??` | `tests/container/test_resolution_context.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `75e1ad9996684489eeb059be1cabbd7d855cb5199648521890fe3bbc4772e201` |
| `??` | `tests/container/test_resolution_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `e7d7505887eba74de585150f36af377b4ae98b5539812ad1fb960c60f1d3d131` |
| `??` | `tests/container/test_scope_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `a1f7b0773dee72126cf46ef6e62c7d3ac11fa65150c53a9428fdad7d42aa24cb` |

</details>

<details>

<summary>tests/database — 29 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/database/test_admin_seeder.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `006b4cdd479c2e847b7c56d48480ebcc096ec29a826e301b284e7541d9e01eb8` |
| ` M` | `tests/database/test_application_schemas.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `cd2cf5d85a9d3a0d394eedadd7ac04fc929dbcfe99eb4ae95a986dd8355571f2` |
| `??` | `tests/database/test_compilation_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `dff222fc6f8aa4418be2142be23da9c4c4f4329baa03fe15f5e380f43931defe` |
| ` M` | `tests/database/test_compiler.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2d71b65d7ae0d7a1319f05d5b04ad0559db89c6ea9a7f3eddfb7e5f16b64db26` |
| ` M` | `tests/database/test_config_integration.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `919b23902a416c812186fdedf8d3c8cca661548a1b47c342eedb52b119db3533` |
| ` M` | `tests/database/test_connection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `fb25462ecc7f099de558dbfbef911ad7ab84df63de87df417e57331293ce636c` |
| ` M` | `tests/database/test_connection_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `13540ad5b207750e53e8d4c1cf12fcb0aba786947f1cf5260d37e2be3e2fef43` |
| `??` | `tests/database/test_connection_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `0ec130190c260ae2c6835daad412851b7792b833aeb538f356e8dbfa271ff232` |
| ` M` | `tests/database/test_context_errors.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `16f98920411a4dc3c320214f8054a24655ec779c311ab91a7c6b44f7032c530d` |
| ` M` | `tests/database/test_dialect.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `bf3b270a4a980d362486d0f2a71ea6d2e57c8044dc49a8ab4d2db2fa9db4df46` |
| ` M` | `tests/database/test_exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3beb24d098b1b9811cd2ebd4f041ec1573c286d803ad24b7df4798ba20cd3298` |
| ` M` | `tests/database/test_migration_seeder_lifecycle.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `0fb75d8cf75c708cf9de5b26df7a05b182116d982f8b165c0acd71eb16c43d8d` |
| ` M` | `tests/database/test_migrator.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `ecf0b2016b815e003dc51d3140545e389bf6dd82ef451bb4312a0dab46a5687d` |
| ` M` | `tests/database/test_mysql_binary.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `72274967bb9cd3a71954190071189fd5ac6c44365b605147818cc8e19a275336` |
| ` M` | `tests/database/test_optional_dependencies.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2d1583a9d7035040b4332cbf94e5ca624b4779414daafc2bad7ad499ee2e9a99` |
| ` M` | `tests/database/test_oracle_compiler.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9fd65bc61d3fd85857ddc557984631395c3b10e24770b2c1bc5054868c1e4713` |
| ` M` | `tests/database/test_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `0a4d6bb8c80e83313f72abf74f95c0c2afd122b64f8db0f978897bb64fe694b9` |
| ` M` | `tests/database/test_redshift.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `14c95caa20d49797e6a825ca422031658be38c85114e249dcc9a751446cf1803` |
| ` M` | `tests/database/test_relations_integration.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3b175c81b383c6090295d9002b34cd46e901e583d4d4451c9657acb69f1e0eb5` |
| ` M` | `tests/database/test_runtime_regressions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `6442a34e899ef5baef2f16f1ec3ab5941d0b0ed8ffef015177aa608ad149d8c5` |
| ` M` | `tests/database/test_schema_models.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `fc83feac58461993bfe5d0afe755b0f653841f402976abbe1ee25dfc62c919c4` |
| ` M` | `tests/database/test_schema_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `a6223bf83f0f6ffc53a0894ee80e4370b098b09f7e448dd6084ab701a6588d37` |
| `??` | `tests/database/test_schema_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `3149e774401500b60ae1ae399c69da0578031ee36393f0a1829d3da762b443cb` |
| `??` | `tests/database/test_seeder_recovery.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `6232db930f741d286ce0df7dd1202eb5f1d179782f6f37d0c69c6ca9dac2cacc` |
| ` M` | `tests/database/test_seeder_runner.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `0b76a0f8f8ca9750a7a21d4d5fd6c2055cb9e50e32c72e34681036fb2071c83c` |
| ` M` | `tests/database/test_sqlserver_compiler.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8f7ef981b347ec9a3890bed5eb8c6ae37994a54e13dca353842fa47b82cad4b6` |
| ` M` | `tests/database/test_sqlserver_creation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9b4c330ef599935a0605f8566b68ec36bbea0d6fe22ec338ccfe7595d945f37a` |
| ` M` | `tests/database/test_sqlserver_entity.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7b619e677645a8c109c8d7321b67062d1b023f50b83d20e19a827baa0c5c4d02` |
| ` M` | `tests/database/test_transaction.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `af47134b768af953bf0510cb7f02a616e696233091aad08347ec744489af95c9` |

</details>

<details>

<summary>tests/encrypter — 5 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/encrypter/contracts/test_encrypter.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `bceeb8b7b8284274eed041e3a49222153b2ab54b9811f2d581821b626f3076df` |
| ` M` | `tests/encrypter/test_encrypter.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `27e64fde3fd794024f2267437b167df6c002d7318f50ce22aee47484754e3d5a` |
| ` M` | `tests/encrypter/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b4b6ccc423a26b0ab378bc5989c6515a23d90e62654916baa0257084d4989191` |
| `??` | `tests/encrypter/test_payload_validation.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `3f5e338fa1458006eaa93031c55200206b347502c58667bf65f8d8e497a2964e` |
| ` M` | `tests/encrypter/test_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `bf835d2aa6743b75e127518c72a075d8b39184837492fd7d54d7827db3f30b78` |

</details>

<details>

<summary>tests/environment — 13 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/environment/contracts/test_caster.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `57958d160499707acb274165d50e69266713e7d28603a92f7db6036005e47ee6` |
| ` M` | `tests/environment/contracts/test_env.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `59b26165e16b062d3f28b68b4a68eedbec0c59f6a914487186a973eff72bc2e6` |
| ` M` | `tests/environment/core/test_dot_env.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `07b41a344cd4c951ffd098a03badf9de9840919d9ae379d8139eec35c3bf6ac8` |
| ` M` | `tests/environment/dynamic/test_caster.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `58b9693c83713b729b1cd1be1d1da2fe62ee1d2bb5ed22e39ec654989b2202fe` |
| ` M` | `tests/environment/enums/test_value_type.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2e090bab7547a9226a0f204322f565643239a9b188b3e3381c9357e3dd0ba852` |
| ` M` | `tests/environment/key/test_key_generator.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `766f0fa100be99df4b3dd6300007a0e4de01b2c8bf2d35a95e7a5418e227b61d` |
| ` M` | `tests/environment/test_facade.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `12da7163d57159541b113c613cd39a1fbbcca442867292dd09afd098525dcd01` |
| ` M` | `tests/environment/test_functions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `233c3840068065e22080dcfdf9291a15ac240397cb87dcd701fd66ec5c87a270` |
| ` M` | `tests/environment/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `81e84718e18d3d91206b064ab9de9a3147ad7e495346d7657542e6b28e685ccd` |
| `??` | `tests/environment/test_persistence_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `5f9a903ff2db59aef202ac9ca82023461aa0735228dc7b177dd46d15a5e34aae` |
| `??` | `tests/environment/test_validation_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `01f6042be7142eaf03298b207caf29e6c8ad3a47acdf1ace175dc3505b8edf9c` |
| ` M` | `tests/environment/validators/test_key_name.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a1aced83f28c1836c5872b937f17c8ef8c77debacadd6f4c38f0fba0ed38d465` |
| ` M` | `tests/environment/validators/test_types.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `faa3985052ed127fdfecbef7fc9215a9e3bb3c80ce747e925f35135d9550d95b` |

</details>

<details>

<summary>tests/failure — 12 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/failure/base/test_handler.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c3353f2c1aa61d25af37365d1e10602d3dca2719fe30ec0fe7f3c7be6871b043` |
| ` M` | `tests/failure/contracts/test_catch.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `46ae9f59769f6f4cb8d313591d818cb7ad560d54f1a8c7fd00b333332ee9dde2` |
| ` M` | `tests/failure/contracts/test_handler.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `4c195a11c97f48715243562dec80d85742997209371b9d9803fa8e82c6332419` |
| ` M` | `tests/failure/entities/test_handling.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `01588ab34e7637643fd8df89068f51bb09f7812c143624b5b08a0d342b933630` |
| ` M` | `tests/failure/entities/test_throwable.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `43df01ee30be720ea52f590bdb34293ecc2e057c1240b4a87d7911d14283dda2` |
| ` M` | `tests/failure/enums/test_kernel_type.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `34050fd9191fc7d2fa5c3a9eb6a9b90faf73999879bbe6db36c84ffc07596e3b` |
| ` M` | `tests/failure/test_catch.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `58703542cc5b41e3cc6f7ce715e592885fc5026e7d32e9ee6f213d7418aa59c7` |
| `??` | `tests/failure/test_contract_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `46c6f587ba375c2a2fcdf4c828cc398cd14fe76d69128371f5f10189157cc8cd` |
| `??` | `tests/failure/test_handler_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `7d57873d8f271f3c69486c89c86b8346a0dc0d0830b384ef2cba6052f2bfb0ed` |
| ` M` | `tests/failure/test_runtime.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `0d5ec0df1f5777d047ab77ea7bc197da1ba15338c2a939950bf36de6f2ca21c4` |
| `??` | `tests/failure/test_runtime_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `3b9549e9e1a14464f94ecb39189c0c190350c4c8e8bfd1d35c8b7a7750a777ac` |
| `??` | `tests/failure/test_scheduling_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `6b4bb18db6ee091abbbe9807d32cc978187ab241d5e81b84d23916ed8d156e78` |

</details>

<details>

<summary>tests/foundation — 2 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| `??` | `tests/foundation/config/test_authenticated_ciphers.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `da627a0a4c0d98b4898e2861f7d3ec82ac9e9d484d3ce06db6961dca197f2aac` |
| ` M` | `tests/foundation/config/test_regressions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `27c6be5686baa767ab0f67f3dc695254a7b7a101a5272bd084dea414a5d53deb` |

</details>

<details>

<summary>tests/hashing — 16 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/hashing/contracts/test_hash_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `a72a835e816d616a5a9c27502e9ea20cf1cfe37e7b94b6ff6e4d34ff9602dab4` |
| ` M` | `tests/hashing/contracts/test_hasher.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9cb48ea60801106db272df9f45d081a7526ec2bc4ded51a74d603f3eb4626ca3` |
| ` M` | `tests/hashing/contracts/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `18d43186affb4242c18dbe8cbb694d569a7bb1ecbac4579db51366100780d216` |
| ` M` | `tests/hashing/hashers/test_argon2_hasher.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `b6595c1ae57a66e6a5bc556088f57a87545444d944f9cbcfe90a2d41b8501b06` |
| ` M` | `tests/hashing/hashers/test_bcrypt_hasher.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `dbe18f75389585f10e89005a9a18787cda175267b9f95cf90bd14b4d740ae72f` |
| ` M` | `tests/hashing/hashers/test_functions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `515edea57eca3c8b15f836a4ea1b08551274868357bef94a72862d37c1fd1fe8` |
| ` M` | `tests/hashing/hashers/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ee18faa7f5392aa571014ad87961a32940d3792c4cdb46e9aff2b4652ed6297e` |
| ` M` | `tests/hashing/test_admission.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `81b8f05bbecd6de633f1757f6173cb24c61bf79d624dce4859ff52bdacd3bf1d` |
| `??` | `tests/hashing/test_cache_concurrency.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `b9e9cb8e9da8ff48820c29f2acaf1188c9836dbb20dabc9b695afb57c5286b88` |
| ` M` | `tests/hashing/test_config.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7337d361f29936e85ed739d3aee02d4308a8a8e6352ad54762420929b58a3209` |
| ` M` | `tests/hashing/test_exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `edb5e60fdfafceecb5dda35cea1aef8240122ec07853efafeda00290e16fad4e` |
| ` M` | `tests/hashing/test_hash_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `0381ad71f3156f03f162d1c59b2822063d6324abbb3a69e294fab8178b3b4e4e` |
| `??` | `tests/hashing/test_invalid_hashes.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `043df5ae91a0d33bb4691a86feeb86cd448eda4e84911ea75075f6606bc2d124` |
| ` M` | `tests/hashing/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `757fcc7e39b015f44d979e2c1c6278dde7519742d6ff4244772dc146073b8941` |
| `??` | `tests/hashing/test_parameter_validation.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `cf1c92175facd96e7c9f619c86808798885f13fc0949c19e698590ad4cbeafb0` |
| ` M` | `tests/hashing/test_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `d2a8c4f9ebe29c2865f79468cf86fb5862c67a88c5810e0bc4d3fb34b2cd4ab8` |

</details>

<details>

<summary>tests/introspection — 24 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/introspection/abstract/contracts/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `81a4436a410c6c9d4ad4ee76655fd2753bd25c6de9c2aa3efe4689b080251c46` |
| ` M` | `tests/introspection/abstract/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `6899e1a3f371aff6dc1fc543880a2541aa49c62fabee46826467ef52ec646cf4` |
| `??` | `tests/introspection/abstract/test_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `19196b01dce06e5bc351f2da4177ae0c3fa6b68621f862cecfb4a99ad2f22e14` |
| ` M` | `tests/introspection/callables/contracts/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `1a9e78e49ce2df1ab01b80229339439f03cd570e311102965bbba98ca1338259` |
| ` M` | `tests/introspection/callables/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `14952fa70fcbad94e5b4176c23ed10aea18100e2c04fb878852da9a3daae2268` |
| ` M` | `tests/introspection/concretes/contracts/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3b61de34968987b69528c443b11806ec19f9e906402556b8e57176277cace643` |
| ` M` | `tests/introspection/concretes/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2a832c53acf510f31d62e541e456b3f632fa127a9a4c451de16b62c2e801affc` |
| ` M` | `tests/introspection/dependencies/contracts/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `06d991d4ff296852be3fdf3b77ac841f782f85afb5c170c9cb186deccc502069` |
| ` M` | `tests/introspection/dependencies/entities/test_argument.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `97ca5d9152c9a49f46363b988ee46dcabe1cd0db0debaf2116a46b20af3c7b14` |
| ` M` | `tests/introspection/dependencies/entities/test_signature.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e3d68deb42ac358c4128bb5f6fc567c095dbf86f95dc72c6a0a71c454ea6fb98` |
| ` M` | `tests/introspection/dependencies/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `705aca1e021d1de1a76cbe7a89d75be5c93433067b5c7b38120cd2cbacac4968` |
| ` M` | `tests/introspection/dependencies/test_signature_cache.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9b440dece6486a1a6c10f50406bf60348c82f84289aabdde3a1a1eaab93cebf2` |
| ` M` | `tests/introspection/instances/contracts/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `f7f18ca956478d8b2b82dc6073f1a1e62d47c765abb8e7da3bd40635e801a0ee` |
| ` M` | `tests/introspection/instances/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `7d503674338ea0c04e613985d7398d5ba8cbd495280c272451d0ef701067e381` |
| ` M` | `tests/introspection/modules/contracts/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `45e6c9aa8b67f8d295eed7f73f7099b39d3ee42d321f55310942153d3a6759f7` |
| ` M` | `tests/introspection/modules/test_inspector.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2e5cc041ef5aed0fdcd02ac809b782db242551892cbd6a8b061951e650bdb27b` |
| ` M` | `tests/introspection/modules/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `311c4bd52a937c04ac0ce835ee8824c496e2b625624fff36d084c0f009028b7e` |
| `??` | `tests/introspection/test_binding_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `bafd22c6120e3ca07c256bfa437e498d94195a2ce9649d547f5afb1fecc5e47b` |
| `??` | `tests/introspection/test_cache_invalidation.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `28ab060d86277c32133dc2d501a731be6de86c2bff16dbec10822ed33d5662b8` |
| `??` | `tests/introspection/test_callable_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `7565e78238638bc095e373886d432e2a12119eb491002be81dfa96385d05243d` |
| `??` | `tests/introspection/test_deferred_annotations.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `633ffabb138bd7abc19da7438c5a8786bbbf45c183d930983e06b3592d9279b6` |
| `??` | `tests/introspection/test_member_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `c9e6238590d9dab705e8798d8f011e3e921cd1bb4e4879605e2a3958002efdfa` |
| `??` | `tests/introspection/test_module_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `bec24a38270ed7971d0db88022f02fb33d6c92a1b7b87d66ab0ce507f6e75c2c` |
| ` M` | `tests/introspection/test_reflection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `80d50d9e682d44a08e2f0aff1463e7807937957e43a011b1f14fb34b6a4689a7` |

</details>

<details>

<summary>tests/localization — 18 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/localization/contracts/test_loader.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5f8c2ff12ca7702577dff7df77aef091aa7b1c82ff580afdc5860868db546c84` |
| ` M` | `tests/localization/contracts/test_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `14c9c765758d10c378848ab78c4cfff6f2207e35f44b16e69e75409a5b737f2c` |
| ` M` | `tests/localization/contracts/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c3542bcb628fd06d9c090dc24397ca434b5a01cd5147cdd038c3a80de69c41dc` |
| ` M` | `tests/localization/contracts/test_repository.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `82fd99141a4a4e48d7a1964caee28d12158e1ce4ef7cb0dd4a5beba27ba79ae7` |
| ` M` | `tests/localization/contracts/test_translator.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c10f8d8131a8b994f31ab8bd1a367096fa21652e258e28667a6259c1df1f58a2` |
| ` M` | `tests/localization/test_cache_limits.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8b6bb26f070353684615d35fd162cfd2c7ffc65cf5ee5a4ba08c97649b822835` |
| ` M` | `tests/localization/test_exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4bff784a244f34449878b7d382faa5214cbdd8af1a4f2fc5bc7e5293aa9a98ee` |
| ` M` | `tests/localization/test_integration.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e500b0c2991f43f3713e9e224cb18cf34bbd4cd7645301a17d75793fe7b7a6fd` |
| ` M` | `tests/localization/test_loader.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e2f8fb32a25061bdb2dcc530b051671a7f14bdfdde6757569d61671733c9f1f5` |
| `??` | `tests/localization/test_loading_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `d9b6380e252e776c7bc56b2e99ba4de6091731af21a278faf8a112126976ff05` |
| ` M` | `tests/localization/test_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `d037e53bbaa9458c5e121979be35336d74223898bab3f86cb80521fe2ec75d65` |
| `??` | `tests/localization/test_manager_concurrency.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `039904ac19584624115f8ef17be988c6f76c5f188e9ad3b64ee80ac9878fd8a3` |
| ` M` | `tests/localization/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `05e2961d439bc1404bd19f3b543cf52b5283010aa66a8ea9563f37a72301d46f` |
| ` M` | `tests/localization/test_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `89e0c3e039275f4fd2b9efc2554dcc7bf22740da68ca28e888a8cb19e238d8ba` |
| ` M` | `tests/localization/test_repository.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `4ea88e3ceae54c1df628f1ec4ce90a2326fb4419ce73139856165f0c1752f186` |
| `??` | `tests/localization/test_translation_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `6f1eb6f545bc6bf71edd38bf4c2350aaef10fe2e9fe48a81ed2b76255d59092f` |
| ` M` | `tests/localization/test_translator.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `f0f449f226893a970afa64086ecad7e1bb538ece4afd6c6571d9c554e7ab7954` |
| ` M` | `tests/localization/test_types.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e8860dbf440f37efe9b572b5af8f77c8dc67214aaf75eb7712cfea91e9998af1` |

</details>

<details>

<summary>tests/logging — 16 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/logging/contracts/test_logger.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `8e8c6a7508295075555ee70b10f44777c34e7c4a5604557d6bdc4512f8526d05` |
| ` M` | `tests/logging/contracts/test_suffix_resolver.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `16b6e7dacb4cee0b44d279dcf8a0d813105bcea616c958c61e15e89adf5b269f` |
| ` M` | `tests/logging/handlers/test_advanced_rotating_file_handler.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `494419dbf766a801b91ac55ed461bc0e29529d737d0b22a7b26dfe97d7bb683a` |
| ` M` | `tests/logging/handlers/test_chunked_suffix_resolver.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `98bd8ad55965baf7c17eb5fc76447407bd948ee7c63d1edfd92c9b9e596fe2db` |
| ` M` | `tests/logging/handlers/test_daily_suffix_resolver.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a666880c1e90b6e7b3d6450f976f59ec429eea45ca39cecb115910d45f25f515` |
| ` M` | `tests/logging/handlers/test_hourly_suffix_resolver.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e709b8af38e16adb30b032457e8260fee14cde55c31f736cf29344968465ef9b` |
| ` M` | `tests/logging/handlers/test_monthly_suffix_resolver.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `203c42baaea5aa89fa658dda5e1bb3418f581778206d3a84d2746964da6149f3` |
| ` M` | `tests/logging/handlers/test_rotating_handler_factory.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `fde1ae048fbb51c7912e70a32c7c4db80ae1493c87f245c8c3d589149bedc9f5` |
| ` M` | `tests/logging/handlers/test_weekly_suffix_resolver.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `ea9478d72c7c9c4001054195080b9ba0bba876746cf2ee8f5187c6d77c728fcb` |
| `??` | `tests/logging/test_handler_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `a41f58e14190904a95c33fc82030fbcae7e86db00940ba8c737aba7caf4a28ad` |
| `??` | `tests/logging/test_lifecycle_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `53d3426edf78516084e8d14defac8ec90f63caf6f46de77be8af2abff50399d9` |
| ` M` | `tests/logging/test_logger.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c4c7131570acf1e7a252504051174b3736e9c7304f89f0bfbcf1ebaf1d65f3e0` |
| ` M` | `tests/logging/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `39347668e6a8acd5ce332d38238210a52a5e258aa483120ae10afc2e38a11b7a` |
| ` M` | `tests/logging/test_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5328851f18f462dbec81d3221278e22cf3d9c5a71d4dc456a1da40a449081751` |
| ` M` | `tests/logging/test_queued.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `15f5e7b5c4a432cfc047a23249a9a0505dbd11c23a239fcccc886616d03cd6e0` |
| `??` | `tests/logging/test_rotation_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `cea86c6774914736db9ab96ba2d435820bd82f472863810fc89e74e66695caeb` |

</details>

<details>

<summary>tests/mcp — 1 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/mcp/test_state.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `cd43c0a0a820c3fd5fcc00988dd887810ff80abcc8c255ff54df6b0ba04c4538` |

</details>

<details>

<summary>tests/metadata — 2 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/metadata/test_framework.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `a9c7174537195a5e3a394da6890376e4f977d5ce8a0fb1d85ce8b4a16eff80c4` |
| ` M` | `tests/metadata/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b2ca2dc01e183c954bffd6714ca633852c998379dbcbb0d0f2e2c6fc9aea9681` |

</details>

<details>

<summary>tests/orm — 100 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/orm/collections/test_collection.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4feae58a9d8bcac39daff3d23db81bed3ab99cb43272ad8db43b1c3411d96bd4` |
| ` M` | `tests/orm/collections/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8dabda13252c0247a180ccafcf66433a63d5d6e3a02924ff512e2213d8c90ba6` |
| ` M` | `tests/orm/collections/test_paginator.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `0b3b9b19c2ca964a76d382a574324593a46f50c86379ee7cc93f58df26ed4826` |
| ` M` | `tests/orm/contracts/test_base_builder.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `969c9c0477b72ba82a5c363da6e44281f6b03a56bd2c1fee1791648a4b7dd6ab` |
| ` M` | `tests/orm/contracts/test_belongs_to_many_relation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5770724ecc895039c9e47718c6ff4a142b466c980aed2db0cef1a2298a0d7c32` |
| ` M` | `tests/orm/contracts/test_builder.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2f85be7578bfc16b2918b879e468bdff88bff2262cd6cbcbb15b15a732f6fd99` |
| ` M` | `tests/orm/contracts/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `883ae554465fd63622a96b36b39ce5fa423b8d0d11d033ea5942ebd62839fd21` |
| ` M` | `tests/orm/contracts/test_query_builder.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `41c9f3a37bafae5a7ae02f0d3bf9c0fd68a85375da9d80fa7b2fdf0ca8a93930` |
| ` M` | `tests/orm/contracts/test_raw_builder.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `6ea6878fa47a314bfbab0a88714e13b90c192bd048f331c1ac86ad2622b3304b` |
| ` M` | `tests/orm/contracts/test_relation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `b4aee88a818774437fc26907b939e5a0952d170e2b31c1d673a0dbbc197f2344` |
| ` M` | `tests/orm/exceptions/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `818a56d6c220d387bb8eac8d78b0b70238be4739fa37b29c745634ee01cfea80` |
| ` M` | `tests/orm/factories/test__attributes.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `047345ad8f08dc1bbcb2a357e017ebc947a97454426c04d7ee82f42cfe9c5504` |
| ` M` | `tests/orm/factories/test__faker.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `20e82b2fb7a32a7fff3f38808c63b734b8e71193495b546345675977b147a060` |
| ` M` | `tests/orm/factories/test_exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a823abd52ce149c32fa972a300fec6e78b65b5a1822f2e80374c5dfc8c226f10` |
| ` M` | `tests/orm/factories/test_factory.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9899d62eaaacdc3496ad04852eebe74ed7577f6fa8e8a4b467d9d752517cd104` |
| `??` | `tests/orm/factories/test_factory_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `5224a59ff6b7c0c161db5b917fd98dc53bb76f912aecb40d2073b307073a4fac` |
| ` M` | `tests/orm/factories/test_fake.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `6bdf2e966a2bdfa2102a3e731242567f294449010bd3b1356a1b1f8c6aecd9e1` |
| ` M` | `tests/orm/factories/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `48c9d9f3ea3d96f2b778f43a77f98ec78eb50820e3fb2517aeb34550147b54b6` |
| ` M` | `tests/orm/factories/test_sequence.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `814e85f2f8106cccdbb181f5fc910f794ef0e34c60ce1951da44c8a9b6553824` |
| ` M` | `tests/orm/query/test_base_builder.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `1722e1f7bba8bdd897cdd61515f57308aedbe4e5b1b11c70342234f582492b85` |
| ` M` | `tests/orm/query/test_builder.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e61a7eb2ddfda67482a644bf4e5c842f6f2198264e09ed91cc8907d1333d834e` |
| ` M` | `tests/orm/query/test_expressions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e3622d8871e15775708044a7bbd970b9aa18209db54dd3691ca2148693a4e249` |
| ` M` | `tests/orm/query/test_join_clause.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e06b704cfd0c7af258cc4d823fb62e8ad7b8eb44686a51cf4088831651a1b5d4` |
| ` M` | `tests/orm/query/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2ed3f0d0a98e9679064e0cd00f6c234ae917d44b37d2870d0b58589521780464` |
| `??` | `tests/orm/query/test_query_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `c171bcf55b2ff75e3165283b7beec05888dba202f75ba957ea060e1ce0ed12d9` |
| ` M` | `tests/orm/query/test_raw_builder.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5085b789a7a5fe8970aeb94d1c52293c318ba59bab232a298405d3a11affdabb` |
| ` M` | `tests/orm/relations/test_belongs_to.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `90436d67e79601d89c520cd7e40cbfc28c50e271f8b13c9ad58a3d00f6545139` |
| ` M` | `tests/orm/relations/test_belongs_to_many.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `1b8cd57f01a60bf85714c9efde8bbba7a68de3b38e7247e8c95580a792b69953` |
| ` M` | `tests/orm/relations/test_has_many.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `457d618d9fcc39f3a196b5b5cb2fc5395ee4595c726d7189805d0caaab52b442` |
| ` M` | `tests/orm/relations/test_has_one.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `242bc15f2c27e6eb739e5616057b05970f6d32a15823f80bc0dd3bede4188178` |
| ` M` | `tests/orm/relations/test_has_one_or_many.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e389ada04fc09af2c237f05237051544ca8d5895eadf8e80bbb93bc8d8536b40` |
| ` M` | `tests/orm/relations/test_mixin.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5a79ea84b4ac455e805459567bd8fa76810aa7bb3364beab8bb3c0527b5f351c` |
| ` M` | `tests/orm/relations/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ae4c26c5d2470df27a8fde43531b85966a845e54927491ac8efacc803f052664` |
| `??` | `tests/orm/relations/test_pivot_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `af5156bdf13ed577d6344e80de18456d104ed008a52a4398c309dcf6f797cf25` |
| ` M` | `tests/orm/relations/test_relation.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ccad8f9796a53ea7ae425ad619b2f6f4e138fa72f933487e482d44afb666ee42` |
| ` M` | `tests/orm/schema/column/test_definition.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `89b00cb9d0ce4f5e4e5457cd3f3bfa87b9c6ae53defd1068ad7aff7769849f18` |
| ` M` | `tests/orm/schema/column/test_options.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `531fcc3adced9d92fd8efba384b9e2bc5e9674f8673b01d093bd666c834f7894` |
| ` M` | `tests/orm/schema/column/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fd3df66af24ba36411d75bb9f55adeb93f0c4efe6b5bf3322928f9709997c261` |
| ` M` | `tests/orm/schema/constraints/test_composite_foreign_key.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2061ca843fec13308f89b68ac6c2753147a3c477cebe7d988ac75de36fe43b69` |
| ` M` | `tests/orm/schema/constraints/test_foreign_reference.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `9a1f0decd5071b6b5669da41e9d5858a3bb3401b9f2925fb70537e28e3709011` |
| ` M` | `tests/orm/schema/constraints/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7d6b4b3138c1283c61100490bac55c571ba981a6544327baa4a9c5d28fbeae94` |
| ` M` | `tests/orm/schema/constraints/test_table_index.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `1bf0190c67a3f3594f20d8a9b77e76b3a4a6c23d70f1a01dec2c852b626f3adb` |
| ` M` | `tests/orm/schema/constraints/test_unique_constraint.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b0ffdf0496b2a144e2480672bda733c95520aac871d6bdfa72b48c016e91a313` |
| ` M` | `tests/orm/schema/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `86e0a13bdb9783e659ad321875e7a00a84aa22cdc3909c8833835e933cb16166` |
| `??` | `tests/orm/schema/test_schema_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `e671b7fd80b40d4ff9d5b63fcffc82d444b7f5a3f113da03603ac9c07c4e70fb` |
| ` M` | `tests/orm/schema/test_table.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `78dfefd1bce6084ad2ed54e5dd8a8f7bb2f42ec164b410d2edc1cea6261b6e7f` |
| ` M` | `tests/orm/schema/types/test__constants.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `fa50fa556a14061e6044063634ea087dad3c367bc2d689aa88b793dd020c515e` |
| ` M` | `tests/orm/schema/types/test_big_integer.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `226cdc6166bf0ad77fb0c10f4405b704a570de1c4319ea5b1e5c089e05cf1c78` |
| ` M` | `tests/orm/schema/types/test_boolean.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e0d88f77ebdf50e9662164457cc749bffcda691302ee0226fc1125660d34f3b7` |
| ` M` | `tests/orm/schema/types/test_column_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b5cc0a894660ac442e804d86e026a87f74a144be94db73fb258bf545888c3054` |
| ` M` | `tests/orm/schema/types/test_date.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `04eaeb266a6f3a88f4cad4f2bc95b7378f09820d40d2df34f8dcd99bb7b21bfe` |
| ` M` | `tests/orm/schema/types/test_date_time.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `91f771b45a94a63b2b645c92b9b259bae1110e33f5b5f654e61e62c819a8eead` |
| ` M` | `tests/orm/schema/types/test_double.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ee48761bf195732cbbc32e91f7196114c75caf5fc2ad9d2aceaad463abb5f4bd` |
| ` M` | `tests/orm/schema/types/test_enum_type.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `a1bec054fa863d9b5d715d8dd23d898e3b4a31500c2b90c3a5ef7fc06012db83` |
| ` M` | `tests/orm/schema/types/test_float_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `d293290d7ac9874023e83c68c126cd045f82bb968f9509c1054c6f4983009467` |
| ` M` | `tests/orm/schema/types/test_integer.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `089fbe25a8abe1ab78f6623cce402568c981fab0511dac87a4d428d60ce451ef` |
| ` M` | `tests/orm/schema/types/test_interval.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `33998444a66a5fa062293cfd59ba7792acac6d365ffbac07f5536279e4fe85ee` |
| ` M` | `tests/orm/schema/types/test_large_binary.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `f3c00986ca203b7681873774214702949adc51d2f26a22b4478eb89547f6d41e` |
| ` M` | `tests/orm/schema/types/test_match_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e7cf5792227bfa66bce0a2297dbdedec4c76feb4f2dbe58d8b1fd028e2451f06` |
| ` M` | `tests/orm/schema/types/test_numeric.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7902ca4da64aac697647be8f4de6e5a3288b655861e3f91602977b53476c463f` |
| ` M` | `tests/orm/schema/types/test_numeric_common.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `63b2171a0e6398d68a620fd4436c6ae3443da7cf16e416bdf1994b2cdd1f2a4e` |
| ` M` | `tests/orm/schema/types/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4f6f57e866d4cefc05978c5fb297744d61926c4b151433749dce467b428c43e8` |
| ` M` | `tests/orm/schema/types/test_pickle_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `1f088ce219f165b5a8102a3ba7d1c3845f6592ea152be935c0e13309e9312a45` |
| ` M` | `tests/orm/schema/types/test_schema_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `eb48a0b6900dc659ac6bc28fc8d653c3c121782848825a46e688f54e6096a1aa` |
| ` M` | `tests/orm/schema/types/test_small_integer.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b4d04e3677f7d6d9d679740ea6b4e9b82401103c2a93412584a3c46fc7cdf6b3` |
| ` M` | `tests/orm/schema/types/test_strict_array.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3a31c4f441b9b4ec66d7f5d234dab62ff35883ec3a7a4e65b617cc792ac727b8` |
| ` M` | `tests/orm/schema/types/test_strict_big_int.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e096d989e3fb5c999b806abcb40284142fccaafdfa1e92598864fe1e99e1fd4a` |
| ` M` | `tests/orm/schema/types/test_strict_binary.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b1a0de2c6537f2b27d2ada8c99cf49b7c2da661e57877193ad781c87b775f01f` |
| ` M` | `tests/orm/schema/types/test_strict_blob.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `89de16f89903135793894775f31b7463e442015b4ae59924a35e98ecd4d0d9df` |
| ` M` | `tests/orm/schema/types/test_strict_char.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5ec62912f49aca30177919cede9d164e7635c4375b9ccbb542b8e24c0bac9ed8` |
| ` M` | `tests/orm/schema/types/test_strict_clob.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `8358431a60ec401b0cac1a8ddd47b2b9bc064a0e660385def0670dde1c6d8615` |
| ` M` | `tests/orm/schema/types/test_strict_decimal.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `7ecf8701d3cfc76421f5c8cdbd7a961579d47ae55e2cbf15be702a9b3fbb013b` |
| ` M` | `tests/orm/schema/types/test_strict_double_precision.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `420b2f98a774f28bf8ff78189585b299e0f2b69b6beec0e9f828a0e719de0a41` |
| ` M` | `tests/orm/schema/types/test_strict_int.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `bff92d1ceb9972f326e290f4d88e296457d8f536c125ecdfe2ff3b88fbf2f947` |
| ` M` | `tests/orm/schema/types/test_strict_json.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3e2f5f8262e93a6b7db609d447aad1fda06466fcefc5bd67392de6c6c18c2f8e` |
| ` M` | `tests/orm/schema/types/test_strict_nchar.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b66edd37498955b60e7ea01fd050adb8961ea605e2d00887426bcd21e5bc1543` |
| ` M` | `tests/orm/schema/types/test_strict_nvarchar.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `71cef2c4ca03615e39cb019abf57657c4e38f13b06710fb6b34c25299618a46b` |
| ` M` | `tests/orm/schema/types/test_strict_real.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b7cf54d383631cb2f2af1da989898e536e270b3c977122cac787ff3869ca146e` |
| ` M` | `tests/orm/schema/types/test_strict_small_int.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `be6be8da18f4e7831b582ebacead1c51c0160af177e94f8adaa181431a431ff0` |
| ` M` | `tests/orm/schema/types/test_strict_timestamp.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `522b94670dbee6c454c2ff9459a35a7d437c10a8166a759c92a8232a7f540e41` |
| ` M` | `tests/orm/schema/types/test_strict_var_binary.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c39c5a832861bcf6dc62d535b8ba5756d6520f7cdd87f7d4ccca33ebe1f11122` |
| ` M` | `tests/orm/schema/types/test_strict_varchar.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `66d535f28df5eb050a369bb6a6a75735188bca4a93342f2c1a8af1c4d6de5065` |
| ` M` | `tests/orm/schema/types/test_string_type.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3f33aa8b2c427f0746d9f41754be5e8295600a867a75498e3c2d4b62941c8154` |
| ` M` | `tests/orm/schema/types/test_text.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a224090013fc4cb15b12694535393dfc7a30d17b6f99cd8f320e23047878734c` |
| ` M` | `tests/orm/schema/types/test_time_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `d859fe15e3720d06a4e4018803afab0f2dc7ab25929d4d421f1a5a2d6f0c895f` |
| ` M` | `tests/orm/schema/types/test_unicode.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `041de690904ac1e0bcc0191a5624e516768894795028d9855e0fd4baa0cad29f` |
| ` M` | `tests/orm/schema/types/test_unicode_text.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `7025f9e95ca35e8391156107a0d5e8b7e8a85aace72205fde0ce49821c63cc4f` |
| ` M` | `tests/orm/schema/types/test_uuid_type.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5da30a7455da98ed842deae9a3656651a33bed42aac79edd631fbeb102884c72` |
| ` M` | `tests/orm/test_attributes.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5ad8925f8f91fc67bfaeeeacab68cebc519485b36e80bcd84413a319a14bbad2` |
| ` M` | `tests/orm/test_chunks.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `97c2dc8350e1b0f2251f889c7cc75e3d947b03c3c697a12417284a1f0034460a` |
| ` M` | `tests/orm/test_events.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9e5cc0c2aca11a323f4c4327bda3ed0f4098e5cf162771b40bf01245344569e2` |
| ` M` | `tests/orm/test_metaclass.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `1ccd2251e3fd0c1e45450eb38b33bd402d8501680016d5aad3c8abbb0cd5cd8f` |
| ` M` | `tests/orm/test_model.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `1e74131ce84ea938848b65dfd7242082b36594e05b53f716af977244781fe615` |
| `??` | `tests/orm/test_model_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `b27566fac939549bf109180a3c4756c51b8ccf7a66c21ba2a513ffa8f01174bf` |
| ` M` | `tests/orm/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `cc853ac685176f6d4c146c94e5ad19889b4e9c19b117494768b0d4299c82e2d0` |
| ` M` | `tests/orm/test_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `28c801c1e296712a993e97dc49888015784660c34a91bac38a96dad9779badb4` |
| ` M` | `tests/orm/test_query_builder.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3ebef61e5d1806ad8c29266185427bc64fd424171535ad90373c7b208295662c` |
| ` M` | `tests/orm/test_resolver.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `739734026036b3557f1ab52a110f89caeb2a5e1bde1aed8e614d2ab4ed6ff0f3` |
| ` M` | `tests/orm/test_soft_deletes.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `a1b4bbcf0247eaffce539c30de7572fbddfec2adcd90874d3aaf98b51bcc04ce` |
| ` M` | `tests/orm/test_state.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5a3e5bca0aa6231de848ee7bb09a1784337675d812309ef520f5d1c78c397b3d` |

</details>

<details>

<summary>tests/schemas — 34 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/schemas/entities/test_failure.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5e85507a12e64f226d1fa82170c0c75794c4c454450b5f5a9864e7c450901577` |
| ` M` | `tests/schemas/exceptions/test_validation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `588d5f3ad243b35591a1a4c5489ca9d98872cd7f90790b4fa98a3155f09e3b59` |
| ` M` | `tests/schemas/rules/test_active_url.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ac8fe5e8e5cec69804183c09bcbad1c5a21b92743fc1af319be8433e9e8ecc2c` |
| ` M` | `tests/schemas/rules/test_confirm_password.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `081e49b7f6900bbb4cc02baf58935dfaa0e1c0112640b984951f7178d919cd12` |
| ` M` | `tests/schemas/rules/test_date.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2d64e9dbf8ad6b19d599c8f15fa296b393a00c0e01e1435a1a48343ba62c98ca` |
| ` M` | `tests/schemas/rules/test_empty.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e60d439f0f06a475cf0307922ec34528e14a8a722ed7a05ff787e02b8ef899f8` |
| ` M` | `tests/schemas/rules/test_file.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `213f4bdbe75bb97745d55828f54b09a410e3ec1e66d410790f9ea83ed600758a` |
| ` M` | `tests/schemas/rules/test_integration.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `b873dbf4a2149024b12178c4836ccc5f23b06b1e8043853da9a0cbf32b39d3e8` |
| ` M` | `tests/schemas/rules/test_numeric.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `3a0b5b086b0127e48b5e619121ef77c03a284e1d4785edfe3bb292e962bc8bb2` |
| ` M` | `tests/schemas/rules/test_string.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `09bc69d36eba434d2e6a0927fc4715445119ef4062325a1a5a8c43a76e481bf9` |
| ` M` | `tests/schemas/rules/test_strong_password.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `2a203942072b4d889ff6640d94eb0b9ed66f192468d3f1fa2754aaa33f9b5d78` |
| ` M` | `tests/schemas/rules/test_support.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `741995fb5e7a73ad1640ab501615eccea3530026405a6dde1f2172d2caf0e7c8` |
| ` M` | `tests/schemas/rules/test_unique.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `49a5bf587435d3837a2ae5d3b9ca108e31a8f3ae5c6d7d2f5c2583b13bd68684` |
| ` M` | `tests/schemas/test_all_failures.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `634c9e57fa782c23eadfd7b945f106ef1f20d3e82bb6ffc54fa0a140d4a4af3a` |
| ` M` | `tests/schemas/test_coercion.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c63502784b0204a0b8efdfdf60bbfeea350181b72028aac2f0bb620fdc71ca8c` |
| ` M` | `tests/schemas/test_collection_validation.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `30cc049094f4d68dd60802dfe17bd01eb41b52e943fa51b9d6917e7de47c91da` |
| ` M` | `tests/schemas/test_compiler.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `d43e882e4fadd6332953f9f66ad19d2d91c4c1593d6ecc78f9363c91f725f549` |
| ` M` | `tests/schemas/test_constraints.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `cd34c7066bed5b12594fc22ca9ab56818917e09c520ec16b5dfbd02a5618b0a7` |
| `??` | `tests/schemas/test_core_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `53546154f976e42271fc8606b7c001ac16debd3034d779755dea3b4ceb0f24cf` |
| `??` | `tests/schemas/test_error_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `5eba290ede0aeea13c141292019ffb2d048bc29ec13b09b1906689619dd973e2` |
| ` M` | `tests/schemas/test_exception_parser.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e696e12a58740751629673f5093bebeb2f74f686fd05404e6ef33be59a5e411e` |
| ` M` | `tests/schemas/test_failure_collector.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `09f873ea91ce1771b336b9bb6a17f77cf2adea0eae42e8655cba64f8a1a0e1fe` |
| ` M` | `tests/schemas/test_fields.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `14a0aa5621cad42e7d07bb36ef40fe66bea4c3e79d56ed631dbe403c1d588e72` |
| ` M` | `tests/schemas/test_instance_validation.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `c1d5c71dc010783929943cc62598892c6d60af51f296e50c61067afa78bb9450` |
| ` M` | `tests/schemas/test_metadata.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `86d1e84f6679633b9b19bd5465d8cd312e01d2295d6256ef1bdee6aea5b29608` |
| ` M` | `tests/schemas/test_nested_annotations.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `00e2a69b18b53b041fc87a0fedc5dfdc900062c571652116fce73fb456ffd1b4` |
| ` M` | `tests/schemas/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ca782dde264ecacef3ce8eb8bd7f7892e4c6987b2b9c8382be2f88e788bab97b` |
| ` M` | `tests/schemas/test_plan_capacity.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `919f938fa2f1f9b0ba995a6622cc0f468370f7d56b23ca33dea791c683ddaedc` |
| ` M` | `tests/schemas/test_rule.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `647a1f4a871a9f5d21e2372dce624604917e870ef876e1f378f119f6c658d498` |
| ` M` | `tests/schemas/test_rules_executor.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2267855aafb62844e6933e6ae09fbb0a8deb5b169695df6d1b52f3ad0b469d7e` |
| ` M` | `tests/schemas/test_rules_import_policy.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `ccf56e395d04610f65bf57e25386610f59a120070505cce61e57c178e41b44d9` |
| `??` | `tests/schemas/test_rules_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `70b510ea9746a57a9e4e241ea4d237f2d9aae59671d982332ff277553b1bfce4` |
| ` M` | `tests/schemas/test_schema.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `8c0fe8c075d68385374bb637ec1ad3b2b02f4f74283d443af31ce3fe0fd9cba3` |
| ` M` | `tests/schemas/test_validator.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `accc0808865cad0092a229b0a1fac7f53c4f0e69f2c20971b162e0c85469bf79` |

</details>

<details>

<summary>tests/session — 15 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/session/contracts/test_session.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5498e675518ddd71789f93a0da8faf106773dc3f9a6210dcd168b93fb526d32b` |
| ` M` | `tests/session/contracts/test_store.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c5f044b0eeb4c6b898f9ca618def7181fcfd4622ea9768d62f110ff9c34e8694` |
| ` M` | `tests/session/entities/test_record.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `eb14996845455323418f21ade5a80e1cb44732345d1377a464995564ba91cf5b` |
| ` M` | `tests/session/stores/test_cache.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `7c9c6cec3bf45cb54ec009723210ca500f3bead4edf82f82ac67178813b4272e` |
| ` M` | `tests/session/stores/test_database.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `16a48bc677aab709f4a76b6b2d4edb50cfb86a95c4e2d913a74457763fba59c6` |
| ` M` | `tests/session/stores/test_file.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `bb614230bb7c79cb413e7a67ac08d82838e4c095ed39136b3ee769be83e24062` |
| ` M` | `tests/session/stores/test_memory.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e29a4fa76d9aea257279eed45b298c449d3a09cdc6210a733cf1dca2a92b5b62` |
| `??` | `tests/session/stores/test_store_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `e0361196cbafc99e108f19e78ddf7683c68b841451e7da62cd56320dce494176` |
| ` M` | `tests/session/test_exceptions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `45faf78cfbeca33dd6d376b9e60abe103fd6c1cfc3677078cff6342a461cb43f` |
| ` M` | `tests/session/test_flash.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c7ce4e0a55d56bd84a79bbf828dbcdccdfb09600700111307a49c882a869cfc2` |
| `??` | `tests/session/test_flash_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `cfacf2d66d93254827d43434fd698172d73e5bb929b5df8b0555cc070e7b67b6` |
| ` M` | `tests/session/test_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `b5700fff5473efdb91d237d752a1cbadb6972966c8fcba5601a3481a38bce8b3` |
| `??` | `tests/session/test_manager_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `ac81e0f63b1c6947cf4c530a4df89bf5782a2ac651be671c678f8bf9c5740558` |
| ` M` | `tests/session/test_renewal.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `10eb9499d11aeaf2527e02958cda8fb83de28f35b34a1e2d0a82bfacc02ff807` |
| ` M` | `tests/session/test_session.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `4da8921f7081a326197f17356a62385a7c9c4d6ba8f9250c51dbd0f380d75738` |

</details>

<details>

<summary>tests/storage — 23 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/storage/drivers/test_azure.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `103fb0af448a4fc394557c5c18dee896e64618ab687c80db80a01b8c87247697` |
| ` M` | `tests/storage/drivers/test_azure_failure_observation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `4289badc743a6133da0eed96d7aebc0ecb3994fe88665942bc07ad0b277bc246` |
| ` M` | `tests/storage/drivers/test_functions.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `85b97cdec69f79a5a540ff7053799e6c4ca95f85f1469fb94b2865963f7a2d9e` |
| ` M` | `tests/storage/drivers/test_gcs.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `1f65eea1e3678b04637cb040da983c32aba237973e543df1ae497add7696c287` |
| ` M` | `tests/storage/drivers/test_local.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e92ec041cd34c66fa3b53ef4bbc0ae66c5b8e8cdc75d5f12d9df5d09b7aa70ed` |
| ` M` | `tests/storage/drivers/test_memory.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `70f1e217a86f6270b7b6101f2498a4102cfb1cc27f4ca4a7723f425579b709d8` |
| `??` | `tests/storage/drivers/test_remote_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `e37d29ba6d5aae9a6c85cbb3f23c7b82622335e91d4b7845c7c4944f46cd3f4f` |
| ` M` | `tests/storage/drivers/test_s3.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9b8c63594b5704f782dc79fc6784e4fff2ce14f383a5ce144ff8bc497552d48c` |
| `??` | `tests/storage/test_api_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `3f718068e69ab50649edc9331c0a250ea9a3ea80cd60f24e1fe04a9dcb63bbd9` |
| ` M` | `tests/storage/test_buffering.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `73f7a56261734a23a1b332e6aff91cbff167d750b63fc84911a5b5d55b23dc5c` |
| ` M` | `tests/storage/test_directory.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `9198dff6429040268c6459a2f5e8a34a20638fc23adaeb1542339ddf4f100b7d` |
| ` M` | `tests/storage/test_disk.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5a73a368058f852bd6dc41cfe672cc3b1b073003c5d4d4d1babba891641d1e95` |
| ` M` | `tests/storage/test_exceptions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `79b8b680ab45f6f74e5d4f2c2777ceba1148179d2417eb0e8fbb53dd1c9fecc6` |
| ` M` | `tests/storage/test_file.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5a20b557435a4bb5fc7fc0a8c5afebc934397ab742b0e185cbcc0fdc6c39fa2c` |
| ` M` | `tests/storage/test_import_policy.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2f8fdf70c6da29b02fe34ea32342f5279dff0ec6d2a95dd3486f7d13f7613497` |
| `??` | `tests/storage/test_local_edges.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `6e0a2a25bc8996e7e0bffaf115225f9d9aeda9ae44e85e49ef503a0dd19485a3` |
| ` M` | `tests/storage/test_manager.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e15e27dac023111777b339d695bdd406c4750bcf0aa893840e40dafcacfdcdad` |
| ` M` | `tests/storage/test_package.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e29d4c06fc46f63543d450689649d5caf40f17865ab3610b80c984d6d6255e93` |
| ` M` | `tests/storage/test_paths.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `5d236589159cb7b9ce033d11857aed9d34a3360a4bd5e404911c6fcef9616617` |
| ` M` | `tests/storage/test_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `28e146b9eed632e4aef8abce88f8fd90cd3e4f298f806fdbde67eb92dc320eb7` |
| `??` | `tests/storage/test_resource_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `e47b9f6d76d72301df5ce2a5c8031e3bffc94ee1df2de6b91c85d05e12f8e3e1` |
| ` M` | `tests/storage/test_stream.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `47648fa802f45cad1db4d90d079605483ff8b510f79f43fd8985189f0cff6e69` |
| ` M` | `tests/storage/test_uploaded_file.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `28cea46168f063e01e43d18a1263d861a385085d9b0c955e12fdd389a3c0ffbb` |

</details>

<details>

<summary>tests/support — 37 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/support/entities/test_base_entity.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `309dae3dcf80aa48f0a6cdb98ef6b5f1697cfaff2b082feafb4269185d21bf43` |
| ` M` | `tests/support/facades/test_datetime.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3a7a59c4be559fb9db741ee4cb0f08b62d7d49a849b1284deff8751d4a7e2849` |
| ` M` | `tests/support/facades/test_debug.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `21df710803b40adcaad4ac09d0149158a0e6f8018cdda8a40590fe786619a266` |
| `??` | `tests/support/facades/test_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `ae8a1e35f14433b6f278d4af72fcfc5ce86c4d22d7846a56e7c4c28b68de7b9d` |
| ` M` | `tests/support/facades/test_router.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `1daecbc476be5ae9be9c76e407876b9a1ee07529a383ec6fffdc66ee6d36d141` |
| ` M` | `tests/support/failure_runtime.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `89e063a39ac11474872e84e0f9cd8248da7a0c6cc8c74cfb5c203756190bacc6` |
| ` M` | `tests/support/formatter/test_serializer.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `59c85bf66ebfd1b0e84f2126404f526b0a7eec77f7f37dd657d21bfbaff3de8a` |
| ` M` | `tests/support/inspirational/contracts/test_inspire.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `530da39d478eae9af8c7171ef5c0bb28f01494e4c9cd3aab7dfb4443fcd08c5e` |
| ` M` | `tests/support/inspirational/test_inspire.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `b434875d8e639c403f91d2d9364ec952dd96cb2474d49659c3907ca04f85cc53` |
| ` M` | `tests/support/inspirational/test_quotes.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `39688bfcc5a7160debd7d43bf208a672fbde9b06dce9a163de431f4f87b15563` |
| `??` | `tests/support/inspirational/test_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `5add28fe9575e3fb87beb6e834dcf398228f3b34b75f8fdae150f110a8231d37` |
| ` M` | `tests/support/patterns/test_final.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `cc0d1a623d9229baed4a0aa26f2f8b2b8484f5005f189def5f9487a9e6a71cec` |
| ` M` | `tests/support/patterns/test_singleton.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `20a18a02ac959edd20970fc22720c81b0fad163cce72c9f1d759772a86b4e650` |
| ` M` | `tests/support/performance/test_counter.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `876bfe8b8196a45dfcb002106aab0d57c5a93121877e17574cc84342d3eec0bd` |
| ` M` | `tests/support/structures/test_freezer.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5bd5192ecfe2602e4cd83019eb7924e6f58b2ea4a7516754ec4e00e27a9b4fbc` |
| ` M` | `tests/support/system/test_workers.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `877186c86db735fad98e475de489b52ea8dcabf515b43ba993012b712845d301` |
| `??` | `tests/support/test_collection_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `9898b31617ebeda229b18d5487e3a862a962f5c9a9e59ad2ddd7146e7a7f2f76` |
| ` M` | `tests/support/test_concurrency.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `baa13f368ebef0df04206ec79bf78c7b6c8019760b9b4b3e9284421a19bc525f` |
| ` M` | `tests/support/test_failure_cancellation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `68cb4586f0d04ecbae28c18acf7d31adb32bd038c99997b5d91d15ce960cebf0` |
| `??` | `tests/support/test_freezer_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `5cd450915b7a999bd766f0e80b4a8eea218be0b0a3eb85ad9e4c781ffc1d3f41` |
| ` M` | `tests/support/test_recovered_failures.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `57f1321927e98dab0903d20cec61089c4b8cc8b836be01fb12d01fbc7cf3bd8e` |
| `??` | `tests/support/test_runtime_annotations.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `5aa136e18f46c93d19e1990a1364d96b02003bccb752cd866fd116ea4b3caa41` |
| `??` | `tests/support/test_utility_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `d10efaabbf05ca8031fc9358ca4431dc3b23d606d8cbb9770d1eb1772ae57ab9` |
| ` M` | `tests/support/types/test_basics.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `87a1db5664913694cf2063eed69c90b8dbe14f67bef305f4c939d58d8c4e6aa1` |
| ` M` | `tests/support/types/test_case.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `49e062366607be8a8f3196d79334d3d5d51318a401f98c456c741f2b6d381128` |
| ` M` | `tests/support/types/test_collection.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e3c17eea0af09f6f85ecabc364a3ba693797cbe98c58f11d66d1636a4e73f0e5` |
| ` M` | `tests/support/types/test_conditionals.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3c69c447f464d4cdf988d2e081fa13dd2c9cf4cf8f9a7f459537fe1efa9e77d5` |
| ` M` | `tests/support/types/test_dot_dict.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `cedeb4ec5349603ed5c01615ef9adfafc5003dd7a2f43003ec1a820dc258b6f1` |
| ` M` | `tests/support/types/test_encoding.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `d6c8fd118dae2d4c55934a196a41a756c2a69a415b4d936655341bad7a6594b5` |
| ` M` | `tests/support/types/test_manipulation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `cf85d8477ab17505ae1977d7be0894d7e95391babdf509baa68cec0823857c28` |
| ` M` | `tests/support/types/test_plural.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `ab700e11a1ae23f457cbc98b00aabeddc9a1b471da05c58d5ce5980ce6b00d63` |
| ` M` | `tests/support/types/test_sentinel.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `e42f96e6ee3a117e9c0c924d39400812c8f79b25ee85053ca26a439a72bf89b7` |
| ` M` | `tests/support/types/test_std.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `31f1b5618877f6a7a71e9ea3d5df10cd90772809ba02319b8eda41bb86eff3ba` |
| `??` | `tests/support/types/test_stringable_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `cddd25da4ed7e288952c27b7e12d6e133241daa56a25ce56d981a33d5fdbb440` |
| `??` | `tests/support/types/test_type_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `5b19d9204b645704cab78d1bbe192faa9310f4fd8aca6ae3b285cd24c9e0674f` |
| ` M` | `tests/support/types/test_unique_indexing.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4db322d9a0ffe03f7d89a8b93573544892db619fb246a666497de8dfd8e3c931` |
| ` M` | `tests/support/types/test_validation.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `25e13a71b848a9b27e5546c52fa981823582b0335f5487b81b3a19498686b63b` |

</details>

<details>

<summary>tests/test — 12 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/test/cases/test_case.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `b926ff8261910e63adab7b2d2b180420dfeab91200cf20f472d5097ae25c9da8` |
| ` M` | `tests/test/clients/test_mcp.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c2d003b8c94072936fe05847f1581c90141349b5603e76ebfdeec322ff483933` |
| ` M` | `tests/test/contracts/test_engine.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `4d49b37472e93265cff6b0726d74f52ca81aae365e14a777b165fc5c158f869d` |
| ` M` | `tests/test/core/test_engine.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `af01ebcda7f953c9c883cb5f686dce08ab354cb526ec2e0a74bc5e286b096401` |
| ` M` | `tests/test/entities/test_result.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c0db3339ffb656de574806609720dc078e555e025b3e373df02927c53ef6e2e8` |
| ` M` | `tests/test/enums/test_status.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `68ac79105ecd4a180c63631d5a962ece4ede458d83e4e1e07e0b9a89bc8e484f` |
| ` M` | `tests/test/executors/test_result_protocols.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `82037819d6df5274490257e83526f1400ebc169d9d63ffb9b830f74a84d4262c` |
| ` M` | `tests/test/executors/test_results.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `95ebc6ad99aed5b11140ff46ca4a3b1b121e1867b2e71a9067ce0b4278277512` |
| ` M` | `tests/test/executors/test_runner.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `260cf1d9ea522db76a2f7c7f687a17fa59b6cf3da6436286ceed737fa598356b` |
| ` M` | `tests/test/test_ci_runner.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `7348ff31dac7c24c4fc3ea91a3e91a24c288dea0e7a18c6127370e0735563f58` |
| ` M` | `tests/test/test_package.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `b83f44c9293c1e17fbffe08a43e5b1ce1a35d55c64fe6629927f6d7937eb0885` |
| ` M` | `tests/test/test_provider.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `cae15af3068343d48e78a371d7c80a08709f8f73e40aad23482468bef1ad7c21` |

</details>

<details>

<summary>tests/view — 15 rutas</summary>

| XY | Ruta relativa a la raíz | Justificación / clasificación | SHA-256 del working tree |
|---|---|---|---|
| ` M` | `tests/view/test_cache.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `b95101a9ca8fef42d5fee2b271f2b855d5f6b172ac0deee73d9d1cb455eeebae` |
| ` M` | `tests/view/test_engine.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `31059d154c26981689f0e8df12f05643ba5bd28671b9203f0264ef49fc4c0b66` |
| `??` | `tests/view/test_engine_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `7fdb84831f37a0a1409a3754f964a38629698d923b870f6a3529ddea365759cb` |
| ` M` | `tests/view/test_environment.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `d79c2f48213db96259c5e52e4c91efc49c22d2cbb5508a7c041edb55f9b91a87` |
| ` M` | `tests/view/test_exceptions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `3ed7a3c212bb30b33e39aa9973e4be0b118b4a7fc8a47205fb5b6c234f7689eb` |
| ` M` | `tests/view/test_extensions.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `5c5f01d03dc8639f87d924d84e40f293f53135f862418eb66422550da26ed268` |
| ` M` | `tests/view/test_factory.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `74d405c3553e8ae6561dbdec645383de809e94fbca8c77041deff4ee95da29e3` |
| ` M` | `tests/view/test_failure_observation.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `ff54a384cd2fd947d8f6acdeb62d79a30e688010b6abdfd2b640bfb60c74a8f6` |
| ` M` | `tests/view/test_filters.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2371ce6642aac9f9b45fd59fa24c6c4f069d905b170984d79a12eced7ed75dd2` |
| `??` | `tests/view/test_global_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `9b62b36c0b002b18ff9f8806124507bff48c89ec6f000d2369dda4db6afaabf2` |
| ` M` | `tests/view/test_globals.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `bc0c15f4ba9769086ff1ce09b6fe4ebefec1a1e294e2e31d02d82aaeb6418730` |
| ` M` | `tests/view/test_loading_workers.py` | Docstrings, comentarios y/o formato: AST sin expresiones documentales igual a HEAD. | `e397a6a6df5443395a4b1c791b61d0dc481c8bc1f2bd2b1af9ab97a6edecd27e` |
| ` M` | `tests/view/test_pending.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `2f6472994ca9db1223a2345147f0993e312d7a341bd77af4c937dd01be658b70` |
| ` M` | `tests/view/test_provider.py` | Pruebas/fixtures: regresiones, consolidación equivalente, aislamiento o anotaciones; ver §4. | `c7c2cd864f4cc53bde901f1947db5a526f9782f33c8782879ad1d83b08835e86` |
| `??` | `tests/view/test_render_regressions.py` | Nueva regresión durable; conservar escenarios y fixtures descritos en §4. | `cfa4ca3f161b7e747e1c1b4f271ef12d9da5bcee7025a13b29d32348060ab69c` |

</details>

### 12.3 Salida documental generada, enumeración completa

Justificación común de todas estas filas: salida de generación de API/documentación existente en el índice. Preservarla; su correspondencia con las últimas fuentes y el build final siguen pendientes. Los cambios se producen con DOCS.ps1, no mediante edición manual de cada HTML.

<details>

<summary>docs/ — 2243 rutas generadas</summary>

| XY | Ruta relativa a la raíz | SHA-256 del working tree |
|---|---|---|
| `M ` | `docs/all-documents.html` | `0ca3ea119b1c29e9a668d4a57a5f90c0548cdee182cfda543af83743ab76ad36` |
| `M ` | `docs/apidocs-help.html` | `5250c8b9a0aae1c00e66fac7dc213cf57985689dcca9f23df76c2bc244b34097` |
| `M ` | `docs/classIndex.html` | `f477a83c4d978d96969af7f0d16551a08a917a9b3c149da6bbc7677f27edcf09` |
| `M ` | `docs/fullsearchindex.json` | `3a2ac928ed125726de3f6eb697be21d49a508dbfd6134aae366fee7dd167b875` |
| `M ` | `docs/index.html` | `f30f0ba373a239c21f8f934069bb3eaeb3012b78bb98fae34324cc8a6da12822` |
| `M ` | `docs/moduleIndex.html` | `77a00d88eab31b56a51867a78788cf6cd8dcba12b4ca1054f626d77b233bcf35` |
| `M ` | `docs/nameIndex.html` | `dfb6d26ddc6405cb55acfbc5e3686af1999c82fb8bbae2daa5379ed93524aef0` |
| `M ` | `docs/objects.inv` | `5b4684e1081605e58835027ba86c21896ce2a04b515b0b17198f47e081e05451` |
| `M ` | `docs/orionis.Application.html` | `5bcc625704e11cec1be559bdf1f582214802d5f8a14cc3315a10c9e6db789174` |
| `M ` | `docs/orionis.IApplication.html` | `70ba6a4584de5aef01cf62c6677d1cfe40fbc7442c558310e5eb1a819c61ef01` |
| `M ` | `docs/orionis._exports.html` | `00162a996b6a8219e25a9c7bead4a74b2a4033a5b2e0230d831714a591eafc0e` |
| `M ` | `docs/orionis.aio.html` | `15f38160bab828798e29f5de11d0ab7c0e50fe323dafb527e399317b9827e0a4` |
| `M ` | `docs/orionis.aio.loop.html` | `e2e6b4c02f793d3c3e221c47c4ec67e823fc5565328b61b8bb7bbaaa1a930d0b` |
| `M ` | `docs/orionis.aio.loop.module.html` | `0f44c7188370cf5264ef2e7a6e2a4f19d666d454ebb7a98ce5b149d2fe47ed76` |
| `M ` | `docs/orionis.auth.AuthConfigurationException.html` | `e3079a04dc874273bd2669c1b7ab38cbe295aab574afea93d3dcfcf8bdab826c` |
| `M ` | `docs/orionis.auth.AuthException.html` | `03edf72253a60b84b9505791087aab652097a7a6905d8b10a6c198f4ae40d828` |
| `M ` | `docs/orionis.auth.AuthenticationException.html` | `99a058b69911967d3c0b14707b85747e4d369387d9b756a5758cb259f37ca016` |
| `M ` | `docs/orionis.auth.AuthorizationException.html` | `22e827342e59e48caa001e2aadfd39e431b402febde7bffa56357a1d4eba4c2d` |
| `M ` | `docs/orionis.auth.GuardNotFoundException.html` | `170bead4d535e289d49b5d6720300ad0891e2418ed7d5258b6c15108e648d47f` |
| `M ` | `docs/orionis.auth.IdentityProviderException.html` | `a07b40d0c74d7f350a678f3c077833aa0d86b8324703a0b33e83351889cfa93f` |
| `M ` | `docs/orionis.auth.PolicyNotFoundException.html` | `a953336f2fef74c4276dc69c67ed23bb61f2e5143b039847864c9d798c6753df` |
| `M ` | `docs/orionis.auth.TokenException.html` | `3002ccb365784c9fe249a22338f8001b4d5129c779d34faf4a5823ffe5aed2f3` |
| `M ` | `docs/orionis.auth.authorization.AuthorizationSnapshot.html` | `0f1876a5a1ac2485d6679c35125bb88fd723e10b781d95e9aaf7467971cd6d5b` |
| `M ` | `docs/orionis.auth.authorization.PolicyRegistry.html` | `f989c722b71cfb5577f44c836b3d9c222e0595cf1ee6298c6fedbbfb2647d737` |
| `M ` | `docs/orionis.auth.authorization.authorizer.Authorizer.html` | `5c1f321ec334a659f7e2b7cfb631bb77c310d4392db709b61cbac0e43d40edad` |
| `M ` | `docs/orionis.auth.authorization.authorizer.html` | `96ee7c448001260fd584ffcb8dff51f3e9aa11c63bc9108e0c01518ede659ef6` |
| `M ` | `docs/orionis.auth.authorization.html` | `ba63150175838bca93a7611e0ebd895a24a4ef9e9a2e48ee79558fdfa2d538da` |
| `M ` | `docs/orionis.auth.authorization.policy.html` | `14fd9e860680539f18e2448ce00f1833ae7f7496ae7d4798c5e50a456b185c4d` |
| `M ` | `docs/orionis.auth.authorization.policy.module.html` | `61d1720e452d9f1a6a8f852597d007f465abae02b89040318dd199d62fa0d491` |
| `M ` | `docs/orionis.auth.authorization.registrar.PermissionRegistrar.html` | `1f61f84fb5f47c0ce48c797ba7bb92a63d6927e5c8e62ce17497fb5dff84d0b3` |
| `M ` | `docs/orionis.auth.authorization.registrar.html` | `0bd0755417db2c90ba681a95d7c3fc83c080f3ad5ad09ac0b2f1dd5e2738d3c3` |
| `M ` | `docs/orionis.auth.authorization.registry.html` | `759127a88185397dcce38780cb9f96f6ce690504b6eff74f2ec62f9b99a2799a` |
| `M ` | `docs/orionis.auth.authorization.repository.DatabasePermissionRepository.html` | `4607b49769df78d10821cef147b9fce115158ee01334ce36ebbcbd480f220b73` |
| `M ` | `docs/orionis.auth.authorization.repository.html` | `4c9a21e1b563214799b41bfc5fb3da261f049849e14f2e3266c66bc5c886a477` |
| `M ` | `docs/orionis.auth.authorization.schema.html` | `dd40ecc8a2ac95b899d6e82b5203bd8ce003c4b89b0d607454952513aecc6b01` |
| `M ` | `docs/orionis.auth.authorization.snapshot.html` | `35340599509583fa286ba7b50cccee152338f260bb29409758f6c786ebd580f7` |
| `M ` | `docs/orionis.auth.concerns.MustVerifyEmail.html` | `e73914e787e6eeecdccadea357e55522ea0c6e32fb665667a1168b0900949470` |
| `M ` | `docs/orionis.auth.concerns.authenticatable.html` | `4a5b5cdeb356d5787a984a97fe70408a5e76cdb3ec7351d76e5e14aaa5a0cef3` |
| `M ` | `docs/orionis.auth.concerns.authenticatable.module.html` | `85afabd575344444244162cde4b2991dfe90e2f987bb78af324ab54c0125aca8` |
| `M ` | `docs/orionis.auth.concerns.authorizable.html` | `3c51ba2563274604dc3645a683951b8d8cf0839a8f024778147c2dba2a4c9ec1` |
| `M ` | `docs/orionis.auth.concerns.authorizable.module.html` | `f0cd81ca4993fee904fb137d5a435c2c1c9e379d3037deac67ea312a344de0a1` |
| `M ` | `docs/orionis.auth.concerns.functions.html` | `bd35cf529e810acaa7a6ec3dc03ee88264ccc2b15d70d3f95c39f15da2e749ce` |
| `M ` | `docs/orionis.auth.concerns.html` | `2758114984c61530406041c8dee8df327b72a08212849103ee6dd6f33e233d47` |
| `M ` | `docs/orionis.auth.concerns.must_verify_email.html` | `118d09a987f9203aec9b3437e4a6745fc8873f6a59937f001347762cacb1880a` |
| `M ` | `docs/orionis.auth.context.AuthenticationContext.html` | `82266f21280d7c546c4cb23f79ae42ed54f6fe277c31a7f9a345dda471a877a0` |
| `M ` | `docs/orionis.auth.context.context.html` | `4ad944ee55a78608044454a02198fadcad01b8001d404188362bb577aa41b181` |
| `M ` | `docs/orionis.auth.context.functions.html` | `e6272c5d12477376670eb2811bc60ab7fd80f0b2ad31086c701afdf5b6c1a9fb` |
| `M ` | `docs/orionis.auth.context.html` | `54c91ad7a786d174e38c0a8579d8e7e35805d01f4b592e62ae9314093f8af486` |
| `M ` | `docs/orionis.auth.contracts.IAccessTokenRepository.html` | `756572fa52560730d59a84facb9783ca4ab253db34adc5c459c7ac7c833e8e63` |
| `M ` | `docs/orionis.auth.contracts.IAuthManager.html` | `bcbbeb8ed7f914805e89da7f2f482990c032bdfca087dab22da06b7d0337c59f` |
| `M ` | `docs/orionis.auth.contracts.IAuthenticatable.html` | `482477aee9ed2952065b9194463f42c2dea55f05f19337e54977c8a9e677a6a3` |
| `M ` | `docs/orionis.auth.contracts.IAuthenticationContext.html` | `23215b4c24200ecdd644c2aa8e2ebb01e380713cba19cb74109f5b1ab6b237cd` |
| `M ` | `docs/orionis.auth.contracts.IAuthorizable.html` | `8ce070e4456c7f61d96a88eb4c52d8adecb3374770ae3c2b6b06a33d73b5bc82` |
| `M ` | `docs/orionis.auth.contracts.IAuthorizationSnapshot.html` | `b930611d70eee6bb8390816dcc7ba4d6eb269c5c9d17449b31762973681a4b7b` |
| `M ` | `docs/orionis.auth.contracts.IAuthorizer.html` | `53b8805da82b03cdbce27fe49f4208e33014098b7c41f67dc2edaa4080821cc8` |
| `M ` | `docs/orionis.auth.contracts.IGuard.html` | `c8c861e58f77b45d200fbcb7f7f3ea382e830fc25151b6f938831736c81c78ee` |
| `M ` | `docs/orionis.auth.contracts.IIdentityProvider.html` | `aa7363a2fe7ed74df2d3ca431bcee273f41dc130ab7fa0661e21baba8c4f1ab0` |
| `M ` | `docs/orionis.auth.contracts.IPermissionRepository.html` | `b844d45fed81c787a97e284253dcd1bd042606da73724488f5caef6944c1f461` |
| `M ` | `docs/orionis.auth.contracts.IPolicy.html` | `999edf70c5320d059d5f5aec16b12b219aa4e17086c1d96476de857517013b3e` |
| `M ` | `docs/orionis.auth.contracts.ISessionGuard.html` | `dc328de343c7a736de812a5ad6e375ea84937a378cb622f215ad91d957d5e178` |
| `M ` | `docs/orionis.auth.contracts.authenticatable.html` | `b0737fe9b68269202ae33e03809765d2b267c4ec5b4a89bd3fe9106de1cff3ec` |
| `M ` | `docs/orionis.auth.contracts.authorizable.html` | `d7958a79f95cbdda01f05fb09052ffbfbd5cd504cf7a89724f9b2753ff473732` |
| `M ` | `docs/orionis.auth.contracts.authorizer.html` | `a640620722dc62cf71dd072d706be3b8cc3d02d032790ebd6905667d2c23bdd9` |
| `M ` | `docs/orionis.auth.contracts.context.html` | `55ab8d4c4186cde3eb1b0feea6dce819a6dbfe8c4baf427a7cfbb6256460006d` |
| `M ` | `docs/orionis.auth.contracts.guard.html` | `9f4f074a9d69969db87b15f177eb40332f286a5fb75ca4a0389ed4e1fd7f43aa` |
| `M ` | `docs/orionis.auth.contracts.html` | `1e3139de8fb351ef66f26144688b566a5a6fd6adad754d77db0cfc9682df5cba` |
| `M ` | `docs/orionis.auth.contracts.identity_provider.html` | `674495ce8d77b9ce18372b6667044e6409f6e474f35955d6c60ed6ecf04b5f3e` |
| `M ` | `docs/orionis.auth.contracts.manager.html` | `d5d00b68341e2d9b5bac57cd73e5c17274a9421368249c0bf9c0849aeaeba59f` |
| `M ` | `docs/orionis.auth.contracts.permission_repository.html` | `a04b84dd7fb7b9bf73a27af462d5131a4f173e74092ef7396e3cd4ebe1bb0a0f` |
| `M ` | `docs/orionis.auth.contracts.policy.html` | `22073c7201acbf58010d6fcb9ba59303f80d8e986cc9643b7c564efc84f861a2` |
| `M ` | `docs/orionis.auth.contracts.session_guard.html` | `eacc33dcbac31433075d05f55a9611f942065da8aa4d24ee97be4d27769ac9d2` |
| `M ` | `docs/orionis.auth.contracts.snapshot.html` | `c50156d1435618b8a7bd45a32a6755adfc5277a6b5e6a812970547f91a201ec2` |
| `M ` | `docs/orionis.auth.contracts.token_repository.html` | `17b1a7073e2741024d342cf8f16f1b1208a2147cc3936d6f42de285beb1424eb` |
| `M ` | `docs/orionis.auth.entities.AccessToken.html` | `be21bb71c4e498ab7bc3c6848ffdb1bbbb04ae18adb874370f4f8ddf59d94f04` |
| `M ` | `docs/orionis.auth.entities.GuardResult.html` | `3921f624d3a8897c146c73a14f541873545ec93e13c85213c602e4aeb0d5090c` |
| `M ` | `docs/orionis.auth.entities.NewAccessToken.html` | `5c634500670b5d76f40162d9c37a1ac90c2ae62c33db27e7df2871cad6c691b1` |
| `M ` | `docs/orionis.auth.entities.access_token.html` | `2193c8546e9313dba556f85cf48498a8df84872063ddc6378c5b42d6c2e78d00` |
| `M ` | `docs/orionis.auth.entities.guard_result.html` | `c9d6291058f30e5fe35bff731b4c66be155c5767fc679bf828e02ef5d211943d` |
| `M ` | `docs/orionis.auth.entities.html` | `6a038d99440e12e7b022dce6b451d9ae987dfe2e3da927df88e3daea67d60281` |
| `M ` | `docs/orionis.auth.entities.new_access_token.html` | `7938104fa3f3b8ffa0fd9d71e7bf0512727e2839aec3ef0e858c2ef5960f9951` |
| `M ` | `docs/orionis.auth.exceptions.html` | `b5f96ca99fc13b81032b3e65330bcf9ff872608add4295637718fd064d8ddd54` |
| `M ` | `docs/orionis.auth.guards.SessionGuard.html` | `2a7b7362c9aa8ae99cfd7f82022e01a4dadda60ea07b0019dcc1ca8a303f36c5` |
| `M ` | `docs/orionis.auth.guards.TokenGuard.html` | `94bcea4f7ac3331b2f4df6d9748174093c74303122cb32ad0476c7ceaf76edac` |
| `M ` | `docs/orionis.auth.guards.html` | `ad1c940c4442f69824ed0e1c8157fa2882b1422c0450a8fa4b43e4000c6dccee` |
| `M ` | `docs/orionis.auth.guards.session_guard.html` | `b5c7bdfa009f0e6f068d87a71fccc1f7e2a9cba8f6c531bb956a1db5f6901bfe` |
| `M ` | `docs/orionis.auth.guards.token_guard.html` | `bea6d9d3a06631a8c0061b0c70b410a0c026c6adcab140a5629b4a114cf9cde3` |
| `M ` | `docs/orionis.auth.html` | `db1fa6f83f8e6d7e96fb852eaca89764569a4e63645a4dd1803c3b1b0e90b7aa` |
| `M ` | `docs/orionis.auth.identity.ModelIdentityProvider.html` | `f07b72b025a3938b39c52ba0baec9554d8ce1aa482676f6dc27e7d1e24f93e91` |
| `M ` | `docs/orionis.auth.identity.html` | `8ad27df3c25d6f76b04fbf813efb326fa61346f8654ddc732ff131d29134c4f3` |
| `M ` | `docs/orionis.auth.identity.provider.html` | `f56a9609f73523950f685595f562ad093068fe78f7300f1a33f19c8ef191f688` |
| `M ` | `docs/orionis.auth.manager.AuthManager.html` | `92d596d831c09bb67d26ddb206b2481224e4ea885b1d0dacf8b2d0c10af089bc` |
| `M ` | `docs/orionis.auth.manager.html` | `8a6e95451eaf6fc50be10c3fa9af7108e397c6e00a043f985ce1607c1815f69d` |
| `M ` | `docs/orionis.auth.middleware.AuthenticateMiddleware.html` | `8ceec731eb1579674c0e1c8fb46df1998173e049055faf5fec38caf7e3a77e0a` |
| `M ` | `docs/orionis.auth.middleware.AuthenticateSessionMiddleware.html` | `460ce81f7d8b4e6abd32aa9d11048e0cdfbdc6bb0a8253ff67bbaea6f9ac0cbc` |
| `M ` | `docs/orionis.auth.middleware.AuthenticateTokenMiddleware.html` | `8c3468f08e5d1cc37bd2d3bdac72df52821a3527a039126a88f665a11e1da1f0` |
| `M ` | `docs/orionis.auth.middleware.GuestMiddleware.html` | `27f80b683fa4c050d5206bedbc181ccf708cfa230f46876552e9de079358c231` |
| `M ` | `docs/orionis.auth.middleware.RequirePermissionMiddleware.html` | `6cf668d87b88ea96d3d88b0f383d3b817ef65341d8ed2c77c9e6281b99228e58` |
| `M ` | `docs/orionis.auth.middleware.RequirePolicyMiddleware.html` | `7eece4b4bbea53477f89fce00b77467d1a29596a658ec78ca99bdd85b50ff764` |
| `M ` | `docs/orionis.auth.middleware.RequireRoleMiddleware.html` | `99fe40ce4f4b3ff21641f25242ed27904d557a105bc10161ed14eaa122992782` |
| `M ` | `docs/orionis.auth.middleware.ResolveIdentityMiddleware.html` | `5cb4974687162d1ce342611e2d02805e13259b3136e104630679633ecdc1f027` |
| `M ` | `docs/orionis.auth.middleware.ResolveSessionIdentityMiddleware.html` | `a0d0915766e263a341cf660ca06b939c1b5cf743866c95af4ca3731fb44ec3b9` |
| `M ` | `docs/orionis.auth.middleware.ResolveTokenIdentityMiddleware.html` | `f5470891393a7cf9c82845e73237d1d1c80f5886c820fe8c878035df2af2dfba` |
| `M ` | `docs/orionis.auth.middleware.authenticate.html` | `b97647478ba24b412ac77f2988e994c09d9d73809a3fffe37d7cab466a6fd720` |
| `M ` | `docs/orionis.auth.middleware.authorize.html` | `149781df3ed4a26cbaee728ac81bc1826ed1f47e7507c7178ac8fae8c9b75a4b` |
| `M ` | `docs/orionis.auth.middleware.guest.html` | `7756e92ad088fe7183495b72573663218f3626a845f351573b56c2834568a5ae` |
| `M ` | `docs/orionis.auth.middleware.html` | `a87d88ab57d93ea63f4df24a810167821b95ba6196a02c5d262bdf816bc5a9eb` |
| `M ` | `docs/orionis.auth.middleware.policy.html` | `77e482f8c1993cd32a55f65eed21a7058253f47258328c038f721e3457c6158a` |
| `M ` | `docs/orionis.auth.middleware.resolve_identity.html` | `00775e8a86c8c3222b8c78dc97054d456daf0ee9691d865189a3588eb88d9636` |
| `M ` | `docs/orionis.auth.passwords.broker.PasswordBroker.html` | `88427c2724fa5e676c20f275caec1db412cc04a38e1380deee4f7f085509c3a9` |
| `M ` | `docs/orionis.auth.passwords.broker._StalePassword.html` | `874719fa1614af09e499a17d25a19f79cfd9af0cae18d202a3bc9f8342d3fba9` |
| `M ` | `docs/orionis.auth.passwords.broker.html` | `571ce267093d4fe4d911b60c5bcba93c19fa037ab968e062f12a2b4785f176b8` |
| `M ` | `docs/orionis.auth.passwords.html` | `3dd94a800747643c9df57e063267f8011c14e900bc494d1f82ccbe766f8e3ae8` |
| `M ` | `docs/orionis.auth.passwords.schema.html` | `8ae532de3bab7d859de89448f8ab934852e799c03bdbb51b38560e93535093b4` |
| `M ` | `docs/orionis.auth.provider.AuthProvider.html` | `4a3522dd3c6b02b558606bfa644fcad723b48b6239b80699a65fdce24232fc5d` |
| `M ` | `docs/orionis.auth.provider.html` | `d4e6ba67bb7ea3f602225ba3a15d1e12a48ef014f7c878a9d30f9fbcbf0e684f` |
| `M ` | `docs/orionis.auth.remember.RememberMe.html` | `bbfec5900ced0e88a4c7e0975bd20f8515ba1b332a005d6814baf3af62f76305` |
| `M ` | `docs/orionis.auth.remember.html` | `0643fccd94c0a4fa91ddd30efc598237301d945e2a3f742b2132173c187411d1` |
| `M ` | `docs/orionis.auth.tokens.AccessTokenRepository.html` | `9a578dec054dad530eed0f386a38914913ecb1396ada291fb38ee19153bd1c6c` |
| `M ` | `docs/orionis.auth.tokens.functions.html` | `f1b29efcf745bc0b889eb5f71b294cfb7933e3e2edf8fec501046346ad8c16cf` |
| `M ` | `docs/orionis.auth.tokens.html` | `9fdc8eee19fbbbbcf422eb6e17f6122f9953ae95711bebea7564922a1a15c545` |
| `M ` | `docs/orionis.auth.tokens.lookup.html` | `26c21eb906c3731e7760bb4c4d8124ba2eb27f86d69c577a519fa11b8c955aab` |
| `M ` | `docs/orionis.auth.tokens.repository.html` | `48bb4f2dc801afec932ce421cff65f5406fccfd85a3938d2f1a456b3ca9105ce` |
| `M ` | `docs/orionis.auth.tokens.schema.html` | `7a0cdff51151f736ccfddb2d15fb6527f7072122324c1061e712a28141a5080e` |
| `M ` | `docs/orionis.background.BackgroundTask.html` | `76b0468799023dbe6589a6e530e905d63c3779dcb1bf80c57f1fd39d6d8e8085` |
| `M ` | `docs/orionis.background.BackgroundTasks.html` | `390d83a554d066ab262be260b36912dd075e92179f8b3f1b1d0140b764a098e1` |
| `M ` | `docs/orionis.background.contracts.html` | `2cfcb414df2f883b6bcfbf1fba190f9a0f3be9ac7ce311963de64ebe39f6da2f` |
| `M ` | `docs/orionis.background.contracts.task.IBackgroundTask.html` | `073a228eb56a2008f4e835a6077d3378654b3954dd722df055fc1bccbec8a097` |
| `M ` | `docs/orionis.background.contracts.task.html` | `32ce0e30655632563861f584acc9958d3db9c6d61defce979d92ea1fb4bf278c` |
| `M ` | `docs/orionis.background.html` | `ca36cd42c6ec7fe8c82bc643404083379a133fda0690c2f7bd8785cc9ec06048` |
| `M ` | `docs/orionis.background.task.html` | `fd8ac9cfba5e8f18727eefc946ef615644d1f1b96b29b9a4454b31656dc94d36` |
| `M ` | `docs/orionis.background.tasks.html` | `952781b44a65b9e9a0d4a8cf564ffae52e7dada8d6862d340476dea332c8615c` |
| `M ` | `docs/orionis.cache.CacheManager.html` | `eb7e2da4458c1eb5d895d909e09a2beacedce7d55ff1b713d9b40f828d191175` |
| `M ` | `docs/orionis.cache.CacheRepository.html` | `10b881830d7d6cf9206c1bd627e99cf280074fbe0a4cdfce8156f3135f440732` |
| `M ` | `docs/orionis.cache.FileBasedCache.html` | `8ae7242a02a53b5e39e1de14768de80ac4220e7f7c106d8745e605b7b97f0864` |
| `M ` | `docs/orionis.cache.cache_manager.html` | `fb2637fa818efb9b80a5293ff22ba18b63a59a0a7713441b791bb3f0dea4dd93` |
| `M ` | `docs/orionis.cache.contracts.ICacheManager.html` | `e4119e2e08995bde9dfca558e0c72145b675883f507fe0432c8a367fc0fdf64a` |
| `M ` | `docs/orionis.cache.contracts.ICacheRepository.html` | `a0970771d8b2c4ed2913093fddb37a4f315924fee9aa2f5edbddd244e47d22d6` |
| `M ` | `docs/orionis.cache.contracts.IFileBasedCache.html` | `d0bda065d9434faf19c655889654d4a83db173e1874f44eadb230e4d5492f59d` |
| `M ` | `docs/orionis.cache.contracts.cache_manager.html` | `27c732503d3d390f516d4c3d4b101257a6accfef1ed037f1906db51ccacb004c` |
| `M ` | `docs/orionis.cache.contracts.file_based_cache.html` | `fe27339aa146d6c867580708b80cc3d440e16ab89128396d8b7269b00143fbfd` |
| `M ` | `docs/orionis.cache.contracts.html` | `cfb1352edba9776dd56af4fa6a64443ff0441247c5c26404fdad8ca451b12e01` |
| `M ` | `docs/orionis.cache.contracts.repository.html` | `4089a3d422794d00f603425b3b301a77b5f8b7342978198495d0c73c286b64cd` |
| `M ` | `docs/orionis.cache.exceptions.CacheException.html` | `d1b65fea8fe8e1d5f413d0aa8204d47adcd91b824fc8e01a342d2e7a0caa70d1` |
| `M ` | `docs/orionis.cache.exceptions.CacheStoreException.html` | `3429a972a15572a6ea74ce667d9ea1b5c239543adc7d2b01625226169e4d9aba` |
| `M ` | `docs/orionis.cache.exceptions.html` | `530f181ccfa35085ef37e52dc7923541e5bb0c62b0f40fac0af72a68bc7b8c2f` |
| `M ` | `docs/orionis.cache.file_based_cache.html` | `bad1dad442c437c596d072c098a1c759aca232011d5284c68ac19fcbfa7f8a9d` |
| `M ` | `docs/orionis.cache.html` | `6b35a17bd19ad84847211f4b41a40931230a0ea5b7cb1d204a0f73b3b7cd01b6` |
| `M ` | `docs/orionis.cache.locks.coalescing.RedisResolverLease.html` | `a3fe5f625ffbbb00a8b9899115570b95b7d28ea9dc3313ce6ccd8bac6340ea38` |
| `M ` | `docs/orionis.cache.locks.coalescing.html` | `86ca58e66f2d27cd974db5b54728619e6d622af69e8b869e9b1251b20882056d` |
| `M ` | `docs/orionis.cache.locks.html` | `07a7068432980eb50977333eb597eef5c256fbc1f0a7af7b0e9bad06d7bb1ebe` |
| `M ` | `docs/orionis.cache.locks.lock.CacheLock.html` | `88455835c117ecf3db279a6b71f917fa5b7dc836930e013901c4b28d202b0054` |
| `M ` | `docs/orionis.cache.locks.lock.html` | `806216cdfee804194c1da1b965e569b7796d35b679726f02643b5319538b5534` |
| `M ` | `docs/orionis.cache.provider.CacheProvider.html` | `03f5b244bf53c50587d97a99930f35a75f9e4cf6d53de0abd907c98c85ad829c` |
| `M ` | `docs/orionis.cache.provider.html` | `3707c2bee0f41814562621ee1528a1f2d7b5f9a40987c76464296b3632b99b54` |
| `M ` | `docs/orionis.cache.repository._Flight.html` | `99c0247b4c76d4821f5b18cc3b2642fe0b86ff465a9a5d9e51be5bc7093f7e00` |
| `M ` | `docs/orionis.cache.repository.html` | `149a6d3b3537a9578d0c464474c78b3801316cff2b7402df569c530a848801b2` |
| `M ` | `docs/orionis.cache.serializer.Serializer.html` | `72f1ecee5bbd7dbecc5ed8597905df5c71acba305c95edee919271388a62587a` |
| `M ` | `docs/orionis.cache.serializer.html` | `6251daf5adfe9877579388bf12640f6139b8293a28b1fdb7822c0a8a3fc71bc6` |
| `M ` | `docs/orionis.cache.serializers.html` | `f4c6d83b7ed3cbd21397fb9819c38d9fbce6ba013663d11555ba82f617c17c54` |
| `M ` | `docs/orionis.cache.serializers.json.MsgspecSerializer.html` | `84c0755078b9007b865ab8cd2cd1c777b15cb3503cd40299cc69996988d14466` |
| `M ` | `docs/orionis.cache.serializers.json.html` | `58b352cedeed9045fa46cc9aa419c188b5e3aa74e95b379cf41698ea650d91cb` |
| `M ` | `docs/orionis.cache.stores.database.DatabaseCacheBackend.html` | `939bc1cc79a2d1b7da2a080c8cd672be724c6d7d8efccc0ed7be48d9cb4590a3` |
| `M ` | `docs/orionis.cache.stores.database.html` | `297750efaa082785efb383c0eb26a3e9bb32019feac1885d407ad27f280a248f` |
| `M ` | `docs/orionis.cache.stores.file.FileCacheBackend.html` | `20eb81407c03094d4b00d5da8e54699e9bb01d0d412970f85f87998bec1a3e4b` |
| `M ` | `docs/orionis.cache.stores.file.html` | `50ff8eaf2f5f935b91a5fff605ee44e4c881a2ca3defea86abe144a24824e167` |
| `M ` | `docs/orionis.cache.stores.html` | `e953e4e24c3e142dbaea4de7c48cbcfdb30f97dc72e125695be65aa06e8dbe40` |
| `M ` | `docs/orionis.cache.stores.memcached.html` | `8c1680cec9db797c27dc9ad0d12f4283e0877e2df87df875131c3ff85ca037c7` |
| `M ` | `docs/orionis.cache.stores.memory.html` | `d2777409d8d551fd629f5ab1aad2f1a1dae752782bab8b0fb4f6b031fe9283e1` |
| `M ` | `docs/orionis.cache.stores.redis.html` | `bb79c1e27115af39c399f75ef23aa9ee9500db82e7485110d7207355a4e7f950` |
| `M ` | `docs/orionis.console.Argument.html` | `b69f54f125bcc0d9a92fc449ff25c49e78efcff5126fa6b9938bf5edad8e2ff9` |
| `M ` | `docs/orionis.console.Console.html` | `044aa4101633b4a5b2b70d27f95839ff94dd6d1e5c62fc07eef1cae28eae06ac` |
| `M ` | `docs/orionis.console.Dumper.html` | `77343eb432bf04afd654ffafa8cb83ddfee9b52a9d3aee7646eed9fa5a1aaf40` |
| `M ` | `docs/orionis.console.ProgressBar.html` | `076097cc63d3bd7e97d8eb95633d0cab4ba5b474a7b740755d44ba5591b15aa6` |
| `M ` | `docs/orionis.console.args.argument.html` | `a6138d37fb30c4dd65a4dd60bf2bdc21f6674daefb8bf33c4f560dd6937572b8` |
| `M ` | `docs/orionis.console.args.html` | `82f3d3a4d9f7876ee673b4fccbf996a3d9aa86905d810b001dfe5a205850d1fb` |
| `M ` | `docs/orionis.console.base.BaseCommand.html` | `f87d09eff37fc60f156c044f5ba338f60c040bdb23bf4a4d72ce4542cfc49521` |
| `M ` | `docs/orionis.console.base.BaseScheduler.html` | `35765bc9b2c2ce5646969502e4dc09725feb2b835f2378af7c00224d13351dc5` |
| `M ` | `docs/orionis.console.base.BaseTaskListener.html` | `862389b70afa4c4dfb02b87a7872b94ea04dceaa8c04e49df474454ae945c2f1` |
| `M ` | `docs/orionis.console.base.command.html` | `62b1f0bc83661b59bc6ec9f237c8deba2b2f7a1cef97581b68d11e3e1cc02aa7` |
| `M ` | `docs/orionis.console.base.contracts.command.IBaseCommand.html` | `2100774fc41e78e2fab12f97589c6331a445049ebe3ae8f7efb50f81733ac9a1` |
| `M ` | `docs/orionis.console.base.contracts.command.html` | `bb7fb5a702259a377d5042affc3dbbef67e8c22701932874d50c9553567597ff` |
| `M ` | `docs/orionis.console.base.contracts.html` | `48e2054f76e79eee16d97e12cab2c28d74bbff55c190190b73e9ba52fab92f01` |
| `M ` | `docs/orionis.console.base.contracts.listener.IBaseTaskListener.html` | `8e7ad15ad34c3d4929c32fa9e185494baf9540740e1ea43791ca73192e9b6567` |
| `M ` | `docs/orionis.console.base.contracts.listener.html` | `be9098c4c2f074d9f500be6c41d0432050bfb7d23d552546075143d314abd95f` |
| `M ` | `docs/orionis.console.base.contracts.scheduler.IBaseScheduler.html` | `2c1b751bcca75f9c92b46f46085fe9316b1ab6d19183ebcc47851ec85b3f2e55` |
| `M ` | `docs/orionis.console.base.contracts.scheduler.html` | `af6f266fb71dfa8e8b37b02164f2036cd00e7edd093430633d67e4b8be013143` |
| `M ` | `docs/orionis.console.base.html` | `01c3c7f3d2daa6387043afb3236a6b0defd3e506d2d2b7b96c0c52b800955598` |
| `M ` | `docs/orionis.console.base.listener.html` | `15f6c7e506fe89f04d775be25664603fc1f753ba983d2e2d41abe5932d6fde7b` |
| `M ` | `docs/orionis.console.base.scheduler.html` | `1d8ddb9f61a7951b73c49a33a0cc244b866adde599c513cf11ac19c3e655231c` |
| `M ` | `docs/orionis.console.bootstrap.html` | `4f7e566217b267f10462995c1cfe3d8c02871da72d8364d4c172c3681743e6ab` |
| `M ` | `docs/orionis.console.cli.html` | `eec3913a32bb832ae24f6a90b7e6dd1e2eecfe4a036789cb7b967250ca96b794` |
| `M ` | `docs/orionis.console.commands.auth.html` | `bcf15f1481553ea2974ec52ce87a3f5c203dc93f1c032d9c893471262f788076` |
| `M ` | `docs/orionis.console.commands.auth.migrate.AuthMigrateCommand.html` | `58dd0b58183024c4344e88789f7aff10fdc31a8e33f3f8b5a5cff58ce1e8a43b` |
| `M ` | `docs/orionis.console.commands.auth.migrate.html` | `a3423392504e68d097b71ad7cf1393e3ceaaa2174f1c7190bd8527655f7860e8` |
| `M ` | `docs/orionis.console.commands.bootstrap._base.BootstrapCommand.html` | `04787994e464eecf45898a7def9e4a2311f169d183a82ee5c2d9871be8aaef98` |
| `M ` | `docs/orionis.console.commands.bootstrap._base.html` | `4a33e7a473578df7114052a0887e6c66fe89dcc83900e3f5be02c41f9e2af31e` |
| `M ` | `docs/orionis.console.commands.bootstrap._config.ConfigBootstrapper.html` | `0dc11de52cb9582f5606c1336b3f42a7d334e440ff21dd891c9b1b068bc3c0e6` |
| `M ` | `docs/orionis.console.commands.bootstrap._config.html` | `cd40153723b76569e23548b9e91ff9c56d772dd003bf6b9778f1cbd254961c66` |
| `M ` | `docs/orionis.console.commands.bootstrap._editor.BootstrapEditError.html` | `e2065896cc18a002cfbb4f97cdaaa91d93755a5c16f38ad8cad60476ddce5a9b` |
| `M ` | `docs/orionis.console.commands.bootstrap._editor.BootstrapEditor.html` | `560afe5dfb46ca51d903ec2425b9f776a0ad4bb3d7a6f25a6ffcc35170779210` |
| `M ` | `docs/orionis.console.commands.bootstrap._editor.html` | `787a1ecf7af48096a2a828a7e8684d3c75120f633f0a7af9676b34b3b5e87717` |
| `M ` | `docs/orionis.console.commands.bootstrap._paths.html` | `33868dd9d48f30cd7d1c31fc7710b8c19bfc329ceea83ed5962666a1168cea25` |
| `M ` | `docs/orionis.console.commands.bootstrap._service.Bootstrapper.html` | `ac6e3335e6b47974f2a0a367775bc76fc1c0621e1c705d0b35713e5eac290965` |
| `M ` | `docs/orionis.console.commands.bootstrap._service.html` | `8e48c9d80529b29dd6503d52b22d5ebd9c206fec119a7976ac61ea195a0c10e6` |
| `M ` | `docs/orionis.console.commands.bootstrap.config.BootstrapConfigCommand.html` | `3ed67de1a5f1fd1e76a56c83360eca1c04c1bad06c17033d38029134a46d6c6e` |
| `M ` | `docs/orionis.console.commands.bootstrap.config.html` | `5538e8c2b7ca2cf111df9819fb5570d9ea20dc86af20ddf791d0e02d2f2239ab` |
| `M ` | `docs/orionis.console.commands.bootstrap.html` | `b97c38163e62e108659a0f98bc4a7fe245f8158b0d8243cfaf240647bf9edf55` |
| `M ` | `docs/orionis.console.commands.bootstrap.lifespan.BootstrapLifespanCommand.html` | `1b426e530d35bcf81952f49c0599e5fbb220f433c43fe2e3cd41ba09d7dd3788` |
| `M ` | `docs/orionis.console.commands.bootstrap.lifespan.html` | `d2868ba81645d3424825c354829fec5da032743ac7f66686bbc0074633ad66dc` |
| `M ` | `docs/orionis.console.commands.bootstrap.routes.BootstrapAiCommand.html` | `f316fa2ad7b9a77ae141be186b33fcdbc729a40f16d845dd99337d5e9b4b8a46` |
| `M ` | `docs/orionis.console.commands.bootstrap.routes.BootstrapApiCommand.html` | `0f24f5b5441ca772fdf06ccf5a5fe808928769a7340aa39969abe8551ba1eb20` |
| `M ` | `docs/orionis.console.commands.bootstrap.routes.BootstrapConsoleCommand.html` | `0ef3040ac365d7185cc4e46130a7fc9dde94ddd46550ccef11b607b87562d4a6` |
| `M ` | `docs/orionis.console.commands.bootstrap.routes.BootstrapWebCommand.html` | `540fabb8edd67dfa3940be515b9ce5492351358e10507bfc0f22eb8a53600027` |
| `M ` | `docs/orionis.console.commands.bootstrap.routes.BootstrapWebsocketCommand.html` | `7f87d571334606f1b22ffe04f9f381ffff9d86eed95a619b8ec52bb444452366` |
| `M ` | `docs/orionis.console.commands.bootstrap.routes.html` | `42682ccf5886e14a1bc4242415b866a3abe79f1e3f6164db0fce9ebbde4aa375` |
| `M ` | `docs/orionis.console.commands.cache.html` | `d7d494277ee736ed7d17bd515d27d61e277f0b1e9e0ef316d1fa7e19016ab852` |
| `M ` | `docs/orionis.console.commands.cache.migrate.CacheMigrateCommand.html` | `9f182153bdfb06d30c4dacb93bfb16ac721c4a6d4150dc8ac5070f76d85856d5` |
| `M ` | `docs/orionis.console.commands.cache.migrate.html` | `f8b9447b8f64f240737fb3a8365e92f1f0caac1456eb2a0fd26353b482329168` |
| `M ` | `docs/orionis.console.commands.db._inspection.DatabaseInspector.html` | `17f2accae26090be79e7d6d0d83e8673e078b4a48fe0027c095c985e822048f9` |
| `M ` | `docs/orionis.console.commands.db._inspection.html` | `77a627841f77eb80bb79898eb90e05e897b09948cd09ef513615b3f56756cf23` |
| `M ` | `docs/orionis.console.commands.db.html` | `100cecffaea84744f59232b6f3ffc577b47f5d1ecdf88c45319de640bf34d833` |
| `M ` | `docs/orionis.console.commands.db.seed.DbSeedCommand.html` | `98de1c397fa9c67248d7825bbd7f74dd9fb27b95ceff5090fadf0180986028c6` |
| `M ` | `docs/orionis.console.commands.db.seed.html` | `86b99f2ce3ad52a1c4712add4a92cc3288c7c27887e0525684efcec881b0a1d5` |
| `M ` | `docs/orionis.console.commands.db.show.DbShowCommand.html` | `8889f84def125094b10531ef5dbb27aea2590d224e0570dcf76458a453b6f5b5` |
| `M ` | `docs/orionis.console.commands.db.show.html` | `121e9934b7b63dee85cb880982e25c9bb0e40eb4978baeb53dc54be5d6bac2b1` |
| `M ` | `docs/orionis.console.commands.db.table.DbTableCommand.html` | `b718ad994bbc83d4d5124731ee8fa888c79ce023b40f041251448938d34a362b` |
| `M ` | `docs/orionis.console.commands.db.table.html` | `a00f771bdd3a38e20072daa02f774d67a7f9663239b260a89826fa3138e3dd5e` |
| `M ` | `docs/orionis.console.commands.db.wipe.DatabaseWiper.html` | `6f323ce734de79b392482ed1863f585a5e7a0fe04d8bb20acf920c5ab15ef49f` |
| `M ` | `docs/orionis.console.commands.db.wipe.DbWipeCommand.html` | `fe97bed9fee65704efc87fed75015f5eddbb414dee0b9cd8d57844f6d1a7767c` |
| `M ` | `docs/orionis.console.commands.db.wipe.WipeResult.html` | `263b81618f9b7596406774da902abdb088286f38bc1ac99f1d66f15bccce4d10` |
| `M ` | `docs/orionis.console.commands.db.wipe.html` | `8fb1d0e623c43f00a266c036361ef0dc470e59535208f8d17a37d8bf1b45282c` |
| `M ` | `docs/orionis.console.commands.html` | `67c08f0ce02d23f752ac2ef14be551bdff13c70fad82b20b9389a884e52fb519` |
| `M ` | `docs/orionis.console.commands.make._base.MakeStubCommand.html` | `1f99e6c422d043e277dcb2701ca1714b58352ec7f56e60e5215827f8c8b0e2f9` |
| `M ` | `docs/orionis.console.commands.make._base.html` | `0eb8b578c200dc7fbfe4978e6298c4a449e3fbb5c63e0513ad9f90d924a7d5e2` |
| `M ` | `docs/orionis.console.commands.make.console.MakeConsoleCommand.html` | `5cfdb1f0315aa7de41a537817ad34537ebcbe26e9545947f31183be63b6a5241` |
| `M ` | `docs/orionis.console.commands.make.console.html` | `45d873e23ac078a486d66089b300a667da706fe19c41ee5ac583674658cf81d2` |
| `M ` | `docs/orionis.console.commands.make.console_listener.MakeConsoleListener.html` | `3a327e62388cc8f064c0eda5993c12965be415f351aa4a8d4be9be4452def4e7` |
| `M ` | `docs/orionis.console.commands.make.console_listener.html` | `a7e925f9bc309c441296310d1df004d954f0583e4acaacc4340d836877ef428c` |
| `M ` | `docs/orionis.console.commands.make.contract.MakeContract.html` | `c2a7c3950324806cb288d3f2ee2a8b5ba0032e4593c327e9b5ed7b25a3bc8133` |
| `M ` | `docs/orionis.console.commands.make.contract.html` | `2453e065241e90c9afc0a5450c6d78c190bf65450f661a0eee09964eae0e600f` |
| `M ` | `docs/orionis.console.commands.make.database_migration.MakeDatabaseMigration.html` | `0f380f91acef737acbf02ab61a8446e4be21cf947f6d0f2b523932887bd9c2ad` |
| `M ` | `docs/orionis.console.commands.make.database_migration.html` | `a9ee96cedc6d28daedf532bb5710a92dcac9516d4ce18f9aabbe9417ac3e51f7` |
| `M ` | `docs/orionis.console.commands.make.database_schema.MakeDatabaseSchema.html` | `ae6c7b2e601e27c6297da428ecc5ceba4b76711f21c24ec85c657b8d75400d7c` |
| `M ` | `docs/orionis.console.commands.make.database_schema.html` | `282c4ec5c237d57ba5ed455f01011bb32109ae6652da7fca0d2756342a2c40ca` |
| `M ` | `docs/orionis.console.commands.make.database_seeder.MakeDatabaseSeeder.html` | `eac656c5a039362f46c3dda1b1da66c38f88418565f5257f68e06716b606f8ef` |
| `M ` | `docs/orionis.console.commands.make.database_seeder.html` | `98b397d3f8fcf597053200f99dde3fbe4456f49b3d973b38d4476a1c77463485` |
| `M ` | `docs/orionis.console.commands.make.facade.MakeFacade.html` | `8438ab2368fe0e6774308df3389994aabbae9a2c46b49762875fdccd32f1fd15` |
| `M ` | `docs/orionis.console.commands.make.facade.html` | `6af3e5c70b317e936359874dd159526cbb927c8ebb0ef1ddbcbed22633f7a074` |
| `M ` | `docs/orionis.console.commands.make.factory.MakeFactory.html` | `147e4b79faa3662c9acd58dd7ccb7b20071e861c8564c9241c4b9c95ced61e0c` |
| `M ` | `docs/orionis.console.commands.make.factory.html` | `de4be2fb3a3d3917bb4949f9bcba0354b459edc3dd4597a224eb0e188ab426a2` |
| `M ` | `docs/orionis.console.commands.make.html` | `553d058053bf880955572b09a0e8310009cd3bac5e686b161fc0da5b76c071d8` |
| `M ` | `docs/orionis.console.commands.make.http_controller.MakeHttpController.html` | `631212cf354db8b7579a40de4549e1bae9213e17d9dd95973ffd346099b4b206` |
| `M ` | `docs/orionis.console.commands.make.http_controller.html` | `600094a970d9c3fdf9303870c49e60db432f5c6e61a907552a449addb9f8a48d` |
| `M ` | `docs/orionis.console.commands.make.http_middleware.MakeHttpMiddleware.html` | `52933f2c5f345ae5f4d993bf1ef4eed40da43b0c716d619bd013e643fdc63805` |
| `M ` | `docs/orionis.console.commands.make.http_middleware.html` | `8011bcd8993fbf50c79462253953fdb50f4a0d296a2b4d8276bc25b80e634f07` |
| `M ` | `docs/orionis.console.commands.make.http_schema.MakeHttpSchema.html` | `d3d7e9899190f63e8754e5235f4b3d9ff3f04e142a74685065bad379d85b6e02` |
| `M ` | `docs/orionis.console.commands.make.http_schema.html` | `e446044d585839faa7f751bdc0cbb457c6dfd490dbeffe6d5eea0ba58257913b` |
| `M ` | `docs/orionis.console.commands.make.http_schema_rule.MakeHttpSchemaRule.html` | `82507e37caef671604b31abf46520751641992dfa1b32cc74aa0dca8d613b819` |
| `M ` | `docs/orionis.console.commands.make.http_schema_rule.html` | `05a45fbb079b756b9695be62f2e5435566e621509d2817b2f7c749d1d054e132` |
| `M ` | `docs/orionis.console.commands.make.job.MakeJob.html` | `54d5cb7661f06864808af321a7d1e8c43f94dee8c73314af9edbaa33600eb7a3` |
| `M ` | `docs/orionis.console.commands.make.job.html` | `01353487e6da4da94edc3af0d5ccd47705aa45530e9d340466db64a2623740b5` |
| `M ` | `docs/orionis.console.commands.make.mail.MakeMail.html` | `d0114a9184ec9dbb07b660ffaf21c7cd6459d980ab21ff175211f6de06aed145` |
| `M ` | `docs/orionis.console.commands.make.mail.html` | `e59898600593638773ca3281038f52a300bad2113dfd148cb919ba8012e69c38` |
| `M ` | `docs/orionis.console.commands.make.mcp.MakeMcpPrompt.html` | `c6bfc32480301f548ef1fb3ab8447b25e58f251ec785bed08e7d181631f3dcf0` |
| `M ` | `docs/orionis.console.commands.make.mcp.MakeMcpResource.html` | `a8a59ff8fefbc1f210a3d574ac36085bfc009f4d0843da93edfbe7928a6142ea` |
| `M ` | `docs/orionis.console.commands.make.mcp.MakeMcpServer.html` | `22c9cff0f237800b66eb7e5e2d3bf3884c27527dee9ba6618a37670ff51471af` |
| `M ` | `docs/orionis.console.commands.make.mcp.MakeMcpTool.html` | `e00abc8aff11381653099ef66dab7d6eee3fdbc091670edd23e57a98d2adb211` |
| `M ` | `docs/orionis.console.commands.make.mcp.html` | `73db86b324e8ba0f00c007b69a7d4254a6888606908f6fc6f4251a75fd8b3b81` |
| `M ` | `docs/orionis.console.commands.make.model.MakeModel.html` | `210cf74c583d2f2f4c18aa37832014e78b9b3bc316c325b71b7fb8a7b0b1cc8d` |
| `M ` | `docs/orionis.console.commands.make.model.html` | `e4baa00b3619c30a87a60c547bccee9e00a5b0a1b4b2ccb9df074a91c7748d59` |
| `M ` | `docs/orionis.console.commands.make.provider.MakeProvider.html` | `04810ab3d95b7dd738f936e74574cef17e7033837b2459efcdbee074ffec22d0` |
| `M ` | `docs/orionis.console.commands.make.provider.html` | `f3d0856e6b2ec02348f72f6bdce28a14940b506a9660ec0d56f01d96a3c5e879` |
| `M ` | `docs/orionis.console.commands.make.realtime.MakeRealtimeHub.html` | `1481985460eeb486e27ab5433130e2c717d9eddd6c741aaf822ecf1c162691ce` |
| `M ` | `docs/orionis.console.commands.make.realtime.MakeRealtimeSocket.html` | `9f250955cd6d6da51613365c045fba92bd1625b31fea4a718ee675eb82430c5c` |
| `M ` | `docs/orionis.console.commands.make.realtime.html` | `83cd625913b0d091d9c12c81a6fb9eaccc6196223b166649f0d3874cb2024eb4` |
| `M ` | `docs/orionis.console.commands.make.service.MakeService.html` | `6040a15aa8d7dc005db56d30f39f40ada0c38cac9ceea76fb7af937326b1b4d9` |
| `M ` | `docs/orionis.console.commands.make.service.html` | `a31bd642b243c8fceeeb9b2014f0d9df28b8c5884d06d7d3996fa677ee835799` |
| `M ` | `docs/orionis.console.commands.make.test.MakeTest.html` | `cd1471a3c8c2ce0619209e6f5e8ea1fc9c9a849a0d1e12cc5e6111fbaa38d17f` |
| `M ` | `docs/orionis.console.commands.make.test.html` | `bda4b0e480449067fa99f36439cc16f71f97bb5addb28ae2e784b03ab3df27c5` |
| `M ` | `docs/orionis.console.commands.mcp.html` | `a470819269052287ae906bb4f64551e89999a73073b586c2f79b1280a998012b` |
| `M ` | `docs/orionis.console.commands.mcp.list.McpListCommand.html` | `733034ec6f9c118021e8d55c248089ff21349306e646e988db3218bcdce36a03` |
| `M ` | `docs/orionis.console.commands.mcp.list.html` | `d29ad66d4e5e94e82eb154ced90d7934e486893b75073ffbe85a5a171aa8fe09` |
| `M ` | `docs/orionis.console.commands.mcp.start.McpStartCommand.html` | `5aba226a36189bf928c21a29e92c4d4305e05bbaf47543cec7c0ff64495c72da` |
| `M ` | `docs/orionis.console.commands.mcp.start.html` | `f8ce01154183e216a1db744bb62d5d1884ca9659786171f761c3387fd455ab50` |
| `M ` | `docs/orionis.console.commands.migrate.base.MigrationCommand.html` | `6bb95d05957324b265d1a0d1f6143f5cddb9c51447cd151a55154967a00ec4cc` |
| `M ` | `docs/orionis.console.commands.migrate.base.html` | `ebd52d8cbce8b2ba80296a19840994ff1e2676925f78d68d51da8ac3eaf0bccf` |
| `M ` | `docs/orionis.console.commands.migrate.fresh.MigrateFreshCommand.html` | `9347752087e32b1274032d2535848d8f38f0c72554f4bd489c063439fd31000c` |
| `M ` | `docs/orionis.console.commands.migrate.fresh.html` | `9e57f0d3cfe121e7058fa8bd440a1a17eaf2a536f472b36ebe8dc346cf124104` |
| `M ` | `docs/orionis.console.commands.migrate.html` | `8fa240fef7085fc3dd1361eb8adba4f1eafc0f174eef13095ef698d1e33fcc9d` |
| `M ` | `docs/orionis.console.commands.migrate.migrate.MigrateCommand.html` | `00e72affcb4c14a391b90df9f3fac815ddcf1d5402a1e8da00dbad865b4d181c` |
| `M ` | `docs/orionis.console.commands.migrate.migrate.html` | `0295b8458da4a2d45225b35c312fa3caf82448709a22565cd1ed898007efc095` |
| `M ` | `docs/orionis.console.commands.migrate.refresh.MigrateRefreshCommand.html` | `fb4077982ae8fe8b182d33d056421ab396f6b77f9b0c814b61d905ea2673c5c8` |
| `M ` | `docs/orionis.console.commands.migrate.refresh.html` | `5f77c668db3e0a3a7dba41dde88afbcad058fdeaf13ea80d09fd1819122483e7` |
| `M ` | `docs/orionis.console.commands.migrate.reset.MigrateResetCommand.html` | `816d048187d1e92fd2bc5dc000f67725752ee2fb28740bdfe48a75efa2f571d7` |
| `M ` | `docs/orionis.console.commands.migrate.reset.html` | `5612b66336f7549a86315c388faa83413888ced1151095fbecf6a207c85fa4f4` |
| `M ` | `docs/orionis.console.commands.migrate.rollback.MigrateRollbackCommand.html` | `3b65833ce3f5d89425041f39982ee599fc57c5b853b67549e8ff955ab15e5b47` |
| `M ` | `docs/orionis.console.commands.migrate.rollback.html` | `20b2122c056a046a727111a2ee319806b15292e7ef415534123ef667ea1ec717` |
| `M ` | `docs/orionis.console.commands.migrate.status.MigrateStatusCommand.html` | `15a0a636b6e2c49afff1f5c2fca600e764c55cdf556d6c0199d2622f9d7a225a` |
| `M ` | `docs/orionis.console.commands.migrate.status.html` | `c527120ca893c2cea14ce935855eb18cd915cc8510aa8be78ff41a9f5278e3e0` |
| `M ` | `docs/orionis.console.commands.queue._signals.WorkerSignals.html` | `a37a63a839f579d777e957f2deb1adc0c3cef9c171674ed1e345e9dab0ba8e79` |
| `M ` | `docs/orionis.console.commands.queue._signals.html` | `5d52382e68e49e7bbe23fa50fb0495b1c04ce0e9795190c70801640a72b69524` |
| `M ` | `docs/orionis.console.commands.queue.clear.QueueClearCommand.html` | `5d00fbbf701a06c2bee25a663bde5b66282c5e5e3ac1466d8a778d4f8e02589b` |
| `M ` | `docs/orionis.console.commands.queue.clear.html` | `7d9e5f092ee8647e2f2385d5ceed8c2ccdb19d48a51d389755a60d670c780c24` |
| `M ` | `docs/orionis.console.commands.queue.failed.QueueFailedCommand.html` | `8f02375c47ef763974048713d3ab55abbc2e3bcc61c0bc1d83b7b2607a57bbe1` |
| `M ` | `docs/orionis.console.commands.queue.failed.html` | `bf581940763d90e35946f30b730555f4a2e1372d56ae71f72dbb5d79de51a5c4` |
| `M ` | `docs/orionis.console.commands.queue.forget.QueueForgetCommand.html` | `6c762c5efd8d7f7abccc6eeb8f8935056c573cceb7d5c061adf500d6380eaf70` |
| `M ` | `docs/orionis.console.commands.queue.forget.html` | `4a1e4f31946206c9eab4fcf703a208426e88468faedc347dadfbbe28269d1f43` |
| `M ` | `docs/orionis.console.commands.queue.html` | `a298c7d9239dfef97ad91bcf1946877573c5d0839dc723c68f7a6adde2215b04` |
| `M ` | `docs/orionis.console.commands.queue.migrate.QueueMigrateCommand.html` | `6bf78b0db5574a2092ba47439b3d6875717428da0acf737e3e9071c32a247895` |
| `M ` | `docs/orionis.console.commands.queue.migrate.html` | `41cca49eac1df312d51971f54b9976444e1c89ea708de20c88045a7b5f6da68c` |
| `M ` | `docs/orionis.console.commands.queue.retry.QueueRetryCommand.html` | `461edfa444ec29106a53770bf2eafc11ba7008b3eda3a3fef00536b151d04c2e` |
| `M ` | `docs/orionis.console.commands.queue.retry.html` | `7fba6d756b8c68af07b44a8d586da2c921496d853638c0b40d8a6fdb4c05c434` |
| `M ` | `docs/orionis.console.commands.queue.work.QueueWorkCommand.html` | `5e036a2f5b9827e1a6d4350e445f46d4e8f63d02f18b7e30215d5da605c4520b` |
| `M ` | `docs/orionis.console.commands.queue.work.html` | `ec458b86d4e87ed74c35a27f1513c7694f6d2984a0b363065f73d4682fbd3bde` |
| `M ` | `docs/orionis.console.commands.route.html` | `6780c0f0735d5505b38fc36aef97efb3a65d5b893ef4da810f49ceeef4f24c52` |
| `M ` | `docs/orionis.console.commands.route.list.RouteListCommand.html` | `54e5f2c5b83d47ab90ea5d9dd39d9efdbec5d85ff8f0b289d1d5b43ef8e27acb` |
| `M ` | `docs/orionis.console.commands.route.list.html` | `63cc6d3e4961311b32f88f72b49026923cccce89d5bcc03011f11505640d85f5` |
| `M ` | `docs/orionis.console.commands.schedule.html` | `76f29d63a96a9b1e2db09190f0bd354c47711ffdd9f41486e04dcf13a1e26f61` |
| `M ` | `docs/orionis.console.commands.schedule.list.ScheduleListCommand.html` | `d93832d23fd7d21f2da557ea593daf2ab093bb88dcdff5c54e3c735f6186c0d8` |
| `M ` | `docs/orionis.console.commands.schedule.list.html` | `d3bbf6d882e6be6e26308a1ac7cc360042ba8fb1e940b92cc84fa9262c1df516` |
| `M ` | `docs/orionis.console.commands.schedule.migrate.ScheduleMigrateCommand.html` | `6e3150878e4b42426a977aa065b1b1f7335b16b2af496194aeaff7b6a697fe12` |
| `M ` | `docs/orionis.console.commands.schedule.migrate.html` | `0143389a780ece5fb34504dd7f0c38b25a6809c214b6050a0d24df1fd5aef67c` |
| `M ` | `docs/orionis.console.commands.schedule.work.ScheduleWorkCommand.html` | `cdbb3189e68e36c52d80450ac82926b74b7cdaaf7c6bc5b8b96a206f67dc0743` |
| `M ` | `docs/orionis.console.commands.schedule.work.html` | `3f51d0417bd73ccfc317e17653d9d059eedb4007d1df730787c5cd0ff461bb6d` |
| `M ` | `docs/orionis.console.commands.seed.html` | `7509e0194b4a07e69c80f7e38b89e05b0c7d57652bf6cc2b825d110c86c5776e` |
| `M ` | `docs/orionis.console.commands.seed.seed.SeedCommand.html` | `a37ca1cabb240c75402a46ff8fe025500de03553cc4949258e9f9d262595e4bd` |
| `M ` | `docs/orionis.console.commands.seed.seed.html` | `431b0456afd41780010e9259b82862e3741294396d492f78eac1151c1849f254` |
| `M ` | `docs/orionis.console.commands.serve.html` | `cf12e0ff715c5894fc447dc6018f7a39e70afddf083eda2c8ffa5d667cba82b0` |
| `M ` | `docs/orionis.console.commands.serve.serve.ServerCommand.html` | `56d8b60979830d53e29fc8e521aa8c98aea8e94b96f72b2bd3a67438592651fc` |
| `M ` | `docs/orionis.console.commands.serve.serve.html` | `c160231037ed8214d6717f9891c474815425d61659d15b81b002fd8a03675514` |
| `M ` | `docs/orionis.console.commands.session.html` | `120c6e45b42f5db96bbdd9d78c9869857dcd54e6bf2ffe81e41459362eb33745` |
| `M ` | `docs/orionis.console.commands.session.migrate.SessionMigrateCommand.html` | `64f02fec080d9199dd5b8eb86114b276bf5accf3ce9dfc346b303c3e6aea6443` |
| `M ` | `docs/orionis.console.commands.session.migrate.html` | `826252aa833f40d9fabe68f548da1d03622f2cf13d250ca82560942dc96edef7` |
| `M ` | `docs/orionis.console.commands.support._clear.html` | `b891a3e3dbb8b2a18c96601a75743de45e8972455e3ff56881ce25fd52309073` |
| `M ` | `docs/orionis.console.commands.support.about.VersionCommand.html` | `ee2f1a7748b0e1ad04cf78682c0b5fc3fc113f5c666e0fa519750c80b5565c20` |
| `M ` | `docs/orionis.console.commands.support.about.html` | `51627de927df9cfe983eebc4f19da0fb6b3f17a1820ced2ecb2c47c5ba70c840` |
| `M ` | `docs/orionis.console.commands.support.clear_cache.ClearCacheCommand.html` | `ec0b001aa085c701358942e1e6b3cb9354d14cfd2dd8d6781235cc4eb0281f32` |
| `M ` | `docs/orionis.console.commands.support.clear_cache.html` | `383b7ac26853cf64998ad17694b98931f3c6f45c14a3ce6cedcffbca5eeef23d` |
| `M ` | `docs/orionis.console.commands.support.clear_logs.ClearLogsCommand.html` | `9de6715ae7ec6e28cb1e4c9e18f61e56c7a151691a80e16da9222e10395c88ec` |
| `M ` | `docs/orionis.console.commands.support.clear_logs.html` | `1128f86b14d195647a3c85323bb771930ddca2451f130247e7747600aa42d1a2` |
| `M ` | `docs/orionis.console.commands.support.clear_testing.ClearTestingCommand.html` | `a818c23160ceef58478a8d34e87932cf3a1462cd08c65ff6e077a7265de51aa0` |
| `M ` | `docs/orionis.console.commands.support.clear_testing.html` | `ee082dbf9ae023016a88213bda2d83f719fe18f6bfb40dc3c328bbe291531f47` |
| `M ` | `docs/orionis.console.commands.support.clear_views.ClearViewsCommand.html` | `4e8476f67913860096f6732b6ee29e3550b2c27e9d4dc9e2eeaacf37463aff5b` |
| `M ` | `docs/orionis.console.commands.support.clear_views.html` | `ff24e13aab5574268c87f99de6d151f4d904f29f31faf93d62419d2d7c0bd39d` |
| `M ` | `docs/orionis.console.commands.support.down.DownCommand.html` | `d5eb4787d7a7d34e6ed6ffe457f4ef6c5acdd7532bc772864b92844a091b7565` |
| `M ` | `docs/orionis.console.commands.support.down.html` | `44ae51c7906e034dfb338a24a9880d0c787ed4500b5e58027c9e9a3f879f186d` |
| `M ` | `docs/orionis.console.commands.support.environment.EnvironmentCommand.html` | `010657c30acf79656a55e61f242ecb094846ca7454786feb3e9b0f56188c5510` |
| `M ` | `docs/orionis.console.commands.support.environment.html` | `4825cdaa1c90ab5c3f1445116567d38345ce8053473c878951709cfebb5423fd` |
| `M ` | `docs/orionis.console.commands.support.html` | `05728281dc1edbb1c407863da2df5126f4176d1621a8829023670eb23e512090` |
| `M ` | `docs/orionis.console.commands.support.install.InstallCommand.html` | `706f8e2a4ce0296cda670f6e6f1f1a385ef2d077bc86a0604409d03f077061fd` |
| `M ` | `docs/orionis.console.commands.support.install.html` | `3896c12b2f226295b7221ea93695c2e5b67db2cb219986babee875747897b037` |
| `M ` | `docs/orionis.console.commands.support.key_generate.KeyGenerateCommand.html` | `978d1bfd4e89b13064dfd847ec0776009c39f8a5ce9d9caf360ee07b346f24d5` |
| `M ` | `docs/orionis.console.commands.support.key_generate.html` | `2e4fbec91677b67fbf536ea8515c5cf3a27d004cca3c8d6b8539965d217b1189` |
| `M ` | `docs/orionis.console.commands.support.list.HelpCommand.html` | `fd0f95f08ebd8db17c2a9cdd687943e2a520c5cd7a2aa33c6193846f1843e5c8` |
| `M ` | `docs/orionis.console.commands.support.list.html` | `380b37bdacba05ae00a23fd3c90f13b8a8ab4871961db27c310d066b602897de` |
| `M ` | `docs/orionis.console.commands.support.maintenance.MaintenanceModeCommand.html` | `2433fd9d80501ee31c9b5d007251fd6ab13f1ca9d253eb1de0ddd5d233e5a83f` |
| `M ` | `docs/orionis.console.commands.support.maintenance.html` | `77342b6701843d0379bf6837bf2beb46ba89da2932a2cf5d725504fa498f4fed` |
| `M ` | `docs/orionis.console.commands.support.optimize.OptimizeCommand.html` | `7f839ff466ea8d3912034cacdb97e19970eea8156da8c9d8459fcb72d1c60f53` |
| `M ` | `docs/orionis.console.commands.support.optimize.html` | `ffadc7db04083692fb84ff7e7eaf0c2dc64c136e103f05465df03cdda4630b1e` |
| `M ` | `docs/orionis.console.commands.support.optimize_clear.OptimizeClearCommand.html` | `5fcecc01e23d68829cd4c13a53a8d7cb9fd21297edcd8714dc5999666bcec222` |
| `M ` | `docs/orionis.console.commands.support.optimize_clear.html` | `325128b27136e76f8a620dfad65823ce622864f3af75ca59c2aa6dced2ba6f3a` |
| `M ` | `docs/orionis.console.commands.support.up.UpCommand.html` | `d84e06efb311d5b0c1d6d26f7c3a480ab89b53ae8af5390d2058608906765000` |
| `M ` | `docs/orionis.console.commands.support.up.html` | `44a15f51f1cb45f449d3796bb7a9a8b033cbfcc3a5b7501945e913352b233203` |
| `M ` | `docs/orionis.console.commands.test.html` | `9e71ed0f751779939107d93816656424f1a6af9d86b0ff85ba56c7b9e7f8c864` |
| `M ` | `docs/orionis.console.commands.test.test.TestCommand.html` | `d547ffbb90d675628485cbee51fd861b801a6441a521859d683795894a55a992` |
| `M ` | `docs/orionis.console.commands.test.test.html` | `eccccdc05ff4499ec84bdf71192a8c2bfbb1f22e8256fb010e575274242b185f` |
| `M ` | `docs/orionis.console.contracts.ISchedule.html` | `cbe897c17246547e0540e5a4d472998f742d6d056a10e27648f9359ac2e4ed5c` |
| `M ` | `docs/orionis.console.contracts.html` | `f77cc6b8972e65c7b7836a3d385a14c0e8840f0d5840882d8fed734f1677645d` |
| `M ` | `docs/orionis.console.contracts.kernel.IKernelCLI.html` | `c68e8a9d7f3079c8a2dd4b5ac1d970c9ac0f76cea3a0e65ae91c5810ec08c63e` |
| `M ` | `docs/orionis.console.contracts.kernel.html` | `a86d582f621f0258dd5eb123510505736a9b04bf765dc4ade8e591a42c4585da` |
| `M ` | `docs/orionis.console.contracts.schedule.html` | `3bba429b3b03e3cc9f13e665daa2df88133603c992f0bfcd66f4c80980c467ba` |
| `M ` | `docs/orionis.console.contracts.store.IScheduleStore.html` | `5f5e1c04bfeb823cbaabe52d58aa75a3f38e8170f1c6bd0aa7e8d5a6a9f61a7f` |
| `M ` | `docs/orionis.console.contracts.store.html` | `3a9b148f14caa7b3de1ff9057a27496cf0bdbb29d5455d1ef1da2352969b8925` |
| `M ` | `docs/orionis.console.core.commands.html` | `0f78913d0db2a5bec5dad54d3885e84883fc3dc8b1eb49a798697a1e6f95af03` |
| `M ` | `docs/orionis.console.core.contracts.html` | `878dcfa3f915075c95661f5dfdc819c89696b373989ece5500c05c4ebc4f60f0` |
| `M ` | `docs/orionis.console.core.contracts.loader.ILoader.html` | `70b46fefd6d54bcfb4ee436b59d288752d304f2f247f7aada52c865384eaf00b` |
| `M ` | `docs/orionis.console.core.contracts.loader.html` | `35278eaf3d1dec2c2c10996cf8fe1204b54a3a7bf765390c9edd6c6acda3bfa5` |
| `M ` | `docs/orionis.console.core.contracts.reactor.IReactor.html` | `0441f2b2cb5c4828a88bd358d0a1ee4b47c8fcd048918d802594103efe882523` |
| `M ` | `docs/orionis.console.core.contracts.reactor.html` | `2787aba77e86a3fb7323b5a4e3270dbc8519a0b054f323fc6a9d4a1cae7f0b5f` |
| `M ` | `docs/orionis.console.core.html` | `d3d0183d944d52cf9d16a72ada860c45228c3259801266232e8eee37baa8cc65` |
| `M ` | `docs/orionis.console.core.loader.Loader.html` | `fd2ce9cbe52e79381dbef552d6ec4630cea5ed92a032f11de40d7939a64df4bb` |
| `M ` | `docs/orionis.console.core.loader.html` | `5d0f69b007125ee91c739840c5155e75b9c5e49981ed550fd078468017781586` |
| `M ` | `docs/orionis.console.core.reactor.Reactor.html` | `c7de49bed215e4244b2840a53d8f9bf7f78264c5b8b20935543b05808834af8f` |
| `M ` | `docs/orionis.console.core.reactor.html` | `0f8ef011e19b07d25d7c58136d8fab511b70c93e5777fb6f7821feb1c313b5c3` |
| `M ` | `docs/orionis.console.debug.contracts.dumper.IDumper.html` | `87bfbc07383b46ff5aa3e01ee60cd3b9a0628b380797a850799a6c1ef1f0e985` |
| `M ` | `docs/orionis.console.debug.contracts.dumper.html` | `5664c6d418e94af80cf9e4a675ff05853fd49b01eb7abbc5a1c9c5732a7f4510` |
| `M ` | `docs/orionis.console.debug.contracts.html` | `5e177eb8a3ff10752c7af97670a13269f32e4b1e1571b3fb2335be96e94acd05` |
| `M ` | `docs/orionis.console.debug.dumper.HttpDump.html` | `8c7844285593a278660d8a46f9ca8a898375993d6c4075e9650625ffe9b1c094` |
| `M ` | `docs/orionis.console.debug.dumper.html` | `7d266c8bdd87fa3ea155689625205979934832ea1ee174d51150bc377be21527` |
| `M ` | `docs/orionis.console.debug.html` | `d9cd1dd83289139c58a039726c387bd034155315cda630c30d3e22f81ff46f99` |
| `M ` | `docs/orionis.console.debug.provider.DumperProvider.html` | `9ce8b62f39aec029b1671d15e539e695d91daea71bd528658e5c8c02022faf2b` |
| `M ` | `docs/orionis.console.debug.provider.html` | `188755ce3450b3996325e797f9fa2ba3c94b639ff6038793a952bffa03d8e0fd` |
| `M ` | `docs/orionis.console.dynamic.contracts.html` | `9b80e2f5abd1dd347595e0640154b0cc530139818d466699311593f4b91a1252` |
| `M ` | `docs/orionis.console.dynamic.contracts.progress_bar.IProgressBar.html` | `771be1a310bc6ee0cc7b5c5779cfc6c16b816177ae1db4ee016599fafc2e6977` |
| `M ` | `docs/orionis.console.dynamic.contracts.progress_bar.html` | `7f249c8bc27dbcb558b8c11b665ad787737a55e24901ec738d8f19cd4ae306cf` |
| `M ` | `docs/orionis.console.dynamic.html` | `0052f34a68cd248c234a2cf95915c07933142b498615e7c26abfb8541d8b3372` |
| `M ` | `docs/orionis.console.dynamic.progress_bar.html` | `fa0f082506d3649bd75b387d636dee0fbf4917674af69d86558b6511c6268c3b` |
| `M ` | `docs/orionis.console.entities.SchedulerEvent.html` | `528ed449837a51ddc354d448401a8c10bb2a5f0b8f803357462643db1eb09061` |
| `M ` | `docs/orionis.console.entities.TaskEvent.html` | `92e676154543c4f6dddec1d2a6a6e8e3f4322bd1b05d6ba4df7841e0e8f80a95` |
| `M ` | `docs/orionis.console.entities.command.html` | `0b677a82b8867147d29cbf11ee994807962e9ee24e4298753d557e25886e8d3d` |
| `M ` | `docs/orionis.console.entities.command.module.html` | `a9ece37be6f9248be2e8bad6a0ea0bfb5627b2cd02b2f8a7a11d4254cb436c87` |
| `M ` | `docs/orionis.console.entities.html` | `c01bd09b97c62aaa0af40b60e2f98d8c662995b8936de0e2e1cead52e46ebb5e` |
| `M ` | `docs/orionis.console.entities.scheduler_event.html` | `5d46e80dbfc292282de28503b9f3c2b3bf9c574406467b926859f470ef8cb2dc` |
| `M ` | `docs/orionis.console.entities.task.html` | `e3d58318d383635ef09e4fd181d1a70150ac0061aaff1fdfc4e9127896bf105e` |
| `M ` | `docs/orionis.console.entities.task.module.html` | `a2fed67bc8cea97165f51dab16d18b577176e120c112e88d92efc14d5417a41e` |
| `M ` | `docs/orionis.console.entities.task_event.html` | `a5d720826d3c5dc615729397101d181f012e1b0e6939a4b0acaa70ecbbf350a0` |
| `M ` | `docs/orionis.console.enums.ANSIColors.html` | `5ec19ec74c92cc19e1c1fadc76daa01fc26d666616aac7a8a2fffa93d3f76e19` |
| `M ` | `docs/orionis.console.enums.ArgumentAction.html` | `9f9c6b0a324cd5cee74af9423c2278a8d59c1aa81c05b4ea1ca0d58b0937ec34` |
| `M ` | `docs/orionis.console.enums.ScheduleStates.html` | `aa0a8c5755139d22ca6ae94641974c288133684fca913617004a82095473f864` |
| `M ` | `docs/orionis.console.enums.SchedulerEvent.html` | `213d2c7f35e6b8179da6bd981b82fc51e52d6cae65c9dd54ed294f8c59aeef57` |
| `M ` | `docs/orionis.console.enums.TaskEvent.html` | `d0c87a31658dea4653ce668aba923ce6c2f711d0f28c8a6e2cf6a012615139da` |
| `M ` | `docs/orionis.console.enums.actions.html` | `98321b69ceaf9d11a6a28130380ce3103617da86b5ee2ed67bfec96dd41fcd13` |
| `M ` | `docs/orionis.console.enums.events.html` | `0953945ad2338255f91454283d1d1a84815bdc8cd1015a2ed392b2b4a17128ba` |
| `M ` | `docs/orionis.console.enums.html` | `6621676cd1dce8682c8396b85a72853bff40981c9f7b93b27871b40dca99fa68` |
| `M ` | `docs/orionis.console.enums.states.html` | `487911839f3a7685f91a6b657fe7f859aabd467f4e5207ffb8bb4a7a4c51de90` |
| `M ` | `docs/orionis.console.enums.styles.html` | `becc608e8969dc57bb05433cb174c846dc0c11104da02d2d731f04f8eb2322d7` |
| `M ` | `docs/orionis.console.fluent.command.html` | `034235c88731297b4fc3c0795e8e4778622947cc9285bc148388d5b7a7296f55` |
| `M ` | `docs/orionis.console.fluent.command.module.html` | `d453a5a64bafcb0df614c645cd4cf88240e2ad18f04811c612c5a25f97917b88` |
| `M ` | `docs/orionis.console.fluent.contracts.command.ICommand.html` | `224c6311bf9ab3ed762fb3982e94b904bb47d62e7e420641eca5bfd3cf3528bc` |
| `M ` | `docs/orionis.console.fluent.contracts.command.html` | `b7ce6d9e17651b218f9e10925c55eaffa0633de8efeef42fe8178bab2b5505e9` |
| `M ` | `docs/orionis.console.fluent.contracts.html` | `6a2e629cb12c77803f222263a7c98810b3a3b340162e4a1ba1f1fd09fb2d6eca` |
| `M ` | `docs/orionis.console.fluent.contracts.task.ITask.html` | `c95f62298a6b26bbb975c82e979fd925d029c4fe3525659353109ce46984ca70` |
| `M ` | `docs/orionis.console.fluent.contracts.task.html` | `037559ee66bd0a69cb98487fddbdb413b7b81b91906b386e7f5612950929a1b8` |
| `M ` | `docs/orionis.console.fluent.html` | `60c242e77b04fc7632a0e7804148cd079919c9707e49c44cf40538874f36020f` |
| `M ` | `docs/orionis.console.fluent.task.html` | `638ea488571260907daf396b64af7ba29b7c917452acddae56db3613209dac30` |
| `M ` | `docs/orionis.console.fluent.task.module.html` | `5c93a268f6186f8930527f852652d9cf04acdb037c4131304f020d3f1d149c76` |
| `M ` | `docs/orionis.console.html` | `251cea5d491f37721beac2e482e6a69365cc44af1170381849e6418a6a518049` |
| `M ` | `docs/orionis.console.kernel.KernelCLI.html` | `de29d20154e7e925bd61aff03a7b6ca6df284be4ad91596d871a9a82b6b0c0e8` |
| `M ` | `docs/orionis.console.kernel.html` | `f7c381fea3a28d45ed02f2df1293f51054b001b73471b334aeed8c1a68ad671a` |
| `M ` | `docs/orionis.console.output.console.html` | `e697ba3aa59a9509c68a295d2f3c21a3d2bebaf17871b7d4389a887f84f67ce6` |
| `M ` | `docs/orionis.console.output.contracts.console.IConsole.html` | `0dfa81f29852b2b6358dc3a25cbba09b65e98e42c74d35ebea19b66f7719e5ca` |
| `M ` | `docs/orionis.console.output.contracts.console.html` | `beadacb757b983ba35562a6cabaa1574ec105ab9c0ad800b0404825c08bf743c` |
| `M ` | `docs/orionis.console.output.contracts.executor.IExecutor.html` | `c5714c15e90bac2cbdc39cd2dfe1fb3c58f81bfb5dffc4b6df33bf133a8a18bd` |
| `M ` | `docs/orionis.console.output.contracts.executor.html` | `41e912e211f6b2b0a1f3511f101e38d08e0da1c98cb0d33ec80f5621bbca10ea` |
| `M ` | `docs/orionis.console.output.contracts.help_command.IHelpCommand.html` | `1b93583885fc4d88c4f362484190e87252c0c1824dbb8bcc755f4e67366e2e49` |
| `M ` | `docs/orionis.console.output.contracts.help_command.html` | `a28085272ef5ceb88a9544fc0d71867d206619d99ec584cfa19b63a8ee9d70ee` |
| `M ` | `docs/orionis.console.output.contracts.html` | `2560b0dfbc13ab4258d679e8332f8a4952fd9baca61723933d3c4cb5553bc11f` |
| `M ` | `docs/orionis.console.output.contracts.http_request.IHTTPRequestPrinter.html` | `0ab382216f633135b77b345afb735120774cc0f5b56f1dbdee2b453e66451409` |
| `M ` | `docs/orionis.console.output.contracts.http_request.html` | `2f283db299f58e9c6c0a3a4ad1f4ba5a2eac1934a26a971ba25d5dbab72679a2` |
| `M ` | `docs/orionis.console.output.contracts.var_dumper.IVarDumper.html` | `88c256acce6daf7ac858eaaf61862174d6fd45af086ec5b4e93f7455487dde27` |
| `M ` | `docs/orionis.console.output.contracts.var_dumper.html` | `9d211be756516118a397faed65ce3578600d6780772e7de885784e70490d6869` |
| `M ` | `docs/orionis.console.output.executor.Executor.html` | `9c1ae36dcee585c4dee8cfaa72719e56bff0ec787cf6b062be04ea01bf3b86f5` |
| `M ` | `docs/orionis.console.output.executor.html` | `25d1a573c22a500757ec360a0c3845c62bfeff61929452e26f1e90c16d130ee4` |
| `M ` | `docs/orionis.console.output.help_command.HelpCommand.html` | `48b41af4fcb55cee5a130855723dfbc0aed6339874eb005de14cad3e5249fc7b` |
| `M ` | `docs/orionis.console.output.help_command.html` | `a14860427bf457c9fcc899f15f377323bba4de4c6ec915817f739d889d58ff0f` |
| `M ` | `docs/orionis.console.output.html` | `859ffe480ac431ae3a2064ea82287105f889edad9c0c504ab881254d7024f0dc` |
| `M ` | `docs/orionis.console.output.http_request.HTTPRequestPrinter.html` | `9b780a83b9033679eb747ab55d1a1022593c953e2d9b5dc89da833beae90d41e` |
| `M ` | `docs/orionis.console.output.http_request.html` | `dea9a65ef2a5d6c702daf7ee262173c068548c37a120479bfb37715f73e643e6` |
| `M ` | `docs/orionis.console.output.var_dumper.VarDumper.html` | `b198204cd76d9aa529df0490cf4692c3f6a48a16bf8e584ac42157574dfedd26` |
| `M ` | `docs/orionis.console.output.var_dumper.html` | `53442e6451980059ccafcfa603326daa28841ce461b03482bad23c6677125bfd` |
| `M ` | `docs/orionis.console.reactor_provider.ReactorProvider.html` | `cd30a15fe73380e699dd71ea4d4c6fd3ad8fc2d3033751e5741eff79e3fc4eaa` |
| `M ` | `docs/orionis.console.reactor_provider.html` | `ab15549f82916ae1aaade7df60f0c36e84dc0c02b32957328b56fb2b39859ff4` |
| `M ` | `docs/orionis.console.scheduler_provider.ScheduleProvider.html` | `2bfa43901f2508904a0c6babea95f9baab41823ffa5e4f0c3c499cf59c22d935` |
| `M ` | `docs/orionis.console.scheduler_provider.html` | `2aab57efffb40e5e0ee356d45bc875f995710c4eb5536bf3c466e2282a334062` |
| `M ` | `docs/orionis.console.startup._OutputProxy.html` | `a50f614fb6c4453ba574b2bc2a84731d37c976c1f23b9a4e100f47c3e548e5b4` |
| `M ` | `docs/orionis.console.startup._StartupFeedback.html` | `0f4ce9a77ee27fb945823dcbad8fb974bae00c4f12d3dbe5b587fb397c1f4da9` |
| `M ` | `docs/orionis.console.startup.html` | `d41b97b20b714dc67a4958557de5c49ca924b78c57f8dc3ea3b72c9bc72cf4bf` |
| `M ` | `docs/orionis.console.stdio.html` | `49bfa8a9a00fc5c060df54d8b0c06e0c6b039f0325be55d8687e1b2808f71f67` |
| `M ` | `docs/orionis.console.tasks.html` | `2126f8a8d8c0ea9711940ab5ac42c5d2196cc42ed26a166a58f17d8a5e775ecb` |
| `M ` | `docs/orionis.console.tasks.schedule.Schedule.html` | `2b24be226a76ef0daa07c8fe0920a7e8572d58c6c8bb40e9d6f2245fd6961225` |
| `M ` | `docs/orionis.console.tasks.schedule.html` | `9762e9afa697c29fde6b6abee736f0378fd3b03756a90dadc41bcfa3220f1cde` |
| `M ` | `docs/orionis.console.tasks.store.ScheduleStore.html` | `8f61f2cfb000b7bd71adc22ce3e160138639cbf2047b4da433ba57bd56ea2b01` |
| `M ` | `docs/orionis.console.tasks.store.html` | `f7c4bc9bb3dee2ad0ff90edc2ab21bda4eb826d9994a694c503cfb31e5439321` |
| `M ` | `docs/orionis.console.templates.html` | `699fe5dbe377cfb854d517f5820c4172296a24accdfa7cec450add0bf0e66102` |
| `M ` | `docs/orionis.console.templates.stub.Stub.html` | `cc9098bd5bc8983fb9e2b7e779b230625e8ad4406ca10c5b5309eff752b72352` |
| `M ` | `docs/orionis.console.templates.stub.html` | `e031f53e129cf70a945b9722b187e209342fa7dc9271ed604f6facba5ef1ab29` |
| `M ` | `docs/orionis.container.container.Container.html` | `2846cfca2a3f6224b80998e66281429908accc3bed9cead897db50b170bb8fe4` |
| `M ` | `docs/orionis.container.container.html` | `ee5a38463ad8a29873161c92d86802f59c0519ce7bb11e4da88d4d12af917d84` |
| `M ` | `docs/orionis.container.context.html` | `77d01695cf36ed3fcbbe800875edf0435c9db51effd7b7d362c3678b3cdffc24` |
| `M ` | `docs/orionis.container.context.manager.ScopeManager.html` | `1e1ab20d21a28f465f098b346c6ed38620462af7f57937215c0c1740743d3326` |
| `M ` | `docs/orionis.container.context.manager.html` | `09948901fb31f1a8be26e7b00d24ad449bc3e3326de9f5a9e235e4cdf586944c` |
| `M ` | `docs/orionis.container.context.scope.ScopedContext.html` | `865e1d8cf02e27c8710479fc9b7abe22cdb7e93e014aff3351af7698fecc120b` |
| `M ` | `docs/orionis.container.context.scope.html` | `a22aa8d64e3b1a89c5a7fde04badd7d8dc70ffd846c0d1de5a00c6b8ed6a5b2c` |
| `M ` | `docs/orionis.container.contracts.IFacade.html` | `036f1dcd0a8fb4d29961c512f696f9c33284b406a3846ff74fc5c3d5acd2a1af` |
| `M ` | `docs/orionis.container.contracts.container.IContainer.html` | `a30d001b4f9f6efc0b62d24c4e8b1139ed030e7d78a8d32424d440e4ad428463` |
| `M ` | `docs/orionis.container.contracts.container.html` | `96a29a6bd761da9fd4b5e10546e205e65b53ef0daf7bf226c15c11a151531fb0` |
| `M ` | `docs/orionis.container.contracts.deferrable_provider.IDeferrableProvider.html` | `c2e1fa888dec6a86a111d804b75d618bfa7c21c90ddd5260cf15b1461a80c2a2` |
| `M ` | `docs/orionis.container.contracts.deferrable_provider.html` | `56af7c21678d2e5fb3afab464eb310a9b8c44a1f58ff49907d02cd88dbb933de` |
| `M ` | `docs/orionis.container.contracts.facade.html` | `301825fa992e8cfe93828302b2d949758811018e35c9df431538fa011e501255` |
| `M ` | `docs/orionis.container.contracts.html` | `61e49e2b0164b3ed26cca21fb95df4521ab5db57cb3d8d5687835323b5b5db6b` |
| `M ` | `docs/orionis.container.contracts.service_provider.IServiceProvider.html` | `b58f4a6057913b21a0997fdefa0e899310cd3b574be8cd62e5e2d8debf6f20fc` |
| `M ` | `docs/orionis.container.contracts.service_provider.html` | `13dd37a1376862918a6697be126817c30a15e43e7eb009617d7891902d6490af` |
| `M ` | `docs/orionis.container.entities.binding.html` | `c753a124bbf758ddffd28bd8084166e4860fee79e61d1f1ac5382e56c862c4c5` |
| `M ` | `docs/orionis.container.entities.binding.module.html` | `62e5e4f24efcfabed5569367bd4d0330464084cfd4e2b3b14498a16bd1c445b6` |
| `M ` | `docs/orionis.container.entities.html` | `8643dd5a9759b2f0acab0b56eb89603d125821ad73f9881deb7a64571496cdef` |
| `M ` | `docs/orionis.container.entities.invocation.InvocationPlan.html` | `7c98f619acc158832f65b6fa265caf8fe6c1430f63d72243472d3eb0a061231f` |
| `M ` | `docs/orionis.container.entities.invocation.html` | `0c2995319e837a4fef0b0457685697e2a5928538662e308f08130852b6330c0f` |
| `M ` | `docs/orionis.container.enums.Lifetime.html` | `229bfe90259806d802873ca2406798ced50ee3ed147b0e6e475e5146d90e34a7` |
| `M ` | `docs/orionis.container.enums.html` | `2da1fe76db34da6f5df6a96b05b67b33898e79cadb038ea5a3302416b9df8e94` |
| `M ` | `docs/orionis.container.enums.lifetimes.html` | `31a93542e22af0e63d970d580b3acef81a8168cbb55f9c29dda2a1ba9592fa9f` |
| `M ` | `docs/orionis.container.exceptions.CircularDependencyException.html` | `bb211f73f9dd6d0ffd67243d12850e709a619aab760bb7ee8c3966b73f45fb53` |
| `M ` | `docs/orionis.container.exceptions.container.html` | `37b718e4fb0babe74a884603167be7dd53c47d55c1b27301eba086e87b1f6625` |
| `M ` | `docs/orionis.container.exceptions.html` | `00c9f96787fc8d768361363df4e017c45d42d3d460c25a12588d73c4f6ccf2c4` |
| `M ` | `docs/orionis.container.facades.facade.ScopedFacade.html` | `d667b71b568c47836c71d67e58fe5d62ccf193dc79312c86aa18f3b4d88968e0` |
| `M ` | `docs/orionis.container.facades.facade.html` | `50574a3683158bc0feaef09e27e52e21f2c818b45b6fb92c48c58dc8bbdf94d1` |
| `M ` | `docs/orionis.container.facades.facade.module.html` | `e61a4fcd518654c54bdc7a35d7bd36bc7ea52809c1b01ea45fdc521ce155f831` |
| `M ` | `docs/orionis.container.facades.html` | `883bd37ffb71b2a7e9e48894f5ead5788f84eda3bb9a5ef1a9ecf7c4fbbc3ed1` |
| `M ` | `docs/orionis.container.facades.meta.FacadeMeta.html` | `0283d49d0c4e9ea2adc6a3550d5b6227543f07d91198db0de631314165395128` |
| `M ` | `docs/orionis.container.facades.meta.ScopedFacadeMeta.html` | `1b044cb292a6e656d95f170774949b808771ac6887b46ecc59080807cfb65f5d` |
| `M ` | `docs/orionis.container.facades.meta._FacadeDispatch.html` | `eccccc8c7d5c72ee3394a67d173055c9e70baa995f41764c746c4c3172f588b2` |
| `M ` | `docs/orionis.container.facades.meta.html` | `87b5d82597c1645948bf0b82c8fa021c882e72eb7973bb87d8a9c2bc7a0a0f39` |
| `M ` | `docs/orionis.container.html` | `4a7d0b8b5785f35a53716bfad8dd7b4e8473f54d4578f60ba4d4bddc17d7a593` |
| `M ` | `docs/orionis.container.providers.DeferrableProvider.html` | `c3cf392bd54055ce69f5bfb2ab78abbe8529ec8e7bf05205fa9e32792241001a` |
| `M ` | `docs/orionis.container.providers.ServiceProvider.html` | `971789f23c2fce73f3c9bdc70b84d7a2dbfea6038ec284d948e3dc50fb957df6` |
| `M ` | `docs/orionis.container.providers.deferrable_provider.html` | `3fed9101aaeb4dc4225045526b690110af8b39c0b996d9a2b2efac73dcc66a08` |
| `M ` | `docs/orionis.container.providers.html` | `06c7d464d477c20244756b944d446957d246296838458229e638114570cb8d2c` |
| `M ` | `docs/orionis.container.providers.service_provider.html` | `f25e68ed668e9a70e63627133896558ecaf46c6190586cc13dd3bdf583081435` |
| `M ` | `docs/orionis.database.ConnectionManager.html` | `80929554569fa1d545cb0a1d9a692dc29519ff196461f203d7d961571991b5f5` |
| `M ` | `docs/orionis.database.ConnectionNotFoundException.html` | `99847194e85c2590a20dc70086c1c7205cb83f35671009652c7679eb7f16b64f` |
| `M ` | `docs/orionis.database.DatabaseException.html` | `d7dabd3e9bc1711fbfe1562f9a444d01df07cf759cb5da3501deaf74dc1db3c9` |
| `M ` | `docs/orionis.database.Migration.html` | `3770d3cfcd05c66d256af89f76a8d43601838d872eb4eb972821f68340154dbe` |
| `M ` | `docs/orionis.database.MigrationNotFoundException.html` | `fdae47cde09076510b65974ae7510b818aea5cc650e598b911a5b64117b56754` |
| `M ` | `docs/orionis.database.MissingDatabaseDependencyException.html` | `5f25bf7798bcb3f111540862260baf3aa00506b517416a6b510ce2d207f50184` |
| `M ` | `docs/orionis.database.QueryException.html` | `028d1d3dcf8c2d4d26a17c73e19351462b01b0faeff3ba2ffd10ad6027a1c878` |
| `M ` | `docs/orionis.database.SQLCompiler.html` | `ea940c45253ad7edb0b15fc49af59266e5e68373aeb014635c4b12999a7d437e` |
| `M ` | `docs/orionis.database.TransactionException.html` | `a9067fe51eb6561fce3d9747ebb40a5d338ed691c8030d4425e81d114148914d` |
| `M ` | `docs/orionis.database.UnsupportedDriverException.html` | `281c36d8e97188719389687a8c5cc6af6d66b256bbcdc57972a87e870a5b621b` |
| `M ` | `docs/orionis.database.compiler.html` | `40d8c56a4c21199b0259996dce38f6832a262382935b77a4f51e85db49d2c9f5` |
| `M ` | `docs/orionis.database.connection._TransactionState.html` | `1c5ed5ab22459dc4b3e904a11a741e2f2038e3fd9778e994d324a65bc95ec259` |
| `M ` | `docs/orionis.database.connection.html` | `8cd3cfc45c637e32b1c71dd792fad9825c90601e91ded27459b9f77992d07b41` |
| `M ` | `docs/orionis.database.connection.module.html` | `9a3652e9ef98cedf9ec357ee659391d025a89bec2a1f0b39d519e2ef3bdb2d2f` |
| `M ` | `docs/orionis.database.connection_manager.html` | `6be0ece3f783a285b99f48fe795b0dae0a4ca88e67999f52375b5fc73be5fd1c` |
| `M ` | `docs/orionis.database.contracts.IConnection.html` | `9c425d38037c5c1d6cb694f0ccc2811bb404460f65bf8c3a9dcdb5cc25f688ea` |
| `M ` | `docs/orionis.database.contracts.IConnectionManager.html` | `8f8fba811a6b8a35014bb2cf704bf9c27bbd6ea73d41cd737bdc7ae60b2d49d5` |
| `M ` | `docs/orionis.database.contracts.ITransaction.html` | `a87c010d22590813162ed03e38c5128e4be2888504fb90f5a5d5256a3eaccd85` |
| `M ` | `docs/orionis.database.contracts.connection.html` | `f068610a777749072f31ff5c9a953f8619cd1dfbcca2e4539272f3a8e55468a8` |
| `M ` | `docs/orionis.database.contracts.connection_manager.html` | `61aaab49ec8c543d36158e3a34dc1455dc9343bb706646b5e2b9686e23d01e63` |
| `M ` | `docs/orionis.database.contracts.html` | `947cb8c6e9c7378394bd8900ec1b68c162ea0873bd5c508dd4f7ce788feef2d8` |
| `M ` | `docs/orionis.database.contracts.migration.html` | `09ae761e508bae7a4574dfcb4bb71357e8103a16b2ea48550955d30a7fd361eb` |
| `M ` | `docs/orionis.database.contracts.migrator.IMigrator.html` | `5b5dd8e609e74ade0aef065b6138a7b588a4fa3fa98eb008cb45a1959bd0e748` |
| `M ` | `docs/orionis.database.contracts.migrator.html` | `2eaf095aa159170bf566e61083e862978ba8cb2597f90fcd40e6f164fe768a50` |
| `M ` | `docs/orionis.database.contracts.schema.ISchema.html` | `1e88b3e107918971688670d7394f808d8fc57abcc1132d0de7cc7734c0a2f2a7` |
| `M ` | `docs/orionis.database.contracts.schema.html` | `0cfa5fe92a90e72371e61b24af71b814e97d154cbca024d742e7c6e5b2dd6993` |
| `M ` | `docs/orionis.database.contracts.transaction.html` | `fc44ce2d04c1b0e42c60eb59f63da5a91c1efda7a5bb41c36ce022c50bf6cd98` |
| `M ` | `docs/orionis.database.dialect._AsyncDBAPIClient.html` | `50dfb27928791e5e078d26a6b82aec2d064a4584b8c5c8785224e9cabe2383a3` |
| `M ` | `docs/orionis.database.dialect._AsyncNativeCreator.html` | `7bfedf31f2fb0fe1496c09cfad3418270cd2585786196f06bc8ea6574ce05634` |
| `M ` | `docs/orionis.database.dialect._MySQLParameterEscaper.html` | `eb7b9bf2de092cd2446ba37204d7d1283986c3c05df427713e686f50448c8202` |
| `M ` | `docs/orionis.database.dialect.html` | `387e3fdae5d126ee73f41e28dded82d394acfaf0d879e4330d844f02e23690c9` |
| `M ` | `docs/orionis.database.entities.InsertResult.html` | `752048d6b8dd41fbc96f34d61df029f5ec65d17f673f1d1d04dd36207b2e0abe` |
| `M ` | `docs/orionis.database.entities.html` | `59400c8f8b610955282bd83b27e6c2135d3b578ce48a0b16cff5ac45dcd8158e` |
| `M ` | `docs/orionis.database.entities.result.html` | `e55c80f2f4bf7e93e62d445c79f96a036cd32208899759294b86ec0c1d12d41c` |
| `M ` | `docs/orionis.database.exceptions.html` | `d2c770865930ff88e488fa0fc6051dc72e272197fada752809d1d5c67272184c` |
| `M ` | `docs/orionis.database.html` | `4c369d78dabbbe3c145f89d0d9f5288ce50942841ad9758fc40b09b5d3110f4c` |
| `M ` | `docs/orionis.database.migrations.context.html` | `05b31984bf8cc41ab4201794a81b21e9de1fbdc5794297398ecd3f79549158ae` |
| `M ` | `docs/orionis.database.migrations.events.html` | `6c6b1319bcd4f93e64a981a812e635c15f1c09d6a56546c3d45bcf3a4dd173a3` |
| `M ` | `docs/orionis.database.migrations.html` | `7072772b198aab7e4981aa035677c75f9f5056d31106a9db6ce18b048a99d550` |
| `M ` | `docs/orionis.database.migrations.migrator.html` | `6bde6764a27839e5f4a7017ac7c4019f3bc9a59034d3c4689185036f5b74c6c0` |
| `M ` | `docs/orionis.database.migrations.migrator.module.html` | `97aab3e6324e2e38b272b1742ba4799f5c4b83469802da43f3554ed3b4fdbd5c` |
| `M ` | `docs/orionis.database.provider.ConnectionManagerProvider.html` | `cf330df0e5b4c52385fa016ac210fcf00486784ecc4b3acbf5e88a581287f7b9` |
| `M ` | `docs/orionis.database.provider.html` | `1cec1293f94052ef76026983e4b0b527ee3243d39c360e7c3ce33f836cfdbf59` |
| `M ` | `docs/orionis.database.redshift.RedshiftDialect.html` | `6817a3df1c564ed9777730d296b85d67e406e4af6234510940240fd0cfcd6b5b` |
| `M ` | `docs/orionis.database.redshift.html` | `535cdcec07c9532c4ee15a71fb92132f3c29ce50e5a35b5ac7869677ba399cc3` |
| `M ` | `docs/orionis.database.schema.ForeignKey.html` | `71ae264a3148d93db94a42fd58c6575e5671d28bfd8d87b8c18714d55e4095e4` |
| `M ` | `docs/orionis.database.schema.PrimaryKey.html` | `8251f2adee3b0c8b68c09be40f86ef1920a960852343986e15a36ea43d4904a4` |
| `M ` | `docs/orionis.database.schema.Timestamps.html` | `526a279189183b4cda7ead611aaafc3ddbca1e451096cfb24d7b910c09118a59` |
| `M ` | `docs/orionis.database.schema.blueprint.html` | `d271284bbe203e9292e31aaca41be2d29a95fe67b4de2924a468208a7dfd7489` |
| `M ` | `docs/orionis.database.schema.blueprint.module.html` | `7d61fc2b14aef537847f7f5bdc941b7e819ab1039c483ccbe06b8be5d079a271` |
| `M ` | `docs/orionis.database.schema.column.html` | `4b2777c99aba439a76212da8338dd3d097855d02a297579b453dc48bd60a89de` |
| `M ` | `docs/orionis.database.schema.column.module.html` | `9c095c0ed07dc832fa4656eefa4c226e85944df8fffb6c3e2a50fe457a9378c0` |
| `M ` | `docs/orionis.database.schema.comment.html` | `69fa47d3208eb237a4344e4f8c70325ea6594f2a8b3a7474300779ae9cf2bac6` |
| `M ` | `docs/orionis.database.schema.comment.module.html` | `7a813f68ed304004e24b17e81862874f1d166f75c5ee1184bd1c597ae9956027` |
| `M ` | `docs/orionis.database.schema.definition_bucket.DefinitionBucket.html` | `57f0b1857d01dac7af03dbb35452deb58c83c96bd768a922d853a2c1cfcd841c` |
| `M ` | `docs/orionis.database.schema.definition_bucket.html` | `853379bfeb65bc1e08d5db0011ab313256b0f9c5d45b4a16ecc22de6bf7f0c4f` |
| `M ` | `docs/orionis.database.schema.definitions.html` | `9a37331976c7d83c1ebd10981df62fd288316a96cf864dc7f7bd5b074c594487` |
| `M ` | `docs/orionis.database.schema.foreign.html` | `79b85abfaea67ad1512fb9a6088921909de9f2b14b950f25b9152d2703eea840` |
| `M ` | `docs/orionis.database.schema.html` | `c869e64f7b1c85aed1b5741f5e5f8e857469e687fb3a9d2d5fce46239b5f6d24` |
| `M ` | `docs/orionis.database.schema.index.html` | `ee0b6696bce983d19d40b15543788cd0eaa16b6cf2b64e31138b77a32acc9a07` |
| `M ` | `docs/orionis.database.schema.index.module.html` | `0224af87916c43cef4bf68fbefafb1b85d2b1bced2367e1e9f49b7494d93700c` |
| `M ` | `docs/orionis.database.schema.primary.html` | `ab883dac46634daf815b5993168d77b13e8876b2b28d36ef85ba17eb464e8754` |
| `M ` | `docs/orionis.database.schema.schema.Schema.html` | `6533455e441465094c6aa6af8f77099407b52b2f9c5f05d650036bcb4c1f91d8` |
| `M ` | `docs/orionis.database.schema.schema.html` | `cc3432a2f1812e5356a45517610c99fe6fdcd5b6c0b0bb56557daaa3df6f7eb3` |
| `M ` | `docs/orionis.database.schema.table_creation.TableCreation.html` | `7e9030b661647d8eb78f787edd6706db823d75a23ac2682ae4ea3f6dbbf28118` |
| `M ` | `docs/orionis.database.schema.table_creation.html` | `52ffb53a6862f879e0b15cc8dfd7f2fda0f0daa27225d1f2e363d448bdd4e40d` |
| `M ` | `docs/orionis.database.schema.timestamp.html` | `48af86977f8b658c8d03915e8438611b70d930cda684a75eaa327336431b68a3` |
| `M ` | `docs/orionis.database.schema.unique.html` | `ac33c3e011382a9ec095a154f04f4a3cf9a2bf9c469e22d1d655b83402117882` |
| `M ` | `docs/orionis.database.schema.unique.module.html` | `e1ed0d8bbe3ebc6b17dafda7539cbd5199910519f150b156c4ba031c9803768b` |
| `M ` | `docs/orionis.database.schema_provider.SchemaProvider.html` | `cb57fc6cb899b1f35f03895821dd966b1f834f18d3108847c935b45fade9a238` |
| `M ` | `docs/orionis.database.schema_provider.html` | `333e25dae4011a9b538ecdc9137ba81e5d2c1c71ed05d90d70d01c92121ab074` |
| `M ` | `docs/orionis.database.seeders.SeederRunner.html` | `46f7287e1f602d6c8c355a3b8c9ecb35bfaa758e9271754ea998e24316015e4f` |
| `M ` | `docs/orionis.database.seeders.events.SeederEvents.html` | `4286b9c5842ef21fed728dfe553c6646beeb8cc2dd753c79cf6c9d7f58572aac` |
| `M ` | `docs/orionis.database.seeders.events.html` | `ce2d89ff910b0294cf092987c7855bf0c4096682876cd33927ce955a046ffdab` |
| `M ` | `docs/orionis.database.seeders.html` | `d9f5b6094e639b14fc343f65629da8e58c7267cdf684a8fc94d91ac6b5a707a7` |
| `M ` | `docs/orionis.database.seeders.runner._ClaimFailed.html` | `07dbb9442576e605509c28fc04d91664814f9cdfc38a8d0e75ffe67c583bba08` |
| `M ` | `docs/orionis.database.seeders.runner.html` | `a017b5ad311b8bb94eb666e70df079460157f152d2b0a749505ad266b455217d` |
| `M ` | `docs/orionis.database.seeders.seeder.html` | `21706776afab3654dd63ca04048e98de13c0d406b66d637d3c5833d0a50f822d` |
| `M ` | `docs/orionis.database.seeders.seeder.module.html` | `917f11b482282ccf176777fe032e787a3bbff23f1164c858155a731ccc93a46a` |
| `M ` | `docs/orionis.database.threaded.connection.ThreadedConnection.html` | `ee8bb08755f864fdcb3274c2f18cc1881d4796979cec3113679a3c3cf295fbf9` |
| `M ` | `docs/orionis.database.threaded.connection.html` | `92942a45016a4692776723d1511803cb805fbea3d39e9a1a6c83614da26d8d0a` |
| `M ` | `docs/orionis.database.threaded.engine.ThreadedEngine.html` | `790db49c9159b90cc17963e0bf432e186120a67ea502ac2b11aa2a5fc9d3440e` |
| `M ` | `docs/orionis.database.threaded.engine.html` | `92cbcb2ae6d1a98ec4a0e9522f0ecf4f6c3bacad6fc01ae29eabf13f00cbe60c` |
| `M ` | `docs/orionis.database.threaded.html` | `93c116098138bc6005b64354b15810ab9a47d39a217c116d4388091cbd774d59` |
| `M ` | `docs/orionis.database.threaded.result.ThreadedResult.html` | `2fb96dd47042f26c4d47df5423ea9ee45be476d196327ea99d6cad6ab95ab1f0` |
| `M ` | `docs/orionis.database.threaded.result.html` | `bd9c9b5950ff51192c71153ae784e612e1a2c1c45943556a0409ab834c728518` |
| `M ` | `docs/orionis.database.threaded.transaction.ThreadedTransaction.html` | `a0460163413728a600223269ac24750bae7cd29bc5f4968a4f776f00f0d087f5` |
| `M ` | `docs/orionis.database.threaded.transaction.html` | `ce0cddd4e90319b6109690d1cbe0078358bc70930e2a4d22c43f3032ce664c64` |
| `M ` | `docs/orionis.database.threaded.worker.ThreadedWorker.html` | `a94a128e838d95f662fa063c05d7c4615f327d6ec5ed7ec33e56df00f3572804` |
| `M ` | `docs/orionis.database.threaded.worker.html` | `0d2a5613eef41fea0ee66513f64a0c55f1c808ee32c6e6b2556e460fc62b56d9` |
| `M ` | `docs/orionis.database.transaction.html` | `b128835a7a9c67f2cc0cb11ff7682951241166a6b860c1d82d27ad9fd3d47007` |
| `M ` | `docs/orionis.database.transaction.module.html` | `cd828a28bb929bebd7fed94ee86667b3c46b54dc388f489a21e7d9509e2718a0` |
| `M ` | `docs/orionis.encrypter.contracts.IEncrypter.html` | `42f93d38860e2d30a3c6b7421170b72cbbb08256a48c85013ed1d8de392c0c30` |
| `M ` | `docs/orionis.encrypter.contracts.encrypter.html` | `3cd5e6aa5be0f85ede42bf8e73de33a76fba41df64f8e47bd013d2ed8e9472db` |
| `M ` | `docs/orionis.encrypter.contracts.html` | `5e2077e5ba82d909ebc1a0644cb4c83ede588c6d362b2a9293f6345bcb78a27e` |
| `M ` | `docs/orionis.encrypter.encrypter._Payload.html` | `b1ff9c99839d89060ac786a4a39afbf50b59b5d10a5ad00b2d99df1593ab5deb` |
| `M ` | `docs/orionis.encrypter.encrypter.html` | `8af212533c9f3ce066d25358cf4761affb111618e05cb1b06d80b65711719db0` |
| `M ` | `docs/orionis.encrypter.encrypter.module.html` | `7823f92c752a670fdfd3ac24ef05fabfb1a5781d8ed9ef08c4ec0e74012262e2` |
| `M ` | `docs/orionis.encrypter.html` | `68c18003f9d8c00ba100a43a3520a45c263d8f85a90e5390b60fe11680b8fe17` |
| `M ` | `docs/orionis.encrypter.provider.EncrypterProvider.html` | `917144454bcc79b138d6ede003dcf138c6da634ec78bf59bdf83b9670b7f566d` |
| `M ` | `docs/orionis.encrypter.provider.html` | `0d814d39416b94951314fe7283122c990432d5ab2a296b1f786be151e74882ad` |
| `M ` | `docs/orionis.environment.Env.html` | `b222b87eb982c7447c5d48599cc607ffaf56a52f0802b82e0bc8a2d28ede18d4` |
| `M ` | `docs/orionis.environment.contracts.caster.IEnvironmentCaster.html` | `a39a13d8fda7be70b807586d66fa6422bd0f67e59ef63ca45a622f0f5756835c` |
| `M ` | `docs/orionis.environment.contracts.caster.html` | `1faf35e06bc8f0dc1df7e12580aaafd4d38d2c8b80e354f4b20c43ae0d34747e` |
| `M ` | `docs/orionis.environment.contracts.env.IEnv.html` | `dc548f43ef54a7407d6a3c64b4a52124b22b89bd75065240407a1aacd4a2bfe9` |
| `M ` | `docs/orionis.environment.contracts.env.html` | `93224e42a180cc80ed27f61e7128115e3ea23a34acac778e0cd2c07f458ac19d` |
| `M ` | `docs/orionis.environment.contracts.html` | `0ddccef466d15b622b48db88cbc6432dc94125332f89afe79c5634a2b9ff4585` |
| `M ` | `docs/orionis.environment.core.dot_env.DotEnv.html` | `bff9ed6a7e1204b597798b55c94d6ce0d463f987bdbf13ec71c18c6b9aa2d99f` |
| `M ` | `docs/orionis.environment.core.dot_env.html` | `fb892186ea8f00faf5afcacfe67a8f1f12acdb2ab975977085ce2223be714785` |
| `M ` | `docs/orionis.environment.core.html` | `4b85df78ae2431ec5028fff2af075469421bc79df4f3c313d4dc63288cdeb847` |
| `M ` | `docs/orionis.environment.dynamic.caster.EnvironmentCaster.html` | `6f0e7f61dc728f0a27f29d89ea8553068c0673825a0781e3b1b699cdd9890f57` |
| `M ` | `docs/orionis.environment.dynamic.caster.html` | `de568942282dd73d474e220ac46bc702395c3d15a080ee334c6aba4107bde259` |
| `M ` | `docs/orionis.environment.dynamic.html` | `eed3c57adfe4fd68951ddea49273a1cf0924eaa49b701d598788f79e0b9fc4a6` |
| `M ` | `docs/orionis.environment.enums.EnvironmentValueType.html` | `0a6ef6635f067890533cbbb0ac55addb8cae84e56205dbab52dec91864df970e` |
| `M ` | `docs/orionis.environment.enums.html` | `670f9e0de63faa7ef5bf604a7b1f642df9ca7249ade9b414093de32d9a16c405` |
| `M ` | `docs/orionis.environment.enums.value_type.html` | `467e29e610949af2387434191d493ac9102bdb87b2fd5b29476bd195a93dad3a` |
| `M ` | `docs/orionis.environment.facade.html` | `f504b432c017d7b6dac75dd57032673a7b4d5fee869478f79d3b99908766b62d` |
| `M ` | `docs/orionis.environment.functions.html` | `07b20ec426187a5f97a7b1306fe9204a46b581b080325909bfc0545ab9d232af` |
| `M ` | `docs/orionis.environment.html` | `ccf99fc429b4fddf9bd8106b5e4ccfa80e1768324f19f8e94809acbfa7b32c23` |
| `M ` | `docs/orionis.environment.key.html` | `a60827b9408b80b39ad0e7cf350996c3a831453457ec9ad7f3b4e270279ae1bb` |
| `M ` | `docs/orionis.environment.key.key_generator.SecureKeyGenerator.html` | `8a83e8b74301121d983b154c5b1954a59a7e9b19ea8284215a80df2c82686c6c` |
| `M ` | `docs/orionis.environment.key.key_generator.html` | `b4d7450d15fdd94049076ca3803368ffb45fb98c629eef70d310e3d68975c009` |
| `M ` | `docs/orionis.environment.validators.html` | `cfce3238dabc3a117ef42322e4aac76618ba00cb24ee515e02e481380e5ef1fa` |
| `M ` | `docs/orionis.environment.validators.key_name.html` | `056a0dbabb45ffd7ea748fc68b28f17a4d63517df67db6c57c8da36a2490c33d` |
| `M ` | `docs/orionis.environment.validators.types.__ValidateTypes.html` | `af378a5fb19188290a882ea786dd43d15450fa5c7f8fcd98183ffcdad2408cba` |
| `M ` | `docs/orionis.environment.validators.types.html` | `e6879d6665bf1542fd58d9d4f95078c26574e9b5cbf2bbd5ba0b633e1b9aec93` |
| `M ` | `docs/orionis.failure.base.BaseExceptionHandler.html` | `69ea51b8d275cb48cd4e6d350af6f72e1004c0aa82a01cbcddc2b888a7f8be81` |
| `M ` | `docs/orionis.failure.base.handler.html` | `6b16c5665e73faa077ec0ffe4d3028e0c1110ddbfc4fd63612b072e9442b9fc3` |
| `M ` | `docs/orionis.failure.base.html` | `633f5ee8eb3c76929ba13073982ff4e2b675f80a7d1c15e1e0d922b010a22797` |
| `M ` | `docs/orionis.failure.catch.html` | `be9ac8a1fccef8c22e691a3ef02b91fb152ae02148ddc3c9a3d05041317a1754` |
| `M ` | `docs/orionis.failure.catch.module.html` | `687ccac525d7d40c8606888447233b0e51de44311f10e98ec07cc02f42727847` |
| `M ` | `docs/orionis.failure.contracts.ICatch.html` | `065fc033277476cea36fc2430a3a8a963b7a034a4410b91dea1190f9eeb19c26` |
| `M ` | `docs/orionis.failure.contracts.catch.html` | `c5f139dda4d59ad0d530931f6085bd83a4f05c3999f471eb176101f4e9cfd570` |
| `M ` | `docs/orionis.failure.contracts.handler.IBaseExceptionHandler.html` | `a432eeaad17e6d959f6c00b0482c09e9b8678d6f96bea0eabef70da5a630629d` |
| `M ` | `docs/orionis.failure.contracts.handler.html` | `689385a7e78f7b9006099a239d699b74ae1cc61dd9e665def7a87caa3614ebe2` |
| `M ` | `docs/orionis.failure.contracts.html` | `6e97d638c239d4596d504862303a7534a1cd8d6cd62478db6bb00d2bfd0b0215` |
| `M ` | `docs/orionis.failure.entities.FailureContext.html` | `75e1efb373579e64456d620a445bae490138ab79e030fd016eddaf14fef8ce93` |
| `M ` | `docs/orionis.failure.entities.FailureHandling.html` | `2ebedf2674078ac4fa46354708bc592a0d45a4fac67fcb51e15891a1afaff75d` |
| `M ` | `docs/orionis.failure.entities.FailureReceipt.html` | `eb72979a89e68229b200bffbc307f63474b501ff93b541efe361d10cdfa99bd8` |
| `M ` | `docs/orionis.failure.entities.context.html` | `5781330c5b6c4388c9e72de49bc105899f2da91b1262b0dc51d9c89dfea8b1e1` |
| `M ` | `docs/orionis.failure.entities.handling.html` | `9f981f0656dbbaf9af951e1785249accf3e4ef46ad83d56ba0e48e61f7ffa50d` |
| `M ` | `docs/orionis.failure.entities.html` | `aa938b3b582cb86dc98dfda99172efdf7eb72f3c708f02620f33217bb808d9d0` |
| `M ` | `docs/orionis.failure.entities.throwable.html` | `4e6a020debf2f590e53a9850c3aede0986289008df0a6a0d565bc5b8a8b7a0b7` |
| `M ` | `docs/orionis.failure.entities.throwable.module.html` | `644e8f5fdddb714234ef6352bfdc2c2e50373889bd2622815a23053c882c0cf6` |
| `M ` | `docs/orionis.failure.enums.KernelContext.html` | `3ae19577648fae2dcf8d27c55964685650ee6360dd34e393b3d2536cec9e3a55` |
| `M ` | `docs/orionis.failure.enums.html` | `6209776aaf397e92d418dc8ac9da77652866f8f94a040a5e5563279b4511e207` |
| `M ` | `docs/orionis.failure.enums.kernel_type.html` | `eb2b961d2a8fb63245732ff9c92fa78cec8690a55b98cf6bc021c43778d22b3f` |
| `M ` | `docs/orionis.failure.html` | `d190dd372f4c46fc662adf760afab962247b980fd2e414e72afb248209ee4b62` |
| `M ` | `docs/orionis.failure.provider.CatchProvider.html` | `810919d9788e756cdc6a8468e5ad90abacec354fb1ba5d4ce702e69b022e9247` |
| `M ` | `docs/orionis.failure.provider.html` | `efe654ca654ed5a3e01bbcd0e0e17c05c0b43bce5fd338c3067c90e4049fd612` |
| `M ` | `docs/orionis.failure.runtime.FailureRuntime.html` | `a71fd779d2af583938a02d9efa4f456ffe4f5069fd319c6810f6cdd765905a7d` |
| `M ` | `docs/orionis.failure.runtime._BorrowedOperation.html` | `2cfcb45bf3ca64b4c8b799467371a7a9f4937872cdcf3d710909e6cecdebb954` |
| `M ` | `docs/orionis.failure.runtime._InactiveOperation.html` | `499864e529cdc142ac2bd780bc576d0eb4089c556cf2b4569f5edf5d4fa118dc` |
| `M ` | `docs/orionis.failure.runtime._Incident.html` | `fd24efc077c8fc7cc17ad60f9244549f57531e8045ebb2488377bf2bca2c0051` |
| `M ` | `docs/orionis.failure.runtime._Operation.html` | `f39424dc51000e8f0f8a36573dbef6ef1abcbc64cd7358dbd9a991c2ca2db80f` |
| `M ` | `docs/orionis.failure.runtime.html` | `63330ef6e9a81640d736c20d67889021e0859f96d702a26755cd9f49ab017c7d` |
| `M ` | `docs/orionis.foundation.application.html` | `e051be6bb2448f054bfc5299110ddaf1cb8397e6a5736dc4f82e08528bdc4692` |
| `M ` | `docs/orionis.foundation.config.app.App.html` | `a3451b09041d2492d84729a3f9ac0b6e8e88b7d738f09ad3fcff3e52b42eea23` |
| `M ` | `docs/orionis.foundation.config.app.Cipher.html` | `80f73cf082b0fdab898ff57d25958764a401936ea6d13f56e37884a9ac93806b` |
| `M ` | `docs/orionis.foundation.config.app.Environments.html` | `afec6e55af23a6d516e09b5131ba4e99d9ffc9ac845f5a5ffae2aee8b63cda95` |
| `M ` | `docs/orionis.foundation.config.app.entities.app.html` | `2508263465d2001daa5b60fc05d28257e6fa70185b541af4a315ef97ec679ec3` |
| `M ` | `docs/orionis.foundation.config.app.entities.html` | `bae5bae6ebfb0dbc31f9e93e1dfde9d02c773f2382884ec0ead80ca5d121bd99` |
| `M ` | `docs/orionis.foundation.config.app.enums.ciphers.html` | `f080cf7dedcad85efcf8a186cca8ca46d839fc8dd656b332f1467c05946c5117` |
| `M ` | `docs/orionis.foundation.config.app.enums.environments.html` | `358404266eb4ce861801c0d035bfa0fe501363bd473a26423946c9929ef34a8e` |
| `M ` | `docs/orionis.foundation.config.app.enums.html` | `888b9e8fc8a61697b0f319cdbd0533e82e4f5b6840fdf5f675f8d9fe6fff79aa` |
| `M ` | `docs/orionis.foundation.config.app.html` | `1aa5488ecb1dc76de2ed432ebf54c1280f1313ee73c169570a5301bf6fba430c` |
| `M ` | `docs/orionis.foundation.config.auth.Auth.html` | `9dceae31e00ed0ce43c04503d909a38b740e6f78387a2b5bbbd5d1fe66b36dae` |
| `M ` | `docs/orionis.foundation.config.auth.Identity.html` | `6f9a26aaba0956d88f3a021b17afef9e8362142b9f678772b1815ba44ab4c56c` |
| `M ` | `docs/orionis.foundation.config.auth.PasswordReset.html` | `bf2c788419a189665871446a423e5f6ef31ab33823e0def0c23c447fef0198ce` |
| `M ` | `docs/orionis.foundation.config.auth.RememberAuth.html` | `fe9d5d5ecafb87cb30c69eae30a83c46e3b880f9572c0f525c8c8296b14d71d8` |
| `M ` | `docs/orionis.foundation.config.auth.SessionAuth.html` | `7fa53a462b2da82395f8c3dc655088f472f90d641b89a40b9899891182be8536` |
| `M ` | `docs/orionis.foundation.config.auth.Tokens.html` | `0221ed89f28f356c858587e4700818f342a4779001dcf883d90807cc399cdf88` |
| `M ` | `docs/orionis.foundation.config.auth.entities.auth.html` | `4b9da432b3cbcfa7f5caeca0e94d218a2deb6d28e081001a5f72cb2e95d42b4d` |
| `M ` | `docs/orionis.foundation.config.auth.entities.html` | `2759202689fdedab129662515d5b7d70f501c3b6746ee4f2e3c2e00d22f7e280` |
| `M ` | `docs/orionis.foundation.config.auth.entities.identity.html` | `cfe42d51a706b2cdbcedb1a48b644a17199292302d4b8cb8d97e404a28516b75` |
| `M ` | `docs/orionis.foundation.config.auth.entities.password_reset.html` | `109267bd31eff7f14fb4a84bb398be255809563cf22111305d3632d51a386e4d` |
| `M ` | `docs/orionis.foundation.config.auth.entities.remember.html` | `660c97c2cb85a1a92b40775fe43e0c6e69804faf689ddb6e81fc9f440f5f31f3` |
| `M ` | `docs/orionis.foundation.config.auth.entities.session.html` | `7c4ffa7cff47d6623ecbd854afc65972cd2eaaa410ba035ca95f59bc47339be2` |
| `M ` | `docs/orionis.foundation.config.auth.entities.tokens.html` | `47ff58cb1b6444988e4fc646e094e377bfaec37289ec9a67d939e7c2c5492cac` |
| `M ` | `docs/orionis.foundation.config.auth.enums.guards.html` | `1d78123ef3ebd91d77a1bfb779153af45aff34b479914663ba301d347a98f343` |
| `M ` | `docs/orionis.foundation.config.auth.enums.guards.module.html` | `84ce087d52299c89df05eced141ed14cfce2043cceaaa25bd78f1f68f5b88f61` |
| `M ` | `docs/orionis.foundation.config.auth.enums.html` | `014383f6031f7740beadd7000e92996dc70ffb70e72867e5b70df1805104e1ff` |
| `M ` | `docs/orionis.foundation.config.auth.html` | `57b7a64a3737f6d5da3def0554ce065f16b8a8e85075176c13b14e850a186ab3` |
| `M ` | `docs/orionis.foundation.config.cache.Cache.html` | `b4953b7f4b8900b9bafb72d414c4a1be32fe9bcd78281ba250d2f8b86f0a9cc1` |
| `M ` | `docs/orionis.foundation.config.cache.Database.html` | `b39b189e82669c708c6a656041629ad0946987012e43b3e085ce7f5205e6b0ee` |
| `M ` | `docs/orionis.foundation.config.cache.Drivers.html` | `665936084ae9c7d0a41123481683d80196a41eabbfb04a236346e9ca69c3fb1b` |
| `M ` | `docs/orionis.foundation.config.cache.File.html` | `c4ed467cf6e4becb607759432a30f69c69ee3d617cd6adcdb0d0efbcd6346193` |
| `M ` | `docs/orionis.foundation.config.cache.Memcached.html` | `6bb3124b33605e3ceb655a1affc62b076c5bf3e4ede37c5bd1fc8c11d1c237ce` |
| `M ` | `docs/orionis.foundation.config.cache.Memory.html` | `7bae186d6f57d727c383225a8b3ba35fd6d0a7276705dd8418e3cdcd53534b64` |
| `M ` | `docs/orionis.foundation.config.cache.Redis.html` | `9a6f16ae7509bdd4d7771bcaa98898fbeb2287d612e21093cf891a07f80d2533` |
| `M ` | `docs/orionis.foundation.config.cache.Stores.html` | `5fa359062a9f4b3a27ebd49eb3006f5e6d3052beefb8332ba117299ae1e02b08` |
| `M ` | `docs/orionis.foundation.config.cache.entities.cache.html` | `34b4c4b5dcbaf86a04b29b421b00570b7471864aba3c9677017f7355c57e5522` |
| `M ` | `docs/orionis.foundation.config.cache.entities.database.html` | `84b98c243bcea3b037822663a2e61069d1ba94a33e6d0f537a04220da3b04dda` |
| `M ` | `docs/orionis.foundation.config.cache.entities.file.html` | `4a9c565e59ab51a2a6436aa2eddf5f8e046d19d18acace08977bd09440d8199f` |
| `M ` | `docs/orionis.foundation.config.cache.entities.html` | `09e368040ff0360988cf5389b174b1cd23656d0dbf9a2fdc2915edb15432829f` |
| `M ` | `docs/orionis.foundation.config.cache.entities.memcached.html` | `ce0bc7c2637aefbb2624bfb80ef70c07149dd9ff23c98b742603f0f3e43fa926` |
| `M ` | `docs/orionis.foundation.config.cache.entities.memory.html` | `7678d5aec1aae14749d5ba5911932011472c75f805f4eba04442c235c58d2c19` |
| `M ` | `docs/orionis.foundation.config.cache.entities.redis.html` | `f5977c0aa80692de7ca52d07476051aa0d26e9b423fe805414311515d0d03d0d` |
| `M ` | `docs/orionis.foundation.config.cache.entities.stores.html` | `8e861f60a4e182fb7f49e1ff61af8e551e7e38db4e7a0aacd9af0f7cb65dc291` |
| `M ` | `docs/orionis.foundation.config.cache.enums.drivers.html` | `822ea101d3c031ad2d1bc10e90cd418b257359a10c7f3f5362e81e7f4bcd82f0` |
| `M ` | `docs/orionis.foundation.config.cache.enums.html` | `9cd5c8952aca9ca0a2e00d2eb5281bf6fc14faf5189330d90f939833ecec708e` |
| `M ` | `docs/orionis.foundation.config.cache.html` | `33276e1979e779428ccda4ce487a3233c8e31c7741f3bab5a592550e3a0fd304` |
| `M ` | `docs/orionis.foundation.config.database.ConnectionName.html` | `484f4ac0109fd90a54b809c165a2bfe0f5578e5f0bc1f2800442a267af798c19` |
| `M ` | `docs/orionis.foundation.config.database.Connections.html` | `928715d4de34b8f741ab606ffec48992aa0ac1f46175fdf52ab61bdfe934376c` |
| `M ` | `docs/orionis.foundation.config.database.Database.html` | `b8312ecc1bac61643660184607971a286dcd3cad03fc6ad92fac3db131d37656` |
| `M ` | `docs/orionis.foundation.config.database.MySQL.html` | `928931e600a247075f6ca9e75344174d7ea64014d8326c89c11f907cd64b5d15` |
| `M ` | `docs/orionis.foundation.config.database.MySQLCharset.html` | `ebc41e3afbcd177ee08a462d342123b197222ea57c8f3c8cb5955fc4881a0370` |
| `M ` | `docs/orionis.foundation.config.database.MySQLCollation.html` | `54ceeac06d62d593305638b3696f1bee52b0688095de0ba95a085a4caf5fc6e8` |
| `M ` | `docs/orionis.foundation.config.database.MySQLEngine.html` | `8ee4245e6a9738f7bd583500de33ec16bc2913c70ca85e56c6af21457b2074c1` |
| `M ` | `docs/orionis.foundation.config.database.Oracle.html` | `30a8c4d46cbfc7ab46309b883813ccce196f9acbb70fe12815dc00cb13cd4747` |
| `M ` | `docs/orionis.foundation.config.database.OracleEncoding.html` | `0042bea15c933c449883efe518b0043b716847e1e3a8778f1301da44844b9fb1` |
| `M ` | `docs/orionis.foundation.config.database.OracleNencoding.html` | `5a8f494cc818038a699b791c83895547e4302e0a91d1a7d3f6b388ed533fbbfb` |
| `M ` | `docs/orionis.foundation.config.database.PGSQL.html` | `370a052d5554be67ba05aa9f66327e2e60ee141858f6a2a67597f3e7409f2a17` |
| `M ` | `docs/orionis.foundation.config.database.PGSQLCharset.html` | `63d8d8f474ac91dee248c009480c9b684322ff7c0c992ee5826099b83a1a308f` |
| `M ` | `docs/orionis.foundation.config.database.PGSQLCollation.html` | `3964c1731d01ecdb4b03073c50a56e97ceca21c8c59676cccd979ef37be267c0` |
| `M ` | `docs/orionis.foundation.config.database.PGSQLSSLMode.html` | `a6031cc37ad1219a9db9cdb87c34499621862639699f732017f3424ce7da2f09` |
| `M ` | `docs/orionis.foundation.config.database.Redshift.html` | `7dad34c0dba531bcba23eca624ee89131aa495a4155520883c05ecaddc0418c6` |
| `M ` | `docs/orionis.foundation.config.database.RedshiftSSLMode.html` | `b9314ca9e6310cc6e1267c3318bd23ee4510db1b62087ecb6d705be1afc5ebc7` |
| `M ` | `docs/orionis.foundation.config.database.SQLServer.html` | `0a4bd36f6046feb88e3fc856367b227ca0d23bd49bc0ff32173af7eca83cbaa2` |
| `M ` | `docs/orionis.foundation.config.database.SQLServerCharset.html` | `d2a865c19a0182e6bd41933a3d48d9d3173c1a19d92c6680b24ad091cee89270` |
| `M ` | `docs/orionis.foundation.config.database.SQLite.html` | `32fe368b260af1b0505c4975bcb855c7efefe047944ae0d3cb355c3ba55d485c` |
| `M ` | `docs/orionis.foundation.config.database.SQLiteForeignKey.html` | `8d7f12ae9861b11146f0f296c4295bdaebc5fab9c3fa2709c32502e049779240` |
| `M ` | `docs/orionis.foundation.config.database.SQLiteJournalMode.html` | `2e085502613bcbd5b38fd3ac64518e72f1e92f6158f70bce833387187f481947` |
| `M ` | `docs/orionis.foundation.config.database.SQLiteSynchronous.html` | `605d828b9205f4466574050ef094c9c5bb789ab30720bd83ff39ef3f88bbb4e3` |
| `M ` | `docs/orionis.foundation.config.database.entities.connections.html` | `caf1848166f57f49a4ee00c9fd4b23c046b470be6900cf7007c3ae4ae0a49a6e` |
| `M ` | `docs/orionis.foundation.config.database.entities.database.html` | `2e539a4972903d649a43cf9d923cba58d4ae226d38f19f732739a780967dd621` |
| `M ` | `docs/orionis.foundation.config.database.entities.html` | `de1ba73d054b31581dce78a8004b2e6ecbe4583cf4968e9de26ab6ef50c6f1a4` |
| `M ` | `docs/orionis.foundation.config.database.entities.mysql.html` | `1cb83854912f99a26780489fddf4259d30ed38c3ed8a07ba4b24d118c3900982` |
| `M ` | `docs/orionis.foundation.config.database.entities.oracle.html` | `543291fbf69899b6f7477bdaa3d8a94d4691f65c7d57d42d5698622647b04476` |
| `M ` | `docs/orionis.foundation.config.database.entities.pgsql.html` | `fd1e5c15a9cc7b32a13d39ee1dfe35f8afdfe2fcd3df10975d3a2b3a43b7336a` |
| `M ` | `docs/orionis.foundation.config.database.entities.redshift.html` | `97460d7c44ef8d351e976573cf85f394d107a2a0f58df17c0c6b41d03fb68a60` |
| `M ` | `docs/orionis.foundation.config.database.entities.sqlite.html` | `e64727560c3420ab9a2357dcb811bd698093b49be9a47c2995cf15eadac13240` |
| `M ` | `docs/orionis.foundation.config.database.entities.sqlserver.html` | `c6fdb893dc4a2c700a196841b121f258d90f30798597fa5deca9e4d7169634f9` |
| `M ` | `docs/orionis.foundation.config.database.enums.connection_name.html` | `124bc05d84bf23e6db2cffc7d0172ef6225157f1bf0435ed81500304eaf03319` |
| `M ` | `docs/orionis.foundation.config.database.enums.html` | `9d2f39f5a25e2e7b2f8587e7191d760a23624e1d70117215dbfd6f6d1522e67d` |
| `M ` | `docs/orionis.foundation.config.database.enums.mysql_charsets.html` | `992906603d025a1877fd4f60a2f578a4ce175ec7c5503346fdac4965dd4712af` |
| `M ` | `docs/orionis.foundation.config.database.enums.mysql_collations.html` | `ad320d628818d4306dafc73d78804f0499c5ba635f85a131c2df16a723df67d0` |
| `M ` | `docs/orionis.foundation.config.database.enums.mysql_engine.html` | `13653d0084a832627e9b66a44fda890d257513454fd5a5530c1a016773190310` |
| `M ` | `docs/orionis.foundation.config.database.enums.oracle_encoding.html` | `febb4b73bb73767d7c8faa559353939c0fec23442a8296b57cd184195faf95e3` |
| `M ` | `docs/orionis.foundation.config.database.enums.oracle_nencoding.html` | `2d07c0543a0328e7105f2878a0cc0ef7a974e6773c435ae75ca6f95dcee5bef8` |
| `M ` | `docs/orionis.foundation.config.database.enums.pgsql_charsets.html` | `d1f5b72b4a71825c541dbecd9c6a24081e4fda623f5c7c9be013c69e9646fb42` |
| `M ` | `docs/orionis.foundation.config.database.enums.pgsql_collations.html` | `08e1c6bc6908626afadff2e83f03932f076320050ae8e1c12c0c87570aa96a96` |
| `M ` | `docs/orionis.foundation.config.database.enums.pgsql_mode.html` | `528f8601a5e19fb23377dd4376844a75405c9da62deb7164cd9dceaa5aa8749c` |
| `M ` | `docs/orionis.foundation.config.database.enums.redshift_mode.html` | `d865a0f8d13471cd0b762149a2cca5f4b2d888e5106f456fad3b9d476863511f` |
| `M ` | `docs/orionis.foundation.config.database.enums.sqlite_foreign_key.html` | `527e3a1a692bdbf0436de9cad7fce6acc8dc416cd813775324fcfc9738c1e489` |
| `M ` | `docs/orionis.foundation.config.database.enums.sqlite_journal.html` | `a5f5ad4303e5f010266d817f690f7234c57d64caa4a6512d3db58ea56a2ae133` |
| `M ` | `docs/orionis.foundation.config.database.enums.sqlite_synchronous.html` | `725723801586bc9a66d373bfb24dc540cd6fb0258fab9711d6643f0a8bb9dfeb` |
| `M ` | `docs/orionis.foundation.config.database.enums.sqlserver_charset.html` | `2f6d8a758da6c98d9a8bcab591444dc01ff7a4c8f4f26a4c50a61677db42c7e9` |
| `M ` | `docs/orionis.foundation.config.database.html` | `2769e2ff65d463b4ca976fb55f9b1c1e8ad1782b2c4ec13e58420aad1f26e30f` |
| `M ` | `docs/orionis.foundation.config.filesystems.Azure.html` | `dfff10c576b09e8399fa9d711e2e891f0bce5465063dc3267b6548e8b7258ac8` |
| `M ` | `docs/orionis.foundation.config.filesystems.Disks.html` | `8e24c4944dfaada3bcdb3051abbfe24ed93d18281684db2b1e7d23551421c094` |
| `M ` | `docs/orionis.foundation.config.filesystems.Filesystems.html` | `930b4ecbf39eddc3d395dfd31580a96eb3d597e47edc585faae0346e93bea3bc` |
| `M ` | `docs/orionis.foundation.config.filesystems.GCS.html` | `a7fc2f82ccc98f1899f6b42847e6fd7937c6ee865bf3cf35acb7708f3d290b4a` |
| `M ` | `docs/orionis.foundation.config.filesystems.Local.html` | `159c0060fa9877a36e3d02093bd3e5d9cd7c81bfb11000b936d3e28e6ebc825b` |
| `M ` | `docs/orionis.foundation.config.filesystems.Public.html` | `3a964e0d78280099a58b998836b77ecf6ab8014b5dd7eb9b012e1a20a2175011` |
| `M ` | `docs/orionis.foundation.config.filesystems.S3.html` | `7089839fa63883851f907cfd1dcca0c53056421200ceb6281fbf3cd06903f66b` |
| `M ` | `docs/orionis.foundation.config.filesystems.entitites.aws.html` | `d8d451a9a91515f45d8895f2a77a47e8cc91cdab894d62ba84ebb63ba2d6da07` |
| `M ` | `docs/orionis.foundation.config.filesystems.entitites.azure.html` | `2ee98c9214b8c8cb58754a9bd248aec23e079506f494caeed3c68e817124332d` |
| `M ` | `docs/orionis.foundation.config.filesystems.entitites.disks.html` | `7f63846a3f6895123ba5e4f26ec57225aa210008ea02131795dc0763e076738e` |
| `M ` | `docs/orionis.foundation.config.filesystems.entitites.filesystems.html` | `5d71804300595bde91d83c29ded2a41f121fee24be124f12c887f6c662e3c9ef` |
| `M ` | `docs/orionis.foundation.config.filesystems.entitites.gcs.html` | `5870165ea761aee91d94457061429dbef011659234f3dcdef64e2892bf86f24f` |
| `M ` | `docs/orionis.foundation.config.filesystems.entitites.html` | `4fdf8d5402f1eb13c9089ada736c4f53773939d224dc65a2120b54366ff86ff1` |
| `M ` | `docs/orionis.foundation.config.filesystems.entitites.local.html` | `2249944a1c6c194903d097d858ab48cfc1024f66c00c05e7f7ed41bd8fae9c0c` |
| `M ` | `docs/orionis.foundation.config.filesystems.entitites.public.html` | `929e4dd378f3c57f7b162edd82e8baf185d46995a7f36c45bdfefa702ed23497` |
| `M ` | `docs/orionis.foundation.config.filesystems.enums.DiskName.html` | `0082df7dfb39d980c944aa92a2a30e587696d28670ab139cdaa6fe4a6213869e` |
| `M ` | `docs/orionis.foundation.config.filesystems.enums.disk_name.html` | `16389b233f686eca2de88f1f75c56a1044d68121776ec78420451b3b44bce351` |
| `M ` | `docs/orionis.foundation.config.filesystems.enums.html` | `854d68be287fa898c2f2d5354fbb59488ff180574aa1d28f7b218542e45c2352` |
| `M ` | `docs/orionis.foundation.config.filesystems.html` | `d1038b151b10a1d3d3e12bfdc63dbdaf572366d71bd7b6ad190b38efe977bafb` |
| `M ` | `docs/orionis.foundation.config.hashing.Argon2.html` | `2194bc3a67cfbbad618f1bbb4ce1ade4da363a88b1952072178a08a6b2ab81f7` |
| `M ` | `docs/orionis.foundation.config.hashing.Bcrypt.html` | `e645d35115703cbe61881f8b46240a2143e75dad8a6236a89e762d6823ff688f` |
| `M ` | `docs/orionis.foundation.config.hashing.Drivers.html` | `373a11bd5c78bf72c206076769e3a13feb345a241cb31f7b631b745492bc18e1` |
| `M ` | `docs/orionis.foundation.config.hashing.Hashing.html` | `52ba3e65f2ce276737b32cfce5bb6ad02bc5c310321f42cec97948fee8005ca7` |
| `M ` | `docs/orionis.foundation.config.hashing.entities.argon2.html` | `260d9a5a68ee9191da0194757af319a27ab24745777b85a96105f78e4b30dcde` |
| `M ` | `docs/orionis.foundation.config.hashing.entities.bcrypt.html` | `59b3b7a8a8c02bc723f7f5e3953c1b733ec638cd46e0386193ca90f0944732db` |
| `M ` | `docs/orionis.foundation.config.hashing.entities.hashing.html` | `acfda6f712403581a11ab36faf8694e64ee3eb9e9f2f9177145e4f7c0c9ae4cf` |
| `M ` | `docs/orionis.foundation.config.hashing.entities.html` | `4c3fdc02a38db2f347472ed5d2c1c1c87f5f44079e72a36bb69021d28647540d` |
| `M ` | `docs/orionis.foundation.config.hashing.enums.drivers.html` | `ccedf93f4bf00a5afb2f298ae4bba1b82b9a4519b7df3e8d474a745bfcd15ca1` |
| `M ` | `docs/orionis.foundation.config.hashing.enums.html` | `34b6e57b99edca833137cd8b10eab8e67955e323d525cb17ebeaae58c87b9c53` |
| `M ` | `docs/orionis.foundation.config.hashing.html` | `0b5a564f684338556ab91d3103b84276ee363ab3546364db7007703f891d9ffa` |
| `M ` | `docs/orionis.foundation.config.html` | `6837b17b46b6a1b97adee92fed93e048f7041ca4abaab804eedc629d83c7bc5f` |
| `M ` | `docs/orionis.foundation.config.http.Cors.html` | `e92f6142997a3e61ea4649e7063962af2ed3c0e6ec66057918484847987a1a93` |
| `M ` | `docs/orionis.foundation.config.http.HTTP.html` | `a89613e84ae641c767e3bcf3f6c7761f7618bece86206d86a178fb1981ad8ba7` |
| `M ` | `docs/orionis.foundation.config.http.HTTPBodyLimits.html` | `4305eb14424a71965c9ac0db28f64e2b7d926f80912128a8f6e05b23af01aeb1` |
| `M ` | `docs/orionis.foundation.config.http.HTTPCsrf.html` | `9619bf20596b5a3e12cd4e0376f05ac9b929ca72ad8bf2db4470fde2e1358bcc` |
| `M ` | `docs/orionis.foundation.config.http.HTTPProxies.html` | `adbba34de7366dedf3d3147b11719cb810ab5a1dacd566d753fc06266693496c` |
| `M ` | `docs/orionis.foundation.config.http.HTTPRateLimit.html` | `ab726678c0d34a7da44920500b7d63371effd939868360daf9cd63eb1504ee37` |
| `M ` | `docs/orionis.foundation.config.http.HTTPSecurity.html` | `802983bfaffaea054a8bb0084a83f2eac4a2aa0a91ecc4f194ecb42efdde2c86` |
| `M ` | `docs/orionis.foundation.config.http.HTTPWebSocket.html` | `575ad58c833da34e8e1b7140a0c15442d7e7dc5e1f9a63c91567b80b37999f52` |
| `M ` | `docs/orionis.foundation.config.http.Redis.html` | `a4a448f8fcd8a87ec5e60f6fd7b0cb64fad79d941d307c7d659b2c4810011cfa` |
| `M ` | `docs/orionis.foundation.config.http.entitites.body.html` | `7dc641c9c26eb74b74e7a29bb17f7aaa0470fd6ae4f972e645ed63ec39cc3474` |
| `M ` | `docs/orionis.foundation.config.http.entitites.cors.html` | `1bfbc8dfb023222b99cc21c4e88df9e134b8ec5a0c106ed8f7b463c3ded79a42` |
| `M ` | `docs/orionis.foundation.config.http.entitites.csrf.html` | `64708233b0c35f8bb6bf83fa1c53685215a1412c54986143d426a53ddaa6ee7a` |
| `M ` | `docs/orionis.foundation.config.http.entitites.html` | `918f8ab947aa6e051be2bb01579784953adaf4afcc0e872a629a408e9b04e6fa` |
| `M ` | `docs/orionis.foundation.config.http.entitites.http.html` | `26c92928c60d79ab1ad15c3cbe7e270c5efc87ba1e933673b691faf5d92307f4` |
| `M ` | `docs/orionis.foundation.config.http.entitites.proxies.html` | `9b27dce1ecc9c1ffd6bccc9cbf3fcbf1d203be9efc03f867c0965afd0258dbdd` |
| `M ` | `docs/orionis.foundation.config.http.entitites.rate_limit.html` | `80c17ec368da12e61b9a365bc3084826f906872496d3c752d12b8224861aa2ae` |
| `M ` | `docs/orionis.foundation.config.http.entitites.redis.html` | `e5c25c62a3677207cbdb2a8813d74b6d8aabc91259881e3f6892bf0e7ab6542a` |
| `M ` | `docs/orionis.foundation.config.http.entitites.security.html` | `cf846eb3ee2c37db4cf04c34d0ea0325d42f28a59ba95e85ea88654746206f95` |
| `M ` | `docs/orionis.foundation.config.http.entitites.websocket.html` | `4d1b62bd9e59275146effc4c5f902954b941f80528bfd6c56da7105e583c3101` |
| `M ` | `docs/orionis.foundation.config.http.html` | `775ca76ba04ad6789f2019c5ba1f7da21057aa4b2e2c0197e9968da0ede81827` |
| `M ` | `docs/orionis.foundation.config.logging.Channels.html` | `f9d6195f9364960718127cf9fd0d29ad936c3cb754a43d6f6d0ecf5dfd738e58` |
| `M ` | `docs/orionis.foundation.config.logging.Chunked.html` | `6e7a2992d498e00986b77fc11aeaa3ef459057ba8b07d7e9b896c8090d538af5` |
| `M ` | `docs/orionis.foundation.config.logging.Daily.html` | `0322202885953b92006b0327b1083bf82860ee6a6f77b96ea37506c1659d6a11` |
| `M ` | `docs/orionis.foundation.config.logging.Hourly.html` | `e66e504c80917e72b1798cd1d3d1683fec7dba2996d2dee4e1089b6ea860add6` |
| `M ` | `docs/orionis.foundation.config.logging.Level.html` | `0bd947c8bfb09feb0cdfeea9686954795dea16c3f7f0e6ef85441c487ad1e75e` |
| `M ` | `docs/orionis.foundation.config.logging.Logging.html` | `1ef930389332465db3d546451083e965a84b8e0bd5d94291589b54d7aa091ebc` |
| `M ` | `docs/orionis.foundation.config.logging.Monthly.html` | `a76e787211e73821db3ac2978583ea13b43ef1692bde6cd428fab6b040e5c1ad` |
| `M ` | `docs/orionis.foundation.config.logging.Stack.html` | `ab06ae00cf9aa26649004f8312e0422bae2cff90e1d31121e3c38f9df8b577f2` |
| `M ` | `docs/orionis.foundation.config.logging.Weekly.html` | `e87a0a6c320c49e251e66ffa1533bfc9967ed4ce21bc5ca58ba2527103fd5c5d` |
| `M ` | `docs/orionis.foundation.config.logging.entities.channels.html` | `3483d987427b8a13fdc1a99aada2d467092df68a817981f2f9a87b8ca31ef5d5` |
| `M ` | `docs/orionis.foundation.config.logging.entities.chunked.html` | `9069274013cb57951cd912c126e3acdfbf3a42a4d7a51b2b94289203255b7a6f` |
| `M ` | `docs/orionis.foundation.config.logging.entities.daily.html` | `b9e2712e4b4300bdf97dce67b3378be67b216bb03fa9bbfcdecc9f9eca46c6ed` |
| `M ` | `docs/orionis.foundation.config.logging.entities.hourly.html` | `6b7775ad63f9e97dd997ca4f353e9195b8990c97277fd10a1fd926eac8211bf2` |
| `M ` | `docs/orionis.foundation.config.logging.entities.html` | `f9a172fda290eda7f9503ded13203b328bb40c63e14f81d507cdc59b29ecb11d` |
| `M ` | `docs/orionis.foundation.config.logging.entities.logging.html` | `58e34e58aac1c74a0f022341d85ccb6f04221aa6df60d30cf88d21fa472cd60f` |
| `M ` | `docs/orionis.foundation.config.logging.entities.monthly.html` | `db563726712958cf76355500babd62a078d20a87813349eae29a31f9fd2a2057` |
| `M ` | `docs/orionis.foundation.config.logging.entities.stack.html` | `612d35808fe3ad0265412d1fd6dd01a8f2d0b8253e43336907bb9a8cbf18533c` |
| `M ` | `docs/orionis.foundation.config.logging.entities.weekly.html` | `75414f4a50eec3ee45398d78ad57739b10d221055f951a29e99e1393e9509a86` |
| `M ` | `docs/orionis.foundation.config.logging.enums.html` | `04b87060347fe18b9e79a797a5267b16622ace821cf77fffb1101ffa5b0a6265` |
| `M ` | `docs/orionis.foundation.config.logging.enums.levels.html` | `a19cdb4dd1de3b96b0620995260b767228455a385aeec9fa712f9db8c7c559a7` |
| `M ` | `docs/orionis.foundation.config.logging.html` | `30b974668345e23991e436c7fddaab6ce9d3226684a4b386bcb1af49e1e39506` |
| `M ` | `docs/orionis.foundation.config.logging.validators.html` | `9b750244a291f8282b12051d8ebf6563106c7bb7d053f6d1f86c160dd6f5ee06` |
| `M ` | `docs/orionis.foundation.config.logging.validators.level._IsValidLevel.html` | `4827c72e49b0778857be7893fb8def98b8448929afc63bd4d087edd26dbfb1c5` |
| `M ` | `docs/orionis.foundation.config.logging.validators.level.html` | `82607404a00056de138adb46532b0cb6a5d8cff324ac49e9d9136583546c617f` |
| `M ` | `docs/orionis.foundation.config.logging.validators.path.__IsValidPath.html` | `db05e87a0d7f7459d46865ef086a051990c89404d20a76c544fa032fffcbe015` |
| `M ` | `docs/orionis.foundation.config.logging.validators.path.html` | `482b4690018fb95fb1e5ec3e4c1708b7b9b697251bc031c345649dab6865117a` |
| `M ` | `docs/orionis.foundation.config.mail.File.html` | `a7f1cf05b94476916ba1db7fe750f2e0ac87bdc6d2adfa883466bd0aeeda3d24` |
| `M ` | `docs/orionis.foundation.config.mail.FromAddress.html` | `cbfff22a8d6002d572f75faf8182515e3e09281d975c00c9ce50e05c8f7213d0` |
| `M ` | `docs/orionis.foundation.config.mail.Mail.html` | `016fa2fc4208953e6b6da6e409d462aa759320c551d6de78c888a31ebce09910` |
| `M ` | `docs/orionis.foundation.config.mail.MailDriver.html` | `db82c9f730bd3372e6fafd9bdef211ee02c7fce0ce07f4c1b068f04e8f192770` |
| `M ` | `docs/orionis.foundation.config.mail.Mailers.html` | `ce073e0728287b1ea09f41f0a319b9a2aee213ec49527faf7708f2c300cf4f05` |
| `M ` | `docs/orionis.foundation.config.mail.Smtp.html` | `b290d6b4c76b334e3de0ffb813346675c350759e21ced72aaad2843ae42ab9d5` |
| `M ` | `docs/orionis.foundation.config.mail.entities.file.html` | `73fc74305b5a7b9afaa154abbcef49ef026fac5a94b4766aa903a0259857d769` |
| `M ` | `docs/orionis.foundation.config.mail.entities.from_address.html` | `050d00219f2039c1c483818a561c438477768c1b4a283453d683685e7a89d09e` |
| `M ` | `docs/orionis.foundation.config.mail.entities.html` | `c1dbf14816dc49375ace5ad14b659a0e540891ef423d32de78120d0adf749420` |
| `M ` | `docs/orionis.foundation.config.mail.entities.mail.html` | `4a18eeb403f392912bae1d012c04f51e802dcfc62e91439e8a3655be83ee8708` |
| `M ` | `docs/orionis.foundation.config.mail.entities.mailers.html` | `d2873b70a9ebadc53a66d654f2f03e0c139c5c4b2654f45b26b82bd07550c010` |
| `M ` | `docs/orionis.foundation.config.mail.entities.smtp.html` | `dc10bb32c78472a93bdf379536817fe5dac08a6e5313a860132472a3b4ff3bc1` |
| `M ` | `docs/orionis.foundation.config.mail.enums.drivers.html` | `8055cd079473bf3f26a3ad96d17d696282f794457327fd76741f2201f4f1fe66` |
| `M ` | `docs/orionis.foundation.config.mail.enums.html` | `7eb8dbf0fd24ae4343a325a3d0cec6d345c0e5abcdc3a6a69bf52eca3620afcf` |
| `M ` | `docs/orionis.foundation.config.mail.html` | `f8a13e2ffac88c18487cede66a0129e0168cdfa31d98b694025c31a8fcec1a16` |
| `M ` | `docs/orionis.foundation.config.mcp.entities.html` | `15092a8b5a24773b0bc16fa071d2cbd63e587746da4d2c798ae88c80ea6a1ca2` |
| `M ` | `docs/orionis.foundation.config.mcp.entities.mcp.html` | `93d78c43bd974c63fbce4ab4125682b1a0e2f9302576cbd91d7e7a21ab076bdc` |
| `M ` | `docs/orionis.foundation.config.mcp.html` | `32119ca89a8a54539030dedc17111043e8ed2056ea321f035be6a6f85611d314` |
| `M ` | `docs/orionis.foundation.config.queue.Connections.html` | `cfb455e87960d5786d80fa15247e539ee3212744db9ff5096bee602686606528` |
| `M ` | `docs/orionis.foundation.config.queue.Database.html` | `4b14fc240982878c38c2728de19e8aa06f0f01b0117d1d26842e8a56d58abf03` |
| `M ` | `docs/orionis.foundation.config.queue.Failed.html` | `06906d62636b9d878e940543225849bb2e82ac60af416775cc8adf454bb0378f` |
| `M ` | `docs/orionis.foundation.config.queue.Queue.html` | `b192096642f144f6a9524ec52b3b67c97490368f1004056d5c74ca1193bad310` |
| `M ` | `docs/orionis.foundation.config.queue.Redis.html` | `1713407c425d0c44f723e617709323da4bf386d9cad122c922b4b8c6534705b0` |
| `M ` | `docs/orionis.foundation.config.queue.Sync.html` | `9bf6ee00d8dfa703f4835ec916a01d6e600ac3973588cd72c1ad45baec319752` |
| `M ` | `docs/orionis.foundation.config.queue.Worker.html` | `b0bbd6d43cb28a2f0ab8307d431cee138b94973f132c43a33ce7596d184643ad` |
| `M ` | `docs/orionis.foundation.config.queue.entities.connections.html` | `e782c28b3d515e7b7cb143e80dd40b279549aaa078c32ec8d93bcaf9a5d074cc` |
| `M ` | `docs/orionis.foundation.config.queue.entities.database.html` | `53065666b3c70fc19ff0fa1b07fa28f9e658a6b5bd1dd75cfd4a5c62377f6572` |
| `M ` | `docs/orionis.foundation.config.queue.entities.failed.html` | `2fce724ce7bbb5c245fb8263a4f2eef3f4505a86a19ce3600b97e4bc3089f021` |
| `M ` | `docs/orionis.foundation.config.queue.entities.html` | `264e7c99f6eac1acd91ef5ae8714fbc1b842d74c7c5c602fedb32e1f721c47d5` |
| `M ` | `docs/orionis.foundation.config.queue.entities.queue.html` | `2e8f766c631ed0d0c55f3a238041dfe46965cb26392969cdd9aac6377823073a` |
| `M ` | `docs/orionis.foundation.config.queue.entities.redis.html` | `570f21e8f16e447afd7b6a19ceb113f5a75030d0d251d7d818242f7888a0cdf4` |
| `M ` | `docs/orionis.foundation.config.queue.entities.sync.html` | `b5d3504f66be563d3421c81ec10abd8fc4fa9b6db1aadcced18bc1c88ecd42dd` |
| `M ` | `docs/orionis.foundation.config.queue.entities.worker.html` | `0becc27fadec60e883d948f890d24429f6ac4908e6f67c11d7859f96e4f7ca52` |
| `M ` | `docs/orionis.foundation.config.queue.enums.drivers.html` | `7272c496b9cd3a230f4b15fec418f671d00f52a7c1ceeaab61d76cdb9db1d7d9` |
| `M ` | `docs/orionis.foundation.config.queue.enums.drivers.module.html` | `4e25c977e89ac5c3780693cc11c36b0dba1befd06dc811220eca6e0b65c2b2e1` |
| `M ` | `docs/orionis.foundation.config.queue.enums.html` | `d2cd3dd288ec2cebb6d7a91082b4b0c4aee3891be5d1340a084fe37be2c0ec18` |
| `M ` | `docs/orionis.foundation.config.queue.html` | `64a78661c60c137ae2bad09b21b17a1c2a75d21332385205ade54257642d562e` |
| `M ` | `docs/orionis.foundation.config.realtime.entities.html` | `90b469b491e31f17aa2b3cd98baa082b5d7d85b69de34420c80dfd60342b1953` |
| `M ` | `docs/orionis.foundation.config.realtime.entities.realtime.html` | `06b6d390296f1103a633204d3d2bdae0c06f0547af999527ededae80b63960e1` |
| `M ` | `docs/orionis.foundation.config.realtime.html` | `8c3e9f482885ca6a8e41f8be11e1ad6327f22d013861c39f20e4838075564596` |
| `M ` | `docs/orionis.foundation.config.scheduler.Database.html` | `5ba89b77dfb8591e863121150a7c4ea4993e7019e09ac1248541b37a4ff6c234` |
| `M ` | `docs/orionis.foundation.config.scheduler.Memory.html` | `05e9520bf6624fa25f7684b331d34133359c566cc0c3b8b5d92e1eb6e9f0602b` |
| `M ` | `docs/orionis.foundation.config.scheduler.Redis.html` | `2f0d00c60e80a36a4d45dd452cbdaa4675250ee2539274d0e6e655b3eb4954e0` |
| `M ` | `docs/orionis.foundation.config.scheduler.Scheduler.html` | `b6261cc163fff9c3a6f09ca2a60e65ab282a677a8a51e1c47d76e6defd681d63` |
| `M ` | `docs/orionis.foundation.config.scheduler.Stores.html` | `8cc30254dc1ab83066bf37c2f776afccdaafe3dcada3f6c07528c06ef9867c8b` |
| `M ` | `docs/orionis.foundation.config.scheduler.entities.database.html` | `4f9d226461d31b61d4bf8a54bf6d0e23443ef721c3ec87cb483937fe8076ada9` |
| `M ` | `docs/orionis.foundation.config.scheduler.entities.html` | `d1c58361cc558e02fbd7d4e3f67cf10b72204149a557f14b1df56fb80cde548d` |
| `M ` | `docs/orionis.foundation.config.scheduler.entities.memory.html` | `7a1b8ae0008038ce2bc6ead11653ac783aa876eaa723769924d94cc9a3e2abed` |
| `M ` | `docs/orionis.foundation.config.scheduler.entities.redis.html` | `3b4f351a9e4602360964bae99050551c3469fe0e219f12750bafadcccc52e7a4` |
| `M ` | `docs/orionis.foundation.config.scheduler.entities.scheduler.html` | `40c1a97f8145bd830d151c022bfdba8403d19615854e0b8c21458c0f507237ec` |
| `M ` | `docs/orionis.foundation.config.scheduler.entities.stores.html` | `1129303e510f5092706985391aa28cabdc8b65bfe2f7b1cad0ef1470f6b62e04` |
| `M ` | `docs/orionis.foundation.config.scheduler.enums.drivers.html` | `8575eba40af041c315ff873161b69dfd0d469a2d96af24fb484bc983817cc864` |
| `M ` | `docs/orionis.foundation.config.scheduler.enums.drivers.module.html` | `0b3678314057d7440b2783a2fb40746ef7e32c13f904f7d70bda81719e13cd9f` |
| `M ` | `docs/orionis.foundation.config.scheduler.enums.html` | `12cd3dcec3a664bd99f32655ea977af1946e0ed8a4f466f192f66b698d71a7a0` |
| `M ` | `docs/orionis.foundation.config.scheduler.html` | `6cec9d626ed9faeea9e8c3f09fca213a4677003539c389d66d745fc67b341027` |
| `M ` | `docs/orionis.foundation.config.session.Session.html` | `9177a70a85e2106c8955f5a1621f15a975885b25287cf3ec5093375eac7ebf83` |
| `M ` | `docs/orionis.foundation.config.session.SessionDriver.html` | `b96931991dc32b13273a82402fad51e543e0fed75512cc3f4668e3b876c9c0cb` |
| `M ` | `docs/orionis.foundation.config.session.entities.html` | `22670dfe1064be0a52c6a113dfe25f417b140f25ce1e55d1fac2cbb90265c92c` |
| `M ` | `docs/orionis.foundation.config.session.entities.session.html` | `d67fdc0ab2a99ae787467ad64ae948197bea46bb13faa96ebc3ce929c717b989` |
| `M ` | `docs/orionis.foundation.config.session.enums.SameSitePolicy.html` | `5a5cf485e190e5e8b9c22b536d33b6570592747b739a7387852de3fb4944d351` |
| `M ` | `docs/orionis.foundation.config.session.enums.drivers.html` | `4d3957d8837537f83e18ebb644c96536061b401f8ff9cd0995c2aae9d07546e3` |
| `M ` | `docs/orionis.foundation.config.session.enums.html` | `f855f7fd4da4e947cbcbc3aafe2e1a354590bbff586ce5600047cd2c11964b4e` |
| `M ` | `docs/orionis.foundation.config.session.enums.same_site_policy.html` | `012ab541f262b5a8c6ae212b60d64c864b71ad281bddcfebe53eaf8fde0c064d` |
| `M ` | `docs/orionis.foundation.config.session.helpers.html` | `08ce5132170f6bc70a0e94cb06fb2e4d9eae5e2c18c2c39f505fce469f012d3d` |
| `M ` | `docs/orionis.foundation.config.session.helpers.secret_key.SecretKey.html` | `8c62c799613722a844f4ad10f321cdcd9d575c316ce6ab7a87aa3f44a52034a4` |
| `M ` | `docs/orionis.foundation.config.session.helpers.secret_key.html` | `b41125c7fc8d902c4bed530edcc63d9aee2f2ce4c6c67406c070ebcc092b618e` |
| `M ` | `docs/orionis.foundation.config.session.html` | `132c7ce9a168ceadf2591d3f311c9645a1c3647dcb444dbfaa83a86739ca6eae` |
| `M ` | `docs/orionis.foundation.config.startup.Configuration.html` | `b3ad7034a8c8c6a2df6d53885be2d1f4cb3eccae89eefa29bdb72dcd56ba711c` |
| `M ` | `docs/orionis.foundation.config.startup.html` | `99a3680f5cf3890fe9b9beead793db3fc8a36ba80b58e825e7fadee67c93d421` |
| `M ` | `docs/orionis.foundation.config.testing.Testing.html` | `6d3175cb415b7f072c7be466889eeb0f58a23b75ddc7e2f311b44346e16fde3c` |
| `M ` | `docs/orionis.foundation.config.testing.entities.html` | `d8a35e4458ac1a423d5fad348dc4c09f4f51d86853f8036d5237cb7aeb2e4fa4` |
| `M ` | `docs/orionis.foundation.config.testing.entities.testing.html` | `3f1979b0ee6f4635b3619324a9254e64af0d774caffb63122399643946bbce59` |
| `M ` | `docs/orionis.foundation.config.testing.enums.VerbosityMode.html` | `4d174423bcbd492c0396740e7c28e720af544d9f39f25bc2237ace72255ad77f` |
| `M ` | `docs/orionis.foundation.config.testing.enums.html` | `e83028e1c290727e862a9f97c97e741cbffb3fc23bd1a95f2c54c969ab130854` |
| `M ` | `docs/orionis.foundation.config.testing.enums.verbosity.html` | `804f405d1fa732cc7aa8f425c75c616806b4d3e575f5e4cf6ce5062252086f2b` |
| `M ` | `docs/orionis.foundation.config.testing.html` | `52cd59fad39d873e1527e56dcfdfd82f3187ca6e826186eac8ae5e6220392922` |
| `M ` | `docs/orionis.foundation.config.validation.html` | `18e25c301e9c064511289c66f414683c76eb301f413af38ca722cea065c6ba38` |
| `M ` | `docs/orionis.foundation.config.view.View.html` | `dcf77714ba45b190311b41abafe0f645a4d8cc4bfabb90d37f76f333ee7a2253` |
| `M ` | `docs/orionis.foundation.config.view.entities.html` | `48fdb846f32a1a2ebaca00eb704e72c7301f8d766210b10d961017435954960f` |
| `M ` | `docs/orionis.foundation.config.view.entities.view.html` | `520b458c71a71803c5f88a3dd36258cfd76e2b3447197ae2be5f258c67d8cd82` |
| `M ` | `docs/orionis.foundation.config.view.html` | `9860d9b6b27d1b690f488e7704066699110e4df8f864a2508164a39fc14b12a3` |
| `M ` | `docs/orionis.foundation.contracts.application.html` | `b5493d126275159aeb8fc21e1a9fc61e4d2906cdfcf14e1ffcac102542a426f0` |
| `M ` | `docs/orionis.foundation.contracts.directory.IDirectory.html` | `b18e5831ece81acbe98035babef3057299a127821232cf1c0521b71ab7c7f8a9` |
| `M ` | `docs/orionis.foundation.contracts.directory.html` | `f242fded91d091329763a3633633365952374a4a8ebc19c1a3db4eb96861eaf6` |
| `M ` | `docs/orionis.foundation.contracts.html` | `767cef8da2b274603b530cbd949cbe4d33ad41a56af050dfa262cf6bb888daa6` |
| `M ` | `docs/orionis.foundation.core_config.html` | `b63619b988140a441e3f89ba018bea21d7af2d5fff4adcd76337c68e3e234ab9` |
| `M ` | `docs/orionis.foundation.core_exception_handler.html` | `0eea0c00f8969893a4e7acc85ea4cc9fb6c7922c8858f24acccda1d47a7485da` |
| `M ` | `docs/orionis.foundation.core_kernels.html` | `e031b9754afe3920a497e72680e1eed6fffc3b8587331510b945d3fc996948f0` |
| `M ` | `docs/orionis.foundation.core_paths.html` | `b45ce1aee7fe94023ec8febcc6e86740803824de7d43230f491b9c35cbac8dfe` |
| `M ` | `docs/orionis.foundation.core_providers.html` | `305cce2c0a51e8ef9de9db30cee0fed9b6430a8dad0b66faa6be17a727037930` |
| `M ` | `docs/orionis.foundation.core_scheduler.html` | `cb1afa905dc370dc5637eff2adbd400e50ffb44cfadc73bfe5e85f83c8c2b972` |
| `M ` | `docs/orionis.foundation.directory.Directory.html` | `e8d41692826efbae7a2030306efb6915e112a4de3472ce50d9b67a4a2638bd36` |
| `M ` | `docs/orionis.foundation.directory.html` | `f3dc6a8fc292ebfb83688777e8b2b62d1fb21fe6da84d16e478c0e7a2bd8113f` |
| `M ` | `docs/orionis.foundation.enums.Runtime.html` | `151455171b4a9ee564ec8dd8ebccef7e975e23f03bcd9b4ed6d1862442ac79cc` |
| `M ` | `docs/orionis.foundation.enums.html` | `1bdc68decd46446321cd7c133eeedd5944f550eb7f1b1d440b11f988a4d4df02` |
| `M ` | `docs/orionis.foundation.enums.lifespan.html` | `cfc7030820e7f5f52eed5913078cdaa5996bd82e16f4217c6daa65a0fd81a420` |
| `M ` | `docs/orionis.foundation.enums.lifespan.module.html` | `d237ad408d98ec5a227713a80031be02450185601e23f10cee39aa45f9022dd6` |
| `M ` | `docs/orionis.foundation.enums.runtimes.html` | `12afb85c7796124f2b85fadc64942befcf1c01056b4012f713374ccb7d7e1357` |
| `M ` | `docs/orionis.foundation.html` | `eb2368099828f7156acb3491cf9a724cb678306473945013b4149a9a6d87b44c` |
| `M ` | `docs/orionis.foundation.lifespan.html` | `78918429e64dd9a0c0d9ce8ae53de26721d8c4b1bbd5915376e3cb93781360cb` |
| `M ` | `docs/orionis.foundation.lifespan.shutdown.html` | `ea079483a512682763fc675140745fd1b28fedc6f224c69a883f998d8d523508` |
| `M ` | `docs/orionis.foundation.lifespan.startup.html` | `8c8ca7790c6ae88b87bccf3a9906a87dfe38429397363e31116269cfb4912fcd` |
| `M ` | `docs/orionis.hashing.HashManager.html` | `730bf03f48757fe3da3d2fd501328114f364377ebf4b176226606ba1c87b4f45` |
| `M ` | `docs/orionis.hashing.contracts.IHashManager.html` | `ebe699d18aa0b3e73b85544e01b66dfa31fd8aa7082ba532652f4cee38c605a4` |
| `M ` | `docs/orionis.hashing.contracts.IHasher.html` | `5fc233b9cb47240269abfd292fca20ed1f37f11796e5eb81abd5449ffa18d747` |
| `M ` | `docs/orionis.hashing.contracts.hash_manager.html` | `ac8ac6ef0f31bf82da8ef5a8a9d91e43090b9d20d45b8e0653139486bb6d462d` |
| `M ` | `docs/orionis.hashing.contracts.hasher.html` | `becf1672fda12ce2102d4bf14df2373d57b6857544d2e3cb9a4756346056217f` |
| `M ` | `docs/orionis.hashing.contracts.html` | `1b885cccd393bd378461d405d50dc57e63666a38c66ed62422b96cd197fbfd91` |
| `M ` | `docs/orionis.hashing.exceptions.HashConfigurationException.html` | `5aa54566986f0e4591db6edf0147ecf941e3c6e7408d7bbbadfbf6a78117f107` |
| `M ` | `docs/orionis.hashing.exceptions.HashDriverNotSupportedException.html` | `abef3e5f092543be10ba5a5988a881cf368609a45a4c5c74e935e16aa4cb27a1` |
| `M ` | `docs/orionis.hashing.exceptions.HashException.html` | `cedfda4fe9c9748558a641b35047fa5fff39cd9ff59f10289618c7a2269ce66a` |
| `M ` | `docs/orionis.hashing.exceptions.MissingHashDependencyException.html` | `13cd1210fba6606f469089bd5e2c2bf5d59994262e8e9efacfd79001d343f122` |
| `M ` | `docs/orionis.hashing.exceptions.html` | `9dd0c17002afa5969bfb6dd8c163d285d900fcf30f2c7f10dd6e36a32074b7b6` |
| `M ` | `docs/orionis.hashing.execution.html` | `4cc61a9be6cd7b711324ef30a70c34798f886503ff42bc4bc10697c112d17f2b` |
| `M ` | `docs/orionis.hashing.hash_manager.html` | `3dde3297d1fffe03717a62e58eabf91bbcc41cbc64afbc5897dd9dde670757fd` |
| `M ` | `docs/orionis.hashing.hashers.Argon2Hasher.html` | `ac304c29f7469e787b1ec07ccfae257ee8c54965ffe899598fb996f1131a0147` |
| `M ` | `docs/orionis.hashing.hashers.BcryptHasher.html` | `8ddc88761cfdd985bd2eb6077b962af5882b020431ee162ab0247469c7ab3b2d` |
| `M ` | `docs/orionis.hashing.hashers.argon2_hasher.html` | `2c7b276c25431094d97d304b2f62ae4b5c696fa7233967fc77c76d7c15f00936` |
| `M ` | `docs/orionis.hashing.hashers.bcrypt_hasher.html` | `c324c5e817152bac4568ed5055045a87a5fa0f9d3432343b2507f6171cda2a7f` |
| `M ` | `docs/orionis.hashing.hashers.functions.html` | `bc2f4bc9d65c11df9a679402e5a40d6dd17f5a5a18fb894aba86fa44a4197ce4` |
| `M ` | `docs/orionis.hashing.hashers.html` | `c89b5ec055784f472fb1f294675291a67bdbd327faf7620d34d20b3fb0e70d89` |
| `M ` | `docs/orionis.hashing.html` | `0333d42a0c87e2e603c45c8ba57a6ded1b528d142c826de72f7dc8c04e77b090` |
| `M ` | `docs/orionis.hashing.provider.HashProvider.html` | `ed27df074c6a91736d9fe0a3112efe584cc5cf4eacacc6077c65186593164312` |
| `M ` | `docs/orionis.hashing.provider.html` | `2e63c95af60431811a2d69720356acf8bd2aa8f2765221e38b4b651946721fcd` |
| `M ` | `docs/orionis.html` | `f30f0ba373a239c21f8f934069bb3eaeb3012b78bb98fae34324cc8a6da12822` |
| `M ` | `docs/orionis.http.BaseMiddleware.html` | `3ebb9d3294bf79fe463ea7d9c8ddaf9e0bd76baf5aad6b0100ee7afe91f726a4` |
| `M ` | `docs/orionis.http.EventStreamResponse.html` | `8a5f7e7d1a2a478daa5a2763a34087cae14a8c570cf1353a6c4e0fa0c4bb656f` |
| `M ` | `docs/orionis.http.FileResponse.html` | `de0054382b9f2f8f628570bb4598aaa04f8e9d6e603d2d9bb5fc569ea811c56d` |
| `M ` | `docs/orionis.http.HTMLResponse.html` | `64d1eb8c0040bdd90fe117e66ce00a0fd80a533db317d1a7f0447b7a27763c90` |
| `M ` | `docs/orionis.http.JSONResponse.html` | `6278e778fd7ee2106a06708bb5d37b5ea5ba6049d48ae440494f2e43ee65c54f` |
| `M ` | `docs/orionis.http.PlainTextResponse.html` | `f521a240472fb8d4eb79d87f330c5b242efa9aca047aaa7d5f713872d9016ae3` |
| `M ` | `docs/orionis.http.RedirectResponse.html` | `844674584e9fc70c9f35b6c65897df02d1c809bac43cd7a1d92caf8bc4110e09` |
| `M ` | `docs/orionis.http.Response.html` | `38d45e1786a4a5bf0b00e76091ef9b0a2df6fce7a1baa01a8e712961760a9299` |
| `M ` | `docs/orionis.http.ResponseFactory.html` | `8e575e013be4df702b05fefbb3fc9a3534fee57ad634fb091dd4d1a75c4d9829` |
| `M ` | `docs/orionis.http.ResponseTemplate.html` | `b699d836eb54c82eb40efcdbcc6908dec70237d06f38cc531db1ff23000abd1f` |
| `M ` | `docs/orionis.http.ServerSentEvent.html` | `5709384ee23a9d69eb44235917ae204d6168d31c88a7b796e3d3ff75e8974ce3` |
| `M ` | `docs/orionis.http.StreamingResponse.html` | `8f50e66f41500e033bff65d6124cf3822b9029504fe6243104d52e57731593a8` |
| `M ` | `docs/orionis.http.WebSocketDisconnected.html` | `d45f8dd15f2dbda332ebe732d58bdaf9138ea409dcbda966cd6b56a544657cbe` |
| `M ` | `docs/orionis.http.WebSocketMessage.html` | `195d17b85e6291272aed5fba4013843efe95420f4629b0636dce8f519a12565c` |
| `M ` | `docs/orionis.http.WebSocketMessageType.html` | `a747099dbf8fd25a19ce736bce7aa057067eee9454aa7c7820807799c0cff004` |
| `M ` | `docs/orionis.http.WebSocketMiddleware.html` | `7085b1c6104e1d20cbc5b9e15b5c831409bdcd340fa4d5650f65b5d12f166068` |
| `M ` | `docs/orionis.http.WebSocketState.html` | `ab9a62fc44a3530ac2b053e3a37400121fc576d945a4e0e3d9e0cc3ce6e0c3eb` |
| `M ` | `docs/orionis.http.adapters.html` | `79ed0047ed17268ae50bd9a12cb2e00c99002dc121537c0b6ddc1fcc955b4c50` |
| `M ` | `docs/orionis.http.adapters.request.asgi.ASGITransportAdapter.html` | `061e7457d8aa0a43297ef5b014c8633efb53fa8c5eac928955112cca8e77f22e` |
| `M ` | `docs/orionis.http.adapters.request.asgi.html` | `6b50163fb60b32a170ac73db5fe2b248c8563cd0049df7a0a1fbb51829b9295b` |
| `M ` | `docs/orionis.http.adapters.request.contracts.html` | `a32ee8edb7b72b0266fc4100ea340e2470a5cd3ef9a0a9311887969605ed4659` |
| `M ` | `docs/orionis.http.adapters.request.contracts.transport.TransportAdapter.html` | `c4f82f8d9d57108106998acf15cc82b90603b9e11a34656f4e8e381c3ef6627e` |
| `M ` | `docs/orionis.http.adapters.request.contracts.transport.html` | `a4270857adda3b7c147acf6654b7d37e5537e3c897c7e635ff3a8e7949b6f6d5` |
| `M ` | `docs/orionis.http.adapters.request.html` | `002afc8e5612aebf0cff1a6edea2e7ec8dc2b58f5ea9510d3effec075e327d2b` |
| `M ` | `docs/orionis.http.adapters.request.rsgi.RSGITransportAdapter.html` | `1f0dd52e0f5d284df81e8fbc8164912c55a3db8e8c705bbbe57c79f3ce337ba9` |
| `M ` | `docs/orionis.http.adapters.request.rsgi.html` | `a8d3014099e8b1ee60e5695ec732fbf4adacd3d23df0b43d199208624d2afff8` |
| `M ` | `docs/orionis.http.adapters.response.asgi.ASGIResponseAdapter.html` | `5defa3153b78df593e2f1ac3d8f036035ce7f0f0bd039a1455ab0b10569cec45` |
| `M ` | `docs/orionis.http.adapters.response.asgi.html` | `bfc7de0a196365fa25dc762caa6b24418f5028eb4a5bf026b4497b195c53dcca` |
| `M ` | `docs/orionis.http.adapters.response.contracts.html` | `3e4a8ffacd5851cd56b3c2f023b54e05b4a4c51020342ac049a6e23e15901fa7` |
| `M ` | `docs/orionis.http.adapters.response.contracts.response.ResponseAdapter.html` | `7f59735d72ae9797869a0c99f43344a6ef7dc3916fd8bc31d7aeb39370bd4d82` |
| `M ` | `docs/orionis.http.adapters.response.contracts.response.html` | `a9970ab76090afe9580e62b1c91f24674ac23565f2a09106ce268e6fc0e9ff31` |
| `M ` | `docs/orionis.http.adapters.response.files.html` | `a34e10516eac28d308c04191a968b0c4097bb990ec3f30424e19f47c22aabff0` |
| `M ` | `docs/orionis.http.adapters.response.html` | `260b9eb3dd50fdded8e209657c942559cc2a4f57a4c9aa3a4a8297688a518811` |
| `M ` | `docs/orionis.http.adapters.response.ranges.html` | `78faf7b853c621e2aeb1ee84e4a6bb3e133ae0d883374d95b814ae7dce20d35d` |
| `M ` | `docs/orionis.http.adapters.response.rsgi.RSGIResponseAdapter.html` | `153d5a24fdc29c3cba7d0893a3bde4a5cd1a19a3038f9ebe23f0fe873b79706c` |
| `M ` | `docs/orionis.http.adapters.response.rsgi.html` | `597bff9955c5db0f17145c2ea18223ac1fbae903763ccdb29bb5b4347f949b6a` |
| `M ` | `docs/orionis.http.adapters.response.streams.html` | `aa05617958b3a606370dac6d74e34ac20e027456c9eaa6b305e9d84e87c57b32` |
| `M ` | `docs/orionis.http.adapters.websocket.asgi.ASGIWebSocketTransport.html` | `73ee406734a8408be03aa39bd462021d85c7294a4c5dfa136d1026cdab2ac5b4` |
| `M ` | `docs/orionis.http.adapters.websocket.asgi.html` | `fede303205ff8ff2dc917c5dac811ccd2269a0ae708528f0e334c67cecabd4ee` |
| `M ` | `docs/orionis.http.adapters.websocket.contracts.html` | `eb265f5103b94243ea870fd07b2462031db6a2c0414193bb8e01004816617219` |
| `M ` | `docs/orionis.http.adapters.websocket.contracts.transport.IWebSocketTransport.html` | `4ce5f3dd99df49e1c8c0a68c6224b1c51823d7c3b44b40e9fc08cb6708e79f95` |
| `M ` | `docs/orionis.http.adapters.websocket.contracts.transport.html` | `383a24a55f32489cb4e2798acfbe2ed35449517043a53c37d0d5ab0ea4696c17` |
| `M ` | `docs/orionis.http.adapters.websocket.failure.html` | `192a97303485f8b7d657e72f2c130f8a8342c682af08480201e6af89133c02a9` |
| `M ` | `docs/orionis.http.adapters.websocket.html` | `5b44d16edd681260a186c65c8cd482330248616dfff8ef2dca9879808cb0b46f` |
| `M ` | `docs/orionis.http.adapters.websocket.rsgi.RSGIWebSocketTransport.html` | `048906054bda343b49e16bb92524b789d2d6adcd7a92a25f3b7d118d63de0c6c` |
| `M ` | `docs/orionis.http.adapters.websocket.rsgi.html` | `42358988def481c5c210875ceb9a32fec49ee914276e77df0c2a30e60866d1df` |
| `M ` | `docs/orionis.http.base.BaseController.html` | `e7c5d073c3075dbbafd74d6facd687c0d4519d96a260cd5d6f79a664d7b26dce` |
| `M ` | `docs/orionis.http.base.controller.html` | `e2fcd99c70e6c85eee4546be5823bf912ee3c33671de0cbe78239d2462326199` |
| `M ` | `docs/orionis.http.base.html` | `b727a6e51ae8b70fce6f01affe6ea7104a956a6cbdf29666326c67158b229378` |
| `M ` | `docs/orionis.http.contracts.endpoint_policy.IHttpEndpointPolicy.html` | `c710ce2391f05abe662795077e4e9e921c00fcedc4edb46d8f080c26e9c902e4` |
| `M ` | `docs/orionis.http.contracts.endpoint_policy.html` | `3af1d6416ef652f3ea928a1c4613e3368704638a7f562b3d4afa8a7a9f0a3b10` |
| `M ` | `docs/orionis.http.contracts.html` | `48a9bd8f6676b7104e148d26604d84fcaa7601798854321043edf9cca2c6428f` |
| `M ` | `docs/orionis.http.contracts.kernel.IKernelHTTP.html` | `e000058f89e6afdb2e785a7aa9177b5107ce1ef62dbddd1366a0ebe8be003dc6` |
| `M ` | `docs/orionis.http.contracts.kernel.html` | `ad909a35bcf5261cbd566e011132446ba3f9981325915e47287631f547c17d38` |
| `M ` | `docs/orionis.http.contracts.request.IRequest.html` | `80ae8a0244ffade881320c5a0f07171c3b5b577addd90c61c7e623da912d06ff` |
| `M ` | `docs/orionis.http.contracts.request.html` | `c57fab2d03a8f6c4a1db8b390458f57963679dc72a2464ff7a6aaf2fe9e1ce60` |
| `M ` | `docs/orionis.http.contracts.response.IResponse.html` | `1ad67d2ec0bfaf92db6cd2fccb218b8023a64dd185a4c897f86522561b80b499` |
| `M ` | `docs/orionis.http.contracts.response.html` | `36c172b43d1ba4c8a89778c5e46d5f39c197f768cbbe3d620596cedd36f04107` |
| `M ` | `docs/orionis.http.default.assistance.html` | `5cb8a3900469c39037cf6aaa2f10faf9d57ee94eba3843d70e101b95b5946510` |
| `M ` | `docs/orionis.http.default.contracts.html` | `8a20285f2cec3791a89ea3a60702e98dba5087b2de81f5b41d400cccd308b3a0` |
| `M ` | `docs/orionis.http.default.contracts.responses.IDefaultResponses.html` | `fa276ced5f201b5e746e82589f90239ed804a15a849e9d5d1a707e1d231d6ece` |
| `M ` | `docs/orionis.http.default.contracts.responses.html` | `a5c00d1749dd998d8926cbc72c897ccd21f278022650b853d188fc5e98dcf3d9` |
| `M ` | `docs/orionis.http.default.controllers.forgot_password_controller.ForgotPasswordController.html` | `830d1bb9b861c9ea44cc7dc69b73c051d879b9729cabcb33ae60d9394f869068` |
| `M ` | `docs/orionis.http.default.controllers.forgot_password_controller.html` | `cf8a6416c46c37633049de240e156ee1e6856f2b6eac9215af733a01277bf9bc` |
| `M ` | `docs/orionis.http.default.controllers.html` | `591b33105cc7a2eeb2f0d76a1170219b9c4176f3eb49789cac203cd94977b7e9` |
| `M ` | `docs/orionis.http.default.controllers.login_controller.LoginController.html` | `22dd8f3f5cd97ca3103973289351561101a51c5ea28f6179cf864fe389805a4a` |
| `M ` | `docs/orionis.http.default.controllers.login_controller.html` | `b8e2b1eb23eece85ea5b724e7807bf43eba65ea1fb4b400eb2035fd8aa80e722` |
| `M ` | `docs/orionis.http.default.controllers.profile_controller.ProfileController.html` | `99ffe42d3347c54cc0b2df2a5083fa2cc73e14bfc073feab78c7d09c1391c03e` |
| `M ` | `docs/orionis.http.default.controllers.profile_controller.html` | `b67c3b9efa2f89a59719cfc96471e3b56a27db9f0438e8570b16e9da25a6b3c8` |
| `M ` | `docs/orionis.http.default.controllers.register_controller.RegisterController.html` | `d247b8213d2f4301f11855dfa4246b8c3181872453de2d2093577b172b1a0622` |
| `M ` | `docs/orionis.http.default.controllers.register_controller.html` | `d614d24514c4d3af15daf2c6c1a49c59f27d9480f33e68b71c4e98966ff557ea` |
| `M ` | `docs/orionis.http.default.html` | `ad2fe50e9f450eaed805d37da1721bf0a47d5d6cc1be59b34bb20d8ff5448469` |
| `M ` | `docs/orionis.http.default.responses.DefaultResponses.html` | `e20ff9bb40bc06dac8c0c3c05c8e0361350989ef77c024d0d9f149dac51efc0d` |
| `M ` | `docs/orionis.http.default.responses.html` | `db7f92d5371e57e56d147d0dc024050175a5df0a1f58901eaed8f6b8f6f829b8` |
| `M ` | `docs/orionis.http.default.schemas.change_password.ChangePasswordSchema.html` | `8bf2c06daa5aa71ac7fefe413a9a28f20e324ff5046262e91d952026f66a9e21` |
| `M ` | `docs/orionis.http.default.schemas.change_password.html` | `fb12d03753ab790ae7cb3290f7874ee486838e79fe4af682a2e7e2ed730a6463` |
| `M ` | `docs/orionis.http.default.schemas.forgot_password.ForgotPasswordSchema.html` | `db4d92e33ada27148259c43e197609b4116f0b2624742209b86b4c267d8178c0` |
| `M ` | `docs/orionis.http.default.schemas.forgot_password.html` | `c922a055760efea92d46334518fcfbc50bf66e865f88128e397de0335fc218a3` |
| `M ` | `docs/orionis.http.default.schemas.html` | `3aab060e563e435fb869cb7df3dccf35ecffbf0f72de1cc5f248c4a79b3b2dbe` |
| `M ` | `docs/orionis.http.default.schemas.login.LoginSchema.html` | `7eba5a6fbf63c05bc50cfad138169799e19e1337ca3e76570ea71b40894494c8` |
| `M ` | `docs/orionis.http.default.schemas.login.html` | `db0036a201ec0c0d80a3322c97152b37115980f3c5769ee083ad967f52aab2ad` |
| `M ` | `docs/orionis.http.default.schemas.register.RegisterSchema.html` | `1215f6a838df77c030fbf08c8d61cef1219aa1ef3937f101d3aaa56634156587` |
| `M ` | `docs/orionis.http.default.schemas.register.html` | `f8141df6abe3db103eef03cb8e22cb6bf4d0f973bc9e0a64db72afe4033981ea` |
| `M ` | `docs/orionis.http.default.schemas.reset_password.ResetPasswordSchema.html` | `c818c1be0a049fd6fdab8c048a7b05c1e8926985cd3e011f89634674a479aadd` |
| `M ` | `docs/orionis.http.default.schemas.reset_password.html` | `c5d9be9f9282feae27977b282a7c23879fa3b827b33fe6ed0f792954782f5b42` |
| `M ` | `docs/orionis.http.enums.HTTPStatus.html` | `aae2b5a5a5d7cf11da48965134a17367e0c19f9ce634eab4a8fbd173e74c30d7` |
| `M ` | `docs/orionis.http.enums.Interface.html` | `5fca622a2672a1ba089c4e5ad69e1a030de23eec0c1962cb11e02669dee7f0b2` |
| `M ` | `docs/orionis.http.enums.WebSocketStatus.html` | `b421a6a98d7bff621bc7bbc118ee449d33334b65e211a435fcf83d834c08d8d3` |
| `M ` | `docs/orionis.http.enums.html` | `2212e278687477e17f43458b676361113a8d7a32223a03d47b42415a388173c1` |
| `M ` | `docs/orionis.http.enums.interfaces.html` | `e1ab283f8a49260b5c79961a3541a2fc5785271147ac9e0a1c9da6199d0587e1` |
| `M ` | `docs/orionis.http.enums.status.html` | `1e28c3fb3a0cf66d60b5412f6e9591143a3487dc213787fdc4b69666fd452de3` |
| `M ` | `docs/orionis.http.exceptions.html` | `46d97819ea9c4ca1437790e333db9bc01dd7d88866e03d9b2b7f5eee85410626` |
| `M ` | `docs/orionis.http.exceptions.response_validation.ResponseValidationException.html` | `17bca5e4f7b61628dd3a5c6ced486f99cd2a659ed45f81a04f3735af275a1877` |
| `M ` | `docs/orionis.http.exceptions.response_validation.html` | `42ed134510d7efff1d9b36db6e8f44913d845cd145507d9107ae923fa0a3ff27` |
| `M ` | `docs/orionis.http.exceptions.websocket.html` | `08485e5110d11216ba3c15b577b0c59569f42273ac1cfca6eae547bfe415d88b` |
| `M ` | `docs/orionis.http.factory.html` | `bc56c726f60a639b2e6072674696e701008bef70f77445641f13a17840fd17d6` |
| `M ` | `docs/orionis.http.html` | `3196e405fdd521a3489cfb951e193194d641fc8ff4d901227631bf398fa06c0c` |
| `M ` | `docs/orionis.http.kernel.KernelHTTP.html` | `43b1bc7fda76c7c6e7eee81fef9feada8bbda2f4f3284ec2f8070d7d14fdc475` |
| `M ` | `docs/orionis.http.kernel._MiddlewareNext.html` | `d9385ae2a5fbad553019758469df2eabcc7d5f253af9285f65cbc34f2fa2e482` |
| `M ` | `docs/orionis.http.kernel._MiddlewarePipeline.html` | `4e6b03b4396b4ca5eefe8a3fb38f072c5e4e63933cbff234925704ebbe451cec` |
| `M ` | `docs/orionis.http.kernel.html` | `2e8410342ded9379311deb25b306c3b020e050a16c8ac3bf2fe59e88b714de63` |
| `M ` | `docs/orionis.http.layer.api.html` | `27b29a08511f4f458144503919108379dd3f5fb2e6f1e98c74a57e6b9db6f2c5` |
| `M ` | `docs/orionis.http.layer.contracts.html` | `f909ebefd0caf4da492d6dbfe176c2393b11c8e7eaa63366d2d925398d7bc804` |
| `M ` | `docs/orionis.http.layer.contracts.middleware.IBaseMiddleware.html` | `ee93c22242c624298a6a862d5cdf9ba95b60bed1b694ae8fc5f1c3c2a6f3deca` |
| `M ` | `docs/orionis.http.layer.contracts.middleware.html` | `eddd6268686de338cc719c8b507cf8f8b03fea7063da8a2334db18421865bc7f` |
| `M ` | `docs/orionis.http.layer.html` | `d67fbcd0f8f23b0a96c08951866590b0c201b68ac85f6b0e5824fe3afffed9e0` |
| `M ` | `docs/orionis.http.layer.shared.cors.CORSException.html` | `cd0d2cd0982402494e0d3481bdf47ebdc26589512fc3ad093816031b270a75ac` |
| `M ` | `docs/orionis.http.layer.shared.cors.CORSMiddleware.html` | `7cc0cea6d9e13d5126b414cbedcb8831b10231f7967bce42fabf19b9f7967c47` |
| `M ` | `docs/orionis.http.layer.shared.cors.html` | `fc1d36783b3d1ae8202182bccaea897908ab46f423dc4591ea0933c4ed5fbac2` |
| `M ` | `docs/orionis.http.layer.shared.html` | `b2d81c2a970deffdfa1963ad279f7545d34f4a6df7e866bb99c974f5b295acdd` |
| `M ` | `docs/orionis.http.layer.shared.maintenance.UnderMaintenanceMiddleware.html` | `7b4227aa6092c792804e286d704a422ebb8a2e4f8d9f5eb5d7ef17f42e26859a` |
| `M ` | `docs/orionis.http.layer.shared.maintenance.html` | `50178e6d3ccf0c36b004b0cfcdd47c869c216a3fdb19a5164be544a55e04e772` |
| `M ` | `docs/orionis.http.layer.shared.proxies.ProxiesMiddleware.html` | `da88412cccda0ca1896d46314a0b672b6427478dcb93c049daff8245ba8225dc` |
| `M ` | `docs/orionis.http.layer.shared.proxies.html` | `446c8f2de0978a2bcb2d3dc5b84801cd5a0b2b1afda271b8f9304a416c46ca6f` |
| `M ` | `docs/orionis.http.layer.shared.rate_limit.RateLimitMiddleware.html` | `184b1831dd583be6d002abbf2d63ff7f6bceacd7a7e1d0d2fbe49b1f1ffb95e3` |
| `M ` | `docs/orionis.http.layer.shared.rate_limit.html` | `3f028e4a094a713a98b00aabcb52341cb0ff0df8977935f1e10757006207456e` |
| `M ` | `docs/orionis.http.layer.shared.security.SecurityMiddleware.html` | `a83acda78f39b691cfaf35852aafc2ce0744ca6d56e77095a4e63a92d0389542` |
| `M ` | `docs/orionis.http.layer.shared.security.html` | `5e9aa5124a51a4f2418fac1c5ec25cb44e82df04b9e0198d63bf6745066fd391` |
| `M ` | `docs/orionis.http.layer.store.html` | `bac0e6607e1e3d8b0e5aa4e2dd1757984cefd616d326595b84664a420681c643` |
| `M ` | `docs/orionis.http.layer.store.memory_rate_limit.MemoryRateLimitStore.html` | `830dd065a44eafb964f39d9d13c20e4f64b49587db2726ea516ac5f99f2136fe` |
| `M ` | `docs/orionis.http.layer.store.memory_rate_limit._RateLimitBucket.html` | `64b5d9ff5272a0c982c878295fc1273aef486475b3315f5b9b5491826690a41d` |
| `M ` | `docs/orionis.http.layer.store.memory_rate_limit.html` | `efae0b68e3f1c369b97a4d9af5900f04d9e4b17f4bb0005c168ef375e7e76847` |
| `M ` | `docs/orionis.http.layer.store.redis_rate_limit.RedisRateLimitStore.html` | `e6b8e81823eb1d6aaf28379596708d36c985b5cccd8b090b76bd6b4a72048d04` |
| `M ` | `docs/orionis.http.layer.store.redis_rate_limit.html` | `71e479916b2f507eaea951a6a5ea8d4d9b20cc663b5cede47d49ca4194b4c4dc` |
| `M ` | `docs/orionis.http.layer.web.csrf_token.CSRFTokenMiddleware.html` | `1f3b88ee2efc5da7c9aa0ecf4f5fa7ef9897482147d9ece40d8f6974717791fc` |
| `M ` | `docs/orionis.http.layer.web.csrf_token.html` | `4034476733d2a3608558750414f709e0050dcff5cf116ed5dc459246063e74be` |
| `M ` | `docs/orionis.http.layer.web.exceptions.CSRFTokenMismatchException.html` | `8e88a6067cb999b5dfa6b10b31a306e84e8aacac9c9d926ca5b5ba5ca21333fa` |
| `M ` | `docs/orionis.http.layer.web.exceptions.html` | `f818c8b80c4d7ce507ccf7a62fd118490ab007f8c24b893e416be026ed5fc44d` |
| `M ` | `docs/orionis.http.layer.web.html` | `0ba6e2ada7a8b00f64e855fcebc58f64c8e31fd0fce57fc69ecfe0818390eaab` |
| `M ` | `docs/orionis.http.layer.web.start_session.StartSessionMiddleware.html` | `b77220c8b10457192dbe35461fdd6367e95efadf7b2f8ac477d80cb3fdf86117` |
| `M ` | `docs/orionis.http.layer.web.start_session.html` | `277dd97e44e198191eb7c4be4aa6d54caf8fa0d183e5ce702c331975e855640c` |
| `M ` | `docs/orionis.http.middleware.html` | `f7f5c0f2bb7c8daa3eee161a42e2411ab46f1019bb7ce385e658ffac06d85aff` |
| `M ` | `docs/orionis.http.payload.body.BodyStream.html` | `55710065e780ad333065c8eb3e806148846c5e75bb8ce002e9798f59de6748a5` |
| `M ` | `docs/orionis.http.payload.body.PayloadTooLargeException.html` | `54c63caf78d7cb0456885c2a1c2975c186eff14923e715dc6969695e240be759` |
| `M ` | `docs/orionis.http.payload.body.html` | `8628c12601e33d9a1ebf7f8f969b7486e952420344710265bbdbef4458f85300` |
| `M ` | `docs/orionis.http.payload.contracts.body_stream.IBodyStream.html` | `3547aad5ae99fa72a8a69e3a8a446c4dc8adad67be554531752b48af75569865` |
| `M ` | `docs/orionis.http.payload.contracts.body_stream.html` | `f10eda1456784fa6ea8ebde1e3819a26b0aa7b4563eeb9f38db19b601ec75e69` |
| `M ` | `docs/orionis.http.payload.contracts.form_data.IFormData.html` | `b7f1520989758d361e9fb90c9c49bcf5c9eb4953ee1116952adf4ac5e41ff641` |
| `M ` | `docs/orionis.http.payload.contracts.form_data.html` | `f019c07d35e8d91491624f676d06b4d70d6777f19c766e3a2b4a09faffbece81` |
| `M ` | `docs/orionis.http.payload.contracts.html` | `8afe20df35f13366d6cbf31ce82a2719fe09aa96d21d3eda14bb17a1a985b665` |
| `M ` | `docs/orionis.http.payload.contracts.media_types.IMediaTypeRegistry.html` | `603c9f51dc4135fbcd0b3f8dc9a897b5b342579e163549d7bf30772474a22c0f` |
| `M ` | `docs/orionis.http.payload.contracts.media_types.html` | `94a51100290443d6da31140241cb6198ce4fd8d965cebc809087698ccdaafe6e` |
| `M ` | `docs/orionis.http.payload.contracts.part.IMultipartPart.html` | `0fdd8cfff364c5eae7657b15b040a8701394cfeedbd33b98aee34853faebbe47` |
| `M ` | `docs/orionis.http.payload.contracts.part.html` | `37182d9bd15615c1442dfa9fba86b78526a9167eeb6d7388fb4bad2f75cef5e5` |
| `M ` | `docs/orionis.http.payload.contracts.stream_parser.IMultipartStreamParser.html` | `899c432182ce5f5d45ffb4ccdfbc3326640fbbcd85dbf9d2053c8fb8e0e63da1` |
| `M ` | `docs/orionis.http.payload.contracts.stream_parser.html` | `85b04b8bdcf1f32e38a3172944b0a079248473bef816e04a0ca0cf1ce7182af1` |
| `M ` | `docs/orionis.http.payload.contracts.uploaded_file.IUploadedFile.html` | `5afe310e47b40d997dbc3ef5aedbbd7750422b36cbe6a653bfd8d494601b0c43` |
| `M ` | `docs/orionis.http.payload.contracts.uploaded_file.html` | `2b5410e0d1b63f7a08ac09f4a57dae302fd56650fc885e3edb4b9961b1761cda` |
| `M ` | `docs/orionis.http.payload.estructures.cookies.Cookies.html` | `b823a2d6942cc9cc1be51e7de399ca52bae6b6bd1d833a9936fe05364fdc0cba` |
| `M ` | `docs/orionis.http.payload.estructures.cookies.html` | `3f6cdf6601c46d8c0e33fff9f942b3c1b1f402e27eae14e99cfb874ebe921e8d` |
| `M ` | `docs/orionis.http.payload.estructures.headers.Headers.html` | `9db02d24297dea61d239790f2eef3861fd7e1792c55bf25fb455e505af15a4c0` |
| `M ` | `docs/orionis.http.payload.estructures.headers.html` | `7d698daa8c072197b0738f0192e755b1cdb6eec46260e8898be1a959805fdfcf` |
| `M ` | `docs/orionis.http.payload.estructures.html` | `a6dd8adf129c64161f365396891fc823a426b691699e03e756eee143a66c2153` |
| `M ` | `docs/orionis.http.payload.estructures.query_params.QueryParams.html` | `75e0efcfa6c95f6181c35f8fa7cc6be80c989b76304361a9856411ec70657a3b` |
| `M ` | `docs/orionis.http.payload.estructures.query_params.html` | `5423e7930f582a4d5ba34cf8927d30cc459a177285d5f0d264c9e8bf6857182f` |
| `M ` | `docs/orionis.http.payload.form_data.FormData.html` | `712b0f2f5c98e1f0e458ac4bcd97cfe78df86d9be98efaa8d4bb68438ba89f00` |
| `M ` | `docs/orionis.http.payload.form_data.html` | `0e1a1c64e78acfa8cd85428689b95f80911e6696c103c302abf0ecb83c9efda7` |
| `M ` | `docs/orionis.http.payload.html` | `13b95c7a6768e23bcd2ca592d745223e9a66ee281e467c36396f8e282de517f5` |
| `M ` | `docs/orionis.http.payload.media_types.MediaTypeRegistry.html` | `2cc7a62a008c694399c7e22ab34182127078070b07351dfc3b37a49eefab97a2` |
| `M ` | `docs/orionis.http.payload.media_types.html` | `8bc5987099736c495dc0cd60d737664c733ea752f12071e3903bdf61349e5548` |
| `M ` | `docs/orionis.http.payload.parsers.html` | `5ffafd571a84da0aacaf22caf55271fd8e382b7cbf2cc5704b02cf39b23c5449` |
| `M ` | `docs/orionis.http.payload.part.MultipartPart.html` | `4ada9f96f422a72841f5aa1acfce56e2f3e6248c273b86be6a9550d83750ae73` |
| `M ` | `docs/orionis.http.payload.part.html` | `e56083fd1617057f29d48b9b90d820090dd9bad408c24fc908a2bce4e8c4209c` |
| `M ` | `docs/orionis.http.payload.stream_parser.MultipartStreamParser.html` | `48f800f45a74f89e0827e740f81159cc5520a3290015f0025de5aeb3601cce8f` |
| `M ` | `docs/orionis.http.payload.stream_parser.html` | `768847a3dd6e4934552c63d2d505c1c2c1d1b71da338278caf9f9d51f65c3b0b` |
| `M ` | `docs/orionis.http.payload.uploaded_file.UploadedFile.html` | `1dc3b4e95a85d56373bf27bcb233fde12e3e30648fc94aaf507a77ec7998db80` |
| `M ` | `docs/orionis.http.payload.uploaded_file.html` | `76ffee61262429c17cee3db230896ae3dab672b435b4c859f0d04388d95c6384` |
| `M ` | `docs/orionis.http.request.UnsupportedMediaTypeException.html` | `3fd0693d9661232125b1c2592ddc74c188032728f1cb3bbecfad04c3b3db203b` |
| `M ` | `docs/orionis.http.request.html` | `f782772d3339a3b0e0a8289c00a23f6aad55d46c6714aad00250a09e3caa1b8b` |
| `M ` | `docs/orionis.http.request.module.html` | `a4244132144f06d25bc1c052d8bc0477ea5d52cf57e39c0b74049fbc1d59bea2` |
| `M ` | `docs/orionis.http.responses.html` | `98d11d28a769a820449c83047fe9c824490ccdbd9c5d30f514fcee5e37abbfb6` |
| `M ` | `docs/orionis.http.routes.auth.html` | `5e0efef7d65ac1e301a94135956da792f1c3d0fa2f0870b83c783a9648b02371` |
| `M ` | `docs/orionis.http.routes.contracts.fluent.IFluentRoute.html` | `a83b465d75954ccefe6a635cf0a94f26c8c30cda6a363e8123cd40ba202309d1` |
| `M ` | `docs/orionis.http.routes.contracts.fluent.html` | `de34bcf90a5cdfdb9f40674bf66630fc1dfd8e6a2b2d3f7473edc5447f611096` |
| `M ` | `docs/orionis.http.routes.contracts.html` | `c1f94927dd183f0bba6eed7fc68fdd131e581c02609ebec0ee92cdd6d662974e` |
| `M ` | `docs/orionis.http.routes.contracts.loader.IRouteLoader.html` | `96e50e9d4994de1dc300128e6a3a793bdebffca146eeb00abba5c4dec78d79a0` |
| `M ` | `docs/orionis.http.routes.contracts.loader.html` | `1e9db74c19898b0ffe2a6396de653482cb292a61b2a867b57dab96858194a23f` |
| `M ` | `docs/orionis.http.routes.contracts.route_cache.IRouteCache.html` | `e1cc919e5a98eb57611cdba9d8b5d72cfb2e9c5e2d7a9e57823f2f26a9fedd81` |
| `M ` | `docs/orionis.http.routes.contracts.route_cache.html` | `42f0b02d55941db6926643d7418b5a90fa29f3828c92d68e72ace1af9386078c` |
| `M ` | `docs/orionis.http.routes.contracts.route_compiler.IRouteCompiler.html` | `b0e3b71460617bd984cbb771e94e8e96cd33dfc489c9fa2d1971facbedb8b48f` |
| `M ` | `docs/orionis.http.routes.contracts.route_compiler.html` | `909c050d71ed9f4d90d81f4b1b78c7f127f29fbaf74e383eb2403983e1846553` |
| `M ` | `docs/orionis.http.routes.contracts.route_resolver.IRouteResolver.html` | `acdb96307f2dc185e6d91d5c283e9a1703c3aca40023d6692ab3afaa515dc88d` |
| `M ` | `docs/orionis.http.routes.contracts.route_resolver.html` | `e87fdd324a6d15afaf119d6343709b285fb6b4b872c93125a034b5529ff92572` |
| `M ` | `docs/orionis.http.routes.contracts.router.IRouter.html` | `979328a61c4fc4fec63f020b0a6439ba09634f0748aa47bdbe7c03033943328b` |
| `M ` | `docs/orionis.http.routes.contracts.router.html` | `a2df6b3580441de52ec81d6dae2db4fa6de542c8b06ff24a9eeaf5c8cb3a7eff` |
| `M ` | `docs/orionis.http.routes.entities.compiled_route.CompiledRoute.html` | `9c9a9a7fce8840551d9079387ff905c2b9446a0a6dd48b7b432aa8e69eb7ae52` |
| `M ` | `docs/orionis.http.routes.entities.compiled_route.html` | `e354cf91f27cae99151848fbfa92519faabd11459d0effcb966cd8fb9cbb3c61` |
| `M ` | `docs/orionis.http.routes.entities.html` | `0aa91d8d042da3a73198b6ae851122086c5944c6e46eec60511308d6bc92e37a` |
| `M ` | `docs/orionis.http.routes.entities.resolved_route.ResolvedRoute.html` | `2d8ab0d071fb317a93dd7b28c6a40a9f3b2653e878ecfb21df5d878cb6f6e4d4` |
| `M ` | `docs/orionis.http.routes.entities.resolved_route.html` | `d111d40a9f4eddf2a26a707d7ccbd5716c0fee8e39a24cb4e80c63f3289bf8e2` |
| `M ` | `docs/orionis.http.routes.enums.html` | `8fc77e3f9056a1f260b940ff67608eb3271174f32b7b53155a1f49e11ec70b29` |
| `M ` | `docs/orionis.http.routes.enums.protocols.RouteProtocol.html` | `1262bfe83a58cf91919c57fa9483dfd308df49c2813f81480bda7e4e008a9e2f` |
| `M ` | `docs/orionis.http.routes.enums.protocols.html` | `2ed7beac3d71145bc0875214aae9aa5f1b100ddb55187de2f5b3b52eb702a6f7` |
| `M ` | `docs/orionis.http.routes.enums.route_types.RouteType.html` | `266f64e516ade72eee6d66aa61339349c667fd549c21cd8f05c58f26da4c8591` |
| `M ` | `docs/orionis.http.routes.enums.route_types.html` | `ad4f225169fb65fe1368dcc4c544d8c9c50130d12a2b23c5c7367e24d510f60e` |
| `M ` | `docs/orionis.http.routes.exceptions.fallback_route_already_registered.FallbackRouteAlreadyRegisteredException.html` | `369cc189b0d519eb42dae9ab62c0ba53954fdd132b5205bf8972e260325fd668` |
| `M ` | `docs/orionis.http.routes.exceptions.fallback_route_already_registered.html` | `f7dfdef2349914c79c6638cbc14b5481610d6a8780c4d3f9a59458b868a3950c` |
| `M ` | `docs/orionis.http.routes.exceptions.html` | `188c69743a9cf71d1d6165a0af36d202e79d03a007803d33ce2695f20d81a9f7` |
| `M ` | `docs/orionis.http.routes.exceptions.method_not_allowed.MethodNotAllowed.html` | `32f5a6c6cec88f6970f9bb76140001d3136e109f6dd6400affd8ee78b1048f5f` |
| `M ` | `docs/orionis.http.routes.exceptions.method_not_allowed.html` | `d1de154445537115c243be1923dc2c8d5d4105f04301c6eba1d68adcee6f7668` |
| `M ` | `docs/orionis.http.routes.exceptions.route_not_found.RouteNotFound.html` | `f583d8b311bd541c029f14de80484fee317df450a08d0a0216984d7dc3dffc43` |
| `M ` | `docs/orionis.http.routes.exceptions.route_not_found.html` | `ed3cc1410496452b60d08e8d7202351388edc9aecb25a05b4d4b8274921a0648` |
| `M ` | `docs/orionis.http.routes.fluent.FluentRoute.html` | `f7e6f9dbf9ca7880e9fc51ddd613e7a2e3d6d547ab7331d5bf0ae4a55b76601f` |
| `M ` | `docs/orionis.http.routes.fluent.html` | `d78e0cc2b24ae05e40d807efd3a8d6d189f20aae8900fa138855e8eebb79b9fe` |
| `M ` | `docs/orionis.http.routes.functions.html` | `6a3f496d822933ad2396ab40b8f606a3eab4e6e7700980627a1ddac8ed067a2e` |
| `M ` | `docs/orionis.http.routes.group.RouteGroup.html` | `bda5fdc7675a6a3cd9996eeda47c4e7e60c81e3d7e80f1a5dac5c4a6513e7ce4` |
| `M ` | `docs/orionis.http.routes.group.html` | `28e31869b189d30ffef6d9b99419476c03df5b75bbcf25aedb469baeb8144810` |
| `M ` | `docs/orionis.http.routes.html` | `f13981e8d6815f468b89b3149bc73a5f771214343455d23712ab6c3ee46eba0e` |
| `M ` | `docs/orionis.http.routes.loader.RouteLoader.html` | `cf50cd2e3199ff92802d5c5a26b3352b1798530215a75b12c32a5b52747431c0` |
| `M ` | `docs/orionis.http.routes.loader.html` | `f3d98f9bcddc0ba6417403dd3c477d38387856c4e2f8b2c8cf2ce966e255dbd2` |
| `M ` | `docs/orionis.http.routes.params_types.html` | `d837a8202e08391501a617b4443f72805b551fc28c46ef76845607bb9478552a` |
| `M ` | `docs/orionis.http.routes.provider.RouterProvider.html` | `c0f1748decdfdce599382bbfbb759e09f4f83ce967828cab11958ba1b7c46cbc` |
| `M ` | `docs/orionis.http.routes.provider.html` | `5bae7912a51de47f8731e4f0c28cbc189648c33bb021e32493548842491a3fa8` |
| `M ` | `docs/orionis.http.routes.route_cache.RouteCache.html` | `90b85a54f694a8377fd8a2b5a79aa8eff434ef73b2d100d5e09e1a14eb819a95` |
| `M ` | `docs/orionis.http.routes.route_cache.html` | `bb11f43977b1aaff64b4a93585c49e1b0f16f41bc30eab818333c204c55f2b6c` |
| `M ` | `docs/orionis.http.routes.route_compiler.RouteCompiler.html` | `727b5d4a3fc9982d2fc31873e34d19834d03e4b57f8d99db3b71b5ee363baee0` |
| `M ` | `docs/orionis.http.routes.route_compiler.html` | `6c8283a39a0509de1ec6b36afdb9445770b81edc47306fd3135e15421fcc4fa3` |
| `M ` | `docs/orionis.http.routes.route_id.RouteID.html` | `ee4d7e6f8d14f4cd781bd8dc3498ec63b97e9136c96ee82eb27900d3499d86fe` |
| `M ` | `docs/orionis.http.routes.route_id.html` | `20fabf5b7b5f48b0a9be7a97bd288f770732c6435656f033c2d44f888a60b83f` |
| `M ` | `docs/orionis.http.routes.route_resolver.RouteResolver.html` | `5290294e0b9c0d0aef9c17ec22d5bd2acb61a7aeaef52080064110680a6d87fc` |
| `M ` | `docs/orionis.http.routes.route_resolver._DepthBucket.html` | `f19088578227aeabb1f2acf76ce379c1a28d1d0a40f26b7fe7f433d835b9b44d` |
| `M ` | `docs/orionis.http.routes.route_resolver._PrefixIndex.html` | `6e63b197d853954c89b2ed78012af56fa7b904cf020929e1c45a851b18b8bbcb` |
| `M ` | `docs/orionis.http.routes.route_resolver.html` | `a0a4fc6a33a70255170a799aa4c98d5fe39fd5180cc0616d09f6fe81ba0dc8ff` |
| `M ` | `docs/orionis.http.routes.router.Router.html` | `1a64b4eaf5a0f63627738e4da5b4ca2adeaf47b3921d4f3910061d3fa6032a0d` |
| `M ` | `docs/orionis.http.routes.router.html` | `417e9552cd47b57f1820424b3d777825480188c69040a1de5e73fc4ac8b3a1fd` |
| `M ` | `docs/orionis.http.routes.types.html` | `73502c4d698f6ef9fe0f84dd744c6342d5b3843e39fc769a4967003e116517db` |
| `M ` | `docs/orionis.http.sse._EventStreamIterator.html` | `c3980c64d7d1788320d60c3badecb9b8e7e7c935f436f024c1f2259264c785df` |
| `M ` | `docs/orionis.http.sse.html` | `2ec1b40474ebec7d2dd0f78b3bd45388fa3b32922b9102b8347ce90e6a1ef9a8` |
| `M ` | `docs/orionis.http.types.html` | `8e16886e7de8c6ed9415ccf2d656d2277f01f7c59f44c747cbc07fa5521a7d91` |
| `M ` | `docs/orionis.http.validation.html` | `b982c3a638f9ae645a8bcb0957b8eabf3b77e2e1062b2caed8cf5c4ce07794c6` |
| `M ` | `docs/orionis.http.websocket.html` | `60b8a8874974c61a6b2b33f19c3a9386506503647360eab6a127b53fa354d21e` |
| `M ` | `docs/orionis.http.websocket.module.html` | `87ec6a51a286d0de05d762c4f70b27d0363a6dfe4fb2b63bdd4ef4e4b6c216fb` |
| `M ` | `docs/orionis.http.websocket_message.html` | `708125b577d6ccadbc066ad37c6f0e31fcff71c19e5737621cbf3d7cd7ca7c1b` |
| `M ` | `docs/orionis.http.websocket_middleware.html` | `be150e3ff98a1aa8f8622550adb213c736999e63e268d075c12268de80a30913` |
| `M ` | `docs/orionis.introspection.ModuleInspector.html` | `b7ea84a249f62ceb4753b7275538b4680aa7ca047cfe85ecaddf4636e71c76ec` |
| `M ` | `docs/orionis.introspection.ReflectDependencies.html` | `a6712d61c507be3d9e25382d8478d26ae4a0c8dba2751b117c8a11197dc655fa` |
| `M ` | `docs/orionis.introspection.ReflectionAbstract.html` | `15796fa830de41246aff5592a327384b3df4d63c622805c2c01b91d68678bba5` |
| `M ` | `docs/orionis.introspection.ReflectionCallable.html` | `46a5a151e0bed9d7c03a163fdde4d5dbb7eb15b9acaf6fa244751771b3dc29fd` |
| `M ` | `docs/orionis.introspection.ReflectionConcrete.html` | `c130771eaf042b3125ff1f48beb386f88ceeefe39bbf15f22e50b5c06ae241ea` |
| `M ` | `docs/orionis.introspection.ReflectionInstance.html` | `e53e971976a8002ff267f921fee6acd450bb956d074c92542191650dd636dfd8` |
| `M ` | `docs/orionis.introspection.ReflectionModule.html` | `51427e051389aa37de24081bd39207d6ab8fc530b8b7de386c46e028dcf618c3` |
| `M ` | `docs/orionis.introspection.abstract.contracts.html` | `680b619b6817e92ab399562414a0b23a2320c90e798883edeb0182be477afb0a` |
| `M ` | `docs/orionis.introspection.abstract.contracts.reflection.IReflectionAbstract.html` | `e8b0fb9107093fff2a569f650209c41c992cb7336f9f1c42c51eb4c7388f6299` |
| `M ` | `docs/orionis.introspection.abstract.contracts.reflection.html` | `ab81f5ad83653d921778667a84f2aa5ac61ccc318934a9943b30aee7bc792d7f` |
| `M ` | `docs/orionis.introspection.abstract.html` | `92caed42d02f3c0427c85ff98994a3368847b95b1e2162d26e970ba94479353b` |
| `M ` | `docs/orionis.introspection.abstract.reflection._Flags.html` | `c99893649b89a7af9367291e37d25cd1e8f23750182b285eba12b28bceb1cb81` |
| `M ` | `docs/orionis.introspection.abstract.reflection.html` | `48122406d35ba284781d74179c711a7abad31357e49b1c16b784f5b19aa8dfd0` |
| `M ` | `docs/orionis.introspection.callables.contracts.html` | `83389ac8afb6cf0e43e267b90603a73997351d9932a6fd699277b8e90a316dbb` |
| `M ` | `docs/orionis.introspection.callables.contracts.reflection.IReflectionCallable.html` | `55c9eb129cfad53257db42f0b9979f5ea7ac079d90a26b5872dc17b0a97bb225` |
| `M ` | `docs/orionis.introspection.callables.contracts.reflection.html` | `cbd50213e542e88381c341fec7df5a9ab193b3718b7b8aae561380dbe9faa9eb` |
| `M ` | `docs/orionis.introspection.callables.html` | `6401799e12d1a5d4ac2006159ed966a19cd5a74348615c8a718d7a92d7861760` |
| `M ` | `docs/orionis.introspection.callables.reflection.html` | `a2ad90a52afe7a48ef13cdebb93df7eea4a7195bb9738d7c8ddf4d455da04d79` |
| `M ` | `docs/orionis.introspection.concretes.contracts.html` | `ca847a2913988f49e5f3e5f6da5fdb48581e8fd24f2b66ba418e4e9bba232452` |
| `M ` | `docs/orionis.introspection.concretes.contracts.reflection.IReflectionConcrete.html` | `b8dea44a499cee5b5a51c3fe5aba45d19e9925e6be6ac021c10969a26c7d71be` |
| `M ` | `docs/orionis.introspection.concretes.contracts.reflection.html` | `0f0cbf0415b144d07399b0a56ac68f5056860d68e657543ab4d1ec6bf5d41c0f` |
| `M ` | `docs/orionis.introspection.concretes.html` | `931ad2a57c042f2fce03ed96eac3d8898a31ecdfc49d8a40c94bfd15ab3d8cac` |
| `M ` | `docs/orionis.introspection.concretes.reflection._ScanBuffers.html` | `5aa49bf443e550db9bff024704c48ac8551f4f426be8f18813f7b06c9f674227` |
| `M ` | `docs/orionis.introspection.concretes.reflection.html` | `a0a2c32412c7a58aba0381e333d80ec8c8a1721c7af17e94a7b0c0402bdad79f` |
| `M ` | `docs/orionis.introspection.dependencies.contracts.html` | `28a9dc565039a90f42636624f5f4e0b3ded094b216c980719994a07cf45b8da9` |
| `M ` | `docs/orionis.introspection.dependencies.contracts.reflection.IReflectDependencies.html` | `b9df331ef291b06349db5d8a1438ad091e3b860257a9bd244d305d0e028cfae5` |
| `M ` | `docs/orionis.introspection.dependencies.contracts.reflection.html` | `89b723ccf0b48155239c5b34446f702902da3cb50f7fd78a3620fcddfbc8a443` |
| `M ` | `docs/orionis.introspection.dependencies.entities.argument.Argument.html` | `97dd6e9b147ef9cb01657b689488113c5f1d8d574f0ecf7a17099962f9ea98ce` |
| `M ` | `docs/orionis.introspection.dependencies.entities.argument.html` | `d9b8fc2a98b6cf81f91ee526d519631f6dd5904c205b0201bb049d420323384f` |
| `M ` | `docs/orionis.introspection.dependencies.entities.html` | `42510d8e5307ecfc4751122a8fe072431afc4a1b52e9169834865279ecbe8ab3` |
| `M ` | `docs/orionis.introspection.dependencies.entities.signature.Signature.html` | `b375906ecf66c4ae9c7c91309c7067857585a757caeccc40fa1bb49ca125e8ec` |
| `M ` | `docs/orionis.introspection.dependencies.entities.signature.html` | `0beb8cb6006c3e447bebe267ebde0de9136a161af0df2a39cccd4713838b3d64` |
| `M ` | `docs/orionis.introspection.dependencies.html` | `f034333c04ccaab4beaa0788189933058ac5a90bd5bd4aca98970d52dc48ab37` |
| `M ` | `docs/orionis.introspection.dependencies.reflection.html` | `7e88781f4a7eeee94c42f9d22e7e9bab546a4832f35fa0432dde4a68ea127268` |
| `M ` | `docs/orionis.introspection.html` | `532161e362613164e4dab3fb5ae5aaccf2f1a5f6f657710a266736c7d8c89985` |
| `M ` | `docs/orionis.introspection.instances.contracts.html` | `9d6a84e47d403dd35c54f9846519a63f9467508ead387b15c16e78a283cace96` |
| `M ` | `docs/orionis.introspection.instances.contracts.reflection.IReflectionInstance.html` | `f74eb6877182e055229b03a5494771af442f8de1279cde9a9f8208957f6a0d73` |
| `M ` | `docs/orionis.introspection.instances.contracts.reflection.html` | `392b0a0d668b84ffbc6e5cc6993a5475bfdb253a860ceb4466865934e2fb03e8` |
| `M ` | `docs/orionis.introspection.instances.html` | `7b247def9f6d45097ce2ea95aa20050a4aae425dc87ec33ac2e97b06fd7e0e53` |
| `M ` | `docs/orionis.introspection.instances.reflection.html` | `783586b0386a8305024aae6fbb26fa472afd635e7e8b57f06e2620917f6a8587` |
| `M ` | `docs/orionis.introspection.modules.contracts.html` | `6ccfd919d95f26fe73befd3988393d39709337b210296039c30567bce13b23a8` |
| `M ` | `docs/orionis.introspection.modules.contracts.reflection.IReflectionModule.html` | `83f5ab3d8dfd921a0eaea49f3273c091eff491ad473ad1071bc69c1931c2cd57` |
| `M ` | `docs/orionis.introspection.modules.contracts.reflection.html` | `69936fa28bfd78428d2f91c10ba8a5eb80759b7c72f69d9e093a6364d4e52139` |
| `M ` | `docs/orionis.introspection.modules.html` | `be66bfcba1b710d271e1013068a92cb5aa607b8c90f72d98359af4a4e1adc18f` |
| `M ` | `docs/orionis.introspection.modules.inspector.html` | `36ff7b47ffa48039a2e245abf2316f643c6f748906a4e8fac8abf54b3f39b1cc` |
| `M ` | `docs/orionis.introspection.modules.reflection.html` | `2133cdb436e681f689fa6dbcd8b17708131d650a7e338a39de8534de664c8905` |
| `M ` | `docs/orionis.introspection.reflection.html` | `bfa0d7a77d357ca596031aca593add3b7e7e8fe18840a07a8118c26293028b4e` |
| `M ` | `docs/orionis.introspection.reflection.module.html` | `e5768ef7730e52c6612814a0a4b8d78e7a8cdb8a052be334997e634562f148cb` |
| `M ` | `docs/orionis.localization.InvalidLocaleException.html` | `59f6d8d9fce7c32cf149790175625bcd78072e4ab6c65bde1c98d8a1bf83000c` |
| `M ` | `docs/orionis.localization.LocalizationManager.html` | `9d2424de6ffce6e19e83638eee7ba6d41dba78bc009594bc2f235d7a80bec3a6` |
| `M ` | `docs/orionis.localization.TranslationException.html` | `a9183d2b35b37c2623d5f2809addafd2d854d53e1e8b60dbbdc7691f55d4c799` |
| `M ` | `docs/orionis.localization.TranslationFileNotFoundException.html` | `637b7a2e5fb2c7ef82b681470be18dd4c946aa538ef17a9a6573c0c60124fc3c` |
| `M ` | `docs/orionis.localization.TranslationLoader.html` | `15e1cd6cc4a8892750e6ab833f2a0b5254ba05df6661752c9f44fb3227b5ca4e` |
| `M ` | `docs/orionis.localization.TranslationRepository.html` | `16f256c775db364d144158d11585c5f99e5d75bcb812f6d572952ad0504fbf5f` |
| `M ` | `docs/orionis.localization.TranslationSyntaxException.html` | `c5d19ce10c2b09b689bc2992f5b81f1f3dd372d4f3f11b34ee3c161b009be6c2` |
| `M ` | `docs/orionis.localization.contracts.ILocalizationManager.html` | `f806c32540f487e7325bf970a97a9c98e8828d4345a656c84c806ec86cb3e458` |
| `M ` | `docs/orionis.localization.contracts.ITranslationLoader.html` | `97f7af359e202b23eb5c127149dc1779a9617d10e17b5475ed94c1bf94de52fb` |
| `M ` | `docs/orionis.localization.contracts.ITranslationRepository.html` | `ff18880e3e6499638e69d32dd451bd20be2c9f30d92e8b399802ad13b1450f85` |
| `M ` | `docs/orionis.localization.contracts.ITranslator.html` | `d3afcc9a1d2d6a4338f06643d75ca24f34b7e3c4408d2e205d9ef5ff10a2602f` |
| `M ` | `docs/orionis.localization.contracts.html` | `d6f8e7e38b8d8e64439595f0f7bff892f624ca9203cb7fffde0d3744fb83f93d` |
| `M ` | `docs/orionis.localization.contracts.loader.html` | `469dd3101bfc77777caebf26c0ef21d051d95aae0b8764211f1a6a74ed6035e4` |
| `M ` | `docs/orionis.localization.contracts.manager.html` | `c9187ef02dcfca0d6232fe66dd1c0d8aea4b9124f14d079da4e05e3da08a938a` |
| `M ` | `docs/orionis.localization.contracts.repository.html` | `fdaccafb77115ccc6c4a3904ed85db1f5675364b11e85b73e117654083aa8834` |
| `M ` | `docs/orionis.localization.contracts.translator.html` | `d92f20b2241839eeef1a928880829da004c899d2e0bb22f6d5dbb5fa95b79ec8` |
| `M ` | `docs/orionis.localization.exceptions.html` | `5617f3f1e34e2745fce2be0b85e81c1ef01af23d7814a52c8c1e4c69f286ab8d` |
| `M ` | `docs/orionis.localization.html` | `5c1cbed383c9f92d82dc73987cc02ae272f56caaf59c38ca8d4f3c4492fae164` |
| `M ` | `docs/orionis.localization.loader.html` | `c41b9d6f6eae67c2143eda1a98298bbfc13107481ab75f536c305401c911402b` |
| `M ` | `docs/orionis.localization.manager.html` | `c31d10bd2beb00312a3d8e7c337250f6308d46563402bdd6d560dca5cee3041d` |
| `M ` | `docs/orionis.localization.provider.LocalizationProvider.html` | `03091f4945480eaf5ff1d9290bdfde96e5753c3749629778620f3462b22eab1b` |
| `M ` | `docs/orionis.localization.provider.html` | `40768c494103bc44f4e1d5b120495f40262be4cfd94b4427f87c54714d664982` |
| `M ` | `docs/orionis.localization.repository.html` | `fcaa57efe62f449518ec746d841c84ec728a41f53a937793895db7877350ca9e` |
| `M ` | `docs/orionis.localization.translator.html` | `9c9ec24a66fc89904931b682048efae3fe7210755e7dbcd92c14ee9d9b9fa00e` |
| `M ` | `docs/orionis.localization.translator.module.html` | `e86be42402ef3c2e56d3fddabba00b0aab02a4e778372b349531829d8e75829c` |
| `M ` | `docs/orionis.localization.types.html` | `c98f106b03e5bdd068608d59689a350e5eef540510f14b35c20937c37450fe98` |
| `M ` | `docs/orionis.logging.contracts.ILogger.html` | `96d6ee7cbe1c6f23fef88e76cab28cf65cf6499d1c778e7f570a4718bce55e59` |
| `M ` | `docs/orionis.logging.contracts.html` | `ba42ff7614894fb750827c40c598d040d6584636765af0dfd26cb9ad8ab7e22b` |
| `M ` | `docs/orionis.logging.contracts.logger.html` | `beb934665a77aca8b44176a6300fb0ac0f2441fd6eb853ca2c0a1b0b9ea192f7` |
| `M ` | `docs/orionis.logging.contracts.suffix_resolver.SuffixResolver.html` | `855ae49d4e27ee26a3beac6f0595a509eb1ec158570d66ec0d71794a5848be10` |
| `M ` | `docs/orionis.logging.contracts.suffix_resolver.html` | `cbdc6311a94cec2334bbc3a1dee1af142ff884dbd963e9e7ae24fc931effa795` |
| `M ` | `docs/orionis.logging.handlers.advanced_rotating_file_handler.AdvancedRotatingFileHandler.html` | `82c56efdd4cfdf5b89a50100d1598fd661d6c34aba6f14fd94bbd2f02fc6345b` |
| `M ` | `docs/orionis.logging.handlers.advanced_rotating_file_handler.html` | `8e337074bfdc26d1d7a6a6de172eddf9f0918c6f04832849bad6d47ccbb9c9fc` |
| `M ` | `docs/orionis.logging.handlers.chunked_suffix_resolver.ChunkedSuffixResolver.html` | `0cdb8130c167efedf6875a2ecf5ce63fffd08d3be68e2f6d7b4dadf0910264bb` |
| `M ` | `docs/orionis.logging.handlers.chunked_suffix_resolver.html` | `8f7b7bca19197eb9056427199462bd6973c8694ec915287eb728ac4996670e2e` |
| `M ` | `docs/orionis.logging.handlers.daily_suffix_resolver.DailySuffixResolver.html` | `aa779c3b674e2ef3469c59caba2e9d39c08df8adce88a6e706de98ba46f73738` |
| `M ` | `docs/orionis.logging.handlers.daily_suffix_resolver.html` | `564074db477ebb20146ea7d2f9c9bf5e5b31e4c9a9d261de7e806eff0858577c` |
| `M ` | `docs/orionis.logging.handlers.hourly_suffix_resolver.HourlySuffixResolver.html` | `6fc422a1a4e2bbc379727d6b66b4f26d5c5d862644e808468a25116d8dea82e1` |
| `M ` | `docs/orionis.logging.handlers.hourly_suffix_resolver.html` | `82099db91bfe3f2dafc5b3f5ea43a32fcfc1e0e06dba9070019786ff3766277b` |
| `M ` | `docs/orionis.logging.handlers.html` | `445518340e231a714da4634ca7cf391efb4de7f41beedf480214b1c519e6ac66` |
| `M ` | `docs/orionis.logging.handlers.monthly_suffix_resolver.MonthlySuffixResolver.html` | `769f28b4838beb9c13ddc6f5d7f642f6d5270e62a8e724c60cf6b5eff71f4acc` |
| `M ` | `docs/orionis.logging.handlers.monthly_suffix_resolver.html` | `aeb9e8068ab544979069a19e47a3929525ec7fa1e66fd744c1bc8569755fdb00` |
| `M ` | `docs/orionis.logging.handlers.queued.BoundedQueueHandler.html` | `32380d10fb5d7faf72a19e6471036f9da2318759461ef9032eddc8e3651984f9` |
| `M ` | `docs/orionis.logging.handlers.queued.LoggingDeliveryError.html` | `1fc315dedbeef06ad53be408e74a6fcdebb41133a4a493ed66e32acc9d4a9fa9` |
| `M ` | `docs/orionis.logging.handlers.queued._Listener.html` | `494bdb9f7822ff7e979a55a320f497e42456a325cbb95acf7834beca877c0987` |
| `M ` | `docs/orionis.logging.handlers.queued.html` | `b435980b7d5f0b8232a114630f5bc56b504733c851d96a349adebd6014b8d8fb` |
| `M ` | `docs/orionis.logging.handlers.rotating_handler_factory.RotatingHandlerFactory.html` | `c3e4d895f04b6a87104b82c0ebf65930f6f40ef8b5515c6358337edb581a87c0` |
| `M ` | `docs/orionis.logging.handlers.rotating_handler_factory.html` | `e06d427796c1a6957395541b7aa7ef3c5aefaa1bbdf922ab6fab747c5ad52be9` |
| `M ` | `docs/orionis.logging.handlers.weekly_suffix_resolver.WeeklySuffixResolver.html` | `bc5c3437333817cd167de89b374f2758a03d69aa32680e29e702e44bb821bf91` |
| `M ` | `docs/orionis.logging.handlers.weekly_suffix_resolver.html` | `e881651160d435df6becc866b2580462f6e23f2326e1f2a77001ebe949da0d26` |
| `M ` | `docs/orionis.logging.html` | `1ed6cadb2988660cf5a88a15d0d122ee1dece3570e66df690a40bb1089d01aab` |
| `M ` | `docs/orionis.logging.logger.html` | `072b2b75802d4c67c6c1bc50bd840f3ad6b8d9e88b45efccaff827c1ee0e22ea` |
| `M ` | `docs/orionis.logging.logger.module.html` | `b304e1a4e9ccf836500d0e1325f319642533f816a5e6942bd35caefed6f904d5` |
| `M ` | `docs/orionis.logging.provider.LoggerProvider.html` | `641ea0c4510d3956bc6b1890959fd7e9b030d5d8271951a391f7a6f54190d780` |
| `M ` | `docs/orionis.logging.provider.html` | `dd9a8731fb545cdb9f8f6e1ca70a3509788bd201ea3ccb2576c25543aeedc290` |
| `M ` | `docs/orionis.mail.PendingMail.html` | `bf0df4531be0adccc68d4d845e9e1ba3f759549fc5fcefcdc3c6ed8915efb194` |
| `M ` | `docs/orionis.mail.composer.MailComposer.html` | `90e2053d455af8065b09288b46a4d7ad4f613b11921b8aa90d5e782e75a7d362` |
| `M ` | `docs/orionis.mail.composer.html` | `94ec0002cbb3e312578ba47abe76e64377dce9e99f51bfc7221f8ff97bd51d33` |
| `M ` | `docs/orionis.mail.contracts.IMailManager.html` | `a578b78dd504475f06e3dcc07a67008b819a60fce9dbfe7f2d1af34294b9e56d` |
| `M ` | `docs/orionis.mail.contracts.IMailTransport.html` | `45144e99a34fe0df1794089ed5ab31804d59e890d1bbd206d705df065cadbda6` |
| `M ` | `docs/orionis.mail.contracts.html` | `e136ef767174305901efc0b11c2d0aa6897a8caa84849d50664cd6b038519ec2` |
| `M ` | `docs/orionis.mail.contracts.manager.html` | `dda7d1d44b2e95b5f9d2fe6c17706ee50a9066ec45d00ec9d64a174f57b6c8db` |
| `M ` | `docs/orionis.mail.contracts.transport.html` | `3fa8153cf784257f3d468a193599ad1616b54f15980a87dfe0de6ef5497fc8fc` |
| `M ` | `docs/orionis.mail.entities.MailOptions.html` | `6c45813526264276f78675dd1617fbbc9e74b9eb92689844c4aa459df0f7bad1` |
| `M ` | `docs/orionis.mail.entities.MailResult.html` | `70e2bf8ebb6a6aec6c3f6cf68b522c595400aa0f08946274568aa861a37e745b` |
| `M ` | `docs/orionis.mail.entities.PreparedMail.html` | `25ecc1acef74a8ee741bbd20f735ab6b519481d822c6411eb506d6413e44d9fc` |
| `M ` | `docs/orionis.mail.entities.SmtpSettings.html` | `6829be11865264b93b3802f8780fe99a9f33e2862d13ef41b2845dc4fc9b73c6` |
| `M ` | `docs/orionis.mail.entities.address.html` | `abeca6d33fc1d3b3ee5a23a0f3b48075535e9d1c63b6fa7d0c57165f287df1c5` |
| `M ` | `docs/orionis.mail.entities.address.module.html` | `c739af76f0bde9cd6d9a3e89e920f052822a981e5d409f0e00decf52ab97dcae` |
| `M ` | `docs/orionis.mail.entities.attachment.html` | `ea63424827758e2cd6c373c745de9223eb2b09474b3cac48f803b33cd50728b9` |
| `M ` | `docs/orionis.mail.entities.attachment.module.html` | `ff370f0376831e31aa60a7af9f99fb31603b738d98f6853ea6245614053719e2` |
| `M ` | `docs/orionis.mail.entities.content.html` | `f9f67d121cb795b0dfff17f755dd85caf84fff71a6842e21a4aa8551686ad0b8` |
| `M ` | `docs/orionis.mail.entities.content.module.html` | `b9f074561cbb0fe818647c5a26a1565b65cbb5539812040f46ae793266f0cb9d` |
| `M ` | `docs/orionis.mail.entities.envelope.html` | `937588d58c446f89a6a74252b247638bc01152c1aa9600d24d26034a7a4b2bb0` |
| `M ` | `docs/orionis.mail.entities.envelope.module.html` | `373fbfa17e1cbe2e8edf157d5c1401281a84a25f804750eb59481ff202d0d211` |
| `M ` | `docs/orionis.mail.entities.html` | `0dcd6e105fe6b6ca4dadc8fada1518f88ae05db4273442a3b99a607c147f72e4` |
| `M ` | `docs/orionis.mail.entities.options.html` | `3d9b239cbfaf938964b48a939e01bd777498406978e4674cbb7eac7a9ecec8f0` |
| `M ` | `docs/orionis.mail.entities.prepared.html` | `2e8f96e68080b4ab6e492e572f62f2d007b4266152b0fb2201c0105397cb2cc9` |
| `M ` | `docs/orionis.mail.entities.result.html` | `d6f57e7e307313aab7c6cba29e158a635ca73d1940357add6bc4091e81852733` |
| `M ` | `docs/orionis.mail.entities.smtp_settings.html` | `01cb22ee52c4560061c1fa574a453280e390ccaed63cda89be8a258d593df245` |
| `M ` | `docs/orionis.mail.enums.MailEncryption.html` | `25ce5a0bedf3161e55550321d43bb4b5713f20c4ff324fa07a13645bcc78666b` |
| `M ` | `docs/orionis.mail.enums.MailStatus.html` | `8753a788f3ed17bb02b181b3c896e77a51bb22009650159805bb4963c17ceb08` |
| `M ` | `docs/orionis.mail.enums.encryption.html` | `f1653a75eb208bac43a21338672a1e7a5ea73e4b0ba7a3b14e7b0e1f089cccd8` |
| `M ` | `docs/orionis.mail.enums.html` | `51b2614aad31377a4b8f3cc4d151364b9ca89351f4b595c11ea8b36d79c7149f` |
| `M ` | `docs/orionis.mail.enums.status.html` | `007e6f861303977f99f04ba4b21b3fb9a616586fe1616816b971d7249b12c18b` |
| `M ` | `docs/orionis.mail.exceptions.MailAttachmentException.html` | `fd0069f5317b805daadfce6632148c991f6cd961b0314ac51014ea69e43a1c95` |
| `M ` | `docs/orionis.mail.exceptions.MailBatchException.html` | `bb116361ba3eb62df3cb2267f5de8eeddb0696f96b5c964687fe6d740012a45a` |
| `M ` | `docs/orionis.mail.exceptions.MailCompositionException.html` | `a0ecb2c6951ab4e6e29e6bda6e963d1cf94411cff169b579de17fed1a9c995d9` |
| `M ` | `docs/orionis.mail.exceptions.MailConfigurationException.html` | `e1c7395091b42f1cba27cd00fb14d14c26133551ed81c317d1210ce5228de4b2` |
| `M ` | `docs/orionis.mail.exceptions.MailException.html` | `6d4e5e9f9c5d2ac2c8764c161c36d5d44ead17e26633499a9f9798ba4867800c` |
| `M ` | `docs/orionis.mail.exceptions.MailTransportException.html` | `f453f8de321e1642d6dda4c074d57136d8dcfff884ac62d3b31445b71ac0d2c7` |
| `M ` | `docs/orionis.mail.exceptions.html` | `2b876635852b098e60285fe1de7eaf062daff95a7885e15de76538453c5fabeb` |
| `M ` | `docs/orionis.mail.functions.html` | `51a4e1b5d23b81dd5e1246b18e2a19ec3593f94fdc57f0b2069f0474cce37ac3` |
| `M ` | `docs/orionis.mail.html` | `551d413c457f732f1f75eefb234fd8d0e7b2840f4931fc51f114cc821886c69d` |
| `M ` | `docs/orionis.mail.mailable.html` | `922d3c106f9736fb604fd0b4cdcffbd2d9c458bd81aa7994b0b295d54df37e08` |
| `M ` | `docs/orionis.mail.mailable.module.html` | `29d6e29a5a11d27c14b5e8108e38924977444c86e4e90d0eebfc753678f354bd` |
| `M ` | `docs/orionis.mail.manager.MailManager.html` | `bb28a1b54f9fc425edd71b03951ff6bc38ce106049cc93823b59896d856d03a0` |
| `M ` | `docs/orionis.mail.manager.html` | `9018ff53b98c90c430ea547b5f535f7f702df514cad2715489fae329c48f1356` |
| `M ` | `docs/orionis.mail.message.html` | `74b9a10fae1995101f3382d63e3fec395a1b54a826163dc912c0f835f736f3bb` |
| `M ` | `docs/orionis.mail.message.module.html` | `41a3035a42606bab89d3f7c51dd0b39545cabc9be353e046543ccd388ada5a10` |
| `M ` | `docs/orionis.mail.pending.html` | `209ce90cb4310762220fa2a943c3321e5552e5528790ba9cc232948bf3c26f0b` |
| `M ` | `docs/orionis.mail.provider.MailProvider.html` | `65a441397e2c04996b693bfa4c9f0b0647ede49e138e220fa66d494f58736452` |
| `M ` | `docs/orionis.mail.provider.html` | `b46d5208dfbd2b084bb5cd163ef40851d5264cb965cbd5bda59d63c0cb79c4c6` |
| `M ` | `docs/orionis.mail.transports.FileTransport.html` | `4486e746bcf95e6c6ed44f89d288808d4953e5088b522b2d5671a604558ed43a` |
| `M ` | `docs/orionis.mail.transports.SmtpTransport.html` | `bca606063da97c2f5fdc72fddf902ce2d51ea37bee58b329d4f763f13d0f0f05` |
| `M ` | `docs/orionis.mail.transports.file.html` | `933a3ce25a253141321d4bece0c55a1b96d5fe9aacb67caaf659976ec8f573e7` |
| `M ` | `docs/orionis.mail.transports.html` | `88c8c2d5fdacb6c3f261b7f86739e580c891375a34b75ee02c047ea3da5efb52` |
| `M ` | `docs/orionis.mail.transports.smtp.html` | `8af699f3eddaf9f4d42c5b8ae5d121c4ba516a87c6e0a62267a99bf1a5ced966` |
| `M ` | `docs/orionis.mail.types.html` | `67bc9a6c92de926c13d354f805c6176543e16929b774a88cd33c850f6db26b92` |
| `M ` | `docs/orionis.mcp.CacheHint.html` | `7f3b61f0713a56441003924f50ebd48b92ac74b9276c993da2f55bbca165d1ac` |
| `M ` | `docs/orionis.mcp.Completion.html` | `62902584d943588b50ec5aa7bcc2ef93b7e1ee96ef12e4d65d3d0136a3ea3483` |
| `M ` | `docs/orionis.mcp.ContentAnnotations.html` | `7347d9d1bfbb747a5907af3741dc67f3ca3ae668fb238875f07e4a3222ff9ea1` |
| `M ` | `docs/orionis.mcp.Icon.html` | `17157feaaa29d2d4460962bd010b837f6e088179bf963602a573770a6624adc8` |
| `M ` | `docs/orionis.mcp.InputRequiredResult.html` | `09ed5e318ad89381dec002eae5b33b8b76581a13210cb601abd1deeb9cc6165d` |
| `M ` | `docs/orionis.mcp.McpExtension.html` | `bdb6409d2f1a4a71cbb360371a1e8e20b8d09987b28d62815cb8f5f5ad8f8ca9` |
| `M ` | `docs/orionis.mcp.McpRequest.html` | `8095a7bca59fc37c4fdd04344d60da971e4fdced2dc8cb8b72ddcee41d22f90c` |
| `M ` | `docs/orionis.mcp.McpResponse.html` | `2b1978f37a8941dd6c7fa6a51a0f3bb1c88c77ccbde7ca71886fecc196f78908` |
| `M ` | `docs/orionis.mcp.McpState.html` | `00b9311334625d969dadb0f0f7beaf942c6908e609e4661113f604d7f77ae490` |
| `M ` | `docs/orionis.mcp.Prompt.html` | `15a3949a8ad3c4a06246d8fdf0487d25ecbbb1af077d8ac2550fa39150f26959` |
| `M ` | `docs/orionis.mcp.PromptArgument.html` | `ab5709d496574993f6bd5a090ac6df938425b5210893e22c4e13c54a3b839cc1` |
| `M ` | `docs/orionis.mcp.Resource.html` | `cc525e744069faa2ae90944da69701648b666811d3378f00fd982d3def8a1906` |
| `M ` | `docs/orionis.mcp.Tool.html` | `9afc79d1bb3f0ea139c445400a6d50e92ed8cc5a3e7e9467ba6fdd6decb27482` |
| `M ` | `docs/orionis.mcp.ToolAnnotations.html` | `ed833cc07de4cc08ff55460faed25179eff8fc36a293d42d26c1752585748195` |
| `M ` | `docs/orionis.mcp.ToolCatalog.html` | `9f382b45132f767bcb44d2737102d8078f6537bd6177d3eedb54f834e49e03b8` |
| `M ` | `docs/orionis.mcp.config.McpConfig.html` | `80015475c8bada57f4c36e4e710cb59dee540ee92b0b11c7bbf669b46c7e22b4` |
| `M ` | `docs/orionis.mcp.config.html` | `a3bae97328eaaddee620c3a82de4a7b84d363fff4ebfdb4b388f542c59e51562` |
| `M ` | `docs/orionis.mcp.context.html` | `a7640d2db3d67ee73ae7b56cbdd6b873b02d600c9ab87f09c52984296dc55e68` |
| `M ` | `docs/orionis.mcp.contracts.event_bus.IMcpEventBus.html` | `ccfc43c9824a8e8939e50f173d034d35198cd16571b039734a4165019f9c07bd` |
| `M ` | `docs/orionis.mcp.contracts.event_bus.html` | `9f956f357689ef01c91afc405a95d691ccd2d16fc5c1e18f839dc805283e99f6` |
| `M ` | `docs/orionis.mcp.contracts.html` | `437014cfe1cacaf2a8024700777bb7a9bec9cef94182d7073b4be8783011461c` |
| `M ` | `docs/orionis.mcp.contracts.manager.IMcpManager.html` | `55967b01b60e2286e5122415a642caf1dcdfd8e49120394d1af3b9cfdc51a0fc` |
| `M ` | `docs/orionis.mcp.contracts.manager.html` | `50315d2725e5c8071fd907b9f3ca8e34c6207f021de14b536f3ee9378ed8811b` |
| `M ` | `docs/orionis.mcp.dispatcher.DispatchResult.html` | `c7ed45171e2c5516bc5e4b97f37deebff40ccff16f5dfbb27ab20a899ea34031` |
| `M ` | `docs/orionis.mcp.dispatcher.McpDispatcher.html` | `66d69d53697ba8e7a63d2a91b0dbdf06ea8cf4dbfd4edb5537504da8808d041e` |
| `M ` | `docs/orionis.mcp.dispatcher.html` | `1dd6e90e1b996862c1c7716be3b14351310a8c8625c573f45693bd6ac8488fed` |
| `M ` | `docs/orionis.mcp.exceptions.McpAuthorizationException.html` | `c79d2dce3f2b753cc8114a16feb3a193693d8c812a29c9aa0764768cefc40b57` |
| `M ` | `docs/orionis.mcp.exceptions.McpInvalidParams.html` | `996ca10de666dc40e47cdfe99847bd58a8e8115d8a0f3fc4f3077fd88438d95f` |
| `M ` | `docs/orionis.mcp.exceptions.McpProtocolException.html` | `7de16627be7c2a56862023aafe788cd140a3fba4162c5d51ab2e5c49429519a0` |
| `M ` | `docs/orionis.mcp.exceptions.html` | `c9bf952c25ee95ab3b2712e45b6df91ab496cadd991dda0698fdeb363d7aa150` |
| `M ` | `docs/orionis.mcp.html` | `7560966d2905277c169b99f3ef36823102692d0bf97639122a13cb9e4bb618ec` |
| `M ` | `docs/orionis.mcp.invoker.McpInvoker.html` | `2a37147b35432a694883f0e5de1889b9e686550ab5afd17b35237dda214627a0` |
| `M ` | `docs/orionis.mcp.invoker._Parameter.html` | `8abc21d130086bf68d0155e8b8e250c1322a780c765b16c31a41c6b745d9146d` |
| `M ` | `docs/orionis.mcp.invoker.html` | `c37ab0c49ea0a51960b58753f3fc04cdb9427166668797b17653ff26467f6544` |
| `M ` | `docs/orionis.mcp.manager.McpManager.html` | `fdb38e5b85bfb979dce06730ba7e42671509047b922fa736022a14aec7fbde1e` |
| `M ` | `docs/orionis.mcp.manager.html` | `2799025a7770666c6dec67c412ac86360e89926a85a170c19ad459c006459505` |
| `M ` | `docs/orionis.mcp.normalization.CacheOptions.html` | `22a753011781603c88a94e5ae4e2d058f3308dfe39a4e3b326564e1aaa39a1f2` |
| `M ` | `docs/orionis.mcp.normalization.html` | `5355c8453d2608c75619ece6767f36c4ebc264f1686ecb0371b7c485e9885c0e` |
| `M ` | `docs/orionis.mcp.protocol.codecs.html` | `6e3146d89fe2b8709513ec993131ab614c6bda6484a45a3fc07e590882bd3c85` |
| `M ` | `docs/orionis.mcp.protocol.constants.html` | `6e12d1b67133017483e726842c24c4eec6b9eeb885d62cca7bf92474eb2e513d` |
| `M ` | `docs/orionis.mcp.protocol.content.Annotations.html` | `1b199567296f4ed8de6f49d7c60be4448f51b5848fde85dc871e0b4feb295f77` |
| `M ` | `docs/orionis.mcp.protocol.content.AudioContent.html` | `7a51e5ac5e50fa72d4c14adec212c55688316b100fccdfdf34d331ff83df76c7` |
| `M ` | `docs/orionis.mcp.protocol.content.BlobResourceContents.html` | `6b602802e22cb88ea88c33b736d64be46c96a91ced1c3e882e71be6b38e15734` |
| `M ` | `docs/orionis.mcp.protocol.content.Content.html` | `288ca9ebafc563999c70f2770f8462bfd97716bea7c369dbf2be2b2877ba8543` |
| `M ` | `docs/orionis.mcp.protocol.content.EmbeddedResource.html` | `5ffe83074e6137d70631f377935c3d19b9529c35bb97074722ad56cd2afe638c` |
| `M ` | `docs/orionis.mcp.protocol.content.ImageContent.html` | `924adfebb17f469083e2834a2ff479eee83dab5cd042abd6eefa7dba731c0d15` |
| `M ` | `docs/orionis.mcp.protocol.content.PromptMessage.html` | `78b51b54f4eab7068125ae36bed04ebbe48510b39db867fe47ef4810056ef693` |
| `M ` | `docs/orionis.mcp.protocol.content.ResourceLink.html` | `c025380aa113cd7df55f1a868e8ae6ef9a9752120c0321246484ab8faa495463` |
| `M ` | `docs/orionis.mcp.protocol.content.TextContent.html` | `a47eac94944529b8b06d680605b2cdc7fee9cf97d8628ff9614eed374dbe25f1` |
| `M ` | `docs/orionis.mcp.protocol.content.TextResourceContents.html` | `710827d2cf478e168a7aab0a007f2a766fe8efb92b403fa39134aae1d3a6b82f` |
| `M ` | `docs/orionis.mcp.protocol.content.html` | `8ceddfe30e9016f22c907a02e0c2b692e70721d85d9c188491cf86dcca5e0134` |
| `M ` | `docs/orionis.mcp.protocol.html` | `45f26217be66eb413fad76117a1041a00506e510e45704cab0951a34ebe90146` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.EnumItems.html` | `3ad80b3bed0594db7350ed1aaae4d8881ea591b0b2d573a0ba44afc45d5d0aa7` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.EnumOption.html` | `cfdc065c53976743b6f7f51745b1cbcb9d03eca21b5f07b0f17ebaf5932fc529` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.FormField.html` | `f9585fbdcea6d58c8daa0aa8e0050f78375af34290203c3a4540685be8275e7a` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.FormRequest.html` | `fc4b50764d9ed4a9b6a6146f4bd7a06a2c27d95fb2ab6bd4c7593c05f2aae710` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.FormResult.html` | `52f8930d6931b2b33829cd484d459e78cd73e084ecdfea1e72632c848e303d53` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.FormSchema.html` | `8a9141050a910caf7c006b2cdac3b209e06a7cda999f0746721b01897f907d99` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.ModelHint.html` | `0367142b37888d3875cb128d53372c42162ad40bfda466813dd4ac98a8118bdc` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.ModelPreferences.html` | `b19c8d761ffd9f036ee3be76e721d218cd6f60d5b140051358051c91f315454e` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.Root.html` | `9092f8c041e246b000037df0bb0193ee66f3bb196c95497641c599c616ed9a96` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.RootsResult.html` | `86cc121946d4aca97c66dc7c0e83a63fda7e65aa2309e79d95ca66a27d26d671` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.SamplingMessage.html` | `cb7a79e11009721e345725f019a006e6deb5cfc05c9448c513125072a36e84f7` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.SamplingRequest.html` | `614e5a493c2fd651db0373b67735b4b02aa669e1d34ac268bf67e312d9b64b6e` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.SamplingResult.html` | `896468610ec9b8030229b4c786a7e35a2960df76b123fe6e503a79c74856f49c` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.ToolChoice.html` | `4a124cb9aed76ad0f998f66fed9bde2e0c90c76f21cf18e3061408249fddcd5c` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.ToolResult.html` | `ad08d5803b9926eb3e2bbd41b3c0c7800b6f5b22d18a4fe947e73fc3ead23bab` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.ToolUse.html` | `ea1b2850ba5704359d9758ad62794a3bdb1d6673d65a5818d9b3ac363ba6097b` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.UrlRequest.html` | `8db4e98d22d980bb7b87a18e2469ab0bbca4cd1a59cc3fc31863a1d9b4106645` |
| `M ` | `docs/orionis.mcp.protocol.input_shapes.html` | `8466c61b7d3aa21c67d36c529a65efe70b3bec0a30b67260619d191c5856ab46` |
| `M ` | `docs/orionis.mcp.protocol.metadata.PrimitiveMetadata.html` | `ddd9656568927df448ea42c6ba6f2ca76ec4cf2c45815d60720375778cdee6d3` |
| `M ` | `docs/orionis.mcp.protocol.metadata.PromptMetadata.html` | `e7e0792f3309c929f80db22faaa857cccfb2974eebfbd78414e2bd98956a0c84` |
| `M ` | `docs/orionis.mcp.protocol.metadata.ResourceMetadata.html` | `58f21a20cb85c7750fd98984fd5a9626391ee3149541ea6742ab1801bd327554` |
| `M ` | `docs/orionis.mcp.protocol.metadata.ServerInfo.html` | `d1723a1877c35d7b8cd4c867d5e732cb52f8b8aad2a95f1232987baffc1f91a0` |
| `M ` | `docs/orionis.mcp.protocol.metadata.ToolMetadata.html` | `c823adc9fb39361c982c739bcded23bb6fcb5003c458bb1bcf8b95d1edebea2f` |
| `M ` | `docs/orionis.mcp.protocol.metadata.html` | `bfead88afd9aee6852ed84414d52fd59a3f96dd9f1d3da133a0b803defe78a4c` |
| `M ` | `docs/orionis.mcp.protocol.metavalidation.html` | `9070cecd165ada01a8f60211ad814aff8133e31a443221a528f74b81c6f8b178` |
| `M ` | `docs/orionis.mcp.protocol.mrtr.html` | `88e8da32aac8108da95c20db7fe5c380c3c52edd912d217fbe66e1282aaf9d3a` |
| `M ` | `docs/orionis.mcp.protocol.requests.CallToolParams.html` | `957f5824bf72bbb7c6c9616142731b64e08ef1a00ccb360a20ec92113121fe63` |
| `M ` | `docs/orionis.mcp.protocol.requests.CancelledParams.html` | `3475d56db787f03fce8554e305e42c45e6b16a5bacc093161abd1bce6701b1ee` |
| `M ` | `docs/orionis.mcp.protocol.requests.CompleteParams.html` | `907a5f74b43dc066c8b4bf392ff131fa19c53fbf36833545d30ade9cb482e020` |
| `M ` | `docs/orionis.mcp.protocol.requests.CompletionArgument.html` | `11a769690c878452b1f78c3fc36b4022ac1beae74d07835fcfdd9e96dabd5fa1` |
| `M ` | `docs/orionis.mcp.protocol.requests.CompletionContext.html` | `d0ad3743b612c1eccf334be8bf178c72033968b913a6a27cf3a5904b3387795d` |
| `M ` | `docs/orionis.mcp.protocol.requests.GetPromptParams.html` | `af255c979074f562df1f14efb4001746f964d5e56dd0b85f5039e4e1df82b65a` |
| `M ` | `docs/orionis.mcp.protocol.requests.InputResponseParams.html` | `ff805396c701a5c465b278b33287663c64ef85972dfe6d5a24498adf5b05c896` |
| `M ` | `docs/orionis.mcp.protocol.requests.JsonRpcRequest.html` | `606c7fe48c4b637c8b5fc6b937baefbc365417d7210ec8defb8a5ce703c73e99` |
| `M ` | `docs/orionis.mcp.protocol.requests.ListenParams.html` | `f3bfd2d743716f261e01c20cb487118f68962866e83d1ca70aada93daba2a3dd` |
| `M ` | `docs/orionis.mcp.protocol.requests.PaginatedParams.html` | `c4b22967184bf1b02e6ffc1e77c2bcbd00f24bb035a9b0aaa2797764d68855c3` |
| `M ` | `docs/orionis.mcp.protocol.requests.PromptReference.html` | `61947e7fd7acd4c9a9d15fedc1487323755b86f3b25fcbda632c2f3bcd6a4d49` |
| `M ` | `docs/orionis.mcp.protocol.requests.ReadResourceParams.html` | `f1b98df329e0bb54721e1c797c7da6d44bfd5525c8f1674ef37647b1ddb1ca44` |
| `M ` | `docs/orionis.mcp.protocol.requests.RequestMetadata.html` | `476409d547a02425b5e5bdc940fd1ab8eb8f59cd17763f5a63501526d16d9c62` |
| `M ` | `docs/orionis.mcp.protocol.requests.RequestParams.html` | `5f4c4268926dafa90165bf22182c9c5eebeabb48ff88b0702488b54e81068155` |
| `M ` | `docs/orionis.mcp.protocol.requests.ResourceTemplateReference.html` | `96f380275bc652ebdb6ab5dcc304b0c948e4d3a74ceafba39bc6112c7fd92028` |
| `M ` | `docs/orionis.mcp.protocol.requests.SubscriptionFilter.html` | `24f6d0435a6e8e3eb89d75ce931d8177898901c29cb80cee7b87816d9d7f1d48` |
| `M ` | `docs/orionis.mcp.protocol.requests.html` | `a76d45a94367f28e814634b9b6c87a5d05a3c17a1180d05299639b413f54f121` |
| `M ` | `docs/orionis.mcp.protocol.results.CacheableResult.html` | `82f53e3f1045d62d6a4f101ed35fe3439226af7497b68de827b42ad2025f0101` |
| `M ` | `docs/orionis.mcp.protocol.results.CallToolResult.html` | `9e10ee53b077b622582109cf81a498cf3f9d9eb18a2f4ee83eec342d07e4245a` |
| `M ` | `docs/orionis.mcp.protocol.results.CompleteCompletionResult.html` | `47383507ccca0ffab457934ceab56f0cd8158441ac75731abfba59ca8dec592f` |
| `M ` | `docs/orionis.mcp.protocol.results.CompleteResult.html` | `b7ef42cea4dc8072cbcd8e11f604c1e36c12a442736140556e5f4f2f1b3feedd` |
| `M ` | `docs/orionis.mcp.protocol.results.DiscoverResult.html` | `1a43bdec2e9acba3cdb6a5ad98f67d5cf8bb3558961e730fb7e02d95d0fdfa71` |
| `M ` | `docs/orionis.mcp.protocol.results.Error.html` | `8118ca51413b73711a28e99f89b271dbd3fe1d59c61eb4deca2ed8f30cf3c7dd` |
| `M ` | `docs/orionis.mcp.protocol.results.ErrorResponse.html` | `173261cda350736a832d197d891d23f48a83064feaa57d4fe6ca1de0f7077e1c` |
| `M ` | `docs/orionis.mcp.protocol.results.GetPromptResult.html` | `f34b98f002054120ae9d3e7d8355beee176b00760397542a42ec8063e6786ba0` |
| `M ` | `docs/orionis.mcp.protocol.results.ListPromptsResult.html` | `ea36c0b44211b87d24d6cbc62a5f70b512c3ad32ead5aec010fc26316da6bc3f` |
| `M ` | `docs/orionis.mcp.protocol.results.ListResourceTemplatesResult.html` | `366d089c623bf1166053e22710d6aab6ac600090077eee9093d8e2234e147314` |
| `M ` | `docs/orionis.mcp.protocol.results.ListResourcesResult.html` | `ff999dd3816c699b03bca0ddbeeb51084df2d6434c289146059e78b2a057362a` |
| `M ` | `docs/orionis.mcp.protocol.results.ListToolsResult.html` | `89507c956d9afc60b0d79ce482781a1b164551dd054dd2352306954e1901be3d` |
| `M ` | `docs/orionis.mcp.protocol.results.Notification.html` | `c977bcb21cd1d4fa7f3f3890b293cf49d75c88844a606bb783196f73227c899e` |
| `M ` | `docs/orionis.mcp.protocol.results.ReadResourceResult.html` | `1482ba48fc95708917409a5ee99fd3ce66eb1459f3e28fd19834bcb6fea50779` |
| `M ` | `docs/orionis.mcp.protocol.results.ResultResponse.html` | `91b86c1ce52fcd7c0d6b083e117d8624bdb23ea127e707f8ac384585e0ecd06f` |
| `M ` | `docs/orionis.mcp.protocol.results.html` | `ece77d479b3a69c9cb3a8b91aeea5f98d4e422027db2bc414fa293748ca2cba6` |
| `M ` | `docs/orionis.mcp.protocol.validation.html` | `2c22aa5fd8f89515384bd958ea14e77bd55774922f99bd4eca8a6b98c5d25b8a` |
| `M ` | `docs/orionis.mcp.provider.McpProvider.html` | `a9120e87d66b6e9aa0d794ccd87cf71676399b4e3ee2b4b0ed8547768eb52e42` |
| `M ` | `docs/orionis.mcp.provider.html` | `5d68057750f80eabb16b56cd5f945428c918301c5ae6ec499b75674ed3464f52` |
| `M ` | `docs/orionis.mcp.reporting.html` | `0070ee50e0c43bfad484e94e9cdb07ed0aacdd630713926eb027238f434923af` |
| `M ` | `docs/orionis.mcp.responses.Progress.html` | `afe455901598d17d0d8af1fce8b46e3485645d8fad8e9a881e8772198da5f7bc` |
| `M ` | `docs/orionis.mcp.responses.html` | `30d54eca0687186450de064b129dd9739e6cf2fee504eedf71cae07bec0b8146` |
| `M ` | `docs/orionis.mcp.routing.McpController.html` | `fba2cd22a53e5f8a0c63fbf63cb60178b306513fab3b3f76e431a96a4296b5d5` |
| `M ` | `docs/orionis.mcp.routing.html` | `773407f696dd96c4276ab16ee28d2a0324ca944b43d126f23c44fa078824ff21` |
| `M ` | `docs/orionis.mcp.server.catalog.html` | `7c1ff39eb409258d2aa854505118e9d1b55ca0563897e59c757824f811436c65` |
| `M ` | `docs/orionis.mcp.server.compiler.CompiledCatalog.html` | `e2f755bb5d72409c144b358c739dcd0b301f0ff88aa757ca91466fd79ce933bf` |
| `M ` | `docs/orionis.mcp.server.compiler.CompiledMcpServer.html` | `3ab395afb40404fb2a6ac5ba4804a2b97c1b4b9423fad6d7b362da261d373483` |
| `M ` | `docs/orionis.mcp.server.compiler.CompiledPrimitive.html` | `8c6c4f13f438340d815627bcd771c402bed7b9e55bd2c3bdbca16bb78b47d8c4` |
| `M ` | `docs/orionis.mcp.server.compiler._CatalogCall.html` | `83232f5cc7efd2d0008a56231a35fa048ca31867d289dcd73ae68b37a01bfa8a` |
| `M ` | `docs/orionis.mcp.server.compiler._Compiler.html` | `6abdc09b1cb03049cb132f84e323dc666735af8022657644749f9a982b8e81ba` |
| `M ` | `docs/orionis.mcp.server.compiler._ExecutePayload.html` | `da890c220bf1ef549f9671bc76505906aafdb1d91c7f55f43c82ea7e87ceff7d` |
| `M ` | `docs/orionis.mcp.server.compiler._SearchPayload.html` | `a753dd222e794cf8e098eafd7bf0a0879ec1857655c98c77bc7b041a516be5a4` |
| `M ` | `docs/orionis.mcp.server.compiler.html` | `9d577bfaf3124bacccf305a4de5fc579b708e4cc2be87a929685a8a07b3038c0` |
| `M ` | `docs/orionis.mcp.server.extension.html` | `f6c697bbdc3f15bbd4ec1f775cc8e642097a6e8dbffc1d74996c950ef5952863` |
| `M ` | `docs/orionis.mcp.server.html` | `d0f5f1486aa5b961acf3f15e6cee07a6910d0da842139fc3acd7cd3bd5adf8f6` |
| `M ` | `docs/orionis.mcp.server.package.html` | `eb3d7d6eb38674c22e47820f9483982e7899764e5b2993b113f1a687e8a23d96` |
| `M ` | `docs/orionis.mcp.server.primitives.Primitive.html` | `3cfca3b630cb6931e6bee0a54b12e74d2441c101ebe5a8a791631f6a1045a145` |
| `M ` | `docs/orionis.mcp.server.primitives.html` | `028dfcaf298a220ca68b17c0e0d4ed09e301d957cc8395f49ee1aeabe0eb7730` |
| `M ` | `docs/orionis.mcp.server.schemas.html` | `2898c3cf29a1a708b8cb8961f9cac41678baaf7b22866854ff0c3ad2ceb63afe` |
| `M ` | `docs/orionis.mcp.server.templates.UriMatcher.html` | `38ce5fa7b459c4f2a818896c21383ebfaba260307d1dfc65fdf79e1ca0f0b2b3` |
| `M ` | `docs/orionis.mcp.server.templates.html` | `117deb2261c7626c632c8cf6b0062adb3281d4edbc3e13a23e4c0faa75b05334` |
| `M ` | `docs/orionis.mcp.state._State.html` | `aedb91ad343e6d41dc0883e9c8b281efc3ed8d278fec2dc93afbb8f5695f4777` |
| `M ` | `docs/orionis.mcp.state.html` | `356093044248dccec3a1d50941076618c79dd0ed23c9a59b0449fefc53ff14a5` |
| `M ` | `docs/orionis.mcp.streams.AsyncClosable.html` | `a9b4eca5a53e86751667e5a9a87bbf6dde12e29e3dd5b141517fdbd36779d889` |
| `M ` | `docs/orionis.mcp.streams.OwnedStream.html` | `34e178d02b702ae9e0f8eda62830ee2ee17d505eace904c225a0b19f9e2379d2` |
| `M ` | `docs/orionis.mcp.streams.html` | `ac94ff8d98484ce3ac4c96e00d2a5edbcbac46a63b3d047d3818ebdc7dee661a` |
| `M ` | `docs/orionis.mcp.subscriptions.event_bus.InMemoryMcpEventBus.html` | `7d8ed34d52c87225aba9cee70604857072fe5f0b2744a0bf43f427c44f22c171` |
| `M ` | `docs/orionis.mcp.subscriptions.event_bus._Listener.html` | `e8d94a362c2feb86a9847be9683e928d413328f14829b93beb757eeae19e276a` |
| `M ` | `docs/orionis.mcp.subscriptions.event_bus._Subscription.html` | `c1761f2d2b0ed3db21783ab0375a41735a9a8cc6f32306ea836be751ddf2f622` |
| `M ` | `docs/orionis.mcp.subscriptions.event_bus.html` | `7ca49960282ef397d33aad75ce745d3a9b503590b5f42379d43c9054f65421a2` |
| `M ` | `docs/orionis.mcp.subscriptions.html` | `0135c3cca6f6f9ebf9c230a0b13342795e60526d127b0211e77bf8f9e0443b07` |
| `M ` | `docs/orionis.mcp.transport.headers.HeaderBinding.html` | `e0fb20a199eefca875d97b93de2e7113f19701c0f936152fc838d0e3337cde5a` |
| `M ` | `docs/orionis.mcp.transport.headers.html` | `0ccc36d1e0b21264ff41ab039d1f726ea34a53281e20f7b4d2cc83f378220301` |
| `M ` | `docs/orionis.mcp.transport.html` | `958cb66a2044360b86811164238e74f2e246f30ee3ba19c767b72ffd20c8c2f1` |
| `M ` | `docs/orionis.mcp.transport.http.McpHttpTransport.html` | `99080a23b667977e4acec5c6109895eea39c2d9227ce95e64368a4aa7126f9ba` |
| `M ` | `docs/orionis.mcp.transport.http._EventFrames.html` | `6d42329d400cca90891325cbaa34c509741a7ec071c49cd46e48ee9c3548b5ed` |
| `M ` | `docs/orionis.mcp.transport.http.html` | `31c823e885a449baf5c086d7d8e679528e3818b35e3293904b9f158829f9b7d5` |
| `M ` | `docs/orionis.mcp.transport.policy.McpHttpPolicy.html` | `30e4dd230d3092a5ce13927c3d7f0b7f8ec06304531378af07c7975cfba23f22` |
| `M ` | `docs/orionis.mcp.transport.policy.McpProtocolResponse.html` | `2edfbbb1925f55db95ea7f55a6e0cc2316beea766d029d20aefaa87c60d9b3fd` |
| `M ` | `docs/orionis.mcp.transport.policy.html` | `fa6e0267f7600297e8e4e41323e501528f5a941ee9468ee3a05863a3369c5fcc` |
| `M ` | `docs/orionis.mcp.transport.standard_io.StandardReader.html` | `4ce0003f74cc2cdcaac138c97c4c6199efcc509f7c544b4d7e07268c6f19114a` |
| `M ` | `docs/orionis.mcp.transport.standard_io.StandardWriter.html` | `b3a0328c817a1c7b5de878f026a0fc4e6298053ae1864f0210eabf94449f140f` |
| `M ` | `docs/orionis.mcp.transport.standard_io.html` | `9c7b4e0daa027630d74492092618a2a1f2f1c06039a3cf061ca3aecebfe1e8a9` |
| `M ` | `docs/orionis.mcp.transport.stdio.LineReader.html` | `9a80bb07566101e167c4666019c5f7f248a2de460e89b6a75f083cc1d054b139` |
| `M ` | `docs/orionis.mcp.transport.stdio.LineWriter.html` | `7c79f1e7e6fbf274d1aa4d538756accc8dc62ba4f67b8d03fac38a36ab838935` |
| `M ` | `docs/orionis.mcp.transport.stdio.McpStdioTransport.html` | `b199e0f75120a69f6ef9d86beb81c6942dff80997d98222b9822f12e8abb925b` |
| `M ` | `docs/orionis.mcp.transport.stdio.html` | `483af4d333ff6b2b2ef5af79bbb6668e5a369733a79694858cf9e4e3a16d5735` |
| `M ` | `docs/orionis.metadata.framework.html` | `042967ba2d682f6e4a9aeb3ec810f5c53b42ad5e69d8344b7a6945794eb4dd15` |
| `M ` | `docs/orionis.metadata.html` | `64a9ec386546b710dbfea61d383f935dc4357fb25491e6addf2425632f43a157` |
| `M ` | `docs/orionis.orm.ConnectionResolver.html` | `0acddc00591762c02c2547ce09024a0e3804528435a1b6d4f62c3dc5f8d386b0` |
| `M ` | `docs/orionis.orm.attributes.AttributesMixin.html` | `8fb75ab0e49a70b8de5601a70224f4c853bd0babb8b69ebda529705b6ccdbabc` |
| `M ` | `docs/orionis.orm.attributes.html` | `21c56854e978d825ef26cb73f8668437039c970cc3c896a7b5edb70d295352af` |
| `M ` | `docs/orionis.orm.collections.collection.html` | `da49a105c9c75c49a70be66d6ab8f5f309d2f55c4655d55b60d313f825437e16` |
| `M ` | `docs/orionis.orm.collections.html` | `5276e7d2e71647450ea200ab9ab17e0c763ffc9615be0dc9f7160ccca5853a9d` |
| `M ` | `docs/orionis.orm.collections.paginator.html` | `1a651489db3af37ed4e8c3b2e557e9b1bba18a8664b3eb5ffdd4f6b74c3503ac` |
| `M ` | `docs/orionis.orm.collections.paginator.module.html` | `9b5abe9bd9c4a3ec5116b9728310e7ae34dafcacc69be57a513e111cd5a834eb` |
| `M ` | `docs/orionis.orm.contracts.IModelQueryBuilder.html` | `41078be97fc2af20d8fcd1938db2c16d15e29056d66ca47ea9d4698e34f7501c` |
| `M ` | `docs/orionis.orm.contracts.base_builder.IQueryBuilderBase.html` | `2fca8214a27576b56909272b43205a6d4333dead887213fbb8516b2565c76251` |
| `M ` | `docs/orionis.orm.contracts.base_builder.html` | `d656c793e690b7accc0c5260a6d3022465f05604c8648daecbe161f2f8a4ad2a` |
| `M ` | `docs/orionis.orm.contracts.belongs_to_many_relation.IBelongsToManyRelation.html` | `963086a5c8bfdf52c2d300c01e4a13678b075876d1c43a7b9b69a4e318c39f24` |
| `M ` | `docs/orionis.orm.contracts.belongs_to_many_relation.html` | `a8dbded2522c6a4f54208bc8dd03b9ce28cfaaea3bb0b35bfe70d960d5c8c3cc` |
| `M ` | `docs/orionis.orm.contracts.builder.html` | `fc32af58e162dea0d99ff29f0d37d08ea581806480819d54f9457f621c0650ea` |
| `M ` | `docs/orionis.orm.contracts.html` | `52a6fee52e48147f2b16e4e9178e887f26bcefd21b23b950c34af0bd43b20aa1` |
| `M ` | `docs/orionis.orm.contracts.query_builder.IQueryBuilder.html` | `598be03b2dfb56a63255270f772e8da48a634a20ff72327fc06481b0796b9220` |
| `M ` | `docs/orionis.orm.contracts.query_builder.html` | `87fc1d8689e89e0edaf7b6456df1215c92dd74b06fbd1e6fd0507f0fc39d5653` |
| `M ` | `docs/orionis.orm.contracts.raw_builder.IRawQueryBuilder.html` | `7cd9e55f07de81d44b0a287951eb777e9fc0d12ea7986214804d830d20274248` |
| `M ` | `docs/orionis.orm.contracts.raw_builder.html` | `bc37e5206c5d6c6185d1413aa5f9cc13ce9e1b03f1fa952eb7b8701720e36587` |
| `M ` | `docs/orionis.orm.contracts.relation.IRelation.html` | `8ba824a5e92ff5b9cc47643f171ef51888ce823a6b08a2e03a0f1f79527d0fef` |
| `M ` | `docs/orionis.orm.contracts.relation.html` | `a908b7c24d29008b5160dd71243dfae86a568b2a4d68d488aa767048dc5e5e9a` |
| `M ` | `docs/orionis.orm.events.EventsMixin.html` | `be82027db91fdcd9cc90ab211a8434108ee2dc5d2f569ca33d7cf72d9d1e61c7` |
| `M ` | `docs/orionis.orm.events.html` | `15f022b9b4ce8ff5577b04015ffa0af6db20b9f60a76ccb0a87a3a4da0286bea` |
| `M ` | `docs/orionis.orm.exceptions.InvalidQueryException.html` | `ca016ab7e1300d4d957865dae87ccf46714734d91b231a0858531842b675c6ca` |
| `M ` | `docs/orionis.orm.exceptions.MassAssignmentException.html` | `6ea06f699b3a018362242ec84d56258b1a593c79215e8f9c02ded881f3268a2e` |
| `M ` | `docs/orionis.orm.exceptions.ModelNotFoundException.html` | `d421ac520c2ce4ae6d8a8f152221c44927a832fcb4a35241c980a2a3694f891f` |
| `M ` | `docs/orionis.orm.exceptions.OrmConfigurationException.html` | `87cbcca4bce053293402ce7e6695916b64070a04053cb1d5fc3e35b8e9e88dd1` |
| `M ` | `docs/orionis.orm.exceptions.OrmException.html` | `d60d63fe2f7176f95698ebdd4db939187e55d2ec78eba913033b2c34bb5399c8` |
| `M ` | `docs/orionis.orm.exceptions.RelationNotFoundException.html` | `251f164b00c0f8969c43f9c20f524e09ec3f5b86616830fba11bd8d7846ef04e` |
| `M ` | `docs/orionis.orm.exceptions.ScopeNotFoundException.html` | `14ec063332149958a16bd281e3fde9cc0ff44444c9e6b722e219d8a3a932eb5c` |
| `M ` | `docs/orionis.orm.exceptions.html` | `a62e14c11df7d7d7bebaff40ff87fbb50f02a0ff85ea6222d2c0d6eae47aa975` |
| `M ` | `docs/orionis.orm.factories.FactoryConcurrencyException.html` | `19c6ad6689eb33b80161c9644a3df3309f6f5bdb45d319a5fed15a431eb43483` |
| `M ` | `docs/orionis.orm.factories.FactoryConfigurationException.html` | `86c54266b17af01d3502d6f3480290f860c045856c2f27bf12fc1300bfbce209` |
| `M ` | `docs/orionis.orm.factories.FactoryDefinitionException.html` | `b3ea3648e0cd3542d19c36ecd6467ce0dd1f03d61f64eae8f5904bd6ee14bc6a` |
| `M ` | `docs/orionis.orm.factories.FactoryDependencyException.html` | `956c4b79e30ab6d3f4e40786a83ec90300ad2f4c1b9006480c0f2d7a1379eb01` |
| `M ` | `docs/orionis.orm.factories.FactoryException.html` | `c7a0b2dee14684f652ff1ce6fb09b92769963eca15603b98bc34f9c7b71f4e7b` |
| `M ` | `docs/orionis.orm.factories.FactoryPersistenceException.html` | `2181bd9a76ca7809b9d98e551e5efdf1c9c060cd7239830bc773487fce60df18` |
| `M ` | `docs/orionis.orm.factories.OptionalFake.html` | `bfaa106a9ba8e4f4cafe7cd7199cf6d0eb386e600784e9392038c7ef632c4cde` |
| `M ` | `docs/orionis.orm.factories.UniqueFake.html` | `adfcc21091e6e405b2e0ba2424324c27a316513199f0214adfabe529730303e2` |
| `M ` | `docs/orionis.orm.factories._attributes.html` | `c9a8ac3099c548f4d2d40cf60a2caf74c5769073d13d4733498d2deb687568d3` |
| `M ` | `docs/orionis.orm.factories._faker.html` | `e1ceecfdacf3ab311473e97588e0404db74783b2147716eb9f6b3f4036d98fa5` |
| `M ` | `docs/orionis.orm.factories.exceptions.html` | `37b53a224c277d3e8916bc3ab7393c8cc846b2b99578c047e276e6ff4b262278` |
| `M ` | `docs/orionis.orm.factories.factory.html` | `c255eeb0a31a59ad6fd0453c68d3b43bb3f5e57a570ba8f553c75f2b07d5bc19` |
| `M ` | `docs/orionis.orm.factories.factory.module.html` | `4abc98a092027f899cc8f8141647a12eeca17a49075b2fafbdb1af57f192abf6` |
| `M ` | `docs/orionis.orm.factories.fake._ProviderState.html` | `c0801e031acd493359a4387824ef2d02a0b17c95425010cb321897c3b7291c07` |
| `M ` | `docs/orionis.orm.factories.fake._ProviderView.html` | `afaba04d6a031525910c3bd15a2e73ab5898183559aaea4148a8452be10d3912` |
| `M ` | `docs/orionis.orm.factories.fake.html` | `508e9308b269983df3f5e7ca4abeecb20af7b615fbcca81ce09d435a5cd490ca` |
| `M ` | `docs/orionis.orm.factories.fake.module.html` | `15f826185de8329f4ffa7edefdade321406437681de728dca3d87b2c3dcac10d` |
| `M ` | `docs/orionis.orm.factories.html` | `3249760e765f3430d5e6348d8c95175973f51a06a0c4381047715093aa375ee9` |
| `M ` | `docs/orionis.orm.factories.sequence.html` | `d8dca38317a303544c38fabc4f50215f21674cb370bc950c7f37b3ab99d4f68d` |
| `M ` | `docs/orionis.orm.factories.sequence.module.html` | `761f2c4673b13a619c773078a7a552db778416d536a646497cfe48ad0b4be42c` |
| `M ` | `docs/orionis.orm.html` | `e71b34efe57d8d6c43eb06323ab0358265e990f17cc1a1b008e29a1d1f02f22c` |
| `M ` | `docs/orionis.orm.metaclass.ModelMeta.html` | `a26dd07807033d2b541e76dcbacd4dc94cf547b90f521db8851946bdadd527c7` |
| `M ` | `docs/orionis.orm.metaclass.ModelMetadata.html` | `61e2b1161da66d6066c9a4aa1159206379a5d3ca1688299cf3b1a1ae9c18818f` |
| `M ` | `docs/orionis.orm.metaclass.html` | `4c8f4dda0d58f0d5df9e895265ab875891abf00a7db42a1062aeec21435d01f2` |
| `M ` | `docs/orionis.orm.model.html` | `e5100c2c3d14e819a68399dc35a10627b6bea3f81a869676159d152780fbbf79` |
| `M ` | `docs/orionis.orm.model.module.html` | `63430dab10eea288eca4bcbd04290eeac60a7d1bd0eb37b7d67212ea13468f9e` |
| `M ` | `docs/orionis.orm.provider.QueryBuilderProvider.html` | `c5b6fa526e9e20af26c6b1cc743b6514d853a5c22ef1a7c015b9e99796242d9a` |
| `M ` | `docs/orionis.orm.provider.html` | `c05d8a54f075dfbca239b0010ac175626fc9250d21da0bf210d6eeb768d03764` |
| `M ` | `docs/orionis.orm.query.AggregateClause.html` | `c02b45f3b3645851b89a09499af6c3e225b360e2d24f519e9d4edda3310ff41e` |
| `M ` | `docs/orionis.orm.query.AggregateFunction.html` | `f7c9c7b62cf34fdf0a085da4d96bda8b7b474418f410d1d04cfc0209315b962c` |
| `M ` | `docs/orionis.orm.query.DeletePlan.html` | `fe1f5700ecf87c3955e140e1b72be0c272b26a1c2e05c659d78e1798e24f50b3` |
| `M ` | `docs/orionis.orm.query.InsertPlan.html` | `a255ec830b96a1018e330d2267e6f5f1ec646508af57558d7734fa143883ce5f` |
| `M ` | `docs/orionis.orm.query.ModelQueryBuilder.html` | `201c39cb28fa92b2b5a70034dd2c04ec3604bead6a824c6792f8625270c387a8` |
| `M ` | `docs/orionis.orm.query.OrderClause.html` | `3be55820bb09ea3600b799d1028a677b06b337c3f54a16ad1c6f8f7c1eeb312a` |
| `M ` | `docs/orionis.orm.query.SelectPlan.html` | `f3d167485f5f10957ed337519a7bc8a935d8e2f9fca74a090517b55e5fa51c5d` |
| `M ` | `docs/orionis.orm.query.SortDirection.html` | `37e928febe693d7fc349b1481d92b81c0ad74ed76bac3be534c677f7848709c7` |
| `M ` | `docs/orionis.orm.query.UpdatePlan.html` | `882ea67e9b7b389fda21860f64f8de051393b5c03ab0c676a558c2f4cbd9eeaf` |
| `M ` | `docs/orionis.orm.query.WhereClause.html` | `1014b97125b060fdbcc5182a9c2e1766d778a3d63e7ceee922f75f3f9de7ea5f` |
| `M ` | `docs/orionis.orm.query.WhereType.html` | `c5711b572c23a9d049ef906b5260cb5f1422af18cbbae9f8a7b1a167d2c88969` |
| `M ` | `docs/orionis.orm.query.base_builder.QueryBuilderBase.html` | `1ddd23f2ca9146050bae988af17e917759a79603fabca6f53c35518e6c8fc020` |
| `M ` | `docs/orionis.orm.query.base_builder.html` | `f172678ee5c1af44a4aca7f1aeec7d65fc6edb8517a3fe26a8ca8ade298961e2` |
| `M ` | `docs/orionis.orm.query.builder.html` | `45349b003db521188353aac4de5a0e9f9686c678b1515137007d03f9d99d0cdb` |
| `M ` | `docs/orionis.orm.query.expressions.JoinCondition.html` | `1ad706ea938ce683cd2d74aa9ceba11f881d5a906aa50c917b39ed4e835432a2` |
| `M ` | `docs/orionis.orm.query.expressions.JoinExpression.html` | `95b83581c5e2f779621a36fd6c085edf192dc0e399990d3768c0be8fa41449e6` |
| `M ` | `docs/orionis.orm.query.expressions.JoinType.html` | `8fe6d87a4ca349c8f977d401429b9d91c94e93f7d5e4313a6a57032bcbcf172e` |
| `M ` | `docs/orionis.orm.query.expressions.LockMode.html` | `b494aa85ce0801d874f648e01abe7ea6bb2c60be6777f6b8fdb70b449a5a55df` |
| `M ` | `docs/orionis.orm.query.expressions.RawExpression.html` | `e6753e191b84aea4017d107fddea56b891ad96fe9c8ad964ba33f830918c4c17` |
| `M ` | `docs/orionis.orm.query.expressions.SubQueryColumn.html` | `745aa1caeff0a93aa654945792e987d93afb017ec9c2d553fc75f01dc550020a` |
| `M ` | `docs/orionis.orm.query.expressions.UnionClause.html` | `e51d833d7c55dce330a12f842f9010faa547bee63ba2038bd3af142151ed3e54` |
| `M ` | `docs/orionis.orm.query.expressions.html` | `fbc6fd9930ab8945fe48d7f99092cb90ef450f13411b8ee6e813a6d04cc02c4d` |
| `M ` | `docs/orionis.orm.query.html` | `f0b07266afb87d5d4f33d397fe71f221da656b81286f3a0e4eceeb69147908e1` |
| `M ` | `docs/orionis.orm.query.join_clause.JoinClause.html` | `eba686ceb91209fe2254929d54540091d0dc9b987254f4152a0b40c03258ae55` |
| `M ` | `docs/orionis.orm.query.join_clause.html` | `af2093d964545bd62784eab3cd2a958aad929c4772dfef761588e8e2b674c53b` |
| `M ` | `docs/orionis.orm.query.raw_builder.RawQueryBuilder.html` | `c7f3b669a296ef463a2b1561c18a138ac63b4969063e1e14ab3d24c37959b036` |
| `M ` | `docs/orionis.orm.query.raw_builder.html` | `5b3c993586aa33bc3f8e279c504a0c3fa6eefc7d5e05cef7783e86dd0ab23ff0` |
| `M ` | `docs/orionis.orm.query_builder.QueryBuilder.html` | `a100f0f8d14a32453a0f0c0127dbb343a78350c026fb1d2ac13f7d6cc78ec578` |
| `M ` | `docs/orionis.orm.query_builder.html` | `e9cfbf396263f957bc02263830ee519a5c59d31f7c4483d0fb6f3f27c8cc31b6` |
| `M ` | `docs/orionis.orm.relations.BelongsToManyRelation.html` | `4514cc41bbc74976b9cce48038c7579326b3861a1f1f0a4d1b2653eb7b22596a` |
| `M ` | `docs/orionis.orm.relations.BelongsToRelation.html` | `f986f0502753153a4d668efd8678f2962f08c0d958839a357cf1c881b23c175c` |
| `M ` | `docs/orionis.orm.relations.HasManyRelation.html` | `d7317a0fc4a9919813c9d4d28ed7e51641346fe7b68b477ac1a14239192a379d` |
| `M ` | `docs/orionis.orm.relations.HasOneOrManyRelation.html` | `669dde0f2ed672298f43b34b7a14e1439cfacc60c61695daa246787bfe6d0878` |
| `M ` | `docs/orionis.orm.relations.HasOneRelation.html` | `6cd93e21a8d034ad572e339da2978d5faab363f4d3a488222e69eb923a78327d` |
| `M ` | `docs/orionis.orm.relations.RelationsMixin.html` | `c9fab68ed9410691f111a5e30056dfb8e6dd06d01c35e37034fab585f7ee17c2` |
| `M ` | `docs/orionis.orm.relations.belongs_to.html` | `b59d9b4b23160d37e8d57e8f79a3dd460f39692d2b46023be7f5087e22c895bb` |
| `M ` | `docs/orionis.orm.relations.belongs_to_many.html` | `35bfbf10b3662539b4b62451e6087b611a0dfb5778517b133a700f17309c3bf9` |
| `M ` | `docs/orionis.orm.relations.has_many.html` | `dbff4da59516264281861fb8c5952edd3050f80450f3d79f602f3e93b3d7ab7f` |
| `M ` | `docs/orionis.orm.relations.has_one.html` | `636e764b25cdc354469dbdcf86343d4ebdb34f2c83c774f3647015c52e4000b6` |
| `M ` | `docs/orionis.orm.relations.has_one_or_many.html` | `3faf35e1490458936cb986406e508eca56188296c2ef1fe66cb432d5f33774a7` |
| `M ` | `docs/orionis.orm.relations.html` | `7ffce517ffb36f0ef983a51c4edd965618b14c1c88d1fc88755f470372787ea3` |
| `M ` | `docs/orionis.orm.relations.mixin.html` | `b1526a466323bfd5a372f34b3218d8d8918e1697730d4c30ab0ea583bfebf478` |
| `M ` | `docs/orionis.orm.relations.relation.html` | `330000cad0440f493e83959bf1b967d3c7c9adfde648565719424d29a721aab7` |
| `M ` | `docs/orionis.orm.relations.relation.module.html` | `f6daffec9b9d342684382185a58eb71d5430a933698bcf4066e8ce60581e654b` |
| `M ` | `docs/orionis.orm.resolver.html` | `bbbf5235f16ae777f6089edb319434f04a2dc73aa238a4a4adc0089e111eef7f` |
| `M ` | `docs/orionis.orm.schema.TableDefinition.html` | `bf7b257614a860eb16aaff52b2c930a59561fff6587f5606d42cc9f6fe1133be` |
| `M ` | `docs/orionis.orm.schema.column.ColumnDefinition.html` | `89d0bda73d80c45759affd6822c75477a138dc2663a89f1a8e82144d48740002` |
| `M ` | `docs/orionis.orm.schema.column.ColumnOptions.html` | `bc870c065a60b09ec0e7bbb49173d90127f52b6fd151f075a49031e7941ca3c9` |
| `M ` | `docs/orionis.orm.schema.column.definition.html` | `0252f4411c2a1c0a6a278834d17a04820f5db1036d3c966d6161812a5e3e67e6` |
| `M ` | `docs/orionis.orm.schema.column.html` | `577f71c662f581a9704d21581adbf00aa345f4010c5f291fe11d5dfd8c8f3c53` |
| `M ` | `docs/orionis.orm.schema.column.options.html` | `941c9ab195f12a318e9bccafc327c79567ce0d9a7e36042b3f3a8a5097a5a7d9` |
| `M ` | `docs/orionis.orm.schema.constraints.CompositeForeignKey.html` | `da263f1313258e433027d4f9c24e81bae813fc1f5e5d6f8f60ace3b531b3267c` |
| `M ` | `docs/orionis.orm.schema.constraints.ForeignReference.html` | `7adb70b32aabe4316d594a72eac95c4a6c626de716b0493304fd3222f7663c90` |
| `M ` | `docs/orionis.orm.schema.constraints.TableIndex.html` | `a562f6445a0206cffe584e7fac0ca891a2e79f82190b626d55939c77564bbdd5` |
| `M ` | `docs/orionis.orm.schema.constraints.UniqueConstraint.html` | `8e1d8cd48f50e7b31099f48ec9a123c1c76e7a972bfeaf9c5535dafef724ed3b` |
| `M ` | `docs/orionis.orm.schema.constraints.composite_foreign_key.html` | `4f5bc2e2eca96675fe7d05a1d7e74e3a2dfc942b8b649f802c8f5f37c520f056` |
| `M ` | `docs/orionis.orm.schema.constraints.foreign_reference.html` | `dad328ef312c72fe84573f215942c1f7a24a719b67240e08df68fb62a38f2e3f` |
| `M ` | `docs/orionis.orm.schema.constraints.html` | `e3abd226bd34062e8b8dfbf4190e890e406370b7190fcc1798db22fc02d3775a` |
| `M ` | `docs/orionis.orm.schema.constraints.table_index.html` | `c537579cefb3ff3fa1155f5ab0f582305f4eae513f05d3f275a0f96a06715830` |
| `M ` | `docs/orionis.orm.schema.constraints.unique_constraint.html` | `65244681adaed9b56391aa90e517451db0f43b245b7e7caa62a774f4b25f875d` |
| `M ` | `docs/orionis.orm.schema.html` | `31628459881b3f0e064bc67e0873a515de7f6ff8cfe3ea0aed831b83c732036d` |
| `M ` | `docs/orionis.orm.schema.table.html` | `6e052a4dd2e51ea28ca5d42399738e40219261e236d57d3108fec8b55c9b3245` |
| `M ` | `docs/orionis.orm.schema.types.BigInteger.html` | `cdecee08b40f8b3cd92a5ce4998794bb104aa1fa5e47b80254c633cf0d03787e` |
| `M ` | `docs/orionis.orm.schema.types.ColumnType.html` | `cf0c302a7e9c0a0b160a8f3f22feddc917ba6eb905ae691e90fa1d916ee9b0ee` |
| `M ` | `docs/orionis.orm.schema.types.DateTime.html` | `b40f266f917bd1d82bce08828d875da2692385822e2c9aa12e1a3e7775076edd` |
| `M ` | `docs/orionis.orm.schema.types.Enum.html` | `4ef8b831dbd58329cfa858b95211a5de976e8687a342dd41b87ad21743b8ac5c` |
| `M ` | `docs/orionis.orm.schema.types.Float.html` | `49a01e46b7b5efdf1b6a02efc610d03913d57e1aced5e7476f0df878cd437fba` |
| `M ` | `docs/orionis.orm.schema.types.LargeBinary.html` | `8ee7e60b2a38780c009a8d28700c197b109dddef39a6126a9fa5bdc725751ab7` |
| `M ` | `docs/orionis.orm.schema.types.MatchType.html` | `efb01eafea1fb6091d5b0ff3f013052cbba980ee23883d12d62cf1a340bbc36a` |
| `M ` | `docs/orionis.orm.schema.types.NumericCommon.html` | `91df8805508a5b50f891346c1e6a3d730e59f6b3844dc8663e7ec0528b67fef0` |
| `M ` | `docs/orionis.orm.schema.types.PickleType.html` | `4c9f794489318298c80d4eaa696beba28fc834f8e13ca54a65ddff1e25fc46ac` |
| `M ` | `docs/orionis.orm.schema.types.SchemaType.html` | `fe66e647bac887929e6151a55329119660bcf2874f0da0d76a8e20898a3a3e20` |
| `M ` | `docs/orionis.orm.schema.types.SmallInteger.html` | `1837fbcb90bb2b60184e4ce4f8bf8aec26f3154e76da87d5ae6394ce36e3f5ac` |
| `M ` | `docs/orionis.orm.schema.types.StrictArray.html` | `35126b8aef9682fe861d20db2861b87a6424a3aa41a1078f174db31d93297515` |
| `M ` | `docs/orionis.orm.schema.types.StrictBigInt.html` | `1cdfa43ffd0ba9c995a8531d1c25154c297d1e82d05fad23686fefbb3bebd056` |
| `M ` | `docs/orionis.orm.schema.types.StrictBinary.html` | `5a4aa656162a9d1bb08c4fda408251921eaee6cf45a276e7735329b4150d8138` |
| `M ` | `docs/orionis.orm.schema.types.StrictBlob.html` | `9749efdbdcde3a579c4f593f8a4aab100761a5b794651d373ea0e08dc3d43298` |
| `M ` | `docs/orionis.orm.schema.types.StrictChar.html` | `ef8e6dcc971aa1e96350390e47df243b3b753bb96764863116a7bd321cdd1768` |
| `M ` | `docs/orionis.orm.schema.types.StrictClob.html` | `f2557256e8de2d2fd9fc8e7da21316b3802fbcc758ba4ced981a067bc305e002` |
| `M ` | `docs/orionis.orm.schema.types.StrictDecimal.html` | `e75f2e919ec5a71887a919925d834062c083731ed08aaac3f1d609dd5719a0ec` |
| `M ` | `docs/orionis.orm.schema.types.StrictDoublePrecision.html` | `74dca0ecac3da49ab2a9789528809bb41e6ea4c4feeb782b7ae5afb0802dd24a` |
| `M ` | `docs/orionis.orm.schema.types.StrictInt.html` | `2b5d59b2992504c0ec64d68c06a2554f2d0a67dedd734ba542146b0b30c4acd6` |
| `M ` | `docs/orionis.orm.schema.types.StrictJson.html` | `d35cd40c94291dab70ef8aa33265548d9ca8c738d8bcfea1692fa7cd8d8921f7` |
| `M ` | `docs/orionis.orm.schema.types.StrictNChar.html` | `4545642b81685571f61859a4d53935024f1698fa3019c048415607ad940d780d` |
| `M ` | `docs/orionis.orm.schema.types.StrictNVarChar.html` | `950244245be951a064d7150715c83fa19d624565a4fdd5c89602e655794a8dbe` |
| `M ` | `docs/orionis.orm.schema.types.StrictReal.html` | `f6a0441a7185092930342ee4c5c76dfbb4387928b38e2b87035fcfa002833a3f` |
| `M ` | `docs/orionis.orm.schema.types.StrictSmallInt.html` | `2893d25882e35657c2458ad78c6f586c8d87d5fa648faa64a1ff94f64d615a30` |
| `M ` | `docs/orionis.orm.schema.types.StrictTimestamp.html` | `bc31bafbdd9b7a589e01d46341bd10258bb1d85ef1b5f3e81ad2d87dc1af6ef4` |
| `M ` | `docs/orionis.orm.schema.types.StrictVarBinary.html` | `5937c044bfe602989e68fa4bf30d2b129a9062bb0f1cea7db17772194a8bde6e` |
| `M ` | `docs/orionis.orm.schema.types.StrictVarChar.html` | `1c8e0cf0eb92af9a776f46aa78e6772aba186b104ff9f76e04bac84186e444cb` |
| `M ` | `docs/orionis.orm.schema.types.String.html` | `db4946d6341d7ff121b0da0dd6fc34189cc85c7fa69b56c46c1cc48a401a18cd` |
| `M ` | `docs/orionis.orm.schema.types.Time.html` | `1581b1638931336860b8bded5b715255add28139eb14c064d2a376b5439b3e22` |
| `M ` | `docs/orionis.orm.schema.types.UnicodeText.html` | `e01531afddc9a1f03351a8f3ba95baea75458f60412f74fbd4eb1971233a46a1` |
| `M ` | `docs/orionis.orm.schema.types.Uuid.html` | `69ec31369905933580e9330500bc47f0edb665ef9ccaf12482842fe102a6d0fe` |
| `M ` | `docs/orionis.orm.schema.types._constants.html` | `90d964d6c6907d51290fca53252a17d397303fffcbf063b9f297f292cd08616e` |
| `M ` | `docs/orionis.orm.schema.types.big_integer.html` | `d25a25c310826a6d78f991fc1e65753d5502c68501b6d50c3d409fef31c51020` |
| `M ` | `docs/orionis.orm.schema.types.boolean.html` | `3c11444ffaacc48432e303e74865453633f3b9d6452994f16037775b3bd984a8` |
| `M ` | `docs/orionis.orm.schema.types.boolean.module.html` | `d47c4a30f1caac54122f537527798bfdcc4216d292715f4495a9bda75e4798c5` |
| `M ` | `docs/orionis.orm.schema.types.column_type.html` | `013e535709004a205e22dcb6e6cf22a9f9b2e5762b6e076a096dd5972ff56b29` |
| `M ` | `docs/orionis.orm.schema.types.date.html` | `8f6087cb8448b1fcf2c2c0b520be981d44ad461cc013ae487ac4c3659a7ff943` |
| `M ` | `docs/orionis.orm.schema.types.date.module.html` | `dc35b233ffec2f8b40d63c58dbbcc023670bf40f85621b3c0c74cd9b6cbc5873` |
| `M ` | `docs/orionis.orm.schema.types.date_time.html` | `3c4ad55e7f42269f929ef9feb05023dbf134c69037c38354b1111c6f8c7c1906` |
| `M ` | `docs/orionis.orm.schema.types.double.html` | `f92ae54c2c126534bc083ca5d8d2783d6b87a1e1070b1638697e837f4a119d53` |
| `M ` | `docs/orionis.orm.schema.types.double.module.html` | `edd24fd72696d214c42d98b3efe976750edef041c156a704719c3f20968a62de` |
| `M ` | `docs/orionis.orm.schema.types.enum_type.html` | `19088c9a11ac31d20d698b749719fec8b2929f5413c9b8e9a6f65913a0b031ec` |
| `M ` | `docs/orionis.orm.schema.types.float_type.html` | `24f7380f00c3535b88b7ad38f6627f7a59d0c686c203745a707c12ce78f16073` |
| `M ` | `docs/orionis.orm.schema.types.html` | `1a72d2079787ad8856a2df585b03526c8df60a5e69ead87b77a260290acc3dc3` |
| `M ` | `docs/orionis.orm.schema.types.integer.html` | `4980023288e8f56fe2d094218a141c3f358f6505c14c75c126b026afdccc7916` |
| `M ` | `docs/orionis.orm.schema.types.integer.module.html` | `8a48b738c0c27b3972a8cb24acdac214b738ed8be1f9f2e140f5047591d15d7d` |
| `M ` | `docs/orionis.orm.schema.types.interval.html` | `4419e86e35da28d5ab1f00a1b43f6ce84da0c80830d9d53e06bcfa6545b355b7` |
| `M ` | `docs/orionis.orm.schema.types.interval.module.html` | `6601ebfa6180328cff6794632ea8f012227b44a578b966e634df2603139097ac` |
| `M ` | `docs/orionis.orm.schema.types.large_binary.html` | `b8c318802e0418d274e45e7a32fe4506dc151b06a0c31ccf5d429fcd07baa63f` |
| `M ` | `docs/orionis.orm.schema.types.match_type.html` | `c98b88f7007282ea4a6f27bfd93f9835f6d2f66630b335327bc8147c7182ca79` |
| `M ` | `docs/orionis.orm.schema.types.numeric.html` | `823e86e7c6764c6f5b7af1dc84b5f6c9f9d7a15933a4954d5febe82929230221` |
| `M ` | `docs/orionis.orm.schema.types.numeric.module.html` | `ffd2d8be541edb46315f5d9024db658e15fce921406a35a342a133ce32c295a2` |
| `M ` | `docs/orionis.orm.schema.types.numeric_common.html` | `db8b6188872a65b2f627c1d2f660c4a97e32da452e29862c70e16b92e5ef3e67` |
| `M ` | `docs/orionis.orm.schema.types.pickle_type.html` | `81420efb75c62ec69b5d5a204069963acda58c4f28e42887a5c5f32d6853948b` |
| `M ` | `docs/orionis.orm.schema.types.schema_type.html` | `8c743ceb0d2fc1f29edd8f84136fbb781100e4cc50d7cb454d7e2f194c765bec` |
| `M ` | `docs/orionis.orm.schema.types.small_integer.html` | `add9e8c08e6e4c556444be3b9e73ff930fecfa75b09cb9d94786fc69840d60b4` |
| `M ` | `docs/orionis.orm.schema.types.strict_array.html` | `a72a71b20f3ac5d06f3aff633dca0b8fe71203d501703d805f46410149a338bc` |
| `M ` | `docs/orionis.orm.schema.types.strict_big_int.html` | `905eab471382dc87ffeb301f50bc777a17da43bf19fb1ad37dff59c70a4e2aae` |
| `M ` | `docs/orionis.orm.schema.types.strict_binary.html` | `f37f673c5d2c35f41211a1379a0daeef3bbf3591f39794dc0282248250611e97` |
| `M ` | `docs/orionis.orm.schema.types.strict_blob.html` | `cf2d72236aca22c15a4c65672cbcf17a3757ac4a5b6e43c1865d74351cc7b95e` |
| `M ` | `docs/orionis.orm.schema.types.strict_char.html` | `47e648f15a6a97eb33b32cc285fd81d89a6d66a89dcb8d81a54e38564a7b33aa` |
| `M ` | `docs/orionis.orm.schema.types.strict_clob.html` | `27be6f3f48f52d96259b7300dbf44fb78a587e3d06e1053d243ce27444c59c9d` |
| `M ` | `docs/orionis.orm.schema.types.strict_decimal.html` | `3b814ca066e263c4428d914fdf5ca84561e6e851b378b7503e37cc060cc1c2e6` |
| `M ` | `docs/orionis.orm.schema.types.strict_double_precision.html` | `7f09a51bb1a82bd4b63a503bbad0c822d792064bef0a5e0ad9b0814cb4b09a83` |
| `M ` | `docs/orionis.orm.schema.types.strict_int.html` | `18f4ac605662e1ba522f0ac5b13c1fc5ccf91df28135e78ccc64dc246a078ebd` |
| `M ` | `docs/orionis.orm.schema.types.strict_json.html` | `9761ae9f4a2600f8a4452b19f6610853bd8c7b8f63d6368e83e28bd2acaf9f79` |
| `M ` | `docs/orionis.orm.schema.types.strict_nchar.html` | `264692beae3785d17784d480f6d00aafb65d976f84f3f4e1a9b4c2a6b650a4b2` |
| `M ` | `docs/orionis.orm.schema.types.strict_nvarchar.html` | `98b0492c9bd68c6892645552b17074fb1c0720b9de6c86a9f355eaaaee47bddf` |
| `M ` | `docs/orionis.orm.schema.types.strict_real.html` | `6efad2257a6600274c16226bf1507697b69a33294e28bc227147f61ea622d2fd` |
| `M ` | `docs/orionis.orm.schema.types.strict_small_int.html` | `5086a27cac44f4b5b661bd08d65e31ea5ca5228f25196907bb48719f4f2d06c9` |
| `M ` | `docs/orionis.orm.schema.types.strict_timestamp.html` | `566e8a9cac05aa9833d8aa4c0ef2899b9a070f544f0c3002e1f4d98bab6547a3` |
| `M ` | `docs/orionis.orm.schema.types.strict_var_binary.html` | `ca73d5e38497d5c97c78b2d73a84004925ab7083b88d10f9e748b2b1b20fe7dc` |
| `M ` | `docs/orionis.orm.schema.types.strict_varchar.html` | `746b587758dcf5e4588e93705a11ad52f25434d1b6e1301bbf407643e0513a61` |
| `M ` | `docs/orionis.orm.schema.types.string_type.html` | `fffd4a0f66f9278f476ce8e82e4815981e3d4a1a390fad0ae24abac6a9864b74` |
| `M ` | `docs/orionis.orm.schema.types.text.html` | `18135da58070ef28322d9532124fbc23d77d1ce2cd0bf122eac669a076735cb7` |
| `M ` | `docs/orionis.orm.schema.types.text.module.html` | `be3e519988c66af4e9abeb5b3e55144a7e5684169475bd294e7bce1253f5db77` |
| `M ` | `docs/orionis.orm.schema.types.time_type.html` | `baa44a0778f2deb7db9283ff479f531704d8358bb41278635991504643669aaf` |
| `M ` | `docs/orionis.orm.schema.types.unicode.html` | `24c13ca8e7a631cdfde68665e7de925c587bbaf20309417ccd3817af2e7de721` |
| `M ` | `docs/orionis.orm.schema.types.unicode.module.html` | `c037b1621036804c8d0a3e4eee345ea33877b9f118fb727698fa5394336bb0d2` |
| `M ` | `docs/orionis.orm.schema.types.unicode_text.html` | `a5e6ae0d66efae0b498fc29dd92f78cb5cae0c92e095e7e543ca7d3575929063` |
| `M ` | `docs/orionis.orm.schema.types.uuid_type.html` | `5e2d0ceffb3c59c0a6e2cd9ebab8e1cc801bdbce5dd323a81d7bc3828d38a6c9` |
| `M ` | `docs/orionis.orm.soft_deletes.SoftDeletesMixin.html` | `4c22003fddb22b6da9f0e0664d8d64e119f6cae1abd91b49c10d6c9b96521d6f` |
| `M ` | `docs/orionis.orm.soft_deletes.html` | `6e42b8b688129e77729357833738fe38756f4344b85b78cb715bc33247d15d78` |
| `M ` | `docs/orionis.orm.state.StateMixin.html` | `6cb43a7b21af4cf99542a1e50f681a7761984472319d9431127ca72dae459281` |
| `M ` | `docs/orionis.orm.state.html` | `3d292dcc389bb8ddf65e72a5b148bcdbba157cab88b6356ed8931a903b1de182` |
| `M ` | `docs/orionis.queues.BaseJob.html` | `37250ab9f4d098c2e1d5cbcc0aeba2673f860a27f193755f2b56664ae93a19cc` |
| `M ` | `docs/orionis.queues.JobContext.html` | `f3a2426ec9810613785e48b83d544a00b1f23acdf54919b35b68f0703f72229b` |
| `M ` | `docs/orionis.queues.JobEnvelope.html` | `0deea50b957af87ecbf95730119a16ed3424d3fb63c1b8b4a5f19eb2a01efc8c` |
| `M ` | `docs/orionis.queues.PendingDispatch.html` | `91c1dd4a757bee577c9c4381ae540698aeff95681fb91769b4c043671a4dcde4` |
| `M ` | `docs/orionis.queues._database._DatabaseStorage.html` | `bc2c10e71ad3cc645db14c4cd1c10c08115d2324601036ae3205a7726dd8878c` |
| `M ` | `docs/orionis.queues._database.html` | `62d43ef26e59bc8e39d742a22cfc19547daaa2d2b43e0be388d2de0d8796832e` |
| `M ` | `docs/orionis.queues.context.html` | `fa9774e88bc79f17152287867190121f19ac78e05f9d436fc76203bf0823cfc9` |
| `M ` | `docs/orionis.queues.contracts.driver.IQueueDriver.html` | `c197a98252a98f07ea92239e956c96b3dd9491de6fc168761a946547474b4255` |
| `M ` | `docs/orionis.queues.contracts.driver.html` | `0d480f8a7aa3047c62769f7e47ac275801e41ace5d1f9672c026cd55c96e190a` |
| `M ` | `docs/orionis.queues.contracts.failed_repository.IFailedJobRepository.html` | `846e4bdbb9f1579c619621c978782ccbee05de63ad34a179349b7f8b47b2bb1b` |
| `M ` | `docs/orionis.queues.contracts.failed_repository.html` | `8c5b6cae42c999f0ed141bfd1cacc21056718b3629f448884f15d8bbe2f7bc0c` |
| `M ` | `docs/orionis.queues.contracts.html` | `13d5267bf7a81aef7a17d65e27865192e7173e66d1efc2e14aa7fb989ead80db` |
| `M ` | `docs/orionis.queues.contracts.job.IJob.html` | `a87098501d58bdbd2c68dae19f16a71e3a2696056051b1da3f0c3835f13d8b1a` |
| `M ` | `docs/orionis.queues.contracts.job.html` | `8326afb3618eccedf3783880b1a8700b3d387020d545df1faa7edae57557e00c` |
| `M ` | `docs/orionis.queues.contracts.manager.IQueueManager.html` | `27f2db0af268632e2f355a9bd21423ba00cea7c36e2f8bfdd48ae0f01af85860` |
| `M ` | `docs/orionis.queues.contracts.manager.html` | `f4532fdd81381e11e557bacab70e68fc2ed0941a57c7fdf78b288c7f2d721986` |
| `M ` | `docs/orionis.queues.contracts.serializer.IJobSerializer.html` | `fb7a8152153cd8c29e0828628d6f3d213cc3237379a86138ce9c6dd5d6107154` |
| `M ` | `docs/orionis.queues.contracts.serializer.html` | `7479c7670c13c57bc6731d1a142053d30304907d337c5042d8c008b9242922b5` |
| `M ` | `docs/orionis.queues.contracts.worker.IWorker.html` | `17bf33b2a477a24dbc58dcc5dcb87b60e4ad7d7422b59df61ee2764ae13d1e3f` |
| `M ` | `docs/orionis.queues.contracts.worker.html` | `46ba99d50decf920f7520b6e9f519ea5512f82a6463e9d49fcd5a2dbd73d19fd` |
| `M ` | `docs/orionis.queues.drivers.database.DatabaseQueueDriver.html` | `5055d65faa263c80fdaca517b8f7bdd89a45950745b83144c09d878b5c78c97e` |
| `M ` | `docs/orionis.queues.drivers.database.html` | `a2955840a8a93cc52217c1e344f3d58d0e25cf7794c0cbcdb004cd5a35f80f45` |
| `M ` | `docs/orionis.queues.drivers.html` | `e9de489584dfe6679ce9173cffb4582639e5a9e6cfbab8c4a4ffddb4d4f9a24a` |
| `M ` | `docs/orionis.queues.drivers.redis.RedisQueueDriver.html` | `a5366e7c9592b13a3c9cf62cc31e67d5ade8c14d4584a011d27ae593ab858b4d` |
| `M ` | `docs/orionis.queues.drivers.redis.html` | `57ca809d644f0b53f6d3f6c438977daa335b030039e271c79b43d09f1df4122f` |
| `M ` | `docs/orionis.queues.drivers.sync.SyncQueueDriver.html` | `fb2cacffc7c1f38f17d6f386682c3e8c24966d60b7458d15a1cab71c08496c6a` |
| `M ` | `docs/orionis.queues.drivers.sync.html` | `f3b0151c91356a092809f948f8990ea54d8e0488d8aa55b99858066b6c50e52a` |
| `M ` | `docs/orionis.queues.entities.envelope.html` | `9603ab83adf008d241f6f6c158f03c6e970cd9f7350a7b5c5df527622095a7cc` |
| `M ` | `docs/orionis.queues.entities.failed_job.FailedJob.html` | `8fdab0e31c748b2438a02b300d2bb56cf1a033e65dc82ca4670031b389669510` |
| `M ` | `docs/orionis.queues.entities.failed_job.html` | `45ab5a6b25ed4d47f958d35ab08ffe98e09d3c00da3498270f69bb9fa3795384` |
| `M ` | `docs/orionis.queues.entities.html` | `efd3c6b86077326d74311c83627f29bb24d474e91e8d0ad96fa3e66f041b2484` |
| `M ` | `docs/orionis.queues.entities.reserved_job.ReservedJob.html` | `d0b1717e10d0ca9232e4a68767c59d25af2ef2e6aad34241569c61f79a5b2790` |
| `M ` | `docs/orionis.queues.entities.reserved_job.html` | `fd2dfcbad0ea046d6a0202fed15204ef4f520e9e1d94c5401a24784fa9c6e323` |
| `M ` | `docs/orionis.queues.exceptions.QueueConfigurationError.html` | `6bc872563b3a3452c234c5435ac993405a33978687831590019fa5e3750f0a41` |
| `M ` | `docs/orionis.queues.exceptions.QueueDispatchError.html` | `3f9c746207d18da12eb7807622efb45cf68277b1803c6b3798c5daca4c1b2bed` |
| `M ` | `docs/orionis.queues.exceptions.QueueError.html` | `cfaedb0ff40c5366b6aa417467fc8da57eb54b0f36095665b7e3abc23c980d74` |
| `M ` | `docs/orionis.queues.exceptions.QueueLeaseError.html` | `2acc8e1fa4b0d1cc1226c5e2bee781d3223b54dd9e0b76d6787cb31e8613bede` |
| `M ` | `docs/orionis.queues.exceptions.QueuePayloadError.html` | `74aa195f8e68c956e6c70e2fb2964963c169bb534ed0a432446c67d5bf5aeab5` |
| `M ` | `docs/orionis.queues.exceptions.QueueRetryError.html` | `3f4f7ec3a51a8a93a4785b158a4d739d107c37085a502941536e29ee2cae58b3` |
| `M ` | `docs/orionis.queues.exceptions.QueueStorageError.html` | `e6d180a73bb5813af21220266884415a2afd482588d745e3ffacd8157cdc5eb7` |
| `M ` | `docs/orionis.queues.exceptions.UnknownJobError.html` | `edc1a56da69217438493639495019fd30fa3e8dc3a56b26e3d327e4535db0932` |
| `M ` | `docs/orionis.queues.exceptions.html` | `08974aad1bb50ea1e9523247f5c6d7b9ec61bfd834d12cfae9b2cb418a034c8a` |
| `M ` | `docs/orionis.queues.failed.html` | `9307b7fc8b391f6d064e74a50dd2944e17715669af18d9a075d104e0a83095aa` |
| `M ` | `docs/orionis.queues.failed.repository.DatabaseFailedJobRepository.html` | `39388ea78ab886edb4c1f56975ea3d46168c9956b4f4d4a2cdcac4c1a6cf94a6` |
| `M ` | `docs/orionis.queues.failed.repository.html` | `457e9b502856ab22cad8f9709954f562036721207a448d37a441d326e444e87a` |
| `M ` | `docs/orionis.queues.functions.html` | `b82fb2abff5a9830eb6290966124887a815e3e62283a35f688a9e1e1ef5fb084` |
| `M ` | `docs/orionis.queues.html` | `72355adf30b5a0f879bb3e4ee0e72fde85018a979247c9646c24c1a08ae5a154` |
| `M ` | `docs/orionis.queues.job.html` | `91076637ef675b856df990fb051bcfcf932dbaf843ec395bc53fec3f809beb34` |
| `M ` | `docs/orionis.queues.manager.QueueManager.html` | `082afe80b01efdd84f5043c435e5b50a5ab2acaedc3c686841f8194547f9bc20` |
| `M ` | `docs/orionis.queues.manager.html` | `e0fa93d729a1778d49fe9ad343cb27fbb40f144eb18f13e174e986b91a9bfc02` |
| `M ` | `docs/orionis.queues.pending.html` | `5716cff18bb5d1520ccfabb41d3a54483327a3387ebb7ccf18e3499d97186fa3` |
| `M ` | `docs/orionis.queues.provider.QueueProvider.html` | `f5f9821f8b8ea10aaf71f22c7d9f176bf6896bceb4b2192166e228d67e0f1f89` |
| `M ` | `docs/orionis.queues.provider.html` | `4afe5e4cc395df3005c4634ca808655cddcb91acbc7eff3ce643ac1e4c925a80` |
| `M ` | `docs/orionis.queues.schema.html` | `b450ffc8e5b03b58933b9e59a1491f5a38fc8dc7b7a60ced666ccfd224573d01` |
| `M ` | `docs/orionis.queues.serializer.JobSerializer.html` | `edb5478f08f10fa151963cd659efce1c12d5fa41ff291d2a7b8bc1bfdd3a80a7` |
| `M ` | `docs/orionis.queues.serializer._JobMetadata.html` | `316d9c0c0c0f44295a66ad4561ab8d4db488f81d3d81b3a70eb095d43c822216` |
| `M ` | `docs/orionis.queues.serializer.html` | `6f29d68a80473576398cbc93a980f5dc93df15bfef9eb56b5be97d91dbf35b9f` |
| `M ` | `docs/orionis.queues.types.html` | `806111214484406ce11492ba3718bd32c8e23c9540d25d668c267cdfd2f4d998` |
| `M ` | `docs/orionis.queues.worker.Worker.html` | `b789be4f2ebdc9e1da9e2f4b5679236edb91bcc4982279b8f5a8cbffe42d4d3d` |
| `M ` | `docs/orionis.queues.worker.WorkerOptions.html` | `7e8d125352d5bb18187162f170012f64c926eed2daee1dac69cd868528aa922d` |
| `M ` | `docs/orionis.queues.worker.html` | `9338b610be840c82832d8b32d05311dcd55e2170a4f46280f0f122fcfcc445e1` |
| `M ` | `docs/orionis.realtime.BroadcastResult.html` | `87f3174abbfb5aca46060e50cc650e91e467ba9a79b936aa7fe7b8da4e4aee60` |
| `M ` | `docs/orionis.realtime.ConnectionManager.html` | `3d824ff6b43137ea81ec1e2e343453e51f2c916af01ca357f10dfc27ca88496f` |
| `M ` | `docs/orionis.realtime.HubClients.html` | `c9ea9f9e93b1e1d9afa2898c3c7fb80467d3e9d2f904fe15d7f7c2319dbcfdd6` |
| `M ` | `docs/orionis.realtime.HubContext.html` | `f31077b1f27275532e17b0e8c4ec4c8d62d0f0acddd8bd9457b25a1eb5375254` |
| `M ` | `docs/orionis.realtime.HubGroups.html` | `b55ef51a8dc04fe55ed9eb5e7b00c609c97fa0d00ff03c283b9c5f33c6212df1` |
| `M ` | `docs/orionis.realtime.HubProtocol.html` | `881027bb5223af0f734f2a8f6ac9dbeee40811db224594ec4faa3d32e772d409` |
| `M ` | `docs/orionis.realtime.clients.ClientTarget.html` | `8258977aa50fe7f045da793a68cc3a12964472797e59fbb9d91f77de54dd1079` |
| `M ` | `docs/orionis.realtime.clients.html` | `4c6a85f001664008b3504d878c5319d5e6475cbe1748c595afd946fbf7c0b169` |
| `M ` | `docs/orionis.realtime.config.RealtimeConfig.html` | `8bf678c88d79c3095be85f607cf0eb87decc6165315e4421de0e8cce6eaed91a` |
| `M ` | `docs/orionis.realtime.config.html` | `33cf7803b2b07493fdeffb5f30e53888384062e32996e38b7bec1d27bfc74734` |
| `M ` | `docs/orionis.realtime.connection.RealtimeConnection.html` | `5e06f8fed5f690a930b73aecc8faceaa2433e45c70347529f2fb64237268f4a5` |
| `M ` | `docs/orionis.realtime.connection.html` | `848d683f88733b0032adb29ee2480d47fd12ce4b4ba92097e8ad740eb2c17d86` |
| `M ` | `docs/orionis.realtime.contracts.IConnectionManager.html` | `b2d8efcb28b31ea58cf755c76d640e4b79af76272f14a9aa5fe746253339e6ba` |
| `M ` | `docs/orionis.realtime.contracts.RealtimeConnectionLike.html` | `4c2a7028032abcfc84e71f764d5d3ffbda2744119f08741865b350a7019c1871` |
| `M ` | `docs/orionis.realtime.contracts.connection.html` | `c4fd3a5259a5ba7875e7aa13ed954718b278f1793335500afa97e857b9d4b195` |
| `M ` | `docs/orionis.realtime.contracts.html` | `709147a0691e833b9c35874f8a05449556855a8711052af3d5b7df1ed394390f` |
| `M ` | `docs/orionis.realtime.contracts.manager.html` | `34876d5f020f7cbde9a9edb8074cbde8b830177e44724a9de004b3e17ce63550` |
| `M ` | `docs/orionis.realtime.decorators.html` | `5d32e52db466c370561ae4799891f58a84a110f7b422489ddcb55d852df983b3` |
| `M ` | `docs/orionis.realtime.entities.html` | `7fe64d599ea58322fbc9da86a9735af1b06fee75b2f175b0c5d6b5101d6546d4` |
| `M ` | `docs/orionis.realtime.errors.ClientInvocationError.html` | `df6d0d2b7d8d6f2dd77b37f293692ca9e86716106908dd43b53ff41c2eb5cb23` |
| `M ` | `docs/orionis.realtime.errors.ProtocolError.html` | `018e8ff516e0cef2de3f4efa92d1d76a58e05fd10094e1f3bdb0fff2b04cc05f` |
| `M ` | `docs/orionis.realtime.errors.RPCError.html` | `4bfe709400f5d00a1d8ac5050a1351f188a2e2551d5f89125d1cde9b89ad842c` |
| `M ` | `docs/orionis.realtime.errors.html` | `08a5b5e16804c42af36986d89d412db03e1d8d410d26ae1222c7095eb271b9c7` |
| `M ` | `docs/orionis.realtime.groups.html` | `c4ad925129bff8b8a36b627f70968ef2fe6e75df278841366bd6c2960b1b292a` |
| `M ` | `docs/orionis.realtime.html` | `9c6b7a2155e43d3ba62c736fd7c741038c43bc0bac8d6a77eb1cc811baf279dd` |
| `M ` | `docs/orionis.realtime.hub.html` | `c0b6577a7797d7dcbefca742aaf12e574b3020fef9139a26fa461ff3170f8db7` |
| `M ` | `docs/orionis.realtime.hub.module.html` | `21eebc58ef2570239c810f7b3f287c122331cdd13490182e956ee0a4a0adc672` |
| `M ` | `docs/orionis.realtime.manager._Broadcast.html` | `155388e2cced8fe905a7c3910aed9974699a07c1f876ffa4b83aa6f80d7337b6` |
| `M ` | `docs/orionis.realtime.manager.html` | `e9ed243f41568356f50433e77a91b2d5c80cbf8d05c6975082ef24549cd5de71` |
| `M ` | `docs/orionis.realtime.metadata.RemoteMethod.html` | `ca38df7acc06f041315083572e80dd48f68a874b0c353cad9606cfcab3bfdc74` |
| `M ` | `docs/orionis.realtime.metadata._ClientParameter.html` | `98b8ead14dd5c4fcab1b8b7df7310888902404014064ef409d45a55ffcd3d053` |
| `M ` | `docs/orionis.realtime.metadata._SchemaPlan.html` | `d90b0883510550a2390da7330341316fed4f239d6e854d3fb185590ba040c0ca` |
| `M ` | `docs/orionis.realtime.metadata.html` | `7d6f4c633b3278bd95a28db6c624d5690d5f35c0e259dedfa466f5eac224d8b6` |
| `M ` | `docs/orionis.realtime.protocol.Cancel.html` | `071802690f89f6f43fed5cc36580bb84bf429d2c3520e617f2421b6a05b50498` |
| `M ` | `docs/orionis.realtime.protocol.Completion.html` | `74c1be56aef43b5d0348ae6f2db297b19683f61a1092197bc3e5d7bd8f0fa5d8` |
| `M ` | `docs/orionis.realtime.protocol.Invoke.html` | `ca4b0f32e186b5af1ec74057acdedbd1fa068e423f5dccadb29b3b9706971285` |
| `M ` | `docs/orionis.realtime.protocol.Ping.html` | `2cdac469b271693396bf9e00b636f7e114c768ba6f4fc110a3b52d3f88146dfd` |
| `M ` | `docs/orionis.realtime.protocol.Pong.html` | `bf289d6227988f2fa34b7b881804f8ba39f84db9c3865230336d4289fea425b8` |
| `M ` | `docs/orionis.realtime.protocol.RPCErrorPayload.html` | `91862b5ce3ceaa4d94ce0150176eeebf08645566f71209007821869e511d7308` |
| `M ` | `docs/orionis.realtime.protocol.html` | `16001a1c6f2cbb3186a09d9f9babce7284fd3654ac79625adab547742761896d` |
| `M ` | `docs/orionis.realtime.provider.RealtimeProvider.html` | `372e3d8fbd160db605f30a2e77b19b9f393feb3370fa7d8c05c54bea4d2f39bc` |
| `M ` | `docs/orionis.realtime.provider.html` | `b22d6756a1c010252620565025f691290cc26911476f517fd9f06a8b5d929a97` |
| `M ` | `docs/orionis.realtime.runtime.HubRuntime.html` | `168940af9f7ced2357653c413cb91a59fefdb72779b10dcffd513f3a8a276a5c` |
| `M ` | `docs/orionis.realtime.runtime.html` | `062a05ae6b8351ee860c87d7ad0b0d8bfd94648a49cb4852e0f2a7697cae3dec` |
| `M ` | `docs/orionis.schemas.coercion.html` | `a6e48c52c361186faeecd77b77462f0be7f75226d275147fe3d4aa2a1edc1a1b` |
| `M ` | `docs/orionis.schemas.compiler.MetaCompiler.html` | `9d71601e172cc594b1b55574e770348438c29cd26fd6c72e8ff8953bec399fe0` |
| `M ` | `docs/orionis.schemas.compiler.MetadataConflictError.html` | `0f49007ae2561b5add5d9eab7557b63645f0c26d95a6152a3503de92251d9cc5` |
| `M ` | `docs/orionis.schemas.compiler.html` | `7de16bb0477f4aa17869deeb80996b5d9b9cb1d9bbc175e5c22da8294708b926` |
| `M ` | `docs/orionis.schemas.constraint_plan._ConstraintMessages.html` | `2f3e9b30f2a3e5b3c2c602db5aa8de97495d965cf4cb6357b3392f11c7eaf64d` |
| `M ` | `docs/orionis.schemas.constraint_plan.html` | `d93a487234e2830aa26e64370899593561b6347ba04212c3d668974036eb91f1` |
| `M ` | `docs/orionis.schemas.constraints.GreaterThan.html` | `2bc3379ff8c16b24873c8f6ecb0cd8521cbd66de614ebcf6d8dfc0365a203239` |
| `M ` | `docs/orionis.schemas.constraints.GreaterThanOrEqual.html` | `757662741747045cd5064795b9897edcb8d81f63b54784266a8f62a621c4c7cb` |
| `M ` | `docs/orionis.schemas.constraints.LessThan.html` | `4d17780bcd3fd7195d3842e7864e493ab24f745b09e674f077c3c9489d3d2220` |
| `M ` | `docs/orionis.schemas.constraints.LessThanOrEqual.html` | `cf64914fe81e8feeccfa5913ba5f7c365d9cf7d12d6e305d2539c6e5baa0cf6d` |
| `M ` | `docs/orionis.schemas.constraints.MaxLength.html` | `ab38b1a8bdb5db9731dd038a8db6d63d7af657ab68950b352d5517a20ae0d276` |
| `M ` | `docs/orionis.schemas.constraints.MinLength.html` | `3e9ea5c64559aea2261e16f7d579b1328a73332375bf1a67a009cf3cbfa6f641` |
| `M ` | `docs/orionis.schemas.constraints.MultipleOf.html` | `9d0dd7e37d2d0ab32d945a2c648669e0a84f052e909a7144a41cb62d63cb9857` |
| `M ` | `docs/orionis.schemas.constraints.Pattern.html` | `eed53523af348b955f138a7984a8e56a5e4719ca8be2a47297eb210069e502ea` |
| `M ` | `docs/orionis.schemas.constraints.TimezoneAware.html` | `10fba82b782d6b389c7b36e4747f46f193b874bfb15315ee4bc8d598bad0702a` |
| `M ` | `docs/orionis.schemas.constraints.TimezoneNaive.html` | `2ea339dc7cd4717e9fc9a670f17370c86d35d833cc3a8653b762fb1654bafba9` |
| `M ` | `docs/orionis.schemas.constraints.html` | `cc20a3eaf32f55477008986a6d7147b8e9b94af3bcc9c62f8128ecea7520f761` |
| `M ` | `docs/orionis.schemas.contracts.constraint.IRule.html` | `45632a9262b1d4afa48c57be2c0e15fff5e34bac0d93561251266b6f19997c8f` |
| `M ` | `docs/orionis.schemas.contracts.constraint.html` | `e39bc75290ba89e6f68ea683ca3945c0e8e8b3d24ca0596a32cd33f19ba136bd` |
| `M ` | `docs/orionis.schemas.contracts.html` | `d6c432b0bb5c0a6e36b5c874d973b56cefe04fc22fdc81f8dcbc4fa825f76b7a` |
| `M ` | `docs/orionis.schemas.entities.failure.ValidationFailure.html` | `3e9d25ea8afac6c47ed4085c42d06470e28de9187d2037f342279631d6ec70b2` |
| `M ` | `docs/orionis.schemas.entities.failure.html` | `743462670edff7994b0726528bab7e93fb409bac2d37435c44cf5e4acca60166` |
| `M ` | `docs/orionis.schemas.entities.html` | `3f32e72f8ba53a7f606e72bb435d47966489d18c1fa40ea3db3cceedbdcc87c7` |
| `M ` | `docs/orionis.schemas.exception_parser.ValidationErrorParser.html` | `d2be496b7daed1b53f6db7fbe74fb96bb23f9d13c062e90b1cfb657297bd2f82` |
| `M ` | `docs/orionis.schemas.exception_parser.html` | `440e4067ff801a4a234bfa53df9d0deee6d8edbf2e3ed8a4ecb714b0031fb9f9` |
| `M ` | `docs/orionis.schemas.exceptions.ValidationException.html` | `5af4b7ed87c3664eca8b6fe3ff56cb7b66ecee6abe01818bc32b2c4f5fdb94ee` |
| `M ` | `docs/orionis.schemas.exceptions.html` | `bf7294dbc699ca123673f4f5fa37505c298ed3f873dbfa711cae97a4265eb4c8` |
| `M ` | `docs/orionis.schemas.exceptions.validation.html` | `bdc667b7e4afe1a0f0b9d71c89bd999e85ef86209892446d552cf0e7c74579e6` |
| `M ` | `docs/orionis.schemas.failure_collector.FailureCollector.html` | `546e623f10240a7d18079b2538e57ee227c6aa4b26015eb066f6738756dc6603` |
| `M ` | `docs/orionis.schemas.failure_collector.html` | `bfcec36ad51265b7ea7ed700485a4cb953aed5141a1d0db650b292209076f24e` |
| `M ` | `docs/orionis.schemas.fields.html` | `bea58ab5f300083b2a8054d1f7d056ca9bf971f14369cccd80003dead908df6e` |
| `M ` | `docs/orionis.schemas.html` | `5e8737680c1b6d4cc90f45ad33da2c2b7b5a611e9819a1da783bf9badd073131` |
| `M ` | `docs/orionis.schemas.instance_payload.html` | `73126743f40395e4b568dcc5990ea972d482f2c8b51ce382a1d7fdcc906904e3` |
| `M ` | `docs/orionis.schemas.meta.constraint.ConstraintMetadata.html` | `3077f77023954daefb3830b71160459088c21facde79f28b4b11373d1d2f6186` |
| `M ` | `docs/orionis.schemas.meta.constraint.html` | `9c98a45ab68b61be9a007753e5f4e8c99c0d296905ef8fc889716ff62f6ff8fa` |
| `M ` | `docs/orionis.schemas.meta.document.DocumentMetadata.html` | `078a65c72076643ed1533d516e8f0aa0d4db895297c04cce033f3a7fa3423ad5` |
| `M ` | `docs/orionis.schemas.meta.document.html` | `3fc8c69b0eb22f17f03666841d7f060cb9f9cbeb7de1d4bac2ee8cbceb306a0d` |
| `M ` | `docs/orionis.schemas.meta.html` | `a57400b831c23757cd77b113d47386182238c8560becd474f5b58b8ba6f955b2` |
| `M ` | `docs/orionis.schemas.meta.validation.ValidationMetadata.html` | `fcc95a26984f4a7dd8794a1904ce8d8b0b203978e4eaaf65b6ae105791431855` |
| `M ` | `docs/orionis.schemas.meta.validation.html` | `495f54d07377426977757c3c03dff4f71beddd909611ff4382a372a9a55012cf` |
| `M ` | `docs/orionis.schemas.metadata.Coerce.html` | `ef0660bb4a33a06d680ebe41264293d51c2d0871a872dca32524bc7e7f9aec7d` |
| `M ` | `docs/orionis.schemas.metadata.Description.html` | `a5bc0829c7258fbaa8acfd6e45ae462d1f4f86cdda1558a55b1a01f3138b2cf5` |
| `M ` | `docs/orionis.schemas.metadata.Examples.html` | `9bd30d633666acba33dff3375f77b0ba4a34c416a2a1cf658ba2e0025f9d5cc5` |
| `M ` | `docs/orionis.schemas.metadata.Extra.html` | `f2e725b54a2681d8795c57a932873c886637044eaba61d688ad7883a7b54f1eb` |
| `M ` | `docs/orionis.schemas.metadata.ExtraJsonSchema.html` | `6931c788408e356bc515b96e39bfc1e7b7b45147539f5214bbf90a1bd2872481` |
| `M ` | `docs/orionis.schemas.metadata.Message.html` | `13352f1978dfe0e9ba0ed301c8eb2a3032b73949bafc0f7854fbcd91068c612d` |
| `M ` | `docs/orionis.schemas.metadata.Title.html` | `1322213475d27bc65eda2a2ccc87365e851934621a9ebea22c6acc673d95a2ca` |
| `M ` | `docs/orionis.schemas.metadata.html` | `f1514432d3d3e22852105c41d93725aa09d0edadd6320794a37c05d2d82d473c` |
| `M ` | `docs/orionis.schemas.rule.Rule.html` | `bb690c9c9fdae797bb38ca8492c9b8127c2dbb090b2abaea3530f5bafb64ef58` |
| `M ` | `docs/orionis.schemas.rule.html` | `1d96d273e280d9ebd3fbbfea517735b22ef62d624a85d368a2cb13bdf03816ee` |
| `M ` | `docs/orionis.schemas.rules.ActiveUrl.html` | `670e0c41af41782e99ea87af6a93704c34dfd1984c7bb841081f258909488e64` |
| `M ` | `docs/orionis.schemas.rules.AfterOrEqual.html` | `e225f9993052486c2a7f3a33014fcd2ba21d332bbfc1c62caca458c05b874c99` |
| `M ` | `docs/orionis.schemas.rules.BeforeOrEqual.html` | `a12b0c74afc72dc753926dd0e782fc8878c0f9885636286c404469dac5f9ec84` |
| `M ` | `docs/orionis.schemas.rules.ConfirmPassword.html` | `4c33dc677443dd9dfc6bdc6994fadd7dd0561da670ffcae244db4d842dadf6de` |
| `M ` | `docs/orionis.schemas.rules.DateFormat.html` | `09b59c57cf0a2dc5caf06bc2d716e8690182f3e7e0f647f074b5e486bd14e63f` |
| `M ` | `docs/orionis.schemas.rules.DecimalPlaces.html` | `70528d20157e86adf50ecc78f7dc7bf1b73a2946db2a863e1422f2b25c0f9b51` |
| `M ` | `docs/orionis.schemas.rules.DoesntEndWith.html` | `19505eb44a60b9dd5fca58a08f4c9bf16954335dd4f07a2d30f44b2be020033d` |
| `M ` | `docs/orionis.schemas.rules.DoesntStartWith.html` | `966fac15cad047ce0fe7f86aa24ad46757255a916e2743aeeeacbcb84b6fa09a` |
| `M ` | `docs/orionis.schemas.rules.Empty.html` | `5ef3bc46d9e2b6dac5864a43f97563d086e9fab5d9580fda42a090d9709db8aa` |
| `M ` | `docs/orionis.schemas.rules.EndsWith.html` | `93bc083fc54482dbce72c759692f34484271efd3158f5dea67d9b343bd04efcd` |
| `M ` | `docs/orionis.schemas.rules.GreaterThanOrEqualField.html` | `1d2e9df93a40f48f50f28ef2c926c66688db99d0b985f339e5a95a1f1cf74f87` |
| `M ` | `docs/orionis.schemas.rules.IpAddress.html` | `7d3258ebaaa25bff5642072015dd37a6812d042d38044685f5aaebf614c42849` |
| `M ` | `docs/orionis.schemas.rules.Json.html` | `5fe1f29108ab9cb4290fb3c66f8ac3a7acc35d9bbb31463947a408de7551d71a` |
| `M ` | `docs/orionis.schemas.rules.LessThanOrEqualField.html` | `5ee8ef4c85e354a895fe44a5b86f7262bbf4d945d1f4731ab390774b8f124e0d` |
| `M ` | `docs/orionis.schemas.rules.MacAddress.html` | `2f518feb726aea3dce18b9854afe4edfde0442c215d094c3f5d96076e4c6a006` |
| `M ` | `docs/orionis.schemas.rules.MaxDigits.html` | `516bfa5c3b06ba2c12204e0b65dc0c3880839d4712d4cf9f91314a1dc1ef925f` |
| `M ` | `docs/orionis.schemas.rules.MimeTypes.html` | `a13cbaae84aa1dc773c258289441a7cc2d558329046bdfa1e07e6bf55c8a11c4` |
| `M ` | `docs/orionis.schemas.rules.NoEmpty.html` | `d2b5b5b1604f9bb5d30d3ae81dfa7c64fb00d153382b60810bd123914459a613` |
| `M ` | `docs/orionis.schemas.rules.StartsWith.html` | `a5623a87cec24891dd0e0e74002a3e11badeb9d26797221585e12bf80d6af3da` |
| `M ` | `docs/orionis.schemas.rules.StrongPassword.html` | `626e4c9f92acf6743b440e81aac332315b191720f493b3399df6e03d5aba53f6` |
| `M ` | `docs/orionis.schemas.rules.Uuid.html` | `f5ad66f351c0e4f7199e43891b362ae28b5a6f32bff9565894716cdf40fe86ef` |
| `M ` | `docs/orionis.schemas.rules.accepted.html` | `be99a5cde9f70def37f5d0e9414ebe27cbc1e85fde51fc9248a9c1e35672f26d` |
| `M ` | `docs/orionis.schemas.rules.accepted.module.html` | `0d77a1aaae6ecd10925d68647d12f7385061775fe0b0b07be98b8653e16d7cfb` |
| `M ` | `docs/orionis.schemas.rules.active_url.html` | `e9d5be42650785c81d7a76c20f7c9218e3518226d215baa7c095cc4e029e90e8` |
| `M ` | `docs/orionis.schemas.rules.after.html` | `7706e88cf4220e6fbf62604e9f2636b3821bd271cf83c6f1a58d8e6996dfb11e` |
| `M ` | `docs/orionis.schemas.rules.after.module.html` | `ac2b89f7ee23e7d444b0e2a807636190752203656840d7a1a6c2f5756978033d` |
| `M ` | `docs/orionis.schemas.rules.after_or_equal.html` | `695632cbcb4da8c33047874d6c3d84c40b84460aea4ebdb9a602b683ad5066bf` |
| `M ` | `docs/orionis.schemas.rules.alpha.html` | `c3710a2b1a516ee39f95726a0e1f3de83f29878ec30f961d8362c1f14046a8c8` |
| `M ` | `docs/orionis.schemas.rules.alpha.module.html` | `f46a75c369b4f997330480e849b742d0c993b8468b31b3a8a5d1ae2b5e49a413` |
| `M ` | `docs/orionis.schemas.rules.ascii.html` | `2ddf3c4a67d79103a2d8e1bfd7d772daf79e493c6395ca08ee40d539967ce6d6` |
| `M ` | `docs/orionis.schemas.rules.ascii.module.html` | `98680dd6112c141dfef00aa0a2a59d05818e1a0d32bcb35c239130ab4169d2db` |
| `M ` | `docs/orionis.schemas.rules.before.html` | `fced202d781eedcdd6ed723ce5fce214024f037ae2da1ab2063dcb6ccebd1879` |
| `M ` | `docs/orionis.schemas.rules.before.module.html` | `a25402142e536d335cd280d62d69477bc219ffc8484dc9fe7fbd17bac9a4375f` |
| `M ` | `docs/orionis.schemas.rules.before_or_equal.html` | `ab8c95fa9290bd5bd35bc64d3afdd003ac6d44d5e912c51a5a3c65c7f9761e25` |
| `M ` | `docs/orionis.schemas.rules.between.html` | `dca8e58e66f24ba1040014efb6a3d62822a03628078fa43fcf05261d613d1f50` |
| `M ` | `docs/orionis.schemas.rules.between.module.html` | `108897969e19e8de214a3871eeb784824118b8b050bbcfbde1a3061c7fa29e15` |
| `M ` | `docs/orionis.schemas.rules.confirm_password.html` | `f465e7098c8f6c0ee79a92c57d0410df371a53276eba7f3f81d53a0770aebd77` |
| `M ` | `docs/orionis.schemas.rules.date_format.html` | `a475fb699d4541694eac2903dc3e342221011ced0bac2b5d80fb113ff9772777` |
| `M ` | `docs/orionis.schemas.rules.decimal_places.html` | `8695c517b9a951086e5d29e723b274a3866134aa360c056c5e5ceaa6b6f2ba3d` |
| `M ` | `docs/orionis.schemas.rules.different.html` | `e2fd00be0ec5822455c0946c608193efc23f2087af9d39c4264c3e248501ef2c` |
| `M ` | `docs/orionis.schemas.rules.different.module.html` | `b8562cd7e75ae9e32c206c3e7a9e969d7ac8218c236963467c8c8043a637419b` |
| `M ` | `docs/orionis.schemas.rules.dimensions.html` | `32e4838a4db6c55019915748da41d439762b1417c10ae61f611d0c0f1e07c275` |
| `M ` | `docs/orionis.schemas.rules.dimensions.module.html` | `7e1b27643fd39d63c83bc8986634480a535b68bc172b8ab452015930143942c6` |
| `M ` | `docs/orionis.schemas.rules.doesnt_end_with.html` | `551d12fd409716cb8c8555f6eb150e0fc2f3a52dc345a5f2f7a968a9dde92357` |
| `M ` | `docs/orionis.schemas.rules.doesnt_start_with.html` | `d4304ebb664adf3c3911179e2635f010d993983c37de7061c51b68db826e05a0` |
| `M ` | `docs/orionis.schemas.rules.email.html` | `e169d62ae57e681b0cbc0b0a321fcaad674f2fe75886b094e6882601827bf903` |
| `M ` | `docs/orionis.schemas.rules.email.module.html` | `4da9196e228b8a9a83fdde2092690897e168967509ae2fc553fedbbbb428bd07` |
| `M ` | `docs/orionis.schemas.rules.empty.module.html` | `66261beb4e919867e8bcdf132449fd226dab83691c8f2b20ee05416fc48730e2` |
| `M ` | `docs/orionis.schemas.rules.encoding.html` | `8d867f68e32d044508d814137978ac5555362013513c9741fec7b3d767881765` |
| `M ` | `docs/orionis.schemas.rules.encoding.module.html` | `40582598322681d628e0e53099bae5df94123fa7057073e3b3edd771198de488` |
| `M ` | `docs/orionis.schemas.rules.ends_with.html` | `eba327d80dc0da04c65fec2daee4b6f318f97f44092412d0d786b3edb9acceb1` |
| `M ` | `docs/orionis.schemas.rules.file.html` | `5be9abe13679abad1a1ca1fc3059846bd9bc38a76ff8b110ac73d9f5f16b72bc` |
| `M ` | `docs/orionis.schemas.rules.file.module.html` | `f70274813cec253e667a1b880c9762b72561196de8a30ab2e152567d887493d3` |
| `M ` | `docs/orionis.schemas.rules.greater_than_or_equal_field.html` | `57b409d355273647d40c7d23dc35675c5fcd93502b527973c3cffce56e9140ab` |
| `M ` | `docs/orionis.schemas.rules.html` | `969ef1658a3df8abc7162ee00cff758f92271a533c8fa144c7ac6e0b520b5445` |
| `M ` | `docs/orionis.schemas.rules.image.html` | `1e25c2a63752e0b88a6c1b5081554d9c26be283145df5fc1fd0e48d26d78df77` |
| `M ` | `docs/orionis.schemas.rules.image.module.html` | `9f67a96f0b84189b1315b42c69dbce433af57c6ebc7d1c8991f820f3c60585a7` |
| `M ` | `docs/orionis.schemas.rules.image_probe.html` | `3062152e9b40583d2cd0838bd81e62ca8d1438a68820caa6d9c5eb34f5878a26` |
| `M ` | `docs/orionis.schemas.rules.integer.html` | `bbf95d6c2e7d5b1b2dea0021d22595a6e2c49674810a9749d1fc802c6c35b368` |
| `M ` | `docs/orionis.schemas.rules.integer.module.html` | `57b1d6fb9e1ecc9c3f0b7c55bcf2bce26841f0f42bedbe96be21342ca6bab96f` |
| `M ` | `docs/orionis.schemas.rules.ip_address.html` | `9c03238353cb98a5f24050775df558d706074970ff41eaa51d84de39c9aca911` |
| `M ` | `docs/orionis.schemas.rules.json_string.html` | `3ac4559e6178477f2dfa52c944b948e93addad4232363acbcb8d0245cf15714e` |
| `M ` | `docs/orionis.schemas.rules.less_than_or_equal_field.html` | `c27b3635e03f1a28399bd83c0b4e7ec490f1169b8b4cc267a9b08e20027e5aa7` |
| `M ` | `docs/orionis.schemas.rules.lowercase.html` | `ef090f34392dbe790f87fbfd86be170a0227b3a7e5952655b69a1202e0194c34` |
| `M ` | `docs/orionis.schemas.rules.lowercase.module.html` | `51f66289ca631f9730940fc009c65865a17e8d1005116d3598a90aac062b0863` |
| `M ` | `docs/orionis.schemas.rules.mac_address.html` | `a206d681741ddf9c2501df849daac7585db8a67c70fab8d137864c006929ecb8` |
| `M ` | `docs/orionis.schemas.rules.max_digits.html` | `6a8cd0a5fc97601fa7cffa320d26f1ae2711fc2b02df3f713a42d0ce759d9788` |
| `M ` | `docs/orionis.schemas.rules.measure.html` | `4294705c76e433fe2d1e680a65b3fd71695c07da1dcad7be577f8d78522bb9c7` |
| `M ` | `docs/orionis.schemas.rules.mime_types.html` | `61e58600a8d4a813f8ea931f7dbaadcabb456bb5986bfa40706c2877701c4249` |
| `M ` | `docs/orionis.schemas.rules.no_empty.html` | `a8599d30b29ffdb5379168909eec3d29319319e2406c2d93d18acdd7e377dbaa` |
| `M ` | `docs/orionis.schemas.rules.size.html` | `f8a7b6f0ac529eb1ec5ba95049a0dbe3c68de79cf786510655753086f5fa381a` |
| `M ` | `docs/orionis.schemas.rules.size.module.html` | `0cf1b4af01ec4d24cb9e6b4e624105b32a59400b70400d90b4b417e73cb5301c` |
| `M ` | `docs/orionis.schemas.rules.starts_with.html` | `1e40783c8a0f14bd9af0041803643766820691618fd72704af850f6c510103d0` |
| `M ` | `docs/orionis.schemas.rules.strong_password.html` | `f2912b9a8ba9777d7aae16e8734b0c4d635ff9314020446241b16e48d0ce146a` |
| `M ` | `docs/orionis.schemas.rules.temporal.html` | `d4b834d6c0d7e8b8955317952d08947c1fd37d169738c26426d7084848e57a41` |
| `M ` | `docs/orionis.schemas.rules.ulid.html` | `98991c18d61ae930ed8a847cf6b2f4d37ce4d35fd9f29eaa3eae91f126b6d74a` |
| `M ` | `docs/orionis.schemas.rules.ulid.module.html` | `11b28409bea930b2202bfca808bc00fcb32fc490309aa5eafb63094184813ee5` |
| `M ` | `docs/orionis.schemas.rules.unique.html` | `d9e1a8c48919c360dedb3f1901fba6d982afcb3b0f39323f2e3415f61d2c345b` |
| `M ` | `docs/orionis.schemas.rules.unique.module.html` | `a260e078d67911ced1024f9bdb2c0b15af2140595ffe3330983e8d1bed7ac15b` |
| `M ` | `docs/orionis.schemas.rules.uppercase.html` | `cc6cc0cef5fab566517117a64de9051c4c05687f45d81f7df18a8bee580d7d4a` |
| `M ` | `docs/orionis.schemas.rules.uppercase.module.html` | `061d1f0e6f99b13cc9a3cb47a84624bd7246af571334e1c8e470f498787a68a9` |
| `M ` | `docs/orionis.schemas.rules.uuid_string.html` | `4ae0683c162532317ca16c71ee726e06cfe5cb6c59bda78da612f0fe0923dd3d` |
| `M ` | `docs/orionis.schemas.rules_executor.html` | `e10b98b0ba522a3121b3f416f6269a716c847b0815def8fa89d316a67897980a` |
| `M ` | `docs/orionis.schemas.schema.SchemaMeta.html` | `64b711d3746b64770dc27923b0aeccde2ed8ef2577863cf33c7c124a0a9dc0bb` |
| `M ` | `docs/orionis.schemas.schema.html` | `28b3d39973b10e71f1c170786a386b37a877c70ae86a8eae66eeb004b22b5b38` |
| `M ` | `docs/orionis.schemas.schema.module.html` | `f30453d5c30eea91ed1fb628df61ee97dbdbe2ccaaac95a5d721258028e74d52` |
| `M ` | `docs/orionis.schemas.validator.Schema.html` | `e0c175280d1a8a79be8957ddaed4b750c1c8bf73cc338ed072a5d11fe1f77434` |
| `M ` | `docs/orionis.schemas.validator.html` | `60d87f5b4cdb06d95429dcad28182b2a5a00f090f6336b92073e6f99c586f0b5` |
| `M ` | `docs/orionis.session.contracts.ISession.html` | `981d0b720e65ca07e5035192873da77313a9db453e53e6394d164c0678490545` |
| `M ` | `docs/orionis.session.contracts.ISessionStore.html` | `c52233655de0194337f1218c74d236b98b253f45c2e1c42cfee23689e24a678c` |
| `M ` | `docs/orionis.session.contracts.html` | `02f499c3954499beb8028f30957f1647eccbdbf068315d509a7be44691158764` |
| `M ` | `docs/orionis.session.contracts.session.html` | `7c2a39e2753e8e9055152100970b8f3dcb16f33336a29631865d4a859d91f67d` |
| `M ` | `docs/orionis.session.contracts.store.html` | `51d3ea9fa70cd2cb60c41bfc7463d4ce29d6e12406ad1adca8fd8b1a4012764f` |
| `M ` | `docs/orionis.session.entities.html` | `d5ba94949f5319c36e577b6f1e2bc364d9603e17718ef99b9538b9dadb495fd4` |
| `M ` | `docs/orionis.session.entities.record.SessionRecord.html` | `d5b82bc85f2a66435e327256c38370a8c2578838f49cb98b912f6de2792b8faf` |
| `M ` | `docs/orionis.session.entities.record.html` | `b9e563557b8624c4f4a65ba95afa3b9f51c99dcb067c323533b043a88929e625` |
| `M ` | `docs/orionis.session.exceptions.SessionException.html` | `0b2bc51689b0b6d0e7bdb65a2f651cde47ba6d7becef31912e7a24a2ee2120ce` |
| `M ` | `docs/orionis.session.exceptions.SessionStorageException.html` | `52f88f97ee8bb432401083ba5afaad76ee6f3dbfee0d1164a9eadb18181c56b6` |
| `M ` | `docs/orionis.session.exceptions.html` | `0d9f1c8d8db7f0b445ed66e8498dbade69355f9f5305c86d65eab5c8a1d93ab2` |
| `M ` | `docs/orionis.session.flash._FlashData.html` | `afb1823d89d7574667a89c24bf71f88c41920cc6754ec3dbce0bbb187ca20b61` |
| `M ` | `docs/orionis.session.flash.html` | `a357a164a9c0bcfbf75a6c491c91a5a603271d109a1bdf7831a8334463ee8b66` |
| `M ` | `docs/orionis.session.html` | `f6cb2aef526dcc41c1039b7fe553e9fe74f6183892ea05be9883f786c561dfc8` |
| `M ` | `docs/orionis.session.manager.SessionManager.html` | `069cd6ffedc856d8d575b105947f35de4462c458ebeb9efa1706f18c5b7e0444` |
| `M ` | `docs/orionis.session.manager.html` | `4e36fbc16aa4a54dcf927e86772e1fb2625a71b6ea5c611e165589c831704288` |
| `M ` | `docs/orionis.session.session.Session.html` | `21dccda663416c280b564d87799f065444e8932d21f6d8ed6ab621dadf8b4fd1` |
| `M ` | `docs/orionis.session.session.html` | `01e9f982277486da8b079abd4f9abaae2ccf334c80eb5ed34ea40f42b4bcde4d` |
| `M ` | `docs/orionis.session.stores.cache.CacheSessionStore.html` | `ffd3cc107245e956779125c2ba185c955e6ddfcfa33897ad7c9310fabe298fb4` |
| `M ` | `docs/orionis.session.stores.cache.html` | `e2ae1db1d6bdddb61f1b4917a728fb07e386ec8d7ae5b0681d4dca832136035d` |
| `M ` | `docs/orionis.session.stores.database.DatabaseSessionStore.html` | `69f65c0870aac755a697f141e7118c6ac49e720547962dc2ade0a9aa264a78ff` |
| `M ` | `docs/orionis.session.stores.database.html` | `c9206698b8daf6d348ada0106c16ac8daa3abea80152b7d22d43310bffc291d9` |
| `M ` | `docs/orionis.session.stores.file.FileSessionStore.html` | `311e49393c288e860c629c7af4387f747181131329a6e868d68b9a9dbb7ca187` |
| `M ` | `docs/orionis.session.stores.file._SessionPayload.html` | `b47ceef56c2430556e3536b0b10825e4673055d10f6645340cde499284e28e07` |
| `M ` | `docs/orionis.session.stores.file.html` | `63733df8e316464cc499912251d9e8402f47f3ee80060a298eb94eb3714deff4` |
| `M ` | `docs/orionis.session.stores.html` | `59971f100c7968bc69f46435e19d4a10c8000e43b263bc508480e6b47fafa47a` |
| `M ` | `docs/orionis.session.stores.memory.MemorySessionStore.html` | `e6aa4cdf3eb1d0cfb94e7811b52576f1c848a155e51780343af4949351c2c0ce` |
| `M ` | `docs/orionis.session.stores.memory.html` | `bf7b2f71d833904adcf2ff4388fba5ababf64935caedf4911fd02e54542f1881` |
| `M ` | `docs/orionis.storage.AsyncStream.html` | `90de429e7a2395fe551316fc5c45719534a3043009288bba010a6aaff516f491` |
| `M ` | `docs/orionis.storage.StorageManager.html` | `145da5627ab2d4d366a21f66ab43b6837c03470aad322e1172477e8fd1635a96` |
| `M ` | `docs/orionis.storage.UploadedFile.html` | `2e5ad7171409cf9fa1081d3453b12da56ea9a6d675ff662e69c7b8f65608db6d` |
| `M ` | `docs/orionis.storage.buffering.html` | `e06e3aafb6a026b551492955df2b3715d54f0e31e45a31c3d480c0fbed5d6b80` |
| `M ` | `docs/orionis.storage.contracts.IDirectory.html` | `3b394dc4ec74f23674960031447414b1553b9dd44baba76e1bbbe076774f4349` |
| `M ` | `docs/orionis.storage.contracts.IDisk.html` | `2d24d76ee87239e6c4cb38bb4404243b4754201a3f23862deff24eedf285fb6d` |
| `M ` | `docs/orionis.storage.contracts.IFile.html` | `6d35473d1936a351bbb5e60cb1b494fe2332c4dafccd59f904bd0d53f49694a8` |
| `M ` | `docs/orionis.storage.contracts.IStorageDriver.html` | `265f19913b2d657690cac548e5dbc3b10657cdc4450c6bd02f67cd68e60bbac7` |
| `M ` | `docs/orionis.storage.contracts.IStorageManager.html` | `f130a7cee2f72862a39fb5180cca6e4dceb6bc9f376bd52b05407a7237a6e562` |
| `M ` | `docs/orionis.storage.contracts.IStorageStream.html` | `ad53d455a26cb514987a223539b3d5e3b0a1519ee08f1a7bc4fa1f1abbb034ae` |
| `M ` | `docs/orionis.storage.contracts.IUploadedFile.html` | `f92796082033cc39fbe891b1eee401c1d3e031255e7772e3fb51ab20213f7df4` |
| `M ` | `docs/orionis.storage.contracts.directory.html` | `0f2f3ec781ddb600f2860e0e7ba205f0ed8e9e2e522dc8974f20e458f19fee33` |
| `M ` | `docs/orionis.storage.contracts.disk.html` | `06355fefb28b59f39724effc91ffac17749ced9bd0b92df36275be64a21864cf` |
| `M ` | `docs/orionis.storage.contracts.driver.html` | `72cf9b55745b829685614848ec310d72dd52bc9b387755d62267d5632005fa74` |
| `M ` | `docs/orionis.storage.contracts.file.html` | `6384195ea53f9e0e252fc7d0f2677a7e1f96105c7b069bfad2b8c60badbb8037` |
| `M ` | `docs/orionis.storage.contracts.html` | `ca6f6774df68aa956be5cf43a7cbad8d6bd0e63b60b961816bab69d88230c35c` |
| `M ` | `docs/orionis.storage.contracts.manager.html` | `8d8ff5cd916c80c8377bf186ae9bb94d4401c2100d64b68604bfc4ea30366a0c` |
| `M ` | `docs/orionis.storage.contracts.stream.html` | `7be57a78d049b93e22d30b47ee0e1394d74934d83625634b66254058e506deca` |
| `M ` | `docs/orionis.storage.contracts.uploaded_file.html` | `ec4655f8dce66ee9c89ee78b04f43b1f95003db5f2f8ae1b6894a17b013f7360` |
| `M ` | `docs/orionis.storage.directory.html` | `52d292c65b9bedf9c99178770aa44883fbb28ef18f333ca4e34578c2e131f493` |
| `M ` | `docs/orionis.storage.directory.module.html` | `ade3da5abc061f2247caea9c7c36a7151e114bc42e9c884ea7960d717cfa3008` |
| `M ` | `docs/orionis.storage.disk.html` | `ab7419c44267f999d13032098e5a59f90d0f7d08200b353a4a7bcf037e89b674` |
| `M ` | `docs/orionis.storage.disk.module.html` | `831d0b5c6c4584e9bfe415f589ab7717ec3d4e031809fba9ef5776572ea951f0` |
| `M ` | `docs/orionis.storage.drivers.AzureStorageDriver.html` | `f98bd5bbcc4c99b695d2cc0e4bc2e5708f72f87b810a843b3a2819de638948e6` |
| `M ` | `docs/orionis.storage.drivers.GoogleStorageDriver.html` | `f21734e33103ba41b352c1b6d823d7e780d4ec91ae8920b78386382bdc000e66` |
| `M ` | `docs/orionis.storage.drivers.LocalStorageDriver.html` | `016b0e886e2b200ac3f9c21584367cdaabd7624a808bfbef99f4a4386737e40b` |
| `M ` | `docs/orionis.storage.drivers.MemoryStorageDriver.html` | `408919b7c5678dccb0bd6df100747d43a09d9aacced3c2540858af69bf8ce033` |
| `M ` | `docs/orionis.storage.drivers.S3StorageDriver.html` | `5d6ddd532eccd96e31c8500bcc1c43d4edcd56e49bb4cece21cfba47318fe66c` |
| `M ` | `docs/orionis.storage.drivers.azure.html` | `be43c97459cc97c70e00f5c83d5779bfa2a0baa93644a1022dd6fb90513ae6d1` |
| `M ` | `docs/orionis.storage.drivers.functions.html` | `b15275a8bb75cd55a0b289f2ae57e2d71a5e417ee3e680828c9620743334abe7` |
| `M ` | `docs/orionis.storage.drivers.gcs.html` | `e6a8671a17445d08810fcf63a98af8f657cbe4fc9cb27b5d5732131943b4e413` |
| `M ` | `docs/orionis.storage.drivers.html` | `ea29a2d3ff0bade6d6b63db186f267d2d7ca2c62898408fe332fcb3e8eb71c2d` |
| `M ` | `docs/orionis.storage.drivers.local.html` | `aee91a5b1ee00759a79680db10275ad69922804eed8672b093ae9b51335dcea6` |
| `M ` | `docs/orionis.storage.drivers.memory._MemoryEntry.html` | `c0b6e25166dea437a1195292299349ee80c3aff20bb4fa6df1b26583bf76b997` |
| `M ` | `docs/orionis.storage.drivers.memory.html` | `7fa48907a2d8a1a674a62e52f02869bd55f5ba8d8edb86714b238c7addcd530d` |
| `M ` | `docs/orionis.storage.drivers.s3.html` | `d7b0900d191063fdd3017220bbce862401c228ca12df723a3c762e36492ead70` |
| `M ` | `docs/orionis.storage.entities.FileInfo.html` | `35a07c6422e3c0c07680d3ed2c95a4f6daf40ada4bf9031644fa372cb34b7616` |
| `M ` | `docs/orionis.storage.entities.file_info.html` | `b722f904d93798241076c58ae6cb44c104c2d21c613fda8f87d8480eeb162492` |
| `M ` | `docs/orionis.storage.entities.html` | `e42231ce9105852ad8a4916ede65374575cb254db81f98d6ceb5a5eb1ee7aed7` |
| `M ` | `docs/orionis.storage.enums.html` | `be78b271e9839d6981ebca0a672c2ddb8d301b543d0bfc70e4a1c75efbf78c79` |
| `M ` | `docs/orionis.storage.enums.visibility.html` | `6266d064c8f5e4f7a411609e9c751c5aa776a9b4606843ceb92f9b664fe07a1b` |
| `M ` | `docs/orionis.storage.enums.visibility.module.html` | `319fb8a27d1ed87d08c0787c07fcf99d9ec33fdd6d64d789ca8679bc19a7e811` |
| `M ` | `docs/orionis.storage.exceptions.DiskNotFoundException.html` | `d190ef88f1c4cb23363636e70ba28a7679eae91f580bf30d82b8be660961d7ea` |
| `M ` | `docs/orionis.storage.exceptions.DriverNotSupportedException.html` | `1e6258a766f4172b8002a5da887090837ed4f5d80c2c44705f434377f28b982c` |
| `M ` | `docs/orionis.storage.exceptions.MissingStorageDependencyException.html` | `61ea8055993e3d775dd46abde1c6775617e381fb1b36e1170292761d73556d9e` |
| `M ` | `docs/orionis.storage.exceptions.StorageException.html` | `a12f43c383cb38e63d7a9af507531065f814511f41ce8e56009bd17463b5e831` |
| `M ` | `docs/orionis.storage.exceptions.StorageFileNotFoundException.html` | `2f35b66fd0d35ec7215315c06696e3f5c56cd5b2b3046f8566dac790110b9b21` |
| `M ` | `docs/orionis.storage.exceptions.StoragePathException.html` | `f93c6cfa83506cfe8565ecd8d38355d3c2399e87a8db937fc19ee71cf7b5b618` |
| `M ` | `docs/orionis.storage.exceptions.UnsupportedStorageOperationException.html` | `9be74d2c8332e0b93f8c2160f29f8fc16013c3f7ad0368cd7ac7db323afc6551` |
| `M ` | `docs/orionis.storage.exceptions.html` | `c921de462165468c20cbf5c08713d78c17e13257dd6e91b126636ca1de31eef8` |
| `M ` | `docs/orionis.storage.file.html` | `6cac7ddfb036d834d2a1441c12bd5662ef480cf1dbfee8863caf4f55243d5764` |
| `M ` | `docs/orionis.storage.file.module.html` | `2abad116da8a87c5588005396b229cdd01fa46f45b5ab3ca1aef952e7209692b` |
| `M ` | `docs/orionis.storage.html` | `68146f25b0a7ef30b93ff45cad41cf4814eea0a840f1f16a559accd231bd7f49` |
| `M ` | `docs/orionis.storage.manager.html` | `6b3efec57f44f123cb9b3bcaeec05b52bcb7aac186aaadd02404354a2fa8b584` |
| `M ` | `docs/orionis.storage.paths.html` | `0b9a289dbadaa57c0009022b6c0ee412ecb5c391ca987108d49c753fe49d2e9c` |
| `M ` | `docs/orionis.storage.provider.StorageProvider.html` | `c969fb978f01c5926f7585b2c88aee666a34423f8e98766a0c7c067e5f8a5d58` |
| `M ` | `docs/orionis.storage.provider.html` | `06b8874345f7b8626033ec9c4afe3897b12c23408a993451e45c31fddaa130eb` |
| `M ` | `docs/orionis.storage.stream.html` | `3cd7ef5e557ac5ccc4b0ed89ce689729f7898ff51b1401702583d58304aac37b` |
| `M ` | `docs/orionis.storage.uploaded_file.html` | `3c17bbc25be23c462229b96500e516f8292a04968f7b6903eea902d51e7c4506` |
| `M ` | `docs/orionis.support.concurrency.BoundedExecutor.html` | `51411b4663ad74a758f3ac63b2a5eeae4e37c3c75ac5ea933e3d23d8b14c3a44` |
| `M ` | `docs/orionis.support.concurrency.WorkQueueFullError.html` | `5c09c184c38b034b16137d19a37294c4353e0ee5e666b68bd1063d60b460eed6` |
| `M ` | `docs/orionis.support.concurrency.html` | `37ba04d8cbc3a0a36b63b37be89847765c304b431cb59e04438fa0c763a914fe` |
| `M ` | `docs/orionis.support.entities.BaseEntity.html` | `e12b134d931c0907b508fba627167dfbeeac563d43c3861e2661933074a20ccd` |
| `M ` | `docs/orionis.support.entities.base.html` | `35491ef74b4460c173c2ea36a9035969e48c8cae03d8d586b9f2e8cb4bffe1ef` |
| `M ` | `docs/orionis.support.entities.html` | `7339fc78674c1b5663e6a7b761fea7d07a010066156c2f1bc0b81ef8d099c625` |
| `M ` | `docs/orionis.support.facades.Crypt.html` | `21662aff27a7724b7e7c10369faf63d9b82541cb474164de0dc5965ae81e3b87` |
| `M ` | `docs/orionis.support.facades.Log.html` | `debba0b638034b3c9c9287d185facbf39ba20180eaec6f62ef4359d37199ee95` |
| `M ` | `docs/orionis.support.facades.Route.html` | `dd404dd5e30bd61824095ec3d9717170e502751ff1ba28f507d0ee71c28b3b48` |
| `M ` | `docs/orionis.support.facades.Test.html` | `0a75999eaab5a9181fffcf3e6f80fa9036aee21fbaebb465ad6b38aa3efcd568` |
| `M ` | `docs/orionis.support.facades.application.html` | `cd7bf1a7edd0e73dec0fc1ad3cb91738e3cb798ea9de65d3bfea579f3411f0d4` |
| `M ` | `docs/orionis.support.facades.application.module.html` | `ca3d2414ea7e392e232bd8262042fc46ef3adc4ddee5146ea023c080f4f5f422` |
| `M ` | `docs/orionis.support.facades.auth.html` | `b99b66e2c5bdb80c1492c458b7b82b09ea98ea2836564e5b5d22ebd3beef570d` |
| `M ` | `docs/orionis.support.facades.auth.module.html` | `2674ddef0b2c54a7aa5f4419349f3b0eea25745c0e139ebb3ad22324c09a5e7b` |
| `M ` | `docs/orionis.support.facades.cache.html` | `51cfae4c865f3234cd3062936768fb27735d0fd9320b7e80eac72a600e069bc1` |
| `M ` | `docs/orionis.support.facades.cache.module.html` | `47c1d14861c46364915337c1785b988ca81065491ffec49541663d4dde14d73a` |
| `M ` | `docs/orionis.support.facades.catch.html` | `e187bde21274e93047680ee064ae46de09df1ef6b35cad187a61ccb486d75729` |
| `M ` | `docs/orionis.support.facades.catch.module.html` | `5c553bb9abb2050bda5c5f9e4c5982715626736b502a6167a3a4169ee78d4153` |
| `M ` | `docs/orionis.support.facades.datetime.html` | `6dd73a4de3f16def076b3e30eb2b8ad99d69d9e252a472e8b2125eea7229a2af` |
| `M ` | `docs/orionis.support.facades.datetime.module.html` | `683468c413c16343b8543ca0041223f7f41455429ac17e78b8f1ab39c59f0003` |
| `M ` | `docs/orionis.support.facades.db.html` | `f4b411cab0785191ebeedc4f6ab450a0a0abeddf9db90a21f137ee940c6dce94` |
| `M ` | `docs/orionis.support.facades.db.module.html` | `e78e8337313a8699990e58060b932f5720496e23e454b45491d5b2c2c0b187e0` |
| `M ` | `docs/orionis.support.facades.debug.html` | `281332ccb3faadeb08dbe4afc4bc9333f34fa2888be67cb96a867b7ef9969a59` |
| `M ` | `docs/orionis.support.facades.debug.module.html` | `8833f56d4e712648f66d47a9b031570708aa642a3f3d7dded80d832299d36c5c` |
| `M ` | `docs/orionis.support.facades.encrypter.html` | `dad394e3af3c154645ccc8f0865a4b20dd4cdbde1e0d4ec9553bc2ec298a424e` |
| `M ` | `docs/orionis.support.facades.hash.html` | `33fabde5690fd56aaec1f50704d51f90f15430f0cb161222a8d646f818ecf273` |
| `M ` | `docs/orionis.support.facades.hash.module.html` | `816114c53c11fa4c0b83db2d9bbbc135bc632d7114e2cf25cc1e7bc5359930c1` |
| `M ` | `docs/orionis.support.facades.html` | `d105677a890bd1dccaee508a68522621a3eaea16f28f22075b5bf35a2b524746` |
| `M ` | `docs/orionis.support.facades.lang.html` | `15756fb9d7f9933e6250a689c277926b0d94c2784395a3e1faa9b4ef23c5a6a6` |
| `M ` | `docs/orionis.support.facades.lang.module.html` | `56989d40ffdcc12055274acfcb6a70c55414668f457257f61555f7aceff2755f` |
| `M ` | `docs/orionis.support.facades.logger.html` | `18433d4280e2a9ec8af1c029740ad47edcefb3f516d25803f522df0f36f6f147` |
| `M ` | `docs/orionis.support.facades.mail.html` | `3b11c26ec5ce2ffc86d3242aeacb772eb4acb258e4e970d51b558dfa532da1d3` |
| `M ` | `docs/orionis.support.facades.mail.module.html` | `17652d850fe04656a1a44492b6c74faa419d41e010067284da9ee17079a1fcc4` |
| `M ` | `docs/orionis.support.facades.mcp.html` | `174f0fa6265f7ff006a95de1c6c8a85c0e664d7788c8cd208fbf155c24c7f7ec` |
| `M ` | `docs/orionis.support.facades.mcp.module.html` | `da0ce27067832ed771d43e0a26eb7e5cddea26e10a87553b3ddc675374ed84d1` |
| `M ` | `docs/orionis.support.facades.queue.html` | `74212c71d651da8f258c8f75340e10d07916ffcc953cf03b19e9825de376a36a` |
| `M ` | `docs/orionis.support.facades.queue.module.html` | `46310867667a5900e15358a03420a103b6413ac36ee408dd1b4924f418c21e9e` |
| `M ` | `docs/orionis.support.facades.reactor.html` | `e52991cc8ab222f070af58f990c65fe9889632492501977fed59d671d5534412` |
| `M ` | `docs/orionis.support.facades.reactor.module.html` | `ac1121db5aa0e390f71fdd114358f7e3bf1a41c126f4a192c704ad6997b78ae7` |
| `M ` | `docs/orionis.support.facades.realtime.html` | `3d1c62e29e4349cba786b2ccc71ff021e1b193307d2b4414f589ddad3ce42d84` |
| `M ` | `docs/orionis.support.facades.realtime.module.html` | `c06ad5cd7e4edb90c0054b1cbe6eaa33a8c5ee829321d42dd21b45326aba8511` |
| `M ` | `docs/orionis.support.facades.router.html` | `b10cf8e7e7f7fa231a7bc0c079ae4a58fc066f087bf81f6f23218acff4a861d7` |
| `M ` | `docs/orionis.support.facades.schedule.html` | `de68336e04a213e3c31fa3020e43e2d7f8613a452edbabba1bbe207b7707c98b` |
| `M ` | `docs/orionis.support.facades.schedule.module.html` | `de00573bf306d664474755173b654741ca47146bd2dfd7454de0886c1783a24a` |
| `M ` | `docs/orionis.support.facades.schema.html` | `86936fd52ec64abf39af54ff888dbf35b5e0c91a09df4712e1cdbd1bac7ebc5f` |
| `M ` | `docs/orionis.support.facades.schema.module.html` | `da600ba6a102e4d041d9e8d6fd1dd671e51133b7bdaa28e3d015d12d4af296d5` |
| `M ` | `docs/orionis.support.facades.session.html` | `8cee06dec43117eeac11a18fe67c5edf3fafe2a2a14144759be8fc9024478388` |
| `M ` | `docs/orionis.support.facades.session.module.html` | `f0ddbce69b5c476efd22ba7404ef166e27c01d9d821cae22f5d589249dd65834` |
| `M ` | `docs/orionis.support.facades.storage.html` | `ab3a7ae8c527b4332e366144aa876b07e9d16e145e8e4e06069ce5d2bfc1629e` |
| `M ` | `docs/orionis.support.facades.storage.module.html` | `50becf07d5dfc2ec56b1c5ed9acee306bac34ae3eccf6923e2b5b03d09776e7f` |
| `M ` | `docs/orionis.support.facades.testing.html` | `e44ba1ff3ed50dd8e4a478f82881ee8c69ae407ee472029331d54c0c9c66e4b0` |
| `M ` | `docs/orionis.support.facades.view.html` | `d5a7ed9e871ef1d67052a54f87c9cc8aeee15e06e4c0c8e1745591428006f89b` |
| `M ` | `docs/orionis.support.facades.view.module.html` | `07a78c8b1d3bf2b83f22a3f1b94018741faadc218daedec3566b357b0c0c6f8e` |
| `M ` | `docs/orionis.support.formatter.exceptions.contracts.html` | `d0324485c4cd41f89dc6999bad16c0a53d368bdedef6b186cc70a3f40f761a6c` |
| `M ` | `docs/orionis.support.formatter.exceptions.contracts.parser.IExceptionParser.html` | `4fb49ca260a94985264834002f5d5d84eafa53d46c3e72911a0227467cc211f0` |
| `M ` | `docs/orionis.support.formatter.exceptions.contracts.parser.html` | `e20ff3ff87df293e8faa627c5b55b20936ece01d11b5cae7a38a7f8749886e74` |
| `M ` | `docs/orionis.support.formatter.exceptions.html` | `3e110e7a5ca4554f216be321fe9ff0d64f71af79ad00040a5abd93ef71eea031` |
| `M ` | `docs/orionis.support.formatter.exceptions.parser.ExceptionParser.html` | `15ae6c67e47c7b6de6c49233a531ebc80ba7b0a5d7fcb3208d815d4eff2ecd53` |
| `M ` | `docs/orionis.support.formatter.exceptions.parser.html` | `b25f5662aabe7e59e8af8d1d1edbb3d2913ce8a937d8fa5a4a96400c2143587e` |
| `M ` | `docs/orionis.support.formatter.html` | `5adf45393aff4b33355ccf1cf44d9e6c46a23350bd7f2726510491fb1c332cca` |
| `M ` | `docs/orionis.support.formatter.serializer.Parser.html` | `0b219a9fb102855a34505b6e5731ed9e88a93c34c9f197f1eb34e892cd4f70dc` |
| `M ` | `docs/orionis.support.formatter.serializer.html` | `acad76d48dbab0e848a3604050cd06e7401726f250fbdcb416661d5891773993` |
| `M ` | `docs/orionis.support.html` | `9d876ad8a566022fa1677daee24c0935978e92fad4a84b009b1837e2e7cda452` |
| `M ` | `docs/orionis.support.inspirational.contracts.IInspire.html` | `0e073e75af33ef918400184cafc6e6742594df975596355bcdb709442a32979f` |
| `M ` | `docs/orionis.support.inspirational.contracts.html` | `7899183a77bbf6f9de201912e880a8fc1fbc120149ffb611627025e3835acb66` |
| `M ` | `docs/orionis.support.inspirational.contracts.inspire.html` | `58d385ccde737efca1a7422ddef30ab1d08421eebe223d052e258f73e0cae0ea` |
| `M ` | `docs/orionis.support.inspirational.html` | `7ab7c009f99d4bb99526fd13905ae97a14e22e8d33681cdf692bdb4d63b5c8b4` |
| `M ` | `docs/orionis.support.inspirational.inspire.html` | `0c4789d1d341bb2d44c5ef693b1a092f409037b0b2a7493153b9785179f66c05` |
| `M ` | `docs/orionis.support.inspirational.inspire.module.html` | `69032f1d958c02d0a6c7e8612ddd778fcd6a4da2ae9b457d67b380d232ec9f05` |
| `M ` | `docs/orionis.support.inspirational.quotes.html` | `36513eecb87aa47690212b09633b7501354f7116b00bea981b043a8f0d25aa65` |
| `M ` | `docs/orionis.support.patterns.final.Final.html` | `a668b2800f17c3f2bc2d84a106bed37b60f431533c1709fcfb32870ed52e99b4` |
| `M ` | `docs/orionis.support.patterns.final.html` | `45a476fb8f58408faacad209267e1b4ae7df4763ddf9c04a6bf24d901b325b2b` |
| `M ` | `docs/orionis.support.patterns.final.meta.html` | `272b970a2624e7f9393fe5b2038e184e92ea8125cc2a1ddb1c27bcb57ad30775` |
| `M ` | `docs/orionis.support.patterns.html` | `c20bbd96e1b3246bc3b7dcdfa0545c1776eb9a517598f8cc1e16d3d407731944` |
| `M ` | `docs/orionis.support.patterns.singleton.Singleton.html` | `aa8e590866c1ab16e0a969cdc6bae44f19c9fa2e8586a4034eb624c09a962c60` |
| `M ` | `docs/orionis.support.patterns.singleton.html` | `8d3f38ee585c2f931aad13eb00f0081cb0fcce1e28e3ab71227690af4d50ce23` |
| `M ` | `docs/orionis.support.patterns.singleton.meta.html` | `defcc7b26b64c37681950d37ffc0d907063acc5bd8cf00ea9e6a871d25711017` |
| `M ` | `docs/orionis.support.performance.PerformanceCounter.html` | `1647eb6edb54c859e78232f981a8d84f9a8b6e6e5dd052e1efaca01d77834f64` |
| `M ` | `docs/orionis.support.performance.contracts.counter.IPerformanceCounter.html` | `09114123a7d22a24e64b008dcd4936acbe03b0dd9ad988a0f2cdf81998d1e3e4` |
| `M ` | `docs/orionis.support.performance.contracts.counter.html` | `d6a15bf4df3947ed405118ba2387b35de07a99e2857666e1c5a8a472165dd74c` |
| `M ` | `docs/orionis.support.performance.contracts.html` | `1b9ae95a7d6c32168309101d413d1bdda55d6ea3daebbc32fd166b2cba839d6f` |
| `M ` | `docs/orionis.support.performance.counter.html` | `6a5a17351eceecc53f609f833d1c86990444f804e58a67a665e92aa931fecd37` |
| `M ` | `docs/orionis.support.performance.html` | `3612329f765bb167f87d22c5c29532b9c8ff34c2573ff08f4b0b804c9deb56de` |
| `M ` | `docs/orionis.support.structures.freezer.FreezeThaw.html` | `a54491d5ac0cedc59d3114faba39066cf65f3a2679a41f008b344f7542b6876f` |
| `M ` | `docs/orionis.support.structures.freezer.html` | `15a81d03d68dd8d4d900292a748c4b51845d5d73c19cd5cbfb7d2cf8070b327b` |
| `M ` | `docs/orionis.support.structures.html` | `3c1b305aa7ba580096444a4afee37fdfd6f49b1fdb60d09eb345c03fa2e5886b` |
| `M ` | `docs/orionis.support.system.contracts.html` | `fd97cd55337d285349029f4a3734df8df302b016b020573261d7a8a7f33c757a` |
| `M ` | `docs/orionis.support.system.contracts.workers.IWorkers.html` | `78a3b01471b7082268b3f1d825b5c2e5d824ba9a343a2c68cd88b25a9224b74d` |
| `M ` | `docs/orionis.support.system.contracts.workers.html` | `3f947a328aa9fae406568947b5b5e50b2f9bf67eb1a2e80e713a1544b99982b8` |
| `M ` | `docs/orionis.support.system.html` | `e59343755e296ab1e044d8f4e84c05da27112d02a74cde37624036e749ff5b68` |
| `M ` | `docs/orionis.support.system.workers.html` | `42c4be2ec1fd4b21eca64d825bf3707cff95245e5c8145c60864db49215d4c12` |
| `M ` | `docs/orionis.support.system.workers.module.html` | `0940d39a3cd002f2638b81b5bb77374171a57c6f7df79a47491b5746a99d57e6` |
| `M ` | `docs/orionis.support.types.DotDict.html` | `ed0b263b1fdf3f6234d9bd5f22f86f1c3cd7f98f3c09c9105fe543c77c6a92fa` |
| `M ` | `docs/orionis.support.types.StdClass.html` | `6cd868087c13f01aafc64a6acfa6d024768dccd817e9a8acdeefe8febb83629f` |
| `M ` | `docs/orionis.support.types.collection.html` | `8db3d1bb33e51e8a085c9045b6d314ed83437d4049ff929fc84c2168ab934273` |
| `M ` | `docs/orionis.support.types.collection.module.html` | `eb54317efbff46f1c6fda9c44d5a33acdcb0e16bd2c39fe43c2bdaf996c35c8d` |
| `M ` | `docs/orionis.support.types.contracts.collection.ICollection.html` | `ed143e63a5f9c499f72c973c1a9514afecf999bd36aca6cd1056aadef7f307f9` |
| `M ` | `docs/orionis.support.types.contracts.collection.html` | `f446b62e652fd5b6b830c29b562a70867a5df22c3513bcb9403d657b94532413` |
| `M ` | `docs/orionis.support.types.contracts.html` | `50906b2acac77417bbb8269f58106ea6ea9f78c2851b32ca1212d6df35d1596a` |
| `M ` | `docs/orionis.support.types.contracts.std.IStdClass.html` | `f444525ab76f2af2f0d26b85232e0458e52c494a17522216b379b5154f38fbca` |
| `M ` | `docs/orionis.support.types.contracts.std.html` | `73ada402ad55ef80fb33eb6ce5da9c77df4b018f7343d983a164002680bbbef9` |
| `M ` | `docs/orionis.support.types.dot_dict.html` | `3b54e4a0cd9d6e53ae2316bc139baa7e010e2ab35571aafcdaf55836ed20d3ec` |
| `M ` | `docs/orionis.support.types.html` | `95ee4be4f141d457b115b00611304d7b25e7e99c76c12aa7c3df77751defdc62` |
| `M ` | `docs/orionis.support.types.sentinel._MISSING_TYPE.html` | `f9c3967ac6d9ff2c14010d41430384309b62907246aece4252e3468313c43eff` |
| `M ` | `docs/orionis.support.types.sentinel.html` | `c0d739120b7c81bb533f97b63753b644d89e23e6f6c68be838042e78c814ce3f` |
| `M ` | `docs/orionis.support.types.std.html` | `ddda307c1f248a74dabfdfecd072fabfabd4211c9a1e2a954587f10327ac8741` |
| `M ` | `docs/orionis.support.types.stringable.html` | `87342b3033f71f29bacd57df9c7b05024e2523970ef2acfdbe031c3b8122ed35` |
| `M ` | `docs/orionis.support.types.stringable.module.html` | `008e955a91718bbd7dc1fa2c12f7d231fa73ae3d2c3e92448109325eec2fdcbf` |
| `M ` | `docs/orionis.support.types.uniqueness.html` | `67fed3fc5ff48ae47530d5a4b0fbfeaa2cc4bb4854a5f068e14e92a81a4482c8` |
| `M ` | `docs/orionis.test.McpTestClient.html` | `b7e8f4b70e0b20c7737a91a5db77f58fd7479517d5f0a6e8edc3f718db211223` |
| `M ` | `docs/orionis.test.McpTestResponse.html` | `7cc2d25a9237c2d43f0f8b553b749f700ace7f68a715636e35fd2ec79d992173` |
| `M ` | `docs/orionis.test.cases.TestCase.html` | `2c7608baee1b1b102a57d3b20288cb76c7f61d666c025942441ee36469e08944` |
| `M ` | `docs/orionis.test.cases.case.html` | `fe560ca2cceeb0bab97a08caa4e398338810940cb77e687c72b49fa5a117fc4f` |
| `M ` | `docs/orionis.test.cases.html` | `7c52887716438cee576cd28f18fb7d94bcc5147c76148b116274ebc58bd1df12` |
| `M ` | `docs/orionis.test.clients.html` | `80689061cf0f9491d8f2cd435ddc235676729b1ddb794b4ae4c438d7d5a5d4e1` |
| `M ` | `docs/orionis.test.clients.mcp.html` | `2e6c9831281e01ba39d7d5d1331c7c9162597c5e818b4f3c722a51e9e58ff908` |
| `M ` | `docs/orionis.test.contracts.engine.ITestingEngine.html` | `63e9a516725ebff9e267df080bef03932cbc768c21b86efeda92931b1a608012` |
| `M ` | `docs/orionis.test.contracts.engine.html` | `b52ef2f0bf688bde84c365e0683902f1e55f2d97028b10e3e711b8027507f127` |
| `M ` | `docs/orionis.test.contracts.html` | `414d8ce742d6703784a9a536598e0d297ad5444a4d3b56bf7d71957f825fd855` |
| `M ` | `docs/orionis.test.core.engine.TestingEngine.html` | `3fa50e302493fa44d5acdfab1bc0816b599b5d777d91dc59551a448c08ef9164` |
| `A ` | `docs/orionis.test.core.engine._PatternTestLoader.html` | `1ea0a7336f1f0ccfcb5e89f64db904299e13d8626158d68d0b288fb5faa87fed` |
| `M ` | `docs/orionis.test.core.engine.html` | `bcc34c62c17d1d8da6c8ac7155430ddcce1ad01dc19c1c20eecf2043efa5c4bb` |
| `M ` | `docs/orionis.test.core.html` | `6abc3ec452ec297479a0649bb976edbc48b1a40f22453ab50892cb38c93af085` |
| `M ` | `docs/orionis.test.entities.html` | `03fe69892023e1480b32ddc6e2aceab8518597476b189a1b499217c1f6febe2c` |
| `M ` | `docs/orionis.test.entities.result.TestResult.html` | `35b78026f7ba61ff4de47381ef147a939c703c5d6cc9f4d49f11f219460e54d0` |
| `M ` | `docs/orionis.test.entities.result.html` | `e1bb0504b4d11e529aeacd5350a981b9ffb4e836d560a1c4f9842346af24bcca` |
| `M ` | `docs/orionis.test.enums.html` | `9e1b7e47e2d43730245d8ca8a4bcdc92d269f7562837617be2391e10f6bb01d5` |
| `M ` | `docs/orionis.test.enums.status.TestStatus.html` | `24435ef8d5171998a6b13e62c9de9563f37cf83fd7cf40e7c2a933a1ae4fc82c` |
| `M ` | `docs/orionis.test.enums.status.html` | `1df70d46bcdb46dda4f598fca81428ecec6f801d55a23a44645187108f8e81b5` |
| `M ` | `docs/orionis.test.executors.html` | `19d42c8b4f2c3e7f63c5be61d90190485d2676007304edc3ce1dec549cb19409` |
| `M ` | `docs/orionis.test.executors.results.TestResultProcessor.html` | `29de401afc054bf833582f153fb8449aacb0ef72fb1b5dc615b365c6dffd805e` |
| `M ` | `docs/orionis.test.executors.results.html` | `80220cf4c86cf4ed006c7de6d6742006670683f1b1de0ba935b59b839d4d90c7` |
| `M ` | `docs/orionis.test.executors.runner.TestRunner.html` | `522d79ac29349d4e568773638c5783a6809bc5e248ca80947d71ce0dbe161deb` |
| `M ` | `docs/orionis.test.executors.runner.html` | `304968b405e4727cfd7705a1301c5f6378062f9b9613b8216ae61f398089e72a` |
| `M ` | `docs/orionis.test.html` | `f689cfc8bed8783196de22431a3c495f3f457d87b016b748827efa22eb3e15fe` |
| `M ` | `docs/orionis.test.provider.TestingProvider.html` | `60a6c4f14296186da3092e1f8c811bc7acd4a70be70f2e7cdabc9626f6b10346` |
| `M ` | `docs/orionis.test.provider.html` | `a25e998da6ef7515a541a2e205cc3bb35dc540f870a5d7f1eb44049b12f1c0fd` |
| `M ` | `docs/orionis.view._failures.html` | `d6204aa2982cc0c8a9ec0256aca079607c02cc23c7252c5a3ab65fc7df4e46a7` |
| `M ` | `docs/orionis.view.cache.OrionisBytecodeCache.html` | `e3e3274f855f37ce11288616e2b5c5974bcc60268f74ddbab2e67eae22a26861` |
| `M ` | `docs/orionis.view.cache.html` | `835305bb0f68fdd1b766e2d859f358fac2385fbaf17c091c35a5b67d5c2d0f8b` |
| `M ` | `docs/orionis.view.contracts.engine.IViewEngine.html` | `c8b7ae505ee6c56e15fc6e9ede55faddd51adb6317033a62ad981bb64a915272` |
| `M ` | `docs/orionis.view.contracts.engine.html` | `d595684a96bda899f2b6fc63cd0ed93135831623b19042637c741eebb4ab08d2` |
| `M ` | `docs/orionis.view.contracts.environment.IViewEnvironment.html` | `4157a0e3eeab15cb9c6f9c5b80c083c7d814b62864586257880b6651ce8c66a6` |
| `M ` | `docs/orionis.view.contracts.environment.html` | `22fef21ae348e707fb6635ec0044a9f66f15ef0589b15d987b82a39e86e3af17` |
| `M ` | `docs/orionis.view.contracts.factory.IViewFactory.html` | `2f87538c19315c555149c50aa6679a76a70d6192937d0812d42aaa229673194d` |
| `M ` | `docs/orionis.view.contracts.factory.html` | `f9fe1563c6c209281827ac14dfc76d56961aefc9b9b961b2e2037e4d894953e6` |
| `M ` | `docs/orionis.view.contracts.html` | `4837443d6256f9ee02b4125cb47522984c7ff634f3126f44e6d841f807aea4e1` |
| `M ` | `docs/orionis.view.engine.Jinja2Engine.html` | `eeab24e5f67a076e9e5cae5dde0cabc874c5933daf9ada932f01eb2f9fe69fd7` |
| `M ` | `docs/orionis.view.engine.html` | `948402d0f802a464a5c49a785f625f750fb8fe27badca66ae03b138588071122` |
| `M ` | `docs/orionis.view.environment.ViewEnvironment.html` | `38bc9eea831959453b93c37f0865a0ce0ee1db3be84b6adab03e14165ac92f6c` |
| `M ` | `docs/orionis.view.environment.html` | `c0f02b3b4cb582de332b99ff90b879ed7363f01d6711c4745db020f5b91cc20d` |
| `M ` | `docs/orionis.view.exceptions.ViewException.html` | `077c3123b52958bbc86b59e289bc69c08583341ac2fb6b02ece0827499220684` |
| `M ` | `docs/orionis.view.exceptions.ViewRenderException.html` | `82e4d51d2e0f675b442a9e82efa0e0bc1d4a168c011dd0bffc05b96b64470054` |
| `M ` | `docs/orionis.view.exceptions.ViewRouteException.html` | `5049086e380f74f5f252af3cd8b4698e220e68ea2e8782158535a42e36aa787c` |
| `M ` | `docs/orionis.view.exceptions.ViewTemplateNotFoundException.html` | `29608078876b7753017b3576fa9a8cde470e6540cd7a2acceb6ccbeaa1aa2a3c` |
| `M ` | `docs/orionis.view.exceptions.html` | `672616c0f55c5ffe0b4ab65c6054dd2df9d9cea6856501ad4fc76b8bccaf1c85` |
| `M ` | `docs/orionis.view.extensions.CsrfExtension.html` | `b5f6b32f5bce87171ad4e3946630010dac99de7afc5c786b2defbb3830735da0` |
| `M ` | `docs/orionis.view.extensions.csrf.html` | `06295b053a5655afbec5efbf121df46dfe42b84cca8986cb22603e498470a069` |
| `M ` | `docs/orionis.view.extensions.html` | `8c54446ab5df546a97c677cebbdcd654cf11b00b9223a3304df32dfef066b8fd` |
| `M ` | `docs/orionis.view.factory.ViewFactory.html` | `1d2621bdd0710a427435242d42ca5957b6321204a52028d906390920d6c45dff` |
| `M ` | `docs/orionis.view.factory.html` | `27371f3d8fd3ce3ebc46ec782f0eb0884accc97aed3d60facb0f6eae091fc3ed` |
| `M ` | `docs/orionis.view.filters.html` | `46c1cb56851c4c175b93fa10d1e35780c6622484b4c3744adf2038c23c3b23ee` |
| `M ` | `docs/orionis.view.filters.json.html` | `ffacf0096fa810fe055fc13c500df8f1d1ba9fa546841b223733f98a4d7216a6` |
| `M ` | `docs/orionis.view.filters.markdown.html` | `2989f7950c192dfe9e38e0cd29f966235209938470c7a2490d1d6afcb0a9740c` |
| `M ` | `docs/orionis.view.globals.app.html` | `f05481bc1f4f022fee13cec82f345044058c5803871dcfc9e1332e42787f851d` |
| `M ` | `docs/orionis.view.globals.asset.html` | `e0942464e23b11ca83b62f38f25cc1bc0bbb8441eb6a90188d9a10b00f6cbc8d` |
| `M ` | `docs/orionis.view.globals.auth.html` | `51b36280bdf58ff14ee0b5808af444053c3ef4c223463954bf0c85f0bd36cdba` |
| `M ` | `docs/orionis.view.globals.bcrypt.html` | `662570699b510ed7f22745d6a14a5de6f2785c4bfe60493f6426170e421a7c7c` |
| `M ` | `docs/orionis.view.globals.cache.html` | `fef89e8f2bd9c6d60a5379c7c115d7027e68c567173b5f7b45a20d5d4218888b` |
| `M ` | `docs/orionis.view.globals.collection.html` | `2fd0e7ab08feb99837e175300e784d46c072469530a655e2fffc780d0ee62b5a` |
| `M ` | `docs/orionis.view.globals.config.html` | `30f8c270abb10fcf943639970a5882f8e90f030d545ddfda0e58a15bc063bb35` |
| `M ` | `docs/orionis.view.globals.csrf.html` | `e0152a028d8e2d5a4b3610b2ca8812cd7da61cb42b2ce15d310408516f78350c` |
| `M ` | `docs/orionis.view.globals.datetime.html` | `b7fe020ad38b9b0c013ae55d137976c076c3b7940ea22e12f2aac99031965c97` |
| `M ` | `docs/orionis.view.globals.dump.html` | `db416769a19f2a907a5340b275b3a8f9d0889774d10f00917432d4c8967c96c7` |
| `M ` | `docs/orionis.view.globals.errors.ErrorBag.html` | `e2625f26ee3874e99c08c21a2d72cd20fd2eb44ce8b9c2318d0ab7d819e55f36` |
| `M ` | `docs/orionis.view.globals.errors.html` | `580d68591affaeb43a13761febac67c856ac0cfe1eec2111332942bc1566c101` |
| `M ` | `docs/orionis.view.globals.flash.html` | `068e05e5266298fe94925bf976e93b0f7e14e15baa9994c4772db85ce48972d1` |
| `M ` | `docs/orionis.view.globals.html` | `841954197dcf1ab9881f7d9e99aa15243e2ce549d8b2ea88497a79085988626e` |
| `M ` | `docs/orionis.view.globals.lang.html` | `cf8fce9a073b40d4964513d7e2e133b8f74fa1b63302b31e246dbaad5254760c` |
| `M ` | `docs/orionis.view.globals.old.html` | `1895d2e1e40ec6c28a2adeb9152e1c8c78b549c500e613a4982c89a47bc1bb10` |
| `M ` | `docs/orionis.view.globals.request.html` | `ad9816a8c8c00f063d7e0497f8fb8d55a64f49f28924b8e5acc1e65127ea5fa8` |
| `M ` | `docs/orionis.view.globals.route.html` | `585bc0b1c3e6b4eccfd3f5221b2665328b1143991dd0db5a98a225ab5e20fa38` |
| `M ` | `docs/orionis.view.globals.session.html` | `14d30c0eddf68671b22e817f17e01fea5041c6022dc0a6896d91e13f6bcee409` |
| `M ` | `docs/orionis.view.globals.stringable.html` | `60a99553154bb9d9324e429e335d040f9deb9df11780de621e1b5a2e76f22568` |
| `M ` | `docs/orionis.view.globals.url.html` | `bc38ce07849a46f1c869ee095224785fbd9bb38698867ea80bc48452fadda71e` |
| `M ` | `docs/orionis.view.globals.version.html` | `f11a565663798d0065a714f1419e9b9816b9a0b911d5ded5c784a88c2d50b44d` |
| `M ` | `docs/orionis.view.html` | `658ec8253c56cf8be209da2106d10df9c64527e60dcc06009e2edc9a940e3411` |
| `M ` | `docs/orionis.view.pending.PendingView.html` | `6037273b59d723ae7925cd1d25f8fa2431028a38e26de5e85352d7407fc14474` |
| `M ` | `docs/orionis.view.pending.html` | `389b5353ee58aec1cf39e55923f46542135e0a1c80a52e4712da58970652eb0e` |
| `M ` | `docs/orionis.view.provider.ViewServiceProvider.html` | `e6a32ae50dc2847a78be98aa26ab10576e9ade0a6223ea110b96a805566b1b84` |
| `M ` | `docs/orionis.view.provider.html` | `67186eaae16c110a4f1d49de9740ca3af8bded793635cf32211daf5843d50e20` |
| `M ` | `docs/searchindex.json` | `53734160bb9f1371d8b9967510dbb5a891773c5a264c67834880d8a55ea114ab` |
| `M ` | `docs/sitemap.xml` | `8e6d57f234d9cee364e621d7fbd353ff10fea5512c3d1a99cc6256acbf24b1d3` |
| `M ` | `docs/undoccedSummary.html` | `7e364c8e8bbd6251ece375a82adb42aa26735a0a38a13cc59717c110a557dced` |

</details>



## Addendum final — 13 de noviembre de 2026

Después del cierre local de la continuación 3, este informe queda actualizado antes de la comprobación final de integridad. La evidencia final que debe conservarse es `continuation-3-final-deduplicated-f1305f2a.json`, `sonar-probe-14bb809a.json`, `quality-all-6cbf8c16.json` y `docs-continuation-3-verify-c4dac5bb.json`; el snapshot nativo contiene 2357 rutas y Sonar verifica 1956 rutas. La única acción restante es ejecutar una vez el verificador de integridad de la continuación 3 sobre esas cuatro evidencias, incluyendo el hash final de este informe junto con el resto.

No se modificarán código ni validadores, ni se hará staging, commit, push o publicación remota. Los recursos propios restantes deben quedar reflejados por el verificador y limpiarse únicamente si pertenecen a esa validación.
