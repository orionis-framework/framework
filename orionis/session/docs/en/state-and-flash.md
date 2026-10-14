# User state and form flash data

Use sessions for small preferences or temporary browser state. Data outlives one request object, but sessions are not permanent domain storage. Avoid passwords, secrets and complete ORM objects.

## Accessing state from a handler

```python
from orionis.http import response
from orionis.session.contracts.session import ISession

async def choose_theme(session: ISession):
    session.put("theme", "dark")
    return response.redirect("/settings", 303).withFlash("notice", "Theme saved")
```

Injection requires an active web scope. Alternatively, `from orionis.support.facades import Session` resolves the same contract. `get`, `put`, `has`, `forget`, `clear` and `all` are synchronous: do not add `await`. Store and manager operations are asynchronous.

```python
from orionis.session.session import Session

session = Session()
assert session.id is None and not session.started
assert session.get("theme", "system") == "system"
session.put("theme", "dark")
assert session.started and session.dirty
assert session.get("theme") == "dark"
```

Writing an equal value does not dirty the session. However, mutating a retrieved collection may change data without `put`; renewal conservatively treats mutable payloads. Do not expose `all()` as a public response: it includes internal bags.

## POST, redirect, GET

`flash(key, value)` makes data readable in the current request and the next. At the next start, the manager removes the old bag and promotes the new one. This is neither a message queue nor indefinite persistence.

```python
from orionis.session.session import Session

session = Session()
session.flashInput({"email": "ada@example.test", "password": "secret", "_csrf": "secret"})
session.flashErrors({"email": "Already registered"})
assert session.getOldInput("email") == "ada@example.test"
assert session.getOldInput("password") is None
assert session.getErrors() == {"email": ["Already registered"]}
```

`flashInput` filters known credential and CSRF field names. Exclude application-specific secrets yourself. `flashErrors` accepts mappings or validation exceptions and normalizes values into message lists. Repeated writes to reserved bags merge.

Response `withInput`, `withErrors` and `withFlash` queue the same data for middleware to apply; do not write it twice. Sessions expose `setPreviousUrl`/`getPreviousUrl`; the web layer updates navigation only for eligible requests/responses. Redirect-back flows must check safe destinations through HTTP helpers rather than trust arbitrary `Referer` input.

## Lifetime and testing

An isolated `Session()` can test value manipulation but does not demonstrate persistence between requests: that depends on the manager, cookies and store. Do not share the instance between concurrent requests. Read [stores](stores-and-concurrency.md) and [security](configuration-and-security.md).

Evidence: [Session](../../session.py), [flash](../../flash.py), [web middleware](../../../http/layer/web/start_session.py). Tests: [data](../../../../tests/session/test_session.py), [flash](../../../../tests/session/test_flash.py), [web persistence](../../../../tests/http/layer/web/test_session_persistence.py).
