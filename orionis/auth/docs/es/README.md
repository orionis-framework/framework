# Autenticación y autorización

Orionis resuelve la identidad actual mediante sesión de navegador o token personal y aplica permisos, roles y políticas. El contexto pertenece a la petición; los servicios compartidos no guardan un usuario global.

Una referencia conservada al contexto pasa a ser invitada cuando se reemplaza o se cierra el scope de su petición. Los lectores de permisos vuelven a comprobar esa pertenencia después de esperar a otro lector. Las operaciones de sesión en espera de otra transición de autenticación también requieren una petición activa antes de invocar el guard.

Los contratos públicos se resuelven de forma diferida desde `orionis.auth.contracts`. Los imports directos y las reexportaciones conservan la identidad de los tipos sin inicialización circular entre guards y entidades.

1. [Identidad y login de sesión](identity-and-session.md): modelo, guards, login y logout.
2. [Permisos, roles y políticas](authorization.md): proteger capacidades y recursos.
3. [Tokens personales](personal-access-tokens.md): emitir, limitar y revocar credenciales.
4. [Recordarme y recuperación de cuentas](account-recovery.md): cookies persistentes, reset y páginas predeterminadas.

Requiere Python 3.14+, modelo ORM configurado, hashing y almacenamiento interno de autenticación para persistencia. Los ejemplos de facade y repositorios necesitan una aplicación inicializada; los ejemplos de snapshots son independientes. Revisa [sesiones](../../../session/docs/es/README.md), [HTTP](../../../http/docs/es/README.md) y [ORM](../../../orm/docs/es/README.md).

## Preparar el almacenamiento de autenticación

En una base nueva, aplica las migraciones de aplicación, prepara las tablas internas de auth y luego ejecuta los seeders de aplicación:

```shell
python -B reactor migrate
python -B reactor auth:migrate
python -B reactor seed
```

`auth:migrate` crea roles, permisos, sus tres tablas de asignación, tokens personales y almacenamiento de recuperación de contraseñas desde definiciones del core. Usa la conexión SQL predeterminada de la aplicación y respeta su prefijo, `AUTH_TOKEN_TABLE` y `AUTH_PASSWORD_RESET_TABLE`. Repetirlo conserva los registros existentes; el comando no crea usuarios, concede privilegios, ejecuta seeders ni escribe historial de migraciones de aplicación.

El modelo de identidad y su migración, los nombres de roles/permisos del negocio, sus asignaciones y las políticas de recursos siguen en la aplicación. Consulta la [preparación de tablas internas y precauciones de actualización](../../../database/docs/es/migrations-and-seeders.md#preparar-tablas-internas-del-framework).

## Ejecución acotada y rendimiento

El proveedor de modelos y el repositorio de tokens nativos combinan los SELECT de token e identidad cuando comparten conexión nativa, la clave es entera/textual y los scopes conservan una consulta simple. Mantienen filtros de scopes, hidratación, eventos retrieved y relaciones anticipadas. Los metadatos del token se validan antes de los eventos; el guard conserva la actualización condicional final de `last_used_at`, comprobando revocación y vencimiento después de resolver la identidad. La ruta admitida usa dos sentencias en lugar de tres y nunca cachea una decisión de autenticación.

Los proveedores/repositorios/conexiones personalizados, claves UUID, bases separadas y scopes complejos mantienen la ruta original. La conversión SQL de claves enteras almacenadas está protegida frente a valores inválidos o fuera de rango. Compilar SQL no sustituye las pruebas de integración con cada motor desplegado.
