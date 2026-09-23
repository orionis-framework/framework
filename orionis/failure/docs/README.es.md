# Errores Auth en el pipeline de excepciones

`Catch.exception()` obtiene el kernel del scope, reporta el error por el handler
configurado e invoca su método CLI o HTTP. `BaseExceptionHandler` busca el estado
HTTP en la clase de excepción y sus ancestros.

| Familia de excepción | Estado |
|---|---|
| `AuthenticationException` | 401 |
| `AuthorizationException` | 403 |
| `CSRFTokenMismatchException` | 419 |
| Errores sin mapping | 500 |

Fallos Auth usan mensajes públicos fijos, no las credenciales recibidas. El guard
token añade `WWW-Authenticate: Bearer` a sus fallos de autenticación. La negociación
estándar conserva HTML o JSON. Subclases de aplicación mantienen el estado de su
ancestro Auth.

El middleware Session web convierte excepciones posteriores antes de persistir
la respuesta: logout y flash sobreviven a una respuesta de error. La cancelación
se propaga después de persistir revocación pendiente. El scope HTTP exterior se
cierra también cuando hay excepciones.

Errores SQL omiten valores y detalles del driver en el límite de base de datos.
Las aplicaciones tampoco deben incluir passwords, tokens en claro o cookies en
excepciones personalizadas ni logs. Desactivar páginas debug en producción.

El contrato está en [Auth](../../auth/docs/README.es.md).
