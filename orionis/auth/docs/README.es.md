# orionis.auth

> `orionis.auth` autentica solicitudes HTTP mediante sesiones o tokens de acceso personal y evalúa permisos, roles y policies dentro de un contexto aislado por solicitud.

## Descripción general

Este módulo proporciona la capa de identidad y autorización de Orionis. El código de aplicación normalmente usa la fachada `Auth`, añade `Authenticatable` y `Authorizable` a su modelo de identidad, declara subclases de `Policy` y protege rutas con middleware de `orionis.auth.middleware`.

El kernel HTTP resuelve el guard de sesión o de token y vincula un `AuthenticationContext` al scope actual del contenedor. El administrador de autenticación singleton y los middleware leen ese contexto, por lo que `Auth.user()`, las comprobaciones de permisos, las abilities de tokens y las policies se refieren siempre a la solicitud actual. Los servicios de soporte persisten permisos, roles, tokens personales, credenciales “remember me” y tokens de restablecimiento mediante el ORM.

## Requisitos

- Python 3.14 o posterior.
- Una instalación normal de Orionis; autenticación no tiene un extra de instalación opcional.
- La identidad configurada debe ser un modelo de Orionis que implemente `IAuthenticatable`; añade `Authorizable` cuando posea permisos, roles o tokens personales.
- El login por sesión requiere una solicitud HTTP activa con middleware de sesión. La persistencia de tokens y autorización requiere las migraciones de auth y una conexión de base de datos configurada.
- La verificación de contraseñas usa el hashing de Orionis. El login “remember me” requiere una columna `remember_token` en la identidad y su modo seguro requiere HTTPS.

## Inicio rápido

Dentro de una solicitud de una aplicación Orionis iniciada, la fachada expone la identidad resuelta y su autorización:

```python
from orionis.support.facades.auth import Auth


async def profile_summary() -> dict[str, object]:
    if Auth.guest():
        return {"authenticated": False}

    return {
        "authenticated": True,
        "identifier": Auth.identifier(),
        "can_edit": await Auth.can("profile.edit"),
    }
```

El kernel HTTP establece el contexto antes de ejecutar el controlador. `Auth.guest()` y `Auth.identifier()` son lecturas síncronas del contexto; las comprobaciones de autorización son asíncronas porque pueden cargar desde la base de datos un snapshot de permisos.

Validación: **Import-validated only** en CPython 3.14.6; la ejecución requiere una aplicación iniciada y un scope de solicitud activo.

## Conceptos principales

### Identidad, guard y contexto

Una identidad implementa `IAuthenticatable`. Un guard extrae credenciales de una solicitud y devuelve un `GuardResult`: el guard de sesión lee la clave de sesión configurada y el guard de token analiza un token Bearer. `ResolveIdentityMiddleware` convierte ese resultado en un `AuthenticationContext` almacenado en el scope actual del contenedor. Un contexto invitado no contiene identidad y usa un snapshot de autorización vacío.

### Autenticación frente a autorización

La autenticación determina quién hizo la solicitud. La autorización combina los permisos y roles persistidos de la identidad con un conjunto opcional de abilities del token. Las abilities solo pueden reducir el acceso:

```text
effective permission = identity permission AND (unrestricted token OR matching ability)
```

Un token restringido no puede usar middleware basado únicamente en roles, pues debe autorizar capacidades de forma explícita.

### Permisos, roles y policies

Los permisos nombran capacidades como `posts.update`; los roles agrupan permisos. Las policies vinculan una clase de recurso con métodos como `view`, `create` o `update`. `Policy.before(identity, ability)` puede devolver `True` o `False` para decidir antes de ejecutar una ability; el valor predeterminado `None` delega al método nombrado. Las clases policy se resuelven mediante el contenedor en cada evaluación, por lo que sus constructores pueden solicitar dependencias.

### Credenciales de sesión y token

El login por sesión guarda el identificador de identidad en la sesión de la solicitud actual. Los tokens personales constan de metadatos persistidos y un secreto devuelto únicamente al crearlos. El repositorio almacena un resumen, no el secreto plano; `NewAccessToken.toDict()` omite intencionalmente `plain_text`.

