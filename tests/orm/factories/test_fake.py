import ast
from itertools import pairwise
from pathlib import Path
import faker as faker_module
from faker import Faker
from faker.exceptions import UniquenessException
from faker.providers import BaseProvider
from database.factories.user_factory import UserFactory
from orionis.orm.factories import Fake, OptionalFake, UniqueFake
from orionis.orm.factories import fake as fake_module
from orionis.test import TestCase

_DEFAULT_POPULATIONS = frozenset(
    {
        "randomChoices",
        "randomElement",
        "randomElements",
        "randomSample",
    },
)

_TYPE_NAMES = {
    "Dict": "dict",
    "List": "list",
    "Set": "set",
    "Tuple": "tuple",
    "Type": "type",
}

def _stub_methods(path: Path, class_name: str) -> dict[str, list[ast.FunctionDef]]:
    """Parse overloaded declarations from a selected stub class.

    Parameters
    ----------
    path : Path
        Installed or framework stub file.
    class_name : str
        Class whose provider declarations are compared.

    Returns
    -------
    dict of str to list of ast.FunctionDef
        Method names mapped to all of their overload declarations.
    """
    module = ast.parse(path.read_text(encoding="utf-8"))
    selected = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    methods: dict[str, list[ast.FunctionDef]] = {}
    for node in selected.body:
        if isinstance(node, ast.FunctionDef):
            overloads = methods.get(node.name)
            if overloads is None:
                overloads = methods[node.name] = []
            overloads.append(node)
    return methods

def _union_members(annotation: ast.expr) -> list[ast.expr]:
    """Flatten equivalent optional and union annotations without evaluating them.

    Parameters
    ----------
    annotation : ast.expr
        Parsed annotation expression.

    Returns
    -------
    list of ast.expr
        Outer union members, preserving nested container annotations.
    """
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return [
            *_union_members(annotation.left),
            *_union_members(annotation.right),
        ]
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        if annotation.value.id == "Optional":
            return [*_union_members(annotation.slice), ast.Constant(None)]
        if annotation.value.id == "Union" and isinstance(
            annotation.slice,
            ast.Tuple,
        ):
            return [
                member
                for item in annotation.slice.elts
                for member in _union_members(item)
            ]
    return [annotation]

def _type_surface(annotation: ast.expr | None) -> str:
    """Normalize builtin names and union order for a symbolic type comparison.

    Parameters
    ----------
    annotation : ast.expr or None
        Parsed annotation, or an absent annotation.

    Returns
    -------
    str
        Comparable annotation without importing or evaluating provider types.
    """
    if annotation is None:
        return ""
    members = _union_members(annotation)
    if len(members) > 1:
        return " | ".join(sorted({_type_surface(member) for member in members}))
    if isinstance(annotation, ast.Name):
        return _TYPE_NAMES.get(annotation.id, annotation.id)
    if isinstance(annotation, ast.Subscript):
        return f"{_type_surface(annotation.value)}[{_type_surface(annotation.slice)}]"
    if isinstance(annotation, ast.Tuple):
        return ", ".join(_type_surface(item) for item in annotation.elts)
    return ast.unparse(annotation)

def _parameter_surface(
    method: ast.FunctionDef,
) -> tuple[tuple[str, str, str, bool], ...]:
    """Compare provider parameter names, annotations, kinds, and requiredness.

    Parameters
    ----------
    method : ast.FunctionDef
        One provider overload declaration.

    Returns
    -------
    tuple of tuple of str, str, str, and bool
        Signature excluding the bound instance parameter.
    """
    parameters: list[tuple[str, str, str, bool]] = []
    positional = [*method.args.posonlyargs, *method.args.args]
    required_count = len(positional) - len(method.args.defaults)
    for index, argument in enumerate(positional):
        if argument.arg == "self":
            continue
        required = index < required_count
        if (
            argument.arg == "elements"
            and fake_module._camel_case(method.name) in _DEFAULT_POPULATIONS
        ):
            required = True
        kind = (
            "positional_only" if index < len(method.args.posonlyargs) else "positional"
        )
        parameters.append(
            (
                argument.arg,
                _type_surface(argument.annotation),
                kind,
                required,
            ),
        )
    for argument, default in zip(
        method.args.kwonlyargs,
        method.args.kw_defaults,
        strict=True,
    ):
        parameters.append(
            (
                argument.arg,
                _type_surface(argument.annotation),
                "keyword_only",
                default is None,
            ),
        )
    for kind, argument in (
        ("var_positional", method.args.vararg),
        ("var_keyword", method.args.kwarg),
    ):
        if argument is not None:
            parameters.append(
                (
                    argument.arg,
                    _type_surface(argument.annotation),
                    kind,
                    False,
                ),
            )
    return tuple(parameters)

