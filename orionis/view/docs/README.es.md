# orionis.view

> `orionis.view` renderiza plantillas Jinja2 asíncronas como respuestas HTML de Orionis con globals, filtros, datos flash y mutaciones de respuesta integrados con el framework.

## Descripción general

`orionis.view` renderiza HTML del lado del servidor con un entorno Jinja2 asíncrono integrado con enrutamiento, sesiones, localización, almacenamiento, seguridad y respuestas HTTP de Orionis. Los controladores usan normalmente la fachada `View`; la fábrica devuelve un `PendingView` diferido que puede acumular datos flash y mutaciones de respuesta antes de renderizar.

Las plantillas pueden referenciarse con notación de puntos como `users.profile` o con rutas relativas como `users/profile.html`. El renderizado siempre usa la ruta asíncrona de Jinja2 y produce un `HTMLResponse` de Orionis con `X-Orionis-Render: SSR`.

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
<a href="{{ await route('users.edit', id=user.id) }}">Edit</a>
```

Devuélvela desde un controlador asíncrono:

```python
from orionis.support.facades import View

async def profile(user):
    return await View.make("users.profile", user=user)
```

## Conceptos principales

### Entorno, motor y fábrica

`ViewEnvironment` posee el único `Environment` Jinja2 configurado, incluidos loaders, cachés, globals, filtros, tests y extensiones. `Jinja2Engine` normaliza identificadores y renderiza asíncronamente. `ViewFactory.make()` crea un `PendingView` en vez de renderizar de inmediato.

`ViewServiceProvider` enlaza los contratos de entorno, motor y fábrica como singletons, registra los componentes integrados y fija la fachada durante el arranque.

### Respuestas diferidas

`PendingView` es awaitable. Antes de esperarlo, invoca `withFlash()`, `withInput()` o `withErrors()` para poner datos flash en cola. También puede encadenarse cualquier método público invocable de `HTMLResponse`, incluidos `addHeader()`, `withCookie()` y `withoutCookie()`; las llamadas se registran y se reproducen en orden después de renderizar.

La entrada enviada se filtra para no almacenar en flash campos similares a credenciales, como contraseñas. Si no existe sesión activa, los datos flash se omiten sin impedir el renderizado.

### Carga de plantillas y escape

Las rutas configuradas se buscan en orden. Las relativas parten de la base de la aplicación. Las páginas de error incluidas por Orionis siguen disponibles bajo el prefijo reservado `__orionis__/default/`. Las plantillas de aplicación usan `autoescape`; las páginas del framework siempre escapan expresiones.

La notación de puntos se convierte en barras y recibe `.html` cuando no hay extensión. Un nombre que ya contiene `/` se trata como ruta. Por ejemplo, `mail.receipt` se vuelve `mail/receipt.html`, mientras `mail/receipt.j2` se conserva.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| `cache.py` | Nombres legibles y resistentes a colisiones para bytecode Jinja2. |
| `contracts/` | Interfaces de entorno, motor y fábrica. |
| `engine.py` | Renderizado Jinja2 asíncrono y normalización de nombres. |
| `environment.py` | Configuración de loaders, escape y cachés en memoria/disco. |
| `exceptions.py` | Jerarquía de excepciones de vistas. |
| `extensions/csrf.py` | Sentencia Jinja `{% csrf %}`. |
| `factory.py` | Fábrica pública de renderizados pendientes. |
| `filters/` | Filtros `json` y `markdown`. |
| `globals/` | Auxiliares de plantilla conscientes de la aplicación. |
| `pending.py` | Renderizado awaitable, cola flash y cola de mutaciones. |
| `provider.py` | Bindings del contenedor y registros integrados. |

## API pública

### API de renderizado

- `View.make(template, **context) -> PendingView`: API principal de fachada tras arrancar la aplicación.
- `ViewFactory.make(template, **context) -> PendingView`: equivalente inyectable.
- `PendingView.render() -> HTMLResponse`: renderizado asíncrono explícito; esperar el objeto pendiente es equivalente.
- `PendingView.withFlash(key, value=None)`, `withInput(values)` y `withErrors(errors)`: ponen estado flash de sesión en cola.
- `IViewFactory`, `IViewEngine` e `IViewEnvironment`: contratos para extensiones y otras implementaciones.

### Personalización del entorno

- `ViewEnvironment.addGlobal(name, value)` registra un valor o callable global.
- `addFilter(name, callback)` registra una operación `value | filter`.
- `addTest(name, callback)` registra un predicado `value is test`.
- `addExtension(extension)` registra una extensión Jinja2 y envuelve fallos en `ViewException`.
- `getJinjaEnvironment()` devuelve el entorno compartido; el código externo debe tratarlo como solo lectura.

### Excepciones

`ViewException` es la base común. `ViewTemplateNotFoundException` representa fallos del loader, `ViewRenderException` envuelve errores de renderizado y `ViewRouteException` informa rutas con nombre desconocidas o parámetros faltantes.

## Flujos de trabajo comunes

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

### Volver a mostrar un formulario fallido

```python
from orionis.view.factory import ViewFactory