## Estructura del módulo

| Área | Responsabilidad |
|---|---|
| `manager.py`, `provider.py` | API de aplicación respaldada por fachada y registro en el contenedor. |
| `context/`, `guards/`, `identity/` | Estado de identidad por solicitud, resolución de credenciales de sesión/token y búsqueda del modelo. |
| `authorization/` | Snapshots de permisos/roles, repositorio de base de datos, registro de policies, autorizador y registrador. |
| `middleware/` | Resolución opcional de identidad y exigencia de autenticación, permiso, rol, policy o acceso de invitado. |
| `tokens/`, `entities/` | Generación, hashing, persistencia y metadatos de tokens, además del resultado de emisión censurado. |
| `passwords/`, `remember.py` | Ciclo de restablecimiento de contraseña y login persistente en navegador. |
| `concerns/`, `contracts/`, `exceptions.py` | Mixins de modelo, interfaces de extensión y jerarquía de excepciones. |

## API pública

### Fachada `Auth` y `AuthManager`

Usa `from orionis.support.facades.auth import Auth`. `AuthProvider` vincula `IAuthManager` como singleton y fija la fachada durante el inicio. Las operaciones principales son:

| Operación | Resultado |
|---|---|
| `context()` | `IAuthenticationContext` actual. |
| `user()`, `identifier()` | Identidad actual o su identificador; `None` para invitados. |
| `check()`, `guest()` | Comprobaciones síncronas del estado de autenticación. |
| `guard(name=None)` | Guard nombrado o predeterminado; lanza `GuardNotFoundException` si falta. |
| `attempt(credentials, remember=False)` | Verifica credenciales e inicia una sesión; devuelve `bool`. |
| `login(identity)`, `logout()` | Inicia o invalida autenticación por sesión en la solicitud activa. |
| `authorization()` | Snapshot inmutable de autorización. |
| `can`, `cannot`, `canAny`, `canAll`, `hasRole` | Consultas asíncronas de permisos y roles. |
| `authorize(permission)` | Exige un permiso; lanza excepciones orientadas a 401/403. |
| `allows`, `denies`, `authorizeResource` | Evalúa o exige una ability de policy. |
| `registerPolicy(resource, policy)` | Vincula una clase policy con un tipo de recurso. |
| `createToken(...)` | Emite un token personal para una identidad autorizable. |
| `revokeCurrentToken()` | Revoca la credencial usada por esta solicitud, si existe. |

`attempt`, `login` y `logout` siempre usan el guard de sesión y requieren una solicitud HTTP activa. `createToken` acepta `name`, los opcionales `tokenable`, `abilities` y `expires_at`; una solicitud autenticada por token no puede emitir otro token.

### `Authenticatable` y `Authorizable`

Importa estos mixins desde `orionis.auth`. `Authenticatable` obtiene el atributo identificador desde los metadatos del modelo ORM y lee el hash desde `AUTH_PASSWORD`, cuyo valor predeterminado es `"password"`. Sobrescribe la variable de clase si el modelo usa otra columna.

`Authorizable` proporciona el tipo polimórfico del propietario y el identificador usados en las tablas de permisos, roles y tokens. `AUTHORIZABLE_TYPE` utiliza por defecto la ruta completa de la clase y puede reemplazarse por un valor estable específico de la aplicación. Ambos mixins se registran como implementaciones virtuales de sus contratos para evitar un conflicto de metaclases con `Model`.

### `Policy`

Crea una subclase de `Policy`, implementa métodos de abilities y registra el par mediante `Auth.registerPolicy(Resource, ResourcePolicy)`. Los métodos reciben primero la identidad autenticada y después la instancia o clase del recurso; pueden ser síncronos o asíncronos. Sobrescribe `before` para una decisión global.

### `AuthorizationSnapshot`

```text
AuthorizationSnapshot(
    permissions: Iterable[str],
    roles: Iterable[str],
    abilities: Iterable[str] | None = None,
)
```

