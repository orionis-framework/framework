# Logging

El logger registra eventos de aplicación en archivos UTF-8 con un canal activo y filtros de severidad.

## Recorrido

1. [Registrar eventos](writing-logs.md): facade, inyección, severidad y diagnóstico.
2. [Rotación y operación](rotation-and-lifecycle.md): configuración, retención, recarga y concurrencia.

Relacionados: [foundation](../../../foundation/docs/es/README.md) · [failure](../../../failure/docs/es/README.md)

## Ejecución acotada y rendimiento

Configura `LOG_QUEUE_CAPACITY=1024`, `Application(...).withConfigLogging(queue_capacity=1024)` o el campo de configuración `Logging` para trasladar emisión, rotación y compresión a colas acotadas en segundo plano. Cero, el valor predeterminado, conserva la emisión síncrona. La capacidad se aplica por handler. Una cola llena lanza `queue.Full` en todos los niveles, incluido crítico; no descarta silenciosamente ni vuelve al I/O bloqueante. Los fallos del destino se notifican con `LoggingDeliveryError` en una emisión posterior, flush o cierre.

`await logger.aclose()` detiene la admisión, vacía los registros aceptados y cierra todos los handlers, notificando fallos después de la limpieza. El apagado HTTP/CLI drena el registro configurado en cola después de los callbacks de ciclo de vida, incluso si un callback falla. Los loggers independientes deben cerrarse explícitamente. Estas colas no garantizan entrega durable ante terminación del proceso ni añaden bloqueos de rotación entre procesos.
