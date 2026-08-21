import re
import sys
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from orionis.metadata import framework
from orionis.test import TestCase

# Public constants that make up the metadata surface of the module.
_PUBLIC_CONSTANTS: tuple[str, ...] = (
    "API",
    "AUTHOR",
    "AUTHOR_EMAIL",
    "DESCRIPTION",
    "DOCS",
    "FRAMEWORK",
    "NAME",
    "PYTHON_REQUIRES",
    "SKELETON",
    "VERSION",
)

# Subset of constants holding an absolute URL.
_URL_CONSTANTS: tuple[str, ...] = ("API", "DOCS", "FRAMEWORK", "SKELETON")

# Project manifest that ships with the repository checkout.
_PYPROJECT: Path = Path(__file__).resolve().parents[2] / "pyproject.toml"

# Accepted shape for the released version: three numeric segments.
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

# Accepted shape for a contact email address.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Accepted shape for a module level constant name.
_CONSTANT_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def public_names() -> set[str]:
    """
    Collect the public attribute names declared by the metadata module.

    Returns
    -------
    set[str]
        Every name of ``orionis.metadata.framework`` that does not start
        with an underscore.
    """
    return {name for name in vars(framework) if not name.startswith("_")}


def read_project_table() -> dict[str, Any]:
    """
    Read the ``[project]`` table of the repository manifest.

    Returns
    -------
    dict[str, Any]
        Parsed contents of the ``[project]`` table.
    """
    with _PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["project"]


class TestFrameworkModuleSurface(TestCase):
    """Structural guarantees of the metadata module."""

    def testModuleExposesExactlyTheDocumentedConstants(self) -> None:
        """
        Expose only the documented metadata constants.

        Validates that no helper, import or intermediate value leaks into
        the public namespace of the module.
        """
        self.assertEqual(public_names(), set(_PUBLIC_CONSTANTS))

    def testEveryPublicNameIsAnUpperSnakeCaseConstant(self) -> None:
        """
        Name every public value as an upper snake case constant.

        Validates that the module keeps a constants-only surface.
        """
        for name in public_names():
            self.assertRegex(name, _CONSTANT_NAME_PATTERN)

    def testEveryConstantHoldsAnImmutableValue(self) -> None:
        """
        Store every constant in an immutable container.

        Validates that a consumer cannot mutate shared metadata in place.
        """
        for name in _PUBLIC_CONSTANTS:
            value = getattr(framework, name)
            self.assertIsInstance(value, (str, tuple), msg=name)

    def testNoConstantIsEmpty(self) -> None:
        """
        Provide a non-empty value for every constant.

        Validates that no placeholder is shipped as an empty string or an
        empty tuple.
        """
        for name in _PUBLIC_CONSTANTS:
            self.assertGreater(len(getattr(framework, name)), 0, msg=name)


class TestFrameworkIdentity(TestCase):
    """Distribution name and short description."""

    def testNameIsTheDistributionIdentifier(self) -> None:
        """
        Publish the distribution under the ``orionis`` identifier.

        Validates the name used by package indexes and by the API URL.
        """
        self.assertEqual(framework.NAME, "orionis")

    def testNameIsANormalisedImportableIdentifier(self) -> None:
        """
        Keep the distribution name normalised and importable.

        Validates that the name is trimmed, lowercase and usable as a
        Python identifier.
        """
        self.assertEqual(framework.NAME, framework.NAME.strip().lower())
        self.assertTrue(framework.NAME.isidentifier())

    def testDescriptionMentionsTheFrameworkName(self) -> None:
        """
        Reference the framework name inside the short description.

        Validates that the summary identifies the project it describes.
        """
        self.assertIn("Orionis", framework.DESCRIPTION)

    def testDescriptionIsASingleTrimmedLine(self) -> None:
        """
        Keep the description on a single trimmed line.

        Validates the shape required by package indexes, which render the
        summary as one line.
        """
        self.assertEqual(framework.DESCRIPTION, framework.DESCRIPTION.strip())
        self.assertNotIn("\n", framework.DESCRIPTION)

    def testDescriptionIsLongEnoughToBeInformative(self) -> None:
        """
        Describe the project with more than a couple of words.

        Validates that the summary is not degraded to a placeholder.
        """
        self.assertGreater(len(framework.DESCRIPTION), 20)


