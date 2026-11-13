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

### Configure the HTTP response

`View.make()` and `response.view()` accept keyword-only `status_code`, `headers`, and `background`, with defaults `200`, `None`, and `None`. `status_code` accepts an `HTTPStatus` or integer, `headers` accepts a mapping of strings, and `background` accepts a `BackgroundTask` to run after response delivery.

```python
from orionis.background import BackgroundTask
from orionis.support.facades import View


async def unauthorized(ip: str, task: BackgroundTask):
    return await View.make(
        "errors.401",
        status_code=401,
        headers={"Cache-Control": "no-store"},
        background=task,
        ip=ip,
    )
```

The equivalent fluent form queues the same response changes without rendering early:

```python
async def unauthorized_fluent(ip: str, task: BackgroundTask):
    return await (
        View
        .make("errors.401", ip=ip)
        .withStatusCode(401)
        .withHeaders({"Cache-Control": "no-store"})
        .withBackground(task)
    )
```

Constructor options apply first, followed by chained mutations in call order. `withHeaders()` merges the supplied names, replacing existing values case-insensitively and retaining unrelated headers. `withBackground(None)` clears the task. These methods also return `self` on a constructed `Response`; validation is immediate there and deferred until `await` on a `PendingView`. Invalid option types or status ranges raise `TypeError` or `ValueError`, independently of template-rendering errors. The default `X-Orionis-Render: SSR` header remains unless supplied headers or a later mutation override it.

The names `status_code`, `headers`, `background`, and `context` are reserved arguments. Pass template variables with those names through the explicit `context` mapping, for example `View.make("errors.401", status_code=401, context={"status_code": "Session expired"})`. Additional keyword variables override entries in that mapping without modifying the caller's mapping. Unlike deferred HTTP options, a `context` value that is neither a mapping nor `None` raises `TypeError` when preparing the view.

### Prepare a form with errors

Configure sessions and CSRF middleware before using form helpers. This controller example requires a booted application and `auth/login.html`:

```python
from orionis.support.facades import View


async def invalid_form():
    return await (
        View
        .make("auth.login")
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

`HTMLResponse` mutations such as `addHeader()` or `withCookie()` are queued and replayed after rendering. The response validates their arguments when each call is applied, not when queued. A noncallable or unknown attribute raises `AttributeError`.

Template errors retain their underlying cause through the pending response. A saturated template worker queue raises `WorkQueueFullError`, so callers can distinguish overload from an invalid template.


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

- `View.make(template, *, status_code=200, headers=None, background=None, context=None, **variables) -> PendingView`: primary facade API after application boot.
- `ViewFactory.make(...) -> PendingView`: injectable equivalent with the same arguments.
- `PendingView.render() -> HTMLResponse`: explicit async render; awaiting the pending object is equivalent.
- `PendingView.withStatusCode(status_code)`, `withHeaders(headers)`, and `withBackground(background)`: queue HTTP response changes and return the pending view.
- `PendingView.withFlash(key, value=None)`, `withInput(values)`, and `withErrors(errors)`: queue session flash state.
- `IViewFactory`, `IViewEngine`, and `IViewEnvironment`: contracts for application extensions and alternate implementations.

---

[Index](README.md) · [http](../../../http/docs/en/README.md) · [session](../../../session/docs/en/README.md) · [mail](../../../mail/docs/en/README.md)
