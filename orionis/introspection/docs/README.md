# orionis.introspection

> `orionis.introspection` provides cached reflection for callables, classes, instances, modules, and dependency-injection signatures.

## Overview

This package wraps Python inspection in purpose-built APIs used throughout Orionis. It can classify a value, reflect a function, abstract or concrete class, instance, or importable module, split members by visibility and execution kind, discover Python modules, load classes, and translate callable parameters into dependency metadata.

The public package exports `Reflection`, the specialized reflection classes, `ReflectDependencies`, and `ModuleInspector`. Results that are expensive to compute are memoized; wrappers expose `clearCache()` when the inspected object is changed deliberately.

## Requirements

- Python 3.14 or newer.
- Importable modules and source files for operations that retrieve source or file paths.
- Runtime annotations when dependency injection must resolve a concrete type.
- `msgspec`, installed by Orionis, for recognizing schema dependencies.

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

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Reflection kinds

`Reflection` is a static entry point. `callable()`, `abstract()`, `concrete()`, `instance()`, and `module()` validate the input and return a specialized wrapper. Predicate helpers mirror `inspect` for functions, methods, classes, modules, generators, coroutines, descriptors, frames, code, tracebacks, and awaitables, with additional Orionis checks for concrete classes, instances, generics, protocols, and typing constructs.

### Member classification

Class and instance wrappers classify public, protected, private, dunder, and “magic” members. Methods are further separated into instance, class, and static methods and into synchronous and asynchronous variants. Python-mangled private names are presented without their class prefix, so callers use the source-level name.

### Dependency signatures

`ReflectDependencies` converts a constructor, method, or callable signature into a `Signature` containing `resolved`, `unresolved`, and declaration-ordered maps of immutable `Argument` values. `self`, `cls`, `*args`, and `**kwargs` are omitted. A parameter with a default is resolved from the default's type; a non-builtin annotation is resolved for container lookup; an unannotated or builtin-only required parameter remains unresolved. `msgspec.Struct` subclasses are marked as schemas.

### Caching

Reflection wrappers cache scans, source, files, annotations, and signatures locally. Dependency analysis uses bounded module-level LRU caches of 1,024 entries. `ModuleInspector.loadClass()` also retains resolved class objects by fully qualified name. Bound-method caching avoids retaining controller instances.

## Module structure

| Path | Responsibility |
|---|---|
| `reflection.py` | Factory and general-purpose classification predicates. |
| `callables/` | Function/method metadata, source, inspect signature, and dependencies. |
| `abstract/` | Reflection and member classification for abstract classes. |
| `concretes/` | Reflection, mutation, and dependency signatures for concrete classes. |
| `instances/` | Instance state plus class member/property reflection. |
| `modules/reflection.py` | Imported-module classes, constants, functions, source, and cache. |
| `modules/inspector.py` | Filesystem discovery, AST import checks, class loading, frozen dataclasses. |
| `dependencies/` | Signature resolution and `Argument` / `Signature` entities. |
| `*/contracts/` | Abstract contracts for each reflection specialization. |

## Public API

### `Reflection`

- `instance(value)`, `abstract(cls)`, `concrete(cls)`, `module(name)`, and `callable(fn)` construct wrappers.
- `isAbstract`, `isConcreteClass`, `isInstance`, `isGeneric`, `isProtocol`, and `isTypingConstruct` apply Orionis classifications.
- `isAsyncGen`, `isAsyncGenFunction`, `isAwaitable`, `isBuiltIn`, `isClass`, `isCode`, `isCoroutine`, `isCoroutineFunction`, `isDataDescriptor`, `isFrame`, `isFunction`, `isGenerator`, `isGeneratorFunction`, `isGetSetDescriptor`, `isMemberDescriptor`, `isMethod`, `isMethodDescriptor`, `isModule`, `isRoutine`, and `isTraceback` expose runtime predicates.

### `ReflectionCallable`

