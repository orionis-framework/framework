import dataclasses
from orionis.support.entities.base import BaseEntity
from orionis.test import TestCase
from orionis.test.entities.result import TestResult
from orionis.test.enums.status import TestStatus

# Complete catalogue of fields declared by the entity.
_EXPECTED_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "status",
    "execution_time",
    "error_message",
    "traceback",
    "class_name",
    "method",
    "module",
    "file_path",
    "doc_string",
    "exception",
    "line_no",
    "source_code",
)

# Fields that must be supplied explicitly at construction time.
_REQUIRED_FIELDS: frozenset[str] = frozenset({
    "id",
    "name",
    "status",
    "execution_time",
})

def _make_result(**overrides: object) -> TestResult:
    """Build a TestResult supplying only the required fields by default."""
    values: dict[str, object] = {
        "id": 1,
        "name": "tests.sample.TestSample.testSample",
        "status": TestStatus.PASSED,
        "execution_time": 0.001,
    }
    values.update(overrides)
    return TestResult(**values)  # type: ignore[arg-type]

class TestTestResultDefinition(TestCase):

    def testExtendsBaseEntity(self) -> None:
        """
        Confirm the entity inherits the shared serialisation mixin.

        Validates that TestResult exposes the framework-wide toDict and
        getFields helpers.
        """
        self.assertTrue(issubclass(TestResult, BaseEntity))

    def testIsADataclass(self) -> None:
        """
        Confirm the entity is declared as a dataclass.

        Validates that field metadata introspection is available for the
        reporting layer.
        """
        self.assertTrue(dataclasses.is_dataclass(TestResult))

    def testDeclaresExpectedFields(self) -> None:
        """
        Declare exactly the documented catalogue of fields.

        Validates the public shape of the entity consumed by the JSON
        cache writer.
        """
        names = tuple(field.name for field in dataclasses.fields(TestResult))
        self.assertEqual(names, _EXPECTED_FIELDS)

    def testEveryFieldDocumentsItself(self) -> None:
        """
        Attach a description to every declared field.

        Validates that metadata introspection always yields a human
        readable explanation for documentation tooling.
        """
        for field in dataclasses.fields(TestResult):
            self.assertIn("description", field.metadata)

    def testOptionalFieldsDeclareNoneDefault(self) -> None:
        """
        Default every optional field to None.

        Validates that a result can be built from the required fields
        alone, without leaking sentinel values.
        """
        for field in dataclasses.fields(TestResult):
            if field.name not in _REQUIRED_FIELDS:
                self.assertIsNone(field.default)

class TestTestResultConstruction(TestCase):

    def testRequiredFieldsAreSufficient(self) -> None:
        """
        Build an instance from the required fields alone.

        Validates that identifier, name, status and execution time are
        the only mandatory inputs.
        """
        self.assertIsInstance(_make_result(), TestResult)

    def testMissingRequiredFieldRaisesTypeError(self) -> None:
        """
        Raise TypeError when a mandatory field is omitted.

        Validates that partially built results cannot reach the
        reporting layer.
        """
        with self.assertRaises(TypeError):
            TestResult(  # type: ignore[call-arg]
                id=1,
                name="test",
                status=TestStatus.PASSED,
            )

    def testPositionalArgumentsAreRejected(self) -> None:
        """
        Raise TypeError when fields are supplied positionally.

        Validates the keyword-only contract that keeps call sites
        readable and order independent.
        """
        with self.assertRaises(TypeError):
            TestResult(1, "test", TestStatus.PASSED, 0.1)  # type: ignore[misc]

    def testRequiredValuesAreStored(self) -> None:
        """
        Store every required value exactly as provided.

        Validates that no coercion is applied to the mandatory inputs.
        """
        result = _make_result(id=42, name="alpha", execution_time=1.25)
        self.assertEqual(
            (result.id, result.name, result.execution_time),
            (42, "alpha", 1.25),
        )

    def testStatusIsStored(self) -> None:
        """
        Store the status member supplied at construction time.

        Validates that the reported outcome is preserved verbatim.
        """
        result = _make_result(status=TestStatus.FAILED)
        self.assertEqual(result.status, TestStatus.FAILED)

    def testEveryStatusIsAccepted(self) -> None:
        """
        Accept each member of the status enumeration.

        Validates that the entity can represent the four documented
        outcomes.
        """
        for status in TestStatus:
            self.assertEqual(_make_result(status=status).status, status)

    def testIdentifierAcceptsArbitraryTypes(self) -> None:
        """
        Accept any object as the result identifier.

        Validates the permissive annotation used to store the memory
        address of the originating test instance.
        """
        for identifier in ("uuid-abc", 99, object()):
            self.assertIs(_make_result(id=identifier).id, identifier)

    def testOptionalFieldsDefaultToNone(self) -> None:
        """
        Leave every optional attribute unset when not provided.

        Validates that omitted diagnostics are reported as None rather
        than empty placeholders.
        """
        result = _make_result()
        self.assertEqual(
            [
                result.error_message,
                result.traceback,
                result.class_name,
                result.method,
                result.module,
                result.file_path,
                result.doc_string,
                result.exception,
                result.line_no,
                result.source_code,
            ],
            [None] * 10,
        )

    def testOptionalFieldsStoreProvidedValues(self) -> None:
        """
        Store every optional diagnostic value supplied explicitly.

        Validates that failure metadata survives construction untouched.
        """
        source = [(10, "    self.fail()"), (11, "")]
        result = _make_result(
            error_message="assertion failed",
            traceback=["Traceback (most recent call last)\n"],
            class_name="TestSample",
            method="testSample",
            module="tests.sample",
            file_path="/workspace/tests/sample.py",
            doc_string="Sample docstring.",
            exception="AssertionError",
            line_no=42,
            source_code=source,
        )
        self.assertEqual(
            [
                result.error_message,
                result.class_name,
                result.method,
                result.module,
                result.file_path,
                result.doc_string,
                result.exception,
                result.line_no,
                result.source_code,
            ],
            [
                "assertion failed",
                "TestSample",
                "testSample",
                "tests.sample",
                "/workspace/tests/sample.py",
                "Sample docstring.",
                "AssertionError",
                42,
                source,
            ],
        )

    def testDiagnosticsDeclareTheStoredShapes(self) -> None:
        """
        Declare the diagnostic fields with the shapes actually stored.

        Validates that the traceback holds formatted lines and that the
        exception holds the raised class name.
        """
        declared = {
            field.name: str(field.type)
            for field in dataclasses.fields(TestResult)
        }
        self.assertEqual(declared["traceback"], "list[str] | None")
        self.assertEqual(declared["exception"], "str | None")

    def testTracebackStoresFormattedLines(self) -> None:
        """
        Store the traceback as the list of formatted lines.

        Validates the payload produced by the result processor for a
        failed test.
        """
        lines = ["Traceback (most recent call last)\n", "AssertionError\n"]
        self.assertEqual(_make_result(traceback=lines).traceback, lines)

