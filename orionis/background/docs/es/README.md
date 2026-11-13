# Tareas después de la respuesta

Una tarea de background pertenece al mismo proceso y se ejecuta después de entregar la respuesta. Úsala para efectos secundarios cortos cuya pérdida sea aceptable; el módulo queues cubre los flujos que necesitan persistencia y reintentos.

## Recorrido

1. [Ejecutar acciones después de responder](response-tasks.md): requisitos, uso progresivo, configuración, integración, errores y referencia pública.

Los ejemplos de construcción de respuestas difieren la ejecución. Para ejecutar sus tareas de background, usa una aplicación Orionis inicializada mediante boot y los providers que requiere la fachada del logger.

Relacionados: [http](../../../http/docs/es/README.md) · [queues](../../../queues/docs/es/README.md) · [logging](../../../logging/docs/es/README.md)
