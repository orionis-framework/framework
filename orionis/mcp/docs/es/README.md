# Servidores MCP nativos

Orionis declara herramientas, recursos y prompts como clases Python y compila su contrato una vez para HTTP, STDIO y pruebas. El protocolo implementado en este checkout es `2026-07-28`, único valor de `SUPPORTED_VERSIONS`; verifica esa compatibilidad con el cliente que conectarás.

1. [Tu primer servidor y herramientas tipadas](servers-and-tools.md).
2. [Recursos, plantillas URI y prompts](resources-and-prompts.md).
3. [Contenido, serialización y metadata](responses-and-content.md).
4. [HTTP, STDIO y configuración](transports-and-configuration.md).
5. [Progreso, continuación, suscripciones y extensiones](advanced-workflows.md).

Requiere Python 3.14+, schemas/msgspec para contratos tipados y una aplicación inicializada para registro de transportes. Los ejemplos con `compile_server` y `McpTestClient(Container(), ServerClass)` funcionan sin servidor ni datos externos. La expansión RFC 6570 utiliza la dependencia declarada `uritemplate`; publicar recursos no otorga acceso implícito al filesystem.

El contexto de cada llamada es independiente. Ninguna anotación descriptiva de una herramienta sustituye [autenticación/autorización](../../../auth/docs/es/README.md). Los endpoints web usan el [kernel HTTP](../../../http/docs/es/README.md) y los handlers usan el [contenedor](../../../container/docs/es/README.md).
