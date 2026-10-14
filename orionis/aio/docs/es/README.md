# Ejecución asíncrona

Loop reúne la creación de loops, el despacho de callables y los puentes síncronos. Empieza por distinguir si tu código ya está dentro de un loop: esa decisión determina qué operación usar.

## Recorrido

1. [Conectar código síncrono y asíncrono](async-execution.md): requisitos, uso progresivo, configuración, integración, errores y referencia pública.

Los ejemplos aislados usan objetos de aplicación mínimos; las facades requieren una aplicación Orionis inicializada y sus providers. El código fuente y los contratos determinan las capacidades descritas.

Relacionados: [background](../../../background/docs/es/README.md) · [foundation](../../../foundation/docs/es/README.md)
