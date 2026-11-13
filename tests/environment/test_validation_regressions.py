# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect typed environment conversion boundaries and error privacy."""

import os
import tempfile
import traceback
from pathlib import Path
from typing import get_type_hints
from unittest.mock import patch

from orionis.environment.contracts.caster import IEnvironmentCaster
from orionis.environment.core.dot_env import DotEnv
from orionis.environment.dynamic.caster import EnvironmentCaster
from orionis.environment.enums.value_type import EnvironmentValueType
from orionis.environment.validators import ValidateTypes
from orionis.support.patterns.singleton.meta import _MISSING
from orionis.test import TestCase


class _TextValue(str):
    """Represent a supported string subclass."""

    __slots__ = ()


class _IntegerValue(int):
    """Represent a supported integer subclass."""


class TestEnvironmentValidationRegressions(TestCase):
    """Check serialization, parsing, and diagnostics against public contracts."""

    def testRejectsInvalidBooleansThroughBothParsers(self) -> None:
        """Reject unknown boolean spellings consistently."""
        for value in ("maybe", "", "truth"):
            entry = f"bool:{value}"
            for parser, arguments in (
                (EnvironmentCaster.parseTyped, (entry,)),
                (EnvironmentCaster(entry).get, ()),
            ):
                with (
                    self.subTest(value=value, parser=parser.__name__),
                    self.assertRaises(
                        ValueError,
                    ),
                ):
                    parser(*arguments)

    def testPreservesEmptyTextualPayloads(self) -> None:
        """Preserve empty string and Base64 payloads through both parsers."""
        for hint in ("str", "base64"):
            with self.subTest(hint=hint):
                entry = EnvironmentCaster("").to(hint)
                self.assertEqual(EnvironmentCaster.parseTyped(entry), "")
                self.assertEqual(EnvironmentCaster(entry).get(), "")

    def testRoundTripsBooleanIntegersAndBinaryBase64(self) -> None:
        """Serialize supported values into payloads the parser can read."""
        for value, hint, expected in (
            (True, "int", 1),
            (False, "int", 0),
            (b"\xff\xfe", "base64", b"\xff\xfe"),
            (b"\x00\xff", "base64", b"\x00\xff"),
        ):
            with self.subTest(value=value, hint=hint):
                stored = EnvironmentCaster(value).to(hint)
                self.assertEqual(EnvironmentCaster.parseTyped(stored), expected)

    def testExpandsHomeBeforeResolvingRelativePaths(self) -> None:
        """Resolve a home-relative path beneath the actual home directory."""
        expected = (Path.home() / "orionis-test-only").as_posix()
        stored = EnvironmentCaster("~/orionis-test-only").to("path")
        self.assertEqual(EnvironmentCaster.parseTyped(stored), expected)

    def testInfersSupportedBaseTypesForSubclasses(self) -> None:
        """Infer serializable canonical hints for supported subclasses."""
        for value, expected in (
            (_TextValue("value"), "str"),
            (_IntegerValue(4), "int"),
        ):
            with self.subTest(expected=expected):
                inferred = ValidateTypes(value=value)
                self.assertEqual(inferred, expected)
                self.assertEqual(
                    EnvironmentCaster.parseTyped(EnvironmentCaster(value).to(inferred)),
                    value,
                )

    def testResolvesCasterContractAnnotations(self) -> None:
        """Resolve runtime types used by the caster interface."""
        hints = get_type_hints(IEnvironmentCaster.to)
        self.assertEqual(hints["type_hint"], str | EnvironmentValueType)

    def testOmitsSensitiveValuesFromConversionTracebacks(self) -> None:
        """Keep synthetic secrets out of conversion errors and visible causes."""
        sensitive_value = "synthetic-secret-marker"
        for hint in ("int", "float", "bool", "list", "dict", "tuple", "set", "base64"):
            entry = f"{hint}:{sensitive_value}"
            for parser, arguments in (
                (EnvironmentCaster.parseTyped, (entry,)),
                (EnvironmentCaster(entry).get, ()),
            ):
                with self.subTest(hint=hint, parser=parser.__name__):
                    with self.assertRaises(ValueError) as caught:
                        parser(*arguments)
                    rendered = "".join(traceback.format_exception(caught.exception))
                    self.assertNotIn(sensitive_value, rendered)
        for hint in ("int", "float", "bool", "list", "dict", "tuple", "set"):
            with self.subTest(serialized_hint=hint):
                with self.assertRaises(ValueError) as caught:
                    EnvironmentCaster(sensitive_value).to(hint)
                rendered = "".join(traceback.format_exception(caught.exception))
                self.assertNotIn(sensitive_value, rendered)


