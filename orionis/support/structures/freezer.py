from __future__ import annotations
from types import MappingProxyType
from typing import Any

# Module-level constants: single global-lookup per isinstance; most common types first.
# Avoids re-creating the type-tuple on every call and enables JIT specialization.
_CONTAINER_TYPES: tuple[type, ...] = (dict, list, tuple, MappingProxyType)
_MUTABLE_TYPES: tuple[type, ...] = (dict, list, tuple)

class FreezeThaw:

    # ruff: noqa: PLR0912, C901

    @staticmethod
    def _isContainer(obj: object) -> bool:
        """
        Determine if the object is a supported container type.

        Parameters
        ----------
        obj : object
            The object to check.

        Returns
        -------
        bool
            True if the object is a MappingProxyType, dict, list, or tuple;
            otherwise, False.
        """
        return isinstance(obj, _CONTAINER_TYPES)

    @staticmethod
    def thaw(obj: object) -> object: # NOSONAR
        """
        Recursively convert frozen containers to mutable equivalents.

        Parameters
        ----------
        obj : object
            The object to thaw. Can be a MappingProxyType, dict, list, or tuple.

        Returns
        -------
        object
            A fully mutable object with preserved references. Non-container
            objects are returned unchanged.
        """
        if not isinstance(obj, _CONTAINER_TYPES):
            return obj

        # Fast-path: empty containers require no traversal or cache
        if not obj:
            return {} if isinstance(obj, (MappingProxyType, dict)) else []

        obj_id = id(obj)
        # list is ~40% faster than deque for LIFO: contiguous memory, no block overhead
        stack: list[object] = [obj]
        cache: dict[int, Any] = {}
        # fixups tracks only container entries -> second pass O(N_containers)
        # instead of O(N_total), critical when most values are primitives
        fixups: list[tuple[Any, Any]] = []

        while stack:
            current = stack.pop()
            c_id = id(current)
            if c_id in cache:
                continue

            if isinstance(current, (MappingProxyType, dict)):
                new_obj: dict[Any, Any] = {}
                cache[c_id] = new_obj
                for k, v in current.items():
                    new_obj[k] = v
                    if isinstance(v, _CONTAINER_TYPES):
                        if id(v) not in cache:
                            stack.append(v)
                        fixups.append((new_obj, k))

            else:  # list or tuple
                # list(current) uses C-level list_extend: faster than [None]*n + fill
                new_seq: list[Any] = list(current)
                cache[c_id] = new_seq
                for i, v in enumerate(current):
                    if isinstance(v, _CONTAINER_TYPES):
                        if id(v) not in cache:
                            stack.append(v)
                        fixups.append((new_seq, i))

        # Local alias: avoids bound-method re-lookup on every loop iteration
        cache_get = cache.get
        for container, key in fixups:
            v = container[key]
            cached = cache_get(id(v))
            if cached is not None:
                container[key] = cached

        # root is already list or dict in cache; no additional O(N) copy needed
        return cache.get(obj_id, obj)

    @staticmethod
    def freeze(obj: object) -> object:  # NOSONAR
        """
        Convert mutable containers to immutable equivalents recursively.

        Parameters
        ----------
        obj : object
            The object to freeze. Can be a dict, list, or tuple.

        Returns
        -------
        object
            A fully immutable object with preserved references. Non-container
            objects or MappingProxyType are returned unchanged.
        """
        # MappingProxyType is already immutable; not in _MUTABLE_TYPES -> return as-is
        if not isinstance(obj, _MUTABLE_TYPES):
            return obj

        # Fast-path: empty containers require no traversal
        if not obj:
            return MappingProxyType({}) if isinstance(obj, dict) else ()

        obj_id = id(obj)
        stack: list[object] = [obj]
        cache: dict[int, Any] = {}

        while stack:
            current = stack.pop()
            c_id = id(current)
            if c_id in cache:
                continue

            if isinstance(current, dict):
                new_obj_d: dict[Any, Any] = {}
                cache[c_id] = new_obj_d
                for k, v in current.items():
                    new_obj_d[k] = v
                    # Push only mutable containers; MappingProxyType is already
                    # immutable and is left unchanged in the second pass
                    if isinstance(v, _MUTABLE_TYPES) and id(v) not in cache:
                        stack.append(v)

            else:  # list or tuple
                new_obj_l: list[Any] = list(current)
                cache[c_id] = new_obj_l
                stack.extend(
                    v for v in current
                    if isinstance(v, _MUTABLE_TYPES) and id(v) not in cache
                )

        # Bottom-up pass (leaves first) ensures correctness for nested structures.
        # DFS with LIFO inserts parents before children -> reversed() = leaves first.
        # When parent is processed, cache[id(child)] is already MappingProxyType/tuple.
        # list(cache.keys()) is required for reversed(); it also eliminates the original
        # list(cache.items()) snapshot, which was unnecessary: mutating existing-key
        # values does not invalidate dict iterators in Python 3.3+.
        for c_id in reversed(list(cache.keys())):
            val = cache[c_id]
            if isinstance(val, dict):
                for k, v in val.items():
                    if id(v) in cache:
                        val[k] = cache[id(v)]
                cache[c_id] = MappingProxyType(val)
            else:  # list
                for i, v in enumerate(val):
                    if id(v) in cache:
                        val[i] = cache[id(v)]
                cache[c_id] = tuple(val)

        return cache.get(obj_id, obj)
