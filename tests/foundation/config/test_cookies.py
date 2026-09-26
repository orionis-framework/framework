from orionis.foundation.config.http import HTTPCsrf
from orionis.foundation.config.session import Session
from orionis.http.responses import Response
from tests.foundation.config.support import ConfigurationTestCase


class TestCookieConfiguration(ConfigurationTestCase):
    def testInvalidNamesAreRejectedBeforeResponseSerialization(self) -> None:
        """Reject cookie names that would otherwise fail on the first response."""
        for value in ("bad=name", "bad;name", "bad\nname", "bad name", "é"):
            for cls, field in ((Session, "cookie"), (HTTPCsrf, "cookie_name")):
                with (
                    self.subTest(value=value, entity=cls.__name__),
                    self.assertRaises(ValueError),
                ):
                    cls(**{field: value})

    def testSecureSameSiteNoneMatchesTheResponseContract(self) -> None:
        """Validate cookie field dependencies before a consumer writes headers."""
        with self.assertRaises(ValueError):
            Session(same_site="none", secure=False)
        with self.assertRaises(ValueError):
            HTTPCsrf(xsrf_cookie=True, cookie_same_site="none", cookie_secure=False)
        config = Session(same_site="none", secure=True)
        response = Response()
        response.setCookie(
            config.cookie,
            "value",
            same_site=config.same_site,
            secure=config.secure,
        )
        self.assertIn("SameSite=none", response.getHeader("set-cookie")[0])

    def testInactiveXsrfCookiePreservesItsOptionalSettings(self) -> None:
        """Allow an inactive cookie and the documented empty browser path."""
        config = HTTPCsrf(xsrf_cookie=False, cookie_same_site="none", cookie_path="")
        self.assertEqual(config.cookie_path, "")
