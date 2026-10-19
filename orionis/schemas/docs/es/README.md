# Schemas y validación

## Descripción general

Un `Schema` Orionis es un `msgspec.Struct` procesado por `SchemaMeta`. Los campos usan anotaciones Python; `Annotated`—alias `Field`—adjunta constraints, reglas, documentación y mensajes. La metaclase compila constraints y planes al crear la clase para mantener pequeño el camino exitoso.

Declaración y validación están separadas. La construcción directa confía en valores ya tipados bajo la semántica del constructor `msgspec`. `await orionis.schemas.validator.Schema.validate(payload, schema)` convierte payloads no confiables y lanza `ValidationException` con fallos por campo. La validación tiene una única entrada y siempre es asíncrona, incluso en schemas sin reglas personalizadas.

## Requisitos

- Python 3.14 o posterior; la compilación usa evaluación diferida de anotaciones.
- Imports explícitos desde `fields`, `constraints`, `metadata`, `rules`, `validator` y `exceptions`; la raíz solo exporta `Schema`.
- Conexión database iniciada para `Unique` y contexto de red/archivo para reglas que lo necesiten.

## Recorrido del módulo

- [Constraints, metadatos y referencia](constraints-and-reference.md)
- [Declarar schemas y convertir datos](declaring-schemas.md)
- [Validación, errores e integración](validation-and-errors.md)

Continúa por: [http](../../../http/docs/es/README.md) · [database](../../../database/docs/es/README.md) · [mcp](../../../mcp/docs/es/README.md).

Los ejemplos que requieren bootstrap, una solicitud o servicios externos indican su contexto. Los resultados de comprobación de esta reconstrucción se distinguen de las notas históricas; no se presupone que se haya ejecutado una integración de producción.

- [Reglas de aplicación y validación con I/O](application-rules.md)
