# Orionis Realtime Protocol v1

This specification defines Orionis application messages carried by WebSocket.
It does not implement SignalR, Socket.IO or another RPC wire protocol. Ordinary
Orionis WebSocket routes do not use this protocol.

## Transport, encoding and version

A route selects its codec before the handshake:

```python
Route.hub("/hubs/chat", ChatHub)                     # JSON
Route.hub("/hubs/devices", DeviceHub, protocol="msgpack")
```

Each complete WebSocket **message** contains exactly one envelope. There is no
record separator, batch array, additional length prefix or application-level
fragmentation. WebSocket servers assemble fragmented transport messages before
Orionis receives them.

JSON routes accept text messages containing a JSON object. MessagePack routes
accept binary messages containing a MessagePack map with string field names.
The envelopes, tag strings and field names are identical in both encodings.
There is no subprotocol negotiation, which keeps the protocol compatible with
both ASGI and Granian RSGI. A frame using the wrong kind causes close 1003 where
the server can transmit that code.

The first successful application envelope is `ready`, whose `version` is the
integer `1`. A client must wait for `ready` before sending invocations and must
disconnect if it cannot support the announced version. A rejected handshake
does not produce `ready`. No client handshake envelope is required.

JSON values use the JSON data model. MessagePack may additionally represent
binary data natively. A client using both encodings should choose data types
that its own codecs support; binary data inside JSON follows msgspec's base64
representation. A result, argument or stream item is application data and is
never interpreted as executable metadata.

## Envelope grammar

Every envelope has a case-sensitive string `type`. Client envelopes reject
unknown fields and incorrect field types. Field defaults below apply only when
that field is omitted; `null` is allowed only where stated.

| Type | Direction | Required fields | Optional fields |
|---|---|---|---|
| `ready` | Server → client | `version: 1`, `connection_id: string` | None |
| `invoke` | Both | `id: string`, `target: string` | `args: array = []`; client → server also accepts `kwargs: object = {}` and `timeout: number or null = null` |
| `completion` | Both | `id: string`; exactly one of `result: any` or `error: Error` | None |
| `send` | Server → client | `target: string`, `args: array` | None |
| `stream_item` | Server → client | `id: string`, `item: any` | None |
| `stream_complete` | Server → client | `id: string` | `error: Error`; omitted on success |
| `cancel` | Client → server | `id: string` | None |
| `ping` | Both | None | None |
| `pong` | Both | None | None |

The `type` field itself is required in every row. In v1 Orionis responds to
client `ping` with `pong` and accepts client `pong` without an additional action.
It does not schedule server pings automatically. These are application messages,
not WebSocket protocol control frames.

`Error` is an object containing exactly `code: string` and `message: string`.
The code must be nonempty and at most 64 characters; the message may be empty
and must be at most 1024 characters. A completion with `error: null`, both
outcomes, or neither outcome is malformed. `result: null` is a successful result.

## Identifiers and limits

An invocation ID is an opaque string of 1–128 printable ASCII characters,
excluding spaces. The client should use a fresh ID for each active invocation.
The server generates its own IDs for server → client requests. Those two
directions have independent ownership: inbound `completion` resolves only a
server-owned pending call; inbound `cancel` targets only a client-owned active
invocation. Clients must maintain those two registries separately too.

Reusing an ID while a client → server invocation is active is a protocol
violation. Reuse after its terminal envelope is permitted, although never
reusing an ID during a connection is simpler. Unknown, late or duplicate
client completions are ignored and allocate no pending entry. Unknown or
duplicate cancellations are harmless.

Once method/producer cleanup and scope release finish, the invocation's outcome
is committed and that ID is no longer a cancellation target. Its terminal
delivery can still be waiting on network backpressure. Clients must wait for
the terminal envelope before reusing the ID so that correlation is unambiguous;
receiving it permits reuse even if the server's delivery task is still finishing.

| Limit | Default / rule |
|---|---|
| Incoming message bytes | `realtime.max_message_size = 1,048,576`; the raw `http.websocket.max_message_size` also applies |
| Invocation ID | 1–128 printable ASCII characters, without spaces |
| Invocation target | 1–128 characters; exposed server names are public Python identifiers |
| Positional arguments | At most 64 |
| Named arguments | At most 64; each key is 1–128 characters |
| Owned server invocations per connection | `realtime.max_concurrent_invocations = 16`; includes active calls and calls finishing terminal delivery |
| Pending client results per connection | `realtime.max_pending_client_invocations = 32` |
| Group name | Nonblank string, at most 256 characters |
| Groups per connection | `realtime.max_groups_per_connection = 64` |