Provides `getCallable`, `getName`, `getModuleName`, `getModuleWithCallableName`, `getDocstring`, `getSourceCode`, `getFile`, `getSignature`, `getDependencies`, and `clearCache`. Its item protocol is a small user-accessible memory cache.

### Class and instance wrappers

Both families expose identity, module, docstring, bases, source, file, annotations, attributes, methods, properties, inspect signatures, dependency signatures, and cache clearing. The many `getPublic*`, `getProtected*`, and `getPrivate*` methods select visibility; `Sync` and `Async` selectors narrow method kind. Concrete and instance wrappers also support controlled attribute/method mutation.

`ReflectionAbstract` supplies the same read-oriented classification surface for abstract classes while preserving abstract member semantics.

### `ReflectionModule`

Imports a dotted module and exposes classes, constants, functions, imports, source, and file. Class and constant getters divide names by visibility; function getters additionally divide sync from async. Its mapping protocol reads or mutates module attributes.

### `ReflectDependencies` and `Signature`

`constructorSignature()`, `methodSignature(name)`, and `callableSignature()` return a `Signature`. The entity offers predicates and selectors: `hasParameters`, `noArgumentsRequired`, `hasUnresolvedArguments`, `getResolved`, `getUnresolved`, `getAllOrdered`, `getPositionalOnly`, `getKeywordOnly`, conversion helpers, and `arguments()`.

### `ModuleInspector`

- `discoverModules(base_path, target_path)` returns dotted modules below a safe base.
- `loadClass(module_path, class_name)` or `loadClass(metadata=...)` imports a class.
- `fileImportsAny(path, targets, allow_empty=False)` parses imports without executing the file.
- `discoverFrozenDataclasses(modules)` imports modules and returns declared frozen dataclasses.

## Common workflows

### Build container arguments

Reflect the selected constructor or handler. Resolve `Signature.resolved` values from the container or schema decoder, and require the caller to provide unresolved builtins or unannotated parameters. Preserve `ordered` and `is_keyword_only` when invoking the target.

### Discover application components

Use `discoverModules()` below a known application root, optionally filter source files with `fileImportsAny()`, and load a declared class with `loadClass()`. Orionis uses this pattern for console commands, migrations, seeders, configuration entities, and queued jobs.

### Inspect code without mutation

Choose the narrowest wrapper, then use its categorized getters. Source/file retrieval can fail for dynamic or built-in objects; metadata and inspect signatures may still be available. Treat returned mutable dictionaries/lists as reflection results, not as authoritative live registries.

### Modify reflected members

`setAttribute`, `removeAttribute`, `setMethod`, module item assignment, and deletion affect the actual reflected class, instance, or module. Clear the wrapper cache after external mutation; wrapper mutation methods invalidate affected data themselves. Restrict this capability to bootstrapping, tests, and controlled metaprogramming.

## Examples

### Analyze injection arguments

```python
from orionis.introspection import ReflectDependencies


class Repository:
    pass


def handler(repository: Repository, raw, *, limit=25):
    return repository, raw, limit


signature = ReflectDependencies(handler).callableSignature()
assert list(signature.getAllOrdered()) == ["repository", "raw", "limit"]
assert list(signature.getResolved()) == ["repository", "limit"]
assert list(signature.getUnresolved()) == ["raw"]
assert signature.getKeywordOnly()["limit"].default == 25
print(signature.hasUnresolvedArguments())
```

Validation: **Executed successfully** on CPython 3.14.6.

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

Validation: **Executed successfully** on CPython 3.14.6.

### Reflect an importable module

```python
from orionis.introspection import Reflection

module = Reflection.module("orionis.introspection.reflection")
assert module.hasClass("Reflection")
assert module.getClass("Reflection") is Reflection
assert module.getFile().endswith("reflection.py")
print(sorted(module.getPublicClasses()))
```

Validation: **Executed successfully** on CPython 3.14.6.

### Discover modules and load a class

