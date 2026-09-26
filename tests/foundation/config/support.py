import importlib
import pkgutil
from dataclasses import is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from orionis.test import TestCase

if TYPE_CHECKING:
    from types import ModuleType


def configuration_modules() -> list[ModuleType]:
    """Load every configuration module, including public package reexports."""
    package = importlib.import_module("orionis.foundation.config")
    modules = [package]
    modules.extend(
        importlib.import_module(info.name)
        for info in pkgutil.walk_packages(package.__path__, package.__name__ + ".")
    )
    modules.extend(
        importlib.import_module("config." + path.stem)
        for path in sorted(Path("config").glob("*.py"))
    )
    return modules


def configuration_classes(modules: list[ModuleType]) -> list[type]:
    """Collect concrete dataclasses once, excluding imported aliases."""
    return [
        value
        for module in modules
        for value in vars(module).values()
        if isinstance(value, type)
        and is_dataclass(value)
        and value.__module__ == module.__name__
    ]


class EnvironmentDouble:
    """Provide deterministic environment values without writing to .env."""

    __slots__ = ("values", "writes")

    def __init__(self) -> None:
        """Create independently controlled values for each test."""
        self.values: dict[str, object] = {}
        self.writes: list[tuple[str, object]] = []

    def get(self, key: str, default: object = None) -> object:
        """Return configured values, including explicit falsy values."""
        return self.values.get(key, default)

    def set(self, key: str, value: object) -> None:
        """Record a generated key without modifying process or disk state."""
        self.writes.append((key, value))


class ConfigurationTestCase(TestCase):
    """Isolate the environment consumed by all configuration factories."""

    def setUp(self) -> None:
        """Replace module environment references before each test."""
        self.modules = configuration_modules()
        self.environment = EnvironmentDouble()
        self.originals = []
        for module in self.modules:
            if hasattr(module, "Env"):
                self.originals.append((module, module.Env))
                module.Env = self.environment

    def tearDown(self) -> None:
        """Restore all references even after failed configuration validation."""
        for module, original in self.originals:
            module.Env = original
