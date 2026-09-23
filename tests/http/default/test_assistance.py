from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit
from orionis.http.default.assistance import (
    CHATGPT_URL_MAX_LENGTH,
    build_chatgpt_url,
)
from orionis.http.default.responses import DefaultResponses
from orionis.support.formatter.exceptions.parser import ExceptionParser
from orionis.test import TestCase
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment
from tests.http._support import replace_attribute
from tests.http.default.test_response_cache import _DefaultFixture
from tests.http.default.test_templates import _Page


def make_trace(count: int = 3, source: str = "return missing_account") -> dict:
    """Build a captured traceback ordered from the failing frame to its callers."""
    return {
        "error_type": "LookupError",
        "error_message": "Missing account & region? #42",
        "error_code": None,
        "stack_trace": [
            {
                "id": count - index,
                "filename": f"app/layer{index}.py",
                "lineno": 40 + index,
                "name": f"call{index}",
                "line_code": source,
                "code": [source],
                "lines": [40 + index],
                "code_with_lines": [f"{40 + index}:{source}"],
            }
            for index in range(count)
        ],
    }


class TestChatGPTHelp(TestCase):
    """Verify useful, bounded trace context and safe rendered assistance links."""

    def _prompt(self, url: str) -> str:
        """Read the single prompt parameter and enforce the full encoded URL limit."""
        self.assertTrue(url.isascii())
        self.assertLessEqual(len(url), CHATGPT_URL_MAX_LENGTH)
        parts = urlsplit(url)
        self.assertEqual((parts.scheme, parts.netloc, parts.path), (
            "https", "chatgpt.com", "/",
        ))
        self.assertFalse(parts.fragment)
        query = parse_qs(parts.query, strict_parsing=True, errors="strict")
        self.assertEqual(list(query), ["prompt"])
        self.assertEqual(len(query["prompt"]), 1)
        return query["prompt"][0]

    def testCompleteTraceIncludesEveryFrameAndSourceInCapturedOrder(self) -> None:
        """Keep the full compact trace, request and reply language when they fit."""
        data = make_trace()
        url, truncated = build_chatgpt_url(data, "es-CO", "GET", "/accounts/42")
        prompt = self._prompt(url)
        self.assertFalse(truncated)
        for value in (
            "Orionis", "Python", "es-CO", "GET", "/accounts/42",
            data["error_type"], data["error_message"],
        ):
            self.assertIn(value, prompt)
        positions = []
        for frame in data["stack_trace"]:
            self.assertIn(f'{frame["filename"]}:{frame["lineno"]}', prompt)
            self.assertIn(frame["name"], prompt)
            self.assertIn(frame["line_code"], prompt)
            positions.append(prompt.index(frame["filename"]))
        self.assertEqual(positions, sorted(positions))

    def testQueryEncodingPreservesUnicodeAndSeparators(self) -> None:
        """Round-trip UTF-8, quotes and query delimiters without extra parameters."""
        data = make_trace(1, 'raise ValueError("sí & también 東京 🔥")')
        data["error_message"] = 'España 東京 🔥 & next=evil? #fragment "quoted"'
        url, truncated = build_chatgpt_url(
            data, "zh-Hans", "POST", "/café?region=東京&account=42#section",
        )
        prompt = self._prompt(url)
        self.assertFalse(truncated)
        self.assertIn(data["error_message"], prompt)
        self.assertIn("zh-Hans", prompt)
        self.assertIn("/café?region=東京&account=42#section", prompt)
        self.assertIn(data["stack_trace"][0]["line_code"], prompt)

    def testOverflowDropsSourceBeforeFrameLocations(self) -> None:
        """Retain the entire call chain before spending space on long source lines."""
        data = make_trace(12, "source_detail_" * 70)
        url, truncated = build_chatgpt_url(data, "en", "GET", "/accounts")
        prompt = self._prompt(url)
        self.assertTrue(truncated)
        self.assertNotIn("source_detail_", prompt)
        for frame in data["stack_trace"]:
            self.assertIn(f'{frame["filename"]}:{frame["lineno"]}', prompt)
            self.assertIn(frame["name"], prompt)
        self.assertRegex(prompt.lower(), r"omitted|truncated|shortened")

    def testDeepTraceKeepsFailureAndReportsOmittedCallers(self) -> None:
        """Bound deep traces while retaining the failing frame and error identity."""
        data = make_trace(2000)
        url, truncated = build_chatgpt_url(data, "pt-BR", "PUT", "/accounts/42")
        prompt = self._prompt(url)
        self.assertTrue(truncated)
        for value in ("pt-BR", "LookupError", "app/layer0.py:40", "call0"):
            self.assertIn(value, prompt)
        self.assertNotIn("app/layer1999.py", prompt)
        self.assertRegex(prompt.lower(), r"\d+.*(?:omitted|truncated|shortened)")

    def testOversizedUnicodeFieldsLeaveRoomForFailureLocation(self) -> None:
        """Keep usable context when message, request and source fields are oversized."""
        data = make_trace(2, "界🔥" * 10000)
        data["error_message"] = "missing account: " + "界🔥" * 10000
        data["stack_trace"][0]["filename"] = "long/" * 10000 + "failure.py"
        url, truncated = build_chatgpt_url(
            data, "ja-JP", "PATCH", "/request/" + "界🔥" * 10000,
        )
        prompt = self._prompt(url)
        self.assertTrue(truncated)
        for value in ("ja-JP", "LookupError", "missing account", "failure.py", "call0"):
            self.assertIn(value, prompt)
        self.assertNotIn("\ufffd", prompt)

    def testNoTraceStillExplainsTheException(self) -> None:
        """Produce a helpful request when an exception has no captured frames."""
        data = make_trace(0)
        url, truncated = build_chatgpt_url(data, "fr", "GET", "/example")
        prompt = self._prompt(url)
        self.assertFalse(truncated)
        self.assertIn("LookupError", prompt)
        self.assertIn(data["error_message"], prompt)
        self.assertIn("fr", prompt)

    def testLongFailurePathLeavesRoomForAllShortCallers(self) -> None:
        """Use spare encoded capacity to retain callers after shortening a long path."""
        data = make_trace(100, "")
        data["error_message"] = "missing"
        for frame in data["stack_trace"]:
            frame.update({"filename": "x", "lineno": 1, "name": "f"})
        data["stack_trace"][0]["filename"] = "long/" * 10000 + "failure.py"
        url, truncated = build_chatgpt_url(data, "es", "GET", "/")
        prompt = self._prompt(url)
        self.assertTrue(truncated)
        self.assertIn("failure.py:1 f", prompt)
        self.assertEqual(prompt.count("x:1 f"), 99)
        self.assertIn("0 older frames omitted", prompt)

    async def testRenderedLinksHaveIconsAndPreparedTraceWithoutJavaScript(self) -> None:
        """Render accessible help links near the error heading with an encoded trace."""
        data = make_trace(2, 'raise LookupError("</script><script>probe()</script>")')

        def parse_data(_parser: ExceptionParser) -> dict:
            """Supply the captured trace without accessing external services."""
            return data

        with TemporaryDirectory() as directory:
            fixture = _DefaultFixture(Path(directory))
            fixture.settings["app.locale"] = "es-CO"
            defaults = DefaultResponses(fixture, fixture, Jinja2Engine(
                ViewEnvironment(fixture),
            ))
            with replace_attribute(ExceptionParser, "toDict", parse_data):
                response = await defaults.exception(
                    "/account?one=1&two=2", "GET", LookupError("Missing account"),
                )
            body = response.getBody()
            page = _Page(body)
            help_links = [
                (index, attrs)
                for index, (tag, attrs) in enumerate(page.elements)
                if tag == "a" and attrs.get("href", "").startswith((
                    "https://chatgpt.com/", "https://www.google.com/search",
                ))
            ]
            self.assertEqual(len(help_links), 2)
            for index, attrs in help_links:
                self.assertEqual(attrs["target"], "_blank")
                self.assertEqual(set(attrs["rel"].split()), {"noopener", "noreferrer"})
                tag, icon = page.elements[index + 1]
                self.assertEqual(tag, "svg")
                self.assertEqual(icon["aria-hidden"], "true")
                self.assertLess(
                    body.index(attrs["href"].split("?")[0].encode()),
                    body.index(b'id="exception-details-title"'),
                )
                if attrs["href"].startswith("https://chatgpt.com/"):
                    prompt = self._prompt(attrs["href"])
                    self.assertIn("es-CO", prompt)
                    self.assertIn("app/layer0.py:40", prompt)
                    self.assertIn("app/layer1.py:41", prompt)
                    self.assertIn(data["stack_trace"][0]["line_code"], prompt)
            self.assertNotIn(b"<script>probe()", body)
            self.assertFalse("".join(page.script_content).strip())
