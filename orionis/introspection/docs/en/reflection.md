# Inspecting classes, functions, and instances

## Quick start

```python
from orionis.introspection import Reflection


def greet(name: str, punctuation: str = "!") -> str:
    """Build a greeting."""
    return f"Hello, {name}{punctuation}"


reflected = Reflection.callable(greet)
assert reflected.getName() == "greet"
assert list(reflected.getSignature().parameters) == ["name", "punctuation"]
assert reflected.getDocstring() == "Build a greeting."
print(reflected.getModuleWithCallableName())
```

## Core concepts

### Reflection kinds

`Reflection` is a static entry point. `callable()`, `abstract()`, `concrete()`, `instance()`, and `module()` validate the input and return a specialized wrapper. Predicate helpers mirror `inspect` for functions, methods, classes, modules, generators, coroutines, descriptors, frames, code, tracebacks, and awaitables, with additional Orionis checks for concrete classes, instances, generics, protocols, and typing constructs.

### Member classification

Class and instance wrappers classify public, protected, private, dunder, and “magic” members. Methods are further separated into instance, class, and static methods and into synchronous and asynchronous variants. Python-mangled private names are recognized by the exact `_ClassName__` marker and exposed as their source-level `__name`, preserving both leading underscores. Class names containing only underscores do not enable mangling. Class scans classify declared members; they do not promise a complete inherited-member listing. Instance attributes include populated inherited slots and exclude callable members. Changing a class name or module refreshes its identity metadata after invalidation; the private-name prefix retains the original declaration name because Python does not remangle existing members.

### Dependency signatures

`ReflectDependencies` converts a constructor, method, or callable signature into a `Signature` containing `resolved`, `unresolved`, and declaration-ordered maps of immutable `Argument` values. Bound instance/class receivers are omitted according to descriptor binding, regardless of their name. Ordinary function and static-method parameters named `self` or `cls` remain explicit arguments. `*args` and `**kwargs` are omitted. A parameter with a default is resolved from the default's type; a non-builtin annotation is resolved for container lookup; an unannotated or builtin-only required parameter remains unresolved. `msgspec.Struct` subclasses are marked as schemas.

### Caching

Reflection wrappers cache scans, source, files, annotations, and signatures locally. Dependency analysis uses bounded module-level LRU caches of 1,024 entries. `ModuleInspector.loadClass()` uses Python's import cache and reads the current class attribute on each call, so replacement modules or classes are visible. Bound-method caching avoids retaining controller instances. `ReflectDependencies` inspects unhashable callable objects without the shared LRU cache.

`clearCache()` clears the wrapper's local metadata and invalidates shared signature caches and invocation plans. Other existing wrappers retain their own local cached results until their own `clearCache()` is called.

## Examples

### Classify a concrete class

```python
from orionis.introspection import Reflection


class Worker:
    category = "demo"

    def run(self, value: int) -> int:
        return value + 1

    async def stop(self) -> None:
        return None


reflected = Reflection.concrete(Worker)
assert reflected.getClassName() == "Worker"
assert "run" in reflected.getPublicSyncMethods()
assert "stop" in reflected.getPublicAsyncMethods()
assert reflected.getAttribute("category") == "demo"
print(reflected.getMethodSignature("run"))
```

### Reflect an importable module

```python
from orionis.introspection import Reflection

module = Reflection.module("orionis.introspection.reflection")
assert module.hasClass("Reflection")
assert module.getClass("Reflection") is Reflection
assert module.getFile().endswith("reflection.py")
print(sorted(module.getPublicClasses()))
```

## Evidence and next steps

[reflection.py](../../reflection.py) · [reflection.py](../../concretes/reflection.py) · [reflection.py](../../instances/reflection.py) · [reflection.py](../../callables/reflection.py)

[Return to the module index](README.md).
