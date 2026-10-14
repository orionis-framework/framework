# Contraseñas

El flujo de una contraseña consta de validación, hashing, almacenamiento del resultado y comprobación en el siguiente acceso. La política de costes y la migración de algoritmos forman parte de ese mismo flujo.

## Recorrido

1. [Almacenar, comprobar y actualizar contraseñas](password-storage.md): requisitos, uso progresivo, configuración, integración, errores y referencia pública.

Los ejemplos aislados usan objetos de aplicación mínimos; las facades requieren una aplicación Orionis inicializada y sus providers. El código fuente y los contratos determinan las capacidades descritas.

Relacionados: [auth](../../../auth/docs/es/README.md) · [encrypter](../../../encrypter/docs/es/README.md)