def _external_code(_provider: object, *, prefix: str = "external") -> str:
    """Supply a native provider function under its backend registration name.

    Parameters
    ----------
    _provider : object
        Backend provider instance binding this function.
    prefix : str, optional
        Prefix to include in the returned value.

    Returns
    -------
    str
        Recognizable custom provider result.
    """
    return f"{prefix}-value"

def _replacement_name(_provider: object) -> str:
    """Supply a replacement for the backend's native name formatter.

    Parameters
    ----------
    _provider : object
        Backend provider instance binding this function.

    Returns
    -------
    str
        Recognizable replacement provider result.
    """
    return "Replacement name"

class _CustomProvider(BaseProvider):
    """Exercise custom providers written with either naming convention."""

    external_code = _external_code

    def frameworkCode(self) -> str:
        """Return a deterministic value from an existing camelCase method.

        Returns
        -------
        str
            Recognizable Orionis-style provider result.
        """
        return "framework-value"

class _ReplacementProvider(BaseProvider):
    """Override a provider already resolved through each facade wrapper."""

    first_name = _replacement_name

class _CollisionProvider(_ReplacementProvider):
    """Declare both spellings of a provider formatter."""

    def firstName(self) -> str:
        """Return the explicitly camelCase provider result.

        Returns
        -------
        str
            Result taking precedence over the native snake_case formatter.
        """
        return "CamelCase name"

