# Realtime: hubs over WebSocket

Realtime adds typed RPC and bidirectional events to WebSocket routes. A Hub declares explicit remote methods; Orionis compiles argument/dependency plans and constructs an instance per invocation. The default registry knows only connections within the current worker.

1. [Building hubs and remote methods](hubs-and-methods.md).
2. [Protocol, streams and client results](protocol-and-streaming.md).
3. [Groups, broadcasts and deployment](groups-and-deployment.md).

Requires Python 3.14+, a booted application and WebSocket-capable ASGI/RSGI serving. Read [WebSocket](../../../http/docs/en/websockets.md), [authentication](../../../auth/docs/en/README.md) and [container](../../../container/docs/en/README.md). Orionis Realtime v1 requires a client implementing its envelopes; SignalR compatibility is not promised.
