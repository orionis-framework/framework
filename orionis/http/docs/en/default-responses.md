# Health, errors and default routes

The router registers favicon, `robots.txt`, `sitemap.xml` and the application's configured health path. `DefaultResponses` renders pages through `IViewEngine`, serves a closed set of packaged assets and provides JSON where appropriate. It is not a static server for arbitrary project files.

## Checking availability

Health returns 200 normally and 503 during maintenance. `Accept: application/json` requests JSON with a state message; HTML shows the corresponding page. This reports application state rather than automatically checking every database, queue or external dependency.

Override the GET favicon, robots and sitemap routes by declaring their paths in application routes. Public files use candidate selection with packaged fallbacks where available. A missing sitemap can return 404; business URL catalogs are not generated automatically.

## Presenting an error from a service

```python
from orionis.http.default.contracts.responses import IDefaultResponses

async def unavailable(pages: IDefaultResponses):
    return await pages.error(
        503, {"message": "Catalog temporarily unavailable"},
        expects_json=True, headers={"Retry-After": "30"},
    )
```

The container must resolve `IDefaultResponses` in a booted application. `error` accepts an integer/`HTTPStatus` between 100 and 599 and text or dictionary content. HTML escapes descriptions; JSON preserves values. Unless you provide your own cache policy, the service adds its conservative default.

Exception pages contain traceback/context and may include an assistance link encoding diagnostic information in a URL. Review what your handler exposes and configure debug for the environment. The `exception()` method does not itself authorize access to diagnostic details.

## Enabling optional authentication pages

`Route.auth()` registers login, registration and recovery GET/POST routes, email verification GET and logout POST. Logout requires session identity. Guest pages use `GuestMiddleware`; verification allows links opened in an already authenticated browser. The web pipeline provides sessions and CSRF.

```python
from orionis.support.facades import Route

Route.auth()
```

Declare it once in web routes. Supply `login_controller`, `register_controller` or `forgot_password_controller` to replace individual controllers. Preserve methods expected by [the actual registration](../../routes/auth.py). Default registration/profile controllers depend on `app.models.user.User`, application views, hashing and mail; they are not a generic flow for every identity model. Check those contracts before enabling them. Read [account recovery](../../../auth/docs/en/account-recovery.md).

## Caches and file changes

The kernel retains the exact `DefaultResponses` service; each call creates a response with independent mutable state. Health retains at most two HTML bodies and invalidates them when application name/locale changes. Error and exception pages render per request and do not cache their payloads.

Allowlisted assets retain paths rather than content or `stat` results. A selected file reflects content changes; adding a higher-priority candidate requires restarting or deleting `responses["favicon"]`, `responses["robots_txt"]` or `responses["sitemap_xml"]`. Missing selected files trigger reselection. Opening can still fail after response construction.

Evidence: [service](../../default/responses.py), [auth routes](../../routes/auth.py), [controllers](../../default/controllers/login_controller.py). Tests: [caches](../../../../tests/http/default/test_response_cache.py), [templates](../../../../tests/http/default/test_templates.py), [assistance](../../../../tests/http/default/test_assistance.py), [auth routes](../../../../tests/auth/test_auth_routes.py). The historical performance review remains under `default/docs/`; its numbers are not current benchmarks.
