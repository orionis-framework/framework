# orionis.session

> `orionis.session` implementa sesiones HTTP server-side perezosas, flash de una solicitud, rotación segura y storage memory, file, cache o database.

## Descripción general

La cookie del navegador lleva solo un identificador aleatorio. Los datos permanecen en un store server-side. `Session` posee valores y flags; `SessionManager` restaura, envejece flash, registra el contrato, persiste, rota IDs y escribe/elimina cookie.

Una sesión nueva es perezosa: leer no crea ID ni almacenamiento. La primera escritura o flash la activa, evitando cookies e I/O para requests sin estado.

## Requisitos

- Python 3.14 o posterior.
- Middleware web de sesión Orionis para inicio/guardado e inyección.
- Directorio escribible para `file`, cache configurado o conexión para `database`.
- HTTPS con `SESSION_SAME_SITE=none`; la configuración exige cookie segura.

## Inicio rápido

```python
from orionis.session.session import Session

session = Session()
assert session.id is None
assert session.started is False

session.put("user_id", 42)
assert session.started is True
assert session.dirty is True
assert session.id is not None
assert session.get("user_id") == 42
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; no se usó store.

## Conceptos principales

### Estado server-side perezoso

`Session` no hace I/O de request/response/cookie/store. `put()` activa en la primera escritura efectiva y no marca dirty si el valor es igual. `forget`, `clear`, `has`, `get` y `all` gestionan el mapping.

### Ciclo flash

`flash` se lee en la solicitud actual y siguiente. Al iniciar, manager descarta la bolsa vieja y promueve la nueva. `flashInput` elimina credenciales/CSRF, `flashErrors` normaliza y escrituras reservadas repetidas se fusionan.

### Rotación e invalidación

Llame `regenerate()` tras login/cambio de privilegio. La rotación espera al save para eliminar el registro viejo antes de persistir ID nuevo. `invalidate()` limpia, borra registro y expira cookie. Si otra solicitud revocó el registro, update/rotación falla cerrado.

### Expiración y renovación

Cada registro tiene expiración UTC. Con intervalo 0 se persiste cada request activo. Un intervalo positivo puede saltar writes de payload escalar sin cambios; datos mutables/dirty siempre se guardan.

### Stores

Memory es local. File usa JSON, replace atómico, locks y GC. Cache delega TTL y usa replace atómico. Database crea tabla portable perezosamente y usa updates condicionales.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `session.py` | Datos, flash, renovación, rotación e invalidación. |
| `manager.py` | Restauración, selección de store, persistencia y cookies. |
| `flash.py` | Filtrado, normalización y aplicación de flash. |
| `stores/memory.py` | Registros aislados en proceso. |
| `stores/file.py` | JSON atómico, locks entre procesos y GC. |
| `stores/cache.py` | Registros cache con TTL/replace. |
| `stores/database.py` | Tabla portable y updates condicionales. |
| `contracts/` | `ISession` e `ISessionStore`. |
| `entities/record.py`, `exceptions.py` | Registro y fallos de storage. |

## API pública

`orionis.session` no tiene exports raíz. El código de aplicación inyecta `ISession` o usa `orionis.support.facades.Session`. Infraestructura importa concretos de sus módulos.

### Datos de sesión

- `get`, `put`, `has`, `forget`, `clear`, `all`.
- `flash`/`getFlash` para datos de una solicitud.
- `flashInput`/`getOldInput` y `flashErrors`/`getErrors` para formularios.
- `setPreviousUrl`/`getPreviousUrl` para navegación.
- `regenerate`/`invalidate` para lifecycle de seguridad.
- Flags: `id`, `started`, `dirty`, `invalidated`, `isNew`, `wantsRegenerate`.

### Contrato de store

`ISessionStore` define `read`, `write`, `update`, `delete`, `gc` async. `update=False` si no reemplaza un registro vivo, evitando deshacer logout/revocación concurrente.

## Flujos de trabajo comunes

### Persistir login con seguridad

Tras validar credenciales, escriba identidad y llame `regenerate()`. No guarde passwords, tokens u objetos grandes.

### Redirigir con input/errores

Use helpers de response/view o `flashInput`/`flashErrors`. Campos tipo password se eliminan, pero secretos propios requieren exclusión explícita.

### Cerrar sesión

Llame `invalidate()` y devuelva por middleware normal. El manager borra storage y expira cookie. Si aborta, `abort()` borra IDs revocados/sustituidos sin emitir uno nuevo.

### Elegir store

Use memory solo si pérdida/no compartir son aceptables. File sirve filesystem local compartido; cache/database suelen servir multi-worker según garantías del backend.

## Ejemplos

### Flashear formulario sin credenciales

```python
from orionis.session.session import Session

session = Session()
session.flashInput({
    "email": "ada@example.test",
    "password": "must-not-persist",
    "csrf_token": "must-not-persist",
})
session.flashErrors({"email": "Already registered"})

