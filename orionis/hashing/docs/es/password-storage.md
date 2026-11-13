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

`needsRehash()` compara el hash con los parámetros actuales del driver. Los hashes vacíos, de otro algoritmo o malformados requieren rehash; la verificación los rechaza con `False`. Indicar rehash no autentica una contraseña ni repara un registro corrupto. Tras un login exitoso, genera y persiste un reemplazo si retorna `True`.

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
- `check` retorna `False` para hashes almacenados vacíos, de otro algoritmo o malformados; `needsRehash` retorna `True` para esos valores. bcrypt valida el coste codificado, alfabeto, longitud y bits finales Base64 antes de considerar actualizado un registro.
- Overrides por llamada crean backend temporal y no mutan defaults.
- `setRounds` muta el driver singleton para toda aplicación; prefiere config u override salvo intención global.
- bcrypt admite contraseñas de hasta 72 bytes UTF-8. Crear un hash con una entrada mayor lanza `ValueError` del backend; la verificación retorna `False` sin truncar el candidato. Las restricciones de tipo del backend siguen vigentes.

## Rendimiento y concurrencia

Cada `make` y `check` usa el ejecutor dedicado de hashing, con dos llamadas activas y 14 pendientes por defecto, sin ocupar el pool predeterminado del loop. La saturación lanza `WorkQueueFullError`. Argon2 conserva sus costes de memoria y paralelismo; dimensiona un ejecutor propio según la capacidad del host.

Los managers conservan drivers y estos cargan y conservan sus backends de forma diferida. Un lock breve protege la lectura conjunta de costes, la publicación en caché y las actualizaciones de setters. La construcción del backend y el hashing se ejecutan fuera del lock. Una operación ya iniciada puede terminar con los costes anteriores, pero no puede reinstalar un backend invalidado por un setter. Configura los drivers compartidos antes de atender solicitudes; los setters siguen cambiando la política de todos los llamadores que usan esa instancia.

La cancelación espera a que termine el trabajo nativo activo antes de liberar su capacidad en el ejecutor; el trabajo en cola puede cancelarse antes de empezar. La verificación usa los costes codificados en el hash almacenado. Recibe hashes de un almacenamiento de credenciales confiable y considera esos costes al dimensionar el presupuesto de workers.

## API pública

### `HashManager(app)`

Lee `hashing`, usando entidad nativa si falta. `driver(name=None)` retorna `IHasher` cacheado; `getDefaultDriver()` retorna `argon2` o `bcrypt`. `make`, `check`, `needsRehash`, `getAlgorithm` y `setRounds` del manager delegan al default.

### `Argon2Hasher(memory=65536, threads=4, time=3, executor=None)`

Usa Argon2id. `memory` está en KiB, `threads` es paralelismo y `time` son iteraciones. Los costes deben ser enteros positivos, con al menos 8 KiB de memoria por thread. El driver limita memoria y tiempo a `2**32 - 1`, y threads a `2**24 - 1`, según la representación nativa de los parámetros. Estos máximos son límites de validación, no presupuestos prácticos de recursos. La construcción, los overrides por llamada y los setters validan la combinación completa. Un setter inválido conserva la configuración anterior. `rounds` por llamada corresponde a `time`. Los setters cambian los valores predeterminados y limpian el backend en caché.

### `BcryptHasher(rounds=12, executor=None)`

Acepta costos enteros de 4 a 31. Overrides `memory` y `threads` se ignoran porque bcrypt no los soporta. `setRounds` cambia el default y limpia backend.

Ambos hashers aceptan un `BoundedExecutor` propio mediante `executor`. Compartirlo establece un límite de capacidad conjunto para los dos algoritmos. Ciérralo con `await executor.aclose()` al finalizar su propietario; si omites el argumento, se usa el ejecutor de hashing compartido por el proceso.

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
