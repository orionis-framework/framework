# Identities and browser authentication

An identity model must implement `IAuthenticatable`. Usually combine `Model` with `Authenticatable`; add `Authorizable` for permissions, roles or tokens. Mixins avoid direct ABC inheritance, which would conflict with the ORM metaclass.

```python
from orionis.auth import Authenticatable, Authorizable
from orionis.orm import Integer, Model, String

class User(Model, Authenticatable, Authorizable):
    id = Integer().primary().autoIncrement()
    email = String(255).unique()
    password = String(255)
```

Place it in an application module and set `AUTH_MODEL` to its path, defaulting to `app.models.user.User`. `AUTH_USERNAME` defaults to `email`. `Authenticatable` reads the key from ORM metadata and the hash from `AUTH_PASSWORD="password"`; override that class variable for another column. Persist hashes through [hashing](../../../hashing/docs/en/README.md), never submitted passwords.

## Login and logout

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

These handlers require web routes with sessions and CSRF; validate format with an application schema first. `attempt` returns `False` on failed authentication. Success rotates the session, stores the identity identifier and rebinds the current context. `login(identity)` accepts an identity verified by another trusted flow; it does not itself check a password.

`attempt`, `login` and `logout` are asynchronous and always use the session guard even when another is default. They raise `AuthException` outside an active HTTP request. Logout invalidates session state; deleting one variable is not equivalent.

## Reading and requiring identity

`Auth.user()`, `identifier()`, `check()`, `guest()` and `context()` are synchronous. Permission checks and snapshot loading require `await`. The kernel uses `ResolveSessionIdentityMiddleware` for web and `ResolveTokenIdentityMiddleware` for API routes; both permit guests. Add `AuthenticateSessionMiddleware` or `AuthenticateTokenMiddleware` to require credentials.

`AuthenticateMiddleware` uses the current/default guard. JSON/AJAX and token guests receive authentication failure; session browsers may redirect to `AUTH_REDIRECT_TO` (`/login`). `GuestMiddleware` redirects authenticated users to `AUTH_HOME` (`/home`). Protected responses include private/no-store cache policy.

## Configuration and extension

`AUTH_GUARD` accepts `session` or `token`; `AUTH_SESSION_KEY` defaults to `_auth_identifier`. Unknown guards raise `GuardNotFoundException`. `AuthProvider` registers a scoped context and shared services/guards; the facade is pinned at boot to support synchronous reads. Do not cache `Auth.user()` in a singleton.

Replace `IIdentityProvider`, `IGuard`, `IAuthManager` or repository contracts through container bindings before dependents are constructed. Configuration does not automatically register new guard names. Continue with [authorization](authorization.md).

Evidence: [manager](../../manager.py), [identities](../../identity/provider.py), [guard](../../guards/session_guard.py), [provider](../../provider.py), [config](../../../../config/auth.py). Tests: [session](../../../../tests/auth/test_identity_and_session.py), [manager](../../../../tests/auth/test_manager.py), [context](../../../../tests/auth/test_context.py), [middleware](../../../../tests/auth/test_middleware.py).
