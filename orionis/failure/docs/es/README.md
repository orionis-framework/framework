# Gestión de excepciones

## Descripción general

Los límites de ejecución del framework entregan las excepciones a un handler de aplicación después del inicio exitoso. `handleFailure(exception, context)` recibe la excepción original una vez por incidente y retorna un plan `FailureHandling` o `None`. `handleResult(value, context)` recibe resultados declarados fallidos sin fabricar excepciones; su implementación predeterminada retorna `None`.

`BaseExceptionHandler` prepara logging y presentación diferidos. El runtime completa el logging bajo sus protecciones de reporte; `Catch.exception()` solicita la presentación HTTP o CLI del mismo plan sin volver a llamar al handler. La política predeterminada conserva `Throwable`, el traceback nativo en el log, el mapeo de estados HTTP, respuestas 500 seguras en producción, detalle en debug y salida CLI.

Los fallos anteriores al inicio quedan fuera de esta cobertura. El código externo que consume errores necesita un propietario explícito que notifique al runtime. La recepción permanece disponible durante el cierre; cuando empiezan a cerrarse los recursos de reporte, `context.reporting_allowed` pasa a false y el plan base deja de programar llamadas al logger.

## Requisitos

- Python 3.14 o posterior y una aplicación Orionis iniciada.
- Scope activo con `kernel` para `Catch.exception()`; `capture()` no requiere scope.
- Request o adaptador de transporte para presentación HTTP.
- Servicios de aplicación para logging, salida de consola y respuestas predeterminadas.
- Handlers personalizados que implementen el contrato de dos hooks; los overrides deben retornar el plan heredado para conservar sus efectos.

La eliminación de `report`, `handleHTTP` y `handleCLI` rompe compatibilidad. Los handlers personalizados deben migrar; no existe un despacho de compatibilidad que llame esos métodos.

## Recorrido del módulo

- [Gestionar excepciones](handling-exceptions.md)
- [Políticas de errores y referencia](policies-and-reference.md)
- [Captura después del inicio](handling-exceptions.md#captura-despues-del-inicio)
- [Migrar un handler personalizado](policies-and-reference.md#migrar-un-handler-personalizado)

Continúa por: [http](../../../http/docs/es/README.md) · [logging](../../../logging/docs/es/README.md).
