# Ejecución asíncrona

Loop reúne la creación de loops, el despacho de callables y los puentes síncronos. Empieza por distinguir si tu código ya está dentro de un loop: esa decisión determina qué operación usar.

## Recorrido

1. [Conectar código síncrono y asíncrono](async-execution.md): requisitos, uso progresivo, configuración, integración, errores y referencia pública.

Los ejemplos usan `Loop` directamente, sin iniciar una aplicación. Distingue los loops prestados de los propios antes de decidir cómo cerrar sus recursos.

Relacionados: [background](../../../background/docs/es/README.md) · [foundation](../../../foundation/docs/es/README.md)