class Engine:
    async def render(self, template: str, context: dict) -> str:
        return ""

pending = ViewFactory(Engine()).make("auth.login")
pending.withInput({"email": "ada@example.com", "password": "secret"})
pending.withErrors({"email": "Unknown account"})
pending.withFlash("status", "Please review the form")

assert pending._flash["_old_input"] == {"email": "ada@example.com"}
assert pending._flash["_errors"] == {"email": ["Unknown account"]}
```

## Ejemplos

### Validar la configuración

```python
from orionis.foundation.config.view import View

config = View(
    paths=["resources/views", "packages/admin/views"],
    cache_size=400,
    cache_path="storage/framework/views",
    auto_reload=False,
    autoescape=True,
)

assert config.paths[0] == "resources/views"
assert config.autoescape is True
```

### Usar los filtros integrados

```python
from orionis.view.filters import _filter_json, _filter_markdown

jsonify = _filter_json()
markdown = _filter_markdown()

assert jsonify({"ok": True}) == '{"ok":true}'
assert markdown("**safe**").strip() == "<p><strong>safe</strong></p>"
```

### Inspeccionar normalización y claves de caché

```python
from orionis.view.cache import OrionisBytecodeCache
from orionis.view.engine import Jinja2Engine

assert Jinja2Engine._normalisePath("users.profile") == "users/profile.html"
assert Jinja2Engine._normalisePath("partials/nav.j2") == "partials/nav.j2"