```python
from pathlib import Path
from orionis.introspection import ModuleInspector

root = Path.cwd()
modules = ModuleInspector.discoverModules(root, root / "orionis" / "introspection")
assert "orionis.introspection" in modules
assert "orionis.introspection.reflection" in modules
loaded = ModuleInspector.loadClass("pathlib", "Path")
assert loaded is Path
print(len(modules))
```

Validation: **Executed successfully** from the repository root on CPython 3.14.6.

### Detect imports through the AST

```python
from pathlib import Path
from orionis.introspection import ModuleInspector

source = Path("orionis/container/entities/invocation.py")
targets = {"orionis.introspection.callables.reflection"}
assert ModuleInspector.fileImportsAny(source, targets)
assert not ModuleInspector.fileImportsAny(source, {"package.that.is.not.imported"})
print(source.name)
```

Validation: **Executed successfully** from the repository root on CPython 3.14.6.

## Configuration

This module has no application configuration file, environment variables, service provider, facade, or external I/O settings. Its relevant operational constants are implementation bounds: dependency signatures use 1,024-entry LRU caches, discovery excludes `__pycache__` and `site-packages`, and recognized virtual-environment directory names are skipped when they contain `pyvenv.cfg`.

## Integration with Orionis

The container uses dependency signatures to resolve constructors and callable invocations without repeatedly inspecting them. Foundation discovers frozen configuration dataclasses. Console discovers command modules; database discovers migrations and seeders; queues load job classes; realtime reads handler metadata. These consumers import concrete utilities directly rather than resolving a service from the container.

Because inspection sits below the container, the package deliberately has no dependency on an application instance. It can be used in framework bootstrap code and focused tooling before Orionis boots.

## Errors and edge cases

- Each specialized wrapper rejects the wrong category: for example, concrete reflection rejects abstract, builtin, generic, protocol, and typing classes.
- `ReflectionInstance` rejects class objects, builtin/ABC instances, and instances whose class is defined in `__main__`.
- `ReflectionCallable` accepts Python functions, bound methods, lambdas, and callable objects exposing `__code__`; other callables can be rejected.
- Source and file lookup can raise `AttributeError`, `TypeError`, or underlying inspection errors for generated, interactive, or built-in objects.
- Unknown methods/properties raise `AttributeError`; invalid mutation names and non-callable methods raise validation errors.
- Required builtin annotations such as `int` remain unresolved by design; defaults make a parameter resolved from the default's concrete type.
- Forward references are resolved when possible. Unavailable names remain conservative metadata instead of being imported speculatively.
- `discoverModules` raises when the target is outside the base. AST checks return `False` for absent, invalid, or undecodable files.
- Module discovery and frozen-dataclass discovery import code where documented; do not run them on untrusted packages.

## Performance and concurrency

Class/member scans are single-pass and cached per wrapper. Inspect and dependency signatures are memoized, and module/class loading uses Python's import cache plus an Orionis class cache. Reuse wrappers in hot paths and call `clearCache()` only after intentional mutation.

The caches are process-local. Reads are suitable for normal concurrent application use under Python's runtime guarantees, but reflected object mutation and cache clearing are not transactional. Do not mutate a shared class/module while other threads or tasks inspect or invoke it. Discovery walks the filesystem synchronously and belongs in bootstrap or tooling, not request hot paths.

## Compatibility

Orionis declares Python 3.14+. Reflection depends on CPython/Python inspection behavior, including descriptors, `inspect.signature`, annotation resolution, name mangling, and import metadata. Objects implemented by extensions, dynamically generated functions, frozen applications, and alternative runtimes may not expose source or file information even when other reflection methods work.

## Verification notes

Validation used CPython 3.14.6. All package exports, contracts, specialized wrappers, member classifiers, dependency entities/resolution, module discovery/loading, caches, and framework consumers were inspected. The **1,022** test methods under `tests/introspection` passed through the Orionis runner. Five standalone programs executed successfully, and every bilingual code block was compiled and compared byte-for-byte.
