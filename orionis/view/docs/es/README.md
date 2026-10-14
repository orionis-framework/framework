# Vistas

View renderiza HTML en el servidor mediante Jinja2 async y lo entrega como una respuesta Orionis.

## Recorrido

1. [Renderizar páginas](rendering-templates.md): contexto, pendientes, respuestas y formularios.
2. [Layouts y helpers](template-language.md): Jinja, enlaces, sesión, traducción y escape.
3. [Configuración y extensiones](configuration-and-extensions.md): loaders, caches, providers y diagnóstico.

Requiere Python 3.14+ y las dependencias Jinja2/MarkupSafe/Markdown/msgspec declaradas en el proyecto. La facade necesita una aplicación iniciada; los ejemplos con motores aislados son útiles para pruebas y extensiones.
