# Recursos, plantillas URI y prompts

Un recurso publica contenido identificable por URI; un prompt produce mensajes para una conversación. Ninguno otorga acceso implícito al filesystem ni ejecuta un modelo de lenguaje. Los handlers utilizan servicios de aplicación para obtener datos y mantienen las mismas comprobaciones de acceso que una herramienta.

## Publicar un recurso parametrizado

```python
from orionis.mcp import McpResponse, Resource, Server
from orionis.mcp.server.compiler import compile_server

class UserResource(Resource):
    uri_template = "demo://users/{user_id}"
    mime_type = "application/json"

    def handle(self, user_id: str) -> McpResponse:
        return McpResponse.structured({"id": user_id})

class DirectoryServer(Server):
    name = "Directory"
    resources = (UserResource,)

assert len(compile_server(DirectoryServer).templates) == 1
```

Declara exactamente una `uri` absoluta o `uri_template`. El handler puede recibir variables decodificadas por nombre o `McpRequest` con `uri`, `uri_variables` y parámetros. Valida autorización sobre la identidad y el registro pedido; conocer el ID no concede lectura.

Las plantillas siguen RFC 6570 nivel cuatro mediante `uritemplate`. Las formas simples se pueden invertir automáticamente; las complejas necesitan `match(uri)` síncrono static/class method que devuelva variables o `None`. El matcher comprueba que volver a expandir las variables produzca la URI original. No aceptes una URI por coincidencia parcial. Prefijos sobre listas/mappings se rechazan y el código conserva formato de booleanos, orden de mappings y escape UTF-8.

`name`, `title`, `description`, `icons`, `meta`, `cache`, `size` y `annotations` aportan catálogo. Una URI no es un comando de lectura de disco; implementa el acceso seguro en el handler y evita publicar rutas internas como contenido sensible.

## Construir un prompt reutilizable

```python
from orionis.mcp import Completion, McpResponse, Prompt, PromptArgument, Server
from orionis.mcp.server.compiler import compile_server

class ExplainPrompt(Prompt):
    arguments = (PromptArgument(name="topic", required=True),)

    def handle(self, topic: str) -> McpResponse:
        return McpResponse.text(f"Explain {topic}").asUser()

    def complete(self) -> Completion:
        return Completion(values=("sessions", "routing"))

class GuideServer(Server):
    name = "Guide"
    prompts = (ExplainPrompt,)

assert "explain" in compile_server(GuideServer).prompts
```

Los argumentos de prompt son strings; no declares un objeto JSON complejo como si fuera entrada Tool. `required=True` exige presencia. Puedes devolver varios `McpResponse` con roles `asUser()` o `asAssistant()` para construir mensajes. Las plantillas no constituyen instrucciones confiables si mezclan contenido externo; la aplicación consumidora debe conservar la procedencia de ese contenido.

`complete()` suministra sugerencias para prompts o plantillas de recurso. Puede devolver `Completion` o lista/tupla de strings, con máximo 100 valores. Recibe el contexto mediante inyección si necesita `request.params`; la comprobación de acceso ocurre antes. Argumentos o referencias desconocidas fallan como parámetros inválidos.

## Catálogos paginados

El dispatcher lista recursos, plantillas y prompts con cursores opacos y páginas acotadas. El cursor pertenece a su método; no lo construyas ni reutilices para un catálogo distinto. La visibilidad y autorización se evalúan por petición y pueden hacer que páginas cambien al cambiar identidad o datos. El cliente debe usar `nextCursor` hasta agotar resultados sin asumir acceso a todo lo listado en una llamada posterior.

Evidencia: [primitivas](../../server/primitives.py), [URI matcher](../../server/templates.py), [dispatcher](../../dispatcher.py), [metadata](../../protocol/metadata.py). Pruebas: [plantillas](../../../../tests/mcp/server/test_templates.py), [dispatcher](../../../../tests/mcp/test_dispatcher.py), [casos límite](../../../../tests/mcp/test_dispatcher_edges.py). Continúa con [serialización](responses-and-content.md).
