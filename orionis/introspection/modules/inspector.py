from __future__ import annotations
import ast
import importlib
import os
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any

_EXCLUDED_DIRECTORIES = frozenset({"__pycache__", "site-packages"})
_VENV_DIRECTORIES = frozenset({".env", ".venv", "env", "venv"})

class ModuleInspector:

    # ruff: noqa: RUF012

    # Cache for resolved class objects keyed by fully-qualified name
    __cache_resolved_classes: dict[str, type] = {}

    @staticmethod
    def discoverModules(
        base_path: Path,
        target_path: Path,
    ) -> set[str]:
        """
        Discover Python modules in a directory tree.

        Traverse the target directory to find Python files and convert their
        paths to module notation. Exclude virtual environments and import caches.
        Collect each directory's modules with package initializers normalized
        to their package module names.

        Parameters
        ----------
        base_path : Path
            Root directory of the application.
        target_path : Path
            Directory to search for Python modules.

        Returns
        -------
        set of str
            Set of discovered module names in dot notation.

        Raises
        ------
        ValueError
            If the target directory is outside the base directory.
        """
        base = base_path.resolve()
        target = target_path.resolve()
        relative_target = target.relative_to(base)
        current = base
        for part in relative_target.parts:
            current /= part
            directory_name = part.casefold()
            if directory_name in _EXCLUDED_DIRECTORIES or (
                directory_name in _VENV_DIRECTORIES
                and (current / "pyvenv.cfg").is_file()
            ):
                return set()

        modules: set[str] = set()
        for directory, subdirectories, files in os.walk(target):
            # Prevent traversal into virtual environments and import caches.
            subdirectories[:] = [
                name for name in subdirectories
                if name.casefold() not in _EXCLUDED_DIRECTORIES
                and (
                    name.casefold() not in _VENV_DIRECTORIES
                    or not (Path(directory) / name / "pyvenv.cfg").is_file()
                )
            ]
            package = ".".join(Path(directory).relative_to(base).parts)
            ModuleInspector._collectDirectoryModules(package, files, modules)
        return modules

    @staticmethod
    def _collectDirectoryModules(
        package: str,
        files: list[str],
        modules: set[str],
    ) -> None:
        """
        Add Python module names from one discovered directory.

        Parameters
        ----------
        package : str
            Dotted package name relative to the application root.
        files : list[str]
            File names reported by the directory walk.
        modules : set[str]
            Destination set shared by the discovery traversal.

        Returns
        -------
        None
            Add modules in place, omitting a root-level package initializer.
        """
        for filename in files:
            if not filename.endswith(".py"):
                continue
            stem = filename[:-3]
            if stem != "__init__":
                modules.add(f"{package}.{stem}" if package else stem)
            elif package:
                modules.add(package)

    @classmethod
    def loadClass(
        cls: type,
        module_path: str | None = None,
        class_name: str | None = None,
        *,
        metadata: dict[str, str] | None = None,
    ) -> type:
        """
        Load and return a class object from a specified module.

        Import the given module and retrieve the class by name, using internal
        caches for efficiency. If not provided directly, module and class names
        can be extracted from the metadata dictionary.

        Parameters
        ----------
        cls : type
            Reference to the class for caching and method access.
        module_path : str or None
            Dotted path to the module (e.g., 'orionis.*.config.app.entities.app').
        class_name : str or None
            Name of the class to retrieve from the module.
        metadata : dict[str, str] or None, optional
            Optional dictionary containing 'module' and 'class' keys.

        Returns
        -------
        type
            The resolved class object.

        Raises
        ------
        ImportError
            If the module cannot be imported.
        AttributeError
            If the class does not exist in the module.
        TypeError
            If the resolved attribute is not a class.
        """
        # Extract module and class names from metadata if provided.
        # Accept both dict and MappingProxyType: freeze() converts nested
        # dicts to MappingProxyType, so both forms must be handled here.
        if (
            metadata is not None
            and isinstance(metadata, (dict, MappingProxyType))
            and metadata
            and module_path is None
            and class_name is None
        ):
            module_path = metadata.get("module")
            class_name = metadata.get("class")

        # Use the fully qualified class name as the cache key
        class_key: str = f"{module_path}.{class_name}"

        # Return the class previously resolved for this path.
        _resolved = cls.__cache_resolved_classes.get(class_key)
        if _resolved is not None:
            return _resolved

        # Retrieve from sys.modules if already imported, otherwise import now
        module = sys.modules.get(module_path)
        if module is None:
            try:
                module = importlib.import_module(module_path)
            except ImportError as e:
                error_msg = f"Could not import module '{module_path}': {e}"
                raise ImportError(error_msg) from e

        # Retrieve the class from the module
        try:
            klass = getattr(module, class_name)
        except AttributeError as e:
            error_msg = (
                f"Module '{module_path}' does not have a class "
                f"'{class_name}': {e}"
            )
            raise AttributeError(error_msg) from e

        # Ensure the resolved attribute is a class
        if not isinstance(klass, type):
            error_msg = (
                f"Attribute '{class_name}' in module '{module_path}' is not a "
                "class."
            )
            raise TypeError(error_msg)

        # Cache the resolved class for future calls
        cls.__cache_resolved_classes[class_key] = klass

        # Return the resolved class
        return klass

    @staticmethod
    def fileImportsAny(
        file_path: Path,
        target_modules: set[str],
    ) -> bool:
        """
        Determine if a file imports any target modules using AST analysis.

        Parameters
        ----------
        file_path : Path
            Path to the file to analyze.
        target_modules : set[str]
            Set of module names to check for imports.

        Returns
        -------
        bool
            True if the file imports any of the target modules, otherwise False.
        """
        # Return when there is no source or no import target to inspect.
        if not target_modules or not file_path.is_file():
            return False

        try:
            # Parse the file content into an AST tree
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            return False

        # Walk the AST and match import nodes directly without a nested helper
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in target_modules:
                return True
            if isinstance(node, ast.Import) and any(
                alias.name in target_modules for alias in node.names
            ):
                return True
        return False

    @staticmethod
    def discoverFrozenDataclasses(
        modules: set[str],
    ) -> set[tuple[str, str, str, type[Any]]]:
        """
        Discover frozen dataclasses in specified modules.

        Traverse the given set of module names, import each module, and inspect
        its attributes to find frozen dataclasses defined within the module.

        Parameters
        ----------
        modules : set[str]
            Set of module names to inspect.

        Returns
        -------
        set[tuple[str, str, str, type[Any]]]
            Set of tuples containing file name (without extension), module path,
            class name, and class type for each discovered frozen dataclass.

        Raises
        ------
        RuntimeError
            If a module cannot be imported.
        """
        dataclasses: set[tuple[str, str, str, type[Any]]] = set()
        for module_path in modules:
            try:
                # Inspect classes declared directly by the imported module.
                module = importlib.import_module(module_path)
                module_name = module.__name__
                file_name = Path(getattr(module, "__file__", None) or "unknown.py").stem
                for attr_name, attr in vars(module).items():
                    if not isinstance(attr, type) or attr.__module__ != module_name:
                        continue
                    params = vars(attr).get("__dataclass_params__")
                    if params is not None and params.frozen:
                        dataclasses.add(
                            (file_name, module_path, attr_name, attr),
                        )
            except Exception as e:
                error_msg = f"Failed to import module {module_path}: {e!s}"
                raise RuntimeError(error_msg) from e

        return dataclasses
