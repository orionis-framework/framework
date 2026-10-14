# Configurar, extender y diagnosticar vistas

View renderiza HTML en el servidor mediante Jinja2 async y lo entrega como una respuesta Orionis.

## Configurar carga y caché

Las rutas se buscan por orden: una plantilla del primer directorio oculta otra del mismo nombre en los siguientes. El prefijo `__orionis__/default/` está reservado para las páginas empaquetadas y se resuelve antes que los paths de aplicación. Los paths relativos de búsqueda y caché se anclan a `app.basePath`.

La caché de plantillas de Jinja y la de bytecode son distintas: `cache_size` limita objetos compilados en memoria; `cache_path` conserva bytecode en disco. Poner `cache_path=None` desactiva solo la segunda. Si desactivas `auto_reload`, reinicia o reconstruye el entorno al publicar cambios: modificar una plantilla no fuerza la actualización de un proceso caliente. La caché no guarda respuestas HTML completas ni decide cache headers.

`Undefined` es permisivo: una variable ausente puede renderizar texto vacío. Eso facilita vistas opcionales pero también oculta errores de nombres. Prepara contexto explícito y verifica páginas con datos completos, vacíos y usuarios invitados. Los templates son código de aplicación confiable: el entorno no es un sandbox para aceptar plantillas arbitrarias de usuarios.

## Registrar filtros, tests y globals

El provider propio debe ejecutarse después de registrar los servicios de View. Añade su clase al registro de providers de tu aplicación según la configuración de Foundation. Este ejemplo muestra el cuerpo de la extensión; no registra la clase automáticamente:

```python
from orionis.container.providers.service_provider import ServiceProvider
from orionis.view.contracts.environment import IViewEnvironment


class ViewHelpersProvider(ServiceProvider):
    async def boot(self) -> None:
        environment: IViewEnvironment = await self.app.make(IViewEnvironment)
        environment.addFilter("money", lambda value: f"${value:,.2f}")
        environment.addTest("positive", lambda value: value > 0)
        environment.addGlobal("support_email", "help@example.com")
```

Úsalos con `{{ total | money }}`, `{% if total is positive %}` y `{{ support_email }}`. `addGlobal`/`addFilter`/`addTest` sustituyen un nombre existente; evita sobrescribir helpers fundamentales accidentalmente. `addExtension` admite extensiones Jinja y envuelve errores de registro en `ViewException`.

Para un motor alternativo implementa `IViewEngine.render(template, context) -> str` como método async y sustituye ese binding antes de resolver `IViewFactory`. La fábrica y el engine se cachean como singletons: cambiar un binding después de resolverlos no reconstruye automáticamente referencias existentes. Personaliza el entorno en boot y trátalo como compartido de solo lectura durante requests. No guardes un usuario ni un tenant en un global mutable.


## Configuración

| Variable de entorno | Predeterminado | Significado |
| --- | --- | --- |
| `VIEW_PATHS` | `["resources/views"]` | Directorios ordenados de búsqueda. |
| `VIEW_CACHE_SIZE` | `400` | Caché de plantillas compiladas; `0` desactiva, `-1` es ilimitado. |
| `VIEW_CACHE_PATH` | `storage/framework/views` | Directorio de bytecode; usa `None` en configuración para desactivarlo. |
| `APP_DEBUG` | `True` | Proporciona `auto_reload`; normalmente se desactiva en producción. |
| `VIEW_AUTOESCAPE` | `True` | Escape HTML automático para plantillas de aplicación. |

Las rutas y el directorio de caché pueden ser absolutos; los valores relativos parten de la base de la aplicación. `paths` debe ser una lista o tupla no vacía de cadenas y `cache_size` debe ser al menos `-1`.



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

### Personalización del entorno

- `ViewEnvironment.addGlobal(name, value)` registra un valor o callable global.
- `addFilter(name, callback)` registra una operación `value | filter`.
- `addTest(name, callback)` registra un predicado `value is test`.
- `addExtension(extension)` registra una extensión Jinja2 y envuelve fallos en `ViewException`.
- `getJinjaEnvironment()` devuelve el entorno compartido; el código externo debe tratarlo como solo lectura.

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

## Inspeccionar nombres de bytecode

`OrionisBytecodeCache` utiliza nombres legibles más un digest de ocho caracteres para distinguir rutas y extensiones. Es una caché compilada regenerable; no la uses como almacén de datos de negocio. Puedes comprobar la clave sin abrir archivos:

```python
from orionis.view.cache import OrionisBytecodeCache

cache = OrionisBytecodeCache("storage/framework/views")
key = cache.getCacheKey("users/profile.html")
assert key.startswith("users.profile.")
assert len(key.rsplit(".", 1)[-1]) == 8
assert key != cache.getCacheKey("users/profile.j2")
```

## Referencia de implementación para extensiones

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

---

[Índice](README.md) · [foundation](../../../foundation/docs/es/README.md) · [container](../../../container/docs/es/README.md) · [failure](../../../failure/docs/es/README.md)
