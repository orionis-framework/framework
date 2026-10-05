from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from orionis.console.templates.stub import Stub
from orionis.test import TestCase

def _create_stub_at_barrier(
    output: Path,
    barrier: Barrier,
) -> str | FileExistsError:
    """
    Attempt to create the same generated file after both workers are ready.

    Parameters
    ----------
    output : Path
        Directory where both workers attempt to create the command.
    barrier : Barrier
        Synchronization point shared by the workers.

    Returns
    -------
    str | FileExistsError
        Generated file path or the collision raised by exclusive creation.
    """
    barrier.wait()
    try:
        return Stub("console_command", "sample", postfix="Command").create(output)
    except FileExistsError as error:
        return error

class TestStub(TestCase):
    """Verify console stub generation and validation behavior."""

    def testCreateWritesReplacedTemplate(self) -> None:
        """Write a template with all command placeholders replaced.

        Returns
        -------
        None
            Assertions verify the generated file content and filename.
        """
        replacements = {
            "signature_literal": repr("sample:run"),
            "description_literal": repr("Runs a sample command."),
        }

        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            Stub(
                "console_command",
                "sample",
                postfix="Command",
                replacements=replacements,
            ).create(
                output,
            )
            generated = output / "sample_command.py"

            self.assertTrue(generated.exists())
            content = generated.read_text(encoding="utf-8")
            self.assertIn("class SampleCommand", content)
            self.assertIn("signature: str = 'sample:run'", content)
            self.assertIn("description: str = 'Runs a sample command.'", content)

    def testClassNameIsReplacedByDefault(self) -> None:
        """Replace the compact class placeholder without explicit input.

        Returns
        -------
        None
            Assertions verify that the derived class name is written.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            Stub("service", "sample_command").create(output)
            content = (output / "sample_command.py").read_text(encoding="utf-8")

            self.assertIn("class SampleCommand", content)

    def testSpacedClassNamePlaceholderIsReplaced(self) -> None:
        """Replace the spaced class placeholder with the derived class name.

        Returns
        -------
        None
            Assertions verify both placeholder forms use the compiled name.
        """
        stub = Stub("service", "sample_command")
        stub._Stub__compileFilenameAndClassname()

        content = stub._Stub__replaceTemplateContent(
            "class {{ class_name }}: {{class_name}}",
        )

        self.assertEqual(content, "class SampleCommand: SampleCommand")

    def testCreateAppendsPostfixToFilename(self) -> None:
        """Append a normalized postfix to the generated filename.

        Returns
        -------
        None
            Assertions verify the output filename.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            stub = Stub("service", "sample", postfix="Command")
            stub._Stub__compileFilenameAndClassname()
            stub.create(output)

            self.assertTrue((output / "sample_command.py").exists())
            self.assertEqual(stub._classname, "SampleCommand")

    def testCompileNameIsStableAcrossRepeatedCalls(self) -> None:
        """Keep the generated class name stable across repeated compilation.

        Returns
        -------
        None
            Assertions verify that a lowercase postfix appears only once.
        """
        stub = Stub("service", "sample", postfix="command")

        stub._Stub__compileFilenameAndClassname()
        stub._Stub__compileFilenameAndClassname()

        self.assertEqual(stub._classname, "SampleCommand")
        self.assertEqual(stub._filename, "sample_command")

    def testCreatePreservesCamelCaseWords(self) -> None:
        """Preserve case within class name components.

        Returns
        -------
        None
            Assertions verify the generated class and source file.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            Stub("service", "HTTP_service", postfix="service").create(output)

            content = (output / "http_service.py").read_text(encoding="utf-8")
            self.assertIn("class HTTPService", content)

    def testCreateRejectsInvalidFilename(self) -> None:
        """Reject class names that cannot produce valid filenames.

        Returns
        -------
        None
            Assertions verify that invalid input raises ``ValueError``.
        """
        with TemporaryDirectory() as temporary:
            message = "Invalid filename 'invalid-name' format."
            with self.assertRaisesRegex(ValueError, message):
                Stub("service", "invalid-name").create(Path(temporary))

    def testCreateDoesNotOverwriteAnExistingFile(self) -> None:
        """Reject a generated path that already exists.

        Returns
        -------
        None
            Verifies the existing file is preserved after the rejected write.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            target = output / "sample_command.py"
            target.write_text("original", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                Stub("service", "sample_command").create(output)

            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def testConcurrentCreatesAllowOnlyOneWriter(self) -> None:
        """Allow only one of two simultaneous writers to create the file.

        Returns
        -------
        None
            Assertions verify the winner and the rejected conflicting write.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            barrier = Barrier(2)
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(_create_stub_at_barrier, output, barrier)
                    for _ in range(2)
                ]
                results = [future.result() for future in futures]

            created = [result for result in results if isinstance(result, str)]
            rejected = [
                result for result in results
                if isinstance(result, FileExistsError)
            ]
            self.assertEqual(len(created), 1)
            self.assertEqual(len(rejected), 1)
            self.assertTrue((output / "sample_command.py").is_file())

    def testCreateReportsMissingTemplate(self) -> None:
        """Report a missing template without probing the path first.

        Returns
        -------
        None
            Assertions verify that missing templates raise ``FileNotFoundError``.
        """
        with TemporaryDirectory() as temporary, self.assertRaises(
            FileNotFoundError,
        ):
            Stub("missing", "sample").create(Path(temporary))

    def testCreateRejectsTemplateTraversal(self) -> None:
        """Reject template names containing path separators.

        Returns
        -------
        None
            Assertions verify that the stub stays within its package.
        """
        with TemporaryDirectory() as temporary, self.assertRaises(ValueError):
            Stub("../service", "sample").create(Path(temporary))

    def testCreateSupportsNestedNamesAndStripsSourceExtension(self) -> None:
        """Create nested modules while deriving the class from the file stem.

        Returns
        -------
        None
            Assertions verify the directory, file extension, and class name.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            generated = Stub("service", "nested/example.py").create(
                output,
                relative_to=output,
            )
            target = output / "nested" / "example.py"

            self.assertEqual(generated, str(Path("nested") / "example.py"))
            self.assertTrue(target.is_file())
            self.assertFalse((output / "nested" / "example.py.py").exists())
            self.assertIn("class Example", target.read_text(encoding="utf-8"))

    def testCreateResolvesTheBaseBeforeMakingThePathRelative(self) -> None:
        """Resolve an equivalent base path before computing the generated path.

        Returns
        -------
        None
            Assertions verify that base path aliases do not reject valid files.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "alias").mkdir()
            generated = Stub("service", "example").create(
                root / "app",
                relative_to=root / "alias" / "..",
            )

            self.assertEqual(generated, str(Path("app") / "example.py"))
            self.assertTrue((root / generated).is_file())

    def testCreateResolvesTheDestinationBeforeMakingThePathRelative(self) -> None:
        """Resolve an equivalent destination before computing its relative path.

        Returns
        -------
        None
            Assertions verify the returned path contains no unresolved aliases.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "alias").mkdir()
            generated = Stub("service", "example").create(
                root / "alias" / ".." / "app",
                relative_to=root,
            )

            self.assertEqual(generated, str(Path("app") / "example.py"))
            self.assertTrue((root / generated).is_file())

    def testCreateUsesRequestedTemplateExtension(self) -> None:
        """Use the caller-selected extension after removing input suffixes.

        Returns
        -------
        None
            Assertions verify a ``.pyi`` output from a ``.py`` input name.
        """
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            Stub("facade_interface", "nested/example.py").create(
                output,
                extension="pyi",
            )

            self.assertTrue((output / "nested" / "example.pyi").is_file())
            self.assertFalse((output / "nested" / "example.py").exists())

    def testCreateRejectsDirectoryTraversal(self) -> None:
        """Reject names that could write outside the configured directory.

        Returns
        -------
        None
            Assertions verify parent traversal is rejected.
        """
        with TemporaryDirectory() as temporary, self.assertRaises(ValueError):
            Stub("service", "../outside").create(Path(temporary))
