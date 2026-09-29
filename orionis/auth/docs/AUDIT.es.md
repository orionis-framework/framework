# Informe de auditoría y corrección de Auth

Fecha: 2026-09-14. Revisión iterativa del código y sus integraciones, con pruebas
de regresión ejecutadas tras cada bloque. Auth y varias integraciones ya eran
cambios locales al comenzar; se conservaron. No se creó commit ni rama, ni se
reinició o migró la base de datos configurada de la aplicación.

## Diagnóstico

La base era válida: autenticación separada de autorización, manager sin usuario
global, contratos propios, provider eager, tokens opacos con digest SHA-256,
snapshots locales y persistencia mediante el ORM/IR de Orionis. No era necesario
reemplazar todo el módulo. Sin embargo, las garantías documentadas de concurrencia
y seguridad excedían el comportamiento real de varias integraciones.

Los siguientes hallazgos se corrigieron. Las rutas apuntan a su implementación
actual; las pruebas preservan las regresiones de los comportamientos anteriores.

### CRITICAL

**C1. Pin global de Session por petición**
- Archivo/componente: [Session](../../support/facades/session.py) y
  [StartSessionMiddleware](../../http/layer/web/start_session.py).
- Problema y causa: `pin()` guardaba la sesión en un atributo de clase compartido.
  El camino de excepción tampoco garantizaba `unpin()`.
- Impacto: lectura o mutación de la sesión de otra petición concurrente.
- Corrección: `ScopedFacade` lee únicamente del scope activo, sin pin global.
- Breaking change: acceso fuera de un scope vivo falla; no devuelve un dispatcher.
- Evidencia: barrera con dos sesiones, salida excepcional y tareas heredadas.

**C2. Policies retenidas globalmente con dependencias de request**
- Archivo/componente: [Authorizer](../authorization/authorizer.py).
- Problema y causa: el singleton cacheaba instancias construidas mediante DI.
  Una policy podía conservar el contexto o Request de su primera ejecución.
- Impacto: autorización calculada con identidad o dependencias de otra petición.
- Corrección: solo se cachean clases; cada evaluación construye una policy nueva.
- Breaking change: no se conserva estado de instancia entre evaluaciones.
- Evidencia: policy con `IAuthenticationContext` inyectado en scopes concurrentes.

**C3. Cookie de sesión usada como ruta de archivo**
- Archivo/componente: [FileSessionStore](../../session/stores/file.py).
- Problema y causa: el ID se concatenaba con la ruta sin validación; la lectura
  de datos corruptos podía además borrar el archivo señalado.
- Impacto: acceso o borrado fuera del directorio de sesiones mediante traversal.
- Corrección: formato de ID restringido en store y filtro antes del lookup HTTP.
- Breaking change: se rechazan IDs con sintaxis de ruta o longitud excesiva.
- Evidencia: cookies con `../`, separadores Windows y sintaxis de unidad no hacen I/O.

**C4. Resurrección de sesiones después de logout**
- Archivo/componente: [SessionManager](../../session/manager.py), sus cuatro stores
  y [CacheRepository](../../cache/repository.py).
- Problema y causa: una request antigua guardaba su payload con upsert después
  de que otra eliminara el registro. Rotar también podía recrear la identidad.
- Impacto: logout o rotación dejaban de revocar efectivamente el ID anterior.
- Corrección: `update()` condicional, `delete()` con resultado, rotación solo si
  la eliminación del ID restaurado gana y `replace()` atómico en caché.
- Breaking change: contratos de stores de Session y repositorios de caché.
- Evidencia: escritura/rotación tardías, dos conexiones SQL y eliminación entre
  lectura y CAS. Los archivos usan locks del SO mediante `filelock`.

### HIGH

**H1. Restricciones PAT omitidas en otras vías de autorización**
- Archivo/componente: [Authorizer](../authorization/authorizer.py),
  [gates de roles](../middleware/authorize.py) y [AuthManager](../manager.py).
- Problema y causa: las policies no consultaban abilities; un gate solo de roles
  las ignoraba; `createToken()` podía emitir una credencial sin la restricción actual.
- Impacto: ampliar acceso mediante una policy, un rol o un nuevo PAT.
- Corrección: comprobar abilities antes del hook de policy, rechazar gates solo
  de roles para credenciales restringidas y prohibir emisión por Auth desde PAT.
