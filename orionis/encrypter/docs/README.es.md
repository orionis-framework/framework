# orionis.encrypter

> `orionis.encrypter` ofrece cifrado y descifrado AES síncrono ligado a la clave de aplicación, con sobres JSON Base64 portables.

## Descripción general

El módulo exporta una clase concreta, `Encrypter`, y mantiene el contrato interno `IEncrypter`. Admite AES-128 y AES-256 en modo CBC o GCM. Cada valor cifrado lleva IV, ciphertext, tag GCM opcional e identificador de cipher dentro de un sobre JSON codificado en Base64.

Las aplicaciones suelen usar la fachada fijada `Crypt`. La construcción directa sirve para extensiones y pruebas aisladas cuando un objeto similar a aplicación entrega `app.key` y `app.cipher`.

## Requisitos

- Python 3.14 o posterior.
- `cryptography>=46.0.3,<47.0.0` y `msgspec>=0.20.0,<0.21.0`, instalados por Orionis.
- Clave exacta de 16 bytes para AES-128 o 32 bytes para AES-256.
- Contenedor Orionis iniciado al usar la fachada `Crypt`.

## Inicio rápido

```python
from orionis.encrypter import Encrypter


class App:
    def config(self, name: str):
        return {
            "app.key": b"k" * 32,
            "app.cipher": "AES-256-GCM",
        }[name]


crypt = Encrypter(App())
token = crypt.encrypt("private value")
assert token != "private value"
assert crypt.decrypt(token) == "private value"
print("round trip ok")
```

Validación: **Executed successfully** en CPython 3.14.6; produjo `round trip ok`.

## Conceptos principales

### Selección de cipher

Cada instancia `Encrypter` queda fijada al cipher y clave configurados. Los identificadores admitidos son `AES-128-CBC`, `AES-256-CBC`, `AES-128-GCM` y `AES-256-GCM`. Un payload solo se descifra con una instancia que use el mismo cipher y clave.

### Formato del sobre

`encrypt()` codifica texto en UTF-8, crea un IV aleatorio nuevo, cifra, serializa `iv`, `value`, `tag` y `cipher` como JSON y codifica ese JSON en Base64. Los campos binarios también son strings Base64. Es texto transportable, no un hash.

### Autenticación

GCM autentica el ciphertext y rechaza cambios mediante su tag de 16 bytes. CBC usa padding PKCS7 pero esta implementación no agrega MAC; prefiere GCM para datos sensibles nuevos. Nunca expongas, registres o confirmes en control de versiones la clave de aplicación.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `encrypter.py` | Validación de clave/cipher, sobre y operaciones AES-CBC/AES-GCM. |
| `contracts/encrypter.py` | Interfaz abstracta `IEncrypter` con `encrypt`/`decrypt`. |
| `provider.py` | Binding singleton y fijación de fachada síncrona. |
| `__init__.py` | Export público `Encrypter`. |

## API pública

### `Encrypter(app)`

Lee `app.key` como bytes y `app.cipher` como string soportado. Construirlo lanza `ValueError` ante cipher desconocido o tamaño de clave incorrecto. Constantes como `SUPPORTED_CIPHERS`, tamaños de clave/IV y tag describen el formato aceptado.

### `encrypt(plaintext: str) -> str`

Acepta un string no vacío y devuelve un sobre Base64 nuevo. Por el IV aleatorio, cifrar dos veces el mismo texto debe producir tokens distintos. Input inválido lanza `TypeError` o `ValueError`; fallos criptográficos se envuelven en `RuntimeError`.

### `decrypt(payload: str) -> str`

Decodifica y valida el sobre, exige que el cipher coincida, verifica tamaños de IV/tag, descifra y decodifica UTF-8. Rechaza input vacío/no string, sobres malformados, cipher distinto, padding incorrecto, tags inválidos y fallos de autenticación.

### `IEncrypter`

El contrato declara solo `encrypt` y `decrypt` síncronos. Impórtalo desde `orionis.encrypter.contracts` para tipar dependencias resueltas por el contenedor.

## Flujos de trabajo comunes

### Cifrar valores de aplicación

Usa `Crypt.encrypt(value)` después del boot, persiste el token como texto opaco y llama `Crypt.decrypt(token)` solo en el límite de confianza que necesita plaintext.

### Rotar clave o cipher

Tokens antiguos no se descifran con una clave nueva ni con otro cipher configurado. Una rotación segura necesita claves versionadas o una migración controlada de lectura antigua/escritura nueva antes de cambiar configuración.

### Probar un servicio directamente

Entrega un doble de aplicación cuyo `config()` retorne bytes normalizados y el string del cipher. Esto evita estado global de fachada y hace deterministas los casos, salvo los bytes del token.

## Ejemplos

### Ejercitar todos los ciphers

```python
from orionis.encrypter import Encrypter


class App:
    def __init__(self, cipher: str) -> None:
        size = 16 if cipher.startswith("AES-128") else 32
        self.values = {"app.key": b"k" * size, "app.cipher": cipher}

    def config(self, name: str):
        return self.values[name]


for cipher in sorted(Encrypter.SUPPORTED_CIPHERS):
    service = Encrypter(App(cipher))
    assert service.decrypt(service.encrypt("Orionis")) == "Orionis"

print("four ciphers ok")
```

