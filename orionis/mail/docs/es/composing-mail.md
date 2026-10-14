# Declarar contenido, destinatarios y adjuntos

Mail separa la declaración del mensaje, la composición MIME y el transporte. Prepara remitente, contenido y política de entrega antes del primer envío.

## Requisitos

- Python 3.14 o posterior.
- Una aplicación Orionis iniciada para facade `Mail`, inyección, vistas y discos configurados.
- Servidor SMTP accesible, o filesystem local con hard links para file.
- Remitente y destinatarios válidos; al menos un cuerpo y un destinatario por envío.



## Inicio rápido

```python
from orionis.mail import Address, Content, Envelope

sender = Address("notifications@example.com", "Example App")
envelope = Envelope(
    subject="Welcome",
    from_address=sender,
    to=("ana@example.com", "ops@example.com"),
    reply_to="support@example.com",
)
content = Content(text="Welcome to Orionis.", html="<p>Welcome to Orionis.</p>")
assert envelope.recipients() == ("ana@example.com", "ops@example.com")
assert content.text == "Welcome to Orionis."
print(sender.asHeader())
```




## Elegir entre un mensaje reutilizable y un envío directo

Un `Mailable` expresa una notificación de negocio reutilizable, como la confirmación de una factura. Implementa `envelope()` y `content()` como métodos síncronos; opcionalmente `attachments()` devuelve una secuencia de `Attachment`. Prepara los datos necesarios antes de construirlo: no hagas consultas ni envíos dentro de esos métodos. El manager los invoca al ejecutar el terminal async.

Para una nota puntual usa `raw(text)` o `html(html)`; para una plantilla usa `send("emails.welcome", data, callback)`. `html()` interpreta contenido literal y no procesa sintaxis Jinja. Una plantilla HTML y una versión texto pueden coexistir mediante `Content(view=..., text=...)` o `Content(view=..., text_view=...)`; el mismo `data` alimenta ambas vistas. No combines `view` con `html` ni `text_view` con `text` en el mismo `Content`.

`Content` requiere al menos un cuerpo; una cadena literal vacía es válida, un identificador de plantilla vacío no. El contexto debe ser un mapping de claves string. Se copian y congelan contenedores propios, pero objetos opacos mantienen su identidad: no dependas de que se congele el estado interno de un modelo. `Mailable` es una clase de aplicación y puede tener atributos mutables; la garantía es que el pipeline no cambia su declaración durante el envío.

### Dirección, privacidad y precedencia

Usa `Address("ana@example.com", "Ana")` para separar buzón y nombre visible. La validación normaliza el dominio IDNA y rechaza encabezados con caracteres de control. Un `Envelope` normaliza y deduplica destinatarios. `reply_to` solo define a quién responder: no añade un receptor de transporte. Un buzón presente en To/Cc no puede aparecer también en Bcc.

Las opciones explícitas de la cadena reemplazan remitente y subject del mailable y añaden destinatarios y adjuntos. Si no hay remitente explícito, se utiliza `mail.from_address`; si tampoco está configurado, la composición falla. Ni validar un buzón ni obtener un resultado SMTP verifica que exista la cuenta.

El compositor elimina Bcc de los encabezados MIME conservando sus receptores en el envelope de transporte. No expongas los destinatarios completos de un `MailResult` a usuarios que no deban verlos.


### Declarar un mailable reutilizable

```python
from orionis.mail import Content, Envelope, Mailable


class WelcomeMail(Mailable):
    def __init__(self, name: str) -> None:
        self.name = name

    def envelope(self) -> Envelope:
        return Envelope(subject="Welcome", to="ana@example.com")

    def content(self) -> Content:
        return Content(
            view="emails.welcome",
            text=f"Welcome, {self.name}.",
            data={"name": self.name},
        )


mail = WelcomeMail("Ana")
assert mail.envelope().subject == "Welcome"
assert mail.attachments() == ()
print(mail.content().text)
```

## Adjuntar contenido de storage

`Attachment.fromStorage(path, disk=None, name=None, mime_type=None)` solo declara la intención. El path es lógico y relativo al disco; los nombres de presentación son basenames sin separadores. El archivo se abre al enviar: puede faltar o cambiar entre declaración y lectura. Autoriza el acceso al documento antes de adjuntarlo y utiliza un disco configurado, como `local` para datos privados.

El MIME explícito gana sobre el reportado por storage; si no hay ninguno se infiere por el nombre y finalmente se usa `application/octet-stream`. Esa inferencia no inspecciona contenido ni aplica antivirus. No se incluyen adjuntos de URL remota, inline/CID ni un API de adjuntos a partir de bytes en este módulo. Si necesitas ese flujo, guarda primero contenido validado en storage.

Todos los adjuntos se leen completos y el MIME resultante se construye en memoria. Incluso con un driver de streams, el correo no tiene memoria constante: limita cantidad y tamaño total antes del envío. Para archivos muy grandes, envía un enlace autorizado o temporal según tu política.


### Declarar adjunto nombrado

```python
from orionis.mail import Attachment

attachment = Attachment.fromStorage(
    "reports/annual.pdf",
    disk="local",
    name="Annual Report.pdf",
    mime_type="application/pdf",
)
assert attachment.path == "reports/annual.pdf"
assert attachment.disk == "local"
assert attachment.name == "Annual Report.pdf"
print(attachment.mime_type)
```

### Objetos de valor

- `Address(address, name=None)` acepta un addr-spec y normaliza su dominio IDNA.
- `Envelope(...)` valida headers, normaliza/deduplica destinatarios e impide que uno sea visible y Bcc.
- `Content(...)` requiere un cuerpo e impide conflictos view/literal por alternativa.
- `Attachment.fromStorage(...)` declara I/O diferido con rutas/metadatos seguros.
- `MailResult` devuelve ID, mailer/driver, destinatarios, estado y ruta opcional.

### `Mailable`

Implemente `envelope()` y `content()`; opcionalmente `attachments()`. Pase instancia a `Mail.send()` o la clase para construcción por contenedor en cada envío.

---

[Índice](README.md) · [view](../../../view/docs/es/README.md) · [storage](../../../storage/docs/es/README.md)
