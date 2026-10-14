# Estado de usuario y formularios con flash

Usa una sesión para preferencias pequeñas o estado temporal del navegador. Los datos no pertenecen al objeto request de una sola petición, pero tampoco son almacenamiento de dominio permanente. Evita contraseñas, secretos y objetos ORM completos.

## Acceder desde un handler

```python
from orionis.http import response
from orionis.session.contracts.session import ISession

async def choose_theme(session: ISession):
    session.put("theme", "dark")
    return response.redirect("/settings", 303).withFlash("notice", "Theme saved")
```

La inyección requiere un scope web activo. Como alternativa, `from orionis.support.facades import Session` accede al mismo contrato. `get`, `put`, `has`, `forget`, `clear` y `all` son síncronos: no añadas `await`. Las operaciones de store y manager sí son asíncronas.

```python
from orionis.session.session import Session

session = Session()
assert session.id is None and not session.started
assert session.get("theme", "system") == "system"
session.put("theme", "dark")
assert session.started and session.dirty
assert session.get("theme") == "dark"
```

Escribir un valor igual al existente no ensucia la sesión. Sin embargo, mutar una colección obtenida puede alterar datos sin llamar a `put`; la renovación considera conservadoramente esos payloads mutables. No expongas `all()` como respuesta pública: incluye bolsas internas.

## Patrón POST, redirect, GET

`flash(key, value)` deja datos disponibles en la petición actual y la siguiente. Al empezar otra petición, el manager descarta la bolsa vieja y promueve la nueva. No es una cola de mensajes ni persiste indefinidamente.

```python
from orionis.session.session import Session

session = Session()
session.flashInput({"email": "ada@example.test", "password": "secret", "_csrf": "secret"})
session.flashErrors({"email": "Already registered"})
assert session.getOldInput("email") == "ada@example.test"
assert session.getOldInput("password") is None
assert session.getErrors() == {"email": ["Already registered"]}
```

`flashInput` filtra nombres de credenciales y CSRF conocidos. Excluye por tu cuenta campos secretos específicos de tu aplicación. `flashErrors` acepta mappings o excepciones de validación; normaliza valores a listas de mensajes. Varias escrituras en las bolsas reservadas se combinan.

Las respuestas `withInput`, `withErrors` y `withFlash` encolan los mismos datos para que el middleware los aplique. No necesitas escribir dos veces. La sesión expone `setPreviousUrl`/`getPreviousUrl`; la capa web solo actualiza la navegación cuando la respuesta y petición son elegibles. Al construir un redirect-back utiliza comprobación de destino seguro del flujo HTTP, no cualquier `Referer` sin validar.

## Duración y pruebas

Un `Session()` aislado sirve para probar manipulación de valores, pero no demuestra persistencia entre peticiones: eso depende del manager, cookies y store. No compartas esa instancia entre solicitudes concurrentes. Lee [stores](stores-and-concurrency.md) y [seguridad](configuration-and-security.md).

Evidencia: [Session](../../session.py), [flash](../../flash.py), [middleware web](../../../http/layer/web/start_session.py). Pruebas: [datos](../../../../tests/session/test_session.py), [flash](../../../../tests/session/test_flash.py), [persistencia web](../../../../tests/http/layer/web/test_session_persistence.py).
