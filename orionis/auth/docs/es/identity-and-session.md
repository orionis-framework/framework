# Identidades y autenticación de navegador

El modelo debe implementar `IAuthenticatable`. La combinación usual es `Model` con `Authenticatable`; añade `Authorizable` para permisos, roles o tokens. Los mixins evitan herencia directa de los contratos ABC, que entraría en conflicto con la metaclase del ORM.

```python
from orionis.auth import Authenticatable, Authorizable
from orionis.orm import Integer, Model, String

class User(Model, Authenticatable, Authorizable):
    id = Integer().primary().autoIncrement()
    email = String(255).unique()
    password = String(255)
```

Guárdalo en un módulo de aplicación y configura `AUTH_MODEL` con su path, por defecto `app.models.user.User`. `AUTH_USERNAME` es `email`. `Authenticatable` obtiene la clave de metadata ORM y lee el hash desde `AUTH_PASSWORD="password"`; sobrescribe esa variable de clase para otra columna. Guarda hashes mediante [hashing](../../../hashing/docs/es/README.md), nunca la contraseña de entrada.

## Login y logout

```python
from orionis.http import Request, response
from orionis.support.facades import Auth

async def login(request: Request):
    values = await request.data()
    credentials = {"email": values.get("email"), "password": values.get("password")}
    if not await Auth.attempt(credentials):
        return response.json({"message": "Invalid credentials"}, 401)
    return response.redirect("/home", 303)

async def logout():
    await Auth.logout()
    return response.redirect("/login", 303)
```

Estos handlers requieren rutas web con sesión y CSRF; valida primero el formato con un schema en la aplicación. `attempt` devuelve `False` si no autentica. En éxito el guard rota sesión, guarda identificador y el manager vuelve a enlazar el contexto actual. `login(identity)` admite una identidad verificada por otro flujo confiable; no comprueba una contraseña por sí mismo.

`attempt`, `login` y `logout` son asíncronos y usan siempre el guard de sesión, aunque el default sea otro. Fuera de una petición HTTP activa generan `AuthException`. Logout invalida el estado de sesión; borrar solo una variable no es equivalente.

## Leer y exigir identidad

`Auth.user()`, `identifier()`, `check()`, `guest()` y `context()` son síncronos. Los checks de permiso y carga de snapshot requieren `await`. El kernel usa `ResolveSessionIdentityMiddleware` en web y `ResolveTokenIdentityMiddleware` en API: permiten invitados. Añade `AuthenticateSessionMiddleware` o `AuthenticateTokenMiddleware` para exigir credenciales.

`AuthenticateMiddleware` usa el guard actual/default. Invitados JSON/AJAX y rutas token reciben fallo de autenticación; un navegador con sesión puede redirigirse a `AUTH_REDIRECT_TO` (`/login`). `GuestMiddleware` redirige usuarios autenticados a `AUTH_HOME` (`/home`). Las respuestas protegidas incluyen política de caché privada/no-store.

## Configuración y extensibilidad

`AUTH_GUARD` acepta `session` o `token`; `AUTH_SESSION_KEY` vale `_auth_identifier`. Un guard desconocido produce `GuardNotFoundException`. `AuthProvider` registra contexto scoped y servicios/guards compartidos; la facade se fija durante boot para admitir lecturas síncronas. No caches `Auth.user()` en un singleton.

Reemplaza `IIdentityProvider`, `IGuard`, `IAuthManager` o contratos de repositorio mediante bindings del contenedor antes de construir dependientes. La configuración no convierte un nombre nuevo de guard en registro automático. Continúa con [autorización](authorization.md).

Evidencia: [manager](../../manager.py), [identidades](../../identity/provider.py), [guard](../../guards/session_guard.py), [provider](../../provider.py), [config](../../../../config/auth.py). Pruebas: [sesión](../../../../tests/auth/test_identity_and_session.py), [manager](../../../../tests/auth/test_manager.py), [contexto](../../../../tests/auth/test_context.py), [middleware](../../../../tests/auth/test_middleware.py).