assert session.getOldInput("email") == "ada@example.test"
assert session.getOldInput("password") is None
assert session.getErrors() == {"email": ["Already registered"]}
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Solicitar rotación

```python
from orionis.session.session import Session

session = Session()
session.put("account", 7)
old_id = session.id
session.regenerate()

assert session.wantsRegenerate is True
assert session.id == old_id
assert session.invalidated is False
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; la rotación real pertenece al save atómico del manager.

### Round-trip en memory store

```python
import asyncio
from datetime import UTC, datetime, timedelta
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.memory import MemorySessionStore


async def example() -> None:
    store = MemorySessionStore()
    record = SessionRecord(
        id="example", data={"count": 1},
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    await store.write(record)
    restored = await store.read("example")
    assert restored is not None and restored.data == {"count": 1}
    restored.data["count"] = 2
    assert (await store.read("example")).data["count"] == 1


asyncio.run(example())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; el store devuelve registros separados.

### Validar configuración de cookie/renovación

```python
from orionis.foundation.config.session import Session as SessionConfig

config = SessionConfig(
    driver="memory",
    lifetime=120,
    renewal_interval=300,
    cookie="sessionid",
    secure=True,
    same_site="none",
)
assert config.driver.value == "memory"
assert config.renewal_interval == 300
assert config.secure is True
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Usar fachada del request

```python
from orionis.support.facades import Session


def remember_theme(theme: str) -> None:
    Session.put("theme", theme)


def current_theme() -> str:
    return Session.get("theme", "system")
```

Validación: **Importación y sintaxis validadas** en CPython 3.14.6; requiere middleware y binding de request.

## Configuración

| Variable | Predeterminado | Propósito |
|---|---:|---|
| `SESSION_DRIVER` | `memory` | `memory`, `file`, `cache`, `database`. |
| `SESSION_LIFETIME` | 120 minutos | Vida server-side. |
| `SESSION_EXPIRE_ON_CLOSE` | false | Omite `Max-Age`. |
| `SESSION_TRACK_PREVIOUS_URL` | true | Recuerda navegación exitosa. |
| `SESSION_RENEWAL_INTERVAL` | 0 segundos | Intervalo mínimo sin cambios. |
| `SESSION_FILES` | `storage/framework/sessions` | Ruta file bajo app root. |
| `SESSION_DB_CONNECTION` / `SESSION_DB_TABLE` | default / `sessions` | Storage database. |
| `SESSION_CACHE_STORE` | cache default | Repositorio cache. |
| `SESSION_COOKIE`, `SESSION_PATH`, `SESSION_DOMAIN` | `sessionid`, `/`, host actual | Identidad/ámbito cookie. |
| `SESSION_SECURE`, `SESSION_HTTP_ONLY` | false, true | Transporte/script. |
| `SESSION_SAME_SITE`, `SESSION_PARTITIONED` | `lax`, false | SameSite y CHIPS. |

El intervalo debe ser no negativo y menor que lifetime en segundos. Nombres/rutas se validan. `SameSite=None` exige `secure=True`.

## Integración con Orionis

La capa web `StartSession` inicia, registra `ISession`, aplica flash pendiente y guarda tras éxito. En excepción/cancelación ejecuta abort cleanup.

La fachada resuelve el mismo contrato. Stores cache/database reutilizan managers; database crea schema dedicado. El middleware rastrea URL anterior solo para navegación elegible.

## Errores y casos límite

- Registros ausentes, inválidos, vencidos, discordantes o corruptos producen sesión nueva; IDs inválidos no llegan al store.
- Fallos I/O pueden producir `SessionStorageException` o errores backend.
- File requiere valores JSON-serializables; otros dependen de su serializer/backend.
- `all()` incluye bolsas internas; no lo exponga directamente.
- Writes iguales no hacen nada, pero valores mutables pueden cambiar; renovación los persiste conservadoramente.
- Memory no cruza procesos ni garantiza threads fuera del uso single-loop.
- Soporte cliente de Partitioned varía; la config solo emite atributo.

## Rendimiento y concurrencia

Activación lazy evita cookies/writes. Renovación reduce writes escalares. Cache usa TTL; file/database ofrecen GC.

File publica atómicamente con locks acotados. Cache/database requieren registro vivo en `update`, preservando revocación. `Session` es request-scoped y no debe compartirse.

## Compatibilidad

Cookies siguen la API Response y reglas de Secure/HttpOnly/SameSite/Partitioned. File usa JSON compacto; cambiar tipos puede afectar registros. Todos los stores intercambian `SessionRecord`, permitiendo implementaciones `ISessionStore` propias.

## Notas de verificación

- `tests/session`: **256 métodos de prueba aprobados** con el runner de Orionis en CPython 3.14.6.
- Se compilaron seis programas bilingües; cinco programas autónomos se ejecutaron correctamente.
- La fachada se validó por importación/sintaxis porque requiere middleware.
- La evidencia cubrió lazy, flash, renovación, rotación/revocación, cookies, abort, stores, locking, GC y configuración.