class TestFrameworkVersion(TestCase):
    """Released version string."""

    def testVersionUsesThreeNumericSegments(self) -> None:
        """
        Format the version as three dot-separated numeric segments.

        Validates the release shape consumed by packaging tools.
        """
        self.assertRegex(framework.VERSION, _VERSION_PATTERN)

    def testVersionSegmentsCarryNoRedundantLeadingZeros(self) -> None:
        """
        Write every version segment in its canonical numeric form.

        Validates that segments such as ``01`` never reach a release.
        """
        for segment in framework.VERSION.split("."):
            self.assertEqual(segment, str(int(segment)), msg=segment)

    def testVersionIsComparableAsATupleOfIntegers(self) -> None:
        """
        Parse the version into an ordered tuple of integers.

        Validates that release tooling can compare two published
        versions.
        """
        parsed = tuple(int(segment) for segment in framework.VERSION.split("."))
        self.assertGreater(parsed, (0, 0, 0))

    def testVersionCarriesNoSurroundingWhitespace(self) -> None:
        """
        Keep the version free of surrounding whitespace.

        Validates that the value can be embedded verbatim in output.
        """
        self.assertEqual(framework.VERSION, framework.VERSION.strip())


class TestFrameworkAuthor(TestCase):
    """Maintainer contact details."""

    def testAuthorHoldsAFullName(self) -> None:
        """
        Record the maintainer with at least a first and a last name.

        Validates that the value is a person name and not a placeholder.
        """
        self.assertGreaterEqual(len(framework.AUTHOR.split()), 2)

    def testAuthorCarriesNoSurroundingWhitespace(self) -> None:
        """
        Keep the maintainer name free of surrounding whitespace.

        Validates that the value can be embedded verbatim in output.
        """
        self.assertEqual(framework.AUTHOR, framework.AUTHOR.strip())

    def testAuthorEmailMatchesAnAddressShape(self) -> None:
        """
        Record the contact email as a routable address.

        Validates the ``local@domain.tld`` shape expected by package
        indexes.
        """
        self.assertRegex(framework.AUTHOR_EMAIL, _EMAIL_PATTERN)

    def testAuthorEmailHasASingleAtSeparator(self) -> None:
        """
        Separate local part and domain with exactly one at sign.

        Validates that the address cannot be split ambiguously.
        """
        self.assertEqual(framework.AUTHOR_EMAIL.count("@"), 1)


class TestFrameworkUrls(TestCase):
    """Absolute URLs advertised by the framework."""

    def testEveryUrlUsesTheHttpsScheme(self) -> None:
        """
        Advertise every URL over HTTPS.

        Validates that no documented resource is served over plain HTTP.
        """
        for name in _URL_CONSTANTS:
            parsed = urlparse(getattr(framework, name))
            self.assertEqual(parsed.scheme, "https", msg=name)

    def testEveryUrlDeclaresAQualifiedHost(self) -> None:
        """
        Point every URL at a fully qualified host.

        Validates that the network location carries a domain separator.
        """
        for name in _URL_CONSTANTS:
            parsed = urlparse(getattr(framework, name))
            self.assertIn(".", parsed.netloc, msg=name)

    def testEveryUrlIsFreeOfWhitespace(self) -> None:
        """
        Keep every URL free of whitespace.

        Validates that the values can be embedded verbatim in rendered
        output without escaping.
        """
        for name in _URL_CONSTANTS:
            value = getattr(framework, name)
            self.assertEqual(value, value.strip(), msg=name)
            self.assertNotIn(" ", value, msg=name)

    def testUrlsPointToDistinctResources(self) -> None:
        """
        Assign a distinct URL to each documented resource.

        Validates that no constant was copied over another by mistake.
        """
        urls = [getattr(framework, name) for name in _URL_CONSTANTS]
        self.assertEqual(len(set(urls)), len(urls))

    def testRepositoryUrlsBelongToTheOrionisOrganisation(self) -> None:
        """
        Host both repositories under the Orionis organisation.

        Validates the framework and skeleton repository locations.
        """
        for name in ("FRAMEWORK", "SKELETON"):
            self.assertIn("orionis", getattr(framework, name).lower(), msg=name)

    def testApiUrlTargetsThePypiJsonEndpointOfThePackage(self) -> None:
        """
        Derive the API URL from the distribution name.

        Validates that renaming the distribution without updating the
        endpoint is reported as a failure.
        """
        self.assertEqual(
            framework.API,
            f"https://pypi.org/pypi/{framework.NAME}/json",
        )


