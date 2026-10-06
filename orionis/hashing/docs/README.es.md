# orionis.hashing

> `orionis.hashing` ofrece hashing asíncrono de contraseñas con Argon2id y bcrypt, selección de driver, verificación y detección de actualización de costo.

## Descripción general

El paquete exporta `HashManager`, `Argon2Hasher` y `BcryptHasher`. El manager lee configuración validada, cachea drivers perezosamente y delega una API `IHasher` común. Orionis usa Argon2id por defecto; bcrypt permanece para almacenes existentes e interoperabilidad explícita.

Crear y verificar hashes consume CPU/memoria, así que ambos drivers envían el trabajo bloqueante a `asyncio.to_thread`. Los hashes codificados incluyen salt, algoritmo y costos. Este módulo hashea passwords; no cifra datos recuperables.

## Requisitos

- Python 3.14 o posterior.
- `pwdlib[argon2,bcrypt]>=0.3.1`, instalado por Orionis.
- Capacidad de worker threads y memoria suficiente para el costo configurado.
- Contenedor Orionis iniciado al usar la fachada `Hash`.

## Inicio rápido

```python
import asyncio
from orionis.hashing import Argon2Hasher


async def main() -> None:
    hasher = Argon2Hasher(memory=32, threads=1, time=1)
    encoded = await hasher.make("correct horse")
    assert await hasher.check("correct horse", encoded)
    assert not await hasher.check("wrong", encoded)
    assert not hasher.needsRehash(encoded)
    print(hasher.getAlgorithm())


asyncio.run(main())
```

Validación: **Executed successfully** en CPython 3.14.6; los costos bajos solo aceleran la ejecución documental.

## Conceptos principales

### Almacenamiento unidireccional

`make()` produce hash codificado con salt. `check()` envía candidato y hash al mismo algoritmo; el plaintext no se recupera. Guarda el resultado completo y no compares hashes directamente, porque salt aleatorio cambia cada salida.

### Driver y algoritmo

El driver `argon2` reporta `argon2id`; `bcrypt` reporta `bcrypt`. `HashManager.make/check/needsRehash` siempre usan el default. Para verificar un algoritmo legacy conocido, selecciona `manager.driver("bcrypt")`.

### Política de rehash

`needsRehash()` compara hash y parámetros actuales. Hashes vacíos, malformados o de otro algoritmo requieren rehash. Tras login exitoso, genera y persiste reemplazo si retorna `True`.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `hash_manager.py` | Configuración, selección lazy y delegación común. |
| `hashers/argon2_hasher.py` | Costos Argon2id, hashing async, verificación y rehash. |
| `hashers/bcrypt_hasher.py` | Costo bcrypt, hashing async, verificación y rehash. |
| `hashers/functions.py` | Import lazy de backend y ayuda de instalación. |
| `contracts/` | Interfaces `IHasher` e `IHashManager`. |
| `exceptions.py` | Jerarquía de errores de config, driver y dependencia. |
| `provider.py` | Binding singleton y fijación de fachada. |

## API pública

### `HashManager(app)`

Lee `hashing`, usando entidad nativa si falta. `driver(name=None)` retorna `IHasher` cacheado; `getDefaultDriver()` retorna `argon2` o `bcrypt`. `make`, `check`, `needsRehash`, `getAlgorithm` y `setRounds` del manager delegan al default.

### `Argon2Hasher(memory=65536, threads=4, time=3)`

Usa Argon2id. `memory` está en KiB, `threads` es paralelismo y `time` iteraciones. Deben ser enteros positivos; config validada además exige 8 KiB por thread. `rounds` por llamada corresponde a `time`. Setters cambian defaults y limpian backend cacheado.

### `BcryptHasher(rounds=12)`

Acepta costos enteros de 4 a 31. Overrides `memory` y `threads` se ignoran porque bcrypt no los soporta. `setRounds` cambia el default y limpia backend.

### Métodos compartidos

- `await make(value, *, rounds=None, memory=None, threads=None) -> str`
- `await check(value, hashed) -> bool`
- `needsRehash(hashed) -> bool`
- `getAlgorithm() -> str`
- `setRounds(rounds) -> Self`

## Flujos de trabajo comunes

### Registrar contraseña

Llama `await Hash.make(password)` y persiste solo el resultado. No registres input ni hash. La aplicación debe validar longitud/política antes.

### Autenticar y actualizar

Llama `await Hash.check(candidate, stored)`. Solo tras match, llama `Hash.needsRehash(stored)` y reemplaza con `await Hash.make(candidate)` si hace falta.

### Migrar bcrypt a Argon2id

Identifica registros legacy, verifica con `await manager.driver("bcrypt").check(...)` y reescribe un login exitoso con manager Argon2 default. El checker Argon2 retorna `False` para bcrypt deliberadamente.

## Ejemplos

### Usar bcrypt explícitamente

