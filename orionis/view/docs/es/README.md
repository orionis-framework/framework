# Vistas

View renderiza HTML en el servidor mediante Jinja2 async y lo entrega como una respuesta Orionis.

## Recorrido

1. [Renderizar páginas](rendering-templates.md): contexto, pendientes, respuestas y formularios.
2. [Layouts y helpers](template-language.md): Jinja, enlaces, sesión, traducción y escape.
3. [Configuración y extensiones](configuration-and-extensions.md): loaders, caches, providers y diagnóstico.

Requiere Python 3.14+ y las dependencias Jinja2/MarkupSafe/Markdown/msgspec declaradas en el proyecto. La facade necesita una aplicación iniciada; los ejemplos con motores aislados son útiles para pruebas y extensiones.

## Ejecución acotada y rendimiento

La carga/compilación fría de la plantilla principal y las comprobaciones de auto-recarga usan un pool dedicado de dos workers y 64 pendientes. Con auto-recarga desactivada, la plantilla caliente se obtiene directamente de la caché acotada de Jinja. El render y los globals asíncronos permanecen en el loop solicitante. `await engine.warmup("page", "layouts/base", "partials/menu")` compila plantillas conocidas sin evaluar globals.

Los loaders de `include`/`extends`/imports anidados de Jinja siguen siendo síncronos dentro del renderizador. Calienta las dependencias conocidas antes de atender tráfico; los nombres dinámicos y la auto-recarga de dependencias aún pueden realizar I/O síncrono. El calentamiento no sustituye la capacidad de la caché de Jinja ni garantiza permanencia después de una expulsión. La saturación se informa mediante `WorkQueueFullError`.
