# orionis.hashing

> Referencia de API derivada de la implementación actual.

## Tabla de contenido

- Requisitos
- Resumen funcional
- Estructura del módulo
- Referencia de API
- Ejemplos de uso
- Características de diseño
- Rendimiento y concurrencia
- Notas de compatibilidad
- Verificación y limitaciones

## Requisitos

Python 3.14 o superior, como declara pyproject.toml.

## Resumen funcional

El inicializador de orionis.hashing expone 3 símbolos públicos. Esta referencia usa __all__, las rutas de exportación y los archivos fuente actuales como evidencia.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| ../__init__.py | Define las exportaciones del paquete. |
| orionis.hashing/ | Implementaciones y subpaquetes de esas exportaciones. |

## Referencia de API

| Símbolo | Importación verificada | Fuente | Declaración | Comportamiento observado |
| --- | --- | --- | --- | --- |
| Argon2Hasher | from orionis.hashing import Argon2Hasher | [hashers/argon2_hasher.py](../hashers/argon2_hasher.py) | Argon2Hasher | Hash passwords with Argon2id. Argon2id won the Password Hashing Competition and is the recommended default driver of the framework. Concurrency ----------- No locks are used. The backend class and the backend instance are cached on first use: a concurrent first use from several threads may build them twice, and the last write wins. Hashing operations only read that cache, and the fluent setters drop it so later calls rebuild the backend with the new cost parameters. |
| Argon2Hasher.make | from orionis.hashing import Argon2Hasher | [hashers/argon2_hasher.py](../hashers/argon2_hasher.py) | async def make(self, value: str, *, rounds: int / None, memory: int / None, threads: int / None) -> str | Hash a plain text value off the event loop. Parameters ---------- value : str Plain text value to hash. rounds : int / None Per-call time cost override. memory : int / None Per-call memory cost override, in kibibytes. threads : int / None Per-call parallelism override. Returns ------- str Encoded Argon2id hash. Raises ------ HashConfigurationException If any override is not a positive integer. |
| Argon2Hasher.check | from orionis.hashing import Argon2Hasher | [hashers/argon2_hasher.py](../hashers/argon2_hasher.py) | async def check(self, value: str, hashed: str) -> bool | Verify a plain text value off the event loop. Parameters ---------- value : str Plain text value to verify. hashed : str Previously generated hash. Returns ------- bool ``True`` when the value matches the hash, ``False`` otherwise. |
| Argon2Hasher.needsRehash | from orionis.hashing import Argon2Hasher | [hashers/argon2_hasher.py](../hashers/argon2_hasher.py) | def needsRehash(self, hashed: str) -> bool | Determine whether the hash uses outdated Argon2id parameters. Parameters ---------- hashed : str Previously generated hash. Returns ------- bool ``True`` when the hash should be regenerated. |
| Argon2Hasher.getAlgorithm | from orionis.hashing import Argon2Hasher | [hashers/argon2_hasher.py](../hashers/argon2_hasher.py) | def getAlgorithm(self) -> str | Return the algorithm identifier of this driver. Returns ------- str Always ``'argon2id'``. |
| Argon2Hasher.setRounds | from orionis.hashing import Argon2Hasher | [hashers/argon2_hasher.py](../hashers/argon2_hasher.py) | def setRounds(self, rounds: int) -> Self | Set the default time cost used by the driver. Parameters ---------- rounds : int New number of iterations. Returns ------- Self The same instance, allowing fluent configuration. Raises ------ HashConfigurationException If the value is not a positive integer. |
| Argon2Hasher.setMemory | from orionis.hashing import Argon2Hasher | [hashers/argon2_hasher.py](../hashers/argon2_hasher.py) | def setMemory(self, memory: int) -> Self | Set the default memory cost used by the driver. Parameters ---------- memory : int New memory cost in kibibytes. Returns ------- Self The same instance, allowing fluent configuration. Raises ------ HashConfigurationException If the value is not a positive integer. |
| Argon2Hasher.setThreads | from orionis.hashing import Argon2Hasher | [hashers/argon2_hasher.py](../hashers/argon2_hasher.py) | def setThreads(self, threads: int) -> Self | Set the default parallelism used by the driver. Parameters ---------- threads : int New degree of parallelism. Returns ------- Self The same instance, allowing fluent configuration. Raises ------ HashConfigurationException If the value is not a positive integer. |
| BcryptHasher | from orionis.hashing import BcryptHasher | [hashers/bcrypt_hasher.py](../hashers/bcrypt_hasher.py) | BcryptHasher | Hash passwords with bcrypt. Kept for interoperability with existing applications that already store bcrypt hashes. Concurrency ----------- No locks are used. The backend class and the backend instance are cached on first use: a concurrent first use from several threads may build them twice, and the last write wins. Hashing operations only read that cache, and the fluent setter drops it so later calls rebuild the backend with the new cost factor. |
| BcryptHasher.make | from orionis.hashing import BcryptHasher | [hashers/bcrypt_hasher.py](../hashers/bcrypt_hasher.py) | async def make(self, value: str, *, rounds: int / None, memory: int / None, threads: int / None) -> str | Hash a plain text value off the event loop. Parameters ---------- value : str Plain text value to hash. rounds : int / None Per-call cost factor override. memory : int / None Ignored, bcrypt has no memory cost parameter. threads : int / None Ignored, bcrypt has no parallelism parameter. Returns ------- str Encoded bcrypt hash. Raises ------ HashConfigurationException If ``rounds`` falls outside the range supported by bcrypt. |
| BcryptHasher.check | from orionis.hashing import BcryptHasher | [hashers/bcrypt_hasher.py](../hashers/bcrypt_hasher.py) | async def check(self, value: str, hashed: str) -> bool | Verify a plain text value off the event loop. Parameters ---------- value : str Plain text value to verify. hashed : str Previously generated hash. Returns ------- bool ``True`` when the value matches the hash, ``False`` otherwise. |
| BcryptHasher.needsRehash | from orionis.hashing import BcryptHasher | [hashers/bcrypt_hasher.py](../hashers/bcrypt_hasher.py) | def needsRehash(self, hashed: str) -> bool | Determine whether the hash uses an outdated cost factor. Parameters ---------- hashed : str Previously generated hash. Returns ------- bool ``True`` when the hash should be regenerated. |
| BcryptHasher.getAlgorithm | from orionis.hashing import BcryptHasher | [hashers/bcrypt_hasher.py](../hashers/bcrypt_hasher.py) | def getAlgorithm(self) -> str | Return the algorithm identifier of this driver. Returns ------- str Always ``'bcrypt'``. |
| BcryptHasher.setRounds | from orionis.hashing import BcryptHasher | [hashers/bcrypt_hasher.py](../hashers/bcrypt_hasher.py) | def setRounds(self, rounds: int) -> Self | Set the default cost factor used by the driver. Parameters ---------- rounds : int New cost factor. Returns ------- Self The same instance, allowing fluent configuration. Raises ------ HashConfigurationException If the value falls outside the range supported by bcrypt. |
| HashManager | from orionis.hashing import HashManager | [hash_manager.py](../hash_manager.py) | HashManager | Expose an algorithm-agnostic hashing API. Resolve the configured password hashing driver and delegate every operation to it, so application code never depends on a concrete algorithm. Concurrency ----------- No locks are used. The only mutable state is the driver cache, written the first time a driver is resolved: a concurrent first resolution from several threads may build the same driver twice, and the last write wins. Driver resolution is synchronous and never suspends, so tasks sharing an event loop never observe a partially built cache; only the hashing work itself is awaited on a worker thread. ``setRounds`` mutates the cached driver, and the provider binds this class as a singleton, so the change is visible to the whole application. |
| HashManager.driver | from orionis.hashing import HashManager | [hash_manager.py](../hash_manager.py) | def driver(self, name: str / None) -> IHasher | Return the hasher bound to the named (or default) driver. Parameters ---------- name : str / None Driver name (``'argon2'`` or ``'bcrypt'``). ``None`` selects the configured default driver. Returns ------- IHasher Hasher instance for the requested driver, created on first access and cached afterwards. Raises ------ HashDriverNotSupportedException If the requested driver is not supported. |
| HashManager.getDefaultDriver | from orionis.hashing import HashManager | [hash_manager.py](../hash_manager.py) | def getDefaultDriver(self) -> str | Return the name of the configured default driver. Returns ------- str Driver name, such as ``'argon2'`` or ``'bcrypt'``. |
| HashManager.make | from orionis.hashing import HashManager | [hash_manager.py](../hash_manager.py) | async def make(self, value: str, *, rounds: int / None, memory: int / None, threads: int / None) -> str | Hash a plain text value with the default driver. The hashing work runs on a worker thread, so the event loop stays free while the cost parameters are burned. Parameters ---------- value : str Plain text value to hash. rounds : int / None Per-call cost override. memory : int / None Per-call memory cost override, in kibibytes. threads : int / None Per-call parallelism override. Returns ------- str Encoded hash produced by the default driver. |
| HashManager.check | from orionis.hashing import HashManager | [hash_manager.py](../hash_manager.py) | async def check(self, value: str, hashed: str) -> bool | Verify a plain text value against an encoded hash. The verification runs on a worker thread, so the event loop stays free while the hash is recomputed. Parameters ---------- value : str Plain text value to verify. hashed : str Previously generated hash. Returns ------- bool ``True`` when the value matches the hash, ``False`` otherwise. |
| HashManager.needsRehash | from orionis.hashing import HashManager | [hash_manager.py](../hash_manager.py) | def needsRehash(self, hashed: str) -> bool | Determine whether a hash was produced with outdated parameters. Parameters ---------- hashed : str Previously generated hash. Returns ------- bool ``True`` when the hash should be regenerated with the current configuration. |
| HashManager.getAlgorithm | from orionis.hashing import HashManager | [hash_manager.py](../hash_manager.py) | def getAlgorithm(self) -> str | Return the algorithm identifier of the default driver. Returns ------- str Algorithm identifier, such as ``'argon2id'`` or ``'bcrypt'``. |
| HashManager.setRounds | from orionis.hashing import HashManager | [hash_manager.py](../hash_manager.py) | def setRounds(self, rounds: int) -> Self | Set the default cost factor used by the default driver. Parameters ---------- rounds : int New cost factor. Returns ------- Self The same manager instance, allowing fluent configuration. Raises ------ HashConfigurationException If the value is not valid for the active driver. |

## Ejemplos de uso

    from orionis.hashing import Argon2Hasher

La ruta de importación coincide con la tabla de API. Estado de importación: failed: missing pwdlib.

## Características de diseño

El paquete utiliza una superficie pública explícita. Los símbolos privados no se incluyen; las declaraciones se enlazan al propietario concreto.

## Rendimiento y concurrencia

No se declara una garantía uniforme en el nivel del paquete. Inspeccione cada archivo enlazado para E/S, corutinas, cachés, bloqueos y estado compartido.

## Notas de compatibilidad

Mínimo declarado: Python 3.14. La validación usó Python 3.14.3. Los límites de dependencias están en pyproject.toml.

## Verificación y limitaciones

Se analizaron los archivos Python y se verificaron las exportaciones. Las excepciones de dependencias, callbacks, E/S o configuración pueden propagarse y no se presentan como exhaustivas.
