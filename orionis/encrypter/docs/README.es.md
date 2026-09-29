# Orionis Encrypter (`orionis.encrypter`)

> Servicio de cifrado simétrico AES, síncrono, expuesto mediante el contrato
> `IEncrypter` y la facade `Crypt`.
>
> 🇬🇧 English version: [README.md](README.md)

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja](#dónde-encaja)
  - [Mapa del módulo](#mapa-del-módulo)
  - [Formato del payload](#formato-del-payload)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [`IEncrypter`](#iencrypter)
  - [`Encrypter`](#encrypter)
    - [Atributos de clase](#atributos-de-clase)
    - [`Encrypter.__init__()`](#encrypter__init__)
    - [`Encrypter.encrypt()`](#encrypterencrypt)
    - [`Encrypter.decrypt()`](#encrypterdecrypt)
    - [Helpers internos](#helpers-internos)
  - [`EncrypterProvider`](#encrypterprovider)
  - [Facade `Crypt`](#facade-crypt)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Cifrar con la configuración de la aplicación](#cifrar-con-la-configuración-de-la-aplicación)
  - [Elegir el cipher explícitamente](#elegir-el-cipher-explícitamente)
  - [Manejo de errores](#manejo-de-errores)
  - [Resolver el servicio y la facade](#resolver-el-servicio-y-la-facade)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

`orionis.encrypter` convierte una cadena en un sobre autodescriptivo
codificado en base64, y viceversa, usando AES en modo CBC o GCM. La clave y
el modo provienen de la configuración de la aplicación (`app.key` y
`app.cipher`), de modo que quien lo usa nunca manipula material de clave,
vectores de inicialización, relleno PKCS7 ni etiquetas de autenticación.

### Dónde encaja

| Componente | Relación |
|---|---|
| `orionis.foundation.contracts.application.IApplication` | Se lee al construir, mediante `app.config("app.key")` y `app.config("app.cipher")`. |
| `orionis.foundation.config.app.enums.ciphers.Cipher` | Origen de `Encrypter.SUPPORTED_CIPHERS`. |
| `orionis.container.providers` | `EncrypterProvider` extiende `ServiceProvider` y `DeferrableProvider`. |
| `orionis.support.facades.encrypter.Crypt` | Facade cuyo accessor es `IEncrypter`; la fija `EncrypterProvider.boot()`. |
| `orionis.view.globals.bcrypt` | Construye los globals de plantilla `encrypt` / `decrypt` con `await app.make(IEncrypter)`. |
| `orionis.support.types.stringable.Stringable` | Sus métodos `encrypt()` / `decrypt()` delegan en la facade `Crypt`. |

### Mapa del módulo

| Archivo | Contenido |
|---|---|
| `orionis/encrypter/__init__.py` | Exporta `Encrypter` (`__all__ = ["Encrypter"]`). |
| `orionis/encrypter/encrypter.py` | `_Payload` (`msgspec.Struct` privado) y `Encrypter`. |
| `orionis/encrypter/provider.py` | `EncrypterProvider`. |
| `orionis/encrypter/contracts/__init__.py` | Exporta `IEncrypter` (`__all__ = ["IEncrypter"]`). |
| `orionis/encrypter/contracts/encrypter.py` | Contrato abstracto `IEncrypter`. |

### Formato del payload

`encrypt()` devuelve `base64(json(_Payload))`. `_Payload` es un
`msgspec.Struct` declarado con `gc=False` y cuatro campos, en este orden:

```python
class _Payload(msgspec.Struct, gc=False):
    iv: str
    value: str
    tag: str | None
    cipher: str
```

| Campo | CBC | GCM |
|---|---|---|
| `iv` | base64 de 16 bytes aleatorios | base64 de 12 bytes aleatorios |
| `value` | base64 del texto cifrado con relleno PKCS7 | base64 del texto cifrado sin la etiqueta final |
| `tag` | `None` | base64 de la etiqueta de autenticación de 16 bytes |
| `cipher` | nombre del cipher configurado | nombre del cipher configurado |

El sobre lleva su propio nombre de cipher, pero `decrypt()` igualmente
rechaza cualquier payload cuyo `cipher` difiera del configurado actualmente.

### Decisiones de diseño

- `Encrypter` declara `__slots__ = ("_aesgcm", "_is_gcm", "cipher", "key")` e
  `IEncrypter` declara `__slots__ = ()`, así que las instancias no arrastran
  diccionario de atributos.
- `_is_gcm` se calcula una sola vez en `__init__` (`"GCM" in self.cipher`),
  de modo que no hay búsqueda de subcadena por operación.
- El objeto `AESGCM` se construye una vez en `__init__` para los ciphers GCM
  y se reutiliza, así que el key schedule no se recalcula en cada llamada.
  Para los ciphers CBC queda en `None` y se construye un `Cipher` nuevo en
  cada operación.
- `SUPPORTED_CIPHERS` es un `ClassVar[frozenset[str]]` derivado del enum
  `Cipher`: las comprobaciones de pertenencia son O(1) y el catálogo es
  inmutable.
- `_Payload` es un `msgspec.Struct` tipado, así que un sobre malformado se
  rechaza por validación de esquema antes de tocar ninguna primitiva
  criptográfica.
- `EncrypterProvider` vincula `IEncrypter` como **singleton**: toda la
  aplicación comparte una instancia (y por tanto un único key schedule de
  `AESGCM`).
- `EncrypterProvider` es un `ServiceProvider` normal, no uno diferido, así que
  su `boot()` corre en el arranque de la aplicación y la facade `Crypt` queda
  fijada antes de atender ninguna petición. Los consumidores síncronos dependen
  de ello.

## Referencia de API

### `IEncrypter`

Ubicación: `orionis/encrypter/contracts/encrypter.py`. También se reexporta
desde `orionis.encrypter.contracts`.

```python
class IEncrypter(ABC):

    __slots__ = ()

    @abstractmethod
    def encrypt(self, plaintext: str) -> str: ...

    @abstractmethod
    def decrypt(self, payload: str) -> str: ...
```

Miembros abstractos: `encrypt` y `decrypt`. Ambos se declaran sin cuerpo, así
que una subclase que no los implemente no se puede instanciar.

`__slots__ = ()` implica que las subclases que declaren sus propios
`__slots__` quedan libres de `__dict__` por instancia.

### `Encrypter`

Ubicación: `orionis/encrypter/encrypter.py`. Única implementación concreta de
`IEncrypter` que trae el framework.

```python
class Encrypter(IEncrypter):

    __slots__ = ("_aesgcm", "_is_gcm", "cipher", "key")
```

Atributos de instancia, todos asignados en `__init__`:

| Atributo | Tipo | Significado |
|---|---|---|
| `key` | `bytes` | Clave AES en crudo, tal como la devuelve `app.config("app.key")`. |
| `cipher` | `str` | Nombre del cipher configurado. |
| `_is_gcm` | `bool` | Indica si el cipher configurado opera en modo GCM. |
| `_aesgcm` | `AESGCM \| None` | Helper AEAD cacheado para GCM, `None` para CBC. |

#### Atributos de clase

| Nombre | Valor | Uso |
|---|---|---|
| `AES_128_KEY_SIZE` | `16` | Longitud de clave exigida por los ciphers `AES-128-*`. |
| `AES_256_KEY_SIZE` | `32` | Longitud de clave exigida por los ciphers `AES-256-*`. |
| `CBC_IV_SIZE` | `16` | Longitud del IV generado y validado en CBC. |
| `GCM_IV_SIZE` | `12` | Longitud del IV generado y validado en GCM. |
| `GCM_TAG_SIZE` | `16` | Longitud de la etiqueta de autenticación en GCM. |
| `PKCS7_BLOCK_SIZE` | `16` | Tamaño de bloque usado para el relleno y su validación. |
| `SUPPORTED_CIPHERS` | `ClassVar[frozenset[str]]` | `{'AES-128-CBC', 'AES-128-GCM', 'AES-256-CBC', 'AES-256-GCM'}`, construido desde el enum `Cipher`. |

#### `Encrypter.__init__()`

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `app` | `IApplication` | Objeto que da acceso a la configuración. Solo se leen `app.config("app.key")` y `app.config("app.cipher")`; no hay comprobación `isinstance`, así que sirve cualquier objeto que exponga `config(path)`. |

**Devuelve:** `None`.

**Lanza:** `ValueError` cuando el cipher configurado no está en
`SUPPORTED_CIPHERS`, cuando un cipher `AES-128-*` no recibe una clave de 16
bytes, o cuando un cipher `AES-256-*` no recibe una clave de 32 bytes.

**Efectos secundarios:** construye y cachea una instancia de `AESGCM` cuando
el cipher opera en modo GCM. Sin E/S y sin registros en el contenedor.

#### `Encrypter.encrypt()`

```python
def encrypt(
    self,
    plaintext: str,
) -> str:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `plaintext` | `str` | Texto a cifrar. Se codifica como UTF-8 antes de llegar al cipher. |

**Devuelve:** `str` — el sobre codificado en base64 descrito en
[Formato del payload](#formato-del-payload).

**Lanza:**

| Excepción | Condición |
|---|---|
| `TypeError` | `plaintext` no es `str` (mensaje: `Plaintext must be a string`). |
| `ValueError` | `plaintext` está vacío (`Plaintext cannot be empty`). |
| `ValueError` | `plaintext.encode("utf-8")` falla, por ejemplo ante un sustituto suelto (`UTF-8 encoding error: ...`). |
| `RuntimeError` | Cualquier fallo lanzado por la rama del cipher, envuelto como `Error during encryption: ...`. |

**Efectos secundarios:** obtiene un IV nuevo de `os.urandom` en cada llamada
(`CBC_IV_SIZE` o `GCM_IV_SIZE` bytes), así que dos llamadas con el mismo
texto nunca devuelven el mismo payload. No muta el estado de la instancia.

#### `Encrypter.decrypt()`

```python
def decrypt(
    self,
    payload: str,
) -> str:
```

| Parámetro | Tipo | Descripción |
|---|---|---|
| `payload` | `str` | Sobre producido previamente por `encrypt()`. |

**Devuelve:** `str` — el texto plano recuperado, decodificado como UTF-8.

**Lanza:**

| Excepción | Condición |
|---|---|
| `TypeError` | `payload` no es `str` (`Payload must be a string`). |
| `ValueError` | `payload` está vacío (`Payload cannot be empty`). |
| `ValueError` | El base64 exterior o el sobre JSON está malformado, o falta un campo obligatorio (`Invalid payload: ...`). |
| `ValueError` | Un campo base64 interno no se puede decodificar (`Error decoding payload data: ...`). |
| `ValueError` | El sobre lo produjo otro cipher (`Payload cipher '...' does not match configured cipher '...'`). |
| `ValueError` | La longitud del IV no corresponde al modo (`Invalid IV for GCM: ...` / `Invalid IV for CBC: ...`). |
| `RuntimeError` | Todo lo lanzado desde la etapa de descifrado, envuelto como `Error during decryption: ...`. |

Las familias de `ValueError` anteriores las lanza la etapa de validación,
antes de ejecutar ninguna primitiva criptográfica. Una vez empieza el
descifrado, **todos** los fallos afloran como `RuntimeError`, incluidos la
etiqueta GCM ausente, una etiqueta de tamaño incorrecto, un relleno PKCS7
inválido y una autenticación GCM fallida.

**Efectos secundarios:** ninguno. Sin E/S y sin mutación del estado de la
instancia.

#### Helpers internos

Métodos privados de `Encrypter`, listados porque determinan qué tipo de
excepción llega a quien llama.

| Método | Etapa | Lanza |
|---|---|---|
| `__decodePayload(payload)` | Validación | `ValueError` — `Invalid payload: ...` |
| `__extractPayloadData(data)` | Validación | `ValueError` — `Error decoding payload data: ...` |
| `__validateCipherMatch(cipher)` | Validación | `ValueError` — cipher incompatible |
| `__validateIvSize(iv)` | Validación | `ValueError` — longitud de IV incorrecta |
| `__performDecryption(value, iv, tag)` | Descifrado | `RuntimeError` — envuelve todo lo de abajo |
| `__encryptCBC(data)` | Cifrado | `RuntimeError` — `Error in CBC encryption: ...` |
| `__decryptCBC(ct, iv)` | Descifrado | `ValueError` con datos vacíos y relleno PKCS7 inválido, `RuntimeError` en el resto |
| `__encryptGCM(data)` | Cifrado | `RuntimeError` — `Error in GCM encryption: ...` |
| `__decryptGCM(value, iv, tag)` | Descifrado | `ValueError` cuando `tag` es `None`, `RuntimeError` en el resto |

`__decryptCBC` rechaza un byte de relleno igual a `0`, un byte de relleno
mayor que `PKCS7_BLOCK_SIZE` y un bloque de relleno cuyos bytes no sean todos
iguales a la longitud declarada.

### `EncrypterProvider`

Ubicación: `orionis/encrypter/provider.py`.

```python
class EncrypterProvider(ServiceProvider):

    def register(self) -> None: ...

    async def boot(self) -> None: ...
```

| Miembro | Comportamiento |
|---|---|
| `register()` | Llama a `self.app.singleton(IEncrypter, Encrypter)`. Nada más. |
| `boot()` | Hace `await` de `Crypt.pin()`, de modo que los accesos posteriores a la facade evitan la resolución por contenedor. No registra ningún binding. |

El constructor lo aporta `ServiceProvider`: `EncrypterProvider(app)` guarda
el contenedor en `self.app`.

El provider figura en `CORE_PROVIDERS`
(`orionis/foundation/core_providers.py`), así que una aplicación obtiene
`IEncrypter` vinculado sin registrar nada a mano. **No** es un
`DeferrableProvider`: diferirlo dejaría la facade `Crypt` sin fijar hasta que
algo resolviera `IEncrypter`, y la primera llamada síncrona de un consumidor
como `Stringable.encrypt()` recibiría un objeto `_FacadeDispatch` en lugar de
una cadena.

### Facade `Crypt`

Ubicación: `orionis/support/facades/encrypter.py`.

```python
class Crypt(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        return IEncrypter
```

La facade resuelve `IEncrypter` desde el contenedor. `EncrypterProvider.boot()`
la fija durante el arranque de la aplicación, así que bajo el runtime de CLI o
HTTP `Crypt.encrypt(...)` y `Crypt.decrypt(...)` son llamadas síncronas
normales — que es justo de lo que dependen `Stringable.encrypt()` y
`Stringable.decrypt()`. En un script suelto que solo importa `bootstrap.app`,
el arranque no ha ocurrido, la facade sigue sin fijar y el acceso a atributos
devuelve un objeto `_FacadeDispatch` que hay que awaitar. El stub
`orionis/support/facades/encrypter.pyi` existe solo para el autocompletado
del editor y nunca se ejecuta.

## Ejemplos de uso

### Cifrar con la configuración de la aplicación

`Encrypter` lee `app.key` y `app.cipher` directamente del contenedor, así que
se puede construir sin registrar el provider.

```python
from bootstrap.app import app
from orionis.encrypter.encrypter import Encrypter

crypt = Encrypter(app)

token = crypt.encrypt("card-4111111111111111")
print("cipher:", crypt.cipher)
print("token is a string:", isinstance(token, str))
print("recovered:", crypt.decrypt(token))
```

Salida con la configuración por defecto de este repositorio:

```text
cipher: AES-256-CBC
token is a string: True
recovered: card-4111111111111111
```

### Elegir el cipher explícitamente

`__init__` solo llama a `config(path)`, de modo que cualquier objeto que
exponga ese método puede aportar la clave y el cipher. Es la forma que usan
las pruebas unitarias.

```python
import base64

import msgspec.json

from orionis.encrypter.encrypter import Encrypter


class StaticConfig:
    """Any object exposing config(path) satisfies what Encrypter reads."""

    def __init__(self, key: bytes, cipher: str) -> None:
        self._values = {"app.key": key, "app.cipher": cipher}

    def config(self, path: str) -> object:
        return self._values[path]


crypt = Encrypter(StaticConfig(b"\x11" * 32, "AES-256-GCM"))

token = crypt.encrypt("Orionis")
envelope = msgspec.json.decode(base64.b64decode(token))

print("fields:", sorted(envelope))
print("cipher:", envelope["cipher"])
print("iv bytes:", len(base64.b64decode(envelope["iv"])))
print("tag bytes:", len(base64.b64decode(envelope["tag"])))
print("recovered:", crypt.decrypt(token))
print("payloads differ:", crypt.encrypt("Orionis") != token)
```

Salida:

```text
fields: ['cipher', 'iv', 'tag', 'value']
cipher: AES-256-GCM
iv bytes: 12
tag bytes: 16
recovered: Orionis
payloads differ: True
```

### Manejo de errores

Los fallos de validación lanzan `ValueError`; todo lo que falla dentro de la
etapa criptográfica lanza `RuntimeError`.

```python
import base64

import msgspec.json

from orionis.encrypter.encrypter import Encrypter


class StaticConfig:
    """Any object exposing config(path) satisfies what Encrypter reads."""

    def __init__(self, key: bytes, cipher: str) -> None:
        self._values = {"app.key": key, "app.cipher": cipher}

    def config(self, path: str) -> object:
        return self._values[path]


cbc = Encrypter(StaticConfig(b"\x11" * 32, "AES-256-CBC"))
gcm = Encrypter(StaticConfig(b"\x11" * 32, "AES-256-GCM"))

# 1. Rejected before any cipher work happens.
try:
    cbc.encrypt("")
except ValueError as exc:
    print("empty ->", exc)

# 2. A payload produced by another cipher is refused.
try:
    cbc.decrypt(gcm.encrypt("Orionis"))
except ValueError as exc:
    print("mismatch ->", exc)

# 3. A malformed envelope never reaches the cipher.
try:
    cbc.decrypt("abcde")
except ValueError as exc:
    print("malformed ->", exc)

# 4. A tampered GCM ciphertext fails authentication.
token = gcm.encrypt("Orionis")
envelope = msgspec.json.decode(base64.b64decode(token))
envelope["value"] = base64.b64encode(b"\x00" * 7).decode()
tampered = base64.b64encode(msgspec.json.encode(envelope)).decode()

try:
    gcm.decrypt(tampered)
except RuntimeError as exc:
    print("tampered ->", exc)

# 5. Configuration errors surface when the service is built.
try:
    Encrypter(StaticConfig(b"\x11" * 16, "AES-256-CBC"))
except ValueError as exc:
    print("key length ->", exc)
```

Salida:

```text
empty -> Plaintext cannot be empty
mismatch -> Payload cipher 'AES-256-GCM' does not match configured cipher 'AES-256-CBC'
malformed -> Invalid payload: Invalid base64-encoded string: number of data characters (5) cannot be 1 more than a multiple of 4
tampered -> Error during decryption: Error in GCM decryption: 
key length -> Key must be 32 bytes for AES-256
```

La línea `Error in GCM decryption:` termina sin detalle porque la excepción
subyacente `InvalidTag` no lleva mensaje.

### Resolver el servicio y la facade

El framework arranca `EncrypterProvider`, así que `IEncrypter` ya está
vinculado y la facade `Crypt` queda fijada en cuanto arranca el runtime de CLI
o HTTP. El script siguiente corre fuera de ese runtime, por eso awaita la
facade; dentro de una aplicación arrancada el `await` sobra.

```python
import asyncio

from bootstrap.app import app
from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.support.facades.encrypter import Crypt


async def main() -> None:
    service = await app.make(IEncrypter)
    print("resolved:", type(service).__name__)
    print("singleton:", service is await app.make(IEncrypter))

    token = await Crypt.encrypt("through the facade")
    print("facade returns:", type(token).__name__)
    print("recovered:", await Crypt.decrypt(token))


asyncio.run(main())
```

Salida:

```text
resolved: Encrypter
singleton: True
facade returns: str
recovered: through the facade
```

## Consideraciones de rendimiento y concurrencia

- Toda la API pública es **síncrona**. `encrypt()` y `decrypt()` nunca hacen
  `await`, nunca tocan el sistema de archivos ni la red, y nunca invocan al
  contenedor.
- Las instancias no arrastran `__dict__` (verificado:
  `hasattr(encrypter, "__dict__")` es `False`), porque `Encrypter` declara
  `__slots__` e `IEncrypter` declara `__slots__ = ()`.
- GCM construye su helper `AESGCM` una vez por instancia; CBC construye un
  objeto `Cipher` nuevo en cada llamada a `encrypt()` y `decrypt()`.
- Cada llamada a `encrypt()` lee entropía nueva de `os.urandom`
  (16 bytes en CBC, 12 en GCM).
- La codificación y decodificación del payload pasan por `msgspec.json`, y
  `_Payload` se declara con `gc=False`, así que el recolector de basura no
  rastrea la estructura.
- Ambas operaciones mantienen en memoria el texto plano y el texto cifrado
  completos; no hay API de streaming ni por bloques.
- Después de `__init__`, `encrypt()` y `decrypt()` solo leen `key`, `cipher`,
  `_is_gcm` y `_aesgcm`; ningún método los reasigna.

> ⚠️ El código fuente no declara ninguna garantía de thread-safety ni de
> concurrencia: el módulo no usa locks ni primitivas de `asyncio`.

## Notas de compatibilidad

- **Python:** el proyecto declara `requires-python = ">=3.14"` en
  `pyproject.toml`. El módulo usa anotaciones `X | None` evaluadas de forma
  perezosa (PEP 649) y evita deliberadamente
  `from __future__ import annotations`, que rompería la inyección de
  dependencias cuando el contenedor reflexiona sobre `Encrypter.__init__`.
- **Dependencias de terceros**, ambas ya requisitos base del framework — no
  hay que instalar nada extra:
  - `cryptography~=48.0` — `Cipher`, `algorithms`, `modes`, `AESGCM`.
  - `msgspec>=0.21.1` — codificación del sobre y validación de esquema.
- **Configuración:** `app.config("app.key")` debe producir una clave tipo
  bytes de exactamente 16 o 32 bytes, acorde a la familia que nombre
  `app.config("app.cipher")`. `config/app.py` lee ambos de las variables de
  entorno `APP_KEY` y `APP_CIPHER`, y la entidad de configuración `App`
  genera una clave con `SecureKeyGenerator` cuando `APP_KEY` no existe.
- **Catálogo de ciphers:** solo se aceptan los cuatro nombres de
  `SUPPORTED_CIPHERS`, derivados de
  `orionis.foundation.config.app.enums.ciphers.Cipher`. Añadir un miembro a
  ese enum cambia lo que acepta `Encrypter`.
- **Autenticación:** solo los payloads GCM llevan etiqueta de autenticación.
  Los payloads CBC guardan `tag: None` y su integridad se comprueba
  únicamente mediante la validación del relleno PKCS7.
- **Portabilidad del payload:** un payload solo lo puede descifrar una
  instancia configurada con el mismo nombre de cipher y la misma clave; la
  comprobación del cipher ocurre antes de usar la clave.
- **Cableado del contenedor:** `EncrypterProvider` forma parte de
  `CORE_PROVIDERS`, así que `IEncrypter` queda vinculado como singleton y la
  facade `Crypt` se fija durante el arranque de la aplicación. Como la caché
  compilada del bootstrap (`storage/framework/bootstrap`) no se invalida por
  cambios dentro de `orionis/`, una aplicación que ya cacheó sus providers debe
  borrar esa carpeta — o ejecutar `reactor optimize:clear` — para tomar este
  cableado.