Text message limits count UTF-8 bytes, including non-ASCII characters. Limits
are validated before invoking a method or allocating its task. Reaching the
active invocation limit produces a `busy` completion, with no waiting queue.
Calls whose terminal delivery is backpressured still consume this budget even
though their method has completed and their scope has been released. This
prevents slow terminal writes from accumulating unlimited delivery tasks.
Groups are managed through application Hub methods, not a built-in wire
envelope. The application must authorize membership changes itself.

## Connection lifecycle

1. Connect to the configured WebSocket route and complete application-specific
   handshake authentication.
2. Orionis runs connection middleware and `Hub.onConnect()`. Rejection ends the
   connection without publishing it as a ready recipient.
3. Orionis accepts the socket if the hook has not already accepted it and sends:

   ```json
   {"type":"ready","version":1,"connection_id":"unpredictable-connection-id"}
   ```

4. Both sides may exchange the allowed envelopes until disconnection.
5. Disconnection cancels active and finishing server invocation tasks, closes stream producers,
   fails pending server → client calls, removes group memberships and releases
   the registry entry and connection scope. There is no reconnection/resumption
   token, message replay or automatic group restoration in v1.

The `connection_id` identifies this connection, not a user or session. A user
may have several connections. An application may include a connection ID in its
own messages, but receiving an ID does not grant permission to target it.

## Client → server invocation

```json
{"type":"invoke","id":"req-1","target":"add","args":[2,3]}
```

`target` selects only a name present in the Hub's boot-compiled `@remote` map.
Public helpers, private attributes, dotted paths and undecorated methods are
not exposed. Unknown names produce `method_not_found` without closing the
socket. Names are case-sensitive; aliases use `@remote(name="wireName")`.

Argument positions count only client-bound parameters. For a server signature
`find(self, order_id: int, service: OrderService, *, details: bool = False)`, a
valid request is:

```json
{"type":"invoke","id":"req-2","target":"find","args":[42],"kwargs":{"details":true}}
```

`service` always comes from DI and has no argument position on the wire. Sending
a named `service`, an unknown name, duplicate positional/named assignment,
missing required value or excess value produces `invalid_arguments`. Type and
schema validation failures produce `validation_error`. Types are strict: a
string `"42"` does not substitute for an integer. Default values are supplied
by the server. Keyword-only parameters must be passed through `kwargs`.

An ordinary result ends the invocation:

```json
{"type":"completion","id":"req-1","result":5}
```

Every invocation receives its own container scope and a fresh Hub instance.
Different invocations may finish out of order. The client correlates outcomes
using `id`, never request order. The framework does not permit concurrent tasks
to read the underlying socket independently.

## Server → client invocation and events

An event does not request a logical return value:

```json
{"type":"send","target":"messageReceived","args":[{"message":"Hello"}]}
```

The server awaits network delivery, but the client sends no completion for a
`send`. A server request expecting a result instead carries an ID:

```json
{"type":"invoke","id":"s1","target":"refreshState","args":[{"section":"orders"}]}
```

The client should dispatch only its explicitly registered local handlers,
then send one of:

```json
{"type":"completion","id":"s1","result":{"revision":12}}
```

```json
{"type":"completion","id":"s1","error":{"code":"unavailable","message":"Try again"}}
```

The server correlates the completion only within that connection. A client
error is exposed to server application code as a sanitized
`ClientInvocationError`; arbitrary client error text is not propagated into
server diagnostics. Server → client invocation selects exactly one client;
group and broadcast targets support `send` only.

The default result deadline is `realtime.client_result_timeout = 30` seconds.
An application can set `invoke(..., timeout=5)`. The deadline covers waiting for
the send and the completion. Timeout/cancellation removes the server's pending
future, but v1 does not send an automatic server → client `cancel` envelope.
The client may finish its local operation; a late completion is ignored.

## Streaming invocation

When a server method returns an async iterable, the request becomes a stream:

```json
{"type":"invoke","id":"progress-1","target":"watchProgress","args":["job-7"]}
```

```json
{"type":"stream_item","id":"progress-1","item":10}
{"type":"stream_item","id":"progress-1","item":50}
{"type":"stream_complete","id":"progress-1"}
```

These examples represent three separate WebSocket messages. A stream may emit
zero items. `stream_complete` is terminal and no separate successful
`completion` follows it. A producer/serialization failure terminates the stream
with `stream_complete` containing `error`.

