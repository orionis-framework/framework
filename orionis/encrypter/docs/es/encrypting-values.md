# Proteger y recuperar valores de aplicación

El cifrado permite recuperar texto sensible usando una clave de aplicación estable. Elige el formato y planifica la custodia de esa clave antes de almacenar los primeros tokens.

## Requisitos

- Python 3.14 o posterior.
- `cryptography>=50.0.1,<51.0` y `msgspec>=0.21.1`, instalados por Orionis.
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

## Preparar el almacenamiento de un secreto

La API cifra texto no vacío. Para un documento estructurado, serialízalo primero y guarda el token opaco completo en una columna suficientemente amplia. El tamaño crece por el IV, el tag, el JSON y las dos capas Base64; no presupongas que un campo dimensionado para el texto original bastará. La librería no añade caducidad, contexto asociado, identificador de clave ni protección contra replay.

Selecciona `AES-256-GCM` de forma explícita para un flujo nuevo que necesite autenticidad. La configuración actual utiliza `AES-256-CBC` por defecto; CBC valida padding pero no tiene MAC. Que un token CBC se descifre no demuestra que nadie haya modificado su contenido. El cifrado tampoco decide qué usuario está autorizado a recuperar el valor: comprueba acceso antes de llamar a `decrypt()`.

Las claves `b"k" * 32` de los ejemplos son datos de prueba. En producción conserva la clave aleatoria en tu gestión de secretos y comparte el mismo valor estable entre workers y despliegues que deban leer los mismos tokens. No reemplaces `APP_KEY` sin una migración: no existe un anillo de claves ni selección automática de claves anteriores.

### Rotación controlada

Mantén acceso a la clave y al cipher originales durante la migración. Descifra con la configuración anterior, vuelve a cifrar con la nueva y sustituye el registro solo cuando ambas operaciones terminen. Una interrupción debe poder reanudarse sin confundir versiones; esa marca de versión y la custodia de claves corresponden a la aplicación. Conserva copias de seguridad de acuerdo con el mismo plan. Nunca pruebes claves de forma indiscriminada en un endpoint público.

## Conceptos principales

### Selección de cipher

Cada instancia `Encrypter` queda fijada al cipher y clave configurados. Los identificadores admitidos son `AES-128-CBC`, `AES-256-CBC`, `AES-128-GCM` y `AES-256-GCM`. Un payload solo se descifra con una instancia que use el mismo cipher y clave.

### Formato del sobre

`encrypt()` codifica texto en UTF-8, crea un IV aleatorio nuevo, cifra, serializa `iv`, `value`, `tag` y `cipher` como JSON y codifica ese JSON en Base64. Los campos binarios también son strings Base64. Es texto transportable, no un hash.

### Autenticación

GCM autentica el ciphertext y rechaza cambios mediante su tag de 16 bytes. CBC usa padding PKCS7 pero esta implementación no agrega MAC; prefiere GCM para datos sensibles nuevos. Nunca expongas, registres o confirmes en control de versiones la clave de aplicación.

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


### Usar la fachada de aplicación

```python
from orionis.support.facades import Crypt

token = Crypt.encrypt("private value")
plaintext = Crypt.decrypt(token)
assert plaintext == "private value"
```

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

## API pública

### `Encrypter(app)`

Lee `app.key` como bytes y `app.cipher` como string soportado. Construirlo lanza `ValueError` ante cipher desconocido o tamaño de clave incorrecto. Constantes como `SUPPORTED_CIPHERS`, tamaños de clave/IV y tag describen el formato aceptado.

### `encrypt(plaintext: str) -> str`

Acepta un string no vacío y devuelve un sobre Base64 nuevo. Por el IV aleatorio, cifrar dos veces el mismo texto debe producir tokens distintos. Input inválido lanza `TypeError` o `ValueError`; fallos criptográficos se envuelven en `RuntimeError`.

### `decrypt(payload: str) -> str`

Decodifica y valida el sobre, exige que el cipher coincida, verifica tamaños de IV/tag, descifra y decodifica UTF-8. Rechaza input vacío/no string, sobres malformados, cipher distinto, padding incorrecto, tags inválidos y fallos de autenticación.

### `IEncrypter`

El contrato declara solo `encrypt` y `decrypt` síncronos. Impórtalo desde `orionis.encrypter.contracts` para tipar dependencias resueltas por el contenedor.

## Referencia de implementación para extensiones

| Ruta | Responsabilidad |
|---|---|
| `encrypter.py` | Validación de clave/cipher, sobre y operaciones AES-CBC/AES-GCM. |
| `contracts/encrypter.py` | Interfaz abstracta `IEncrypter` con `encrypt`/`decrypt`. |
| `provider.py` | Binding singleton y fijación de fachada síncrona. |
| `__init__.py` | Export público `Encrypter`. |

---

[Índice](README.md) · [foundation](../../../foundation/docs/es/README.md) · [hashing](../../../hashing/docs/es/README.md)
