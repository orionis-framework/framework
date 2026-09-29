# Orionis Performance (`orionis.support.performance`)

> Utilidad de cronómetro de alta resolución (`PerformanceCounter`) con APIs síncrona y asíncrona equivalentes, además de soporte como gestor de contexto (`with`/`async with`), para medir el tiempo de bloques de código.
>
> 🇬🇧 English version: [README.md](README.md)

`orionis.support.performance` provee una única clase utilitaria enfocada
— `PerformanceCounter` — para medir el tiempo transcurrido (wall-clock)
alrededor de un bloque de código (un manejador de petición, un comando
de consola, un benchmark, etc.). Envuelve `time.perf_counter()` detrás de
una API pequeña y encadenable que funciona de forma idéntica ya sea que
el código circundante sea síncrono o `async`, y expone la duración
transcurrida en varias unidades comunes. El propio kernel de consola del
framework (`orionis.console.core.reactor.Reactor`) la usa para reportar
cuánto tardó cada comando ejecutado.

---

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Descripción funcional del módulo](#descripción-funcional-del-módulo)
3. [Referencia de API](#referencia-de-api)
   - [`PerformanceCounter`](#performancecounter-orionissupportperformancecounterperformancecounter)
   - [Contrato (`IPerformanceCounter`)](#contrato-iperformancecounter)
4. [Ejemplos de uso](#ejemplos-de-uso)
5. [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
6. [Notas de diseño](#notas-de-diseño)
7. [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Requisitos

No se necesita instalación adicional además del propio framework:

```bash
pip install orionis
```

- **Python:** 3.14 o superior (el mismo mínimo que el resto del framework).
- **Dependencias:** ninguna más allá de la librería estándar de Python
  (`time`, `typing.Self`).

## Descripción funcional del módulo

| Tipo | Archivo | Clase base | Propósito |
|---|---|---|---|
| `PerformanceCounter` | [counter.py](../counter.py) | `IPerformanceCounter` (`ABC`) | Objeto cronómetro: `start()`/`stop()` (o sus equivalentes `async` `astart()`/`astop()`) registran lecturas de `time.perf_counter()`, y una familia de métodos `get*`/`aget*` convierte el tiempo transcurrido resultante a segundos, milisegundos, microsegundos o minutos. |

`PerformanceCounter` implementa el contrato `IPerformanceCounter`
(definido en `orionis/support/performance/contracts/counter.py`) y se
re-exporta directamente desde el paquete:

```python
from orionis.support.performance import PerformanceCounter
```

---

## Referencia de API

### `PerformanceCounter` (`orionis.support.performance.counter.PerformanceCounter`)

```python
PerformanceCounter() -> None
```

Un objeto basado en `__slots__` (`_start_time`, `_diff_time`,
`_diff_time`, `_is_async_mode`) sin argumentos de constructor. Todos los
métodos de "inicio" y "parada" devuelven `self`, por lo que las llamadas
se pueden encadenar; todos los métodos "get" leen el tiempo transcurrido
registrado por el último ciclo `start()`/`stop()` (o `astart()`/
`astop()`).

| Método | Firma | Descripción |
|---|---|---|
| `start` | `start() -> PerformanceCounter` | Registra la lectura actual de `time.perf_counter()` como el tiempo de inicio, borra el resultado anterior y marca la instancia en modo **síncrono**. Devuelve `self`. |
| `astart` | `astart() -> PerformanceCounter` *(async)* | Igual que `start()`, pero marca la instancia en modo **asíncrono**. Devuelve `self`. |
| `stop` | `stop() -> PerformanceCounter` | Lee el reloj y calcula el tiempo transcurrido desde `start()`. Devuelve `self`. Lanza `RuntimeError` si el contador se inició con `astart()` (usar `astop()` en su lugar) o `ValueError` si nunca se inició. |
| `astop` | `astop() -> PerformanceCounter` *(async)* | Registra el tiempo final y calcula el tiempo transcurrido desde `astart()`. Devuelve `self`. Lanza `RuntimeError` si el contador se inició con `start()` (usar `stop()` en su lugar). |
| `elapsedTime` | `elapsedTime() -> float` | Tiempo transcurrido en segundos desde el último ciclo `start()`/`stop()` completado. Lanza `ValueError` si el contador no se ha iniciado y detenido. |
| `aelapsedTime` | `aelapsedTime() -> float` *(async)* | Equivalente asíncrono de `elapsedTime()`. Mismo comportamiento de `ValueError`. |
| `getSeconds` / `agetSeconds` | `getSeconds() -> float` | Tiempo transcurrido en segundos — un alias de `elapsedTime()`/`aelapsedTime()`. |
| `getMilliseconds` / `agetMilliseconds` | `getMilliseconds() -> float` | Tiempo transcurrido en milisegundos (`elapsed * 1_000`). |
| `getMicroseconds` / `agetMicroseconds` | `getMicroseconds() -> float` | Tiempo transcurrido en microsegundos (`elapsed * 1_000_000`). |
| `getMinutes` / `agetMinutes` | `getMinutes() -> float` | Tiempo transcurrido en minutos (`elapsed / 60`). |
| `restart` | `restart() -> PerformanceCounter` | Limpia las lecturas de fin/transcurrido e inmediatamente registra un nuevo tiempo de inicio en modo **síncrono**. Devuelve `self`. |
| `arestart` | `arestart() -> PerformanceCounter` *(async)* | Igual que `restart()`, pero marca la instancia en modo **asíncrono**. Devuelve `self`. |
| `__enter__` / `__exit__` | — | `with PerformanceCounter() as counter:` llama a `start()` al entrar y a `stop()` al salir (incluso si el bloque lanza una excepción). |
| `__aenter__` / `__aexit__` | — | `async with PerformanceCounter() as counter:` llama a `astart()` al entrar y a `astop()` al salir (incluso si el bloque lanza una excepción). |

Todos los métodos de acceso `get*`/`aget*` (`elapsedTime`, `getSeconds`,
`getMilliseconds`, `getMicroseconds`, `getMinutes`, y sus equivalentes
con prefijo `a`) lanzan `ValueError` con el mensaje *"Counter has not
been started and stopped properly."* si aún no existe un ciclo de
medición completo (es decir, `stop()`/`astop()` nunca se llamó después
de `start()`/`astart()`).

### Contrato (`IPerformanceCounter`)

`orionis/support/performance/contracts/counter.py` define
`IPerformanceCounter` como un `abc.ABC` (`__slots__ = ()`) con
declaraciones `@abstractmethod` que reflejan cada método público de
`PerformanceCounter` (docstrings incluidos, sin implementación). Existe
para que otros módulos — como el kernel `Reactor` de consola, que recibe
un `PerformanceCounter` mediante inyección de dependencias tipado como
`IPerformanceCounter` — puedan depender de la interfaz en lugar de la
clase concreta.

---

## Ejemplos de uso

### Inicio/parada manual (síncrono)

```python
import time
from orionis.support.performance import PerformanceCounter

counter = PerformanceCounter()
counter.start()
time.sleep(0.05)
counter.stop()

print(f"{counter.getMilliseconds():.2f} ms")
print(f"{counter.elapsedTime():.4f} s")
```

### Gestor de contexto `with` (síncrono)

```python
import time
from orionis.support.performance import PerformanceCounter

with PerformanceCounter() as counter:
    time.sleep(0.05)

print(f"El bloque tardó {counter.getSeconds():.4f} s")
```

### Gestor de contexto `async with` (asíncrono)

```python
import asyncio
from orionis.support.performance import PerformanceCounter

async def main() -> None:
    async with PerformanceCounter() as counter:
        await asyncio.sleep(0.05)
    print(f"El bloque tardó {await counter.agetMilliseconds():.2f} ms")

asyncio.run(main())
```

### Reutilizar una instancia con `restart()`

```python
import time
from orionis.support.performance import PerformanceCounter

counter = PerformanceCounter()
counter.start()
time.sleep(0.02)
counter.stop()
print(f"Primera medición: {counter.getMilliseconds():.2f} ms")

counter.restart()
time.sleep(0.04)
counter.stop()
print(f"Segunda medición: {counter.getMilliseconds():.2f} ms")
```

### Mezclar modos síncrono/asíncrono lanza `RuntimeError`

```python
import asyncio
from orionis.support.performance import PerformanceCounter

async def main() -> None:
    counter = PerformanceCounter()
    await counter.astart()
    try:
        counter.stop()  # se inició con astart(), debe detenerse con astop()
    except RuntimeError as exc:
        print(exc)  # "Cannot use stop() after astart(). Use astop() instead."

asyncio.run(main())
```

---

## Consideraciones de rendimiento y concurrencia

- `PerformanceCounter` usa `time.perf_counter()`, un reloj monotónico de
  alta resolución pensado específicamente para medir duraciones cortas
  — **no** es tiempo de calendario/reloj de pared y su valor absoluto no
  tiene significado fuera de calcular diferencias entre dos lecturas del
  mismo proceso.
- La clase está basada en `__slots__` (`_start_time`, `_diff_time`,
  `_is_async_mode`), por lo que cada instancia tiene una
  huella de memoria pequeña y fija, sin el costo de un `__dict__` por
  instancia.
- Los métodos con prefijo `a` (`astart`, `astop`, `aelapsedTime`,
  `agetSeconds`, `agetMilliseconds`, `agetMicroseconds`, `agetMinutes`,
  `arestart`) son `async def` por simetría de API y para integrarse
  limpiamente con puntos de llamada `async`/`await` (como `async with`),
  pero **no realizan ninguna E/S asíncrona real ni esperan nada
  internamente** — la medición en sí siempre es una llamada síncrona a
  `time.perf_counter()`.
- `start()`/`stop()` y `astart()`/`astop()` son mutuamente excluyentes en
  la misma instancia: mezclarlos (por ejemplo, `astart()` seguido de
  `stop()`) lanza `RuntimeError` en lugar de producir silenciosamente una
  lectura incorrecta. `restart()`/`arestart()` reinician esta bandera de
  modo junto con el estado de tiempo.
- Una instancia de `PerformanceCounter` **no es segura para hilos** y no
  está pensada para compartirse entre tareas/hilos concurrentes: guarda
  un único estado mutable de inicio/transcurrido, por lo que medir
  varias operaciones superpuestas requiere una instancia por operación
  (o reutilizar una instancia secuencialmente vía `restart()`).
- Todas las operaciones son `O(1)` y usan estado de tamaño fijo. Las
  lecturas del reloj y las operaciones aritméticas crean objetos `float`,
  y cada llamada `async def` esperada crea un objeto coroutine; no hay
  iteración ni E/S externa.

## Notas de diseño

- **API fluida/encadenable**: `start()`, `stop()`, `astart()`,
  `astop()`, `restart()` y `arestart()` devuelven todos `self`,
  permitiendo patrones como `PerformanceCounter().start()` en una sola
  expresión.
- **Modos síncrono/asíncrono explícitos**: en lugar de soportar
  silenciosamente el uso mezclado, `PerformanceCounter` rastrea
  `_is_async_mode` y lanza `RuntimeError` en llamadas `stop`/`astop`
  no coincidentes — esto hace que el uso incorrecto falle rápido en
  lugar de producir una duración engañosa.
- **Soporte de gestor de contexto (ambas variantes)**: `__enter__`/
  `__exit__` y `__aenter__`/`__aexit__` se implementan directamente en
  la clase (en lugar de vía `contextlib`), deteniendo siempre el
  contador al salir — incluso si el bloque `with`/`async with` lanza una
  excepción — reflejando la limpieza garantizada estilo
  `contextlib.ExitStack`.
- **Diseño basado en interfaz primero**: `IPerformanceCounter` (un
  `abc.ABC` solo con declaraciones `@abstractmethod`) permite que otros
  componentes del framework, como `orionis.console.core.reactor.Reactor`,
  dependan del contador y lo reciban por inyección de dependencias
  usando el tipo de interfaz en lugar de la clase concreta
  `PerformanceCounter`.
- **`__slots__` para un objeto tipo valor**: al ser una utilidad de
  medición de tiempo pequeña e instanciada con frecuencia,
  `PerformanceCounter` evita el `__dict__` por instancia declarando
  `__slots__` para sus tres atributos.

## Notas de compatibilidad

- Requiere **Python 3.14+**, en línea con el resto del framework
  `orionis` (`requires-python = ">=3.14"` en `pyproject.toml`).
- Sin dependencias de terceros; solo usa `time` y `typing.Self` de la
  librería estándar.
- Sin comportamiento específico de plataforma; `time.perf_counter()`
  está disponible y se comporta de forma consistente en las plataformas
  que el propio Python soporta.
- Se usa internamente en `orionis.console.core.reactor.Reactor` (el
  kernel de consola del framework) para medir la ejecución de comandos,
  pero el módulo en sí no depende del resto del framework más allá de
  su propio contrato.