```python
import asyncio
from orionis.hashing import BcryptHasher


async def main() -> None:
    hasher = BcryptHasher(rounds=4)
    encoded = await hasher.make("secret")
    assert await hasher.check("secret", encoded)
    assert not await hasher.check("other", encoded)
    print(hasher.getAlgorithm())


asyncio.run(main())
```

Validación: **Executed successfully** en CPython 3.14.6; costo 4 acelera este ejemplo, no es recomendación productiva.

### Resolver drivers mediante manager

```python
import asyncio
from orionis.hashing import HashManager


class App:
    def config(self, name: str):
        assert name == "hashing"
        return {
            "driver": "argon2",
            "argon2": {"memory": 32, "threads": 1, "time": 1},
            "bcrypt": {"rounds": 4},
        }


async def main() -> None:
    manager = HashManager(App())
    encoded = await manager.make("password")
    assert manager.getDefaultDriver() == "argon2"
    assert await manager.check("password", encoded)
    assert manager.driver("bcrypt").getAlgorithm() == "bcrypt"
    print(manager.getAlgorithm())


asyncio.run(main())
```

Validación: **Executed successfully** en CPython 3.14.6.

### Actualizar parámetros de costo

```python
import asyncio
from orionis.hashing import Argon2Hasher


async def main() -> None:
    old = Argon2Hasher(memory=32, threads=1, time=1)
    encoded = await old.make("secret")
    stronger = Argon2Hasher(memory=64, threads=1, time=2)
    assert stronger.needsRehash(encoded)
    replacement = await stronger.make("secret")
    assert await stronger.check("secret", replacement)
    print("rehash required")


asyncio.run(main())
```

Validación: **Executed successfully** en CPython 3.14.6.

### Usar la fachada de aplicación

```python
from orionis.support.facades import Hash

encoded = await Hash.make("secret")
valid = await Hash.check("secret", encoded)
if valid and Hash.needsRehash(encoded):
    encoded = await Hash.make("secret")
```

Validación: **Import-only** en CPython 3.14.6; requiere aplicación y fachada fijada.

## Configuración

`config/hashing.py` mapea entorno a entidades congeladas:

| Ajuste | Entorno | Default | Restricción |
|---|---|---:|---|
| `hashing.driver` | `HASH_DRIVER` | `argon2` | `argon2` o `bcrypt`. |
| `hashing.argon2.memory` | `ARGON_MEMORY` | `65536` KiB | Entero positivo; al menos `8 * threads`. |
| `hashing.argon2.threads` | `ARGON_THREADS` | `4` | Entero positivo. |
| `hashing.argon2.time` | `ARGON_TIME` | `3` | Entero positivo. |
| `hashing.bcrypt.rounds` | `BCRYPT_ROUNDS` | `12` | Entero de 4 a 31. |

Ajusta costos en hardware productivo y monitorea latencia/memoria. Cambiarlos no rompe hashes anteriores; `needsRehash` señala actualización.

## Integración con Orionis

`HashProvider` es core. Vincula `IHashManager` a `HashManager` como singleton y fija `orionis.support.facades.Hash` durante boot para resolver miembros async y sync.

Autenticación, registro, password reset, seeders y modelos pueden usar fachada o inyectar `IHashManager`. Clases concretas sirven para migraciones y pruebas.

## Errores y casos límite

- Costos inválidos lanzan `HashConfigurationException`; entidades config pueden lanzar `TypeError`/`ValueError` antes.
- Driver desconocido lanza `HashDriverNotSupportedException` al resolverlo.
- Backend ausente se convierte en `MissingHashDependencyException` con ayuda `uv add`.
- `check` retorna `False` para hash vacío, malformado o extranjero; `needsRehash` retorna `True`.
- Overrides por llamada crean backend temporal y no mutan defaults.
- `setRounds` muta el driver singleton para toda aplicación; prefiere config u override salvo intención global.
- Persisten restricciones del backend, incluidas limitaciones prácticas de tamaño de password bcrypt.

## Rendimiento y concurrencia

Cada `make` y `check` usa `asyncio.to_thread`, liberando event loop pero consumiendo su pool. Argon2 consume memoria y lanes configurados; limita concurrencia de login/registro según capacidad.

Managers cachean drivers y drivers cachean clase/instancia backend. No hay locks en primer fill: hilos nativos pueden crear equivalentes y gana última escritura. Tasks del loop no ven construcción síncrona parcial. Setters mutan estado compartido y no deben competir con requests.

## Compatibilidad

Orionis declara Python 3.14+ y `pwdlib[argon2,bcrypt]>=0.3.1`. Se validó en CPython 3.14.6 Windows con ambos backends. Formatos son estándar Argon2/bcrypt, aunque costos disponibles y passwords bcrypt muy largos pueden variar por versión.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, contratos, manager, hashers, carga lazy, errores, provider/fachada, config, integraciones y `tests/hashing`. Las 180 pruebas pasaron con el runner Orionis. Cuatro programas ejecutaron hashing real; fachada solo se validó por importación.
