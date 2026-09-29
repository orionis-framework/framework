# Autenticación y autorización

`orionis/auth/` responde dos preguntas distintas y las mantiene separadas
a propósito:

| Pregunta | Capa | Punto de entrada |
|---|---|---|
| ¿Quién es este usuario? | Autenticación | `Guard` → `AuthenticationContext` |
| ¿Qué puede hacer este usuario? | Autorización | `Authorizer` → `AuthorizationSnapshot` |

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja](#dónde-encaja)
  - [Pipeline de la petición](#pipeline-de-la-petición)
  - [Mapa de archivos](#mapa-de-archivos)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [Configuración](#configuración)
  - [Mixins de identidad](#mixins-de-identidad)
  - [Proveedor de identidad](#proveedor-de-identidad)
  - [Guards](#guards)
  - [Contexto de autenticación](#contexto-de-autenticación)
  - [Snapshot de autorización](#snapshot-de-autorización)
  - [Authorizer y policies](#authorizer-y-policies)
  - [Registrar de permisos](#registrar-de-permisos)
  - [Personal access tokens](#personal-access-tokens)
  - [Fachada Auth](#fachada-auth)
  - [Middleware](#middleware)
  - [Excepciones y estados HTTP](#excepciones-y-estados-http)
  - [Service provider](#service-provider)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Preparar el modelo de identidad](#preparar-el-modelo-de-identidad)
  - [Login y logout web](#login-y-logout-web)
  - [Proteger rutas](#proteger-rutas)
  - [Emitir y usar un token de API](#emitir-y-usar-un-token-de-api)
  - [Declarar una policy](#declarar-una-policy)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Compatibilidad](#compatibilidad)
- [Límites de seguridad](#límites-de-seguridad)
- [Fuera del alcance de esta versión](#fuera-del-alcance-de-esta-versión)

## Descripción funcional

### Dónde encaja

El módulo se sitúa entre el kernel HTTP y tus controladores. Reutiliza
las piezas que el framework ya posee en vez de duplicarlas:

| Responsabilidad | Dueño |
|---|---|
| Hashing de contraseñas | `orionis/hashing/` (`IHashManager`) |
| Sesión y cookies | `orionis/session/` |
| Consultas y migraciones | `orionis/orm/`, `orionis/database/` |
| Scope de petición | `Container.beginScope()` (`contextvars`) |
| Respuestas de error | `orionis/failure/` y `orionis/http/` |

### Pipeline de la petición

Para una petición web:

```text
Request → SessionGuard → Session → Identity → AuthenticationContext → Controller
```

Para una petición de API:

```text
Request → TokenGuard → PersonalAccessToken → Identity → AuthenticationContext → Controller
```

El resto del framework trabaja con la identidad autenticada sin saber qué
guard la produjo.

### Mapa de archivos

```text
orionis/auth/
├── contracts/          Interfaces de las que depende cada pieza
├── concerns/           Mixins que se añaden al modelo de identidad
├── context/            Estado autenticado de la petición
├── guards/             SessionGuard, TokenGuard
├── identity/           ModelIdentityProvider
├── authorization/      Snapshot, authorizer, policies, registrar, repositorio
├── tokens/             Generación, hashing y persistencia del secreto
├── middleware/         Guardas de ruta de autenticación y autorización
├── entities/           GuardResult, AccessToken, NewAccessToken
├── manager.py          AuthManager, respaldo de la fachada Auth
├── provider.py         AuthProvider, registrado en CORE_PROVIDERS
└── exceptions.py       AuthException y sus subclases
```

### Decisiones de diseño

- **La identidad autenticada nunca vive en un singleton.** Vive en el
  scope de contenedor que el kernel HTTP abre por petición, respaldado
  por `contextvars`. Dos peticiones concurrentes jamás se ven entre sí.
- **Sin acoplamiento a una clase llamada `User`.** El modelo de identidad
  viaja como ruta con puntos en `config/auth.py` y se resuelve perezosamente.
- **Tokens opacos, no JWT.** Solo se guarda un digest SHA-256 del secreto
  y una actualización condicional rechaza revocaciones confirmadas antes de
  publicar la identidad. No se cancelan peticiones ya autorizadas en curso.
- **Las abilities intersectan, nunca elevan.** La autorización efectiva es
  `permisos de la identidad ∩ abilities del token`.
- **Los mixins son clases planas.** Se registran como subclases virtuales
  de sus contratos, porque heredar de un `ABC` chocaría con `ModelMeta`,
  la metaclase de todo modelo de Orionis.

## Referencia de API

### Configuración

`config/auth.py` extiende la entidad `Auth` del framework.

```python
@dataclass(frozen=True, kw_only=True)
class Auth(BaseEntity):
    default: Guards | str
    identity: Identity | dict
    session: SessionAuth | dict
    tokens: Tokens | dict
```

| Clave | Significado | Valor por defecto |
|---|---|---|
| `auth.default` | Guard usado cuando no se nombra ninguno | `session` |
| `auth.identity.model` | Ruta con puntos del modelo de identidad | `app.models.user.User` |
| `auth.identity.username` | Atributo con el que se busca la identidad | `email` |
| `auth.session.key` | Clave de sesión con el identificador | `_auth_identifier` |
| `auth.session.redirect_to` | Página a la que se envía a los invitados | `None` |
| `auth.tokens.table` | Tabla que almacena los tokens | `personal_access_tokens` |
| `auth.tokens.expiration` | Vigencia por defecto en minutos | `None` |
| `auth.tokens.secret_bytes` | Bytes aleatorios del secreto | `40` |

No se duplica nada de `config/session.py` ni de `config/hashing.py`.
Las credenciales enviadas usan siempre `password`. `getAuthPassword()` selecciona
el hash almacenado; el mixin lee `AUTH_PASSWORD`, que puede nombrar otra columna.

### Mixins de identidad

```python
class Authenticatable:
    AUTH_PASSWORD: ClassVar[str] = "password"

    def getAuthIdentifierName(self) -> str: ...
    def getAuthIdentifier(self) -> object: ...
    def getAuthPassword(self) -> str: ...

class Authorizable:
    AUTHORIZABLE_TYPE: ClassVar[str | None] = None

    def getAuthorizableType(self) -> str: ...
    def getAuthorizableId(self) -> object: ...
```

`getAuthIdentifierName()` lee la clave primaria de los metadatos del
modelo, así que una clave UUID funciona sin configuración adicional.

### Proveedor de identidad

```python
class IIdentityProvider(ABC):
    async def retrieveById(self, identifier: object) -> IAuthenticatable | None: ...
    async def retrieveByCredentials(self, credentials: Mapping[str, object]) -> IAuthenticatable | None: ...
    async def validateCredentials(self, identity: IAuthenticatable | None, credentials: Mapping[str, object]) -> bool: ...
```

`ModelIdentityProvider` lo implementa sobre el ORM de Orionis.
Restaura claves enteras, de texto y UUID mediante los metadatos del modelo y
respeta scopes globales y soft deletes. Las identidades desconocidas hacen trabajo
de hashing para reducir señales de enumeración, sin prometer igualdad exacta
entre algoritmos o costes históricos. El módulo de hashing ejecuta el coste en
un hilo de trabajo, así que la verificación nunca bloquea el event loop.

### Guards

```python
class IGuard(ABC):
    @property
    def name(self) -> str: ...
    async def resolve(self, request: Request) -> GuardResult | None: ...

class ISessionGuard(IGuard):
    async def attempt(self, request: Request, credentials: Mapping[str, object], *, remember: bool = False) -> IAuthenticatable | None: ...
    def login(self, request: Request, identity: IAuthenticatable) -> None: ...
    async def logout(self, request: Request) -> None: ...
```

`SessionGuard.login()` exige una identidad con clave persistida, solicita rotar
el ID de sesión y renueva inmediatamente CSRF con la configuración HTTP existente.
La clave de identidad se guarda como texto canónico. `await logout()` revoca el
acceso persistente e invalida la sesión. `await Auth.attempt(credentials,
remember=True)` conserva el acceso mediante una cookie independiente y revocable;
consulta [Recordarme](REMEMBER_ME.es.md) para configuración y límites.
Persistencia, borrado del ID anterior y cookies corresponden a
`StartSessionMiddleware` y `SessionManager`; Auth no crea sesiones paralelas.

`TokenGuard` lee `Authorization: Bearer <token>`, rechaza por igual los
tokens desconocidos, revocados y expirados, y actualiza `last_used_at`
con una sola sentencia.
Valida tipo e identificador del propietario y condiciona ese UPDATE a que el
token siga vigente y no revocado. Fechas o abilities no nulas corruptas rechazan
la credencial, en vez de convertirla en un token sin restricciones.
El esquema Bearer no distingue mayúsculas. Cabeceras Authorization duplicadas
se rechazan.

### Contexto de autenticación

```python
class IAuthenticationContext(ABC):
    @property
    def identity(self) -> IAuthenticatable | None: ...
    @property
    def guard(self) -> str | None: ...
    @property
    def abilities(self) -> frozenset[str] | None: ...
    @property
    def credentialId(self) -> object | None: ...
    @property
    def isAuthenticated(self) -> bool: ...
    @property
    def isGuest(self) -> bool: ...
    def identifier(self) -> object | None: ...
    async def authorization(self) -> IAuthorizationSnapshot: ...
```

Dos funciones de módulo mueven el contexto dentro y fuera del scope:

```python
def current_auth_context() -> IAuthenticationContext: ...
def bind_auth_context(context: IAuthenticationContext) -> None: ...
```

Fuera de una petición, `current_auth_context()` devuelve el
`GUEST_CONTEXT` compartido y `bind_auth_context()` lanza `AuthException`.
`AuthProvider` registra además `IAuthenticationContext` como `SCOPED`: la DI puede
inyectar un contexto invitado antes de resolver identidad. Autenticar publica un
contexto nuevo. Las referencias vinculadas quedan como invitado tras reemplazo,
cierre del scope o acceso desde otro scope. No deben retenerse en singletons.

Un lock por petición serializa resolución, login, logout y revocación del token
actual. Repetir un guard reutiliza su contexto, incluidos invitados; otro guard
no puede sustituir silenciosamente una identidad autenticada. Las tareas que
sobreviven a la petición deben abrir un scope nuevo.

### Snapshot de autorización

```python
class AuthorizationSnapshot(IAuthorizationSnapshot):
    def __init__(self, permissions, roles, abilities=None) -> None: ...

    @property
    def permissions(self) -> frozenset[str]: ...
    @property
    def roles(self) -> frozenset[str]: ...
    @property
    def abilities(self) -> frozenset[str] | None: ...
    def can(self, permission: str) -> bool: ...
    def hasRole(self, role: str) -> bool: ...
```

El snapshot se resuelve como mucho una vez por petición, bajo un lock que
pertenece al contexto, y responde a todas las comprobaciones posteriores
sin volver a la base de datos.

### Authorizer y policies

```python
class IAuthorizer(ABC):
    async def can(self, context, permission: str) -> bool: ...
    async def canAny(self, context, permissions: Iterable[str]) -> bool: ...
    async def canAll(self, context, permissions: Iterable[str]) -> bool: ...
    async def hasRole(self, context, role: str) -> bool: ...
    async def allows(self, context, ability: str, resource: object) -> bool: ...
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None: ...
```

Una policy declara un método por ability, más un hook `before` opcional:

```python
class Policy(IPolicy):
    async def before(self, identity: object, ability: str) -> bool | None: ...
```

Las búsquedas de clases de policy siguen el MRO y se cachean. Las instancias se
construyen por DI en cada evaluación, nunca se cachean globalmente, por lo que
las dependencias de petición permanecen aisladas. Un token restringido debe
incluir el nombre exacto del método de policy en sus abilities antes del hook,
y la policy también debe permitir la operación. Solo `True` autoriza. Los métodos
privados y `before` no son abilities públicas. Una policy o método ausente lanza
`PolicyNotFoundException`.

### Registrar de permisos

```python
class PermissionRegistrar:
    async def createPermission(self, name: str) -> object: ...
    async def createRole(self, name: str) -> object: ...
    async def givePermissionTo(self, authorizable, *permissions: str) -> None: ...
    async def revokePermissionFrom(self, authorizable, *permissions: str) -> None: ...
    async def assignRole(self, authorizable, *roles: str) -> None: ...
    async def removeRole(self, authorizable, *roles: str) -> None: ...
    async def grantToRole(self, role: str, *permissions: str) -> None: ...
    async def revokeFromRole(self, role: str, *permissions: str) -> None: ...
```

Los nombres tienen un único namespace: únicos, no vacíos, sin espacios laterales,
de hasta 255 caracteres. Las claves compuestas de pivotes hacen idempotente la
asignación. Los conflictos de INSERT se aíslan con transacción o savepoint y solo
se absorben si existe la misma fila; otros errores SQL se propagan. La aplicación
puede agrupar varias operaciones del registrar en una transacción conjunta.

### Personal access tokens

```python
class IAccessTokenRepository(ABC):
    async def create(self, tokenable, name: str, *, abilities=None, expires_at=None) -> NewAccessToken: ...
    async def findByPlainText(self, plain_text: str) -> AccessToken | None: ...
    async def touch(self, token_id: object) -> bool: ...
    async def revoke(self, token_id: object) -> bool: ...
    async def revokeAll(self, tokenable) -> int: ...
    async def purgeExpired(self) -> int: ...
```

El secreto solo está disponible en `plain_text` del resultado de emisión.
`repr()` y `NewAccessToken.toDict()` lo omiten. Devolver ese atributo explícitamente
una vez y nunca registrarlo. La introspección genérica y `dataclasses.asdict()`
no son mecanismos de redacción.

Abilities `None` significa sin restricción; una colección vacía no permite ninguna
ability. Valores malformados se rechazan sin coerción. Las fechas se normalizan
a UTC. `touch()` devuelve `False` si ganó expiración o revocación. Si el driver
schemaless no devuelve el ID generado, se recupera por el digest único.

### Fachada Auth

`Auth` se pinea durante el boot, de modo que sus métodos síncronos se
pueden llamar sin `await`, incluso desde las plantillas.

| Método | ¿Awaitable? | Propósito |
|---|---|---|
| `Auth.user()` | no | Identidad autenticada, o `None` |
| `Auth.identifier()` | no | Identificador de la identidad |
| `Auth.check()` / `Auth.guest()` | no | Estado de autenticación |
| `Auth.context()` | no | Contexto de autenticación completo |
| `Auth.guard(name)` | no | Guard configurado |
| `Auth.attempt(credentials)` | sí | Login web con credenciales |
| `Auth.login(identity)` / `Auth.logout()` | sí | Ciclo de vida de la sesión |
| `Auth.can(...)` / `cannot` / `canAny` / `canAll` | sí | Comprobación de permisos |
| `Auth.hasRole(role)` | sí | Comprobación de rol |
| `Auth.authorize(permission)` | sí | Exigir un permiso |
| `Auth.allows(ability, resource)` / `denies` | sí | Comprobación de policy |
| `Auth.authorizeResource(ability, resource)` | sí | Exigir una policy |
| `Auth.createToken(name, ...)` | sí | Emitir un token de acceso |
| `Auth.revokeCurrentToken()` | sí | Revocar el token presentado |
| `Auth.registerPolicy(resource, policy)` | no | Vincular una policy |

### Middleware

| Clase | Efecto |
|---|---|
| `ResolveIdentityMiddleware` | Fija el contexto y permite continuar a invitados |
| `ResolveSessionIdentityMiddleware` | Predeterminado del kernel para Web; resuelve sesión y permite invitados |
| `ResolveTokenIdentityMiddleware` | Predeterminado del kernel para API; resuelve Bearer y permite invitados |
| `AuthenticateMiddleware` | Exige identidad con el guard de la petición, o el configurado antes de resolverla |
| `AuthenticateSessionMiddleware` | Igual, fijado al guard de sesión |
| `AuthenticateTokenMiddleware` | Igual, fijado al guard de token |
| `GuestMiddleware` | Invitados continúan; navegadores autenticados salen de rutas de invitado |
| `RequirePermissionMiddleware` | Exige los permisos declarados |
| `RequireRoleMiddleware` | Exige los roles declarados |
| `RequirePolicyMiddleware` | Exige una ability sobre una clase de recurso |

El router de Orionis adjunta **clases** de middleware, no instancias
parametrizadas, así que los requisitos se declaran creando subclases. Una
clase real además mantiene válida la caché compilada de rutas, cosa que
una clase generada dinámicamente no podría hacer.
El kernel HTTP establece la identidad antes del middleware de aplicación y de ruta:

```text
Web: StartSession → CSRFToken → ResolveSessionIdentity → middleware de ruta → handler
API: ResolveTokenIdentity → middleware de ruta → handler
```

Estos valores predeterminados cubren todas las rutas resueltas, tanto controladores
como vistas. Las rutas públicas no necesitan middleware de auth para usar
`Auth.user()`, `Auth.check()` o directivas de autenticación en plantillas. La ausencia
de credenciales o las credenciales no utilizables producen un contexto invitado;
no restringen el acceso. API no inicia sesiones ni lee credenciales de sesión.
OPTIONS/preflight y errores anteriores al despacho no resuelven identidad.

Conserva `AuthenticateSessionMiddleware` o `AuthenticateTokenMiddleware` en grupos
protegidos, `GuestMiddleware` en login/registro y permisos/roles/policies en los
recursos correspondientes. Aplicar esas restricciones a todas las rutas también
restringiría los endpoints públicos. Resolver de nuevo el mismo guard reutiliza el
contexto, incluidos invitados, sin repetir consultas a repositorios.

El kernel fija el guard por tipo de ruta, independientemente de `auth.default`.
`ResolveIdentityMiddleware` y `AuthenticateMiddleware` sin guard explícito reutilizan
el de la petición; antes de resolverla siguen usando `auth.default`. Un guard fijado
explícitamente conserva su significado y no puede reemplazar un contexto autenticado
por otro guard. `.withOutMiddleware()` excluye middleware de ruta, no el del kernel.

`GuestMiddleware.redirect_to` reemplaza `auth.session.home` (fallback `/home`);
clientes JSON/AJAX autenticados reciben 403. La pertenencia a roles es informativa:
un middleware basado solo en
roles rechaza tokens restringidos, pues no declara una capacidad para intersectar.

Las peticiones anónimas sin credenciales no consultan repositorios de autenticación.
Web recupera la identidad cuando la sesión la contiene; API con credenciales válidas
también consulta el token y actualiza su último uso. Los permisos se cargan bajo demanda.
Resolver identidad no modifica las cabeceras de caché: un handler público que devuelve
datos personalizados debe establecer un `Cache-Control` apropiado, por ejemplo
`private, no-store`. Las rutas protegidas conservan las cabeceras de `AuthenticateMiddleware`.

### Excepciones y estados HTTP

```python
class AuthException(Exception): ...
class AuthConfigurationException(AuthException): ...
class AuthenticationException(AuthException): ...
class AuthorizationException(AuthException): ...
class GuardNotFoundException(AuthException): ...
class IdentityProviderException(AuthException): ...
class PolicyNotFoundException(AuthException): ...
class TokenException(AuthException): ...
```

Dos de ellas están mapeadas en `orionis/failure/base/handler.py`:

| Excepción | Estado | Significado |
|---|---|---|
| `AuthenticationException` | `401` | No hay identidad autenticada válida |
| `AuthorizationException` | `403` | Hay identidad, pero sin autorización |

Los navegadores reciben la página de error HTML estándar y los clientes
de API reciben JSON, porque el handler respeta `request.wantsJson()`.
Cuando `auth.session.redirect_to` está configurado,
`AuthenticateMiddleware` redirige solo navegadores del guard de sesión. Las rutas
token rechazan invitados con 401 incluso sin `Accept` e incluyen
`WWW-Authenticate: Bearer`. Las subclases de excepciones Auth conservan 401/403.
El handler estándar sigue eligiendo HTML o JSON por negociación de contenido.

### Service provider

`AuthProvider` está listado en `CORE_PROVIDERS` y **no** es diferido:
`Auth.check()` es síncrono, así que la fachada debe estar pineada cuando
se renderiza la primera plantilla.

```python
class AuthProvider(ServiceProvider):
    def register(self) -> None: ...
    async def boot(self) -> None: ...
```

| Lifetime | Componentes | Motivo |
|---|---|---|
| `SINGLETON` | Manager, guards, proveedor, authorizer, repositorios y registrar | No retienen identidad actual ni instancias de policy |
| `SCOPED` | Contexto, locks de operación/snapshot y Session vinculada | Estado de la petición |
| Por evaluación | Instancia de policy | La DI usa el scope actual |

`Auth` pinea su manager stateless al arrancar. `Session` usa `ScopedFacade`, que
lee directamente del scope activo sin un pin global de proceso.

## Ejemplos de uso

### Preparar el modelo de identidad

```python
from typing import ClassVar
from orionis.auth import Authenticatable, Authorizable
from orionis.orm import BigInteger, Boolean, DateTime, Model, String

class User(Model, Authenticatable, Authorizable):
    hidden: ClassVar[list[str]] = ["password", "remember_token"]
    fillable: ClassVar[list[str]] = ["name", "email", "password"]

    id = BigInteger().primary().autoIncrement()
    name = String(255)
    email = String(255).unique()
    password = String(255)
    active = Boolean().default(value=True)
```

### Login y logout web

```python
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.support.facades import Auth

class LoginController(BaseController):

    async def login(self, payload: LoginSchema) -> HttpResponse:
        """Authenticate the visitor and open a session."""
        granted = await Auth.attempt({
            "email": payload.email,
            "password": payload.password,
        })
        if not granted:
            return response.redirect("/login").withErrors({
                "email": "These credentials do not match our records.",
            })
        return response.redirect("/dashboard")

    async def logout(self) -> HttpResponse:
        """Close the session of the current visitor."""
        await Auth.logout()
        return response.redirect("/login")
```

### Proteger rutas

```python
from orionis.auth.middleware import (
    AuthenticateSessionMiddleware,
    RequirePermissionMiddleware,
)

class CanManageUsers(RequirePermissionMiddleware):
    """Route guard requiring the user management permissions."""

    permissions = ("users.view", "users.update")

Route.get("/users", [UserController, "index"]).middleware(
    AuthenticateSessionMiddleware,
    CanManageUsers,
)
```

### Emitir y usar un token de API

```python
from orionis.support.facades import Auth

# Inside a controller, for the authenticated identity.
issued = await Auth.createToken("mobile-app", abilities=["users.view"])
plain_text = issued.plain_text          # shown once, never stored

# The client then sends it on every request:
#     Authorization: Bearer <plain_text>
#
# Even if the identity also owns "users.delete", the token cannot use it:
#     await Auth.can("users.view")      -> True
#     await Auth.can("users.delete")    -> False
```

Protege las rutas de API con el guard de token:

```python
from orionis.auth.middleware import AuthenticateTokenMiddleware

Route.get("/api/v1/users", [UserController, "index"]).middleware(
  AuthenticateTokenMiddleware,
)
```

### Declarar una policy

```python
from orionis.auth import Policy
from orionis.support.facades import Auth

class PostPolicy(Policy):
    """Authorize operations performed on a single post."""

    async def update(self, identity: object, post: Post) -> bool:
        """Allow the update only for the author of the post."""
        return post.user_id == identity.getAuthIdentifier()

# Register it once, during boot.
Auth.registerPolicy(Post, PostPolicy)

# Then, inside a controller:
await Auth.authorizeResource("update", post)
```

## Rendimiento y concurrencia

- El guard de sesión añade un SELECT de identidad tras restaurar Session.
  Guardar una sesión activada renueva juntos servidor y cookie.
- Un PAT requiere tres sentencias: digest, identidad y UPDATE condicional de uso.
  Este camino no calcula un hash de contraseña.
- El primer chequeo RBAC añade un SELECT con UNION de grants directos, roles y
  grants heredados. Doce solicitudes concurrentes del snapshot hacen exactamente
  un SELECT en la prueba; las siguientes usan los sets inmutables sin SQL adicional.
- Las policies añaden construcción por DI y su lógica de aplicación. Cargan RBAC
  solo si lo necesitan; el contenedor cachea los metadatos de reflexión.
- Autorizar invitados no hace SQL. El middleware web puede crear sesión para
  CSRF y navegación.
- Actualizar Session exige registro vigente. SQL usa UPDATE, archivos usan
  `filelock` entre workers y caché usa reemplazo atómico o CAS de aiocache. Las
  peticiones antiguas no recrean sesiones borradas al guardarlas mediante el manager.
- No hay caché global de permisos. Un snapshot cargado permanece fijo para su
  contexto; los siguientes contextos observan los cambios de permisos.

## Compatibilidad

- Python `>= 3.14`, igual que el resto del framework.
- Bases de datos: el módulo aporta la migración de
  `personal_access_tokens` y reutiliza las tablas `permissions`, `roles`,
  `model_has_permissions`, `model_has_roles` y `role_has_permissions` que
  ya crean las migraciones del framework.
- Roles, permisos y tokens usan `table.id()`; pivotes usan claves compuestas.
  Los propietarios usan `VARCHAR(255)` canónico para enteros, texto y UUID.
  El compilador SQL
  añade una variante SQLite a las claves primarias `BIGINT`
  autoincrementales, porque SQLite solo trata una clave primaria de una
  columna como alias de `ROWID` cuando el tipo declarado es literalmente
  `INTEGER`. PostgreSQL sigue recibiendo `BIGSERIAL` y MySQL sigue
  recibiendo `BIGINT AUTO_INCREMENT`.
- `filelock` es dependencia base para bloquear persistencia entre procesos.
- Tras habilitar el módulo, borra `storage/framework/bootstrap` (o
  ejecuta `reactor optimize:clear`): la caché compilada de arranque no se
  invalida por cambios dentro de `orionis/`.

Cambios incompatibles: retirar `auth.identity.password` y argumentos `guard_name`.
`touch()` y `delete()` de stores de sesión devuelven booleanos. Los stores propios
deben implementar `update()` atómico y repositorios de caché `replace()` atómico.
`NewAccessToken.toDict()` redacta el secreto. Las policies se construyen por
evaluación y solo `True` autoriza; abilities también restringen policies. Una
petición autenticada con PAT no puede emitir otros PAT con `Auth.createToken()`.
`Auth.revokeCurrentToken()` también deja invitado el contexto actual.

Bases existentes necesitan una migración revisada: unificar nombres duplicados
y referencias de pivotes antes de eliminar `guard_name`, convertir propietarios
a texto y añadir índices de expiración/revocación y de permisos por rol.
Reconstruir es apropiado solo
para bases alpha desechables. Editar migraciones aplicadas no cambia sus tablas.
Respaldar datos reales; esta revisión no reinicia la base de la aplicación.

## Límites de seguridad

- Exigir HTTPS y cookies Secure/HttpOnly en producción. Limitar login y emisión
  de tokens con los controles HTTP de la aplicación.
- `Auth.attempt()` solo inicia sesión cuando `identity.active is True`.
  Los valores ausentes, nulos o falsos se rechazan después de verificar la
  contraseña.
- Revocar no cancela trabajo ya autorizado. Operaciones estrictas deben revalidar
  en su propia transacción. El aislamiento de lectura depende del motor configurado.
- Propietarios polimórficos no tienen FK hacia una tabla global de usuarios.
  Revocar tokens y retirar grants antes de borrar permanentemente al propietario;
  nunca reciclar su par tipo/clave. Las FK de roles/permisos son restrictivas:
  retirar pivotes primero y habilitar FK en SQLite.
- Los locks requieren soporte del sistema de archivos para las primitivas de
  `filelock`; sistemas de red necesitan validación de despliegue. Session en memoria
  es de un proceso. El payload concurrente sigue last-writer-wins, no una mezcla
  transaccional de carritos o datos flash.
- Los errores SQL omiten detalles del driver y valores para no registrar
  credenciales. La aplicación tampoco debe registrar passwords, cookies ni PAT.
- Las pruebas ejecutan SQLite en archivo, conexiones separadas, adaptadores
  ASGI/RSGI y DI real. PostgreSQL/MySQL/Oracle/SQL Server, Redis/Memcached vivos
  y workers en procesos separados requieren certificación de despliegue.

## Fuera del alcance de esta versión

Deliberadamente no implementados, y diseñados para poder añadirse sin
reescribir el núcleo: JWT, OAuth, OpenID Connect, LDAP, autenticación
básica, API keys genéricas, SSO, autenticación WebSocket, MFA, social
login, restablecimiento de contraseña, verificación de email, magic
links, impersonation y multi-tenancy específica de autenticación.

Las jerarquías y la herencia de roles también están ausentes a
propósito: un rol no es más que una agrupación de permisos.
