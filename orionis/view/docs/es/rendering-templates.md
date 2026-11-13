# Renderizar páginas y respuestas HTML

View renderiza HTML en el servidor mediante Jinja2 async y lo entrega como una respuesta Orionis.

## Requisitos

- Python 3.14 o posterior.
- Al menos un directorio de plantillas configurado; el predeterminado es `resources/views` relativo a la base de la aplicación.
- Una aplicación Orionis inicializada para la fachada y los globals de plantilla respaldados por servicios.
- Jinja2, MarkupSafe, Markdown y msgspec instalados mediante las dependencias del proyecto.



## Inicio rápido

Crea `resources/views/users/profile.html`:

```html
<!doctype html>
<h1>{{ user.name }}</h1>
<a href="{{ route('users.edit', id=user.id) }}">Edit</a>
```

Devuélvela desde un controlador asíncrono:

```python
from orionis.support.facades import View


async def profile(user):
    return await View.make("users.profile", user=user)
```



## Elegir contexto, render y respuesta

`View.make()` es síncrono y crea un `PendingView`; el I/O y la evaluación de expresiones ocurren al esperarlo. Usa `return await View.make("users.profile", user=user)` desde el controlador. Un servicio que solo necesita texto puede recibir `IViewEngine` y llamar `await engine.render(template, context)`; ese resultado es `str`, no `HTMLResponse`. Mail usa este último contrato para generar cuerpos MIME.

La respuesta pendiente conserva un dict de contexto y colas mutables. Crea una por operación, pasa datos preparados y evita compartirla entre requests. Esperar dos veces el mismo pendiente renderiza dos veces y puede aplicar el flash de nuevo. No es una promesa memoizada. La llamada a `make()` tampoco valida que la plantilla exista.

Los nombres de dot notation no contienen la extensión: `users.profile` busca `users/profile.html`. Para una extensión explícita usa `/`, por ejemplo `users/profile.j2`; `users.profile.html` se transforma como nombre de puntos, no como una ruta con extensión. Las rutas de `{% extends %}` y `{% include %}` pertenecen a Jinja y deben escribirse como rutas reales con extensión.

### Configurar la respuesta HTTP

`View.make()` y `response.view()` aceptan `status_code`, `headers` y `background` exclusivamente por nombre, con valores predeterminados `200`, `None` y `None`. `status_code` acepta un `HTTPStatus` o entero, `headers` acepta un mapping de cadenas y `background` acepta una `BackgroundTask` que se ejecutará después del envío de la respuesta.

```python
from orionis.background import BackgroundTask
from orionis.support.facades import View


async def unauthorized(ip: str, task: BackgroundTask):
    return await View.make(
        "errors.401",
        status_code=401,
        headers={"Cache-Control": "no-store"},
        background=task,
        ip=ip,
    )
```

La forma equivalente por encadenamiento pone los mismos cambios en cola sin adelantar el render:

```python
async def unauthorized_fluent(ip: str, task: BackgroundTask):
    return await (
        View
        .make("errors.401", ip=ip)
        .withStatusCode(401)
        .withHeaders({"Cache-Control": "no-store"})
        .withBackground(task)
    )
```

Primero se aplican las opciones del constructor y después las mutaciones encadenadas en el orden de llamada. `withHeaders()` combina los nombres proporcionados, reemplaza sus valores sin distinguir mayúsculas y conserva las demás cabeceras. `withBackground(None)` elimina la tarea. Estos métodos también devuelven `self` en un `Response` construido; allí la validación es inmediata y en un `PendingView` se difiere hasta el `await`. Los tipos de opción o rangos de estado inválidos producen `TypeError` o `ValueError`, independientemente de los errores de renderizado de plantilla. Se conserva la cabecera predeterminada `X-Orionis-Render: SSR` salvo que las cabeceras proporcionadas o una mutación posterior la reemplacen.

Los nombres `status_code`, `headers`, `background` y `context` son argumentos reservados. Para variables de plantilla con esos nombres usa el mapping explícito `context`, por ejemplo `View.make("errors.401", status_code=401, context={"status_code": "Session expired"})`. Las variables adicionales por nombre prevalecen sobre las entradas de ese mapping sin modificar el mapping original. Si `context` no es un mapping ni `None`, se lanza `TypeError` al preparar la vista; su validación no se difiere como la de las opciones HTTP.

