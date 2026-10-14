# Permisos, roles y políticas de recursos

Un permiso identifica una capacidad, como `posts.publish`; un rol agrupa permisos. Una política decide sobre una instancia o clase de recurso. Exigir identidad no exige automáticamente ninguna capacidad.

## Crear y asignar capacidades

`PermissionRegistrar` utiliza las tablas de migraciones auth: `permissions`, `roles`, `model_has_permissions`, `model_has_roles` y `role_has_permissions`.

```python
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.auth.contracts.authorizable import IAuthorizable

async def make_editor(registrar: PermissionRegistrar, user: IAuthorizable):
    await registrar.createPermission("posts.publish")
    await registrar.createRole("editor")
    await registrar.grantToRole("editor", "posts.publish")
    await registrar.assignRole(user, "editor")
```

Obtén el registrar mediante el contenedor y pasa una identidad de origen confiable. `givePermissionTo`/`revokePermissionFrom` manejan permisos directos, `removeRole` quita roles y `revokeFromRole` elimina permisos de un rol. Las restricciones únicas arbitran duplicados concurrentes. `Authorizable.AUTHORIZABLE_TYPE` puede fijar un tipo estable en vez del path de clase; cambiarlo después altera vínculos con registros existentes.

## Proteger una ruta

```python
from orionis.auth.middleware import RequirePermissionMiddleware

class CanPublish(RequirePermissionMiddleware):
    permissions = ("posts.publish",)
    requires_all = True
```

Adjunta `.middleware(CanPublish)`. Declara clases reales, no instancias parametrizadas ni clases locales generadas. Un invitado genera `AuthenticationException`; una identidad sin permiso, `AuthorizationException`. `requires_all=False` admite cualquiera. `RequireRoleMiddleware` usa `roles` y por defecto admite cualquiera; los tokens restringidos no pueden usar solo roles para saltarse límites de capacidades.

En controladores usa `await Auth.can(...)`, `cannot`, `canAny`, `canAll`, `hasRole` o `authorize`, importando Auth desde `orionis.support.facades`. La autorización carga un snapshot inmutable y lo conserva en el contexto; cambios en base de datos no refrescan automáticamente un snapshot ya cargado durante la misma petición.

## Política sobre un recurso

```python
from dataclasses import dataclass
from orionis.auth import Policy

@dataclass
class Article:
    owner_id: int

class ArticlePolicy(Policy):
    async def update(self, identity, article: Article) -> bool:
        return identity.getAuthIdentifier() == article.owner_id
```

Registra `Auth.registerPolicy(Article, ArticlePolicy)` durante boot. En un handler que cargó `article`, llama `await Auth.authorizeResource("update", article)` antes de modificarlo. `allows`/`denies` devuelven booleanos. Para habilidades de clase como `create`, una subclase de `RequirePolicyMiddleware` establece `ability="create"` y `resource=Article`.

Las habilidades pueden ser síncronas o asíncronas y deben devolver `True`. `before` es un hook **asíncrono** que devuelve `True`, `False` o `None` para delegar. La política se resuelve nuevamente mediante el contenedor por evaluación. Política o método ausente produce `PolicyNotFoundException`; nombres privados y `before` no son habilidades invocables.

## Intersección con tokens

`AuthorizationSnapshot(permissions, roles, abilities=None)` no restringe permisos de identidad cuando abilities es `None`; una colección vacía niega todos. Para permisos, el acceso es la intersección de permisos de identidad y abilities. Para políticas, el nombre de habilidad también debe estar en abilities cuando el token las limita, antes de ejecutar `before`. Declarar una cadena en un token no crea privilegios.

Evidencia: [registrar](../../authorization/registrar.py), [authorizer](../../authorization/authorizer.py), [snapshot](../../authorization/snapshot.py). Pruebas: [permisos](../../../../tests/auth/test_permissions.py), [políticas](../../../../tests/auth/test_authorizer.py), [snapshot](../../../../tests/auth/test_snapshot.py). Continúa con [tokens](personal-access-tokens.md).
