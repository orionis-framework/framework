# Reading requests and validating input

`Request` separates synchronous metadata from asynchronous body reads. Properties including `method`, `path`, `scheme`, `url`, `baseUrl`, `headers`, `queryParams`, `cookies`, `ip`, `port` and `state` need no `await`. Parsers read a stream: await `body()`, `text()`, `json()`, `xml()`, `msgpack()`, `formUrlEncoded()`, `form()`, `payload()` or `data()`.

## A preferences endpoint

```python
from orionis.http import Request, response
from orionis.schemas import Schema
from orionis.schemas.validator import Schema as Validator

class Preferences(Schema):
    theme: str
    compact: bool = False

async def save_preferences(request: Request):
    values = await request.data()
    preferences = await Validator.validateAsync(values, Preferences)
    return response.json({"theme": preferences.theme, "compact": preferences.compact})
```

Register the handler with the appropriate authentication policy. This example teaches decoding and explicit schema validation; add business rules and persistence as described in [schemas](../../../schemas/docs/en/README.md). The kernel also supports typed schema parameters through its injection plans; avoid duplicating manual reads when choosing that flow.

## Choosing a parser

`json()` preserves any valid JSON value, including arrays and scalars. `payload()` selects a parser by `Content-Type` and retains the result's shape. `data()` supplies a normalized dictionary for forms and application payloads; do not use it when you must preserve a top-level JSON array. Specific helpers reject incompatible MIME types with `UnsupportedMediaTypeException`.

`headers` supports case-insensitive lookups and `getAll()` for repeated values. `queryParams.get()` and `.getAll()` distinguish one value from all values. Cookies and URL parameters remain untrusted input: an `Authorization` header or a present `bearerToken` does not establish authentication. Use the [Auth](../../../auth/docs/en/README.md) context.

## One body consumer

`stream()` yields incremental bytes. A body can only be reread when fully retained within the buffer limit. Do not combine large-file streaming with a later `json()` read or run concurrent consumers on one request. Parsers cache results where applicable, but caching cannot make an unbuffered consumed stream replayable.

`HTTP_MAX_BODY_SIZE` limits total input, `HTTP_MAX_BUFFER_SIZE` limits replay memory and `HTTP_MAX_CONCURRENT_REQUESTS` bounds active requests per worker. Bootstrap defaults are 16 MiB, 2 MiB and 128. Limits apply while chunks arrive; a small `Content-Length` does not bypass them. Duplicate or contradictory framing is rejected before the handler runs.

## Negotiation and errors

`wantsJson()`, `wantsHtml()`, `wantsXml()`, `accepts(mime)` and `isAjax()` help choose a representation. They do not establish permission. API/JSON schema failures become structured errors; web forms can redirect with errors and filtered input. Validation helpers check return destinations to prevent untrusted input controlling a redirect.

When diagnosing a failed read, check `Content-Type`, size, prior consumption and format before relaxing limits. Do not log complete credential-bearing bodies.


## Formats and custom parsers

`data()` requires a top-level mapping for JSON/MessagePack and collapses form keys into a scalar or list according to repetition. Dispatch accepts exact MIME types `application/json`, `application/msgpack`, `application/x-www-form-urlencoded` and `multipart/form-data`; unlike `json()`, it does not automatically recognize every `+json` subtype. `payload()` returns bytes when no parser is registered. XML uses defusedxml to reject internal/external entities.

Create a registry for infrastructure-built Requests without mutating the default singleton:

```python
from orionis.http.payload.media_types import DEFAULT_MEDIA_TYPES

registry = DEFAULT_MEDIA_TYPES.extend({"application/vnd.example.label": lambda raw: raw.decode("utf-8")})
parser = registry.get("application/vnd.example.label")
assert parser is not None and parser(b"ready") == "ready"
assert DEFAULT_MEDIA_TYPES.get("application/vnd.example.label") is None
```

Pass `registry=` to the Request constructor when owning that integration. `register` mutates a registry and `extend` creates a new one. This does not change `data()` dispatch. The native kernel constructs Requests with the default registry; this API does not by itself register a global parser provider.

Buffer limits also bound materialization by `body()`, JSON and similar parsers. A body allowed by the 16 MiB total budget can exceed the 2 MiB buffer and fail a complete read through those helpers; use streaming or deliberately adjust both budgets.

Evidence: [Request](../../request.py), [BodyStream](../../payload/body.py), [HTTP validation](../../validation.py). Tests: [requests](../../../../tests/http/test_request.py), [limits](../../../../tests/http/test_request_limits.py), [validation](../../../../tests/http/test_validation.py). Continue with [forms and uploads](forms-and-uploads.md).
