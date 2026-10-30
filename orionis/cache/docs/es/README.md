# Caché

Una caché guarda datos regenerables para evitar repetir consultas o cálculos. Diseña primero la clave, el tiempo de vida y la invalidación: ningún backend sustituye la fuente persistente de verdad.

## Recorrido

1. [Guardar y regenerar datos](caching-values.md): claves, TTL, cache-aside, lotes y contadores.
2. [Stores y locks](stores-and-locks.md): configuración, alcance, consistencia y extensibilidad.
3. [Artefactos derivados](source-artifacts.md): invalidación por fuentes y serialización local.

Relacionados: [orm](../../../orm/docs/es/README.md) · [foundation](../../../foundation/docs/es/README.md)

## Ejecución acotada y rendimiento

Usa `await Cache.rememberOnce(key, ttl, resolver, wait_timeout=10)` o su equivalente en el repositorio para coordinar fallos concurrentes del mismo backend, prefijo, clave y loop. Los solicitantes comparten el resultado, incluido `None`; el almacenamiento y los aciertos posteriores conservan la semántica de TTL/serialización del backend. Un productor fallido o cancelado libera la entrada para permitir reintentos. La resolución recursiva de la misma clave falla explícitamente. El registro débil no retiene claves terminadas sin solicitantes activos. `remember` y `rememberForever` conservan su comportamiento.

La opción `lease=segundos` añade el bloqueo del backend y vuelve a consultar el valor. Redis espera mediante adquisición atómica NX con TTL y libera únicamente el lease de su propietario. Es coordinación entre procesos según las garantías del backend, no ejecución exactamente una vez: los bloqueos de memoria/archivo son locales al proceso y el lease puede vencer durante el productor. Los efectos secundarios siguen necesitando idempotencia. `wait_timeout` limita cada fase de admisión local o Redis y la limpieza del lease Redis; no limita la ejecución del productor ni las lecturas/escrituras normales de caché. `multiGet`/`multiSet` de archivos usan una transición al worker por lote, conservan bloqueos, orden y TTL por clave y se detienen entre entradas al cancelar, después de terminar la operación actual.