### Preparar un formulario con errores

Configura sesiones y middleware CSRF antes de utilizar los helpers de formulario. El ejemplo de controlador requiere una aplicación iniciada y la plantilla `auth/login.html`:

```python
from orionis.support.facades import View


async def invalid_form():
    return await (
        View
        .make("auth.login")
        .withInput({"email": "ada@example.com"})
        .withErrors({"email": "Unknown account"})
        .withFlash("status", "Please review the form")
        .addHeader("Cache-Control", "no-store")
    )
```

```html
<form method="post" action="{{ url('/login') }}">
  {% csrf %}
  <label>Email <input name="email" value="{{ old('email', '') }}"></label>
  {% if errors.has('email') %}
    <p role="alert">{{ errors.first('email') }}</p>
  {% endif %}
  <label>Password <input type="password" name="password"></label>
  <button type="submit">Sign in</button>
</form>
```

`withInput()` filtra campos de credenciales conocidos, pero no es un clasificador universal de secretos: selecciona qué campos conservar. `withErrors()` normaliza mensajes escalares a listas. El flash se aplica antes del render; un fallo posterior de plantilla no deshace esa mutación de sesión. Sin sesión disponible, el pendiente omite las escrituras flash; el helper CSRF, en cambio, necesita poder resolver la sesión y su token.

Las mutaciones de `HTMLResponse`, como `addHeader()` o `withCookie()`, se ponen en cola y se reproducen después del render. Los argumentos se validan por la respuesta al aplicar cada llamada, no al encolarlos. Un atributo no invocable o inexistente produce `AttributeError`.

Los errores de plantilla conservan su causa original al atravesar la respuesta pendiente. Una cola saturada de workers de plantillas produce `WorkQueueFullError`, lo que permite distinguir la sobrecarga de una plantilla inválida.


### Renderizar directamente con un motor aislado

```python
import asyncio

import jinja2

from orionis.view.engine import Jinja2Engine


class Environment:
    def __init__(self) -> None:
        self.jinja = jinja2.Environment(
            loader=jinja2.DictLoader({"hello.html": "Hello {{ name }}!"}),
            enable_async=True,
            autoescape=True,
        )

    def getJinjaEnvironment(self) -> jinja2.Environment:
        return self.jinja


html = asyncio.run(Jinja2Engine(Environment()).render("hello", {"name": "Ada"}))
assert html == "Hello Ada!"
```

### Construir una respuesta HTML y poner mutaciones en cola

```python
import asyncio

from orionis.view.factory import ViewFactory


class Engine:
    async def render(self, template: str, context: dict) -> str:
        return f"<h1>{context['title']}</h1>"


pending = ViewFactory(Engine()).make("pages.home", title="Welcome")
pending.addHeader("X-Page", "home").withCookie("theme", "dark")
response = asyncio.run(pending.render())

assert response.getBody() == b"<h1>Welcome</h1>"
assert response.getHeader("X-Page") == ["home"]
assert response.getHeader("X-Orionis-Render") == ["SSR"]
```

### API de renderizado

- `View.make(template, *, status_code=200, headers=None, background=None, context=None, **variables) -> PendingView`: API principal de fachada tras arrancar la aplicación.
- `ViewFactory.make(...) -> PendingView`: equivalente inyectable con los mismos argumentos.
- `PendingView.render() -> HTMLResponse`: renderizado asíncrono explícito; esperar el objeto pendiente es equivalente.
- `PendingView.withStatusCode(status_code)`, `withHeaders(headers)` y `withBackground(background)`: ponen cambios de la respuesta HTTP en cola y devuelven la vista pendiente.
- `PendingView.withFlash(key, value=None)`, `withInput(values)` y `withErrors(errors)`: ponen estado flash de sesión en cola.
- `IViewFactory`, `IViewEngine` e `IViewEnvironment`: contratos para extensiones y otras implementaciones.

---

[Índice](README.md) · [http](../../../http/docs/es/README.md) · [session](../../../session/docs/es/README.md) · [mail](../../../mail/docs/es/README.md)
