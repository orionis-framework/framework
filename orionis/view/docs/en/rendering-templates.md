# Rendering pages and HTML responses

View renders server-side HTML with async Jinja2 and returns an Orionis response.

## Requirements

- Python 3.14 or newer.
- At least one configured template directory; the default is `resources/views` relative to the application base path.
- A bootstrapped Orionis application for the facade and service-backed template globals.
- Jinja2, MarkupSafe, Markdown, and msgspec as installed by the project dependencies.



## Quick start

Create `resources/views/users/profile.html`:

```html
<!doctype html>
<h1>{{ user.name }}</h1>
<a href="{{ route('users.edit', id=user.id) }}">Edit</a>
```

Return it from an async controller:

```python
from orionis.support.facades import View

async def profile(user):
    return await View.make("users.profile", user=user)
```



## Choose context, rendering, and response

`View.make()` is synchronous and creates a `PendingView`; I/O and expression evaluation happen when it is awaited. Use `return await View.make("users.profile", user=user)` from a controller. A service needing text alone can inject `IViewEngine` and call `await engine.render(template, context)`; the result is `str`, not `HTMLResponse`. Mail uses this contract to generate MIME bodies.

A pending response retains a context dict and mutable queues. Create one per operation, pass prepared data, and avoid sharing it across requests. Awaiting the same object twice renders twice and may apply flash again. It is not a memoized promise. `make()` also does not check template existence.

Dot notation omits the extension: `users.profile` looks for `users/profile.html`. For an explicit extension use `/`, such as `users/profile.j2`; `users.profile.html` is transformed as a dotted identifier, not as a path with an extension. `{% extends %}` and `{% include %}` names belong to Jinja and must use actual paths including extensions.

### Prepare a form with errors

Configure sessions and CSRF middleware before using form helpers. This controller example requires a booted application and `auth/login.html`:

```python
from orionis.support.facades import View


async def invalid_form():
    return await (
        View.make("auth.login")
        .withInput({"email": "ada@example.com"})
        .withErrors({"email": "Unknown account"})
        .withFlash("status", "Please review the form")
        .addHeader("Cache-Control", "no-store")
    )
```

```html
<form method="post" action="{{ url('/login') }}">
  {% csrf %}
  <label>Email <input name="email" value="{{ old('email', '') }}"></label>
  {% if errors.has('email') %}
    <p role="alert">{{ errors.first('email') }}</p>
  {% endif %}
  <label>Password <input type="password" name="password"></label>
  <button type="submit">Sign in</button>
</form>
```

`withInput()` filters known credential fields but is not a universal secret classifier: select fields worth retaining. `withErrors()` normalizes scalar messages to lists. Flash is applied before rendering; a later template failure does not roll back that session mutation. When a session is unavailable, the pending response skips flash writes; the CSRF helper instead needs to resolve the session and its token.

`HTMLResponse` mutations such as `addHeader()` or `withCookie()` are queued and replayed after rendering. The response validates their arguments when each call is applied, not when queued. A noncallable or unknown attribute raises `AttributeError`. The final response carries `X-Orionis-Render: SSR` unless a mutation changes it.


### Render directly with an isolated engine

```python
import asyncio

import jinja2

from orionis.view.engine import Jinja2Engine

class Environment:
    def __init__(self) -> None:
        self.jinja = jinja2.Environment(
            loader=jinja2.DictLoader({"hello.html": "Hello {{ name }}!"}),
            enable_async=True,
            autoescape=True,
        )

    def getJinjaEnvironment(self) -> jinja2.Environment:
        return self.jinja

html = asyncio.run(Jinja2Engine(Environment()).render("hello", {"name": "Ada"}))
assert html == "Hello Ada!"
```

### Build an HTML response and queue mutations

```python
import asyncio

from orionis.view.factory import ViewFactory

class Engine:
    async def render(self, template: str, context: dict) -> str:
        return f"<h1>{context['title']}</h1>"

pending = ViewFactory(Engine()).make("pages.home", title="Welcome")
pending.addHeader("X-Page", "home").withCookie("theme", "dark")
response = asyncio.run(pending.render())

assert response.getBody() == b"<h1>Welcome</h1>"
assert response.getHeader("X-Page") == ["home"]
assert response.getHeader("X-Orionis-Render") == ["SSR"]
```

### Rendering API

- `View.make(template, **context) -> PendingView`: primary facade API after application boot.
- `ViewFactory.make(template, **context) -> PendingView`: injectable equivalent.
- `PendingView.render() -> HTMLResponse`: explicit async render; awaiting the pending object is equivalent.
- `PendingView.withFlash(key, value=None)`, `withInput(values)`, and `withErrors(errors)`: queue session flash state.
- `IViewFactory`, `IViewEngine`, and `IViewEnvironment`: contracts for application extensions and alternate implementations.

---

[Index](README.md) · [http](../../../http/docs/en/README.md) · [session](../../../session/docs/en/README.md) · [mail](../../../mail/docs/en/README.md)