- Breaking change: sí. El repositorio de emisión sigue siendo una API administrativa
  de confianza, no un endpoint autorizado automáticamente.
- Evidencia: abilities vacías, hook permisivo, propietario incorrecto y emisión
  de token desde un contexto restringido son rechazados.

**H2. Policies autorizaban resultados truthy y métodos internos**
- Archivo/componente: [Authorizer](../authorization/authorizer.py).
- Problema y causa: `bool(result)` aceptaba valores como una cadena de error y el
  nombre del método no distinguía abilities de atributos internos.
- Impacto: una policy defectuosa podía permitir acceso accidentalmente.
- Corrección: solo `True` autoriza; métodos privados y `before` no son abilities.
- Breaking change: sí, retornos no booleanos dejan de conceder acceso.

**H3. Metadatos corruptos de PAT se convertían en permisos sin restricción**
- Archivo/componente: [AccessTokenRepository](../tokens/repository.py).
- Problema y causa: errores de JSON o fecha retornaban `None`, igual que SQL NULL.
- Impacto: perder restricciones o expiración de un token.
- Corrección: solo NULL conserva esa semántica; datos malformados rechazan el PAT.
- Breaking change: sí, entradas malformadas se rechazan en lugar de coercionarse.
- Evidencia: JSON inválido, `null` textual, objetos, tipos mixtos y fechas inválidas.

**H4. Revocación durante resolución y propietario opcional**
- Archivo/componente: [TokenGuard](../guards/token_guard.py).
- Problema y causa: después del lookup había awaits de identidad y un `touch()`
  incondicional; el tipo de propietario se verificaba solo si exponía el método.
- Impacto: publicar una credencial ya revocada o de una clase de identidad ajena.
- Corrección: validar tipo e ID y exigir éxito del UPDATE final condicionado.
- Breaking change: `touch()` devuelve bool; proveedores deben identificar al dueño.
- Evidencia: revocación pausada dentro del lookup y respuesta con ID incorrecto.

**H5. Scopes y referencias Auth sobrevivían al final de la request**
- Archivo/componente: [ScopeManager](../../container/context/manager.py) y
  [AuthenticationContext](../context/context.py).
- Problema y causa: una tarea hija heredaba el scope y podía repoblarlo tras salir;
  referencias al contexto antiguo seguían autorizando después de logout.
- Impacto: identidad disponible fuera del lifetime correcto o después de reemplazo.
- Corrección: scopes de un solo uso y cerrados para publicación; contexto verifica
  scope activo, scope llamador y que siga siendo el binding actual.
- Breaking change: no se puede reabrir un scope ni reutilizar un contexto entre scopes.
- Evidencia: regresión inicial falló, después pasó; pruebas de cierre y DI tardía.

**H6. Logout no persistía si el controlador fallaba**
- Archivo/componente: [StartSessionMiddleware](../../http/layer/web/start_session.py).
- Problema y causa: `call_next()` podía abandonar el middleware antes de guardar.
- Impacto: el cliente podía seguir reutilizando una sesión que intentó cerrar.
- Corrección: `ICatch` convierte errores dentro del middleware; `abort()` persiste
  la revocación pendiente cuando una cancelación impide responder.
- Breaking change: constructor del middleware recibe `ICatch`.
- Evidencia: logout seguido de excepción o cancelación elimina el registro.

**H7. Errores de grants ocultos y transacciones abortadas**
- Archivo/componente: [PermissionRegistrar](../authorization/registrar.py).
- Problema y causa: se absorbía cualquier `QueryException` como si fuera duplicado;
  recuperar un INSERT fallido dentro de una transacción podía dejarla inutilizable.
- Impacto: reportar éxito sin aplicar grants o abortar operaciones relacionadas.
- Corrección: transacción/savepoint local y comprobación del duplicado antes de
  absorberlo; otros fallos se propagan.
- Breaking change: fallos reales antes ocultos ahora son visibles.
- Evidencia: tabla inexistente, duplicado dentro de transacción externa y rollback.

**H8. Namespace guard_name aparente, no aplicado**
- Archivo/componente: registrar, repositorio y migraciones de roles/permisos.
- Problema y causa: el esquema y API permitían namespaces, pero se buscaba por nombre
  y el snapshot combinaba resultados sin esa separación.