cache = OrionisBytecodeCache("storage/framework/views")
key = cache.getCacheKey("users/profile.html")
assert key.startswith("users.profile.")
assert len(key.rsplit(".", 1)[-1]) == 8
```

## Configuración

| Variable de entorno | Predeterminado | Significado |
| --- | --- | --- |
| `VIEW_PATHS` | `["resources/views"]` | Directorios ordenados de búsqueda. |
| `VIEW_CACHE_SIZE` | `400` | Caché de plantillas compiladas; `0` desactiva, `-1` es ilimitado. |
| `VIEW_CACHE_PATH` | `storage/framework/views` | Directorio de bytecode; usa `None` en configuración para desactivarlo. |
| `APP_DEBUG` | `True` | Proporciona `auto_reload`; normalmente se desactiva en producción. |
| `VIEW_AUTOESCAPE` | `True` | Escape HTML automático para plantillas de aplicación. |

Las rutas y el directorio de caché pueden ser absolutos; los valores relativos parten de la base de la aplicación. `paths` debe ser una lista o tupla no vacía de cadenas y `cache_size` debe ser al menos `-1`.

## Integración con Orionis

El proveedor registra estos globals: `app`, `asset`, `secure_asset`, `cache`, `collect`, `config`, `csrf_field`, `csrf_token`, `dump`, `encrypt`, `decrypt`, `errors`, `flash`, `framework_version`, `python_version`, `now`, `today`, `old`, `request`, `route`, `session`, `stringable`, `url`, `secure_url`, `trans`/`__`, `choice`, `locale` y `locales`.

Muchos globals son asíncronos porque resuelven estado del framework vinculado al ámbito. El renderer asíncrono de Jinja espera sus valores; las llamadas explícitas en plantillas pueden usar `await` como en el inicio rápido. Los filtros `json` y `markdown` y la extensión `{% csrf %}` se instalan automáticamente.

La generación de rutas con nombre interpola marcadores `{name}` y `{name:type}`, codifica valores de ruta con porcentaje y añade argumentos restantes como query parameters. Con una petición activa, los auxiliares construyen URLs absolutas desde ella; de otro modo, la ruta puede devolver el path interpolado.

## Errores y casos límite

- Las plantillas ausentes conservan `ViewTemplateNotFoundException`; los demás fallos del render pendiente se envuelven en `ViewRenderException` preservando su causa.
- El motor envuelve los errores de plantilla Jinja en `ViewRenderException`.
- Atributos encadenados desconocidos de `PendingView` lanzan `AttributeError`; solo pueden ponerse en cola atributos invocables de `HTMLResponse`.
- Las operaciones flash no hacen nada si no está disponible el servicio de sesión.
- `errors.first()` devuelve el primer mensaje disponible y la bolsa normaliza mensajes escalares a listas.
- El filtro JSON devuelve `str(value)` cuando msgspec no puede codificarlo.
- El filtro Markdown emite HTML; las reglas de autoescape determinan si la cadena se trata como markup al insertarla.
- La extensión `{% csrf %}` lanza `ViewRenderException` si `csrf_field` no está registrado.
- Una ruta con nombre desconocida o un parámetro faltante lanza `ViewRouteException`.
- El `Undefined` predeterminado de Jinja es permisivo; una variable ausente suele renderizarse vacía en vez de lanzar.

## Rendimiento y concurrencia

El entorno, el motor y la fábrica son singletons. Jinja conserva hasta `cache_size` plantillas compiladas en memoria y opcionalmente persiste bytecode en disco. Los nombres de caché incluyen el nombre aplanado y legible más un digest SHA-1 de ocho caracteres para evitar colisiones de extensiones o rutas.

La normalización de nombres usa una caché LRU protegida por bloqueo y limitada a 1.024 entradas. Los planes de interpolación de rutas con nombre se memoizan; hilos en carrera solo pueden calcular y almacenar el mismo valor determinista. El renderizado es asíncrono, mientras el entorno compartido solo se modifica durante el arranque. Registra globals, filtros, tests y extensiones personalizados al arrancar proveedores, no durante peticiones concurrentes.

## Compatibilidad

El módulo requiere Python 3.14+ y renderizado asíncrono de Jinja2. Las plantillas usan sintaxis Jinja2, no cadenas de formato Python. `PendingView` devuelve el `HTMLResponse` nativo de Orionis, por lo que cabeceras, cookies, trabajo en segundo plano y transportes posteriores siguen los contratos del módulo HTTP.

`orionis.view` no posee reexportaciones raíz; usa `orionis.support.facades.View` en código de aplicación o importa clases concretas desde sus módulos de definición para extensiones y pruebas aisladas.

## Notas de verificación

Esta documentación se regeneró contra el código fuente actual y se verificó con CPython 3.14.6. Los 207 métodos de prueba bajo `tests/view` aprobaron. Los siete bloques Python son idénticos entre idiomas: los seis ejemplos autónomos de implementación se ejecutaron correctamente y el inicio rápido con fachada se validó sintácticamente porque requiere una aplicación y un archivo de plantilla.
