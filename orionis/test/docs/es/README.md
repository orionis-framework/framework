# Pruebas de aplicaciones

## Descripción general

`orionis.test` es la capa de pruebas asíncronas de Orionis sobre `unittest` de Python. Ofrece un `TestCase` consciente de la aplicación, un motor configurable de descubrimiento y ejecución, resultados estructurados, reportes Rich en consola y un cliente MCP en proceso que recorre la serialización JSON-RPC y el dispatcher reales.

El paquete está diseñado para pruebas del framework y de aplicaciones que necesitan inyección de dependencias de Orionis sin abandonar las aserciones, fixtures, omisiones, fallos esperados o subpruebas habituales de `unittest`.

## Requisitos

- Python 3.14 o posterior.
- Una estructura normal de aplicación Orionis cuando las pruebas requieran servicios de la aplicación.
- Módulos y métodos de prueba cuyos nombres coincidan con los patrones configurados.
- Una declaración de servidor MCP y un contenedor de aplicación arrancable para pruebas de integración MCP.

## Recorrido del módulo

- [Probar herramientas MCP dentro del proceso](mcp-testing.md)
- [Resultados, configuración y referencia](results-and-reference.md)
- [Escribir y ejecutar pruebas](writing-and-running-tests.md)

Continúa por: [foundation](../../../foundation/docs/es/README.md) · [mcp](../../../mcp/docs/es/README.md).

Los ejemplos que requieren bootstrap, una solicitud o servicios externos indican su contexto. Los resultados de comprobación de esta reconstrucción se distinguen de las notas históricas; no se presupone que se haya ejecutado una integración de producción.