class TestFrameworkPythonRequires(TestCase):
    """Minimum interpreter version required by the framework."""

    def testPythonRequiresIsATupleOfIntegers(self) -> None:
        """
        Express the requirement as a tuple of integers.

        Validates the element type required to compare the value against
        ``sys.version_info``.
        """
        self.assertIsInstance(framework.PYTHON_REQUIRES, tuple)
        for part in framework.PYTHON_REQUIRES:
            self.assertIsInstance(part, int)

    def testPythonRequiresExposesMajorAndMinorSegments(self) -> None:
        """
        Expose exactly the major and minor segments.

        Validates the shape consumed by the ``about`` and ``serve``
        commands, which index the first two positions of the tuple.
        """
        self.assertEqual(len(framework.PYTHON_REQUIRES), 2)

    def testPythonRequiresIsComparableWithVersionInfo(self) -> None:
        """
        Compare the requirement against ``sys.version_info``.

        Validates the guard used by ``Application`` to reject unsupported
        interpreters.
        """
        self.assertIsInstance(sys.version_info >= framework.PYTHON_REQUIRES, bool)

    def testRunningInterpreterSatisfiesTheRequirement(self) -> None:
        """
        Run the suite on an interpreter that meets the requirement.

        Validates that the declared floor is not above the interpreter
        the framework is actually tested with.
        """
        segments = sys.version_info[: len(framework.PYTHON_REQUIRES)]
        self.assertGreaterEqual(segments, framework.PYTHON_REQUIRES)

    def testPythonRequiresTargetsTheDeferredAnnotationsRelease(self) -> None:
        """
        Require the release that ships deferred annotation evaluation.

        Validates that the floor stays at Python 3.14, the version whose
        PEP 649 support the schema metaclass depends on.
        """
        self.assertEqual(framework.PYTHON_REQUIRES, (3, 14))


class TestFrameworkProjectManifest(TestCase):
    """Consistency between the metadata module and ``pyproject.toml``."""

    project: dict[str, Any]

    def setUp(self) -> None:
        """
        Load the ``[project]`` table shipped with the repository.

        The manifest is absent when the package is installed from a built
        distribution, in which case every test of the class is skipped.
        """
        if not _PYPROJECT.is_file():
            self.skipTest("pyproject.toml is not available in this installation")
        self.project = read_project_table()

    def testVersionMatchesTheProjectManifest(self) -> None:
        """
        Publish the same version in the module and in the manifest.

        Validates that a release bump updates both declarations.
        """
        self.assertEqual(self.project["version"], framework.VERSION)

    def testNameAndDescriptionMatchTheProjectManifest(self) -> None:
        """
        Publish the same name and summary in both declarations.

        Validates that the packaged distribution and the runtime metadata
        never drift apart.
        """
        self.assertEqual(self.project["name"], framework.NAME)
        self.assertEqual(self.project["description"], framework.DESCRIPTION)

    def testAuthorMatchesTheProjectManifest(self) -> None:
        """
        Declare the same maintainer contact in both declarations.

        Validates the author entry rendered by package indexes.
        """
        author = self.project["authors"][0]
        self.assertEqual(author["name"], framework.AUTHOR)
        self.assertEqual(author["email"], framework.AUTHOR_EMAIL)

    def testPythonRequiresMatchesTheProjectManifest(self) -> None:
        """
        Derive the manifest requirement from the same version floor.

        Validates that installers and the runtime guard agree on the
        minimum supported interpreter.
        """
        expected = ">=" + ".".join(str(part) for part in framework.PYTHON_REQUIRES)
        self.assertEqual(self.project["requires-python"], expected)

    def testUrlsMatchTheProjectManifest(self) -> None:
        """
        Advertise the same repository and documentation URLs.

        Validates the ``[project.urls]`` entries against the constants.
        """
        urls = self.project["urls"]
        self.assertEqual(urls["Homepage"], framework.FRAMEWORK)
        self.assertEqual(urls["Repository"], framework.FRAMEWORK)
        self.assertEqual(urls["Documentation"], framework.DOCS)