El snapshot conserva tres colecciones inmutables. `can(permission)` aplica la intersección de abilities del token y `hasRole(role)` comprueba directamente los roles. `abilities=None` significa que la credencial no reduce los permisos de la identidad; un iterable vacío no permite ninguno.

### Middleware de rutas

Importa los middleware desde `orionis.auth.middleware`:

- `ResolveSessionIdentityMiddleware` y `ResolveTokenIdentityMiddleware` establecen la identidad, pero admiten invitados.
- `AuthenticateMiddleware` usa el guard actual/predeterminado; sus subclases de sesión/token fijan uno.
- `GuestMiddleware` admite invitados y redirige navegadores autenticados a `auth.session.home`.
- `RequirePermissionMiddleware`, `RequireRoleMiddleware` y `RequirePolicyMiddleware` se configuran creando una subclase y asignando atributos de clase.

Las respuestas protegidas reciben `Cache-Control: no-store, private`. Los invitados de sesión pueden redirigirse a `auth.session.redirect_to`; clientes JSON/AJAX y rutas de token reciben en su lugar una excepción de autenticación.

### Tokens y tipos de soporte

`AccessToken` contiene metadatos inmutables y `NewAccessToken` los combina con la credencial `plain_text` disponible una sola vez. `AccessTokenRepository` expone `create`, `findByPlainText`, `touch`, `revoke`, `revokeAll` y `purgeExpired`. `generate_token_secret` y `hash_token_secret` son helpers públicos, aunque las aplicaciones normalmente emiten tokens mediante `Auth.createToken`.

### Contratos de extensión

Los contratos de `orionis.auth.contracts` cubren administrador, guards, proveedor de identidad, repositorios de permisos y tokens, policy, contexto, snapshots e identidades autenticables/autorizables. Sustituye un servicio vinculando tu implementación con su contrato en el contenedor antes de construir los servicios dependientes.

## Flujos de trabajo comunes

### Autenticar una sesión de navegador

Recibe las credenciales en un manejador HTTP y llama `await Auth.attempt(credentials, remember=...)`. Si tiene éxito, el guard rota la sesión, guarda el identificador, emite opcionalmente la credencial persistente y el administrador vuelve a vincular el contexto actual. Si falla, devuelve `False` sin autenticar la solicitud.

### Proteger una ruta

Usa `AuthenticateSessionMiddleware` o `AuthenticateTokenMiddleware` cuando baste cualquier identidad válida. Para una capacidad concreta, crea una subclase de `RequirePermissionMiddleware` y declara `permissions`; asigna `requires_all=False` para aceptar cualquiera. Declara el middleware como clase real para que la caché de rutas compiladas pueda referenciarlo.

### Autorizar un recurso cargado

Registra su policy una vez durante la preparación de la aplicación, carga el recurso en el controlador y llama `await Auth.authorizeResource("update", resource)`. Abilities de clase como `create` o `viewAny` pueden usar una subclase de `RequirePolicyMiddleware`.

### Emitir y revocar un token personal

Llama `await Auth.createToken(...)` desde una solicitud autenticada por sesión, muestra `plain_text` una vez y conserva solo metadatos en respuestas posteriores. Los clientes envían `Authorization: Bearer <plain_text>`. Una solicitud autenticada por token puede revocarse con `await Auth.revokeCurrentToken()`.

## Ejemplos

### Aplicar abilities de token a permisos

Este ejemplo ejecutable demuestra que las abilities reducen, pero nunca amplían, los permisos de la identidad:

```python
from orionis.auth import AuthorizationSnapshot


snapshot = AuthorizationSnapshot(
    permissions={"posts.read", "posts.update"},
    roles={"editor"},
    abilities={"posts.read"},
)

print(snapshot.can("posts.read"))    # True
print(snapshot.can("posts.update"))  # False
print(snapshot.hasRole("editor"))    # True
```

Validación: **Executed successfully** en CPython 3.14.6.

### Definir un modelo autenticable y una policy

