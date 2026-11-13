# Introspección y metaprogramación

## Descripción general

Este paquete envuelve la inspección de Python en APIs especializadas que usa todo Orionis. Puede clasificar un valor, reflejar una función, clase abstracta o concreta, instancia o módulo importable, separar miembros por visibilidad y tipo de ejecución, descubrir módulos Python, cargar clases y convertir parámetros de callables en metadatos de dependencias.

El paquete público exporta `Reflection`, las clases especializadas, `ReflectDependencies` y `ModuleInspector`. Los resultados costosos se memoizan; los wrappers exponen `clearCache()` cuando el objeto inspeccionado se modifica deliberadamente.

## Requisitos

- Python 3.14 o posterior.
- Módulos importables y archivos fuente para operaciones que recuperan código o rutas.
- Anotaciones disponibles en runtime cuando la inyección debe resolver un tipo concreto.
- `msgspec`, instalado por Orionis, para reconocer dependencias de schemas.

## Recorrido del módulo

- [Dependencias, descubrimiento y referencia](dependencies-and-discovery.md)
- [Inspeccionar clases, funciones e instancias](reflection.md)

Continúa por: [container](../../../container/docs/es/README.md) · [console](../../../console/docs/es/README.md).
