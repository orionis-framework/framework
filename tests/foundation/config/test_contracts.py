import ast
import re
import tempfile
from dataclasses import asdict, fields
from pathlib import Path
from typing import get_args, get_type_hints

from orionis.foundation.config.app import App
from orionis.foundation.config.startup import Configuration
from orionis.foundation.core_config import CORE_CONFIG
from tests.foundation.config.support import (
    ConfigurationTestCase,
    configuration_classes,
)


class TestConfigurationContracts(ConfigurationTestCase):
    def testAllDefaultsAndSerializedConfigurationsConstruct(self) -> None:
        """Construct and round-trip every entity and application subclass."""
        for cls in configuration_classes(self.modules):
            with self.subTest(entity=cls.__module__):
                original = cls()
                self.assertEqual(asdict(cls(**asdict(original))), asdict(original))

    def testEveryFieldRejectsAnUnsupportedObject(self) -> None:
        """Exercise the initialization guards of every declared field."""
        for cls in configuration_classes(self.modules):
            for field in fields(cls):
                with (
                    self.subTest(entity=cls.__name__, field=field.name),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    cls(**{field.name: object()})

    def testNullabilityMatchesDeclaredTypes(self) -> None:
        """Distinguish nullable options from required configuration values."""
        for cls in configuration_classes(self.modules):
            annotations = get_type_hints(cls)
            for field in fields(cls):
                with self.subTest(entity=cls.__name__, field=field.name):
                    if type(None) in get_args(annotations[field.name]):
                        cls(**{field.name: None})
                    else:
                        with self.assertRaises((TypeError, ValueError)):
                            cls(**{field.name: None})

    def testBootstrapDefaultsPreserveExplicitApplicationChoices(self) -> None:
        """Compare the application templates with their framework bases."""
        overrides = {
            "BootstrapAppAuth": ("session", "redirect_to", "/login"),
            "BootstrapCache": ("prefix", None, ""),
        }
        self.environment.values["APP_KEY"] = bytes(range(32))
        for cls in configuration_classes(self.modules):
            if not cls.__module__.startswith("config."):
                continue
            with self.subTest(entity=cls.__name__):
                expected = asdict(cls.__bases__[0]())
                if cls.__name__ in overrides:
                    section, field, value = overrides[cls.__name__]
                    if field is None:
                        expected[section] = value
                    else:
                        expected[section][field] = value
                self.assertEqual(asdict(cls()), expected)

    def testStartupContainsEveryCoreConfigurationSection(self) -> None:
        """Include hashing, scheduler and view in nested startup validation."""
        self.assertEqual(set(Configuration().toDict()), set(CORE_CONFIG))
        configured = Configuration(
            hashing={"bcrypt": {"rounds": 4}},
            scheduler={"jitter": 0, "misfire_grace_time": None},
            view={"cache_size": 0, "autoescape": False},
        )
        self.assertEqual(configured.hashing.bcrypt.rounds, 4)
        self.assertIsNone(configured.scheduler.misfire_grace_time)
        self.assertFalse(configured.view.autoescape)
        with self.assertRaises(ValueError):
            Configuration(hashing={"bcrypt": {"rounds": 32}})

    def testPublicExportsRemainImportable(self) -> None:
        """Import the whole configuration tree and verify its declared exports."""
        for module in self.modules:
            for name in getattr(module, "__all__", ()):
                with self.subTest(module=module.__name__, export=name):
                    self.assertTrue(hasattr(module, name))

    def testConfigurationMethodsFollowProjectConventions(self) -> None:
        """Protect camelCase methods and Python protocol method names."""
        for root in (Path("config"), Path("orionis/foundation/config")):
            for path in root.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.ClassDef):
                        continue
                    for method in node.body:
                        if not isinstance(
                            method,
                            (ast.FunctionDef, ast.AsyncFunctionDef),
                        ):
                            continue
                        with self.subTest(path=str(path), method=method.name):
                            special = re.fullmatch(r"__[a-z_]+__", method.name)
                            camel = re.fullmatch(
                                r"_{0,2}[a-z][a-zA-Z0-9]*",
                                method.name,
                            )
                            self.assertTrue(special or camel)

    def testNoConfigurationUsesRuntimeAssertions(self) -> None:
        """Keep validation active when Python runs with optimization enabled."""
        for module in self.modules:
            if module.__file__ is None:
                continue
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
            self.assertFalse(
                any(isinstance(node, ast.Assert) for node in ast.walk(tree)),
            )

    def testInvalidAppDoesNotGenerateOrPersistAKey(self) -> None:
        """Validate all application fields before generating a missing key."""
        for options in ({"maintenance": 1}, {"timezone": "Missing/Zone"}):
            with (
                self.subTest(options=options),
                self.assertRaises((TypeError, ValueError)),
            ):
                App(key=None, **options)
        self.assertEqual(self.environment.writes, [])

    def testEmptyRoutingFileDoesNotBlockConfigurationBoot(self) -> None:
        """Allow empty optional route files while rejecting non-routing code."""
        from orionis.foundation.application import Application

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "api.py"
            path.write_text("\n", encoding="utf-8")
            app = Application()
            resolve = app._Application__resolveAndValidateRoutingFiles
            self.assertEqual(
                resolve(str(path), {"orionis.support.facades.router"}),
                [path],
            )
            path.write_text("value = 1\n", encoding="utf-8")
            with self.assertRaises(TypeError):
                resolve(str(path), {"orionis.support.facades.router"})