El modelo proporciona los identificadores de autenticación y autorización; la policy acepta abilities sync y async:

```python
from orionis.auth import Authenticatable, Authorizable, Policy
from orionis.orm import Integer, Model, String


class User(Model, Authenticatable, Authorizable):
    id = Integer().primary().autoIncrement()
    email = String(255).unique()
    password = String(255)


class UserPolicy(Policy):
    async def update(self, identity: User, user: User) -> bool:
        return identity.getAuthIdentifier() == user.getAuthIdentifier()
```

Regístrala durante la preparación de la aplicación mediante `Auth.registerPolicy(User, UserPolicy)`.

Validación: **Import-validated only** en CPython 3.14.6; no se ejecutó ninguna operación de base de datos.

### Declarar middleware de permisos

Los requisitos del middleware viven en subclases en vez de argumentos del constructor:

```python
from orionis.auth.middleware import RequirePermissionMiddleware


class CanPublishPosts(RequirePermissionMiddleware):
    permissions = ("posts.create", "posts.publish")
    requires_all = True
```

Asocia `CanPublishPosts` a una ruta. Los invitados provocan `AuthenticationException`; las identidades autenticadas que no posean ambos permisos provocan `AuthorizationException`.

Validación: **Import-validated only** en CPython 3.14.6; ejecutar la ruta requiere el pipeline de solicitudes de una aplicación.

### Serializar metadatos sin filtrar el secreto

`NewAccessToken` excluye su credencial utilizable de `repr` y `toDict`:

```python
from orionis.auth import AccessToken, NewAccessToken


issued = NewAccessToken(
    access_token=AccessToken(
        id=1,
        tokenable_type="app.models.user.User",
        tokenable_id=7,
        name="automation",
    ),
    plain_text="1|example-secret",
)

print(issued.toDict()["access_token"]["name"])  # automation
print("example-secret" in repr(issued))          # False
```

La aplicación debe entregar `issued.plain_text` una sola vez a través de un canal protegido.

Validación: **Executed successfully** en CPython 3.14.6.

## Configuración

La aplicación bootstrap lee estas variables de entorno para construir la configuración `auth`:

| Configuración | Variable de entorno | Valor predeterminado del bootstrap |
|---|---|---|
| `auth.default` | `AUTH_GUARD` | `session` |
| `auth.identity.model` | `AUTH_MODEL` | `app.models.user.User` |
| `auth.identity.username` | `AUTH_USERNAME` | `email` |
| `auth.session.key` | `AUTH_SESSION_KEY` | `_auth_identifier` |
| `auth.session.redirect_to` | `AUTH_REDIRECT_TO` | `/login` |
| `auth.session.home` | `AUTH_HOME` | `/home` |
| `auth.tokens.table` | `AUTH_TOKEN_TABLE` | `personal_access_tokens` |
| `auth.tokens.expiration` | `AUTH_TOKEN_EXPIRATION` | `None` (sin expiración automática) |
| `auth.tokens.secret_bytes` | `AUTH_TOKEN_SECRET_BYTES` | `40` (permitido: 32–128) |
| `auth.passwords.expiration` | `AUTH_PASSWORD_RESET_EXPIRATION` | `60` minutos |
| `auth.passwords.throttle` | `AUTH_PASSWORD_RESET_THROTTLE` | `60` segundos |
| `auth.passwords.table` | `AUTH_PASSWORD_RESET_TABLE` | `password_reset_tokens` |
| `auth.remember.cookie` | `AUTH_REMEMBER_COOKIE` | `orionis_remember` |
| `auth.remember.lifetime` | `AUTH_REMEMBER_LIFETIME` | `43200` minutos |
| `auth.remember.secure` | `AUTH_REMEMBER_SECURE` | `True` |

El guard predeterminado solo acepta `session` o `token`. Las entidades de configuración validan nombres no vacíos, valores positivos de expiración/throttle y límites del secreto durante el inicio. El nombre de la cookie “remember me” debe ser distinto del nombre de cookie de sesión.

## Integración con Orionis

