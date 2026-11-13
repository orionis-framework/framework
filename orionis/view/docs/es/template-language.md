# Construir layouts y utilizar helpers

Combina la sintaxis Jinja con los servicios Orionis sin mezclar lógica de negocio y presentación.

## Componer layouts reutilizables

Las plantillas usan Jinja2, con expresiones `{{ value }}` y sentencias `{% ... %}`. Prepara datos en tu controlador o servicio; no introduzcas consultas costosas dentro de cada iteración. Los callables async se esperan automáticamente por el entorno async: escribe `{{ route("users.edit", id=user.id) }}`. La palabra Python `await` no forma parte de una expresión de plantilla.

Crea `resources/views/layouts/base.html`:

```html
<!doctype html>
<html lang="en">
<head><title>{% block title %}Reports{% endblock %}</title></head>
<body>
  {% include "partials/navigation.html" %}
  <main>{% block content %}{% endblock %}</main>
</body>
</html>
```

Crea `partials/navigation.html` con tu navegación, y `reports/index.html` con:

```html
{% extends "layouts/base.html" %}
{% block title %}Recent reports{% endblock %}
{% block content %}
  <ul>
  {% for report in reports %}
    <li>{{ report.title }}</li>
  {% else %}
    <li>No reports yet.</li>
  {% endfor %}
  </ul>
{% endblock %}
```

Devuelve `await View.make("reports.index", reports=reports)`. `extends` reutiliza el layout y `block` reemplaza una zona; `include` inserta otra plantilla. Un bucle con `{% else %}` cubre colecciones vacías. Para bloques con parámetros puedes utilizar macros de Jinja; Orionis no añade una sintaxis propia de componentes ni directivas Blade.

## Helpers de aplicación

Los siguientes nombres se registran durante `ViewServiceProvider.boot()`. Los helpers que resuelven request, sesión o servicios necesitan esos componentes activos; no basta crear una instancia aislada de `Jinja2Engine`.

| Tarea | Helpers disponibles |
|---|---|
| Rutas y enlaces | `route(name, **params)`, `url(path="/", **query)`, `secure_url(path="/", **query)` |
| Assets | `asset(path, disk=None)`, `secure_asset(path, disk=None)`; disco `public` si se omite. |
| Autenticación | `auth()` devuelve la facade; `auth().user()`, `.check()`, `.guest()`. |
| Solicitud / sesión | `request()`, `session()`; pueden devolver `None` fuera de scope. |
| Formularios | `old(key, default=None)`, `errors.any/has/get/first/all`, `flash(key, default=None)` |
| CSRF | `csrf_token()`, `csrf_field()`, `{% csrf %}`; el campo oculto se llama `_csrf`. |
| Traducción | `trans(key, locale=None, **replace)`, `__(...)`, `choice(key, count, locale=None, **replace)`, `locale()`, `locales()` |
| Estado global | `app()`, `config(key, default=None)`, `cache(key, default=None)` |
| Datos y diagnóstico | `collect(value=None)`, `stringable(value="")`, `dump(*values)` |
| Fecha/versiones | `now()`, `today()`, `framework_version()`, `python_version()` |
| Cifrado | `encrypt(plaintext)`, `decrypt(payload)` |

Los parámetros de `route` usados en el path se codifican; los restantes forman query string. `url` y `secure_url` insertan los parámetros de consulta antes de un `#fragment` existente y conservan literalmente ese fragmento. Una ruta inexistente o un argumento obligatorio ausente produce `ViewRouteException`. Las URLs usan el origen de la solicitud cuando existe y pueden ser relativas fuera de scope. `secure_url` cambia el esquema a HTTPS si hay host; no descubre uno para una ruta relativa. `asset` pide `file.url()` al disco: no comprueba existencia ni publica el archivo.

`cache(key, default)` considera `None` como ausencia. `errors` es una bolsa con métodos, no un dict. `errors.any()` requiere al menos una lista de mensajes no vacía; las claves asociadas a listas vacías no cuentan. Fuera del scope de sesión, cada resultado vacío es independiente; con sesión, `errors.all()` devuelve el mapping de errores existente. `old` devuelve texto vacío para un valor `None`. `auth()` no cachea identidad: conserva el scope de la solicitud; comprueba `auth().check()` antes de acceder a atributos del usuario. Para locales concurrentes pasa `locale=` explícitamente, porque `locale()` refleja el valor global compartido.

`today()` devuelve un `pendulum.DateTime` a medianoche. `encrypt` y `decrypt` utilizan el encrypter configurado.

## Escape y contenido confiable

El autoescape está habilitado para la aplicación por defecto. Conserva `{{ user.name }}` con escape; `|safe` y `Markup` solo deben utilizarse con HTML que controles. Tanto `json` como `markdown` devuelven valores `str` normales sujetos al autoescape de Jinja. El filtro `markdown` produce HTML sin sanitización de contenido arbitrario. Marcarlo como seguro puede permitir HTML introducido por usuarios; incorpora una política de sanitización si tu producto acepta Markdown externo.

`json` serializa con msgspec, opcionalmente `|json(indent=2)`, pero devuelve `str(value)` si falla la serialización o el formato. Es un filtro de presentación, no una garantía de JSON válido para todos los objetos ni un escape específico para `<script>`. Evita interpolarlo como código ejecutable. La etiqueta `{% csrf %}` acepta builders `csrf_field` síncronos o asíncronos, escapa las cadenas normales y conserva los valores `Markup`. La ausencia del builder produce `ViewRenderException`.

`dump()` expone datos como HTML y debe reservarse para diagnóstico controlado; no vuelques secretos. Los helpers de cifrado no reemplazan la autorización.

---

[Índice](README.md) · [auth](../../../auth/docs/es/README.md) · [localization](../../../localization/docs/es/README.md) · [storage](../../../storage/docs/es/README.md) · [session](../../../session/docs/es/README.md)
