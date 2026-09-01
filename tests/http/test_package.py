from types import ModuleType
import orionis.http as http_package
from orionis.http import factory as factory_module
from orionis.http import middleware as middleware_module
from orionis.http import request as request_module
from orionis.http import responses as responses_module
from orionis.http import types as types_module
from orionis.test import TestCase

_EXPECTED_EXPORTS: tuple[str, ...] = (
    "BaseMiddleware",
    "FileResponse",
    "HTMLResponse",
    "HttpResponse",
    "JSONResponse",
    "NextCallable",
    "PlainTextResponse",
    "RedirectResponse",
    "Request",
    "Response",
    "ResponseFactory",
    "StreamingResponse",
    "response",
)


class TestHttpPackageExports(TestCase):

    def testDeclaresTheDocumentedPublicSurface(self) -> None:
        """
        Expose exactly the documented set of public names.

        Validates that the package contract stays explicit, so adding or
        removing an export is always a deliberate change.
        """
        self.assertEqual(tuple(http_package.__all__), _EXPECTED_EXPORTS)

    def testEveryDeclaredExportIsImportable(self) -> None:
        """
        Resolve every name declared in the export list.

        Validates that ``__all__`` never advertises a symbol the package
        does not actually provide.
        """
        missing = [
            name
            for name in http_package.__all__
            if not hasattr(http_package, name)
        ]
        self.assertEqual(missing, [])

    def testNoExportShadowsASubmodule(self) -> None:
        """
        Keep every submodule reachable through attribute access.

        Validates that no re-exported symbol collides with a sibling
        module name, which would make ``orionis.http.<name>`` resolve to
        the wrong object depending on the import order.
        """
        shadowed = [
            name
            for name in http_package.__all__
            if isinstance(getattr(http_package, name), ModuleType)
        ]
        self.assertEqual(shadowed, [])

    def testResponseClassesComeFromTheResponsesModule(self) -> None:
        """
        Re-export the response hierarchy without duplicating it.

        Validates that the names exposed by the package are the very same
        objects defined in ``orionis.http.responses``.
        """
        self.assertIs(http_package.Response, responses_module.Response)
        self.assertIs(http_package.HTMLResponse, responses_module.HTMLResponse)
        self.assertIs(http_package.JSONResponse, responses_module.JSONResponse)
        self.assertIs(
            http_package.PlainTextResponse,
            responses_module.PlainTextResponse,
        )
        self.assertIs(
            http_package.RedirectResponse,
            responses_module.RedirectResponse,
        )
        self.assertIs(
            http_package.StreamingResponse,
            responses_module.StreamingResponse,
        )
        self.assertIs(http_package.FileResponse, responses_module.FileResponse)

    def testRequestAndMiddlewareComeFromTheirOwnModules(self) -> None:
        """
        Re-export the request and middleware primitives unchanged.

        Validates that the package facade adds no wrapper layer over the
        objects controllers and middleware subclass.
        """
        self.assertIs(http_package.Request, request_module.Request)
        self.assertIs(
            http_package.BaseMiddleware,
            middleware_module.BaseMiddleware,
        )
        self.assertIs(
            http_package.NextCallable,
            middleware_module.NextCallable,
        )

    def testFactoryExportsTheSharedInstance(self) -> None:
        """
        Share a single stateless response factory across the framework.

        Validates that ``response`` is the module-level instance and that
        it is an instance of the exported factory class.
        """
        self.assertIs(http_package.ResponseFactory, factory_module.ResponseFactory)
        self.assertIs(http_package.response, factory_module.response)
        self.assertIsInstance(http_package.response, factory_module.ResponseFactory)


class TestHttpResponseAlias(TestCase):

    def testAliasResolvesToTheResponseBaseClass(self) -> None:
        """
        Point the handler return alias at the response base class.

        Validates that annotating a controller with ``HttpResponse``
        accepts every concrete response subclass.
        """
        self.assertIs(types_module.HttpResponse.__value__, responses_module.Response)

    def testAliasIsReExportedByThePackage(self) -> None:
        """
        Expose the alias through the package root.

        Validates that controllers can import it from ``orionis.http``
        without reaching into the private module layout.
        """
        self.assertIs(http_package.HttpResponse, types_module.HttpResponse)

    def testAliasNameMatchesItsIdentifier(self) -> None:
        """
        Keep the alias name aligned with the exported identifier.

        Validates that type checkers and error messages report the same
        name developers write in their annotations.
        """
        self.assertEqual(types_module.HttpResponse.__name__, "HttpResponse")
