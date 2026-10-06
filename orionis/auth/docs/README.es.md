# orionis.auth

> Resuelve identidades mediante sesiones y tokens opacos, autorización por scope, login persistente y credenciales de recuperación de contraseñas.

Versión inglesa: [README.md](README.md). Punto de entrada para agentes: [SKILL.md](SKILL.md).

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [Exportaciones e imports](#exportaciones-e-imports)
- [Mixins de identidad](#mixins-de-identidad)
- [AuthenticationContext y helpers de scope](#authenticationcontext-y-helpers-de-scope)
- [AuthorizationSnapshot](#authorizationsnapshot)
- [ModelIdentityProvider](#modelidentityprovider)
- [SessionGuard](#sessionguard)
- [RememberMe](#rememberme)
- [TokenGuard](#tokenguard)
- [Funciones y entidades de tokens](#funciones-y-entidades-de-tokens)
- [AccessTokenRepository](#accesstokenrepository)
- [Authorizer, Policy y PolicyRegistry](#authorizer-policy-y-policyregistry)
- [PermissionRegistrar y DatabasePermissionRepository](#permissionregistrar-y-databasepermissionrepository)
- [AuthManager](#authmanager)
- [Middlewares](#middlewares)
- [PasswordBroker](#passwordbroker)
- [AuthProvider](#authprovider)
- [Excepciones](#excepciones)
- [Contratos](#contratos)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)

## Requisitos

Auth no tiene un extra de instalación propio. Las operaciones respaldadas por
base de datos requieren una conexión Orionis configurada, un modelo de identidad
compatible y tablas existentes. Las operaciones de sesión también requieren una
petición con `request.state.session`. Los mixins, entidades, snapshots y helpers
de contexto puros no necesitan preparar una base de datos.

| Área | Preparación adicional y evidencia |
|---|---|
| Identidad | Configurar `auth.identity.model`; proporcionar metadatos ORM y el mixin o contrato de autenticación. Véase [ModelIdentityProvider](../identity/provider.py). |
| Login web | Iniciar la sesión antes de resolver la identidad. El [kernel HTTP](../../http/kernel.py) construye `StartSessionMiddleware`, el middleware CSRF y `ResolveSessionIdentityMiddleware` en ese orden. |
| Login persistente | Proporcionar una columna nullable `remember_token` y soporte de comparación y reemplazo en el proveedor. Se requiere HTTPS cuando `auth.remember.secure` es true. Véase [RememberMe](../remember.py). |
| RBAC | Crear `permissions`, `roles`, `model_has_permissions`, `model_has_roles` y `role_has_permissions`, con nombres únicos y claves compuestas en los pivotes. Véanse [registrar](../authorization/registrar.py) y [repository](../authorization/repository.py). |
| Tokens de acceso | Crear la tabla de tokens configurada; la [migración suministrada](../../../database/migrations/m0000000011_create_personal_access_tokens_table.py) usa `personal_access_tokens` por defecto. El digest debe ser único. |
| Recuperación de contraseña | Crear la tabla de recuperación configurada. El [esquema](../../../database/schemas/password_reset_tokens_v1.py) declara `email` como clave primaria, `token` nullable, `user_id`, `password_fingerprint` y `created_at`. La [migración](../../../database/migrations/m0000000012_create_password_reset_tokens_table.py) la crea. |

Los gestores, repositorios y brokers no crean estas tablas. Los drivers de base
de datos y backends de hashing son dependencias de sus servicios Orionis, no
motores de autenticación alternativos. Las restricciones de dependencias se
detallan en [Notas de compatibilidad](#notas-de-compatibilidad).

Los siguientes valores son fallbacks, no una promesa sobre una aplicación
configurada. Las entidades de configuración leen variables de entorno y pueden
sobrescribirse mediante la configuración de la aplicación.

| Clave | Fallback | Fuente y restricción verificada |
|---|---|---|
| `auth.default` | `"session"` | [Auth](../../foundation/config/auth/entities/auth.py): normaliza los nombres de guards admitidos. `AuthManager` selecciona el guard de sesión si el valor es falsy. |
| `auth.identity.model` | `"app.models.user.User"` | [Identity](../../foundation/config/auth/entities/identity.py): ruta cualificada de clase no vacía; el [proveedor](../identity/provider.py) la importa de forma diferida. |
| `auth.identity.username` | `"email"` | [Identity](../../foundation/config/auth/entities/identity.py): cadena no vacía. Las contraseñas enviadas siguen usando la clave literal `"password"`. |
| `auth.session.key` | `"_auth_identifier"` | [SessionAuth](../../foundation/config/auth/entities/session.py): cadena no vacía. El guard guarda también un fingerprint de contraseña bajo esta clave más `"_password"`. |
| `auth.session.redirect_to` | `None` | [SessionAuth](../../foundation/config/auth/entities/session.py): cadena o `None`; destino del navegador invitado, no el home posterior al login. |
| `auth.session.home` | `"/home"` | [SessionAuth](../../foundation/config/auth/entities/session.py): cadena no vacía, utilizada por `GuestMiddleware`. |
| `auth.tokens.table` | `"personal_access_tokens"` | [Tokens](../../foundation/config/auth/entities/tokens.py): cadena no en blanco. |
| `auth.tokens.expiration` | `None` | [Tokens](../../foundation/config/auth/entities/tokens.py): entero positivo en minutos, excluidos los booleanos, o `None`. |
| `auth.tokens.secret_bytes` | `40` | [Tokens](../../foundation/config/auth/entities/tokens.py): entero entre 32 y 128, excluidos los booleanos. |
| `auth.remember.cookie` | `"orionis_remember"` | [RememberAuth](../../foundation/config/auth/entities/remember.py): letras ASCII, dígitos, guiones bajos o guiones, sin quedar vacía; debe diferir de `session.cookie`. |
| `auth.remember.lifetime` | `43200` | [RememberAuth](../../foundation/config/auth/entities/remember.py): entero positivo en minutos, excluidos los booleanos. |
| `auth.remember.secure` | `True` | [RememberAuth](../../foundation/config/auth/entities/remember.py): booleano; los nombres de cookie con prefijo de seguridad exigen true. |
| `auth.passwords.table` | `"password_reset_tokens"` | [PasswordReset](../../foundation/config/auth/entities/password_reset.py): cadena no en blanco. |
| `auth.passwords.expiration` | `60` | [PasswordReset](../../foundation/config/auth/entities/password_reset.py): entero positivo en minutos, excluidos los booleanos. |
| `auth.passwords.throttle` | `60` | [PasswordReset](../../foundation/config/auth/entities/password_reset.py): entero positivo en segundos, excluidos los booleanos. |

`SessionGuard` lee por separado `http.csrf.session_key` y
`http.csrf.token_length`, con fallbacks `"_csrf_token"` y `32`.
Solo los constructores de entidades realizan las validaciones anteriores;
varios servicios concretos aceptan un objeto similar a la aplicación y leen
valores sin validar. `RememberMe` y `PasswordBroker` construyen explícitamente
sus entidades de configuración.

## Descripción funcional

Los guards convierten las credenciales de una petición en identidades y valores
`GuardResult`. `AuthenticationContext` publica ese resultado dentro de un scope
del contenedor; su snapshot diferido combina permisos de identidad con
restricciones de credencial. `AuthManager` expone estos servicios y las
transiciones de sesión; `RememberMe` y `PasswordBroker` gestionan por separado
las credenciales persistentes y de recuperación.

Sus colaboradores directos son `IHashManager`, ORM/query builders de Orionis,
scopes del contenedor y el pipeline HTTP/sesión. La [fachada Auth](../../support/facades/auth.py)
resuelve `IAuthManager`; está fuera del módulo, no es una exportación raíz de Auth.
El [kernel](../../http/kernel.py) resuelve identidades de sesión en rutas web y
de token en rutas API antes de los middlewares de aplicación/ruta. La resolución
permite invitados; la protección es una operación separada de middleware o gestor.

## Estructura del módulo

Se inspeccionaron los 53 archivos Python, incluidos los 11 inicializadores de
paquete. No hay recursos de ejecución no Python dentro de este módulo.

| Archivos o paquete | Responsabilidad y símbolos principales |
|---|---|
| [__init__.py](../__init__.py) | Dieciséis exportaciones raíz diferidas y descubrimiento de atributos del paquete. |
| [exceptions.py](../exceptions.py) | Ocho excepciones públicas de autenticación. |
| [manager.py](../manager.py), [provider.py](../provider.py) | `AuthManager`, `AuthProvider`. |
| [remember.py](../remember.py) | `RememberMe`, `apply_remember_cookie`. |
| [concerns/authenticatable.py](../concerns/authenticatable.py), [authorizable.py](../concerns/authorizable.py), [functions.py](../concerns/functions.py), [must_verify_email.py](../concerns/must_verify_email.py), [inicializador](../concerns/__init__.py) | Mixins de identidad, normalización de claves y marcador de verificación de correo. |
| [context/context.py](../context/context.py), [functions.py](../context/functions.py), [inicializador](../context/__init__.py) | `AuthenticationContext`, `GUEST_CONTEXT`, binding y bloqueo de transiciones. |
| [authorization/authorizer.py](../authorization/authorizer.py), [policy.py](../authorization/policy.py), [registry.py](../authorization/registry.py), [repository.py](../authorization/repository.py), [registrar.py](../authorization/registrar.py), [snapshot.py](../authorization/snapshot.py), [inicializador](../authorization/__init__.py) | Evaluación de policies, caché de búsquedas, lecturas/escrituras RBAC y snapshots. |
| [guards/session_guard.py](../guards/session_guard.py), [token_guard.py](../guards/token_guard.py), [inicializador](../guards/__init__.py) | Guards de sesión y de tokens personales de acceso. |
| [identity/provider.py](../identity/provider.py), [inicializador](../identity/__init__.py) | `ModelIdentityProvider`. |
| [entities/access_token.py](../entities/access_token.py), [guard_result.py](../entities/guard_result.py), [new_access_token.py](../entities/new_access_token.py), [inicializador](../entities/__init__.py) | Metadatos de credencial y resultados de guard/emisión. |
| [tokens/functions.py](../tokens/functions.py), [repository.py](../tokens/repository.py), [inicializador](../tokens/__init__.py) | Secreto aleatorio de token, digest y persistencia. |
| [middleware/authenticate.py](../middleware/authenticate.py), [authorize.py](../middleware/authorize.py), [guest.py](../middleware/guest.py), [policy.py](../middleware/policy.py), [resolve_identity.py](../middleware/resolve_identity.py), [inicializador](../middleware/__init__.py) | Diez clases públicas de middleware. |
| [passwords/broker.py](../passwords/broker.py), [inicializador](../passwords/__init__.py) | `PasswordBroker`; el inicializador está vacío. |
| [Inicializador de contratos](../contracts/__init__.py) y sus doce archivos enlazados en [Contratos](#contratos) | Interfaces abstractas, incluido el soporte opcional de token persistente. |

## Referencia de API

Los bloques de declaraciones reproducen las firmas, decoradores, campos y valores
predeterminados del código. Se omiten los cuerpos: son fragmentos de referencia,
no scripts ejecutables. Los tipos conservan su escritura aunque se importen solo
bajo `TYPE_CHECKING`. Los scripts ejecutables aparecen exclusivamente en
[Ejemplos de uso](#ejemplos-de-uso). El módulo no declara overloads, enumeraciones
públicas ni alias públicos de tipos.

Las excepciones descritas incluyen fallos explícitos y propagaciones
inspeccionadas; no son listas exhaustivas cuando intervienen dependencias,
callbacks, imports u operaciones de base de datos.

### Exportaciones e imports

El [inicializador raíz](../__init__.py) exporta de forma diferida `AccessToken`,
`AuthConfigurationException`, `AuthException`, `Authenticatable`,
`AuthenticationContext`, `AuthenticationException`, `Authorizable`,
`AuthorizationException`, `AuthorizationSnapshot`, `GuardNotFoundException`,
`IdentityProviderException`, `MustVerifyEmail`, `NewAccessToken`, `Policy`,
`PolicyNotFoundException` y `TokenException`.
Su `__getattr__` delega en [resolve_export](../../_exports.py), que importa y
cachea el objeto solicitado en el namespace del paquete. Los nombres desconocidos
lanzan `AttributeError`; `__dir__` incluye atributos cargados y exports declarados.

| Paquete importable | Reexportaciones adicionales |
|---|---|
| `orionis.auth.authorization` | `PolicyRegistry`, `EMPTY_SNAPSHOT`, `Policy`, `AuthorizationSnapshot`. El authorizer y los colaboradores SQL necesitan imports desde sus archivos. |
| `orionis.auth.concerns` | `Authenticatable`, `Authorizable`, `MustVerifyEmail`, `model_primary_key`. |
| `orionis.auth.context` | `AuthenticationContext`, `GUEST_CONTEXT`, `bind_auth_context`, `current_auth_context`. |
| `orionis.auth.entities` | `AccessToken`, `GuardResult`, `NewAccessToken`. |
| `orionis.auth.guards` | `SessionGuard`, `TokenGuard`. |
| `orionis.auth.identity` | `ModelIdentityProvider`. |
| `orionis.auth.tokens` | `AccessTokenRepository`, `generate_token_secret`, `hash_token_secret`. |
| `orionis.auth.middleware` | Las diez clases de middleware detalladas abajo. |
| `orionis.auth.contracts` | Los doce contratos detallados abajo. |

Importar `orionis.auth.context.functions.authentication_lock`,
`orionis.auth.concerns.functions.authorizable_key`,
`orionis.auth.passwords.broker.PasswordBroker`, `orionis.auth.remember.RememberMe`,
`orionis.auth.manager.AuthManager` y `orionis.auth.provider.AuthProvider` desde
sus archivos de definición. Estos nombres no se reexportan desde la raíz.

### Mixins de identidad

Fuentes: [Authenticatable](../concerns/authenticatable.py),
[Authorizable](../concerns/authorizable.py), [helpers](../concerns/functions.py),
[MustVerifyEmail](../concerns/must_verify_email.py).
Las rutas de importación son `orionis.auth.concerns.authenticatable`,
`orionis.auth.concerns.authorizable`, `orionis.auth.concerns.functions` y
`orionis.auth.concerns.must_verify_email`, respectivamente.

```python
class Authenticatable:
    AUTH_PASSWORD: ClassVar[str] = "password"
    def getAuthIdentifierName(self) -> str:
    def getAuthIdentifier(self) -> object:
    def getAuthPassword(self) -> str:

class Authorizable:
    AUTHORIZABLE_TYPE: ClassVar[str | None] = None
    def getAuthorizableType(self) -> str:
    def getAuthorizableId(self) -> object:

class MustVerifyEmail:

def authorizable_key(identity: object) -> tuple[str, str]:
def model_primary_key(instance: object) -> str:
```

`Authenticatable.getAuthIdentifierName()` usa el nombre no vacío de la clave
primaria en los metadatos de clase o `"id"`; el accessor del identificador devuelve
ese atributo o `None`. `getAuthPassword()` lee `AUTH_PASSWORD` y devuelve una
cadena vacía si el hash falta o no es una cadena. El mixin no calcula hashes.

`Authorizable.getAuthorizableType()` devuelve el valor explícito de clase cuando
no es `None`; en otro caso, el módulo y nombre cualificado de la clase real.
`getAuthorizableId()` usa la misma búsqueda con metadatos/fallback. Renombrar una
clase puede cambiar su tipo derivado de propietario persistido. Los mixins se
registran como subclases virtuales de `IAuthenticatable` y `IAuthorizable`; no
heredan de `ABCMeta` ni añaden almacenamiento de modelo por sí mismos.

`authorizable_key()` acepta accessors invocables mediante duck typing. Devuelve
tipo de propietario e ID textual canónico, ambos no vacíos y de hasta 255
caracteres. Los IDs deben ser `int`, `str` o `UUID`, excluidos los booleanos.
Lanza `AuthException` para formas/claves inválidas; las excepciones de los
accessors del objeto se propagan. Ningún helper consulta almacenamiento ni
elimina espacios. `MustVerifyEmail` es una clase marcador vacía, no un emisor de
verificaciones, emisor de tokens ni middleware.

### AuthenticationContext y helpers de scope

Fuentes e imports: `orionis.auth.context.context`
([implementación](../context/context.py)), `orionis.auth.context.functions`
([helpers](../context/functions.py)). Contrato: `IAuthenticationContext`.

```python
class AuthenticationContext(IAuthenticationContext):
    def __init__(
        self,
        identity: IAuthenticatable | None = None,
        guard: str | None = None,
        abilities: Iterable[str] | None = None,
        repository: IPermissionRepository | None = None,
        credential_id: object | None = None,
    ) -> None:
    @property
    def identity(self) -> IAuthenticatable | None:
    @property
    def guard(self) -> str | None:
    @property
    def abilities(self) -> frozenset[str] | None:
    @property
    def credentialId(self) -> object | None:
    @property
    def isAuthenticated(self) -> bool:
    @property
    def isGuest(self) -> bool:
    def identifier(self) -> object | None:
    async def authorization(self) -> IAuthorizationSnapshot:
    def __repr__(self) -> str:

GUEST_CONTEXT: AuthenticationContext = AuthenticationContext()

def authentication_lock() -> asyncio.Lock:
def current_auth_context() -> IAuthenticationContext:
def bind_auth_context(context: IAuthenticationContext) -> None:
```

El constructor conserva referencias a identidad/repositorio y materializa las
abilities como `frozenset`, o conserva `None`. No valida los nombres individuales
de ability. Las propiedades públicas no tienen setter/deleter. `identifier()`
llama a `getAuthIdentifier()` de la identidad actual o devuelve `None`.

`bind_auth_context()` exige un `ScopeManager` activo, asigna el contexto bajo
`IAuthenticationContext` y vincula a ese scope los contextos incorporados distintos
de `GUEST_CONTEXT`. Reutilizar un contexto incorporado en otro scope lanza
`AuthException`. Tras vincularlo, la identidad y el ID de credencial pasan a
`None` cuando se reemplaza el contexto, cierra el scope o lo lee un scope distinto.
Guard/abilities siguen visibles. Un contexto no vinculado no comprueba propietario;
construirlo no lo convierte en local al scope. Las implementaciones personalizadas
del contrato no adquieren las comprobaciones incorporadas mediante este helper.

`current_auth_context()` devuelve el binding actual o el invitado compartido si
no hay scope/binding activo. Basta un scope activo; no tiene que ser una petición
HTTP. `authentication_lock()` devuelve un `asyncio.Lock` guardado en el scope o
lanza `AuthException` si no hay un scope activo. Serializa operaciones de auth
cooperantes, no escrituras directas arbitrarias de la aplicación.

`authorization()` devuelve `EMPTY_SNAPSHOT` para contextos obsoletos, invitados
o ausencia de repositorio. En otro caso llama de forma diferida a
`repository.loadFor(identity)`, cachea un `AuthorizationSnapshot` y vuelve a
comprobar la propiedad después del I/O esperado. El bloqueo del contexto y una
segunda comprobación de caché comparten una carga exitosa entre tareas cooperantes.
Los fallos de carga se propagan y no se cachean; otra llamada puede reintentarlos.
No hay un método público de refresh/invalidación. `repr()` expone estado invitado
o guard e ID, no contraseñas ni tokens. El `_fork()` privado es soporte de ciclo de
vida, no una API pública de propagación; crea nueva propiedad/caché/bloqueo.

### AuthorizationSnapshot

Importar `orionis.auth.authorization.snapshot.AuthorizationSnapshot` y
`EMPTY_SNAPSHOT`; ambos se reexportan desde `orionis.auth.authorization`.
Fuente: [snapshot.py](../authorization/snapshot.py).

```python
class AuthorizationSnapshot(IAuthorizationSnapshot):
    def __init__(
        self,
        permissions: Iterable[str],
        roles: Iterable[str],
        abilities: Iterable[str] | None = None,
    ) -> None:
    @property
    def permissions(self) -> frozenset[str]:
    @property
    def roles(self) -> frozenset[str]:
    @property
    def abilities(self) -> frozenset[str] | None:
    def can(self, permission: str) -> bool:
    def hasRole(self, role: str) -> bool:
    def __repr__(self) -> str:

EMPTY_SNAPSHOT: AuthorizationSnapshot = AuthorizationSnapshot(
    permissions=(),
    roles=(),
)
```

Las entradas se materializan y deduplican inmediatamente. Las propiedades exponen
valores `frozenset` de solo lectura sin copiarlos. `permissions` es el conjunto
propio, no una intersección precalculada: `can()` exige pertenencia a permisos y,
cuando existan, a abilities. `None` no restringe; un conjunto vacío de abilities
no permite nada. No se expanden comodines ni se normalizan nombres o mayúsculas.
`hasRole()` ignora las abilities de credencial. Entradas/claves no hashables
pueden propagar `TypeError`; los constructores no exigen el tipo de elemento
anotado. Los iteradores se consumen al construir. `repr()` muestra los tamaños de
las colecciones y si las abilities no restringen. Es una clase con slots y
propiedades públicas de solo lectura, no una dataclass congelada.

### ModelIdentityProvider

Importar `orionis.auth.identity.provider.ModelIdentityProvider` o su reexportación
desde el paquete identity. Fuente: [provider.py](../identity/provider.py).

```python
class ModelIdentityProvider(IIdentityProvider):
    def __init__(self, app: IApplication, hasher: IHashManager) -> None:
    def model(self) -> type[Model]:
    async def retrieveById(self, identifier: object) -> IAuthenticatable | None:
    async def retrieveByCredentials(
        self,
        credentials: Mapping[str, object],
    ) -> IAuthenticatable | None:
    async def updateRememberToken(
        self,
        identity: IAuthenticatable,
        expected: str | None,
        token: str | None,
    ) -> bool:
    async def validateCredentials(
        self,
        identity: IAuthenticatable | None,
        credentials: Mapping[str, object],
    ) -> bool:
```

`model()` importa la ruta cualificada configurada en el primer uso y cachea la
clase. Los fallos de import/atributo/ruta y los valores que no sean una subclase
de `IAuthenticatable` lanzan `IdentityProviderException`. La implementación
comprueba ese contrato, no la herencia ORM; las consultas posteriores requieren
los metadatos ORM y métodos de query declarados. Cambiar configuración no invalida
una clase ya resuelta.

`retrieveById(None)` devuelve `None` sin resolver el modelo. Las demás claves deben
ser `int`, `str` o `UUID` no vacíos, de hasta 255 caracteres textuales y no
booleanos. Las claves de columna entera se convierten con `int`; las de columna
UUID usan `UUID` y respetan `as_uuid`; las demás pasan a texto. Las conversiones
inválidas devuelven `None`. Las queries conservan scopes y soft deletes del modelo.

`retrieveByCredentials()` lee solo el campo username configurado; su ausencia,
cadena vacía o valor no string devuelven `None`. No elimina espacios, convierte
a minúsculas ni comprueba contraseñas. `validateCredentials()` lee `"password"`,
acepta una cadena no vacía de hasta 4096 caracteres y espera al hasher. Las
identidades o hashes almacenados ausentes también llaman a `make()` y devuelven
`False`. Un `ValueError` de verificación se trata como credencial inválida; los
demás fallos se propagan. No se garantiza igualdad temporal. El [driver Argon2
inspeccionado](../../hashing/hashers/argon2_hasher.py) delega el cálculo/verificación
en `asyncio.to_thread`.

`updateRememberToken()` devuelve `False` si el modelo carece de `remember_token`.
En otro caso actualiza condicionalmente una fila que coincida con clave de
identidad, hash de contraseña y token esperado, usando comparación SQL NULL para
`expected=None`. Un reemplazo no nulo también exige `active=True` en SQL. Devuelve
si cambió exactamente una fila; no muta la instancia de identidad recibida.
Accede a `identity.AUTH_PASSWORD` además de los tres métodos del contrato.

### SessionGuard

Importar `orionis.auth.guards.session_guard.SessionGuard`, también reexportado por
guards. Fuente: [session_guard.py](../guards/session_guard.py).
Contrato: `ISessionGuard`.

```python
class SessionGuard(ISessionGuard):
    def __init__(self, app: IApplication, identities: IIdentityProvider) -> None:
    @property
    def name(self) -> str:
    async def resolve(self, request: Request) -> GuardResult | None:
    async def attempt(
        self,
        request: Request,
        credentials: Mapping[str, object],
        *,
        remember: bool = False,
    ) -> IAuthenticatable | None:
    def login(self, request: Request, identity: IAuthenticatable) -> None:
    async def logout(self, request: Request) -> None:
```

`name` es `"session"`. El constructor captura configuración/proveedor y crea
`RememberMe`. Por tanto puede propagar errores de configuración persistente,
incluida una colisión de nombres de cookie. El guard no conserva identidad actual.

| Operación | Resultado, mutación y casos límite |
|---|---|
| `resolve(request)` | Sin sesión devuelve `None`. Busca el identificador almacenado y compara el fingerprint guardado con el hash actual. La ausencia de identidad/fingerprint o una diferencia elimina las dos claves auth e intenta restauración persistente. Una sesión ordinaria válida devuelve `GuardResult`; esta rama no comprueba `active`. |
| `attempt(request, credentials, remember=...)` | Espera búsqueda y verificación, y después exige `active is True` en Python. Credenciales/estado inválidos devuelven `None`. Opt-in emite una credencial persistente; opt-out olvida la anterior. Luego llama a `login()` y devuelve la identidad, no un booleano. |
| `login(request, identity)` | Requiere sesión e ID escalar no vacío de tipo `int`, `str` o `UUID`, excluidos los booleanos; si no, lanza `AuthException`. Solicita regeneración, guarda ID canónico/fingerprint, crea un token CSRF y actualiza `request.state.csrf_token`. No comprueba contraseña ni `active`. |
| `logout(request)` | Revoca login persistente, elimina claves auth e invalida la sesión. Sin sesión solo encola eliminación de cookie persistente. Los errores del proveedor pueden propagarse antes de invalidar. |

El guard no guarda la sesión ni emite cookies por sí mismo. Esas operaciones
pertenecen al [middleware de sesión](../../http/layer/web/start_session.py) y al
[gestor de sesión](../../session/manager.py). Llamar directamente al guard no
vincula un `AuthenticationContext`; middleware/gestor realizan esa publicación.

### RememberMe

Importar `orionis.auth.remember.RememberMe` y `apply_remember_cookie`.
Fuente: [remember.py](../remember.py).

```python
class RememberMe:
    def __init__(self, app: IApplication, identities: IIdentityProvider) -> None:
    def clearCookie(self, request: Request) -> None:
    async def issue(self, request: Request, identity: IAuthenticatable) -> None:
    async def restore(self, request: Request) -> IAuthenticatable | None:
    async def revoke(self, request: Request, identifier: object) -> None:
    async def forget(self, request: Request, identity: IAuthenticatable) -> None:

def apply_remember_cookie(request: Request, response: Response) -> None:
```

El estado público es `RememberMe.settings` (`RememberAuth`) y
`RememberMe.identities` (proveedor inyectado), asignados sin anotaciones de campo
declaradas. La clase no declara slots; esas referencias pueden reemplazarse.
El constructor lanza `ValueError` si su cookie coincide con `session.cookie` y
propaga los errores de validación de settings.

`issue()` exige `request.scheme == "https"` si la configuración segura está
activada; después crea selector de identidad, vencimiento y secreto aleatorio de
32 bytes. El almacenamiento conserva un digest versionado vinculado a toda la
cookie y al hash actual de contraseña. Usa
`updateRememberToken(identity, expected, replacement)` y lanza `AuthException`
si la persistencia informa fallo. El llamador debe comprobar antes la contraseña:
este método no lo hace. Una nueva emisión reemplaza el único grant de la identidad.

`restore()` devuelve `None` ante transporte inseguro, cookie ausente/no string,
credenciales inválidas, identidades inactivas o carrera de comparación y reemplazo
perdida. Las cookies se limitan a 512 caracteres y al patrón exacto de selector,
vencimiento y secreto de 43 caracteres. Los valores presentados malformados o
vencidos encolan eliminación; una identidad ausente o digest distinto no
necesariamente encola cambios de cookie. Una restauración exitosa rota la
credencial, conserva el vencimiento original y encola el tiempo restante.
Devuelve la identidad sin hacer login ni vincular contexto; `SessionGuard`
realiza la transición de sesión.

`revoke()` busca el identificador recibido si no es `None`, olvida su grant cuando
lo encuentra y elimina la cookie. `forget()` compara y reemplaza un token
existente por `None` y encola eliminación; un resultado false no se lanza como
error. Las excepciones del proveedor se propagan. `clearCookie()` solo encola una
cookie vacía con edad cero.

La cola vive en el estado de la petición. `apply_remember_cookie()` no hace nada
sin estado pendiente; en otro caso llama a `response.setCookie()` y establece
`Cache-Control` en `"no-store"`. Las cookies usan `/`, HttpOnly, Secure configurado
y SameSite lax, sin Domain. Aplicar la cola no la elimina. Vencimiento,
comparación de digest y rotación condicional son independientes del almacenamiento
de la sesión ordinaria.

### TokenGuard

Importar `orionis.auth.guards.token_guard.TokenGuard`, también reexportado por
guards. Fuente: [token_guard.py](../guards/token_guard.py). Contrato: `IGuard`.

```python
class TokenGuard(IGuard):
    def __init__(
        self,
        tokens: IAccessTokenRepository,
        identities: IIdentityProvider,
    ) -> None:
    @property
    def name(self) -> str:
    async def resolve(self, request: Request) -> GuardResult | None:
```

`name` es `"token"`. `resolve()` lee `request.bearerToken`, busca metadatos,
recupera al propietario, compara sus accessors invocables con el tipo e ID
canónico almacenados y después espera `touch(id)`. Credenciales/propietarios
ausentes o inutilizables, propietarios distintos o touch fallido devuelven
`None`. El éxito devuelve `GuardResult` con abilities e ID de credencial del
registro. No comprueba `active`, calcula hashes de contraseña, inicia sesión ni
vincula contexto. Los fallos de dependencias se propagan; revocar no cancela el
trabajo ya en curso.

La [implementación de Request.bearerToken](../../http/request.py) acepta Bearer
sin distinguir mayúsculas, elimina espacios alrededor del token y rechaza
cabeceras Authorization duplicadas. Ese parsing pertenece a Request, no a TokenGuard.

### Funciones y entidades de tokens

Imports y fuentes: `orionis.auth.tokens.functions`
([helpers](../tokens/functions.py)), `orionis.auth.entities.access_token`
([AccessToken](../entities/access_token.py)), `orionis.auth.entities.guard_result`
([GuardResult](../entities/guard_result.py)), `orionis.auth.entities.new_access_token`
([NewAccessToken](../entities/new_access_token.py)).

```python
def generate_token_secret(size: int) -> str:
def hash_token_secret(secret: str) -> str:

@dataclass(frozen=True, slots=True, kw_only=True)
class AccessToken:
    id: object
    tokenable_type: str
    tokenable_id: object
    name: str
    abilities: frozenset[str] | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    def toDict(self) -> dict[str, object]:

@dataclass(frozen=True, slots=True, kw_only=True)
class GuardResult:
    identity: IAuthenticatable
    guard: str
    abilities: frozenset[str] | None = None
    credential_id: object | None = None

@dataclass(frozen=True, slots=True, kw_only=True)
class NewAccessToken:
    access_token: AccessToken
    plain_text: str = field(repr=False)
    def toDict(self) -> dict[str, object]:
```

`generate_token_secret()` delega en `secrets.token_urlsafe(size)` sin validar por
su cuenta un rango de tamaño. `hash_token_secret()` codifica una cadena en UTF-8
y devuelve su digest SHA-256 hexadecimal de 64 caracteres. Ninguno hace I/O.
Los errores de tipo/codificación/tamaño de la biblioteca estándar pueden
propagarse; este helper de digest no es el servicio de hashing de contraseñas.

El decorador dataclass genera constructores, igualdad, representación y
comportamiento de asignación congelada; aquí no se declaran constructores
explícitos. Todos los campos de construcción son solo por nombre, con los
requeridos/defaults mostrados arriba. Las dataclasses no validan los tipos anotados
ni congelan profundamente referencias arbitrarias. `GuardResult` conserva la
referencia de identidad.

| Entidad | Significado de campos |
|---|---|
| `AccessToken` | `id`: clave de fila del token; `tokenable_type`/`tokenable_id`: tipo/clave de propietario polimórfico; `name`: etiqueta de emisión; `abilities`: límites de credencial; `created_at`: momento de emisión; `expires_at`: vencimiento; `last_used_at`: uso registrado; `revoked_at`: momento de revocación. Los cuatro timestamps tienen None por defecto. |
| `GuardResult` | `identity`: objeto resuelto; `guard`: nombre del guard productor; `abilities`: límites de credencial; `credential_id`: clave de credencial revocable o None. |
| `NewAccessToken` | `access_token`: metadatos almacenados; `plain_text`: secreto bearer recién emitido. Ningún campo tiene valor predeterminado. |

`AccessToken.toDict()` llama a `dataclasses.asdict()` y devuelve metadatos copiados,
incluidas fechas y colecciones de abilities nativas, no serialización JSON.
`NewAccessToken.toDict()` devuelve solo metadatos `{"access_token": ...}`. Su
`repr()` generado excluye `plain_text`; el atributo sigue siendo legible
directamente. El `dataclasses.asdict()` genérico sí lo expone. Ningún campo de
`AccessToken` conserva el digest de base de datos; el secreto plano solo se
devuelve al emitir, no al consultar.

### AccessTokenRepository

Importar `orionis.auth.tokens.repository.AccessTokenRepository`, también
reexportado por tokens. Fuente: [repository.py](../tokens/repository.py).

```python
class AccessTokenRepository(IAccessTokenRepository):
    def __init__(self, app: IApplication, db: IQueryBuilder) -> None:
    async def create(
        self,
        tokenable: IAuthorizable,
        name: str,
        *,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
    async def findByPlainText(self, plain_text: str) -> AccessToken | None:
    async def touch(self, token_id: object) -> bool:
    async def revoke(self, token_id: object) -> bool:
    async def revokeAll(self, tokenable: IAuthorizable) -> int:
    async def purgeExpired(self) -> int:
```

`create()` guarda digest de secreto aleatorio, clave canónica de propietario,
nombre original, abilities codificadas y timestamps; devuelve `NewAccessToken`.
Los nombres deben ser cadenas no en blanco de hasta 255 caracteres; los espacios
periféricos se conservan. Las abilities rechazan strings/bytes como colección,
valores no hashables, más de 256 entradas distintas, nombres no string, vacíos o
de más de 255 caracteres. Se convierten en `frozenset`; los duplicados se colapsan
y el padding se conserva. El límite de tamaño se comprueba después de materializar
el iterable. Los valores de token inválidos lanzan `TokenException`; propietarios
inválidos lanzan `AuthException` desde la normalización de claves.

Un vencimiento explícito se normaliza a UTC sin offset de zona horaria. `None`
aplica minutos de expiración configurados o queda ilimitado si no existen.
La implementación también acepta cadenas ISO parseables pese a la anotación
datetime declarada; los valores no nulos malformados lanzan `TokenException`.
Se pueden guardar vencimientos ya transcurridos, pero fallan al consultar después.
El JSON almacenado es un array ordenado de abilities o SQL NULL sin restricciones.

Si la inserción no proporciona ID generado, la creación lo busca por digest único.
La ausencia de fila lanza entonces `TokenException`. Los fallos SQL se propagan;
la emisión no crea una transacción de aplicación ni reintenta colisiones de digest.

`findByPlainText()` rechaza entradas no string, vacías o de más de 512 caracteres
antes del I/O. Tokens desconocidos, revocados, vencidos o con timestamps/abilities
malformados devuelven `None`; se aceptan timestamps nulos. El registro encontrado
contiene metadatos, no el secreto. `touch(None)`/`revoke(None)` devuelven `False`;
en otro caso touch actualiza condicionalmente una fila no revocada con deadline
nulo o futuro, mientras revoke marca una fila no revocada sin considerar su
vencimiento. Ambos devuelven si cambiaron filas.

`revokeAll()` marca todas las filas no revocadas que coincidan con tipo de
propietario e ID canónico y devuelve el recuento afectado. `purgeExpired()` hace
dos deletes: primero vencimientos transcurridos, después los revocados restantes;
devuelve la suma. Ningún método cambia directamente un contexto de petición;
la revocación de token actual del gestor añade esa transición.

### Authorizer, Policy y PolicyRegistry

Imports: `orionis.auth.authorization.authorizer.Authorizer`,
`orionis.auth.authorization.policy.Policy`,
`orionis.auth.authorization.registry.PolicyRegistry`. Fuentes:
[authorizer](../authorization/authorizer.py), [policy](../authorization/policy.py),
[registry](../authorization/registry.py).

```python
class Authorizer(IAuthorizer):
    def __init__(self, app: IApplication) -> None:
    def registry(self) -> PolicyRegistry:
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
    async def can(
        self,
        context: IAuthenticationContext,
        permission: str,
    ) -> bool:
    async def canAny(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
    async def canAll(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
    async def hasRole(
        self,
        context: IAuthenticationContext,
        role: str,
    ) -> bool:
    async def allows(
        self,
        context: IAuthenticationContext,
        ability: str,
        resource: object,
    ) -> bool:

class Policy(IPolicy):
    async def before(self, identity: object, ability: str) -> bool | None:

class PolicyRegistry:
    def __init__(self) -> None:
    def register(self, resource: type, policy: type[IPolicy]) -> None:
    def policyFor(self, resource: type) -> type[IPolicy] | None:
    def bindings(self) -> dict[type, type[IPolicy]]:
```

Las operaciones de permiso/rol deniegan a invitados sin cargar snapshot y vuelven
a comprobar autenticación después de esperarlo. `canAny()`/`canAll()` usan
`any()`/`all()` con cortocircuito sobre el iterable: para un contexto autenticado
la entrada vacía da false/true respectivamente, pero ambas dan false a invitados.
No copian el iterable suministrado; un iterador de un solo uso puede consumirse
solo parcialmente.

`allows()` deniega a invitados, identificadores inválidos, abilities con prefijo
guion bajo, `before` y abilities ausentes de una restricción no nula antes de
construir la policy. Resuelve la clase del recurso o el tipo de instancia.
Una policy ausente lanza `PolicyNotFoundException`. Cada evaluación espera
`app.build(policy_class)` para crear una policy nueva.

El hook `before` siempre se espera. `None` continúa; cualquier otro valor detiene
la evaluación, pero solo `True` literal concede. Solo después de ese hook se exige
un handler de ability invocable; si falta entonces, lanza `PolicyNotFoundException`.
Los handlers reciben identidad y recurso y pueden devolver síncronamente o
producir un awaitable. De nuevo solo `True` literal concede, y el contexto debe
seguir exponiendo el mismo objeto identidad después de evaluar. Hooks, DI y
handlers pueden propagar sus propias excepciones. `Policy.before()` devuelve
`None` por defecto; sobrescribirlo con un hook síncrono no corresponde a este
contrato esperado. Un hook que concede puede omitir un handler ausente, pero no
las restricciones de credencial comprobadas antes.

`registry()` devuelve el registro vivo. `register()` exige una clase de recurso
y una subclase de `IPolicy` o lanza `TypeError`, reemplaza cualquier binding
anterior y limpia toda la caché de búsquedas. `policyFor()` recorre el MRO del
recurso al fallar caché y guarda una clase policy o `None`; la caché no declara
límite de tamaño. `bindings()` devuelve una copia superficial del diccionario.
No se cachean instancias de policy.

### PermissionRegistrar y DatabasePermissionRepository

Imports: `orionis.auth.authorization.registrar.PermissionRegistrar` y
`orionis.auth.authorization.repository.DatabasePermissionRepository`.
Fuentes: [registrar](../authorization/registrar.py),
[repository](../authorization/repository.py).

```python
class PermissionRegistrar:
    def __init__(self, db: IQueryBuilder) -> None:
    async def createPermission(self, name: str) -> object:
    async def createRole(self, name: str) -> object:
    async def givePermissionTo(
        self,
        authorizable: IAuthorizable,
        *permissions: str,
    ) -> None:
    async def revokePermissionFrom(
        self,
        authorizable: IAuthorizable,
        *permissions: str,
    ) -> None:
    async def assignRole(
        self,
        authorizable: IAuthorizable,
        *roles: str,
    ) -> None:
    async def removeRole(
        self,
        authorizable: IAuthorizable,
        *roles: str,
    ) -> None:
    async def grantToRole(self, role: str, *permissions: str) -> None:
    async def revokeFromRole(self, role: str, *permissions: str) -> None:

class DatabasePermissionRepository(IPermissionRepository):
    def __init__(self, db: IQueryBuilder) -> None:
    async def loadFor(
        self,
        authorizable: IAuthorizable,
    ) -> tuple[frozenset[str], frozenset[str]]:
```

Crear devuelve el ID de una fila existente/nueva. Los nombres de creación deben
ser cadenas no vacías, sin padding y de hasta 255 caracteres; si no, lanzan
`AuthException`. Una inserción perdida se recupera dentro de transacción/savepoint
solo si existe la fila correspondiente; si no, se propaga `QueryException`.
Si falta el ID generado se busca por nombre; no poder recuperar un ID lanza
`AuthException`.

Los métodos de grant/assign crean filas nombradas ausentes y adjuntan pivotes
polimórficos. Las claves compuestas permiten recuperar asignaciones duplicadas
tras verificar una fila idéntica. Revoke/remove eliminan solo pivotes coincidentes
e ignoran nombres desconocidos; no eliminan definiciones de roles/permisos.
Los métodos sobre propietario lo validan incluso sin nombres variádicos.
`grantToRole()` sigue creando/resolviendo el rol con una lista de permisos vacía;
`revokeFromRole()` busca primero el rol. Las operaciones sobre varios nombres son
secuenciales, no una única transacción todo-o-nada que cubra el método entero.
Los cambios del registrar no invalidan snapshots de contextos ya existentes.

`loadFor()` normaliza al propietario; un `AuthException` de esa normalización
produce dos conjuntos vacíos sin consultar. Los demás errores de accessor/query
se propagan. Una sentencia UNION recoge nombres de rol, permisos directos y
permisos heredados de rol; el resultado se materializa en `frozenset`s de permisos
y roles, en ese orden. No tiene caché de permisos propia y usa los cinco nombres
fijos de tabla, no un namespace de guard configurable. Los roles no tienen jerarquía.

### AuthManager

Importar `orionis.auth.manager.AuthManager`. Fuente: [manager.py](../manager.py).
La fachada externa `orionis.support.facades.auth.Auth` expone este contrato tras
el boot de su proveedor; no es la entidad de configuración también llamada Auth.

```python
class AuthManager(IAuthManager):
    def __init__(
        self,
        app: IApplication,
        authorizer: IAuthorizer,
        permissions: IPermissionRepository,
        session_guard: ISessionGuard,
        token_guard: TokenGuard,
        tokens: IAccessTokenRepository,
    ) -> None:
    def context(self) -> IAuthenticationContext:
    def user(self) -> IAuthenticatable | None:
    def identifier(self) -> object | None:
    def check(self) -> bool:
    def guest(self) -> bool:
    def guard(self, name: str | None = None) -> IGuard:
    async def attempt(
        self, credentials: Mapping[str, object], *, remember: bool = False,
    ) -> bool:
    async def login(self, identity: IAuthenticatable) -> None:
    async def logout(self) -> None:
    async def authorization(self) -> IAuthorizationSnapshot:
    async def can(self, permission: str) -> bool:
    async def cannot(self, permission: str) -> bool:
    async def canAny(self, permissions: Iterable[str]) -> bool:
    async def canAll(self, permissions: Iterable[str]) -> bool:
    async def hasRole(self, role: str) -> bool:
    async def authorize(self, permission: str) -> None:
    async def allows(self, ability: str, resource: object) -> bool:
    async def denies(self, ability: str, resource: object) -> bool:
    async def authorizeResource(self, ability: str, resource: object) -> None:
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
    async def createToken(
        self,
        name: str,
        *,
        tokenable: IAuthorizable | None = None,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
    async def revokeCurrentToken(self) -> bool:
```

El constructor guarda los dos guards inyectados por sus nombres y un default
configurado. No hay un método público de registro de guards. `guard()` usa el
default para `None` u otros nombres falsy y lanza `GuardNotFoundException` si la
clave no existe. Los métodos de estado son síncronos y consultan el contexto
actual; fuera de un scope observan a un invitado.

`attempt()`, `login()` y `logout()` requieren un scope activo con un valor bajo la
clave real `Request` o lanzan `AuthException`. Cooperan mediante
`authentication_lock()` y siempre usan el guard de sesión, sin considerar el
default ni el guard resuelto antes. Attempt convierte el resultado identidad/`None`
del guard en booleano; un attempt fallido no reemplaza el contexto existente.
Attempt/login exitosos vinculan un contexto de sesión nuevo con repositorio de
permisos. Logout vincula un contexto invitado de sesión tras el logout del guard.
Las transiciones directas del gestor no aplican la prohibición de cambiar guard
del middleware resolver.

Los métodos de autorización delegan en contexto/authorizer. `cannot()` y `denies()`
niegan sus comprobaciones booleanas correspondientes. `authorize()`/`authorizeResource()`
devuelven `None` al permitir, lanzan `AuthenticationException` a invitados o
`AuthorizationException` a identidades autenticadas denegadas. Los fallos de
búsqueda de policy y dependencias permanecen visibles. `registerPolicy()` muta
el registro del authorizer.

`createToken()` rechaza un contexto con ID de credencial no nulo mediante
`AuthorizationException`, incluso si se proporciona propietario explícito.
En otro caso usa `tokenable` o la identidad actual: su ausencia lanza
`AuthenticationException`; un propietario que no implemente `IAuthorizable` lanza
`AuthException`. Puede usarse un propietario authorizable explícito fuera de una
petición autenticada. Los errores de validación/persistencia del repositorio
se propagan.

`revokeCurrentToken()` devuelve `False` si no hay credencial; en otro caso toma
el bloqueo de transición, vuelve a comprobar la credencial, la revoca y vincula un
contexto invitado que conserva el guard. Se elimina identidad incluso si revoke
devuelve `False`; una excepción del repositorio impide ese nuevo binding.

### Middlewares

Las diez clases se reexportan desde `orionis.auth.middleware`.
Archivos fuente y sufijos de import de definición:
[resolve_identity](../middleware/resolve_identity.py),
[authenticate](../middleware/authenticate.py), [guest](../middleware/guest.py),
[authorize](../middleware/authorize.py), [policy](../middleware/policy.py).
Heredan [BaseMiddleware](../../http/middleware.py); `call_next` es un callable
async sin argumentos que devuelve `Response`.

```python
class ResolveIdentityMiddleware(BaseMiddleware):
    guard: ClassVar[str | None] = None
    def __init__(
        self,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:

class ResolveSessionIdentityMiddleware(ResolveIdentityMiddleware):
    guard: ClassVar[str | None] = Guards.SESSION.value
    async def handle(self, request: Request, call_next: NextCallable) -> Response:

class ResolveTokenIdentityMiddleware(ResolveIdentityMiddleware):
    guard: ClassVar[str | None] = Guards.TOKEN.value

class AuthenticateMiddleware(ResolveIdentityMiddleware):
    cache_control: ClassVar[str | None] = "no-store, private"
    def __init__(
        self,
        app: IApplication,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:

class AuthenticateSessionMiddleware(AuthenticateMiddleware):
    guard: ClassVar[str | None] = Guards.SESSION.value

class AuthenticateTokenMiddleware(AuthenticateMiddleware):
    guard: ClassVar[str | None] = Guards.TOKEN.value

class GuestMiddleware(ResolveIdentityMiddleware):
    guard: ClassVar[str | None] = Guards.SESSION.value
    redirect_to: ClassVar[str | None] = None
    def __init__(
        self,
        app: IApplication,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
    async def handle(self, request: Request, call_next: NextCallable) -> Response:

class RequirePermissionMiddleware(BaseMiddleware):
    permissions: ClassVar[tuple[str, ...]] = ()
    requires_all: ClassVar[bool] = True
    def __init__(self, authorizer: IAuthorizer) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:

class RequireRoleMiddleware(BaseMiddleware):
    roles: ClassVar[tuple[str, ...]] = ()
    requires_all: ClassVar[bool] = False
    def __init__(self, authorizer: IAuthorizer) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:

class RequirePolicyMiddleware(BaseMiddleware):
    ability: ClassVar[str] = ""
    resource: ClassVar[type | None] = None
    def __init__(self, authorizer: IAuthorizer) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
```

Las variantes heredan constructor/handler de la base salvo cuando se muestran
explícitamente. Las variables de clase definen restricciones; las instancias
tienen slots. Declarar una subclase real e importable corresponde al
[router](../../http/routes/router.py) basado en clases y a la
[caché de rutas](../../http/routes/route_cache.py), no a pasar una instancia
de middleware parametrizada.

| Clase/grupo | Comportamiento y fallos |
|---|---|
| `ResolveIdentityMiddleware` | Bajo el bloqueo de transición, elige guard explícito, guard del contexto actual o default del gestor. Resolver el mismo guard reutiliza resultados autenticados e invitados. Cambiar un contexto autenticado a otro guard lanza `AuthenticationException`. Sin scope lanza `AuthException`; guard desconocido propaga `GuardNotFoundException`. Vincula contexto resuelto/invitado y llama a la siguiente capa. |
| `ResolveSessionIdentityMiddleware` | Fija `"session"`, hereda resolución y aplica cookies persistentes encoladas tras el retorno exitoso de las capas posteriores. No aplica ese hook si una capa posterior lanza. |
| `ResolveTokenIdentityMiddleware` | Fija `"token"` y hereda el handler que permite invitados. |
| `AuthenticateMiddleware` y variantes | Exigen identidad. Un navegador invitado con guard de sesión y redirect configurado recibe 302; invitados JSON/AJAX y de token lanzan `AuthenticationException`. Las respuestas devueltas por capas posteriores/redirect reciben Cache-Control configurado si es truthy. Las excepciones no pasan por ese paso de cabecera. |
| `GuestMiddleware` | Fija sesión por defecto. Los invitados continúan. Los clientes JSON/AJAX autenticados lanzan `AuthorizationException`; los demás autenticados reciben redirect al home. El destino es el override de clase, home configurado o fallback. |
| `RequirePermissionMiddleware` | Permisos vacíos lanzan `AuthConfigurationException` antes de comprobar identidad. Invitados lanzan `AuthenticationException`; fallos de todos/alguno lanzan `AuthorizationException`. Por defecto exige todos. No resuelve un guard por sí mismo. |
| `RequireRoleMiddleware` | Roles/configuración vacíos e invitados siguen el mismo orden de errores. Cualquier abilities no nulo, incluido un conjunto vacío, lanza `AuthorizationException`. Por defecto acepta algún rol; modo all corta al faltar uno. |
| `RequirePolicyMiddleware` | Ability/recurso ausentes lanzan `AuthConfigurationException`; invitados lanzan `AuthenticationException`; abilities denegadas lanzan `AuthorizationException`. Pasa la clase de recurso declarada al authorizer; policies/handlers ausentes pueden propagar `PolicyNotFoundException`. |

Solo el grupo authenticate añade su Cache-Control de protección. La resolución
pública, gates de rol/permiso/policy y redirects de invitado no añaden esa cabecera
de manera independiente. Las capas de identidad del kernel son separadas de las
exclusiones de middleware de ruta; la resolución API no inicia sesión.

### PasswordBroker

Importar `orionis.auth.passwords.broker.PasswordBroker`; el inicializador de
passwords no lo reexporta. Fuente: [broker.py](../passwords/broker.py).

```python
class PasswordBroker:
    def __init__(
        self, app: IApplication, db: IQueryBuilder, hashing: IHashManager,
    ) -> None:
    async def issue(self, email: str) -> tuple[Model, str] | None:
    async def valid(self, email: str, token: str) -> bool:
    async def reset(self, email: str, token: str, password: str) -> Model | None:
```

Los campos públicos sin anotación de instancia son `PasswordBroker.settings`,
`PasswordBroker.model`, `PasswordBroker.db`, `PasswordBroker.hashing` y
`PasswordBroker.tokens`: settings validados, modelo de identidad resuelto
inmediatamente, gateway seleccionado para su conexión, hasher inyectado y
repositorio de tokens de acceso. Son referencias mutables; el broker no declara
slots. Los fallos de import/configuración del modelo pueden ocurrir al construir.

Las tres operaciones eliminan espacios periféricos y convierten el correo a
minúsculas. A diferencia de la búsqueda de credenciales, consultan la columna
literal `email` independientemente del username configurado. `issue()` devuelve
`None` para identidades desconocidas o cooldown no transcurrido. El valor emitido
es `(identity, plain_reset_token)`; se guardan digest, ID canónico, fingerprint
de contraseña y segundos Unix de creación. La primera inserción usa la clave
primaria email; las posteriores solo actualizan una fila anterior al throttle.
Un `QueryException` capturado se absorbe solo si ahora existe una fila para el
correo; los demás fallos SQL se propagan. Las filas consumidas conservan cooldown.

`valid()` no consume un token. Requiere un secreto URL-safe de exactamente 43
caracteres, digest coincidente, creación estrictamente posterior al límite de
vencimiento, el mismo ID de cuenta actual y fingerprint de contraseña sin cambios.
Valores inválidos/obsoletos/vencidos devuelven `False`; los fallos de dependencias
siguen visibles. Ni emitir ni validar comprueba por su cuenta activación de cuenta.

`reset()` resuelve la credencial, calcula el hash de reemplazo antes de abrir una
transacción y después pone el token a null condicionalmente y actualiza la
contraseña de la misma cuenta solo si aún coincide su hash anterior. Limpia
`remember_token` cuando el modelo declara esa columna y revoca tokens de acceso
si la identidad implementa `IAuthorizable`. Una actualización de contraseña
obsoleta lanza una excepción privada que revierte y se convierte en `None`;
los demás fallos se propagan con rollback. Una credencial consumida/inválida
devuelve `None`.

**Discrepancia observada:** la docstring describe una identidad actualizada como
resultado, pero se devuelve la instancia cargada antes sin refrescar atributos.
Hay que consultar otra vez la identidad persistida para inspeccionar contraseña
o estado remember nuevos. El ejemplo completo verifica esta distinción. El broker
no comprueba fortaleza/confirmación de contraseña ni entrega correos. Los
fingerprints de sesión existentes rechazan la contraseña cambiada en una
resolución posterior; el broker no enumera ni elimina registros del session store.

### AuthProvider

Importar `orionis.auth.provider.AuthProvider`. Fuente: [provider.py](../provider.py).
Ciclo de vida base: [ServiceProvider](../../container/providers/service_provider.py).

```python
class AuthProvider(ServiceProvider):
    def register(self) -> None:
    async def boot(self) -> None:
```

El proveedor figura en [CORE_PROVIDER_METADATA](../../foundation/core_providers.py)
y no es deferrable. `register()` declara exactamente estos bindings:

| Lifetime | Contrato/clave e implementación |
|---|---|
| Scoped | `IAuthenticationContext` a `AuthenticationContext`. |
| Singleton | `IIdentityProvider` a `ModelIdentityProvider`; `IPermissionRepository` a `DatabasePermissionRepository`; `IAuthorizer` a `Authorizer`; `PermissionRegistrar` a sí mismo; `IAccessTokenRepository` a `AccessTokenRepository`; `ISessionGuard` a `SessionGuard`; `TokenGuard` a sí mismo; `IAuthManager` a `AuthManager`. |

`boot()` espera `Auth.pin()`. Importar un paquete o registrar bindings no fija
la fachada. El [Application.boot inspeccionado](../../foundation/application.py)
crea la aplicación y arranca proveedores eager para uso headless; el inicio
HTTP/CLI también los arranca. Tras fijar, los métodos sync del gestor siguen
siendo sync y los async deben seguir esperándose. El guard construye `RememberMe`;
`PasswordBroker` no se registra explícitamente por AuthProvider.

### Excepciones

Todos los imports de definición usan `orionis.auth.exceptions`; los ocho nombres
se reexportan desde la raíz. Fuente: [exceptions.py](../exceptions.py).

```python
class AuthException(Exception):
class AuthConfigurationException(AuthException):
class AuthenticationException(AuthException):
class AuthorizationException(AuthException):
class GuardNotFoundException(AuthException):
class IdentityProviderException(AuthException):
class PolicyNotFoundException(AuthException):
class TokenException(AuthException):
```

Heredan el constructor estándar y no declaran campos adicionales. Las condiciones
concretas se describen con la API que las lanza. En particular,
`AuthConfigurationException` se usa explícitamente en declaraciones vacías de
middleware, no para cualquier error de configuración; los validadores de entidad
también lanzan `TypeError` o `ValueError`. Los errores ORM/hash/import no se
convierten automáticamente en `AuthException`.

El [handler inspeccionado](../../failure/base/handler.py) mapea
`AuthenticationException` y subclases a 401, y `AuthorizationException` y
subclases a 403. Selecciona JSON usando `request.wantsJson()` y añade
`WWW-Authenticate: Bearer` en fallos de autenticación con guard token actual.
Un redirect del middleware de autenticación es una respuesta alternativa,
no un mapeo de excepción a estado.

### Contratos

El [inicializador de contratos](../contracts/__init__.py) reexporta las doce ABCs.
Declaran slots vacíos. Los métodos abstractos describen puntos de extensión, no
implementaciones concretas de base de datos/scope; instanciar una implementación
abstracta incompleta lanza el `TypeError` estándar. El comportamiento concreto
relevante se documentó arriba. Los siguientes fragmentos incluyen cada miembro.

`orionis.auth.contracts.authenticatable.IAuthenticatable`
([fuente](../contracts/authenticatable.py)) y
`orionis.auth.contracts.authorizable.IAuthorizable`
([fuente](../contracts/authorizable.py)):

```python
class IAuthenticatable(ABC):
    @abstractmethod
    def getAuthIdentifierName(self) -> str:
    @abstractmethod
    def getAuthIdentifier(self) -> object:
    @abstractmethod
    def getAuthPassword(self) -> str:

class IAuthorizable(ABC):
    @abstractmethod
    def getAuthorizableType(self) -> str:
    @abstractmethod
    def getAuthorizableId(self) -> object:
```

`orionis.auth.contracts.guard.IGuard` ([fuente](../contracts/guard.py)) y
`orionis.auth.contracts.session_guard.ISessionGuard`
([fuente](../contracts/session_guard.py)); el segundo hereda nombre/resolución:

```python
class IGuard(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
    @abstractmethod
    async def resolve(self, request: Request) -> GuardResult | None:

class ISessionGuard(IGuard):
    @abstractmethod
    async def attempt(
        self,
        request: Request,
        credentials: Mapping[str, object],
        *, remember: bool = False,
    ) -> IAuthenticatable | None:
    @abstractmethod
    def login(self, request: Request, identity: IAuthenticatable) -> None:
    @abstractmethod
    async def logout(self, request: Request) -> None:
```

`orionis.auth.contracts.identity_provider.IIdentityProvider`
([fuente](../contracts/identity_provider.py)). Solo los tres últimos métodos de
abajo son abstractos. `updateRememberToken()` tiene cuerpo base que devuelve
`False`; la implementación opcional documentada debe comparar contraseña y
credencial esperada y exigir identidad activa al emitir un reemplazo no nulo.

```python
class IIdentityProvider(ABC):
    async def updateRememberToken(
        self,
        identity: IAuthenticatable,
        expected: str | None,
        token: str | None,
    ) -> bool:
    @abstractmethod
    async def retrieveById(self, identifier: object) -> IAuthenticatable | None:
    @abstractmethod
    async def retrieveByCredentials(
        self,
        credentials: Mapping[str, object],
    ) -> IAuthenticatable | None:
    @abstractmethod
    async def validateCredentials(
        self,
        identity: IAuthenticatable | None,
        credentials: Mapping[str, object],
    ) -> bool:
```

`orionis.auth.contracts.context.IAuthenticationContext`
([fuente](../contracts/context.py)) y
`orionis.auth.contracts.snapshot.IAuthorizationSnapshot`
([fuente](../contracts/snapshot.py)); las propiedades solo tienen getter:

```python
class IAuthenticationContext(ABC):
    @property
    @abstractmethod
    def identity(self) -> IAuthenticatable | None:
    @property
    @abstractmethod
    def guard(self) -> str | None:
    @property
    @abstractmethod
    def abilities(self) -> frozenset[str] | None:
    @property
    @abstractmethod
    def credentialId(self) -> object | None:
    @property
    @abstractmethod
    def isAuthenticated(self) -> bool:
    @property
    @abstractmethod
    def isGuest(self) -> bool:
    @abstractmethod
    def identifier(self) -> object | None:
    @abstractmethod
    async def authorization(self) -> IAuthorizationSnapshot:

class IAuthorizationSnapshot(ABC):
    @property
    @abstractmethod
    def permissions(self) -> frozenset[str]:
    @property
    @abstractmethod
    def roles(self) -> frozenset[str]:
    @property
    @abstractmethod
    def abilities(self) -> frozenset[str] | None:
    @abstractmethod
    def can(self, permission: str) -> bool:
    @abstractmethod
    def hasRole(self, role: str) -> bool:
```

`orionis.auth.contracts.permission_repository.IPermissionRepository`
([fuente](../contracts/permission_repository.py)),
`orionis.auth.contracts.policy.IPolicy` ([fuente](../contracts/policy.py)) y
`orionis.auth.contracts.authorizer.IAuthorizer`
([fuente](../contracts/authorizer.py)):

```python
class IPermissionRepository(ABC):
    @abstractmethod
    async def loadFor(
        self,
        authorizable: IAuthorizable,
    ) -> tuple[frozenset[str], frozenset[str]]:

class IPolicy(ABC):
    @abstractmethod
    async def before(self, identity: object, ability: str) -> bool | None:

class IAuthorizer(ABC):
    @abstractmethod
    async def can(
        self,
        context: IAuthenticationContext,
        permission: str,
    ) -> bool:
    @abstractmethod
    async def canAny(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
    @abstractmethod
    async def canAll(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
    @abstractmethod
    async def hasRole(
        self,
        context: IAuthenticationContext,
        role: str,
    ) -> bool:
    @abstractmethod
    async def allows(
        self,
        context: IAuthenticationContext,
        ability: str,
        resource: object,
    ) -> bool:
    @abstractmethod
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
```

`orionis.auth.contracts.token_repository.IAccessTokenRepository`
([fuente](../contracts/token_repository.py)):

```python
class IAccessTokenRepository(ABC):
    @abstractmethod
    async def create(
        self,
        tokenable: IAuthorizable,
        name: str,
        *,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
    @abstractmethod
    async def findByPlainText(self, plain_text: str) -> AccessToken | None:
    @abstractmethod
    async def touch(self, token_id: object) -> bool:
    @abstractmethod
    async def revoke(self, token_id: object) -> bool:
    @abstractmethod
    async def revokeAll(self, tokenable: IAuthorizable) -> int:
    @abstractmethod
    async def purgeExpired(self) -> int:
```

`orionis.auth.contracts.manager.IAuthManager` ([fuente](../contracts/manager.py)):

```python
class IAuthManager(ABC):
    @abstractmethod
    def context(self) -> IAuthenticationContext:
    @abstractmethod
    def user(self) -> IAuthenticatable | None:
    @abstractmethod
    def identifier(self) -> object | None:
    @abstractmethod
    def check(self) -> bool:
    @abstractmethod
    def guest(self) -> bool:
    @abstractmethod
    def guard(self, name: str | None = None) -> IGuard:
    @abstractmethod
    async def attempt(
        self, credentials: Mapping[str, object], *, remember: bool = False,
    ) -> bool:
    @abstractmethod
    async def login(self, identity: IAuthenticatable) -> None:
    @abstractmethod
    async def logout(self) -> None:
    @abstractmethod
    async def authorization(self) -> IAuthorizationSnapshot:
    @abstractmethod
    async def can(self, permission: str) -> bool:
    @abstractmethod
    async def cannot(self, permission: str) -> bool:
    @abstractmethod
    async def canAny(self, permissions: Iterable[str]) -> bool:
    @abstractmethod
    async def canAll(self, permissions: Iterable[str]) -> bool:
    @abstractmethod
    async def hasRole(self, role: str) -> bool:
    @abstractmethod
    async def authorize(self, permission: str) -> None:
    @abstractmethod
    async def allows(self, ability: str, resource: object) -> bool:
    @abstractmethod
    async def denies(self, ability: str, resource: object) -> bool:
    @abstractmethod
    async def authorizeResource(self, ability: str, resource: object) -> None:
    @abstractmethod
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
    @abstractmethod
    async def createToken(
        self,
        name: str,
        *,
        tokenable: IAuthorizable | None = None,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
    @abstractmethod
    async def revokeCurrentToken(self) -> bool:
```

## Ejemplos de uso

Cada bloque es un script independiente para Python 3.14+ con el framework
instalado o este checkout en `PYTHONPATH`. Todos se comprobaron sintácticamente,
resolvieron sus imports Orionis hacia el checkout local inspeccionado y se
ejecutaron correctamente en CPython 3.14.6/Windows. Los dos primeros no escriben
recursos; los de base de datos cambian a un directorio temporal propio antes de
importar configuración de servicios. Los dobles mínimos de petición/aplicación
son explícitos, no transportes HTTP completos. Los costes de hashing bajos de
abajo son preparación de pruebas, no configuración de producción.

### Contexto, snapshot y una excepción real

Ocho comprobaciones concurrentes reutilizan una carga de repositorio. Reemplazar
el contexto vuelve anónima la referencia anterior; vincular sin scope lanza
`AuthException`. Estado: **ejecutado correctamente**.

```python
import asyncio
from orionis.auth import Authenticatable, Authorizable, AuthenticationContext
from orionis.auth.authorization import EMPTY_SNAPSHOT, AuthorizationSnapshot
from orionis.auth.context import bind_auth_context, current_auth_context
from orionis.auth.contracts import IAuthorizable, IPermissionRepository
from orionis.auth.exceptions import AuthException
from orionis.container.context.manager import ScopeManager


class Identity(Authenticatable, Authorizable):
    __slots__ = ("id",)

    def __init__(self) -> None:
        self.id = 7


class Permissions(IPermissionRepository):
    __slots__ = ("loads",)

    def __init__(self) -> None:
        self.loads = 0

    async def loadFor(
        self, authorizable: IAuthorizable,
    ) -> tuple[frozenset[str], frozenset[str]]:
        assert authorizable.getAuthorizableId() == 7
        self.loads += 1
        await asyncio.sleep(0)
        return frozenset({"posts.read", "posts.update"}), frozenset({"editor"})


async def main() -> None:
    try:
        bind_auth_context(AuthenticationContext())
    except AuthException:
        assert current_auth_context().isGuest
    else:
        raise AssertionError("Binding without a scope should fail")

    repository = Permissions()
    context = AuthenticationContext(
        identity=Identity(), guard="token", abilities=["posts.read"],
        repository=repository, credential_id=10,
    )
    async with ScopeManager():
        bind_auth_context(context)
        snapshots = await asyncio.gather(
            *(context.authorization() for _ in range(8)),
        )
        assert repository.loads == 1
        assert all(snapshot is snapshots[0] for snapshot in snapshots)
        assert snapshots[0].can("posts.read")
        assert not snapshots[0].can("posts.update")
        assert snapshots[0].hasRole("editor")
        assert context.identifier() == 7
        bind_auth_context(AuthenticationContext(guard="token"))
        assert context.identity is None and context.credentialId is None
        assert await context.authorization() is EMPTY_SNAPSHOT

    assert current_auth_context().isGuest
    assert AuthorizationSnapshot((), (), ()).abilities == frozenset()
    print("Context, snapshot and exception checks passed.")


asyncio.run(main())
```

### Evaluación de policies con el contenedor real

Se evalúa una ability síncrona en una policy nueva construida por el contenedor.
Las restricciones deniegan antes de despachar; un handler ausente sin restricción
lanza `PolicyNotFoundException`. Estado: **ejecutado correctamente**.

```python
import asyncio
from dataclasses import dataclass
from orionis.auth import Authenticatable, AuthenticationContext, Policy
from orionis.auth.authorization.authorizer import Authorizer
from orionis.auth.exceptions import PolicyNotFoundException
from orionis.container.container import Container


class Identity(Authenticatable):
    __slots__ = ()
    id = 7


@dataclass
class Document:
    owner_id: int


class DocumentPolicy(Policy):
    __slots__ = ()

    def update(self, identity: object, resource: Document) -> bool:
        return resource.owner_id == identity.getAuthIdentifier()


async def main() -> None:
    app = Container()
    authorizer = Authorizer(app)
    authorizer.registerPolicy(Document, DocumentPolicy)
    context = AuthenticationContext(identity=Identity(), abilities=["update"])
    async with app.beginScope():
        assert await authorizer.allows(context, "update", Document(7))
        assert not await authorizer.allows(context, "update", Document(8))
        assert not await authorizer.allows(context, "delete", Document(7))
        unrestricted = AuthenticationContext(identity=Identity())
        try:
            await authorizer.allows(unrestricted, "delete", Document(7))
        except PolicyNotFoundException:
            pass
        else:
            raise AssertionError("A missing policy method should fail")
    assert authorizer.registry().policyFor(Document) is DocumentPolicy
    print("Policy and container checks passed.")


asyncio.run(main())
```

### Login de sesión, restauración persistente y logout

Usa modelo, hasher, archivo SQLite, Session y parser de cookies reales con un
doble mínimo de petición HTTPS. Confirma rotación y rechazo de cookie anterior
sin conectar con navegador o servidor. Estado: **ejecutado correctamente**.

```python
import asyncio
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


original_directory = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        from orionis.auth import Authenticatable
        from orionis.auth.guards import SessionGuard
        from orionis.auth.identity import ModelIdentityProvider
        from orionis.auth.remember import apply_remember_cookie
        from orionis.database.connection_manager import ConnectionManager
        from orionis.hashing.hash_manager import HashManager
        from orionis.http.payload.estructures.cookies import Cookies
        from orionis.http.responses import Response
        from orionis.orm import BigInteger, Boolean, Model, String
        from orionis.orm.resolver import ConnectionResolver
        from orionis.session.session import Session

        class Account(Model, Authenticatable):
            __slots__ = ()
            table = "accounts"
            timestamps = False
            fillable = ["email", "password", "active"]
            hidden = ["password", "remember_token"]
            casts = {"active": "bool"}
            id = BigInteger().primary().autoIncrement()
            email = String(255).unique()
            password = String(255)
            active = Boolean()
            remember_token = String(100).nullable()

        class Settings:
            def config(self, key: str) -> object:
                return {
                    "database": {
                        "default": "sqlite",
                        "connections": {"sqlite": {
                            "driver": "sqlite", "database": "auth.sqlite",
                            "prefix": "",
                        }},
                    },
                    "hashing": {
                        "driver": "argon2",
                        "argon2": {"memory": 32, "threads": 1, "time": 1},
                    },
                    "auth.identity.model": f"{__name__}.Account",
                    "auth.remember": {
                        "cookie": "sample_remember", "lifetime": 30,
                        "secure": True,
                    },
                }.get(key)

        def incoming(cookies: object = None) -> SimpleNamespace:
            return SimpleNamespace(
                scheme="https", cookies={} if cookies is None else cookies,
                state=SimpleNamespace(session=Session()),
            )

        async def main() -> None:
            settings = Settings()
            manager = ConnectionManager(settings)
            ConnectionResolver.setManager(manager)
            try:
                await manager.connection().createTable(Account.__meta__.table)
                hashing = HashManager(settings)
                credential = secrets.token_urlsafe(24)
                account = await Account.create({
                    "email": "ada@example.test",
                    "password": await hashing.make(credential), "active": True,
                })
                provider = ModelIdentityProvider(settings, hashing)
                guard = SessionGuard(settings, provider)
                first = incoming()
                identity = await guard.attempt(
                    first, {"email": account.email, "password": credential},
                    remember=True,
                )
                assert identity is not None
                assert first.state.session.wantsRegenerate
                assert first.state.session.get("_auth_identifier") == str(account.id)
                response = Response()
                apply_remember_cookie(first, response)
                header = response.getHeader("set-cookie")[0]
                assert "Secure" in header and "HttpOnly" in header
                cookie = Cookies(header.split(";", 1)[0])
                second = incoming(cookie)
                restored = await guard.resolve(second)
                assert restored is not None and restored.identity.id == account.id
                assert await guard.resolve(incoming(cookie)) is None
                await guard.logout(second)
                assert second.state.session.invalidated
                assert (await Account.find(account.id)).remember_token is None
                print("Session, remember-cookie and logout checks passed.")
            finally:
                await manager.disconnect()
                ConnectionResolver.clear()

        asyncio.run(main())
    finally:
        os.chdir(original_directory)
```

### RBAC, token restringido, middleware y reset de contraseña

El script prepara sus siete tablas auxiliares y el modelo de identidad. Combina
login de sesión mediante el gestor, permisos de rol, resolución de token
restringido, middleware de permiso, revocación actual y reset de contraseña de un
solo uso. Comprueba el cambio persistido, rechazo de sesión anterior y revocación
de tokens; desconecta antes de eliminar SQLite. Estado: **ejecutado correctamente**.

```python
import asyncio
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


original_directory = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        from orionis.auth import Authenticatable, Authorizable
        from orionis.auth.authorization.authorizer import Authorizer
        from orionis.auth.authorization.registrar import PermissionRegistrar
        from orionis.auth.authorization.repository import DatabasePermissionRepository
        from orionis.auth.exceptions import AuthorizationException
        from orionis.auth.guards import SessionGuard, TokenGuard
        from orionis.auth.identity import ModelIdentityProvider
        from orionis.auth.manager import AuthManager
        from orionis.auth.middleware import (
            RequirePermissionMiddleware, ResolveTokenIdentityMiddleware,
        )
        from orionis.auth.passwords.broker import PasswordBroker
        from orionis.auth.tokens import AccessTokenRepository
        from orionis.container.context.manager import ScopeManager
        from orionis.database.connection_manager import ConnectionManager
        from orionis.hashing.hash_manager import HashManager
        from orionis.http.request import Request
        from orionis.http.responses import Response
        from orionis.orm import BigInteger, Boolean, DateTime, Model, String, Text
        from orionis.orm.query_builder import QueryBuilder
        from orionis.orm.resolver import ConnectionResolver
        from orionis.orm.schema.column import ColumnDefinition
        from orionis.orm.schema.table import TableDefinition
        from orionis.session.session import Session

        class Account(Model, Authenticatable, Authorizable):
            __slots__ = ()
            table = "accounts"
            timestamps = False
            fillable = ["email", "password", "active"]
            casts = {"active": "bool"}
            id = BigInteger().primary().autoIncrement()
            email = String(255).unique()
            password = String(255)
            active = Boolean()
            remember_token = String(100).nullable()

        class Settings:
            def config(self, key: str) -> object:
                return {
                    "database": {
                        "default": "sqlite",
                        "connections": {"sqlite": {
                            "driver": "sqlite", "database": "workflow.sqlite",
                            "prefix": "",
                        }},
                    },
                    "hashing": {
                        "driver": "argon2",
                        "argon2": {"memory": 32, "threads": 1, "time": 1},
                    },
                    "auth.identity.model": f"{__name__}.Account",
                    "auth.passwords": {
                        "table": "password_reset_tokens",
                        "expiration": 15, "throttle": 60,
                    },
                }.get(key)

        class Readers(RequirePermissionMiddleware):
            __slots__ = ()
            permissions = ("posts.read",)

        def definition(
            name: str, columns: dict[str, ColumnDefinition],
            primary: tuple[str, ...],
        ) -> TableDefinition:
            for column_name, column in columns.items():
                column.name = column_name
            return TableDefinition(
                name=name, columns=columns,
                primary_key=primary[0] if len(primary) == 1 else None,
                composite_primary_key=primary if len(primary) > 1 else None,
            )

        async def main() -> None:
            settings = Settings()
            manager = ConnectionManager(settings)
            ConnectionResolver.setManager(manager)
            try:
                connection = manager.connection()
                await connection.createTable(Account.__meta__.table)
                for name in ("permissions", "roles"):
                    await connection.createTable(definition(name, {
                        "id": BigInteger().primary().autoIncrement(),
                        "name": String(255).unique(),
                    }, ("id",)))
                for name, foreign in (
                    ("model_has_permissions", "permission_id"),
                    ("model_has_roles", "role_id"),
                ):
                    await connection.createTable(definition(name, {
                        foreign: BigInteger(), "model_type": String(255),
                        "model_id": String(255),
                    }, (foreign, "model_id", "model_type")))
                await connection.createTable(definition("role_has_permissions", {
                    "permission_id": BigInteger(), "role_id": BigInteger(),
                }, ("permission_id", "role_id")))
                await connection.createTable(definition("personal_access_tokens", {
                    "id": BigInteger().primary().autoIncrement(),
                    "tokenable_type": String(255), "tokenable_id": String(255),
                    "name": String(255), "token": String(64).unique(),
                    "abilities": Text().nullable(),
                    "expires_at": DateTime().nullable(),
                    "last_used_at": DateTime().nullable(),
                    "revoked_at": DateTime().nullable(),
                    "created_at": DateTime().nullable(),
                    "updated_at": DateTime().nullable(),
                }, ("id",)))
                await connection.createTable(definition("password_reset_tokens", {
                    "email": String(255).primary(), "token": String(64).nullable(),
                    "user_id": String(255), "password_fingerprint": String(64),
                    "created_at": BigInteger(),
                }, ("email",)))
                db = QueryBuilder(manager)
                hashing = HashManager(settings)
                credential = secrets.token_urlsafe(24)
                account = await Account.create({
                    "email": "ada@example.test",
                    "password": await hashing.make(credential), "active": True,
                })
                identities = ModelIdentityProvider(settings, hashing)
                repository = DatabasePermissionRepository(db)
                registrar = PermissionRegistrar(db)
                tokens = AccessTokenRepository(settings, db)
                authorizer = Authorizer(settings)
                session_guard = SessionGuard(settings, identities)
                auth = AuthManager(
                    settings, authorizer, repository, session_guard,
                    TokenGuard(tokens, identities), tokens,
                )
                await registrar.grantToRole("editor", "posts.read", "posts.update")
                await registrar.assignRole(account, "editor")
                web = SimpleNamespace(state=SimpleNamespace(session=Session()))
                async with ScopeManager() as scope:
                    scope[Request] = web
                    await auth.login(account)
                    assert await auth.hasRole("editor")
                    assert await auth.canAll(["posts.read", "posts.update"])
                    issued = await auth.createToken("reader", abilities=["posts.read"])
                request = SimpleNamespace(bearerToken=issued.plain_text)

                async def endpoint() -> Response:
                    return Response("accepted")

                async def secured() -> Response:
                    return await Readers(authorizer).handle(request, endpoint)

                async with ScopeManager():
                    response = await ResolveTokenIdentityMiddleware(
                        auth, repository,
                    ).handle(request, secured)
                    assert response.getBody() == b"accepted"
                    assert not await auth.can("posts.update")
                    try:
                        await auth.createToken("not-allowed")
                    except AuthorizationException:
                        pass
                    else:
                        raise AssertionError("Token sessions cannot issue tokens")
                    assert await auth.revokeCurrentToken()
                    assert auth.guest()
                assert await tokens.findByPlainText(issued.plain_text) is None
                other = await tokens.create(account, "before-reset")
                broker = PasswordBroker(settings, db, hashing)
                issued_reset = await broker.issue(" ADA@example.test ")
                assert issued_reset is not None
                _, reset_token = issued_reset
                assert await broker.valid(account.email, reset_token)
                replacement = secrets.token_urlsafe(24)
                returned = await broker.reset(account.email, reset_token, replacement)
                assert returned is not None
                updated = await Account.find(account.id)
                assert await hashing.check(replacement, updated.getAuthPassword())
                assert returned.getAuthPassword() != updated.getAuthPassword()
                assert await session_guard.resolve(web) is None
                assert await tokens.findByPlainText(other.plain_text) is None
                assert not await broker.valid(account.email, reset_token)
                assert await broker.issue(account.email) is None
                print("RBAC, token, middleware and reset checks passed.")
            finally:
                await manager.disconnect()
                ConnectionResolver.clear()

        asyncio.run(main())
    finally:
        os.chdir(original_directory)
```

## Características de diseño

| Mecanismo observado | Consecuencia concreta y evidencia |
|---|---|
| Exportaciones e import de modelo diferidos | El acceso a un atributo raíz carga/cachea solo su destino declarado; la búsqueda del modelo se difiere salvo en el constructor del broker. Véanse [inicializador](../__init__.py), [proveedor de identidad](../identity/provider.py) y [broker](../passwords/broker.py). |
| Mixins virtuales simples | Los modelos ORM obtienen comportamiento de autenticación sin heredar la metaclase ABC de los contratos. Véanse [Authenticatable](../concerns/authenticatable.py) y [Authorizable](../concerns/authorizable.py). |
| Propiedad de scope y reemplazo de contexto | Los contextos incorporados vinculados retenidos no exponen identidad autenticada después de que su scope/binding deje de ser actual. Véase [contexto](../context/context.py). |
| Propiedades frozenset de solo lectura | Los consumidores públicos de snapshot no pueden asignar propiedades o mutar conjuntos expuestos; las referencias de identidad no se copian. Véase [snapshot](../authorization/snapshot.py). |
| Dataclasses de tokens congeladas y solo por nombre | El decorador genera constructores/comportamiento de campos; la redacción de NewAccessToken es específica de su representación y toDict. Véanse [entidades](../entities/__init__.py). |
| Servicios principales con slots y contratos de slots vacíos | Guards, contextos, snapshots, servicios de identidad/token/RBAC, gestor y middlewares restringen su estado de instancia declarado. RememberMe, PasswordBroker y MustVerifyEmail no declaran slots. Véanse sus declaraciones enlazadas. |
| Tipos de credencial separados | PAT consulta digests de secretos opacos; remember vincula cookie y contraseña; reset vincula destinatario, ID de cuenta y fingerprint de contraseña. No son payloads JWT. Véanse [tokens](../tokens/repository.py), [remember](../remember.py) y [broker](../passwords/broker.py). |

## Rendimiento y concurrencia

- [AuthenticationContext](../context/context.py) materializa abilities al construir,
  pero carga permisos de forma diferida. Un snapshot exitoso se retiene para ese
  contexto; escrituras RBAC posteriores no lo refrescan. El bloqueo cubre tareas
  cooperantes que comparten contexto, con comprobaciones de propiedad después
  de las cargas esperadas.
- [authentication_lock](../context/functions.py) es un bloqueo por scope activo.
  Lo usan transiciones de sesión del gestor, middleware resolver y revocación
  actual. Las llamadas directas a guard/repositorio y bindings explícitos no lo
  adquieren de manera independiente.
- [DatabasePermissionRepository](../authorization/repository.py) construye una
  sentencia UNION y materializa conjuntos. [PermissionRegistrar](../authorization/registrar.py)
  resuelve competencia sobre claves únicas/compuestas con transacciones/savepoints
  y verificación de fila, no con un bloqueo Python global. No hay atomicidad
  implícita de operaciones múltiples.
- [TokenGuard](../guards/token_guard.py) hace búsqueda de token, búsqueda de
  identidad y actualización condicional de uso para una credencial utilizable.
  Evita hashing de contraseña. [AccessTokenRepository](../tokens/repository.py)
  puede añadir búsqueda del ID al crear, materializa abilities antes de limitar
  su recuento y utiliza dos deletes para purgar.
- [RememberMe](../remember.py) rota con actualización condicional de token/contraseña;
  retiene un grant por identidad, no una lista de dispositivos. Quien pierde una
  rotación concurrente no elimina la cookie de reemplazo del ganador.
  [PasswordBroker](../passwords/broker.py) calcula hash antes de su transacción;
  consumo condicional del token y coincidencia de contraseña determinan el commit.
- [PolicyRegistry](../authorization/registry.py) retiene resultados de búsqueda
  de clase/MRO, incluidos fallos, sin límite de tamaño; cada registro los limpia.
  [Authorizer](../authorization/authorizer.py) construye policies por evaluación,
  y los callbacks pueden realizar trabajo bloqueante o I/O propio.
- Una declaración async no demuestra que todo el trabajo sea no bloqueante.
  Generación de secretos, digest, materialización set/JSON e import de clase
  son síncronos; el backend inspeccionado mueve hashing costoso a un hilo worker.

> ⚠️ No especificado en el código fuente: una garantía global del módulo para mutación/registro entre hilos o reutilización de bloqueos y servicios vivos entre event loops. Los bloqueos por scope y escrituras condicionales documentados no establecen esa garantía más amplia.

## Notas de compatibilidad

El [manifiesto](../../../pyproject.toml) declara Python `>=3.14`; el
[lockfile](../../../uv.lock) conserva esa restricción. Se validó con CPython
3.14.6 en Windows. Hay anotaciones nativas de uniones/genéricos incorporados;
muchos tipos solo se importan bajo `TYPE_CHECKING`, aprovechando evaluación
diferida de anotaciones. Estas observaciones no declaran soporte por debajo del
mínimo ni certifican cada versión posterior de Python.

| Dependencia | Restricción declarada | Lockfile y entorno de validación |
|---|---|---|
| `sqlalchemy[asyncio]` | `>=2.0.54,<3.0` | `2.1.1` |
| `aiosqlite` | `>=0.22.1` | `0.22.1` |
| `msgspec` | `>=0.21.1` | `0.22.0` |
| `pwdlib[argon2,bcrypt]` | `>=0.3.1` | `0.3.1` |
| `argon2-cffi` | Backend transitivo de hashing, no restricción directa | `25.1.0` |
| `bcrypt` | Backend transitivo de hashing, no restricción directa | `5.0.0` |
| `python-dotenv` | `>=1.2.3,<2.0` | `1.2.4` |
| `pendulum` | `>=3.2.0,<4.0` | `3.2.0` |

Las versiones bloqueadas/instaladas no son los mínimos soportados. SQLite y
asyncpg son dependencias base; el manifiesto declara extras de base de datos
opcionales para otros drivers. Auth no importa directamente drivers opcionales.
El comportamiento SQL/aislamiento depende de la conexión seleccionada.

Las sesiones antiguas sin fingerprint de contraseña son rechazadas por
[SessionGuard.resolve](../guards/session_guard.py). Los IDs de propietario se
persisten como texto canónico; el proveedor restaura tipos nativos.
La implementación consulta metadatos ORM privados; una clase IAuthenticatable
arbitraria no suministra por sí sola las operaciones ORM necesarias.
Los constructores que arma el contenedor importan dependencias en runtime, no
anotaciones string pospuestas; los fragmentos de referencia no deben convertirse
en firmas alternativas evaluando imports de anotación ausentes.

## Verificación y limitaciones

Comprobaciones realizadas para esta documentación:

| Comprobación | Resultado |
|---|---|
| Identidad y límites | El descubrimiento de paquetes parte de la raíz; se verificó que `orionis/auth` corresponde a `orionis.auth` y su docs directo no es un reparse point. |
| Inventario de fuente | Los 53 archivos Python inspeccionados; 280 entradas públicas documentadas, incluidos contratos, campos, helpers, constantes y dos métodos repr explícitos. |
| Fidelidad de API literal | Tokens de declaraciones comparados con firmas extraídas del AST, incluidos decoradores, anotaciones y defaults, sin evaluarlos. |
| Ejemplos | Cuatro scripts independientes: sintaxis correcta, imports locales correctos, ejecución y aserciones correctas. El código es idéntico en ambos idiomas. |
| Pruebas existentes | 359 descubiertas, 359 resultados PASSED, sin fallos/skips, mediante Application.boot y TestingEngine nativo en una copia temporal de tests/resources. Los imports del código Auth apuntaron a este checkout. |
| Documentación | Comprobados orden de encabezados, equivalencia de bloques, literales técnicos inline, enlaces locales, anclas del índice y ausencia de variables de plantilla pendientes. |
| Skill | Frontmatter YAML de dos campos e identidad derivada del módulo comprobados; referencias locales verificadas. |
| Alcance de escritura | Hashes iniciales/finales incluyen archivos ignorados/no registrados; solo cambiaron los tres documentos autorizados. Se conservaron documentos previos e índice Git. |

El inventario excluye dependencias importadas como APIs Auth independientes,
normalizadores/builders SQL privados, `_StalePassword`, helpers de despacho de
exports como API invocable de consumidor y métodos privados de fork/binding de
contexto. Sus efectos relevantes se explican arriba. Los métodos generados por
dataclass se identifican mediante el decorador, no con firmas literales inventadas.
Cada entrada pública identificada está representada; las exclusiones no son APIs
públicas faltantes.

**Limitación del editor:** los diagnósticos de skills de VS Code exigen que el
nombre coincida con la carpeta (`docs`) e informan varios enlaces con fragmentos
como rutas de archivo literales. El punto de entrada local solicitado conserva
deliberadamente `orionis-auth` en [SKILL.md](SKILL.md); no es un paquete de skill
instalado. Su subconjunto YAML, archivos destino y anclas Markdown superaron las
comprobaciones independientes anteriores. Estos diagnósticos permanecen; no se
cambió configuración ni registro.

**Implementación frente a descripciones previas:** la resolución ordinaria por
sesión/token no impone el test `active is True` del login con credenciales; las
policies comprueban existencia de handler después del hook before; reset devuelve
una identidad no refrescada. La frase de docstring que asegura invitado en consola
es más estrecha que el comportamiento real del helper con scope activo. Estas
distinciones se conservaron, no se corrigieron en el fuente.

> ⚠️ No ejecutado en este entorno: PostgreSQL, MySQL, Oracle y SQL Server reales, cachés externos, transporte de correo, flujos completos navegador/servidor, workers de SO independientes y certificación entre hilos/event loops. Se usaron archivos SQLite aislados y pruebas nativas/de componentes sin servicios o credenciales externas.

> ⚠️ No verificable con los archivos disponibles: garantías de producción sobre el aislamiento, filesystem, reverse proxy, política HTTPS o implementaciones personalizadas de identidad/policy elegidas por la aplicación. No se aportó configuración de despliegue ni ejecución de servicios como evidencia.

No se realizaron benchmarks ni se midió porcentaje de cobertura de ejecución.
Este manual documenta Auth y sus integraciones necesarias, no las APIs de módulos
del framework ajenos al alcance.
