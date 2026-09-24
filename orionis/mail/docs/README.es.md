# Correo de Orionis

Los Mailables reutilizables y los envíos directos comparten un único flujo
asíncrono de preparación y envío. Los únicos transportes de producción son
**SMTP** y **file**.

[Manual en inglés](README.md)

## Contenido

- [Arquitectura](#arquitectura)
- [Configuración](#configuración)
- [API pública](#api-pública)
- [Ejemplos](#ejemplos)
- [Vistas y adjuntos](#vistas-y-adjuntos)
- [MIME y privacidad](#mime-y-privacidad)
- [Resultados y errores](#resultados-y-errores)
- [Extender drivers](#extender-drivers)
- [Arranque y scripts](#arranque-y-scripts)
- [Concurrencia y límites](#concurrencia-y-límites)
- [Verificación](#verificación)

## Arquitectura

```text
Mail facade / IMailManager
    -> independent PendingMail
    -> Mailable declarations OR direct Content + operation-local Message
    -> merged, validated Envelope
    -> IViewEngine.render + IStorageManager.disk(...).file(...).open(...)
    -> EmailMessage -> immutable PreparedMail (MIME bytes + transport envelope)
    -> IMailTransport -> MailResult
```

| Componente | Responsabilidad |
| --- | --- |
| [MailManager](../manager.py) / [IMailManager](../contracts/manager.py) | Leer configuración central y registrar/resolver factories. |
| [PendingMail](../pending.py) | Crear cadenas síncronas independientes e implementar los terminales asíncronos. |
| [Message](../message.py) | Modificar la configuración de un único callback de envío directo. |
| [Mailable](../mailable.py) | Declarar síncronamente sobre, contenido y adjuntos reutilizables. |
| [MailComposer](../composer.py) | Validar, renderizar vistas, cerrar streams y serializar MIME. |
| [IMailTransport](../contracts/transport.py) | Consumir bytes preparados y el sobre de transporte separado. |
| [MailProvider](../provider.py) | Registrar servicios compartidos y fijar la fachada durante el arranque. |

`MailManager` reutiliza los terminales de `PendingMail`; `raw()` y `html()` no
contienen rutas SMTP independientes. Las factories se ejecutan por envío y pueden
obtener transportes compartidos sin estado de operación desde el contenedor.
Ni el manager ni los transportes incorporados conservan destinatarios, cuerpos
o adjuntos de una operación.

No se necesitan dependencias adicionales. Se utilizan `email`, `smtplib`, `ssl`
y filesystem de la biblioteca estándar, los workers de `Loop.execute()`, el motor
de vistas configurado, storage y `DateTime.now()`.

## Configuración

Un **mailer** es el nombre de una configuración. Un **driver** es la
implementación del transporte. Por ejemplo, el mailer `archive` puede utilizar
el driver `file`.

El bootstrap frozen existente sigue funcionando sin campos adicionales:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.mail.entities.file import File
from orionis.foundation.config.mail.entities.from_address import FromAddress
from orionis.foundation.config.mail.entities.mail import Mail
from orionis.foundation.config.mail.entities.mailers import Mailers
from orionis.foundation.config.mail.entities.smtp import Smtp
from orionis.environment import Env


@dataclass(frozen=True, kw_only=True)
class BootstrapMail(Mail):
    default: str = field(
        default_factory=lambda: Env.get("MAIL_MAILER", "smtp"),
    )
    from_address: FromAddress | dict = field(
        default_factory=lambda: FromAddress(
            address=Env.get("MAIL_FROM_ADDRESS", ""),
            name=Env.get("MAIL_FROM_NAME", Env.get("APP_NAME", "Orionis")),
        ),
    )
    mailers: Mailers | dict = field(
        default_factory=lambda: Mailers(
            smtp=Smtp(
                url=Env.get("MAIL_URL", ""),
                host=Env.get("MAIL_HOST", ""),
                port=Env.get("MAIL_PORT", 587),
                encryption=Env.get("MAIL_ENCRYPTION", "TLS"),
                username=Env.get("MAIL_USERNAME", ""),
                password=Env.get("MAIL_PASSWORD", ""),
                timeout=None,
            ),
            file=File(path="storage/mail"),
        ),
    )
```

Se admiten diccionarios anidados equivalentes y mailers adicionales mediante
entradas de diccionario. `Mailers(smtp=..., file=...)` no cambia:

```python
mail_configuration = {
    "default": "archive",
    "mailers": {
        "archive": {"driver": "file", "path": "storage/mail/archive"},
        "file": {"path": "storage/mail"},
        "smtp": {
            "host": "smtp.example.com",
            "port": 587,
            "encryption": "TLS",
            "username": "",
            "password": "",
            "url": "",
            "timeout": 30,
        },
    },
}
```

Las entradas convencionales `smtp` y `file` pueden omitir `driver`; los demás
nombres deben declararlo. Se respeta el campo `driver` de una entidad cuando
existe. La entidad `Mail` conserva los nombres de los diccionarios durante
`asdict()`/`toDict()`, sin convertirlos a los campos fijos de `Mailers`. `default`
ya no está limitado a esos dos nombres. Un mailer o driver desconocido produce
un error al enviar, nunca un fallback. Los providers pueden registrar drivers
antes de su primer uso.

Los servicios solo leen `app.config("mail")`: no releen variables de entorno ni
importan el módulo de configuración de la aplicación. Copian los valores
seleccionados en estructuras de solo lectura, sin modificar el original. Las
entidades conservan la validación estructural de tipos; puertos, timeouts,
cifrado y autenticación SMTP **efectivos** se validan al seleccionar el
transporte, después de aplicar la URL. Una configuración SMTP no utilizada no
impide enviar mediante file ni fijar la fachada.

La sección `from_address` declara un remitente global, por lo que un mensaje solo
necesita `fromAddress()` o `Envelope(from_address=...)` cuando quiere anularlo. El
remitente explícito siempre gana; el global solo se lee si el sobre final no lleva
ninguno. Un `address` vacío mantiene el remitente obligatorio en cada envío. Si el
mensaje termina sin remitente, el envío falla antes del transporte; nunca se
deduce del username SMTP.

### Opciones SMTP y MAIL_URL

| Opción | Significado |
| --- | --- |
| `host` | Host SMTP efectivo obligatorio. |
| `port` | Entero efectivo entre 1 y 65535; se rechazan booleanos. |
| `encryption` | Sin distinguir mayúsculas: `TLS` = STARTTLS obligatorio; `SSL` = TLS implícito; `""` o `none` = conexión sin cifrado solicitada explícitamente. Otros valores fallan. |
| `username`, `password` | Ambos vacíos omiten autenticación. Solo uno informado es un error. |
| `timeout` | Entero positivo de segundos o `None`. smtplib bloqueante no admite cero; tampoco se aceptan floats, booleanos ni negativos. |
| `url` | Vacía utiliza los campos individuales; en otro caso se aplican las reglas siguientes. |

`encryption` sigue siendo un string, no un campo nullable. TLS utiliza la tienda
de confianza del sistema, verifica certificados y hostname, y exige TLS 1.2 como
mínimo. Un STARTTLS ausente o fallido nunca deriva a texto plano.

Para una `MAIL_URL` no vacía:

1. Solo se admiten `smtp://` y `smtps://`, con host obligatorio.
2. El host de la URL sustituye a `host`.
3. `smtp://` utiliza su puerto explícito o el campo `port`, manteniendo el cifrado
   configurado. No solicita texto plano implícitamente.
4. `smtps://` fuerza TLS implícito y utiliza su puerto explícito o 465.
5. Las credenciales de URL reemplazan username/password **como conjunto**, tras
   decodificar escapes. Si no hay credenciales en la URL se usan ambos campos.
6. `timeout` es independiente de la URL.
7. Se rechazan paths (incluida una barra final), queries, fragmentos, esquemas
   desconocidos, hosts mal formados y puertos inválidos, sin reinterpretarlos.

`timeout=None` significa espera de socket ilimitada, no un default oculto. Utiliza
un entero positivo cuando una espera indefinida no resulte adecuada. El timeout
del socket no es un límite global de duración del envío.

### Transporte file

`File.path` es un directorio. Las rutas relativas parten de `app.basePath`, no
del cwd del proceso ni del disco predeterminado de storage. Se respetan las rutas
absolutas; se rechazan rutas de Windows relativas solo a una unidad o raíz por
ser ambiguas.

El worker crea el directorio, escribe un temporal privado de nombre único, hace
flush y fsync, y publica un nombre `.eml` aleatorio mediante `os.link`. La
publicación es atómica y exclusiva: una colisión nunca sobrescribe otro mensaje
y un archivo final nunca expone contenido escrito a medias. En `finally` se
intenta eliminar el temporal que pertenece a esa operación.

Se requiere un filesystem con enlaces duros, como NTFS en Windows o filesystems
locales POSIX habituales. Si no lo admite, se produce un error explícito; no hay
fallback con sobrescritura insegura. Se usan permisos restrictivos cuando la
plataforma los permite: 0600 para el temporal y 0700 para el nuevo directorio
final. En Windows el acceso efectivo depende de las ACL heredadas. No se promete
durabilidad de entradas de directorio ante cortes de energía ni protección ante
cambios externos de permisos.

No guardes mensajes en directorios públicos ni en control de versiones. Este
repositorio ignora `storage/mail/`; excluye también tus rutas personalizadas.
Almacenar un `.eml` no equivale a entregarlo a un buzón.

## API pública

```python
from orionis.support.facades.mail import Mail
from orionis.mail import (
    Address, Attachment, Content, Envelope, MailResult, Mailable, Message,
    PendingMail,
)
from orionis.mail.contracts.manager import IMailManager
```

Deliberadamente no se exporta otra fachada `Mail` desde `orionis.mail`.

### Valores

| Valor | Constructor o factory |
| --- | --- |
| `Address` | `Address(address: str, name: str | None = None)` |
| `Envelope` | `Envelope(*, subject="", from_address=None, to=(), cc=(), bcc=(), reply_to=())` |
| `Content` | `Content(*, view=None, html=None, text=None, text_view=None, data=None)` |
| `Attachment` | `Attachment.fromStorage(path, *, disk=None, name=None, mime_type=None)` |

Los valores son frozen y utilizan slots. Las colecciones de direcciones se
convierten en tuplas. Los contenedores mapping/list/tuple/set del contexto se
copian recursivamente a mappings de solo lectura, tuplas y frozensets; los ciclos
de contenedores se rechazan. Los objetos arbitrarios, incluidos servicios,
conservan su identidad: **no se hace deepcopy** y correo no los modifica.
Los mapas de rechazo del resultado también se copian y protegen.

`Content.view` identifica una vista HTML; `html` es HTML literal. Son excluyentes.
Igualmente, `text_view` excluye al texto literal `text`. Hay que declarar al menos
un cuerpo. `""` es un cuerpo intencional, no ausencia. Ambas vistas usan el mismo
`data` explícito. Los literales nunca se interpretan como plantillas y no existe
conversión automática de HTML a texto.

### Composición síncrona

`Mail`, `IMailManager` y `PendingMail` ofrecen `mailer(name)`,
`fromAddress(address, name=None)`, `to(addresses, name=None)`, `cc(...)`, `bcc(...)`,
`replyTo(...)`, `subject(value)` y `attach(attachment)`.

Cada llamada devuelve inmediatamente un `PendingMail` independiente, sin
renderizar, leer adjuntos ni resolver transportes. **No** utilices `await` en
llamadas intermedias. `Message` ofrece los mismos mutadores del sobre salvo
`mailer`, pero devuelve siempre el **mismo Message mutable**, exclusivo de una
operación de callback.

Los destinatarios aceptan un string, un `Address` o una lista/tupla de ellos.
`name` solo puede acompañar a un único string, nunca a un `Address` o colección.
Una cadena con varias direcciones separadas por comas se rechaza: utiliza una
colección. `fromAddress()` admite un solo remitente y establece tanto `From` como
el remitente de transporte, sin crear una cabecera `Sender` diferente.

Llamadas repetidas a `subject()` y `fromAddress()` sustituyen el valor anterior.
Destinatarios y adjuntos se agregan. La deduplicación conserva orden y mayúsculas
de la parte local; los dominios se normalizan mediante IDNA y sin distinguir
mayúsculas. Los conflictos entre destinatario visible y Bcc se rechazan.

### Terminales asíncronos

Todos devuelven `MailResult` y existen en manager, fachada y cadenas:

| Operación | Interpretación |
| --- | --- |
| `await Mail.send(mailable)` | Declaraciones síncronas del Mailable; no admite `data` ni callback. |
| `await Mail.send(view, data=None, callback=None)` | Un string siempre identifica una vista HTML. |
| `await Mail.send(content, *, callback=None)` | Content contiene sus datos; otro argumento data es inválido. |
| `await Mail.raw(text, callback=None)` | Texto plano literal. |
| `await Mail.html(html, callback=None)` | HTML literal. |

Incluso pasar explícitamente `None` en un argumento prohibido es un error, no un
valor ignorado. No existen aliases `from_`, `sender`, `setFrom`, `text`, `sendText`
ni `sendHtml`.

El callback recibe un `Message` exclusivo y se invoca exactamente una vez.
Admite funciones, métodos y objetos callable. Debe devolver `None`, el Message
recibido o un awaitable que resuelva a uno de esos valores. Se espera el awaitable
antes de continuar. Cualquier otro resultado, incluidos `False` u otro Message,
es un error. Una excepción impide el transporte. Mantén rápidos los callbacks
síncronos; los mutadores no realizan E/S.

En Mailables se obtiene primero la declaración: los escalares explícitos de la
cadena prevalecen y sus destinatarios/adjuntos se agregan. En envíos directos el
Message parte de la cadena: los escalares del callback prevalecen y sus
destinatarios/adjuntos se agregan.

## Ejemplos

Los ejemplos se ejecutan después del arranque normal. Las fixtures de aceptación
incluyen `emails.welcome`, `emails.invoice`, `emails/welcome.txt` y los archivos
de storage `documents/guide.pdf` e `invoices/42.pdf`.

### Mailable reutilizable

```python
from orionis.mail import Address, Attachment, Content, Envelope, MailResult, Mailable
from orionis.support.facades.mail import Mail


class WelcomeMail(Mailable):
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def envelope(self) -> Envelope:
        return Envelope(
            from_address=Address("no-reply@example.com", "Example App"),
            subject="Welcome",
        )

    def content(self) -> Content:
        return Content(
            view="emails.welcome",
            data={"name": self.name},
            text=f"Hello, {self.name}. Welcome to our application.",
        )

    def attachments(self) -> list[Attachment]:
        return [Attachment.fromStorage(
            "documents/guide.pdf", disk="local", name="guide.pdf",
            mime_type="application/pdf",
        )]


async def send_welcome() -> MailResult:
    return await (
        Mail.mailer("file").to(Address("ana@example.com", "Ana"))
        .send(WelcomeMail("Ana"))
    )
```

Si `envelope()` ya declara destinatarios, basta `await Mail.send(mailable)`.
`envelope()` y `content()` son declaraciones síncronas obligatorias;
`attachments()` devuelve una secuencia vacía por defecto. Enviar no modifica
el Mailable.

### Controlador sin Mailable

```python
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.mail import Attachment, Message
from orionis.support.facades.mail import Mail


def configure_welcome(message: Message) -> None:
    message.fromAddress("no-reply@example.com", "Example App")
    message.to("ana@example.com", "Ana")
    message.cc("operations@example.com")
    message.bcc("audit@example.com")
    message.replyTo("support@example.com")
    message.subject("Welcome")
    message.attach(Attachment.fromStorage(
        "documents/guide.pdf", disk="local", name="guide.pdf",
        mime_type="application/pdf",
    ))


class WelcomeController(BaseController):
    __slots__ = ()

    async def sendWelcome(self) -> HttpResponse:
        result = await Mail.send(
            "emails.welcome", {"name": "Ana"}, configure_welcome,
        )
        return response.json({
            "message_id": result.message_id,
            "status": result.status,
        })
```

El controlador devuelve una respuesta HTTP real, no un MailResult ni una
operación pendiente. `HttpResponse` es el alias de anotación del framework,
no un tipo para utilizar con `isinstance()`.

### Servicio fluido con adjunto

```python
from orionis.mail import Attachment, Content, MailResult
from orionis.support.facades.mail import Mail


class InvoiceDeliveryService:
    __slots__ = ()

    async def sendInvoice(
        self, recipient: str, invoice_number: str, attachment_path: str,
    ) -> MailResult:
        return await (
            Mail.mailer("file")
            .fromAddress("billing@example.com", "Example Billing")
            .to(recipient).subject(f"Invoice {invoice_number}")
            .attach(Attachment.fromStorage(
                attachment_path, disk="local", name=f"invoice-{invoice_number}.pdf",
                mime_type="application/pdf",
            ))
            .send(Content(
                view="emails.invoice", data={"invoice_number": invoice_number},
                text=f"Your invoice {invoice_number} is attached.",
            ))
        )
```

### Texto y HTML literales

```python
from orionis.support.facades.mail import Mail


async def send_notifications() -> None:
    await (
        Mail.fromAddress("notifications@example.com", "Example App")
        .to("ana@example.com").subject("Report ready")
        .raw("Your report is ready.")
    )
    await (
        Mail.fromAddress("notifications@example.com", "Example App")
        .to("ana@example.com").subject("Report ready")
        .html("<h1>Your report is ready.</h1>")
    )
```

`Mail.raw(text, callback)` y `Mail.html(html, callback)` también pueden iniciar
una operación directamente, con adjuntos configurados por el callback.

### Callback asíncrono

```python
from orionis.mail import MailResult, Message
from orionis.support.facades.mail import Mail


class NotificationService:
    __slots__ = ()

    async def configureMessage(self, message: Message) -> None:
        message.fromAddress("notifications@example.com", "Example App")
        message.to("ana@example.com")
        message.subject("Notification")

    async def sendNotification(self) -> MailResult:
        return await Mail.mailer("file").raw(
            "Your notification is ready.", self.configureMessage,
        )
```

### Cadenas concurrentes independientes

```python
import asyncio
from orionis.support.facades.mail import Mail


async def send_independent_messages() -> None:
    base = (
        Mail.mailer("file")
        .fromAddress("notifications@example.com", "Example App")
        .subject("Notification")
    )
    first = base.to("ana@example.com")
    second = base.to("luis@example.com")
    await asyncio.gather(first.raw("Hello, Ana."), second.raw("Hello, Luis."))
```

`base` sigue sin destinatarios y `first` no comparte destinatarios con `second`.

### Inyección de dependencias

```python
from orionis.mail import MailResult
from orionis.mail.contracts.manager import IMailManager


class AlertService:
    __slots__ = ("__mail",)

    def __init__(self, mail: IMailManager) -> None:
        self.__mail = mail

    async def sendAlert(self, recipient: str) -> MailResult:
        return await (
            self.__mail.fromAddress("alerts@example.com", "Example App")
            .to(recipient).subject("Service alert")
            .raw("A service alert requires your attention.")
        )
```

Fachada e inyección resuelven el mismo singleton. Importa los contratos de los
constructores en runtime y no uses anotaciones pospuestas como strings en
servicios construidos mediante DI.

## Vistas y adjuntos

Las vistas se convierten en `str` mediante el contrato existente
`IViewEngine.render(template, context)`, no mediante respuestas HTTP o
PendingView. Se conservan loaders, caché, extensiones, filtros, escape y
convenciones de nombres de Orionis. Las plantillas independientes funcionan sin
una petición HTTP. El contexto es explícito por envío y no se instala en globals.

```python
from orionis.mail import Content, MailResult
from orionis.support.facades.mail import Mail


async def send_two_views() -> MailResult:
    return await (
        Mail.mailer("file").fromAddress("no-reply@example.com")
        .to("ana@example.com")
        .send(Content(
            view="emails.welcome", text_view="emails/welcome.txt",
            data={"name": "Ana"},
        ))
    )
```

Las vistas de texto conservan el escape configurado del motor. Para una extensión
explícita distinta de HTML utiliza una ruta con barra, como `emails/welcome.txt`.
Correo no crea un segundo entorno Jinja.

`Attachment.fromStorage()` valida la declaración sin E/S. La preparación resuelve
el disco explícito o predeterminado, obtiene el archivo mediante storage, abre
su stream binario asíncrono, lee los bytes y lo cierra. No reconstruye rutas
locales ni utiliza URLs públicas. Cero bytes es válido; archivos inexistentes,
ilegibles o valores de fallo no binarios abortan todo el envío.

Prevalece el MIME explícito, después metadatos MIME válidos de storage, luego
inferencia por nombre y finalmente `application/octet-stream`. Prevalece el
nombre explícito; si no existe, se muestra solo el basename lógico. Se rechazan
controles, separadores de rutas y parámetros MIME inseguros. Los errores de
lectura/apertura conservan la causa y un error al cerrar no oculta un error
anterior de lectura. Cualquier fallo impide el transporte.

## MIME y privacidad

- `EmailMessage` construye texto, HTML, `multipart/alternative` y
  `multipart/mixed`, con alternativas correctamente anidadas y adjuntos binarios.
- Admite Unicode en asuntos, nombres, cuerpos y nombres de archivo. Cada
  operación obtiene Date de `DateTime.now()` y genera un Message-ID, conservado
  en el resultado.
- Las cabeceras To/Cc están separadas de la unión de destinatarios del sobre.
  Bcc participa en esa unión pero nunca se serializa como cabecera MIME o `.eml`.
- Se admiten mensajes con solo Bcc. Una dirección no puede estar a la vez en
  To/Cc y Bcc.
- Las cabeceras rechazan CR/LF y otros controles. Las direcciones utilizan el
  parser estándar de correo, no una regex improvisada. Se normaliza el dominio
  y se conservan las mayúsculas de la parte local.
- Las partes locales no ASCII, incluido Reply-To, requieren SMTPUTF8 y 8BITMIME.
  Se negocian explícitamente o se falla, sin eliminar caracteres. Los nombres
  visibles Unicode por sí solos no requieren SMTPUTF8.

Todas las vistas y lecturas terminan antes de abrir SMTP o publicar un archivo.
Message no expone un `EmailMessage` mutable para saltarse la validación.

## Resultados y errores

`MailResult` es frozen, utiliza slots y expone estos atributos:

| Atributo | Tipo |
| --- | --- |
| `message_id` | `str` |
| `mailer` | `str` |
| `driver` | `str` |
| `status` | `MailStatus` |
| `recipients` | `tuple[str, ...]` |
| `accepted_recipients` | `tuple[str, ...]` |
| `rejected_recipients` | `Mapping[str, tuple[int, str]]` |
| `file_path` | `Path | None` |

`MailStatus`, de `orionis.mail.enums.status`, es un `StrEnum` con los miembros
`ACCEPTED`, `PARTIAL` y `STORED`, por lo que `result.status == "stored"` sigue
funcionando y el valor se serializa como texto plano.

`accepted` significa que SMTP aceptó DATA para todos los destinatarios previstos.
`partial` indica aceptación para algunos y rechazo para otros. Los rechazos
conservan su código SMTP con mensajes acotados, sin controles y con credenciales
ocultadas. Si falla DATA o se rechazan todos los destinatarios, se lanza una
excepción, nunca un resultado de éxito falso.

`stored` indica publicación completa en file. Sus colecciones de aceptación y
rechazo están vacías; `recipients` conserva el sobre previsto y `file_path`
referencia el archivo final. SMTP devuelve `file_path=None`. Ningún estado
confirma entrega al buzón ni lectura.

Las excepciones están en `orionis.mail.exceptions`:

| Excepción | Significado |
| --- | --- |
| `MailException` | Base común de errores de correo. |
| `MailConfigurationException` | Mailer, driver, factory u opciones seleccionadas inválidos o desconocidos. |
| `MailCompositionException` | Combinaciones de API, cabeceras, declaraciones, callbacks, vistas o MIME inválidos. |
| `MailAttachmentException` | Subclase de composición para adjuntos inseguros o ilegibles. |
| `MailTransportException` | Fallo de transacción SMTP o publicación de archivo. |

Los fallos SMTP indican etapa, tipo de excepción y código cuando existe. Se
suprimen las excepciones de protocolo originales en el traceback porque podrían
contener credenciales o respuestas privadas. El módulo no registra sesiones
SMTP, URLs con credenciales, contraseñas ni contenido MIME. Siempre se intenta
cerrar la conexión sin ocultar el error principal.

## Extender drivers

`IMailManager.extend(driver, factory)` registra un nombre único y devuelve
`None`. Reemplazar un driver incorporado o duplicado es un error explícito.
Todas las factories tienen la misma firma tipada, exportada como
`TransportFactory` desde `orionis.mail.types`:

```python
from collections.abc import Awaitable, Callable, Mapping
from orionis.foundation.contracts.application import IApplication
from orionis.mail.contracts.transport import IMailTransport

type TransportFactory = Callable[
    [IApplication, Mapping[str, object]],
    IMailTransport | Awaitable[IMailTransport],
]
```

Reciben el contenedor y una copia de solo lectura de la configuración seleccionada,
incluido `driver`. Pueden esperar `app.make()`/`app.build()` para resolver
dependencias. Las factories síncronas deben ser rápidas y no bloqueantes. El
registro no construye transportes: se resuelven durante el terminal de envío,
después de preparar correctamente el mensaje.

Este ejemplo utilizable reutiliza file, sin añadir otro backend al framework:

```python
from collections.abc import Mapping
from pathlib import Path
from orionis.container.providers import ServiceProvider
from orionis.foundation.contracts.application import IApplication
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.exceptions import MailConfigurationException
from orionis.mail.transports.file import FileTransport


async def archive_factory(
    app: IApplication, config: Mapping[str, object],
) -> IMailTransport:
    output = config.get("path")
    if not isinstance(output, str) or not output.strip():
        error_msg = "An archive output path is required."
        raise MailConfigurationException(error_msg)
    path = Path(output)
    if not path.is_absolute():
        path = app.basePath / path
    return await app.build(FileTransport, path=path)


class ArchiveProvider(ServiceProvider):
    __slots__ = ()

    async def boot(self) -> None:
        manager = await self.app.make(IMailManager)
        manager.extend("custom_archive", archive_factory)
```

Registra el provider con `app.withProviders(...)` **antes** de `create()`. Declara
`driver="custom_archive"` y un `path` en su mailer. Las pruebas también ejercitan
un transporte de registro definido solo en tests, registrado mediante un provider
real y la configuración central.

Un nuevo transporte implementa el método asíncrono
`send(message: PreparedMail, *, mailer: str, driver: str) -> MailResult`.
`PreparedMail`, de `orionis.mail.entities.prepared`, contiene `message_id`, `sender`,
`recipients`, `mime: bytes` y `smtp_utf8: bool`, sin vistas ni rutas lógicas de
storage. Los transportes personalizados compartidos tampoco deben guardar estado
mutable de operación y deben respetar resultados, privacidad y errores.

## Arranque y scripts

`MailProvider` es eager y forma parte de `CORE_PROVIDERS`. `register()` vincula
compositor e `IMailManager`; `boot()` espera `Mail.pin()`. Los arranques normales
HTTP ASGI/RSGI y CLI permiten utilizar la fachada fluida síncronamente desde la
primera llamada. El arranque no abre ni valida operativamente transportes.
Los constructores de arranque reciben contratos, no fachadas aún sin fijar.

Un simple `from bootstrap.app import app` carga configuración y registros, pero
**no** ejecuta los hooks normales del runtime. Para scripts que necesiten el
arranque completo, vistas o providers personalizados, es preferible un comando
de Orionis. Para un script externo de texto/HTML que solo necesite correo se
admite el arranque explícito del componente:

```python
from bootstrap.app import app
from orionis.aio import Loop
from orionis.mail.provider import MailProvider
from orionis.support.facades.mail import Mail


async def main() -> None:
    await MailProvider(app).boot()
    await (
        Mail.mailer("file").fromAddress("no-reply@example.com")
        .to("ana@example.com").raw("Sent from an explicitly booted script.")
    )


if __name__ == "__main__":
    Loop.run(main())
```

Este script mínimo no ejecuta el boot de otros providers. Para vistas, su provider
también debe inicializar globals, filtros y extensiones; deben arrancarse además
los hooks y drivers propios de la aplicación. Utiliza el arranque CLI normal
cuando existan esas dependencias. Nunca trates `_FacadeDispatch` de una fachada
sin fijar como si fuera un PendingMail.

Después de incorporar este provider a un checkout compilado, invalida solo
`storage/framework/bootstrap` o utiliza el mecanismo optimize-clear existente.
La caché no vigila automáticamente los cambios del código del framework.

## Concurrencia y límites

- Cada entrada de fachada y derivación de cadena es independiente. Message es
  mutable **por operación**; conservarlo no permite modificar un mensaje cuyo
  snapshot ya se tomó. Los Mailables pueden reutilizarse sin mutaciones del módulo.
- Cada envío SMTP utiliza su propia conexión. SMTP, TLS, serialización MIME y
  publicación de archivos bloqueantes se ejecutan con `Loop.execute()`, fuera
  del event loop.
- MIME y adjuntos pueden materializarse completos en memoria: **no** hay
  streaming de extremo a extremo. Considera tamaños concurrentes y copias de
  codificación al dimensionar el proceso.
- La cancelación en callback/render se propaga antes del transporte. La
  preparación mantiene la propiedad de un stream en curso hasta completarlo y
  cerrarlo, y después propaga cancelación; un backend bloqueado puede retrasar
  esa limpieza.
- Cancelar la espera de un worker SMTP/file no necesariamente detiene al worker.
  SMTP podría haber aceptado el mensaje y el archivo todavía podría publicarse.
  El worker conserva la responsabilidad de cerrar conexión y limpiar temporales.
- Timeout, cancelación o desconexión no demuestran ausencia de entrega. No hay
  reintentos automáticos. `timeout=None` puede bloquear indefinidamente al worker
  y al cierre del proceso que espere su finalización.
- Esta versión no incluye colas, programación, reintentos, failover, balanceo,
  proveedores HTTP, tracking, webhooks, imágenes inline, Markdown de correo,
  generadores ni una API pública de fakes. No hay métodos vacíos para esas funciones.

## Verificación

[Las pruebas](../../../tests/mail) utilizan el runner del framework y dobles
explícitos de red, sin credenciales externas ni correos SMTP reales. Cubren el
bootstrap original, diccionarios nombrados, ambos estilos de composición,
DI/fachadas, Jinja real, storage local y sin rutas locales, MIME/privacidad,
modos y fallos SMTP, publicación atómica, concurrencia y cancelación.

[La fixture de aplicación aislada](../../../tests/mail/fixtures/application.py)
ejecuta los ejemplos tras arranque HTTP lifespan y CLI normales, con una respuesta
real de controlador y un transporte personalizado registrado por provider.
[La fixture de tipos](../../../tests/mail/fixtures/typecheck.py) verifica las
sobrecargas desde código consumidor. Las únicas supresiones localizadas de tipos
SMTP corresponden al timeout float-only del stub de typeshed; las pruebas
confirman que Python 3.14 acepta `None` en los dos constructores SMTP reales sin
abrir conexiones.

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe reactor test --start-dir=tests/mail --verbosity=1
.\.venv\Scripts\python.exe -m ruff check orionis/mail tests/mail
uvx pyright --pythonpath .venv/Scripts/python.exe --pythonversion 3.14 orionis/mail orionis/support/facades/mail.pyi tests/mail/fixtures/typecheck.py
```

La interoperabilidad con servidores SMTP reales y filesystems no locales debe
verificarse en el despliegue; la suite no certifica proveedores externos.
