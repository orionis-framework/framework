# Entorno y configuración de proceso

## Descripción general

La API del paquete es `Env` junto al helper `env()`. Ambos delegan a un singleton de proceso `DotEnv`. En el primer uso resuelve `.env` desde el directorio actual, lo crea si falta, lo carga en `os.environ` dando precedencia al archivo y conserva sus entradas para `all()`.

Los valores pueden usar prefijos explícitos como `int:`, `bool:`, `list:`, `path:` o `base64:`. Los no prefijados aún reconocen nulos, booleanos y literales Python seguros. `EnvironmentCaster` implementa serialización y parsing tipado.

## Requisitos

- Python 3.14 o posterior.
- `python-dotenv>=1.2.3,<2.0`, instalado por Orionis.
- Acceso de lectura al `.env` elegido para la carga inicial y `reload`; acceso de escritura para crear el archivo y ejecutar `set` o `unset` persistentes.
- Claves de consulta y modificación públicas que coincidan con `[A-Z][A-Z0-9_]*`.

## Recorrido del módulo

- [Persistencia, recarga y referencia de Env](operations-and-reference.md)
- [Leer y escribir configuración de entorno](typed-configuration.md)

Continúa por: [foundation](../../../foundation/docs/es/README.md) · [encrypter](../../../encrypter/docs/es/README.md).

Los ejemplos funcionan sin iniciar la aplicación ni usar servicios externos. Ejecútalos desde un directorio temporal: incluso la primera operación limitada al proceso inicializa el singleton y carga el `.env` elegido.
