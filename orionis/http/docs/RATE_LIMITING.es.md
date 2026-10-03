# Límites de tasa HTTP

El limitador global se ejecuta después de resolver proxies confiables y utiliza
la IP del cliente resuelta por el transporte. Permanece deshabilitado por defecto.
Si no hay IP, conserva el comportamiento anterior y omite la comprobación.
Configura los proxies confiables y verifica que el servidor entregue la dirección
del cliente antes de depender de cuotas por IP.

```python
from orionis.foundation.config.http import HTTP, HTTPRateLimit

http = HTTP(rate_limit=HTTPRateLimit(
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window_seconds=60,
    rate_limit_store="memory",
    rate_limit_max_keys=10_000,
    rate_limit_max_events=100_000,
))
```

Ambos stores cuentan intentos aceptados en una ventana deslizante. Un intento
expira cuando cumple exactamente una ventana de antigüedad. Los rechazos no
extienden la cuota. Las respuestas 429 incluyen la duración configurada como
valor conservador de `Retry-After`.

## Store de memoria acotado

El store predeterminado conserva como máximo 10.000 clientes y 100.000 marcas de
tiempo aceptadas entre todos los clientes. `RATE_LIMIT_MAX_KEYS` y
`RATE_LIMIT_MAX_EVENTS` permiten configurar esos enteros positivos. Al alcanzar
la capacidad, conserva las cuotas activas y rechaza nuevos intentos con 429.
Los clientes existentes pueden continuar hasta agotar su cuota o la capacidad
total de marcas de tiempo. Se acota el número de objetos conservados; no son un
presupuesto exacto de bytes ni un límite para toda la memoria del proceso.

La recolección incremental revisa como máximo 64 clientes por pasada, incluso
con tráfico rechazado. Un store lleno puede rechazar conservadoramente mientras
otra pasada todavía no ha alcanzado clientes expirados. El tráfico activa la
limpieza; no existe una tarea periódica. Cuando vuelve un cliente también se
eliminan sus marcas vencidas. Un `threading.Lock` serializa las actualizaciones
entre threads y event loops. Cada proceso mantiene su propio store independiente.

## Store compartido en Redis

```python
http = HTTP(rate_limit=HTTPRateLimit(
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window_seconds=60,
    rate_limit_store="redis",
    rate_limit_redis_url="redis://127.0.0.1:6379/0",
    rate_limit_redis_prefix="my-app:http:rate-limit",
    rate_limit_redis_timeout_seconds=1,
))
```

Las variables correspondientes son `RATE_LIMIT_STORE`, `RATE_LIMIT_REDIS_URL`,
`RATE_LIMIT_REDIS_PREFIX` y `RATE_LIMIT_REDIS_TIMEOUT`. Usa `rediss://` para TLS.
Todos los workers de una misma cuota deben compartir base de datos, prefijo,
límite y ventana. Usa prefijos distintos por aplicación. Construye un store por
event loop de worker: los clientes Redis no deben compartirse entre threads.

Un script Lua elimina marcas vencidas, comprueba la cuota, agrega un intento
aceptado único y establece el TTL de forma atómica. El reloj pertenece a Redis;
los relojes de los workers Python no necesitan sincronización. Los nombres de
clave conservan hashes SHA-256 de las identidades del cliente. Cada script toca
una clave. El transporte es un cliente Redis regular; no ofrece enrutamiento
para Redis Cluster ni Sentinel.

Las conexiones son perezosas y el pool admite por defecto 100 conexiones
simultáneas; las opciones de la URL Redis pueden cambiar ajustes del pool.
El timeout abarca el intento completo, incluida la conexión. Los
reintentos automáticos están deshabilitados. Errores de conexión, timeout, pool
agotado, tipos Redis incompatibles y falta de memoria en Redis rechazan con 503
y `Retry-After: 1`. No se sustituye silenciosamente la cuota compartida por una
local. La cancelación del servidor se propaga. El cierre HTTP de la aplicación
libera las conexiones propias sin borrar cuotas; las instancias construidas
manualmente deben ejecutar `await close()`.

Las claves expiran una ventana después del último intento aceptado y cada
sorted set conserva como máximo los intentos de su cuota. Redis no aplica los
topes globales de clientes/eventos del store de memoria. Configura el límite de
memoria de Redis y utiliza `noeviction` cuando la expulsión de claves no deba
reiniciar cuotas. Reinicios, failover, persistencia, borrado administrativo y
evicción pueden perder historial; no se garantizan cuotas estrictas durante
esos eventos.

## Validación y frontera de certificación

Las suites regulares cubren capacidad sin reiniciar cuotas, expiración, ocho
event loops en threads, comandos Redis, cancelación, propiedad del cliente,
configuración del backend y respuestas 429/503. La suite optativa ejecuta Lua
real, dos clientes independientes con 100 intentos concurrentes, tres procesos
separados compartiendo una cuota, expiración, recreación del store y tipos de
clave incompatibles:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:ORIONIS_HTTP_REDIS_URL = "redis://127.0.0.1:6379/0"
.\.venv\Scripts\python.exe reactor test --start-dir="tests/http/layer/store" --file-pattern="redis_rate_limit_integration.py" --verbosity=1
```

Estas comprobaciones se ejecutaron en Windows, Python 3.14 y Redis 5.0.14.1.
El test concurrente configura timeout de 10 segundos por el coste de asyncio
debug del runner; el valor predeterminado del producto sigue siendo 1 segundo.
Son pruebas de corrección, no benchmarks ni certificación de failover o memoria
en ejecución prolongada. La certificación del despliegue debe cubrir versiones
Redis soportadas, workers Linux, TLS, autenticación, fallos de red y capacidad.
