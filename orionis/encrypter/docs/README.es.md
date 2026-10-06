# orionis.encrypter

> Cifrado síncrono de cadenas con AES-CBC y AES-GCM, sobres JSON tipados,
> clave configurada en la aplicación y un proveedor singleton de carga inmediata.

Versión en inglés: [README.md](README.md).

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [IEncrypter](#iencrypter)
- [Encrypter](#encrypter)
- [Encrypter.__init__](#encrypter__init__)
- [Atributos y constantes](#atributos-y-constantes)
- [Encrypter.encrypt](#encrypterencrypt)
- [Encrypter.decrypt](#encrypterdecrypt)
- [Formato del payload](#formato-del-payload)
- [Etapas de error](#etapas-de-error)
- [EncrypterProvider](#encrypterprovider)
- [Integración con Crypt](#integración-con-crypt)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Ciclos de cifrado autónomos](#ciclos-de-cifrado-autónomos)
- [Manejo de errores reales](#manejo-de-errores-reales)
- [Aplicación, contenedor y fachada](#aplicación-contenedor-y-fachada)
- [Recifrado de registros locales](#recifrado-de-registros-locales)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)
- [Cobertura del código fuente](#cobertura-del-código-fuente)
- [Registro de validación](#registro-de-validación)
- [Discrepancias de docstrings](#discrepancias-de-docstrings)
- [Alcance y límites](#alcance-y-límites)

## Requisitos

Proporciona `app.config("app.key")` y `app.config("app.cipher")` antes de construir
`Encrypter`; este no aporta valores predeterminados. La clave debe ser `bytes`
en crudo, no una cadena codificada con `base64:`. Utiliza uno de los cuatro
valores exactos siguientes y una clave de la longitud correspondiente. Estas
lecturas y comprobaciones pertenecen a [Encrypter.__init__](../encrypter.py).

| Valor de cipher | Bytes de clave | Bytes de IV | Bytes de tag |
|---|---|---|---|
| `AES-128-CBC` | 16 | 16 | Ninguno |
| `AES-256-CBC` | 32 | 16 | Ninguno |
| `AES-128-GCM` | 16 | 12 | 16 |
| `AES-256-GCM` | 32 | 12 | 16 |

El catálogo procede de
[orionis/foundation/config/app/enums/ciphers.py](../../foundation/config/app/enums/ciphers.py),
`Cipher`, importado con el alias `OrionisCipher` dentro de la implementación.
El constructor no normaliza mayúsculas, separadores ni objetos enum; pasa el
`.value` del enum cuando proporciones configuración directamente.

La [entidad de configuración App](../../foundation/config/app/entities/app.py)
del framework, `App.__post_init__` / `App.__validateKey`, normaliza el cipher
y la clave, decodifica claves explícitas con `base64:` y codifica claves de
cadena ordinarias como UTF-8. Si su clave es `None`, genera una y persiste
`APP_KEY` mediante `Env.set`. Esto pertenece a la configuración, no a
`Encrypter`. Construir valores predeterminados de la aplicación puede, por
tanto, escribir un archivo de entorno local; los ejemplos usan directorios
de trabajo temporales.

El uso del contenedor y la fachada requiere además crear la aplicación y
arrancar los proveedores. `Application.create()` registra los servicios de
carga inmediata; `await Application.boot()` también espera sus métodos `boot()`
para scripts sin servidor. El arranque CLI/HTTP realiza esa fase de los
proveedores igualmente. Consulta
[Application.create / boot](../../foundation/application.py) y
[EncrypterProvider](#encrypterprovider). No hace falta un extra opcional de
cifrado ni un servicio externo; las dependencias declaradas aparecen en
[Notas de compatibilidad](#notas-de-compatibilidad).

## Descripción funcional

El módulo cifra cadenas UTF-8 no vacías y las recupera desde sobres JSON
envueltos en base64. CBC usa relleno PKCS7; GCM usa un tag de autenticación.
Ambas ramas generan un IV por llamada de cifrado y exigen el cipher configurado
al descifrar ([Encrypter](../encrypter.py)).

`EncrypterProvider` vincula `IEncrypter` a un único `Encrypter` administrado por
la aplicación y fija la fachada `Crypt`. La construcción directa solo necesita
acceso a la configuración; resolver desde el contenedor y despachar por la
fachada son cuestiones de integración separadas
([provider.py](../provider.py), [Crypt](../../support/facades/encrypter.py)).

## Estructura del módulo

Se inspeccionaron recursivamente los cinco archivos Python siguientes. El
módulo no contiene recursos no Python utilizados en su ejecución.

| Ruta en el repositorio | Responsabilidad y símbolos públicos propios |
|---|---|
| [orionis/encrypter/__init__.py](../__init__.py) | Reexporta `Encrypter`; `__all__ = ["Encrypter"]`. |
| [orionis/encrypter/encrypter.py](../encrypter.py) | `Encrypter`; `_Payload` privado, `_PAYLOAD_DECODER` compartido y nueve auxiliares privados. |
| [orionis/encrypter/contracts/__init__.py](../contracts/__init__.py) | Reexporta `IEncrypter`; `__all__ = ["IEncrypter"]`. |
| [orionis/encrypter/contracts/encrypter.py](../contracts/encrypter.py) | Contrato abstracto `IEncrypter`. |
| [orionis/encrypter/provider.py](../provider.py) | `EncrypterProvider`; sin reexportación desde el paquete raíz. |

## Referencia de API

Los bloques de declaraciones de esta sección son fragmentos de referencia
copiados del código, no scripts completos: las firmas no tienen un cuerpo
inventado ni puntos suspensivos. Los imports públicos se describen por separado.
Las excepciones indicadas no son exhaustivas para objetos de configuración
arbitrarios o fallos de dependencias.

### IEncrypter

Importa `IEncrypter` desde `orionis.encrypter.contracts` o
`orionis.encrypter.contracts.encrypter`. Código fuente:
[contracts/encrypter.py](../contracts/encrypter.py).

```python
class IEncrypter(ABC):
```

```python
@abstractmethod
def encrypt(
    self,
    plaintext: str,
) -> str:
```

```python
@abstractmethod
def decrypt(
    self,
    payload: str,
) -> str:
```

Estos métodos abstractos síncronos declaran entradas y salidas de cadena y las
mismas familias `TypeError`, `ValueError` y `RuntimeError` que la implementación.
Sus cuerpos solo contienen docstrings, por lo que no cifran ni validan una
implementación personalizada. Implementa ambos métodos antes de instanciar
una subclase; de lo contrario, la maquinaria ABC lanza `TypeError`.

El contrato declara `__slots__ = ()` y ningún constructor explícito. Las
subclases también deben declarar slots para no introducir su propio diccionario
de instancia. Las comprobaciones estructurales están en
[tests/encrypter/contracts/test_encrypter.py](../../../tests/encrypter/contracts/test_encrypter.py),
`TestIEncrypterDefinition` y `TestIEncrypterImplementations`.

### Encrypter

Importa `Encrypter` desde `orionis.encrypter` o
`orionis.encrypter.encrypter`. Código fuente: [encrypter.py](../encrypter.py).

```python
class Encrypter(IEncrypter):
```

Implementa los dos métodos del contrato. Su constructor explícito, constantes
y atributos escribibles se documentan a continuación. No declara ninguna
propiedad pública, iterador, protocolo de gestor de contexto, sobrecarga ni
método de cierre de recursos.

### `Encrypter.__init__`

Código fuente: [encrypter.py](../encrypter.py), `Encrypter.__init__`.

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

- `app: IApplication` es obligatorio. Solo se invocan `config("app.key")` y
  `config("app.cipher")`; no hay comprobación en ejecución de
  `isinstance(app, IApplication)`. Los ejemplos autónomos utilizan un objeto
  mínimo de configuración, como los dobles de las pruebas existentes, no un
  protocolo nuevo.
- Devuelve `None`; almacena los resultados de configuración, valida la
  pertenencia del cipher y la longitud de clave, calcula `_is_gcm` y construye
  `AESGCM(self.key)` para GCM. CBC deja `_aesgcm` en `None`. No conserva el objeto
  de aplicación.
- `ValueError` explícito: cipher no admitido o clave de longitud incorrecta
  para la familia `AES-128` / `AES-256`.
- Los errores del callback de configuración se propagan sin traducir. No hay
  comprobación explícita del tipo de clave: `None` falla en `len(key)` con
  `TypeError`, y un cipher no hashable falla en la pertenencia con `TypeError`.
  GCM también delega la validación de clave en `AESGCM`. Una cadena de longitud
  correcta puede pasar la construcción CBC y fallar al cifrar; eso no la
  convierte en una representación admitida de clave en bytes.

Aquí no se deriva la clave ni se decodifica `base64:`. El propio constructor
no recarga configuración, asume recursos ni registra servicios en el contenedor.
Consulta `TestEncrypterInitialisation` en
[tests/encrypter/test_encrypter.py](../../../tests/encrypter/test_encrypter.py).

### Atributos y constantes

Código fuente: [encrypter.py](../encrypter.py), `Encrypter` y su constructor.
Las seis constantes numéricas no tienen anotación de tipo declarada; no
confundas su tipo `int` inferido con una anotación presente en el código.

```python
AES_128_KEY_SIZE = 16
AES_256_KEY_SIZE = 32
CBC_IV_SIZE = 16
GCM_IV_SIZE = 12
GCM_TAG_SIZE = 16
PKCS7_BLOCK_SIZE = 16
SUPPORTED_CIPHERS: ClassVar[frozenset[str]] = frozenset(
    cipher.value for cipher in OrionisCipher
)
```

Estas constantes definen las longitudes en bytes y el catálogo aceptado de
[Requisitos](#requisitos). `SUPPORTED_CIPHERS` se calcula al definir la clase,
no se reconstruye en cada consulta; sus cuatro valores actuales proceden de
`OrionisCipher`. El valor frozenset es inmutable, pero un llamador Python puede
reasignar los atributos de clase.

| Atributo público | Anotación declarada en el constructor | Valor almacenado |
|---|---|---|
| `key` | `bytes` | Resultado de `app.config("app.key")`, sin copia ni conversión. |
| `cipher` | `str` | Resultado de `app.config("app.cipher")`, sin normalización. |

Ambos son slots escribibles ordinarios, no propiedades validadas. Asignarlos
no actualiza `_is_gcm` ni `_aesgcm`: GCM sigue utilizando el auxiliar construido
con la clave original, mientras CBC construye su cipher con el `key` actual.
El `cipher` actual se usa en los sobres y las comparaciones. No existe un método
público de reconfiguración que coordine esos campos; construye otra instancia
con configuración coherente al utilizar otra clave o modo.

### Encrypter.encrypt

Código fuente: [encrypter.py](../encrypter.py), `Encrypter.encrypt`,
`__encryptCBC` y `__encryptGCM`.

```python
def encrypt(
    self,
    plaintext: str,
) -> str:
```

`plaintext: str` es obligatorio y no puede estar vacío. No se eliminan espacios,
caracteres de control ni texto multibyte. Se codifica como UTF-8 y se cifra
completamente en memoria. Devuelve un `str` con el sobre descrito en
[Formato del payload](#formato-del-payload), no bytes de texto cifrado en crudo.

| Excepción que recibe quien llama | Condición |
|---|---|
| `TypeError` | La entrada no es `str`: `Plaintext must be a string`. |
| `ValueError` | Entrada vacía: `Plaintext cannot be empty`. |
| `ValueError` | La codificación UTF-8 lanza `UnicodeEncodeError`, por ejemplo ante `"\ud800"`; se encadena el error original. |
| `RuntimeError` | Una `Exception` en la rama de cifrado seleccionada se envuelve con `Error during encryption:` y se encadena. Incluye fallos de la primitiva, aleatoriedad y codificación del sobre. |

Cada llamada obtiene un nuevo IV aleatorio mediante `os.urandom`. Repetir el
texto suele producir sobres diferentes, pero la implementación no mantiene un
registro de nonces ni garantiza unicidad. El método no cambia atributos de
instancia, escribe archivos, accede a la red ni resuelve servicios. La obtención
de aleatoriedad y el trabajo criptográfico síncrono se ejecutan en el hilo de
quien llama. Consulta `TestEncrypterEncrypt` / `TestEncrypterRoundTrip` en
[tests/encrypter/test_encrypter.py](../../../tests/encrypter/test_encrypter.py).

### Encrypter.decrypt

Código fuente: [encrypter.py](../encrypter.py), `Encrypter.decrypt` y los
auxiliares de [Etapas de error](#etapas-de-error).

```python
def decrypt(
    self,
    payload: str,
) -> str:
```

`payload: str` es obligatorio y no puede estar vacío. Devuelve el `str` UTF-8
recuperado tras decodificar el sobre, comparar el cipher, validar el IV y
descifrar. El cipher del payload no selecciona otro algoritmo o configuración.

| Excepción que recibe quien llama | Condición |
|---|---|
| `TypeError` | La entrada no es `str`: `Payload must be a string`. |
| `ValueError` | Entrada vacía: `Payload cannot be empty`. |
| `ValueError` | Falla la decodificación base64 exterior o JSON tipado; los errores de decodificador capturados reciben el prefijo `Invalid payload:`. msgspec rechaza campos ausentes o de tipo incorrecto. |
| `ValueError` | Falla la decodificación base64 interior; un `binascii.Error` capturado recibe el prefijo `Error decoding payload data:`. |
| `ValueError` | El `cipher` del payload no es exactamente igual al `cipher` actual de la instancia. |
| `ValueError` | El IV no mide 16 bytes para CBC o 12 bytes para GCM. |
| `RuntimeError` | Una `Exception` dentro de `__performDecryption` se envuelve con `Error during decryption:` y se encadena: tag GCM ausente o de longitud incorrecta, autenticación fallida, ciphertext CBC malformado, relleno inválido o UTF-8 recuperado inválido. |

El decodificador base64 de Python usa su modo predeterminado, no estricto.
Las cadenas base64 con caracteres no ASCII pueden propagar un `ValueError`
del decodificador sin el prefijo del módulo. Las comprobaciones no constituyen
un validador de base64 canónico. Los métodos dejan el estado de la instancia
intacto y no conservan recursos externos que requieran limpieza. Consulta
`TestEncrypterDecryptPayloadValidation` / `TestEncrypterDecryptFailures` en
[tests/encrypter/test_encrypter.py](../../../tests/encrypter/test_encrypter.py).

### Formato del payload

Código fuente: [encrypter.py](../encrypter.py), `_Payload`, `_PAYLOAD_DECODER`,
`__encryptCBC`, `__encryptGCM`, `__decodePayload` y `__extractPayloadData`.
`_Payload` es un `msgspec.Struct` privado declarado con `gc=False`, no un objeto
público que deba construir quien llama. Sus campos obligatorios se declaran
en este orden: `iv: str`, `value: str`, `tag: str | None`, `cipher: str`.

La representación exterior es base64 estándar de JSON UTF-8; cada campo binario
también usa base64 estándar, no base64 URL-safe. El JSON se emite desde el struct,
sin diccionario intermedio.

| Campo | CBC | GCM |
|---|---|---|
| `iv` | 16 bytes aleatorios, codificados | 12 bytes aleatorios, codificados |
| `value` | Ciphertext alineado a bloques de bytes UTF-8 con relleno PKCS7, codificado | Ciphertext sin el tag final, codificado |
| `tag` | JSON `null` | Tag de 16 bytes, codificado |
| `cipher` | Cadena exacta configurada | Cadena exacta configurada |

CBC siempre añade relleno, incluido un bloque completo de 16 bytes si los
bytes del texto ya están alineados. Al retirarlo rechaza bytes descifrados
vacíos, longitud de relleno cero o superior a 16 y bytes de relleno no uniformes.
`decrypt()` puede aceptar texto vacío correctamente rellenado aunque
`encrypt("")` lo rechace.

GCM llama a `AESGCM.encrypt(iv, data, None)` y
`AESGCM.decrypt(iv, value + tag, None)`: no aporta datos autenticados adicionales.
Las cadenas `tag` vacías se convierten en `None`; GCM rechaza el tag ausente en
la etapa de descifrado. CBC no utiliza el tag decodificado para autenticar ni
exige que sea `null` al consumir un sobre.

msgspec exige los cuatro campos, incluido `tag` aunque su valor sea `null`;
el decodificador configurado acepta campos JSON desconocidos. La decodificación
base64 no pasa `validate=True`, por lo que descarta algunos caracteres ajenos
al alfabeto. Las longitudes de IV y tag GCM se comprueban después de decodificar;
no hay límite máximo explícito del payload ni comprobación de caducidad o
repetición. Descifrar CBC correctamente no demuestra autenticidad: esa rama
no incluye MAC ni firma.

### Etapas de error

Los auxiliares siguientes son detalles privados de implementación en
[encrypter.py](../encrypter.py); se incluyen para explicar errores públicos,
no como API que deba invocar una aplicación.

| Símbolo privado | Función y efecto público |
|---|---|
| `__decodePayload` | Decodifica base64 exterior y usa el decodificador JSON tipado compartido; los errores capturados se convierten en `ValueError`. |
| `__extractPayloadData` | Decodifica IV, ciphertext y tag si es truthy; un `binascii.Error` capturado se convierte en `ValueError`. |
| `__validateCipherMatch` | Rechaza la incompatibilidad de cipher con `ValueError`. |
| `__validateIvSize` | Rechaza la longitud incorrecta del IV con `ValueError`. |
| `__performDecryption` | Comprueba presencia y longitud del tag GCM, llama al auxiliar del modo y decodifica UTF-8; envuelve `Exception` en `RuntimeError`. |
| `__encryptCBC` | Genera IV, rellena, cifra y serializa; envuelve `Exception` en `RuntimeError`. |
| `__decryptCBC` | Descifra y comprueba relleno; relanza `ValueError` y envuelve las demás `Exception`. Quien lo invoca envuelve ambos casos en `RuntimeError`. |
| `__encryptGCM` | Genera IV, cifra, separa tag y serializa; envuelve `Exception` en `RuntimeError`. |
| `__decryptGCM` | Une ciphertext/tag y autentica; relanza `ValueError` y envuelve las demás `Exception`. Quien lo invoca envuelve ambos casos en `RuntimeError`. |

Los envoltorios capturan `Exception`, no todas las subclases de `BaseException`.
Se conservan las cadenas de causas con `raise ... from ...`; un `InvalidTag` de
GCM puede tener mensaje vacío. No dependas de que el mensaje completo sea estable
entre dependencias. El módulo no define excepciones llamadas `EncryptionError`
o `DecryptionError`.

### EncrypterProvider

Importa desde `orionis.encrypter.provider`. Código fuente:
[provider.py](../provider.py).

```python
class EncrypterProvider(ServiceProvider):
```

```python
def register(self) -> None:
```

```python
async def boot(self) -> None:
```

El constructor se hereda, no se declara en este módulo. Su fuente literal es
[ServiceProvider.__init__](../../container/providers/service_provider.py):

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

- El constructor heredado almacena `app` en `self.app`; no copia la aplicación
  ni valida su tipo.
- `register()` no tiene parámetros adicionales, devuelve `None` y llama a
  `self.app.singleton(IEncrypter, Encrypter)`. Declara un binding; no construye
  por sí mismo un servicio de cifrado ni fija una fachada.
- `boot()` no tiene parámetros adicionales; esperarlo devuelve `None` después
  de `await CryptFacade.pin()`. Esto resuelve y cachea el servicio en la fachada;
  no registra ningún binding adicional.
- Ninguna sobrescritura traduce errores del contenedor o la fachada. En
  particular, pueden propagarse fallos de configuración al construir el
  servicio para fijarlo. Llamar a `boot()` sobre un doble de proveedor no
  convierte ese doble en la aplicación de la fachada: `Facade.resolve()`
  utiliza su propia referencia de aplicación.

El proveedor es de carga inmediata, no `DeferrableProvider`, y figura en
`CORE_PROVIDER_METADATA` / `CORE_PROVIDERS` de
[orionis/foundation/core_providers.py](../../foundation/core_providers.py).
`Application.create()` lo registra; `Application.boot()` o el arranque de
proveedores CLI/HTTP lo esperan. Esto permite utilizar consumidores síncronos
de fachada después del arranque. Las pruebas del proveedor están en
[tests/encrypter/test_provider.py](../../../tests/encrypter/test_provider.py),
incluidos registro, pertenencia al núcleo y ausencia de carga diferida, y boot
con un doble que registra llamadas.

### Integración con Crypt

`Crypt` es una fachada relacionada, no una exportación pública propia de este
módulo. Impórtala desde `orionis.support.facades.encrypter`; código fuente:
[Crypt.getFacadeAccessor](../../support/facades/encrypter.py).

```python
class Crypt(Facade):
```

```python
@classmethod
def getFacadeAccessor(cls) -> type:
```

El método devuelve la clase `IEncrypter`, no una cadena. No recibe argumentos
adicionales. El [encrypter.pyi](../../support/facades/encrypter.pyi) paralelo
hereda `IEncrypter` e `IFacade`; aporta metadatos de editor y comprobación de
tipos, no una implementación de cifrado en ejecución.

Antes de fijarla, `Crypt.encrypt(...)` produce un `_FacadeDispatch` esperable;
espéralo solo después de crear la aplicación. Resolver ese servicio de carga
inmediata no arranca por sí solo su proveedor ni lo fija automáticamente.
Después de arrancar el proveedor o de `await Crypt.pin()`, `Crypt.encrypt(...)`
y `Crypt.decrypt(...)` devuelven cadenas síncronamente; esperar esas cadenas
lanza `TypeError`. Resolver explícitamente antes de crear la aplicación lanza
`RuntimeError`. Evidencia:
[Facade.resolve / pin / unpin](../../container/facades/facade.py) y
[FacadeMeta.__getattr__ / _FacadeDispatch](../../container/facades/meta.py).

Para mantener una forma de llamada estable durante el arranque, utiliza
`service = await app.make(IEncrypter)` y luego métodos síncronos del servicio.
[Stringable.encrypt / decrypt](../../support/types/stringable.py) delegan en
`Crypt` sin `await`. Los builders de vista
[_global_encrypt / _global_decrypt](../../view/globals/bcrypt.py), en cambio,
esperan `app.make(IEncrypter)` dentro de sus callbacks asíncronos y después
llaman al servicio.

## Ejemplos de uso

Cada bloque Python siguiente es un script completo e independiente para Python
3.14+ con el framework y sus dependencias normales importables. Ejecuta cada uno
en un proceso nuevo: el ejemplo de integración utiliza el estado singleton de
la aplicación y la fachada. Si ejecutas un script sin instalar el checkout,
incluye la raíz del repositorio en `PYTHONPATH` antes de lanzarlo. Cada script
cambia a su propio directorio temporal antes de importar el framework y restaura
el directorio original.

Ejecuta el ejemplo de integración con la configuración de entorno predeterminada
de Orionis. Las variables del SO heredadas pueden sobrescribir otras rutas o
servicios de la aplicación; cambiar el directorio no limpia `os.environ`. Los
procesos de validación no heredaron variables de aplicación/servicios ni
credenciales.

Las claves se generan localmente para la demostración y no se imprimen ni
conservan. Los scripts no cargan la aplicación, credenciales ni servicios de
este checkout. Las salidas esperadas omiten claves, IV y ciphertext aleatorios.

### Ciclos de cifrado autónomos

Ejercita todos los ciphers admitidos e inspecciona su sobre. `SimpleNamespace`
solo aporta el acceso a configuración que consume el constructor; no es una
subclase de `IApplication`. El comportamiento esperado se basa en
[Encrypter.encrypt / decrypt](../encrypter.py) y las pruebas de ciclo existentes.

```python
import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

previous_cwd = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        import msgspec.json as msjson
        from orionis.encrypter import Encrypter

        for cipher in sorted(Encrypter.SUPPORTED_CIPHERS):
            key_size = 16 if cipher.startswith("AES-128") else 32
            values = {"app.key": os.urandom(key_size), "app.cipher": cipher}
            crypt = Encrypter(SimpleNamespace(config=values.__getitem__))
            plaintext = "Orionis\ninvoice=42"
            payload = crypt.encrypt(plaintext)
            assert crypt.decrypt(payload) == plaintext
            assert not hasattr(crypt, "__dict__")
            envelope = msjson.decode(base64.b64decode(payload))
            assert set(envelope) == {"iv", "value", "tag", "cipher"}
            assert envelope["cipher"] == cipher
            if cipher.endswith("GCM"):
                assert len(base64.b64decode(envelope["iv"])) == 12
                assert len(base64.b64decode(envelope["tag"])) == 16
            else:
                assert len(base64.b64decode(envelope["iv"])) == 16
                assert envelope["tag"] is None
            print(f"{cipher}: round trip verified")
    finally:
        os.chdir(previous_cwd)
```

```text
AES-128-CBC: round trip verified
AES-128-GCM: round trip verified
AES-256-CBC: round trip verified
AES-256-GCM: round trip verified
```

### Manejo de errores reales

Distingue la validación de entrada y sobre de un fallo de autenticación GCM.
Cambia un bit de un byte del ciphertext conservando el tag; no deduzcas el
fallo de reemplazar bytes aleatoriamente. Evidencia:
[etapas de error de Encrypter](../encrypter.py).

```python
import base64
import os
from collections.abc import Callable
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


def expect_error(
    exception_type: type[Exception],
    operation: Callable[[], object],
) -> Exception:
    """Return the expected exception and reject a successful operation."""
    try:
        operation()
    except exception_type as exc:
        return exc
    message = "The operation did not raise the expected exception."
    raise AssertionError(message)


previous_cwd = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        import msgspec.json as msjson
        from orionis.encrypter import Encrypter

        key = os.urandom(32)
        values = {"app.key": key, "app.cipher": "AES-256-GCM"}
        crypt = Encrypter(SimpleNamespace(config=values.__getitem__))
        expect_error(TypeError, partial(crypt.encrypt, 42))
        empty = expect_error(ValueError, partial(crypt.encrypt, ""))
        assert str(empty) == "Plaintext cannot be empty"
        expect_error(ValueError, partial(crypt.decrypt, "abcde"))
        cbc_values = {"app.key": key, "app.cipher": "AES-256-CBC"}
        cbc = Encrypter(SimpleNamespace(config=cbc_values.__getitem__))
        expect_error(ValueError, partial(cbc.decrypt, crypt.encrypt("record")))

        envelope = msjson.decode(base64.b64decode(crypt.encrypt("record")))
        ciphertext = bytearray(base64.b64decode(envelope["value"]))
        ciphertext[0] ^= 1
        envelope["value"] = base64.b64encode(ciphertext).decode("ascii")
        tampered = base64.b64encode(msjson.encode(envelope)).decode("ascii")
        failure = expect_error(RuntimeError, partial(crypt.decrypt, tampered))
        assert failure.__cause__ is not None
        assert str(failure).startswith("Error during decryption:")
        print("Input, envelope and cipher mismatch checks verified")
        print("Tampered GCM ciphertext: RuntimeError")
    finally:
        os.chdir(previous_cwd)
```

```text
Input, envelope and cipher mismatch checks verified
Tampered GCM ciphertext: RuntimeError
```

### Aplicación, contenedor y fachada

Crea una aplicación real dentro de un directorio temporal. Primero utiliza el
dispatcher sin fijar después de `create()` y luego espera el arranque de
proveedores inmediatos con `boot()`. Ejercita
[Application](../../foundation/application.py), [EncrypterProvider](../provider.py),
[Crypt](../../support/facades/encrypter.py) y el
[consumidor Stringable real](../../support/types/stringable.py). Este script
no inicia un servidor ni un backend externo.

```python
import asyncio
import inspect
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory

previous_cwd = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        from orionis.encrypter.contracts import IEncrypter
        from orionis.foundation.application import Application
        from orionis.support.facades.encrypter import Crypt
        from orionis.support.types.stringable import Stringable

        app = Application(base_path=Path(directory))
        app.withConfigApp(key=os.urandom(32), cipher="AES-256-GCM")

        async def main() -> None:
            """Exercise the service before and after eager provider startup."""
            app.create()
            service = await app.make(IEncrypter)
            assert service is await app.make(IEncrypter)
            pending = Crypt.encrypt("deferred facade")
            assert inspect.isawaitable(pending)
            payload = await pending
            assert await Crypt.decrypt(payload) == "deferred facade"
            print("Created application: singleton and deferred facade verified")

            await app.boot()
            assert await Crypt.resolve() is service
            payload = Crypt.encrypt("pinned facade")
            assert isinstance(payload, str)
            assert Crypt.decrypt(payload) == "pinned facade"
            wrapped_payload = Stringable("string consumer").encrypt()
            assert isinstance(wrapped_payload, str)
            assert Stringable(wrapped_payload).decrypt() == "string consumer"
            print("Booted application: synchronous Crypt and Stringable verified")

        asyncio.run(main())
    finally:
        logging.shutdown()
        os.chdir(previous_cwd)
```

```text
Created application: singleton and deferred facade verified
Booted application: synchronous Crypt and Stringable verified
```

### Recifrado de registros locales

Combina serialización JSON, almacenamiento temporal, descifrado CBC y cifrado
GCM con dos instancias independientes. Es composición de aplicación sobre
[encrypt / decrypt](../encrypter.py), no una API de rotación de claves del
módulo. Las claves solo viven en este proceso; los archivos y cualquier
artefacto de configuración generado se eliminan con el directorio temporal.

```python
import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

previous_cwd = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        import msgspec.json as msjson
        from orionis.encrypter import Encrypter

        legacy_values = {
            "app.key": os.urandom(32),
            "app.cipher": "AES-256-CBC",
        }
        current_values = {
            "app.key": os.urandom(16),
            "app.cipher": "AES-128-GCM",
        }
        legacy = Encrypter(SimpleNamespace(config=legacy_values.__getitem__))
        current = Encrypter(SimpleNamespace(config=current_values.__getitem__))
        records = [{"id": index, "label": f"record-{index}"} for index in range(3)]
        old_payloads = [
            legacy.encrypt(msjson.encode(record).decode("utf-8"))
            for record in records
        ]
        legacy_path = Path(directory) / "legacy.json"
        current_path = Path(directory) / "current.json"
        legacy_path.write_bytes(msjson.encode(old_payloads))
        stored_payloads = msjson.decode(legacy_path.read_bytes())
        new_payloads = [
            current.encrypt(legacy.decrypt(payload)) for payload in stored_payloads
        ]
        current_path.write_bytes(msjson.encode(new_payloads))
        restored = [
            msjson.decode(current.decrypt(payload).encode("utf-8"))
            for payload in msjson.decode(current_path.read_bytes())
        ]
        assert restored == records
        for payload in new_payloads:
            envelope = msjson.decode(base64.b64decode(payload))
            assert envelope["cipher"] == "AES-128-GCM"
        print("3 local records re-encrypted and verified")
    finally:
        os.chdir(previous_cwd)
```

```text
3 local records re-encrypted and verified
```

## Características de diseño

- Contrato ABC con slots vacíos y slots concretos -> `Encrypter` no tiene
  `__dict__` por instancia; solo almacena `_aesgcm`, `_is_gcm`, `cipher` y `key`
  ([IEncrypter](../contracts/encrypter.py), [Encrypter](../encrypter.py)).
- Indicador de modo y auxiliar GCM calculados una vez -> conserva la selección
  de modo y el auxiliar de clave GCM desde la construcción, sin recalcularlos
  al asignar slots públicos.
- Struct tipado privado y decodificador compartido -> la validación de campos
  del sobre se separa de la validación criptográfica. `_Payload(gc=False)` no
  tiene un grafo de objetos cíclico en los campos usados aquí; no es una API
  pública de esquemas.
- Proveedor singleton inmediato y pin de fachada de proceso -> reutiliza los
  servicios creados por la aplicación, mientras las construcciones directas
  `Encrypter(app)` siguen produciendo objetos separados
  ([provider.py](../provider.py), [Facade](../../container/facades/facade.py)).
- Envoltorios de excepciones anidados -> quien llama debe distinguir el
  `ValueError` de validación previa del `RuntimeError` de la etapa criptográfica,
  incluidas sus causas. Los mecanismos reales están en
  [encrypter.py](../encrypter.py).

## Rendimiento y concurrencia

Evidencia: [Encrypter y sus auxiliares](../encrypter.py),
[provider.py](../provider.py), [estado de fachada](../../container/facades/facade.py).

`encrypt()` / `decrypt()` son síncronos y no contienen `await`, despacho a
executors, acceso a archivos o red, generadores ni API de streaming. Codificación,
decodificación, relleno, cifrado y aleatoriedad se ejecutan en el hilo de quien
llama; invocarlos dentro de una corrutina no vuelve asíncrono ese trabajo.
El boot del proveedor y la resolución del contenedor son operaciones de
integración asíncronas, no métodos de cifrado.

Entradas, ciphertext, JSON y base64 se materializan completos, con copias por
codificación, concatenación y slicing. CBC añade entre 1 y 16 bytes de relleno
y GCM extrae un tag de 16 bytes. Para una longitud de texto en bytes `n`, el
procesamiento y los búferes crecen con el mensaje completo; no hay un límite
explícito de entrada. No se afirma un throughput, tiempo constante ni ausencia
de asignaciones.

`AESGCM` se conserva por instancia GCM; CBC construye un `Cipher` y contexto
nuevos por operación. `_PAYLOAD_DECODER` se comparte a nivel de módulo y no
dispone de API de invalidación. Estas observaciones no demuestran un calendario
de claves concreto del backend ni una garantía de seguridad entre hilos.
No hay caché de payloads ni resultados.

Los métodos públicos no reasignan campos de instancia después de inicializar
ni suspenden a mitad para intercalar tareas asyncio. Aun así, los slots públicos
pueden cambiarse externamente, y las instancias singleton y de fachada comparten
esos cambios. El módulo no aporta locks alrededor de métodos, acceso al
decodificador ni configuración.

> ⚠️ No especificado en el código fuente: no existe un contrato de seguridad
> del módulo para el uso concurrente entre hilos del decodificador compartido,
> auxiliar GCM y campos singleton escribibles. Aquí no se certificó el uso entre
> hilos ni entre procesos.

## Notas de compatibilidad

- El proyecto declara Python `>=3.14` en
  [pyproject.toml](../../../pyproject.toml); [uv.lock](../../../uv.lock) también
  declara `>=3.14`. Se valida con CPython **3.14.6 en Windows**. No se ejecutaron
  otras versiones de Python ni sistemas operativos para esta documentación.
- El código usa `bytes | None`, `tuple[...]` y `ClassVar[frozenset[str]]`.
  Esa sintaxis por sí sola no declara compatibilidad con runtimes anteriores.
  El constructor concreto importa `IApplication` en ejecución y no utiliza
  anotaciones de cadena futuras; el contrato y el proveedor sí las utilizan.
  El tipo real del constructor importa para la reflexión del contenedor.
- Las dependencias base de [pyproject.toml](../../../pyproject.toml) son
  `cryptography>=50.0.1,<51.0` y `msgspec>=0.21.1`. No son extras opcionales de
  cifrado. [uv.lock](../../../uv.lock) resuelve **cryptography 50.0.2** y
  **msgspec 0.22.0**; también son las versiones instaladas para la validación,
  no las versiones mínimas declaradas.
- Los sobres contienen una cadena de cipher, pero no identificador de clave,
  parámetros de derivación, caducidad ni migración automática. La recuperación
  correcta necesita configuración coincidente de cipher y clave. Una clave
  GCM incorrecta falla en autenticación; CBC no comprueba identidad de clave ni
  autenticidad más allá de descifrado, relleno y procesamiento UTF-8, por lo que
  no garantiza rechazar toda clave incorrecta o manipulación
  ([Encrypter](../encrypter.py)).
- `Stringable.encrypt()` / `decrypt()` están anotados y documentados como
  retorno `Stringable`, pero devuelven directamente resultados de `Crypt` sin
  envolverlos. Con esta implementación fijada, el resultado observado es `str`,
  no un `Stringable` recién construido
  ([stringable.py](../../support/types/stringable.py)).

## Verificación y limitaciones

### Cobertura del código fuente

Se inventariaron y documentaron los cinco archivos Python del módulo, ambas
listas de exportación, tres clases públicas, siete métodos públicos declarados
(incluido el constructor explícito), siete constantes públicas y dos atributos
públicos. El constructor heredado del proveedor se atribuye a su clase base real.
No hay funciones libres, alias, excepciones, enums, propiedades, sobrecargas ni
protocolos especiales públicos propios más allá de ese constructor.

`_Payload`, `_PAYLOAD_DECODER` y nueve auxiliares privados solo se describen
cuando explican el formato del sobre, estado o límites de errores. Diecinueve
sentencias de importación son dependencias o reexportaciones, no diecinueve API
públicas propias adicionales. En particular, `msgspec`, `Cipher` de cryptography,
`algorithms`, `modes`, `AESGCM`, `OrionisCipher`, `IApplication`, `ServiceProvider`
y `CryptFacade` no son API de este módulo que deban adoptarse como exportaciones
nuevas.

Se inspeccionaron los cuatro archivos de pruebas existentes:
[test_encrypter.py](../../../tests/encrypter/test_encrypter.py) (43 métodos),
[test_provider.py](../../../tests/encrypter/test_provider.py) (8),
[test_package.py](../../../tests/encrypter/test_package.py) (2) y
[contracts/test_encrypter.py](../../../tests/encrypter/contracts/test_encrypter.py)
(8). Aportan 61 métodos de prueba concretos, no garantías universales de seguridad.

### Registro de validación

Los cuatro ejemplos se extrajeron literalmente de este README y se ejecutaron
en procesos independientes con el entorno virtual del repositorio: CPython
3.14.6, Windows, cryptography 50.0.2 y msgspec 0.22.0. Se comprobó que el archivo
de cada módulo Orionis importado pertenecía a este repositorio local, no a otra
copia instalada.

| Ejemplo | Estado | Comprobaciones completadas |
|---|---|---|
| Ciclos de cifrado autónomos | Ejecutado correctamente | Sintaxis, imports locales, cuatro ciphers, dimensiones del sobre, ciclos completos y salida esperada exacta. |
| Manejo de errores reales | Ejecutado correctamente | Sintaxis, imports locales, validación de entrada/sobre/cipher, manipulación de ciphertext, cadena de causas y salida esperada exacta. |
| Aplicación, contenedor y fachada | Ejecutado correctamente | Sintaxis, imports locales, creación/boot reales, identidad singleton, fachada sin/con pin, Stringable y salida esperada exacta. |
| Recifrado de registros locales | Ejecutado correctamente | Sintaxis, imports locales, E/S temporal, composición CBC a GCM, registros recuperados y salida esperada exacta. |

Quince casos adicionales confirmaron claves ausentes o no binarias, entradas
de cipher enum o no hashables, campos JSON desconocidos, base64 no estricto o
no ASCII, tags ausentes/null/vacíos, tag CBC ignorado, texto CBC vacío con
relleno, clave GCM cacheada tras asignación pública y normalización base64 de App.

Pasaron las **61 pruebas existentes**, con **0 fallos, 0 errores y 0 omisiones**.
Se cargaron desde sus archivos locales originales y se ejecutaron mediante
[orionis.test.executors.runner.TestRunner](../../test/executors/runner.py) tras
arrancar una aplicación real bajo una raíz temporal. Se comprobaron tanto los
resultados internos del runner como los estados publicados; no fue una ejecución
directa de `unittest` ni una ejecución de todo el framework. No se lanzó Reactor
contra el bootstrap de este checkout.

La ejecución suprimió bytecode, utilizó directorios temporales de trabajo y
configuración, cerró los handlers de logging antes de limpiar y aplicó barreras
de auditoría para rechazar escrituras fuera del área temporal externa y acceso
a la red. La única excepción de sockets fue la inicialización del par interno
de sockets de asyncio en Windows, identificada por el objeto de código del
auxiliar estándar, no por un permiso general a servicios locales. No se permitió
ningún artefacto de ejecución en el repositorio.

### Discrepancias de docstrings

- [Encrypter.__performDecryption](../encrypter.py) enumera `ValueError` para
  comprobaciones del tag, pero su `except Exception` envolvente los convierte
  en `RuntimeError`.
- [Encrypter.__decryptGCM](../encrypter.py) describe el fallo de autenticación
  como `ValueError`; el backend instalado lanza `InvalidTag`, que el auxiliar
  envuelve en `RuntimeError` y la ruta pública vuelve a envolver.
- [Crypt.getFacadeAccessor](../../support/facades/encrypter.py) describe un
  accessor de cadena y pruebas unitarias con retorno `str`; la firma es
  `-> type` y la implementación devuelve `IEncrypter`.
- [Stringable.encrypt / decrypt](../../support/types/stringable.py) llaman a
  esta implementación mediante `Crypt` pese a su prosa de placeholder y
  descripción de retorno `Stringable`. La ejecución fijada devuelve un `str`.
- `TestEncrypterInitialisation.testGcmModeCachesTheAuthenticatedCipherHelper` en
  [test_encrypter.py](../../../tests/encrypter/test_encrypter.py) menciona en su
  docstring un calendario de claves calculado una vez, pero sus aserciones solo
  demuestran el indicador de modo y el tipo del auxiliar. Este manual no afirma
  nada sobre el calendario de claves del backend.

Son observaciones de implementación frente a descripción, no cambios de código
ni recomendaciones de refactorización.

### Alcance y límites

Esta documentación no incluye benchmarks, servicios externos, credenciales
reales, cambios de dependencias, ediciones de código o pruebas ni auditoría de
seguridad. Los scripts y evidencias de validación permanecen fuera del
repositorio. El manual describe la implementación inspeccionada y los casos
ejecutados localmente, no certifica un protocolo criptográfico independiente
ni un despliegue.