class TestEnvironmentProcessValueLimits(TestCase):
    """Check native process limits before publishing persisted values."""

    def setUp(self) -> None:
        """Isolate the singleton, process values, and backing file."""
        super().setUp()
        self.addCleanup(
            type.__setattr__,
            DotEnv,
            "_singleton_instance",
            vars(DotEnv)["_singleton_instance"],
        )
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)
        self.enterContext(patch.dict(os.environ))
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self._path = directory / ".env"
        self._environment = DotEnv(str(self._path))

    def testValidatesPlatformLimitsBeforePersisting(self) -> None:
        """Keep file, cache, and process unchanged when native limits reject data."""
        key = "ORIONIS_LIMIT_VALUE"
        for value in ("x" * 32767, "\U0001f642" * 16384):
            with self.subTest(utf16_bytes=len(value.encode("utf-16-le"))):
                self._environment.set(key, "before")
                initial_file = self._path.read_text(encoding="utf-8")
                initial_cache = self._environment.all()
                if os.name == "nt":
                    with self.assertRaises(ValueError):
                        self._environment.set(key, value)
                    self.assertTrue(
                        self._path.read_text(encoding="utf-8") == initial_file,
                        "Rejected process data changed the persisted file.",
                    )
                    self.assertEqual(self._environment.all(), initial_cache)
                    self.assertEqual(os.environ[key], "before")
                else:
                    self.assertTrue(self._environment.set(key, value))
                    self.assertEqual(self._environment.get(key), value)
                    self.assertEqual(self._environment.all()[key], value)
        boundary_value = "x" * (32767 - len(key) - 1)
        self.assertTrue(self._environment.set(key, boundary_value))
        self.assertEqual(self._environment.get(key), boundary_value)
        if os.name == "nt":
            self.assertTrue(self._environment.set(key, "\ud800", only_os=True))
            self.assertEqual(os.environ[key], "\ud800")
        else:
            with self.assertRaises(UnicodeEncodeError):
                self._environment.set(key, "\ud800", only_os=True)
            self.assertEqual(os.environ[key], boundary_value)
        self.assertEqual(self._environment.all()[key], boundary_value)

    def testValidatesEveryReloadedValueBeforePublishing(self) -> None:
        """Preserve all process and cached values when a later entry is invalid."""
        key = "ORIONIS_LIMIT_VALUE"
        retained_key = "ORIONIS_LIMIT_RETAINED"
        for value in ("x" * 32767, "\U0001f642" * 16384):
            with self.subTest(utf16_bytes=len(value.encode("utf-16-le"))):
                self._environment.set(retained_key, "before")
                self._environment.set(key, "before")
                initial_cache = self._environment.all()
                self._path.write_text(
                    f"{retained_key}=after\n{key}={value}\n",
                    encoding="utf-8",
                )
                if os.name == "nt":
                    with self.assertRaises(RuntimeError):
                        self._environment.reload()
                    self.assertEqual(os.environ[retained_key], "before")
                    self.assertEqual(os.environ[key], "before")
                    self.assertEqual(self._environment.all(), initial_cache)
                else:
                    self.assertTrue(self._environment.reload())
                    self.assertEqual(os.environ[retained_key], "after")
                    self.assertEqual(os.environ[key], value)
                    self.assertEqual(self._environment.all()[key], value)