`AuthProvider` registra un `IAuthenticationContext` scoped; proveedor de identidad, repositorio de permisos, autorizador, repositorio de tokens y guards singleton; y el `IAuthManager` singleton. Después fija la fachada `Auth` de forma anticipada porque las operaciones síncronas de fachada deben poder llamarse inmediatamente.

El kernel HTTP instala el resolvedor de identidad apropiado para rutas web y API, y abre el scope del contenedor que aísla el estado de autenticación. El módulo se integra con almacenamiento ORM/base de datos, administrador de hashing, sesiones, cookies de respuesta, pipeline de middleware del router y manejador de excepciones. Las migraciones de auth crean las estructuras de permisos, roles, tokens personales y restablecimiento que usan los repositorios.

## Errores y casos límite

- `AuthException` es la base para fallos de configuración, autenticación, autorización, guard ausente, proveedor de identidad, policy ausente y token.
- Login/logout de sesión fuera de una solicitud HTTP activa lanza `AuthException`.
- `authorize` y `authorizeResource` lanzan `AuthenticationException` para invitados y `AuthorizationException` para solicitudes autenticadas denegadas.
- Un guard desconocido lanza `GuardNotFoundException` e incluye los nombres registrados.
- Requisitos de middleware vacíos lanzan `AuthConfigurationException`; una policy ausente provoca `PolicyNotFoundException`.
- La creación de tokens requiere un propietario `IAuthorizable`. Las solicitudes autenticadas por token no pueden emitir tokens personales anidados.
- Los secretos de token se validan, resumen y comparan mediante helpers de biblioteca de tiempo constante, y nunca pueden recuperarse de los metadatos. Credenciales inválidas, expiradas, revocadas, mal formadas o con propietario inactivo fallan de forma cerrada.
- Un token restringido solo puede conceder la intersección de permisos de identidad y abilities; no puede conceder permisos ausentes ni superar middleware de roles.
- Las credenciales “remember me” fallan de forma cerrada sobre HTTP con modo seguro, cookies mal formadas/expiradas, cambios de contraseña, identidades inactivas o rotación fallida.

## Rendimiento y concurrencia

El estado de autenticación se almacena en el scope de solicitud del contenedor, mientras administradores, guards, middleware y repositorios son singletons sin estado de solicitud. La vinculación del contexto aísla solicitudes concurrentes sin copiar servicios singleton.

Las mutaciones de autenticación usan un lock asíncrono asociado al contexto activo. Los snapshots de autorización se cargan de forma diferida y se almacenan en el contexto de la solicitud; sus datos `frozenset` son inmutables y pueden compartirse entre corrutinas de esa solicitud. La búsqueda de la clase policy se almacena, pero las instancias policy se resuelven nuevamente en el scope actual.

El hashing de contraseñas se ejecuta mediante el administrador de hashing fuera del hilo del event loop. Las escrituras de base de datos arbitran carreras de tokens personales, “remember me” y restablecimiento; el restablecimiento consume su token y actualiza condicionalmente la contraseña dentro de una transacción. Las credenciales persistentes rotan sin extender su fecha límite original.

## Compatibilidad

El proyecto declara Python 3.14+; la validación usó CPython 3.14.6 en Windows. La autenticación es independiente de la plataforma. Utiliza las dependencias declaradas por el framework para SQLAlchemy/base de datos asíncrona, hashing, HTTP, sesión y contenedor, y no tiene un extra opcional. Aun así, el backend de base de datos configurado puede requerir su extra de driver.

## Notas de verificación

Se inspeccionaron exportaciones, administrador, provider, contextos, guards, middleware, autorización, tokens, identidad, flujos “remember”/contraseña, configuración auth, migraciones, integraciones directas y `tests/auth`. Las 359 pruebas de auth pasaron mediante el ejecutor Orionis en CPython 3.14.6. Se ejecutaron los ejemplos de snapshot y censura; los ejemplos de fachada, modelo/policy y middleware se validaron por import porque su ejecución completa requiere estado de aplicación/solicitud o base de datos.
