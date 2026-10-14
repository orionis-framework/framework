# Introspection and metaprogramming

## Overview

This package wraps Python inspection in purpose-built APIs used throughout Orionis. It can classify a value, reflect a function, abstract or concrete class, instance, or importable module, split members by visibility and execution kind, discover Python modules, load classes, and translate callable parameters into dependency metadata.

The public package exports `Reflection`, the specialized reflection classes, `ReflectDependencies`, and `ModuleInspector`. Results that are expensive to compute are memoized; wrappers expose `clearCache()` when the inspected object is changed deliberately.

## Requirements

- Python 3.14 or newer.
- Importable modules and source files for operations that retrieve source or file paths.
- Runtime annotations when dependency injection must resolve a concrete type.
- `msgspec`, installed by Orionis, for recognizing schema dependencies.

## Module learning path

- [Dependencies, discovery, and reference](dependencies-and-discovery.md)
- [Inspecting classes, functions, and instances](reflection.md)

Continue with: [container](../../../container/docs/en/README.md) · [console](../../../console/docs/en/README.md).

Examples that require bootstrap, a request, or external services state that context. Verification for this reconstruction is distinct from historical notes; a production integration is not assumed to have been executed.
