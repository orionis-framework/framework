# Almacenar, comprobar y actualizar contraseñas

El flujo de una contraseña consta de validación, hashing, almacenamiento del resultado y comprobación en el siguiente acceso. La política de costes y la migración de algoritmos forman parte de ese mismo flujo.

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

## Diseñar el registro y el acceso

Valida la política de contraseña antes de llamar a `make()`, guarda el resultado codificado completo y verifica el siguiente intento con `check()`. No uses un hash nuevo como comparación: cada ejecución incorpora un salt y cambia el resultado. El servicio no persiste registros, limita intentos ni mantiene sesiones; esas tareas corresponden a tu flujo de autenticación.

La actualización se realiza solo después de una comprobación correcta. Si el registro es antiguo, calcula el reemplazo y persístelo con el mismo mecanismo de concurrencia que utiliza tu modelo de usuario. No reemplaces un hash después de un intento fallido. Para migrar de bcrypt, selecciona expresamente `driver("bcrypt")` al verificar los registros legados; el driver Argon2 predeterminado no selecciona automáticamente otro algoritmo.

Los costes reducidos de los ejemplos son exclusivamente para pruebas. En producción mide latencia y memoria con concurrencia real: el valor predeterminado Argon2 de `65536` KiB supone aproximadamente 64 MiB de coste de memoria por operación, además del proceso y del backend. El executor evita bloquear el loop, pero no elimina ese consumo. Limita concurrencia en el acceso y la creación de cuentas.

`HashManager` no expone `extend()`. Para una implementación propia cumple `IHasher` y, si sustituyes la selección global, `IHashManager`, y registra el servicio en el contenedor según el orden de tus providers. No modifiques `_drivers` ni dependas de los métodos privados de los hashers. Usa configuración o overrides por llamada; setters como `setRounds()` afectan la instancia compartida.

## Conceptos principales

### Almacenamiento unidireccional

`make()` produce hash codificado con salt. `check()` envía candidato y hash al mismo algoritmo; el plaintext no se recupera. Guarda el resultado completo y no compares hashes directamente, porque salt aleatorio cambia cada salida.

### Driver y algoritmo

El driver `argon2` reporta `argon2id`; `bcrypt` reporta `bcrypt`. `HashManager.make/check/needsRehash` siempre usan el default. Para verificar un algoritmo legacy conocido, selecciona `manager.driver("bcrypt")`.

### Política de rehash

`needsRehash()` compara hash y parámetros actuales. Los hashes vacíos y los que el backend seleccionado no identifica requieren rehash; otros formatos inválidos pueden propagar un error del backend. Tras login exitoso, genera y persiste reemplazo si retorna `True`.

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


### Usar la fachada de aplicación

```python
from orionis.support.facades import Hash

async def verify_example() -> None:
    encoded = await Hash.make("secret")
    valid = await Hash.check("secret", encoded)
    if valid and Hash.needsRehash(encoded):
        encoded = await Hash.make("secret")
```

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
- `check` retorna `False` para hashes vacíos o no identificados por el backend; `needsRehash` retorna `True` para esos valores. Un formato identificado pero inválido aún puede propagar un error del backend.
- Overrides por llamada crean backend temporal y no mutan defaults.
- `setRounds` muta el driver singleton para toda aplicación; prefiere config u override salvo intención global.
- Persisten restricciones del backend, incluidas limitaciones prácticas de tamaño de password bcrypt.

## Rendimiento y concurrencia

Cada `make` y `check` usa `asyncio.to_thread`, liberando event loop pero consumiendo su pool. Argon2 consume memoria y lanes configurados; limita concurrencia de login/registro según capacidad.

Managers cachean drivers y drivers cachean clase/instancia backend. No hay locks en primer fill: hilos nativos pueden crear equivalentes y gana última escritura. Tasks del loop no ven construcción síncrona parcial. Setters mutan estado compartido y no deben competir con requests.

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

## Referencia de implementación para extensiones

| Ruta | Responsabilidad |
|---|---|
| `hash_manager.py` | Configuración, selección lazy y delegación común. |
| `hashers/argon2_hasher.py` | Costos Argon2id, hashing async, verificación y rehash. |
| `hashers/bcrypt_hasher.py` | Costo bcrypt, hashing async, verificación y rehash. |
| `hashers/functions.py` | Import lazy de backend y ayuda de instalación. |
| `contracts/` | Interfaces `IHasher` e `IHashManager`. |
| `exceptions.py` | Jerarquía de errores de config, driver y dependencia. |
| `provider.py` | Binding singleton y fijación de fachada. |

---

[Índice](README.md) · [auth](../../../auth/docs/es/README.md) · [encrypter](../../../encrypter/docs/es/README.md)
