# Sesiones HTTP

Una sesión conserva datos en el servidor y envía al navegador únicamente un identificador aleatorio. Orionis la crea de forma perezosa: leer una sesión vacía no genera automáticamente registro ni cookie. El middleware web coordina restauración, flash, persistencia y limpieza.

1. [Estado y flash](state-and-flash.md): preferencias, formularios y navegación entre peticiones.
2. [Almacenamiento y concurrencia](stores-and-concurrency.md): elegir driver e implementar un store.
3. [Configuración y ciclo seguro](configuration-and-security.md): cookies, renovación y rotación.

Necesitas Python 3.14+ y rutas web para persistencia automática. `orionis.session` no reexporta clases en su raíz: inyecta `ISession`, usa la facade `Session` o importa la implementación desde su módulo. Lee antes [HTTP](../../../http/docs/es/README.md) y continúa con [autenticación](../../../auth/docs/es/README.md).
