# HTTP: de la ruta a la respuesta

La capa HTTP de Orionis ofrece una API común sobre ASGI y RSGI. El mismo controlador puede recibir una solicitud normalizada, validar datos y devolver una respuesta JSON, HTML, archivo, stream o SSE. Las conexiones WebSocket utilizan una API separada sobre el mismo sistema de rutas.

Necesitas Python 3.14+, las dependencias declaradas del framework y una aplicación inicializada para utilizar facades y servicios del contenedor. Los ejemplos de funciones son código de aplicación: se ejecutan cuando el kernel atiende una petición. Los ejemplos que solo construyen respuestas pueden utilizarse sin arrancar un servidor.

## Recorrido recomendado

1. [Ciclo de petición y controladores](request-lifecycle.md): servicios, scopes y ejecución asíncrona.
2. [Rutas, parámetros y grupos](routing.md): diseña una API y organiza acceso.
3. [Entrada y validación](requests-and-validation.md): lee metadatos y cuerpos correctamente.
4. [Formularios y archivos](forms-and-uploads.md): entradas repetidas y recursos temporales.
5. [Respuestas y cookies](responses.md): JSON, vistas, redirecciones y descargas.
6. [Streaming y SSE](streaming-and-sse.md): entrega progresiva y limpieza.
7. [WebSocket](websockets.md): conexión, mensajes y middleware.
8. [Middleware y seguridad](middleware-and-security.md): CSRF, CORS, proxies y límites.
9. [Páginas y rutas predeterminadas](default-responses.md): salud, errores y autenticación opcional.

Continúa con [sesiones](../../../session/docs/es/README.md), [autenticación](../../../auth/docs/es/README.md), [schemas](../../../schemas/docs/es/README.md), [vistas](../../../view/docs/es/README.md) y [hubs Realtime](../../../realtime/docs/es/README.md).

