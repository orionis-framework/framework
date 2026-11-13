# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve ORM declaration contracts without connecting to a database."""

import asyncio
import inspect
import subprocess
import sys
from collections.abc import Callable
from typing import Any, get_type_hints

from orionis.orm.collections.paginator import Paginator
from orionis.orm.schema import types
from orionis.orm.schema.column import definition
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.constraints import (
    CompositeForeignKey,
    TableIndex,
    UniqueConstraint,
)
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import LargeBinary, Numeric, StrictDecimal, String
from orionis.orm.schema.types.column_type import ColumnType
from orionis.support.types.collection import Collection
from orionis.test import TestCase


class TestSchemaRegressions(TestCase):
    """Keep declaration annotations executable and numeric options unambiguous."""

    def testPublicAnnotationsResolveToConcreteMetadataTypes(self) -> None:
        """Resolve constructors, dataclass fields and collection properties.

        Returns
        -------
        None
            No return value.
        """
        expectations = (
            (ColumnDefinition.__init__, "column_type", ColumnType),
            (ColumnOptions, "item_type", ColumnDefinition | None),
            (ColumnOptions.__init__, "item_type", ColumnDefinition | None),
            (ColumnOptions, "comparator", Callable[[object, object], bool] | None),
            (TableDefinition, "columns", dict[str, ColumnDefinition]),
            (TableDefinition.__init__, "columns", dict[str, ColumnDefinition]),
            (TableDefinition, "foreign_keys", tuple[CompositeForeignKey, ...]),
            (TableDefinition, "indexes", tuple[TableIndex, ...]),
            (TableDefinition, "unique_constraints", tuple[UniqueConstraint, ...]),
            (Paginator.__init__, "items", Collection),
            (Paginator.items.fget, "return", Collection),
            (definition, "_OPTION_GETTER", Callable[[ColumnOptions], tuple[Any, ...]]),
        )
        for target, name, expected in expectations:
            with self.subTest(target=target, annotation=name):
                actual = get_type_hints(target)[name]
                self.assertEqual(actual, expected)
        for name in types.__all__:
            column_class = getattr(types, name)
            if inspect.isclass(column_class) and issubclass(
                column_class,
                ColumnDefinition,
            ):
                with self.subTest(column=name):
                    self.assertIs(
                        get_type_hints(column_class.__init__)["return"],
                        type(None),
                    )

    def testValidatedLengthsAndNumericShapesRejectBooleans(self) -> None:
        """Reject boolean values where declarations require integer magnitudes.

        Returns
        -------
        None
            No return value.
        """
        for column_class in (String, LargeBinary):
            with (
                self.subTest(column=column_class.__name__),
                self.assertRaises(ValueError),
            ):
                column_class(length=True)
        for column_class in (Numeric, StrictDecimal):
            for precision, scale in ((True, 0), (2, False), (2, True)):
                with (
                    self.subTest(
                        column=column_class.__name__,
                        precision=precision,
                        scale=scale,
                    ),
                    self.assertRaises(ValueError),
                ):
                    column_class(precision, scale)

    async def testMetadataImportsResolveInFreshProcesses(self) -> None:
        """Resolve mutually referenced metadata regardless of import order.

        Returns
        -------
        None
            No return value.
        """
        script = """
import importlib
import sys
from typing import get_type_hints
importlib.import_module(sys.argv[1])
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.table import TableDefinition
from orionis.orm.collections.paginator import Paginator
from orionis.support.types.collection import Collection
assert get_type_hints(ColumnOptions)['item_type'] == ColumnDefinition | None
assert get_type_hints(TableDefinition)['columns'] == dict[str, ColumnDefinition]
assert get_type_hints(Paginator.__init__)['items'] is Collection
"""
        for first in (
            "orionis.orm.schema.column.options",
            "orionis.orm.schema.column.definition",
            "orionis.orm.schema.table",
            "orionis.orm.collections.paginator",
        ):
            with self.subTest(first=first):
                result = await asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, "-B", "-c", script, first],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