- Impacto: autorización incoherente si la aplicación confiaba en esos namespaces.
- Corrección: eliminar el concepto no soportado y hacer único el nombre canónico.
- Breaking change: retirar columna y argumento `guard_name`, conciliando datos previos.

**H9. IDs generados dependían de la caché DDL del proceso**
- Archivo/componente: repositorios PAT y registrar.
- Problema y causa: un INSERT schemaless podía devolver ID nulo, a diferencia de
  tests que acababan de crear la tabla con metadata en el mismo compilador.
- Impacto: grants fallidos y credenciales recién emitidas no revocables por su ID.
- Corrección: recuperar el ID por digest o nombre único cuando el driver lo omite.
- Breaking change: no; añade un SELECT únicamente en ese caso.
- Evidencia: pruebas con compilador frío para PAT y RBAC.

**H10. Identidades UUID incompatibles con propietarios BIGINT**
- Archivo/componente: migraciones, claves de autorización y proveedor de identidad.
- Problema y causa: abstracción genérica de identidad sobre columnas de propietario
  exclusivamente numéricas; drivers estrictos necesitan el tipo nativo al consultar.
- Impacto: fallos de login/token/grants con modelos que no usan claves enteras.
- Corrección: propietarios textuales canónicos y conversión por metadata a int/UUID.
- Breaking change: tipo de columnas y valores de metadatos de propietario.
- Evidencia: modelo `Member` UUID real, password accessor propio, sesión, PAT y RBAC.

**H11. Exposición accidental de credenciales en salida**
- Archivo/componente: entidades PAT, registro web y conexión SQL.
- Problema y causa: `toDict()` incluía el PAT; el registro mostraba `str(exception)`;
  errores SQL incluían valores enlazados o detalle del driver.
- Impacto: credenciales o hashes en logs, páginas de error o serializaciones genéricas.
- Corrección: PAT redactado en `toDict()`, errores gestionados por infraestructura
  y QueryException pública sin valores ni cadena del driver.
- Breaking change: sí, serialización PAT y detalle de QueryException.
- Evidencia: inspección de repr, diccionario y traceback formateado con valor centinela.

**H12. Demo web sin autenticación y contraseña alterada al registrarse**
- Archivo/componente: controladores de login y registro de la aplicación.
- Problema y causa: login solo confirmaba recepción; registro aplicaba `strip()`
  al secreto antes del hashing.
- Impacto: falsa impresión de login y contraseñas distintas de las introducidas.
- Corrección: login/logout reales, invitados en formularios y contraseña intacta.
- Breaking change: cambia el comportamiento del ejemplo, no una API de Auth.
- Evidencia: controlador con credenciales válidas e inválidas contra el stack real.

### MEDIUM

**M1. Hashing bloqueante en el event loop**
- Archivo/componente: SessionGuard y registro web.
- Causa/impacto: verificación costosa síncrona detenía otras requests del worker.
- Corrección: `Hash.make()`/`Hash.check()` son corrutinas que queman su coste con
  `asyncio.to_thread`, sin duplicar la API ni configuración de Hashing.
- Breaking change: ambas operaciones deben awaitarse en todo el código llamante.
- Evidencia: thread ID del verificador distinto del event loop.

**M2. Snapshot con varias consultas y lista intermedia de roles**
- Archivo/componente: [DatabasePermissionRepository](../authorization/repository.py).
- Causa/impacto: hasta tres SELECT y posibilidad de mezclar lecturas entre awaits.
- Corrección: un UNION SELECT. Se corrigió el compilador para tres ramas y operadores
  mixtos en SQLite. Se añadió índice inverso por rol en el pivote.
- Breaking change: no API; migrar el índice en bases existentes.
- Evidencia: 12 solicitudes concurrentes del snapshot producen exactamente un SELECT.

**M3. Integración DI y configuración incompleta**
- Archivo/componente: AuthProvider, AuthenticationContext y config Auth.
- Causa/impacto: sin binding scoped para invitados; anotaciones del constructor no
  evaluables por DI; configuración password duplicaba y contradecía el accessor.
- Corrección: binding SCOPED, tipos runtime y una única clave de entrada `password`.
- Breaking change: retirar `auth.identity.password`; usar `getAuthPassword()`.