class TestTestResultImmutability(TestCase):

    def testAttributeAssignmentIsRejected(self) -> None:
        """
        Raise FrozenInstanceError when an attribute is reassigned.

        Validates that a recorded outcome can never be rewritten after
        the fact.
        """
        result = _make_result()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.name = "modified"  # type: ignore[misc]

    def testAttributeDeletionIsRejected(self) -> None:
        """
        Raise FrozenInstanceError when an attribute is deleted.

        Validates that the frozen contract also blocks removal of
        recorded diagnostics.
        """
        result = _make_result()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            del result.name  # type: ignore[misc]

    def testIdenticalResultsCompareEqual(self) -> None:
        """
        Compare two results with identical fields as equal.

        Validates the generated equality used when de-duplicating
        reports.
        """
        self.assertEqual(_make_result(), _make_result())

    def testDifferentStatusesCompareUnequal(self) -> None:
        """
        Compare two results with different statuses as unequal.

        Validates that the outcome participates in structural equality.
        """
        self.assertNotEqual(
            _make_result(status=TestStatus.PASSED),
            _make_result(status=TestStatus.FAILED),
        )

    def testResultIsHashable(self) -> None:
        """
        Hash a frozen result without raising an error.

        Validates that results can be stored in sets or used as
        dictionary keys.
        """
        self.assertIsInstance(hash(_make_result()), int)

class TestTestResultSerialisation(TestCase):

    def testToDictExposesEveryField(self) -> None:
        """
        Export every declared field through toDict.

        Validates the payload written to the JSON results cache.
        """
        self.assertEqual(tuple(_make_result().toDict()), _EXPECTED_FIELDS)

    def testToDictConvertsStatusToPlainValue(self) -> None:
        """
        Serialise the status as its plain string value.

        Validates that the exported payload stays JSON friendly.
        """
        exported = _make_result(status=TestStatus.ERRORED).toDict()
        self.assertEqual(exported["status"], "ERRORED")

    def testToDictPreservesOptionalValues(self) -> None:
        """
        Export optional diagnostics with their stored values.

        Validates that failure details survive the dictionary
        conversion.
        """
        exported = _make_result(error_message="boom", line_no=7).toDict()
        self.assertEqual((exported["error_message"], exported["line_no"]), ("boom", 7))

    def testGetFieldsDescribesEveryField(self) -> None:
        """
        Describe every declared field through getFields.

        Validates the introspection helper used by documentation
        generators.
        """
        described = tuple(entry["name"] for entry in _make_result().getFields())
        self.assertEqual(described, _EXPECTED_FIELDS)

    def testGetFieldsExposesTypesAndMetadata(self) -> None:
        """
        Expose the type names and metadata of a described field.

        Validates that each entry carries the documentation attached to
        the dataclass field.
        """
        described = {entry["name"]: entry for entry in _make_result().getFields()}
        entry = described["error_message"]
        self.assertIn("str", entry["types"])
        self.assertIn("description", entry["metadata"])
