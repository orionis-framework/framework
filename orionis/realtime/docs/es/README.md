# Realtime: hubs sobre WebSocket

Realtime añade RPC tipado y eventos bidireccionales a rutas WebSocket. Un Hub declara métodos remotos explícitos; Orionis compila argumentos y dependencias y construye una instancia por invocación. El registro predeterminado conoce únicamente conexiones del worker actual.

1. [Crear hubs y métodos remotos](hubs-and-methods.md).
2. [Protocolo, streams y resultados de clientes](protocol-and-streaming.md).
3. [Grupos, broadcasts y despliegue](groups-and-deployment.md).

Requiere Python 3.14+, una aplicación inicializada y servidor ASGI/RSGI con WebSocket. Lee [WebSocket](../../../http/docs/es/websockets.md), [autenticación](../../../auth/docs/es/README.md) y [contenedor](../../../container/docs/es/README.md). El protocolo Orionis Realtime v1 requiere un cliente que implemente sus envelopes; no promete compatibilidad con SignalR.