**M4. Persistencia de Session inconsistente**
- Archivo/componente: SessionManager y stores memoria/caché/SQL.
- Causa/impacto: payload anidado compartido en memoria, fechas ISO sin convertir,
  prefijos SQL omitidos y cookie renovada sin renovar el vencimiento del servidor.
- Corrección: copias independientes, fechas validadas, planes IR y renovación conjunta.
- Breaking change: cada sesión activada renueva mediante escritura condicional.

**M5. CSRF no rotaba realmente al iniciar sesión**
- Archivo/componente: SessionGuard y CSRFTokenMiddleware.
- Causa/impacto: marcar regeneración del ID no cambiaba el CSRF ya guardado.
- Corrección: renovar CSRF con configuración HTTP y actualizar/eliminar cookie XSRF.
- Breaking change: el CSRF previo al login deja de ser válido.

### LOW

**L1. Semánticas HTTP incompletas**
- Archivo/componente: middleware y BaseExceptionHandler.
- Causa/impacto: rutas token podían redirigir al login; subclases Auth caían en 500.
- Corrección: 401 con desafío Bearer para token, 403 para autorización, mapping por MRO.
- Request acepta el esquema Bearer sin distinguir mayúsculas y rechaza cabeceras
  Authorization duplicadas, en lugar de elegir silenciosamente la última.
- Breaking change: respuestas antes incorrectas cambian a estados adecuados.

**L2. Documentación y entidades desalineadas**
- Archivo/componente: manuales, `.pyi`, entidades PAT y configuración Auth.
- Causa/impacto: promesas de aislamiento/timing/cache que el código no garantizaba;
  entidades con `__dict__` heredado y anotaciones diferidas innecesarias en Auth.
- Corrección: entidades slotted, anotaciones nativas, manuales bilingües y stub preciso.
- Breaking change: solo los cambios de contrato enumerados, sin aliases de compatibilidad.

## Architecture

Web: scope HTTP -> Session -> CSRF -> guard -> contexto -> autorización -> controlador
-> respuesta/persistencia -> transporte -> cleanup. API usa TokenGuard sin Session.
La identidad pertenece a la aplicación; Auth no administra una tabla global User.
Autenticación resuelve identidad. Autorización combina permisos directos, roles
y policies contextuales. Las abilities restringen, nunca conceden por sí solas.

## Changes

Auth: contexto, helpers, guards, proveedor, manager, authorizer, registrar, repositorios,
entidades, contratos, middleware y configuración. Integraciones: scopes/fachadas del
contenedor, Session y Cache, CSRF, handler de errores, SQL/UNION y controladores web.
Se actualizaron tests locales y se añadió una suite de integración HTTP.
Los manuales de Auth, Session, Cache y Container reflejan los contratos actuales;
HTTP, Database y Failure cuentan con referencias de integración bilingües.

## Removed

- Caché global de instancias de policy y helper `__policyInstance`.
- Pins de Session desde el middleware por cada request.
- `guard_name` y `DEFAULT_GUARD_NAME`, sin namespace de reemplazo redundante.
- `auth.identity.password`, sustituido por el accessor ya existente.
- Dependencia de BaseEntity en las entidades PAT para evitar exposición y `__dict__`.
- Confirmación ficticia de login y exposición directa de errores del registro.

## Database

Roles/permisos únicos por nombre; tres pivotes con PK compuestas; propietarios
VARCHAR(255); índice de permisos por rol; digest PAT único; índices de propietario,
expiración y revocación. Se mantienen FK restrictivas, no cascadas implícitas.
Se probaron seis migraciones reales, idempotencia y rollback en SQLite temporal.
No se aplicaron cambios a tablas existentes de la aplicación.

## HTTP

ASGI y RSGI comparten la misma resolución, autorización y cleanup. Contexto y sesión
permanecen disponibles durante el envío; después no pueden recuperarse desde la
fachada por una tarea heredada. Excepciones y early returns conservan cleanup;
logout persiste incluso ante excepción o cancelación.

## Middleware

Resolver identidad es opt-in para páginas públicas. Authenticate exige identidad;
sus variantes fijan sesión o PAT. Guest protege formularios de entrada. Permission
exige capacidades, Role es solo para credenciales no restringidas, Policy protege
una clase de recurso; recursos concretos se autorizan en el controlador.

## DI

SINGLETON: manager, guards, proveedor, authorizer, repositorios y registrar, sin
identidad actual. SCOPED: contexto y locks; Session se vincula al scope. Policies:
instancia nueva por evaluación. La fachada Auth pinea solo el manager stateless.

