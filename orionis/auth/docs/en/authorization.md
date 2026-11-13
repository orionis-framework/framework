# Permissions, roles and resource policies

Permissions name capabilities such as `posts.publish`; roles group permissions. Policies decide access to a resource instance or class. Requiring identity does not automatically require a capability.

## Creating and assigning capabilities

`PermissionRegistrar` uses framework-owned tables: `permissions`, `roles`, `model_has_permissions`, `model_has_roles` and `role_has_permissions`. Prepare them with `python -B reactor auth:migrate`; no application migrations are required for these tables.

Define application-specific role and permission names, assignments, and policies in application code or seeders. The framework supplies the storage, not default privileges or administrator accounts.

```python
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.auth.contracts.authorizable import IAuthorizable


async def make_editor(registrar: PermissionRegistrar, user: IAuthorizable):
    await registrar.createPermission("posts.publish")
    await registrar.createRole("editor")
    await registrar.grantToRole("editor", "posts.publish")
    await registrar.assignRole(user, "editor")
```

Resolve the registrar through the container and pass a trusted identity. `givePermissionTo`/`revokePermissionFrom` manage direct permissions, `removeRole` removes roles and `revokeFromRole` removes role permissions. Unique constraints arbitrate concurrent duplicates. `Authorizable.AUTHORIZABLE_TYPE` can provide a stable type instead of the class path; changing it later changes links to existing rows.

Owner identifiers accept integers or non-empty strings of at most 255 characters; boolean values and oversized integers are rejected before database access. If a failed write is followed by a failed duplicate-check query, the registrar observes the secondary query failure and re-raises the original write error.

## Protecting a route

```python
from orionis.auth.middleware import RequirePermissionMiddleware


class CanPublish(RequirePermissionMiddleware):
    permissions = ("posts.publish",)
    requires_all = True
```

Attach `.middleware(CanPublish)`. Declare real classes rather than parameterized instances or generated local classes. Guests raise `AuthenticationException`; identities lacking permission raise `AuthorizationException`. `requires_all=False` accepts any permission. `RequireRoleMiddleware` uses `roles` and defaults to any; restricted tokens cannot bypass capability limits through role-only checks.

Controllers use `await Auth.can(...)`, `cannot`, `canAny`, `canAll`, `hasRole` or `authorize`, importing Auth from `orionis.support.facades`. Authorization lazily loads an immutable snapshot and retains it in context; database changes do not automatically refresh an already-loaded snapshot in the same request.

## A resource policy

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

Register `Auth.registerPolicy(Article, ArticlePolicy)` at boot. In a handler that loaded `article`, call `await Auth.authorizeResource("update", article)` before modification. `allows`/`denies` return booleans. For class-level abilities such as `create`, subclass `RequirePolicyMiddleware` with `ability="create"` and `resource=Article`.

Ability methods may be synchronous or asynchronous and must return `True`. `before` is an **asynchronous** hook returning `True`, `False` or `None` to delegate. Policies are freshly resolved through the container for each evaluation. Missing policies/methods raise `PolicyNotFoundException`; private names and `before` cannot be invoked as abilities.

Explicit policy registrations retain their resource and policy classes. Cached inherited matches and misses use weak resource keys, so looking up an unregistered transient subclass does not keep it alive. Register policies during application boot.

## Intersecting token capabilities

`AuthorizationSnapshot(permissions, roles, abilities=None)` adds no identity permission restriction when abilities is `None`; an empty collection denies all. Permission access intersects identity permissions and abilities. For policies, the ability name must also occur in restricted token abilities before `before` executes. Naming a capability in a token does not grant privileges. The snapshot copies its inputs into frozen sets and exposes read-only properties; mutating the original collections does not change an existing snapshot.

Evidence: [registrar](../../authorization/registrar.py), [authorizer](../../authorization/authorizer.py), [snapshot](../../authorization/snapshot.py). Tests: [permissions](../../../../tests/auth/test_permissions.py), [policies](../../../../tests/auth/test_authorizer.py), [snapshot](../../../../tests/auth/test_snapshot.py). Continue with [tokens](personal-access-tokens.md).