Each item is serialized and its send awaited before requesting the next item.
The server never materializes the full stream. Items belonging to different
concurrent invocations or events may interleave; each stream's own items retain
their production order.

The producer's `aclose()` and the invocation scope's cleanup complete before
the successful `stream_complete` is sent. Ordinary successful `completion`
messages likewise follow scope release. Terminal errors are sent after the
same cleanup path has unwound.

Async generator methods and methods annotated `AsyncIterable[...]` or
`AsyncIterator[...]` are recognized at registration and have no default lifetime
timeout. A client can specify a finite positive `timeout`, in seconds, bounded
by `realtime.invocation_timeout`. Ordinary calls default to that configured
30-second limit. For a dynamically returned stream without a stream annotation,
the ordinary deadline covers the method call until it returns the iterable;
the runtime then removes that implicit deadline. An explicit client timeout
still covers the whole stream. Timeouts never set the connection's lifetime.

The method deadline covers dependency resolution, binding, method execution,
stream item production/delivery and producer cleanup. The final terminal
`completion` or `stream_complete` is sent after exiting both the invocation
scope and its deadline. It still awaits network backpressure, so terminal
delivery may finish after the method's timeout duration. A slow terminal send
does not convert a committed result into a second timeout outcome. The
connection continues to own and budget that delivery until it finishes, and
disconnect/shutdown can cancel it. Clients needing a deadline for receiving a
terminal envelope must maintain their own local timer as well.

## Cancellation

```json
{"type":"cancel","id":"progress-1"}
```

The server cancels only that active invocation. It runs the method's `finally`
blocks, closes its async generator/iterator when it exposes `aclose()`, and
releases the invocation scope. A live connection receives a terminal error with
code `cancelled`: `completion` for an ordinary invocation or `stream_complete`
for a stream. Cancellation racing an already finished call may have no effect.
Repeated cancellation does not interrupt cleanup a second time.

If execution and cleanup finish before cancellation takes effect, the committed
outcome wins. Cancellation cannot change that outcome while its terminal write
is waiting on backpressure, and no second `cancelled` terminal is generated for
that completed invocation.

A write already underway may finish before the cancellation envelope is sent;
clients must accept previously produced stream items until the terminal
envelope. Cancellation of one invocation does not cancel an in-progress shared
socket write or another invocation. Disconnection does cancel the entire
connection's owned work and does not promise delivery of terminal envelopes.

Cancellation is cooperative Python task cancellation. Application code must not
suppress `CancelledError` or perform indefinitely blocking synchronous work.

## Errors and closure

| Error code | Meaning |
|---|---|
| `method_not_found` | Target absent from the explicit remote dispatch map. |
| `invalid_arguments` | Invalid binding or invocation timeout above the configured maximum. |
| `validation_error` | A value violates its declared type or schema rules. |
| `unauthorized` | The operation requires authentication. |
| `forbidden` | The operation failed application authorization. |
| `busy` | Active calls plus calls finishing terminal delivery already consume the connection's invocation budget. |
| `timeout` | The invocation exceeded its applicable deadline. |
| `cancelled` | An active invocation was cancelled. |
| `internal_error` | Method execution or result serialization failed unexpectedly. |

These are per-invocation outcomes and do not normally close the socket. Error
messages are intentionally generic, contain no traceback, and should not be
used for machine classification; use `code` instead. Applications may raise
an explicit `RPCError` with an application-owned code, but must not put secrets
in public codes or messages.

Malformed envelopes, unknown message types, incompatible frames, invalid IDs
and duplicate active IDs close the connection immediately. Orionis does not
send an uncorrelated error envelope for them. Where transport support permits,
the close code is 1002 for a protocol violation, 1003 for an incompatible frame,
1009 for a message-size violation, or 1011 for a fatal lifecycle/transport
failure. Ordinary closure uses 1000 and shutdown uses 1001.

ASGI can transmit supported close details. The installed Granian RSGI interface
does not expose WebSocket close-frame code/reason: it performs default closure,
while Orionis retains its local failure classification. A client must therefore
treat connection loss as terminal even when no detailed wire code is available.

## Delivery and distribution

`send`/RPC is realtime and **non-durable**. Queue jobs are the durable execution
primitive. A disconnected client's messages are not stored for its return.
The default registry is confined to the current process/worker; broadcasts and
groups do not reach connections in another worker. No distributed backplane,
offline queue, exactly-once delivery or automatic retry is specified by v1.
