# Cookies, renewal and secure lifecycle

Configure sessions in `config/session.py`. Frozen configuration validates names, cookie policy, driver and intervals at boot. Environment values are read when bootstrap is constructed; changing an already running worker's environment is not per-request reconfiguration.

| Variable | Default | Effect |
|---|---|---|
| `SESSION_DRIVER` | `memory` | Server store. |
| `SESSION_LIFETIME` | 120 minutes | Record expiration. |
| `SESSION_EXPIRE_ON_CLOSE` | false | Omits cookie Max-Age; server expiry still applies. |
| `SESSION_RENEWAL_INTERVAL` | 0 seconds | Minimum interval for renewing unchanged scalar payloads. |
| `SESSION_TRACK_PREVIOUS_URL` | true | Tracks eligible navigation. |
| `SESSION_COOKIE`, `SESSION_PATH`, `SESSION_DOMAIN` | `sessionid`, `/`, current host | Cookie identity and scope. |
| `SESSION_SECURE`, `SESSION_HTTP_ONLY` | false, true | HTTPS and script policy. |
| `SESSION_SAME_SITE`, `SESSION_PARTITIONED` | `lax`, false | Cross-site policy and Partitioned attribute. |

Enable Secure in production HTTPS. `SameSite=None` requires Secure. Renewal intervals must be nonnegative and shorter than lifetime in seconds. A positive interval reduces writes/cookies for unchanged scalar reads; mutable or dirty payloads are still saved. It neither guarantees user activity nor eliminates every write.

```python
from orionis.foundation.config.session import Session as SessionConfig

config = SessionConfig(driver="memory", lifetime=120, renewal_interval=300,
                       secure=True, http_only=True, same_site="none")
assert config.renewal_interval == 300
```

## Rotating after privilege changes

```python
from orionis.session.session import Session

session = Session()
session.put("account", 7)
old_id = session.id
session.regenerate()
assert session.wantsRegenerate
assert session.id == old_id
session.invalidate()
assert session.invalidated
```

`regenerate()` requests rotation; the identifier does not change immediately. The manager coordinates deleting the old record and persisting the new one when saving the response. Auth login already integrates rotation: do not build a parallel flow that bypasses its context. `invalidate()` clears data and requests record deletion/an expired cookie. `clear()` only removes values; it is not secure logout.

## Recovery and failures

Missing, malformed or expired cookies and corrupt records produce a fresh lazy session. Invalid IDs never reach storage. Storage errors are not silently converted into cookies promising nonexistent persistence; inspect `SessionStorageException` and backend errors.

`SessionManager.start(request)`, `save(response, session)` and `abort(session)` are asynchronous infrastructure operations. Middleware should own them to prevent double saves. `abort` removes invalidated or superseded identifiers after errors/cancellation without issuing a new cookie. Tests also cover concurrent revocation while another request completes.

Do not share `Session` objects across requests or assume HttpOnly prevents CSRF. Keep [CSRF protection](../../../http/docs/en/middleware-and-security.md) and use [Auth](../../../auth/docs/en/README.md) for identity. Sessions do not automatically encrypt each storage payload.

Evidence: [configuration](../../../../config/session.py), [manager](../../manager.py), [session lifecycle](../../session.py). Tests: [manager](../../../../tests/session/test_manager.py), [renewal](../../../../tests/session/test_renewal.py), [foundation config](../../../foundation/config/session/entities/session.py).