## Security

Se revisaron fijación/invalidación de sesión, traversal de cookies, hashing,
filtración de credenciales, metadatos corruptos, revocación y propietario PAT,
escalada por abilities, policies y roles, CSRF y estados HTTP. No se introdujeron
JWT, OAuth, MFA, reset de contraseña, verificación de correo ni autenticación WS.

## Concurrency

Scopes independientes por request; locks locales para transiciones y snapshot;
instancias de policy no compartidas; revocación decide en el almacenamiento.
SQLite de archivo evita resultados engañosos de StaticPool en `:memory:`.
Se usan eventos/barreras para interleavings, no solo tareas sin suspensión real.

## Performance

Sesión: un SELECT de identidad, más I/O del store. PAT: lookup por digest, lookup
de identidad y UPDATE de uso: tres sentencias. Primer RBAC: un SELECT UNION;
siguientes checks: cero SQL. Policy: construcción DI más su lógica, sin SQL RBAC
obligatorio. Emisión con compilador frío puede añadir lookup del ID generado.
No hay caché global de permisos ni reflexión de Auth por cada check simple.

## Tests

| Suite | Aprobadas |
|---|---:|
| Auth | 274/274 |
| Container | 231/231 |
| HTTP | 493/493 |
| Session | 247/247 |
| Cache | 201/201 |
| Database | 182/182 |
| ORM | 247/247 |
| Failure | 89/89 |
| View | 204/204 |
| Foundation | 30/30 |
| Hashing | 176/176 |
| Encrypter | 61/61 |
| Total de las suites afectadas | 2435/2435 |

Ejecutadas con el venv del repositorio y `reactor test`; no se afirma ejecución
de toda la suite del framework ni cobertura de líneas del 100%.
Ruff ALL pasa sobre fuente y tests modificados. Se consultaron diagnósticos del
editor y se solicitó Sonar sobre las rutas críticas modificadas.

## Remaining Risks

- Bases existentes necesitan una migración de datos revisada, especialmente si
  hay nombres duplicados bajo `guard_name`. Respaldar antes de transformar claves.
- No se ejecutaron PostgreSQL/MySQL/Oracle/SQL Server ni Redis/Memcached vivos.
  No se certificaron workers OS separados ni sistemas de archivos de red.
- Revocar no cancela decisiones ya autorizadas. Operaciones sensibles deben
  revalidar dentro de su frontera transaccional; el snapshot es por contexto.
- Cambios concurrentes del payload de sesión son last-writer-wins, no merge.
  Redis/Memcached pueden rechazar un CAS concurrente sin sobrescribirlo.
- Las aplicaciones deben aplicar HTTPS, Secure/HttpOnly, rate limiting, límites
  de concurrencia operativos y reglas de suspensión/elegibilidad de identidad.
- Los propietarios polimórficos requieren limpieza al borrarse y claves no
  reutilizables. `Auth.attempt()` solo acepta identidades con `active is True`.
- Encrypter no participa en la seguridad de los PAT ni del ID de sesión: Auth
  usa secretos opacos, no payloads cifrados. Su suite no equivale a una certificación
  criptográfica de todos los usos posibles de Crypt.
- La caché compilada de bootstrap debe invalidarse al desplegar cambios de
  contratos/proveedores/configuración. Las carpetas docs pueden estar ignoradas
  por Git y deben incluirse expresamente al versionar esta revisión.

## Breaking Changes

Retirar `auth.identity.password` y `guard_name`; migrar columnas de propietario a
texto e índices nuevos. Custom Session stores implementan `update() -> bool` y
`delete() -> bool`; custom cache repositories implementan `replace() -> bool`.
`IAccessTokenRepository.touch()` devuelve bool. `NewAccessToken.toDict()` no expone
`plain_text`. Policies no conservan instancias y requieren True explícito.
Tokens restringidos no usan gates solo de rol ni saltan restricciones de policies.
Auth no emite PAT desde otra petición PAT. `revokeCurrentToken()` deja el contexto
invitado. Scopes no se reabren; la fachada Session exige un scope activo.
QueryException deja de exponer SQL/valores del driver. Login del ejemplo ahora
autentica; logout es POST protegido por CSRF y middleware de sesión.