class TestFake(TestCase):
    """Verify Orionis naming while preserving real Faker behavior."""

    def testProviderViewsAreLazyStableAndDictionaryFree(self) -> None:
        """Allocate optional views only when requested and retain their identity.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        self.assertIsNone(fake._unique)
        self.assertIsNone(fake._optional)
        self.assertIs(fake.unique, fake.unique)
        self.assertIsNone(fake._optional)
        self.assertIs(fake.optional, fake.optional)
        for view in (fake, fake.unique, fake.optional, fake._state):
            self.assertFalse(hasattr(view, "__dict__"))

    def testCamelCaseProviderWinsWhenBothSpellingsExist(self) -> None:
        """Retain explicit camelCase precedence on every provider view.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        fake.addProvider(_CollisionProvider)
        self.assertEqual(fake.firstName(), "CamelCase name")
        self.assertEqual(fake.unique.firstName(), "CamelCase name")
        self.assertEqual(fake.optional.firstName(prob=1), "CamelCase name")

    def testEquivalentBackendsShareOnlyImmutableProviderNames(self) -> None:
        """Reuse aliases without sharing random generators or bound methods.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        first = UserFactory(locale="en_US", seed=42).fake
        second = UserFactory(locale="en_US", seed=42).fake
        self.assertIs(first._state.aliases, second._state.aliases)
        self.assertIsNot(first._state, second._state)
        self.assertIsNot(first.firstName, second.firstName)
        self.assertIsNot(first.random, second.random)
        with self.assertRaises(TypeError):
            first._state.aliases["firstName"] = "last_name"
        first.addProvider(_CustomProvider)
        self.assertIsNot(first._state.aliases, second._state.aliases)
        self.assertEqual(first.externalCode(), "external-value")
        with self.assertRaises(AttributeError):
            second.externalCode()

    def testFactoryExposesFrameworkFacades(self) -> None:
        """Keep native Faker objects behind all public data generation views.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        self.assertIsInstance(fake, Fake)
        self.assertIsInstance(fake.unique, UniqueFake)
        self.assertIsInstance(fake.optional, OptionalFake)
        self.assertIsInstance(fake["en_US"], Fake)
        self.assertIsInstance(fake.unique["en_US"], UniqueFake)
        for view in (fake, fake.unique, fake.optional, fake["en_US"]):
            self.assertNotIsInstance(view, Faker)

    def testCamelCaseProvidersPreserveNativeSeededOutput(self) -> None:
        """Normalize method names without altering provider arguments or output.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        for locale in ("en_US", "es_CO"):
            with self.subTest(locale=locale):
                fake = UserFactory(locale=locale, seed=42).fake
                native = Faker(locale)
                native.seed_instance(42)
                self.assertEqual(fake.firstName(), native.first_name())
                self.assertEqual(fake.lastName(), native.last_name())
                self.assertEqual(fake.phoneNumber(), native.phone_number())
                self.assertEqual(
                    fake.randomInt(min=10, max=90, step=2),
                    native.random_int(min=10, max=90, step=2),
                )
                self.assertEqual(
                    fake.dateBetween(start_date="-10d", end_date="today"),
                    native.date_between(start_date="-10d", end_date="today"),
                )
                self.assertEqual(fake.name(), native.name())
                self.assertEqual(fake.email(), native.email())

        for locale, native_name, public_name in (
            ("en_US", "postalcode", "postalcode"),
            ("ko_KR", "postal_code", "postalCode"),
        ):
            fake = UserFactory(locale=locale, seed=42).fake
            native = Faker(locale)
            native.seed_instance(42)
            self.assertEqual(
                getattr(fake, public_name)(),
                getattr(native, native_name)(),
            )
            self.assertEqual(
                getattr(fake.unique, public_name)(),
                getattr(native.unique, native_name)(),
            )
            self.assertEqual(
                getattr(fake.optional, public_name)(prob=1),
                getattr(native.optional, native_name)(prob=1),
            )

    def testSeedInstanceOnlyResetsTheCurrentFacade(self) -> None:
        """Retain independent random generators when a factory is reseeded.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        first = UserFactory(locale="en_US", seed=42).fake
        second = UserFactory(locale="en_US", seed=42).fake
        expected = Faker("en_US")
        expected.seed_instance(42)
        self.assertEqual(first.firstName(), expected.first_name())
        first.seedInstance(99)
        reseeded = Faker("en_US")
        reseeded.seed_instance(99)
        self.assertEqual(first.firstName(), reseeded.first_name())
        expected.seed_instance(42)
        self.assertEqual(second.firstName(), expected.first_name())
        self.assertIsNot(first.random, second.random)

    def testUniqueNormalizesNamesAndSharesClearLifecycle(self) -> None:
        """Keep the same uniqueness history across facade and factory clearing.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = UserFactory(locale="en_US", seed=42)
        unique = factory.fake.unique
        value = ("one-value",)
        self.assertEqual(unique.randomElement(elements=value), "one-value")
        with self.assertRaises(UniquenessException):
            unique.randomElement(elements=value)
        unique.clear()
        self.assertEqual(unique.randomElement(elements=value), "one-value")
        factory.clearUnique()
        self.assertEqual(unique.randomElement(elements=value), "one-value")

    def testUniqueExcludeTypesRetainsSharedHistory(self) -> None:
        """Exclude selected result types while retaining uniqueness for others.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        unique = UserFactory(locale="en_US", seed=42).fake.unique
        excluded = unique.excludeTypes([int])
        self.assertIsInstance(excluded, UniqueFake)
        for _ in range(3):
            self.assertEqual(excluded.randomElement(elements=(7,)), 7)
        self.assertEqual(unique.randomElement(elements=("seen",)), "seen")
        with self.assertRaises(UniquenessException):
            excluded.randomElement(elements=("seen",))
        excluded.clear()
        self.assertEqual(excluded.randomElement(elements=("seen",)), "seen")

    def testOptionalRetainsNativeProbabilityAndSeedSemantics(self) -> None:
        """Pass probability controls through the optional camelCase facade.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        native = Faker("en_US")
        native.seed_instance(42)
        for probability in (1, 0.01, 0.5, 1, 0.5):
            self.assertEqual(
                fake.optional.phoneNumber(prob=probability),
                native.optional.phone_number(prob=probability),
            )
        with self.assertRaises(ValueError):
            fake.optional.phoneNumber(prob=0)

    def testUnknownAndSnakeCaseMembersRaiseAttributeError(self) -> None:
        """Require Orionis public names on every provider access path.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        for view in (fake, fake.unique, fake.optional):
            for member in (
                "first_name",
                "phone_number",
                "random_int",
                "missingProvider",
            ):
                with (
                    self.subTest(view=type(view).__name__, member=member),
                    self.assertRaises(AttributeError),
                ):
                    getattr(view, member)
        for member in ("factories", "providers", "seed"):
            with (
                self.subTest(member=member),
                self.assertRaises(AttributeError),
            ):
                getattr(fake, member)

    def testDirAdvertisesNormalizedProviderNames(self) -> None:
        """Make interactive discovery consistent with the framework surface.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        for view in (fake, fake.unique, fake.optional):
            members = dir(view)
            self.assertIn("firstName", members)
            self.assertIn("phoneNumber", members)
            self.assertIn("randomInt", members)
            self.assertNotIn("first_name", members)
            self.assertNotIn("phone_number", members)
            self.assertNotIn("random_int", members)

    def testCustomProvidersSupportBothNativeAndFrameworkNames(self) -> None:
        """Expose custom providers added after the facade already exists.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        first = UserFactory(locale="en_US", seed=42).fake
        second = UserFactory(locale="en_US", seed=42).fake
        first.addProvider(_CustomProvider)
        self.assertEqual(first.externalCode(prefix="custom"), "custom-value")
        self.assertEqual(first.frameworkCode(), "framework-value")
        self.assertEqual(first.unique.externalCode(), "external-value")
        self.assertEqual(first.optional.frameworkCode(prob=1), "framework-value")
        self.assertIn("externalCode", dir(first))
        self.assertIn("frameworkCode", dir(first))
        self.assertNotIn("external_code", dir(first))
        with self.assertRaises(AttributeError):
            first.external_code()
        with self.assertRaises(AttributeError):
            second.externalCode()

    def testProviderOverridesRefreshPreviouslyUsedFacadeViews(self) -> None:
        """Apply provider replacement to ordinary, optional, and unique views.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        unique = fake.unique
        optional = fake.optional
        excluded = unique.excludeTypes([str])
        fake.firstName()
        unique.firstName()
        optional.firstName(prob=1)
        excluded.firstName()
        fake.addProvider(_ReplacementProvider)
        self.assertEqual(fake.firstName(), "Replacement name")
        self.assertEqual(unique.firstName(), "Replacement name")
        self.assertEqual(optional.firstName(prob=1), "Replacement name")
        self.assertEqual(excluded.firstName(), "Replacement name")

    def testLocaleIndexingKeepsNamesAndUniqueHistory(self) -> None:
        """Retain facade boundaries and Faker state when selecting a locale.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        native = Faker("en_US")
        native.seed_instance(42)
        self.assertEqual(fake["en_US"].phoneNumber(), native["en_US"].phone_number())
        unique = fake.unique["en_US"]
        self.assertEqual(unique.randomElement(elements=("seen",)), "seen")
        with self.assertRaises(UniquenessException):
            fake.unique.randomElement(elements=("seen",))
        with self.assertRaises(KeyError):
            fake["not_a_locale"]

    def testFormatterUtilitiesUseFrameworkMethodNames(self) -> None:
        """Resolve and replace formatters without exposing native method names.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        fake = UserFactory(locale="en_US", seed=42).fake
        native = Faker("en_US")
        native.seed_instance(42)
        self.assertEqual(fake.format("firstName"), native.first_name())
        self.assertEqual(fake.getFormatter("firstName")(), native.first_name())
        fake.unique.firstName()
        fake.optional.firstName(prob=1)
        fake.setFormatter("firstName", lambda: "Custom formatter")
        self.assertEqual(fake.firstName(), "Custom formatter")
        self.assertEqual(fake.unique.firstName(), "Custom formatter")
        self.assertEqual(fake.optional.firstName(prob=1), "Custom formatter")
        for operation in (fake.format, fake.getFormatter):
            with self.assertRaises(AttributeError):
                operation("first_name")

class TestFakeStub(TestCase):
    """Keep provider signatures and IDE documentation aligned with Faker."""

    def testBundledProviderSignaturesMatchTheInstalledFakerStub(self) -> None:
        """Match names, types, parameter kinds, and overloads against Faker.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        root = Path(__file__).resolve().parents[3]
        stub_path = root / "orionis/orm/factories/fake.pyi"
        facade = _stub_methods(stub_path, "_ProviderMethods")
        native_path = Path(next(iter(faker_module.__path__))) / "proxy.pyi"
        native = _stub_methods(native_path, "Faker")
        excluded = {"items", "seed", "seed_instance", "seed_locale"}
        expected = {
            fake_module._camel_case(name): methods
            for name, methods in native.items()
            if not name.startswith("_") and name not in excluded
        }
        self.assertEqual(set(facade), set(expected))
        for name, overloads in expected.items():
            multiplier = 2 if name in _DEFAULT_POPULATIONS else 1
            self.assertEqual(len(facade[name]), len(overloads) * multiplier, name)
            observed = {
                (_parameter_surface(method), _type_surface(method.returns))
                for method in facade[name]
            }
            for method in overloads:
                self.assertIn(
                    (_parameter_surface(method), _type_surface(method.returns)),
                    observed,
                    name,
                )
            if name in _DEFAULT_POPULATIONS:
                default = next(
                    method
                    for method in facade[name]
                    if all(
                        parameter[0] != "elements"
                        for parameter in _parameter_surface(method)
                    )
                )
                self.assertEqual(
                    _type_surface(default.returns),
                    "str" if name == "randomElement" else "Sequence[str]",
                    name,
                )

    def testOptionalSignaturesAddOnlyProbabilityAndAnOuterNone(self) -> None:
        """Preserve provider overloads and annotate optional values accurately.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        root = Path(__file__).resolve().parents[3]
        stub_path = root / "orionis/orm/factories/fake.pyi"
        normal = _stub_methods(stub_path, "_ProviderMethods")
        optional = _stub_methods(stub_path, "_OptionalProviderMethods")
        self.assertEqual(set(optional), set(normal))
        for name, overloads in normal.items():
            self.assertEqual(len(optional[name]), len(overloads), name)
            observed = {
                (_parameter_surface(method), _type_surface(method.returns))
                for method in optional[name]
            }
            for method in overloads:
                union = ast.BinOp(method.returns, ast.BitOr(), ast.Constant(None))
                parameters = _parameter_surface(method)
                ordinary = tuple(
                    item for item in parameters if not item[2].startswith("var_")
                )
                variadic = tuple(
                    item for item in parameters if item[2].startswith("var_")
                )
                self.assertIn(
                    (
                        (
                            *ordinary,
                            ("prob", "float", "keyword_only", False),
                            *variadic,
                        ),
                        _type_surface(union),
                    ),
                    observed,
                    name,
                )

    def testEveryDeclarationHasNumpyHelpForItsParametersAndResult(self) -> None:
        """Require complete documentation on every public stub declaration.

        Returns
        -------
        None
            Validate overload-specific parameter help and NumPy result sections.
        """
        root = Path(__file__).resolve().parents[3]
        stub_path = root / "orionis/orm/factories/fake.pyi"
        source = stub_path.read_text(encoding="utf-8")
        self.assertLessEqual(max(map(len, source.splitlines())), 88)
        tree = ast.parse(source)
        for method in ast.walk(tree):
            if not isinstance(method, ast.FunctionDef):
                continue
            documentation = ast.get_docstring(method)
            self.assertIsNotNone(documentation, method.name)
            if documentation is None:
                continue
            self.assertIn("Returns\n-------\n", documentation, method.name)
            self.assertNotIn("Examples\n", documentation, method.name)
            for directive in (":sample", ":example", ":param ", ":meth:"):
                self.assertNotIn(directive, documentation, method.name)
            parameters = {
                parameter[0] for parameter in _parameter_surface(method)
            } - {"cls"}
            for argument in parameters:
                self.assertIn("Parameters\n----------\n", documentation)
                self.assertIn(f"{argument} :", documentation, method.name)

    def testOptionalHelpDocumentsProbabilityAndMissingResults(self) -> None:
        """Explain the native optional behavior on every optional overload.

        Returns
        -------
        None
            Validate probability limits, defaults, errors, and None results.
        """
        root = Path(__file__).resolve().parents[3]
        stub_path = root / "orionis/orm/factories/fake.pyi"
        methods = _stub_methods(stub_path, "_OptionalProviderMethods")
        for name, overloads in methods.items():
            for method in overloads:
                documentation = ast.get_docstring(method) or ""
                self.assertIn("prob : float, optional", documentation, name)
                self.assertIn("(0, 1]", documentation, name)
                self.assertIn("defaults to 0.5", documentation, name)
                self.assertIn("Return None", " ".join(documentation.split()), name)
                self.assertIn("Raises\n------\n", documentation, name)
                self.assertIn("ValueError", documentation, name)

    def testProviderHelpRetainsNativeBehaviorAndFormatterReferences(self) -> None:
        """Keep useful upstream explanations in the translated provider help.

        Returns
        -------
        None
            Validate integer bounds, placeholder behavior, and locale references.
        """
        root = Path(__file__).resolve().parents[3]
        stub_path = root / "orionis/orm/factories/fake.pyi"
        methods = _stub_methods(stub_path, "_ProviderMethods")
        integer_help = " ".join(
            (ast.get_docstring(methods["randomInt"][0]) or "").split(),
        )
        self.assertIn("range(min, max + 1, step)", integer_help)
        self.assertIn("min : int, optional", integer_help)
        self.assertIn("max : int, optional", integer_help)
        placeholder_help = ast.get_docstring(methods["bothify"][0]) or ""
        self.assertIn("Number signs", placeholder_help)
        self.assertIn("Question marks", placeholder_help)
        name_help = ast.get_docstring(methods["firstName"][0]) or ""
        self.assertIn("localized first name", name_help)
        for name, overloads in methods.items():
            for method in overloads:
                documentation = ast.get_docstring(method) or ""
                self.assertIn("Faker formatter:", documentation, name)
                self.assertIn("supporting locale", documentation, name)
                self.assertIn("https://faker.readthedocs.io/", documentation, name)

    def testStubDefinitionsAreSeparatedByABlankLine(self) -> None:
        """Separate stub declarations without splitting their decorators.

        Returns
        -------
        None
            Validate blank lines between classes, methods, and overloads.
        """
        root = Path(__file__).resolve().parents[3]
        stub_path = root / "orionis/orm/factories/fake.pyi"
        source = stub_path.read_text(encoding="utf-8")
        lines = source.splitlines()
        for scope in ast.walk(ast.parse(source)):
            if not isinstance(scope, (ast.Module, ast.ClassDef)):
                continue
            definitions = [
                node for node in scope.body
                if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            ]
            for previous, current in pairwise(definitions):
                declaration_lines = (
                    current.lineno,
                    *(decorator.lineno for decorator in current.decorator_list),
                )
                start_line = min(declaration_lines)
                self.assertGreater(start_line, previous.end_lineno + 1, current.name)
                self.assertEqual(lines[start_line - 2], "", current.name)

