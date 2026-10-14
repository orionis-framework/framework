# Salud, errores y rutas predeterminadas

El router registra favicon, `robots.txt`, `sitemap.xml` y la ruta de salud configurada por la aplicación. `DefaultResponses` renderiza páginas mediante `IViewEngine`, sirve un conjunto cerrado de recursos del paquete y ofrece respuestas JSON cuando corresponde. No es un servidor estático para cualquier archivo del proyecto.

## Comprobar disponibilidad

La ruta de salud devuelve 200 en estado normal y 503 durante mantenimiento. `Accept: application/json` solicita JSON con un mensaje de estado; la representación HTML muestra la página correspondiente. Es una señal del estado de la aplicación, no una comprobación automática de cada base de datos, cola o dependencia externa.

Puedes reemplazar los GET de favicon, robots y sitemap declarando esos paths en rutas de aplicación. Los archivos públicos usan una selección de candidatos con fallback del paquete donde existe. Un sitemap ausente puede terminar en 404; no se genera un catálogo de URLs de negocio.

## Presentar errores desde un servicio

```python
from orionis.http.default.contracts.responses import IDefaultResponses

async def unavailable(pages: IDefaultResponses):
    return await pages.error(
        503, {"message": "Catalog temporarily unavailable"},
        expects_json=True, headers={"Retry-After": "30"},
    )
```

El contenedor debe resolver `IDefaultResponses` en una aplicación inicializada. `error` acepta estado entero/`HTTPStatus` entre 100 y 599 y contenido texto o diccionario. HTML escapa la descripción; JSON conserva los valores. Si no proporcionas política de caché propia, el servicio añade la política conservadora predeterminada.

Las páginas de excepción contienen traceback y contexto y pueden incluir un enlace de asistencia que codifica parte del diagnóstico en una URL. Revisa qué información muestra tu manejador y configura debug para el entorno. El método `exception()` no constituye por sí solo una frontera de autorización para ver detalles.

## Personalizar autenticación opcional

`Route.auth()` registra GET/POST de login, registro y recuperación; GET de verificación de email y POST de logout. Logout exige identidad de sesión. Las páginas para invitados usan `GuestMiddleware`; la verificación admite el enlace desde un navegador ya autenticado. El pipeline web proporciona sesión y CSRF.

```python
from orionis.support.facades import Route

Route.auth()
```

Solo declara una vez desde rutas web. Puedes pasar `login_controller`, `register_controller` y `forgot_password_controller` para reemplazar cada controlador. Conserva los métodos que espera [el registro real](../../routes/auth.py). Los controladores predeterminados de registro/perfil dependen del modelo `app.models.user.User`, vistas, hashing y correo de la aplicación; no son un flujo genérico para cualquier modelo. Comprueba esos contratos antes de activarlos. Consulta [recuperación de cuentas](../../../auth/docs/es/account-recovery.md).

## Cachés y cambios de archivos

El kernel retiene el servicio exacto `DefaultResponses`; devuelve respuestas nuevas con estado mutable independiente. Salud conserva como máximo dos cuerpos HTML y los invalida cuando cambian nombre/locale. Errores y excepciones se renderizan por petición y sus datos no se cachean.

Los recursos permitidos conservan paths, no contenido ni resultados `stat`. El archivo seleccionado sigue reflejando cambios de contenido; añadir un candidato de prioridad superior exige reiniciar o eliminar `responses["favicon"]`, `responses["robots_txt"]` o `responses["sitemap_xml"]`. Un archivo seleccionado desaparecido fuerza nueva selección. La apertura aún puede fallar después de construir la respuesta.

Evidencia: [servicio](../../default/responses.py), [rutas auth](../../routes/auth.py), [controladores](../../default/controllers/login_controller.py). Pruebas: [cachés](../../../../tests/http/default/test_response_cache.py), [plantillas](../../../../tests/http/default/test_templates.py), [asistencia](../../../../tests/http/default/test_assistance.py), [rutas auth](../../../../tests/auth/test_auth_routes.py). La revisión histórica de rendimiento permanece en `default/docs/`; sus cifras no se presentan como benchmarks actuales.