Validación: **Executed successfully** en CPython 3.14.6; produjo `four ciphers ok`.

### Inspeccionar metadata del sobre

```python
import base64
import json
from orionis.encrypter import Encrypter


class App:
    def config(self, name: str):
        return {"app.key": b"k" * 32, "app.cipher": "AES-256-GCM"}[name]


token = Encrypter(App()).encrypt("inspect me")
envelope = json.loads(base64.b64decode(token))
assert envelope["cipher"] == "AES-256-GCM"
assert envelope["tag"] is not None
print(sorted(envelope))
```

Validación: **Executed successfully** en CPython 3.14.6; los campos fueron `cipher`, `iv`, `tag` y `value`.

### Rechazar un valor GCM modificado

```python
import base64
import json
from orionis.encrypter import Encrypter


class App:
    def config(self, name: str):
        return {"app.key": b"k" * 32, "app.cipher": "AES-256-GCM"}[name]


crypt = Encrypter(App())
envelope = json.loads(base64.b64decode(crypt.encrypt("sealed")))
changed = bytearray(base64.b64decode(envelope["value"]))
changed[0] ^= 1
envelope["value"] = base64.b64encode(changed).decode()
tampered = base64.b64encode(json.dumps(envelope).encode()).decode()

try:
    crypt.decrypt(tampered)
except RuntimeError:
    print("tampering rejected")
```

Validación: **Executed successfully** en CPython 3.14.6; autenticación GCM rechazó el cambio.

### Usar la fachada de aplicación

```python
from orionis.support.facades import Crypt

token = Crypt.encrypt("private value")
plaintext = Crypt.decrypt(token)
assert plaintext == "private value"
```

Validación: **Import-only** en CPython 3.14.6; las llamadas requieren contenedor y fachada fijada.

## Configuración

`config/app.py` aporta los ajustes:

| Ajuste | Entorno | Significado |
|---|---|---|
| `app.cipher` | `APP_CIPHER` | Uno de los cuatro identificadores AES; predeterminado `AES-256-CBC`. |
| `app.key` | `APP_KEY` | Texto raw o clave con prefijo `base64:` del tamaño exacto requerido. |

La configuración validada convierte la clave a bytes. Si no existe, `SecureKeyGenerator` crea un valor aleatorio compatible con Laravel, con prefijo `base64:`, lo persiste mediante `Env.set` y lo normaliza. Conserva una clave estable en producción: perderla hace irrecuperable el ciphertext existente.

## Integración con Orionis

`EncrypterProvider` es core y no diferido. Vincula `IEncrypter` a `Encrypter` como singleton y fija `Crypt` durante el boot asíncrono para que las llamadas síncronas no devuelvan un dispatcher diferido.

`Stringable.encrypt/decrypt`, flujos de registro, globals de vista y estado MCP usan el servicio o fachada. Código con inyección puede solicitar `IEncrypter`; código de aplicación puede importar `Crypt` desde `orionis.support.facades`.

## Errores y casos límite

- Plaintext y payload vacíos lanzan `ValueError`; valores no string lanzan `TypeError`.
- Ciphers no soportados y tamaños de clave incorrectos fallan al construir.
- Base64/JSON externo o campos tipados inválidos lanzan `ValueError`.
- Cipher distinto e IV incorrecto lanzan `ValueError` antes de descifrar.
- GCM exige tag de 16 bytes; fallos de autenticación aparecen como `RuntimeError` envuelto.
- CBC rechaza ciphertext vacío y padding PKCS7 inválido, pero no autentica metadata ni ciphertext.
- El plaintext debe ser texto UTF-8 válido; esta no es una API para bytes arbitrarios.

## Rendimiento y concurrencia

La implementación es síncrona y usa CPU. GCM conserva un objeto `AESGCM` inmutable por servicio; CBC crea contexto por llamada. El sobre usa estructuras/decoder `msgspec` reutilizables. Cada llamada mantiene estado local y obtiene IV nuevo desde `os.urandom`, por lo que el singleton puede atender llamadas concurrentes sin estado mutable por operación.

El tamaño del token incluye JSON, dos capas Base64 y overhead de IV/tag. No uses esta API como formato streaming para archivos grandes; elige un esquema streaming específico y autenticado.

## Compatibilidad

Orionis declara Python 3.14+, `cryptography` 46.x y `msgspec` 0.20.x. La validación usó CPython 3.14.6 en Windows. El sobre registra el cipher exacto pero no versión de clave; todos los lectores deben compartir configuración compatible.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, contrato, implementación, provider, fachada, configuración app, normalización de clave, integraciones y `tests/encrypter`. Las 61 pruebas pasaron con el runner Orionis. Cuatro programas directos se ejecutaron correctamente; el ejemplo de fachada solo se validó por importación porque requiere boot de aplicación.
